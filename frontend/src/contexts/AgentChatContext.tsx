import { createContext, useContext, type ReactNode } from "react";
import { useAgentChat } from "../hooks/useAgentChat";

type AgentChatValue = ReturnType<typeof useAgentChat>;

const AgentChatContext = createContext<AgentChatValue | null>(null);

/**
 * Agent 聊天状态 Context，在 AppLayout 层提供，供侧边栏和聊天页面共享
 */
export function AgentChatProvider({ children }: { children: ReactNode }) {
  const chat = useAgentChat();

  return (
    <AgentChatContext.Provider value={chat}>
      {children}
    </AgentChatContext.Provider>
  );
}

/**
 * 获取 Agent 聊天状态，必须在 AgentChatProvider 内使用
 */
export function useAgentChatContext(): AgentChatValue {
  const ctx = useContext(AgentChatContext);
  if (!ctx) throw new Error("useAgentChatContext 必须在 AgentChatProvider 内使用");
  return ctx;
}
