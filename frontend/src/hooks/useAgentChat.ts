import { useState, useCallback, useRef, useEffect } from "react";
import type {
  AgentState,
  ChatMessage,
  ChatSession,
  SSEEventData,
  NodeKey,
} from "../types/agent";
import { agentApi } from "../api/agentApi";
import { getNodeKey, createInitialState } from "../types/agent";

function uuid(): string {
  return Math.random().toString(36).substring(2, 10) + Date.now().toString(36);
}

const NODE_LABELS: Record<string, string> = {
  supervisor: "规划",
  search: "搜索",
  read: "阅读",
  analyze: "分析",
  tag: "标签",
  knowledge: "总结",
  review: "审核",
  finalize: "完成",
  chat: "对话",
};

function getNodeSummary(nodeKey: NodeKey, data: NonNullable<SSEEventData[NodeKey]>): string {
  switch (nodeKey) {
    case "search":
      return `搜索完成，找到 ${(data as { search_results: unknown[] }).search_results?.length ?? 0} 篇相关资料`;
    case "read":
      return `阅读完成，提取了 ${(data as { read_notes: unknown[] }).read_notes?.length ?? 0} 条笔记`;
    case "analyze":
      return "分析完成，已构建知识结构";
    case "tag":
      return "标签生成完成";
    case "knowledge":
      return "知识总结已生成";
    case "review": {
      const r = (data as { review_result: { status: string } }).review_result;
      return r?.status === "pass"
        ? "审核通过"
        : "审核建议修改，将重新规划";
    }
    case "finalize":
      return "最终总结已生成";
    default:
      return "处理完成";
  }
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

export { NODE_LABELS };

export function useAgentChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [currentState, setCurrentState] = useState<AgentState | null>(null);
  const [loading, setLoading] = useState(false);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [activeNode, setActiveNode] = useState<string>("");
  const stateRef = useRef<AgentState>(createInitialState());

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
    if (event.stream_chunk) {
      const { chunk, node_output_key } = event.stream_chunk;

      if (node_output_key === "tools") return;

      setActiveNode(node_output_key);
      setMessages((prev) => {
        const lastMsg = prev[prev.length - 1];
        if (lastMsg && lastMsg.nodeName === node_output_key) {
          const updatedMsg = { ...lastMsg, content: lastMsg.content + chunk };
          return [...prev.slice(0, -1), updatedMsg];
        } else {
          return [...prev, { id: uuid(), role: "ai", content: chunk, timestamp: Date.now(), nodeName: node_output_key }];
        }
      });
      return;
    }
    if (event.source === "research" && event.type === "node_update") {
      const nodeKey = event.node as string;
      const nodeState = event.state as Record<string, unknown>;
      if (!nodeKey || !nodeState) return;

      const flatEvent: Record<string, unknown> = { ...nodeState, session_id: event.session_id };
      const nodeData = flatEvent[nodeKey];

      stateRef.current = accumulateState(stateRef.current, flatEvent as SSEEventData, nodeKey as NodeKey);
      setCurrentState({ ...stateRef.current });

      if (nodeKey === "supervisor") {
        const nextNode = (nodeData as { next: string })?.next;
        if (nextNode) setActiveNode(nextNode);
        return;
      }
      setActiveNode(nodeKey);
      if (nodeKey === "finalize") {
        setMessages((prev) => {
          const lastMsg = prev[prev.length - 1];
          if (lastMsg && lastMsg.nodeName === "finalize") {
            return [...prev.slice(0, -1), { ...lastMsg, state: { ...stateRef.current } }];
          }
          return prev;
        });
        return;
      }

      const agentMsg: ChatMessage = {
        id: uuid(),
        role: "ai",
        content: getNodeSummary(nodeKey as NodeKey, nodeData as NonNullable<SSEEventData[NodeKey]>),
        state: { ...stateRef.current },
        nodeName: nodeKey,
        timestamp: Date.now(),
      };
      addMessage(agentMsg);
      return;
    }

    const nodeKey = getNodeKey(event);
    if (!nodeKey) return;

    const nodeData = event[nodeKey]!;
    stateRef.current = accumulateState(stateRef.current, event, nodeKey);
    setCurrentState({ ...stateRef.current });

    if (nodeKey === "supervisor") {
      const nextNode = (nodeData as { next: string })?.next;
      if (nextNode) {
        setActiveNode(nextNode);
      }
      return;
    }
    setActiveNode(nodeKey);
    if (nodeKey === "finalize") {
      setMessages((prev) => {
        const lastMsg = prev[prev.length - 1];
        if (lastMsg && lastMsg.nodeName === "finalize") {
          return [...prev.slice(0, -1), { ...lastMsg, state: { ...stateRef.current } }];
        }
        return prev;
      });
      return;
    }

    const agentMsg: ChatMessage = {
      id: uuid(),
      role: "ai",
      content: getNodeSummary(nodeKey, nodeData),
      state: { ...stateRef.current },
      nodeName: nodeKey,
      timestamp: Date.now(),
    };
    addMessage(agentMsg);
  }, [addMessage, stateRef]);

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
            const errMsg: ChatMessage = {
              id: uuid(),
              role: "ai",
              content: `处理出错: ${err.message}`,
              timestamp: Date.now(),
            };
            addMessage(errMsg);
          },
          onClose: () => { },
        });
      } catch (err) {
        const errMsg: ChatMessage = {
          id: uuid(),
          role: "ai",
          content: `请求失败: ${err instanceof Error ? err.message : "未知错误"}`,
          timestamp: Date.now(),
        };
        addMessage(errMsg);
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

  const showResultCard = !!currentState?.final_answer;

  return {
    messages,
    currentState,
    loading,
    activeNode,
    submit,
    stop,
    showResultCard,
    sessions,
    activeThreadId,
    loadSession,
    startNewSession,
    deleteSession,
  };
}
