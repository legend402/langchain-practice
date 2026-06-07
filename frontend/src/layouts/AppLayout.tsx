import { Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { SidebarProvider, useSidebar } from "../contexts/SidebarContext";
import { AgentChatProvider, useAgentChatContext } from "../contexts/AgentChatContext";
import { ParseTaskProvider } from "../contexts/ParseTaskContext";
import SessionSidebar from "../components/SessionSidebar";

/**
 * 应用主布局内部组件：渲染侧边栏和内容区
 */
function AppLayoutInner() {
  const auth = useAuth();
  const chat = useAgentChatContext();
  const sidebar = useSidebar();
  const navigate = useNavigate();

  return (
    <>
      <SessionSidebar
        sessions={chat.sessions}
        activeThreadId={chat.activeThreadId}
        onSelect={(threadId) => {
          chat.loadSession(threadId);
          navigate("/");
        }}
        onNew={chat.startNewSession}
        onDelete={chat.deleteSession}
        collapsed={sidebar.collapsed}
        onToggle={sidebar.toggle}
        userEmail={auth.user?.email}
        onLogout={auth.logout}
      />
      <div className="h-screen">
        <Outlet />
      </div>
    </>
  );
}

/**
 * 应用主布局：包裹 SidebarProvider 和 AgentChatProvider
 */
export default function AppLayout() {
  return (
    <div className="h-screen bg-background">
      <SidebarProvider>
        <AgentChatProvider>
          <ParseTaskProvider>
            <AppLayoutInner />
          </ParseTaskProvider>
        </AgentChatProvider>
      </SidebarProvider>
    </div>
  );
}
