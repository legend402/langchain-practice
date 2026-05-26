import type {
  HumanFeedback,
  SubmitRequest,
  SSEEventData,
  SSEEventHandler,
} from "../types/agent";

const API_BASE = "http://localhost:4030";

export interface AgentApi {
  submitSSETask: (
    request: SubmitRequest,
    events: SSEEventHandler,
  ) => Promise<void>;
  submitFeedback: (
    sessionId: string,
    feedback: HumanFeedback,
    events: SSEEventHandler,
  ) => Promise<void>;
}

const realApi: AgentApi = {
  async submitSSETask(
    request: SubmitRequest,
    events: SSEEventHandler,
  ): Promise<void> {
    const response = await fetch(`${API_BASE}/chat/start`, {
      method: "POST",
      body: JSON.stringify(request),
      headers: { "Content-Type": "application/json" },
    });

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

  async submitFeedback(
    sessionId: string,
    feedback: HumanFeedback,
    events: SSEEventHandler,
  ): Promise<void> {
    const response = await fetch(`${API_BASE}/chat/${sessionId}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(feedback),
    });

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
};

export const agentApi: AgentApi = realApi;
