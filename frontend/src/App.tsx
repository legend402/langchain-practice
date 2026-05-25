import { useAgentChat } from "./hooks/useAgentChat";
import Header from "./components/Header";
import SearchForm from "./components/SearchForm";
import WorkflowStepper from "./components/WorkflowStepper";
import MessageList from "./components/MessageList";
import FeedbackPanel from "./components/FeedbackPanel";

export default function App() {
  const chat = useAgentChat();

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Header />
      <main className="flex-1 flex flex-col max-w-3xl w-full mx-auto px-4 pb-4">
        <SearchForm onSubmit={chat.submit} loading={chat.loading} />
        <WorkflowStepper state={chat.currentState} />
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
  );
}
