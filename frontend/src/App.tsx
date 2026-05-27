import { useAgentChat } from "./hooks/useAgentChat";
import Header from "./components/Header";
import SearchForm from "./components/SearchForm";
import MessageList from "./components/MessageList";
import FeedbackPanel from "./components/FeedbackPanel";
import SessionSidebar from "./components/SessionSidebar";

export default function App() {
  const chat = useAgentChat();

  return (
    <div className="min-h-screen bg-background flex">
      <SessionSidebar
        sessions={chat.sessions}
        activeThreadId={chat.activeThreadId}
        onSelect={chat.loadSession}
        onNew={chat.startNewSession}
        onDelete={chat.deleteSession}
        collapsed={chat.sidebarCollapsed}
        onToggle={chat.toggleSidebar}
      />

      <div className={`flex-1 flex flex-col min-w-0 main-area ${chat.sidebarCollapsed ? "sidebar-collapsed" : "sidebar-expanded"}`}>
        <Header />
        <main className="flex-1 flex flex-col max-w-3xl w-full mx-auto px-4 pb-4">
          <SearchForm onSubmit={chat.submit} loading={chat.loading} />
          <MessageList messages={chat.messages} loading={chat.loading} />
          {chat.showFeedbackPanel && chat.currentState && (
            <FeedbackPanel
              state={chat.currentState}
              onSubmit={chat.submitFeedback}
              disabled={chat.loading}
            />
          )}
        </main>
      </div>
    </div>
  );
}
