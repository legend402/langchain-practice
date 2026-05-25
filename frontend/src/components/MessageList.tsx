import { useRef, useEffect } from "react";
import type { ChatMessage } from "../types/agent";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import ResultCard from "./ResultCard";
import { Bot, User } from "lucide-react";

interface MessageListProps {
  messages: ChatMessage[];
  loading: boolean;
}

export default function MessageList({ messages, loading }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  if (messages.length === 0 && !loading) {
    return (
      <div className="flex-1 flex items-center justify-center py-20">
        <p className="text-ink-400 text-sm">输入知识点问题开始对话</p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto overflow-x-hidden space-y-4 pb-4">
      {messages.map((msg) => (
        <div
          key={msg.id}
          className={`flex gap-3 ${msg.role === "user" ? "justify-end" : ""}`}
        >
          {msg.role === "agent" && (
            <div className="flex-shrink-0 w-7 h-7 rounded-full bg-accent flex items-center justify-center mt-0.5">
              <Bot className="w-4 h-4 text-white" />
            </div>
          )}
          <div
            className={`max-w-[80%] min-w-0 ${
              msg.role === "user"
                ? "glass-card px-4 py-2.5"
                : "w-full"
            }`}
          >
            {msg.role === "user" ? (
              <p className="text-sm text-ink-100 whitespace-pre-wrap break-words">
                {msg.content}
              </p>
            ) : msg.nodeName === "finalize" && msg.state ? (
              <ResultCard state={msg.state} />
            ) : (
              <div className="glass-card px-4 py-3">
                <div className="prose prose-sm max-w-none break-words text-ink-100">
                  <Markdown remarkPlugins={[remarkGfm]}>
                    {msg.content}
                  </Markdown>
                </div>
                {msg.nodeName && (
                  <span className="text-[11px] text-ink-400 mt-2 block">
                    节点: {msg.nodeName}
                  </span>
                )}
              </div>
            )}
          </div>
          {msg.role === "user" && (
            <div className="flex-shrink-0 w-7 h-7 rounded-full bg-ink-100 flex items-center justify-center mt-0.5">
              <User className="w-4 h-4 text-white" />
            </div>
          )}
        </div>
      ))}
      {loading && (
        <div className="flex gap-3">
          <div className="flex-shrink-0 w-7 h-7 rounded-full bg-accent flex items-center justify-center">
            <Bot className="w-4 h-4 text-white" />
          </div>
          <div className="glass-card px-4 py-3">
            <div className="flex items-center gap-2">
              <div className="flex gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse-dot" />
                <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse-dot [animation-delay:0.3s]" />
                <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse-dot [animation-delay:0.6s]" />
              </div>
              <span className="text-xs text-ink-400">正在处理...</span>
            </div>
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
