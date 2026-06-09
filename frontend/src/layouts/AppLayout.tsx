import { Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { SidebarProvider, useSidebar } from "../contexts/SidebarContext";
import { AgentChatProvider, useSessionContext } from "../contexts/AgentChatContext";
import SessionSidebar from "../components/SessionSidebar";

function AppLayoutInner() {
  const auth = useAuth();
  const session = useSessionContext();
  const sidebar = useSidebar();
  const navigate = useNavigate();

  return (
    <>
      <SessionSidebar
        sessions={session.sessions}
        activeThreadId={session.activeThreadId}
        onSelect={(threadId) => {
          session.loadSession(threadId);
          navigate("/");
        }}
        onNew={() => {
          session.startNewSession();
          navigate("/");
        }}
        onDelete={session.deleteSession}
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

export default function AppLayout() {
  return (
    <div className="h-screen bg-background">
      <SidebarProvider>
        <AgentChatProvider>
          <AppLayoutInner />
        </AgentChatProvider>
      </SidebarProvider>
    </div>
  );
}
