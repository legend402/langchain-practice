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
  FeedbackRequest,
} from "../types/agent";
import { getNodeSummary } from "../types/agent";
import { httpClient } from "./client";

export interface AgentApi {
  submitSSETask: (
    request: SubmitRequest,
    events: SSEEventHandler,
  ) => Promise<void>;
  submitFeedback: (
    sessionId: string,
    feedback: FeedbackRequest,
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

function parseMessages(rows: ChatMessageFromDB[]): ChatMessage[] {
  return rows
    .filter((r) => {
      if (r.role === "human" || r.role === "user") return true;
      const nodeName = r.node_name || extractNodeName(r.state);
      return nodeName !== "supervisor" && nodeName !== "tools" && nodeName !== "human";
    })
    .map((r) => {
      const role: "human" | "ai" = (r.role === "user" || r.role === "human") ? "human" : "ai";
      const nodeName = (r.node_name || extractNodeName(r.state)) as NodeKey | null;
      const effectiveNodeName = (nodeName as string) === "chat" ? null : nodeName;
      const flatState = flattenState(r.state, effectiveNodeName);

      let content = r.content ?? "";
      if (!content && effectiveNodeName && r.state) {
        const state = r.state as Record<string, unknown>;
        const nodeData = state[effectiveNodeName] as Record<string, unknown>;
        content = effectiveNodeName === "finalize"
          ? (nodeData?.final_answer as string) ?? ""
          : nodeData ? getNodeSummary(effectiveNodeName, nodeData) : "";
      }

      const isStep = !!effectiveNodeName && effectiveNodeName !== "finalize";

      return {
        id: String(r.id),
        role,
        content,
        state: flatState,
        nodeName: effectiveNodeName ?? undefined,
        stepSummary: isStep ? true : undefined,
        timestamp: new Date(r.create_at).getTime(),
      };
    });
}

let activeAbortController: AbortController | null = null;

const realApi: AgentApi = {
  async submitSSETask(
    request: SubmitRequest,
    events: SSEEventHandler,
  ): Promise<void> {
    if (activeAbortController) {
      activeAbortController.abort();
    }
    activeAbortController = new AbortController();
    const currentController = activeAbortController;

    const response = await httpClient.stream("/chat/start", request, {
      signal: currentController.signal,
    });
    await agentApi.dispatchEvent(events, response);
  },
  async submitFeedback(
    sessionId: string,
    feedback: FeedbackRequest,
    events: SSEEventHandler,
  ): Promise<void> {
    if (activeAbortController) {
      activeAbortController.abort();
    }
    activeAbortController = new AbortController();
    const currentController = activeAbortController;

    const response = await httpClient.stream(`/chat/${sessionId}/feedback`, feedback, {
      signal: currentController.signal,
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
    let closed = false;

    function safeClose() {
      if (closed) return;
      closed = true;
      events.onClose?.();
    }

    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        safeClose();
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
          safeClose();
          return;
        }
        try {
          const parsed: SSEEventData = JSON.parse(payload);
          events.onMessage?.(parsed);
        } catch {
        }
      }
    }
  },
  async stopChat(session_id: string) {
    if (activeAbortController) {
      activeAbortController.abort();
      activeAbortController = null;
    }
    const { data } = await httpClient.post<ResponseResult>(`/chat/${session_id}/stop`);
    return data;
  },
  async getSessions(): Promise<ChatSession[]> {
    const { data } = await httpClient.get<ChatSession[]>("/chat/sessions");
    return data;
  },

  async getMessages(threadId: string): Promise<ChatMessage[]> {
    const { data } = await httpClient.get<ChatMessageFromDB[]>(`/chat/${threadId}/messages`);
    return parseMessages(data);
  },

  async deleteSession(threadId: string): Promise<void> {
    await httpClient.delete(`/chat/${threadId}`);
  },
};

export const agentApi: AgentApi = realApi;
