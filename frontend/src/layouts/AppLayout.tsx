import { Outlet } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { useAgentChat } from "../hooks/useAgentChat";
import { SidebarProvider, useSidebar } from "../contexts/SidebarContext";
import SessionSidebar from "../components/SessionSidebar";

/**
 * 应用主布局内部组件：渲染侧边栏和内容区
 */
function AppLayoutInner() {
  const auth = useAuth();
  const chat = useAgentChat();
  const sidebar = useSidebar();

  return (
    <>
      <SessionSidebar
        sessions={chat.sessions}
        activeThreadId={chat.activeThreadId}
        onSelect={(threadId) => {
          chat.loadSession(threadId);
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
 * 应用主布局：包裹 SidebarProvider
 */
export default function AppLayout() {
  return (
    <div className="h-screen bg-background">
      <SidebarProvider>
        <AppLayoutInner />
      </SidebarProvider>
    </div>
  );
}
