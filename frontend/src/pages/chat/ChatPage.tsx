import { useAuth } from "../../hooks/useAuth";
import { useAgentChat } from "../../hooks/useAgentChat";

import SearchForm from "../../components/SearchForm";
import MessageList from "../../components/MessageList";
import SessionSidebar from "../../components/SessionSidebar";

/**
 * 聊天主页面：包含侧栏、消息列表和搜索表单
 */
export default function ChatPage() {
  const chat = useAgentChat();
  const auth = useAuth();

  return (
    <div className="h-screen flex">
      <SessionSidebar
        sessions={chat.sessions}
        activeThreadId={chat.activeThreadId}
        onSelect={chat.loadSession}
        onNew={chat.startNewSession}
        onDelete={chat.deleteSession}
        collapsed={chat.sidebarCollapsed}
        onToggle={chat.toggleSidebar}
        userEmail={auth.user?.email}
        onLogout={auth.logout}
      />

      <div
        className={`flex-1 flex flex-col min-w-0 h-screen main-area ${
          chat.sidebarCollapsed ? "sidebar-collapsed" : "sidebar-expanded"
        }`}
      >
        <main
          className="flex-1 flex flex-col max-w-3xl w-full mx-auto px-4 overflow-hidden"
          style={{ height: "calc(100vh)" }}
        >
          <MessageList
            messages={chat.messages}
            loading={chat.loading}
            currentState={chat.currentState}
            activeNode={chat.activeNode}
          />
          <div className="shrink-0 pb-4 pt-0 space-y-3">
            <SearchForm onSubmit={chat.submit} onStop={chat.stop} loading={chat.loading} />
          </div>
        </main>
      </div>
    </div>
  );
}
