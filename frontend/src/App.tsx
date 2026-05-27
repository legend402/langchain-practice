import { useAgentChat } from "./hooks/useAgentChat";

import SearchForm from "./components/SearchForm";
import MessageList from "./components/MessageList";
import FeedbackPanel from "./components/FeedbackPanel";
import SessionSidebar from "./components/SessionSidebar";

export default function App() {
  const chat = useAgentChat();

  return (
    <div className="h-screen bg-background flex">
      <SessionSidebar
        sessions={chat.sessions}
        activeThreadId={chat.activeThreadId}
        onSelect={chat.loadSession}
        onNew={chat.startNewSession}
        onDelete={chat.deleteSession}
        collapsed={chat.sidebarCollapsed}
        onToggle={chat.toggleSidebar}
      />

      <div className={`flex-1 flex flex-col min-w-0 h-screen main-area ${chat.sidebarCollapsed ? "sidebar-collapsed" : "sidebar-expanded"}`}>
        <main className="flex-1 flex flex-col max-w-3xl w-full mx-auto px-4 overflow-hidden" style={{ height: "calc(100vh)" }}>
          <MessageList messages={chat.messages} loading={chat.loading} />
          <div className="flex-shrink-0 pb-4 pt-2 space-y-3">
            {chat.showFeedbackPanel && chat.currentState && (
              <FeedbackPanel
                state={chat.currentState}
                onSubmit={chat.submitFeedback}
                disabled={chat.loading}
              />
            )}
            <SearchForm onSubmit={chat.submit} loading={chat.loading} />
          </div>
        </main>
      </div>
    </div>
  );
}
