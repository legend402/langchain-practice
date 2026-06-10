import { useState } from "react";
import { useChatContext, useSessionContext } from "../../contexts/AgentChatContext";
import { useSidebar } from "../../contexts/SidebarContext";
import type { FileUpload } from "../../types/knowledge";
import type { FeedbackRequest } from "../../types/agent";
import logoSvg from "../../assets/logo.svg";

import SearchForm from "../../components/SearchForm";
import MessageList from "../../components/MessageList";
import HumanFeedbackPanel from "../../components/HumanFeedbackPanel";

export default function ChatPage() {
  const chat = useChatContext();
  const session = useSessionContext();
  const sidebar = useSidebar();
  const [attachments, setAttachments] = useState<FileUpload[]>([]);

  const isEmpty = chat.messages.length === 0 && !chat.loading;

  function handleAddAttachment(file: FileUpload) {
    setAttachments((prev) => [...prev, file]);
  }

  function handleRemoveAttachment(fileId: string) {
    setAttachments((prev) => prev.filter((f) => f.id !== fileId));
  }

  async function handleSubmit(query: string) {
    const fileIds = attachments.length > 0 ? attachments.map((f) => f.id) : undefined;
    setAttachments([]);
    await chat.submit(query, fileIds);
  }

  const searchForm = (
    <SearchForm
      onSubmit={handleSubmit}
      onStop={chat.stop}
      loading={chat.loading}
      attachments={attachments}
      onAddAttachment={handleAddAttachment}
      onRemoveAttachment={handleRemoveAttachment}
    />
  );

  const feedbackPanel = chat.humanInterrupt && (
    <HumanFeedbackPanel
      interrupt={chat.humanInterrupt}
      onSubmit={(feedback: FeedbackRequest) => chat.submitFeedback(feedback)}
      loading={chat.loading}
    />
  );

  return (
    <div
      className={`flex-1 flex flex-col min-w-0 h-screen main-area ${
        sidebar.collapsed ? "sidebar-collapsed" : "sidebar-expanded"
      }`}
    >
      <main
        className={`max-w-3xl w-full mx-auto px-4 overflow-hidden ${
          isEmpty ? "flex flex-col items-center justify-center h-screen" : "flex flex-col h-screen"
        }`}
      >
        {isEmpty ? (
          <div className="flex flex-col items-center gap-6 w-full -mt-16">
            <div className="flex items-center gap-2">
              <img src={logoSvg} alt="" className="w-5 h-5 text-accent" />
              <h1 className="text-xl font-semibold text-ink-100 tracking-tight">
                知识研究助手
              </h1>
            </div>
            <p className="text-sm text-ink-400 text-center">
              提出问题，AI 将自动搜索、分析并生成结构化知识总结
            </p>
            <div className="w-full max-w-2xl">
              {searchForm}
            </div>
          </div>
        ) : (
          <>
            <MessageList
              messages={chat.messages}
              loading={chat.loading}
              currentState={chat.currentState}
              activeNode={chat.activeNode}
              activeThreadId={session.activeThreadId}
            />
            <div className="shrink-0 pb-4 pt-0 space-y-3">
              {chat.humanInterrupt ? feedbackPanel : searchForm}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
