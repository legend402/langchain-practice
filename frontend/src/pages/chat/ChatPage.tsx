import { useState } from "react";
import { useAuth } from "../../hooks/useAuth";
import { useAgentChat } from "../../hooks/useAgentChat";
import type { FileUpload } from "../../types/knowledge";

import SearchForm from "../../components/SearchForm";
import MessageList from "../../components/MessageList";
import SessionSidebar from "../../components/SessionSidebar";

/**
 * 聊天主页面：包含侧栏、消息列表和搜索表单
 */
export default function ChatPage() {
  const chat = useAgentChat();
  const auth = useAuth();
  const [attachments, setAttachments] = useState<FileUpload[]>([]);

  /**
   * 添加文件附件
   * @param file - 文件上传记录
   */
  function handleAddAttachment(file: FileUpload) {
    setAttachments((prev) => [...prev, file]);
  }

  /**
   * 移除文件附件
   * @param fileId - 文件 ID
   */
  function handleRemoveAttachment(fileId: string) {
    setAttachments((prev) => prev.filter((f) => f.id !== fileId));
  }

  /**
   * 提交消息并附带文件 ID
   * @param query - 用户输入的查询内容
   */
  async function handleSubmit(query: string) {
    const fileIds = attachments.length > 0 ? attachments.map((f) => f.id) : undefined;
    setAttachments([]);
    await chat.submit(query, fileIds);
  }

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
            <SearchForm
              onSubmit={handleSubmit}
              onStop={chat.stop}
              loading={chat.loading}
              attachments={attachments}
              onAddAttachment={handleAddAttachment}
              onRemoveAttachment={handleRemoveAttachment}
            />
          </div>
        </main>
      </div>
    </div>
  );
}
