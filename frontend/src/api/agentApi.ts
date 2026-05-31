import type {
  SubmitRequest,
  SSEEventData,
  SSEEventHandler,
  ChatSession,
  ChatMessageFromDB,
  ChatMessage,
  AgentState,
  NodeKey,
  ResponseResult,
} from "../types/agent";

const API_BASE = "http://localhost:4030";

export interface AgentApi {
  abort: AbortController;
  submitSSETask: (
    request: SubmitRequest,
    events: SSEEventHandler,
  ) => Promise<void>;
  stopChat: (sessionId: string) => Promise<ResponseResult>;
  dispatchEvent: (events: SSEEventHandler, response: Response) => Promise<void>;
  getSessions: () => Promise<ChatSession[]>;
  getMessages: (threadId: string) => Promise<ChatMessage[]>;
  deleteSession: (threadId: string) => Promise<void>;
}

const NODE_KEYS = [
  "supervisor", "search", "read", "analyze", "tag",
  "knowledge", "review", "finalize",
] as const;

function extractNodeName(state: Record<string, unknown> | AgentState | null): string | null {
  if (!state) return null;
  for (const key of NODE_KEYS) {
    if (key in state && (state as Record<string, unknown>)[key] !== null && typeof (state as Record<string, unknown>)[key] === "object") {
      return key;
    }
  }
  return null;
}

function flattenState(
  state: Record<string, unknown> | AgentState | null,
  nodeName: string | null,
): AgentState | undefined {
  if (!state || !nodeName) return undefined;
  const s = state as Record<string, unknown>;
  const nodeData = s[nodeName];
  if (!nodeData || typeof nodeData !== "object") return undefined;
  return { ...(nodeData as Record<string, unknown>), session_id: s.session_id ?? "" } as unknown as AgentState;
}

function getNodeSummary(nodeName: string, nodeData: Record<string, unknown>): string {
  switch (nodeName) {
    case "search":
      return `搜索完成，找到 ${(nodeData.search_results as unknown[])?.length ?? 0} 篇相关资料`;
    case "read":
      return `阅读完成，提取了 ${(nodeData.read_notes as unknown[])?.length ?? 0} 条笔记`;
    case "analyze":
      return "分析完成，已构建知识结构";
    case "tag":
      return "标签生成完成";
    case "knowledge":
      return "知识总结已生成";
    case "review": {
      const r = nodeData.review_result as { status: string } | undefined;
      return r?.status === "pass" ? "审核通过" : r?.status === "need_human" ? "需要人工审核" : "审核建议修改";
    }
    case "finalize":
      return (nodeData.final_answer as string) ?? "最终总结已生成";
    default:
      return "处理完成";
  }
}

function parseMessages(rows: ChatMessageFromDB[]): ChatMessage[] {
  return rows
    .filter((r) => {
      if (r.role === "human" || r.role === "user") return true;
      const nodeName = r.node_name || extractNodeName(r.state);
      return nodeName !== "supervisor";
    })
    .map((r) => {
      const role: "human" | "ai" = (r.role === "user" || r.role === "human") ? "human" : "ai";
      const nodeName = (r.node_name || extractNodeName(r.state)) as NodeKey | null;
      const effectiveNodeName = nodeName === "chat" ? null : nodeName;
      const flatState = flattenState(r.state, effectiveNodeName);

      let content = r.content ?? "";
      if (!content && effectiveNodeName && r.state) {
        const state = r.state as Record<string, unknown>;
        const nodeData = state[effectiveNodeName] as Record<string, unknown>;
        content = effectiveNodeName === "finalize"
          ? (nodeData?.final_answer as string) ?? ""
          : nodeData ? getNodeSummary(effectiveNodeName, nodeData) : "";
      }

      return {
        id: String(r.id),
        role,
        content,
        state: flatState,
        nodeName: effectiveNodeName ?? undefined,
        timestamp: new Date(r.create_at).getTime(),
      };
    });
}

const realApi: AgentApi = {
  abort: new AbortController(),
  async submitSSETask(
    request: SubmitRequest,
    events: SSEEventHandler,
  ): Promise<void> {
    agentApi.abort.abort();
    agentApi.abort = new AbortController();
    const response = await fetch(`${API_BASE}/chat/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
      signal: agentApi.abort.signal,
    });

    await agentApi.dispatchEvent(events, response);
  },
  async dispatchEvent(events: SSEEventHandler, response: Response) {
    if (!response.ok || !response.body) {
      events.onError?.(new Error(`请求失败: ${response.status}`));
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        events.onClose?.();
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed.startsWith("data: ")) continue;
        const payload = trimmed.slice(6);
        if (payload === "[DONE]") {
          events.onClose?.();
          return;
        }
        try {
          const parsed: SSEEventData = JSON.parse(payload);
          events.onMessage?.(parsed);
        } catch {
          // skip non-JSON lines
        }
      }
    }
  },
  async stopChat(session_id: string) {
    agentApi.abort.abort();
    const res = await fetch(`${API_BASE}/chat/${session_id}/stop`, {
      method: "POST",
    });
    if (!res.ok) throw new Error(`停止会话失败: ${res.status}`);
    const data = await res.json();
    return data;
  },
  async getSessions(): Promise<ChatSession[]> {
    const res = await fetch(`${API_BASE}/chat/sessions`);
    if (!res.ok) throw new Error(`获取会话列表失败: ${res.status}`);
    const data = await res.json();
    return data.result ?? data;
  },

  async getMessages(threadId: string): Promise<ChatMessage[]> {
    const res = await fetch(`${API_BASE}/chat/${threadId}/messages`);
    if (!res.ok) throw new Error(`获取消息失败: ${res.status}`);
    const data = await res.json();
    const rows: ChatMessageFromDB[] = data.result ?? data;
    return parseMessages(rows);
  },

  async deleteSession(threadId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/chat/${threadId}`, { method: "DELETE" });
    if (!res.ok) throw new Error(`删除会话失败: ${res.status}`);
  },
};

export const agentApi: AgentApi = realApi;
