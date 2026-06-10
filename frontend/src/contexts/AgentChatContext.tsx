import { createContext, useContext, useMemo, type ReactNode } from "react";
import { useAgentChat } from "../hooks/useAgentChat";

type AgentChatValue = ReturnType<typeof useAgentChat>;

/**
 * 会话相关状态，变化频率低，供侧边栏使用
 */
interface SessionSlice {
  sessions: AgentChatValue["sessions"];
  activeThreadId: AgentChatValue["activeThreadId"];
  loadSession: AgentChatValue["loadSession"];
  startNewSession: AgentChatValue["startNewSession"];
  deleteSession: AgentChatValue["deleteSession"];
}

/**
 * 聊天相关状态，变化频率高，供聊天页面使用
 */
interface ChatSlice {
  messages: AgentChatValue["messages"];
  currentState: AgentChatValue["currentState"];
  loading: AgentChatValue["loading"];
  activeNode: AgentChatValue["activeNode"];
  submit: AgentChatValue["submit"];
  stop: AgentChatValue["stop"];
  humanInterrupt: AgentChatValue["humanInterrupt"];
  submitFeedback: AgentChatValue["submitFeedback"];
}

const SessionContext = createContext<SessionSlice | null>(null);
const ChatContext = createContext<ChatSlice | null>(null);

/**
 * Agent 聊天状态 Provider，拆分为 SessionContext（低频）和 ChatContext（高频）
 */
export function AgentChatProvider({ children }: { children: ReactNode }) {
  const chat = useAgentChat();

  const sessionValue = useMemo<SessionSlice>(() => ({
    sessions: chat.sessions,
    activeThreadId: chat.activeThreadId,
    loadSession: chat.loadSession,
    startNewSession: chat.startNewSession,
    deleteSession: chat.deleteSession,
  }), [chat.sessions, chat.activeThreadId, chat.loadSession, chat.startNewSession, chat.deleteSession]);

  const chatValue = useMemo<ChatSlice>(() => ({
    messages: chat.messages,
    currentState: chat.currentState,
    loading: chat.loading,
    activeNode: chat.activeNode,
    submit: chat.submit,
    stop: chat.stop,
    humanInterrupt: chat.humanInterrupt,
    submitFeedback: chat.submitFeedback,
  }), [chat.messages, chat.currentState, chat.loading, chat.activeNode, chat.submit, chat.stop, chat.humanInterrupt, chat.submitFeedback]);

  return (
    <SessionContext.Provider value={sessionValue}>
      <ChatContext.Provider value={chatValue}>
        {children}
      </ChatContext.Provider>
    </SessionContext.Provider>
  );
}

export function useSessionContext(): SessionSlice {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSessionContext 必须在 AgentChatProvider 内使用");
  return ctx;
}

export function useChatContext(): ChatSlice {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error("useChatContext 必须在 AgentChatProvider 内使用");
  return ctx;
}
