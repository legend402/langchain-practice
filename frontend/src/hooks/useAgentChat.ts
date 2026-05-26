import { useState, useCallback, useRef } from "react";
import type {
  AgentState,
  ChatMessage,
  HumanFeedback,
  SSEEventData,
  NodeKey,
} from "../types/agent";
import {
  agentApi,
} from "../api/agentApi";
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
  human: "人工审核",
  finalize: "完成",
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
        : r?.status === "need_human"
        ? "需要人工审核"
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
    case "human": {
      const d = event.human!;
      next.human_message = d.human_message;
      next.next = "human";
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
  const stateRef = useRef<AgentState>(createInitialState());

  const addMessage = useCallback((msg: ChatMessage) => {
    setMessages((prev) => [...prev, msg]);
  }, []);

  const submit = useCallback(
    async (query: string) => {
      const userMsg: ChatMessage = {
        id: uuid(),
        role: "user",
        content: query,
        timestamp: Date.now(),
      };
      addMessage(userMsg);
      setLoading(true);

      stateRef.current = createInitialState();

      try {
        await agentApi.submitSSETask({ query }, {
          onMessage: (event: SSEEventData) => {
            const nodeKey = getNodeKey(event);
            if (!nodeKey) return;

            const nodeData = event[nodeKey]!;
            stateRef.current = accumulateState(stateRef.current, event, nodeKey);
            setCurrentState({ ...stateRef.current });

            if (nodeKey === "supervisor") {
              return;
            }

            const isFinalize = nodeKey === "finalize";
            const agentMsg: ChatMessage = {
              id: uuid(),
              role: "agent",
              content: isFinalize
                ? (nodeData as { final_answer: string }).final_answer
                : getNodeSummary(nodeKey, nodeData),
              state: { ...stateRef.current },
              nodeName: nodeKey,
              timestamp: Date.now(),
            };
            addMessage(agentMsg);
          },
          onError: (err: Error) => {
            const errMsg: ChatMessage = {
              id: uuid(),
              role: "agent",
              content: `处理出错: ${err.message}`,
              timestamp: Date.now(),
            };
            addMessage(errMsg);
          },
          onClose: () => {},
        });
      } catch (err) {
        const errMsg: ChatMessage = {
          id: uuid(),
          role: "agent",
          content: `请求失败: ${err instanceof Error ? err.message : "未知错误"}`,
          timestamp: Date.now(),
        };
        addMessage(errMsg);
      } finally {
        setLoading(false);
      }
    },
    [addMessage],
  );

  const submitFeedback = useCallback(
    async (feedback: HumanFeedback) => {
      if (!currentState) return;
      setLoading(true);

      const feedbackMsg: ChatMessage = {
        id: uuid(),
        role: "user",
        content: `[${feedback.decision}] ${feedback.comment}`,
        timestamp: Date.now(),
      };
      addMessage(feedbackMsg);

      try {
        await agentApi.submitFeedback(
          currentState.session_id,
          feedback,
          {
            onMessage: (event: SSEEventData) => {
              const nodeKey = getNodeKey(event);
              if (!nodeKey) return;

              const nodeData = event[nodeKey]!;
              stateRef.current = accumulateState(stateRef.current, event, nodeKey);
              setCurrentState({ ...stateRef.current });

              if (nodeKey === "supervisor") {
                return;
              }

              const isFinalize = nodeKey === "finalize";
              const agentMsg: ChatMessage = {
                id: uuid(),
                role: "agent",
                content: isFinalize
                  ? (nodeData as { final_answer: string }).final_answer
                  : getNodeSummary(nodeKey, nodeData),
                state: { ...stateRef.current },
                nodeName: nodeKey,
                timestamp: Date.now(),
              };
              addMessage(agentMsg);
            },
            onError: (err: Error) => {
              const errMsg: ChatMessage = {
                id: uuid(),
                role: "agent",
                content: `处理出错: ${err.message}`,
                timestamp: Date.now(),
              };
              addMessage(errMsg);
            },
            onClose: () => {},
          }
        );
      } catch (err) {
        const errMsg: ChatMessage = {
          id: uuid(),
          role: "agent",
          content: `反馈提交失败: ${err instanceof Error ? err.message : "未知错误"}`,
          timestamp: Date.now(),
        };
        addMessage(errMsg);
      } finally {
        setLoading(false);
      }
    },
    [currentState, addMessage],
  );

  const showFeedbackPanel =
    currentState?.next === "human" ||
    currentState?.review_result?.status === "need_human";

  const showResultCard = !!currentState?.final_answer;

  return {
    messages,
    currentState,
    loading,
    submit,
    submitFeedback,
    showFeedbackPanel,
    showResultCard,
  };
}
