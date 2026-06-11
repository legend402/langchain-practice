import { useState, useCallback, useRef, useEffect } from "react";
import type {
  AgentState,
  ChatMessage,
  ChatSession,
  SSEEventData,
  NodeKey,
  HumanInterrupt,
  FeedbackRequest,
} from "../types/agent";
import { agentApi } from "../api/agentApi";
import { getNodeKey, createInitialState, getNodeSummary, NODE_LABELS } from "../types/agent";

let _seq = 0;
function uuid(): string {
  return `${Date.now().toString(36)}_${(++_seq).toString(36)}_${Math.random().toString(36).slice(2, 6)}`;
}

function accumulateState(
  prev: AgentState,
  event: SSEEventData,
  nodeKey: NodeKey,
): AgentState {
  const next: AgentState = { ...prev };
  const sessionId = event.session_id ?? prev.session_id;
  next.session_id = sessionId;

  switch (nodeKey) {
    case "supervisor": {
      const d = event.supervisor!;
      next.supervisor_reason = d.supervisor_reason;
      next.next = d.next;
      break;
    }
    case "search": {
      const d = event.search!;
      next.search_results = d.search_results;
      next.source_index = d.source_index ?? prev.source_index;
      break;
    }
    case "read": {
      const d = event.read!;
      next.read_notes = d.read_notes;
      next.read_notes_summary = d.read_notes_summary;
      next.evidence_items = d.evidence_items ?? prev.evidence_items;
      break;
    }
    case "analyze": {
      const d = event.analyze!;
      next.analysis_result = d.analysis_result;
      next.analysis_summary = d.analysis_summary;
      break;
    }
    case "tag": {
      const d = event.tag!;
      next.tags = d.tags;
      break;
    }
    case "knowledge": {
      const d = event.knowledge!;
      next.knowledge_summary = d.knowledge_summary;
      break;
    }
    case "review": {
      const d = event.review!;
      next.review_result = d.review_result;
      break;
    }
    case "finalize": {
      const d = event.finalize!;
      next.final_answer = d.final_answer;
      next.next = "finalize";
      break;
    }
  }

  return next;
}

/**
 * 将 SSE 事件归一化为统一的 node_update 结构
 * research 路径: event.state 展开后提取 nodeKey 对应的数据
 * chat 路径: 直接从 event 中查找 nodeKey
 */
function normalizeNodeUpdate(event: SSEEventData): {
  nodeKey: string;
  nodeData: unknown;
  flatEvent: SSEEventData;
} | null {
  if (event.source === "research" && event.type === "node_update") {
    const nodeKey = event.node as string;
    const nodeState = event.state as Record<string, unknown>;
    if (!nodeKey || !nodeState) return null;
    const flatEvent: Record<string, unknown> = { ...nodeState, session_id: event.session_id };
    const nodeData = flatEvent[nodeKey];
    if (!nodeData) return null;
    return { nodeKey, nodeData, flatEvent: flatEvent as SSEEventData };
  }

  const nodeKey = getNodeKey(event);
  if (!nodeKey) return null;
  return { nodeKey, nodeData: event[nodeKey]!, flatEvent: event };
}

export { NODE_LABELS };

export function useAgentChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [currentState, setCurrentState] = useState<AgentState | null>(null);
  const [loading, setLoading] = useState(false);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [activeNode, setActiveNode] = useState<string>("");
  const [humanInterrupt, setHumanInterrupt] = useState<HumanInterrupt | null>(null);
  const stateRef = useRef<AgentState>(createInitialState());

  const chunkQueue = useRef<{ chunk: string; nodeKey: string }[]>([]);
  const rafId = useRef<number>(0);

  const flushChunks = useCallback(() => {
    const queue = chunkQueue.current;
    if (queue.length === 0) return;
    chunkQueue.current = [];

    let pendingNode = "";
    setMessages((prev) => {
      const msgs = [...prev];
      let last = msgs[msgs.length - 1];
      for (const { chunk, nodeKey } of queue) {
        pendingNode = nodeKey;
        if (last && last.nodeName === nodeKey) {
          last = { ...last, content: last.content + chunk };
          msgs[msgs.length - 1] = last;
        } else {
          last = { id: uuid(), role: "ai", content: chunk, timestamp: Date.now(), nodeName: nodeKey };
          msgs.push(last);
        }
      }
      return msgs;
    });

    if (pendingNode) setActiveNode(pendingNode);
  }, []);

  const enqueueChunk = useCallback((chunk: string, nodeKey: string) => {
    chunkQueue.current.push({ chunk, nodeKey });
    if (!rafId.current) {
      rafId.current = requestAnimationFrame(() => {
        rafId.current = 0;
        flushChunks();
      });
    }
  }, [flushChunks]);

  const addMessage = useCallback((msg: ChatMessage) => {
    setMessages((prev) => [...prev, msg]);
  }, []);

  const refreshSessions = useCallback(async () => {
    try {
      const list = await agentApi.getSessions();
      setSessions(list);
    } catch { }
  }, []);

  useEffect(() => {
    refreshSessions();
  }, [refreshSessions]);

  const loadSession = useCallback(async (threadId: string) => {
    if (threadId === activeThreadId) return;
    try {
      const msgs = await agentApi.getMessages(threadId);
      setMessages(msgs);
      setActiveThreadId(threadId);
      stateRef.current = createInitialState();

      const finalizeMsg = msgs.filter((m) => m.nodeName === "finalize");
      if (finalizeMsg.length > 0 && finalizeMsg[finalizeMsg.length - 1].state) {
        setCurrentState(finalizeMsg[finalizeMsg.length - 1].state!);
      } else {
        setCurrentState(null);
      }
    } catch { }
  }, [activeThreadId]);

  const startNewSession = useCallback(() => {
    setMessages([]);
    setCurrentState(null);
    setActiveThreadId(null);
    setActiveNode("");
    setHumanInterrupt(null);
    stateRef.current = createInitialState();
  }, []);

  const deleteSession = useCallback(async (threadId: string) => {
    try {
      await agentApi.deleteSession(threadId);
      setSessions((prev) => prev.filter((s) => s.thread_id !== threadId));
      if (activeThreadId === threadId) {
        startNewSession();
      }
    } catch { }
  }, [activeThreadId, startNewSession]);

  const handleNodeUpdate = useCallback((event: SSEEventData) => {
    const normalized = normalizeNodeUpdate(event);
    if (!normalized) return;

    const { nodeKey, nodeData } = normalized;
    stateRef.current = accumulateState(stateRef.current, normalized.flatEvent, nodeKey as NodeKey);

    if (nodeKey === "supervisor") {
      const nextNode = (nodeData as { next: string })?.next;
      if (nextNode) setActiveNode(nextNode);
      return;
    }

    setActiveNode(nodeKey);

    if (nodeKey === "finalize") {
      setCurrentState({ ...stateRef.current });
      setMessages((prev) => {
        const lastMsg = prev[prev.length - 1];
        if (lastMsg && lastMsg.nodeName === "finalize") {
          return [...prev.slice(0, -1), { ...lastMsg, state: { ...stateRef.current } }];
        }
        return prev;
      });
      return;
    }

    setCurrentState({ ...stateRef.current });

    const agentMsg: ChatMessage = {
      id: uuid(),
      role: "ai",
      content: getNodeSummary(nodeKey as NodeKey, nodeData as Record<string, unknown>),
      nodeName: nodeKey,
      stepSummary: true,
      timestamp: Date.now(),
    };
    addMessage(agentMsg);
  }, [addMessage]);

  const handleMessage = useCallback((event: SSEEventData) => {
    if ((event as Record<string, unknown>).type === "stopped") {
      setLoading(false);
      setActiveNode("");
      addMessage({
        id: uuid(),
        role: "ai",
        content: "已停止生成",
        timestamp: Date.now(),
      });
      return;
    }
    if ((event as Record<string, unknown>).type === "error") {
      setLoading(false);
      addMessage({
        id: uuid(),
        role: "ai",
        content: `处理出错: ${(event as Record<string, unknown>).error}`,
        timestamp: Date.now(),
      });
      return;
    }
    if (event.human) {
      setLoading(false);
      setHumanInterrupt(event.human);
      return;
    }
    if (event.stream_chunk) {
      const { chunk, node_output_key } = event.stream_chunk;
      if (node_output_key === "tools") return;
      enqueueChunk(chunk, node_output_key);
      return;
    }

    handleNodeUpdate(event);
  }, [addMessage, enqueueChunk, handleNodeUpdate]);

  const submit = useCallback(
    async (query: string, fileIds?: string[]) => {
      const userMsg: ChatMessage = {
        id: uuid(),
        role: "human",
        content: query,
        timestamp: Date.now(),
      };
      addMessage(userMsg);
      setActiveNode("");
      setLoading(true);

      stateRef.current = createInitialState();

      try {
        let sessionRefreshed = false;
        await agentApi.submitSSETask({ query, thread_id: activeThreadId ?? undefined, file_ids: fileIds }, {
          onMessage: (event: SSEEventData) => {
            handleMessage(event);

            if (event.session_id && !sessionRefreshed) {
              sessionRefreshed = true;
              setActiveThreadId(event.session_id);
              refreshSessions();
            }
          },
          onError: (err: Error) => {
            addMessage({
              id: uuid(),
              role: "ai",
              content: `处理出错: ${err.message}`,
              timestamp: Date.now(),
            });
          },
          onClose: () => { },
        });
      } catch (err) {
        addMessage({
          id: uuid(),
          role: "ai",
          content: `请求失败: ${err instanceof Error ? err.message : "未知错误"}`,
          timestamp: Date.now(),
        });
      } finally {
        setLoading(false);
      }
    },
    [activeThreadId, addMessage, handleMessage, refreshSessions],
  );

  const stop = useCallback(async () => {
    if (!activeThreadId) return;
    try {
      await agentApi.stopChat(activeThreadId);
    } catch { }
    setLoading(false);
    setActiveNode("");
  }, [activeThreadId]);

  const submitFeedback = useCallback(
    async (feedback: FeedbackRequest) => {
      if (!activeThreadId) return;
      setHumanInterrupt(null);
      setLoading(true);
      setActiveNode("");

      try {
        await agentApi.submitFeedback(activeThreadId, feedback, {
          onMessage: (event: SSEEventData) => {
            handleMessage(event);

            if (event.session_id && !activeThreadId) {
              setActiveThreadId(event.session_id);
              refreshSessions();
            }
          },
          onError: (err: Error) => {
            addMessage({
              id: uuid(),
              role: "ai",
              content: `处理出错: ${err.message}`,
              timestamp: Date.now(),
            });
          },
          onClose: () => { },
        });
      } catch (err) {
        addMessage({
          id: uuid(),
          role: "ai",
          content: `请求失败: ${err instanceof Error ? err.message : "未知错误"}`,
          timestamp: Date.now(),
        });
      } finally {
        setLoading(false);
      }
    },
    [activeThreadId, handleMessage, refreshSessions, addMessage],
  );

  return {
    messages,
    currentState,
    loading,
    activeNode,
    submit,
    stop,
    sessions,
    activeThreadId,
    loadSession,
    startNewSession,
    deleteSession,
    humanInterrupt,
    submitFeedback,
  };
}
