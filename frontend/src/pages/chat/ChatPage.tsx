import { useState } from "react";
import { useAgentChatContext } from "../../contexts/AgentChatContext";
import { useSidebar } from "../../contexts/SidebarContext";
import type { FileUpload } from "../../types/knowledge";

import SearchForm from "../../components/SearchForm";
import MessageList from "../../components/MessageList";

/**
 * 聊天主页面：消息列表和搜索表单（侧边栏由 AppLayout 管理）
 */
export default function ChatPage() {
  const chat = useAgentChatContext();
  const sidebar = useSidebar();
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
    <div
      className={`flex-1 flex flex-col min-w-0 h-screen main-area ${
        sidebar.collapsed ? "sidebar-collapsed" : "sidebar-expanded"
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
  );
}
