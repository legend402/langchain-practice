import { useRef, useEffect, useState } from "react";
import type { AgentState, ChatMessage } from "../types/agent";
import MarkdownRenderer from "./MarkdownRenderer";
import ResultCard from "./ResultCard";
import StateCard from "./StateCard";
import {
  Bot,
  User,
  ListChecks,
  Search,
  BookOpen,
  FlaskConical,
  Tags,
  Lightbulb,
  ClipboardCheck,
  ChevronDown,
  Sparkles,
} from "lucide-react";

interface MessageListProps {
  messages: ChatMessage[];
  loading: boolean;
  currentState: AgentState | null;
  activeNode: string;
}

const NODE_LOADING_TEXT: Record<string, string> = {
  supervisor: "正在规划研究路径",
  search: "正在获取相关资料",
  read: "正在阅读并提取内容",
  analyze: "正在分析知识结构",
  tag: "正在提取标签和关键词",
  knowledge: "正在生成知识总结",
  review: "正在审核内容质量",
  human: "等待人工审核",
  finalize: "正在生成最终回答",
};

const NODE_ICON: Record<string, React.ComponentType<{ className?: string }>> = {
  search: Search,
  read: BookOpen,
  analyze: FlaskConical,
  tag: Tags,
  knowledge: Lightbulb,
  review: ClipboardCheck,
  supervisor: ListChecks,
};

function StepCard({
  msg,
  expanded,
  onToggle,
}: {
  msg: ChatMessage;
  expanded: boolean;
  onToggle: () => void;
}) {
  const Icon = msg.nodeName ? NODE_ICON[msg.nodeName] ?? Bot : Bot;
  const nodeLabel = msg.nodeName
    ? { supervisor: "规划", search: "搜索", read: "阅读", analyze: "分析", tag: "标签", knowledge: "总结", review: "审核", human: "人工审核" }[msg.nodeName] ?? msg.nodeName
    : "";

  return (
    <div className="glass-card overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-2.5 px-4 py-3 text-left hover:bg-white/30 transition-colors"
      >
        <div className="w-6 h-6 rounded-md bg-accent/10 flex items-center justify-center flex-shrink-0">
          <Icon className="w-3.5 h-3.5 text-accent" />
        </div>
        <span className="text-xs font-medium text-ink-400 flex-shrink-0">
          {nodeLabel}
        </span>
        <span className="text-sm text-ink-100 truncate flex-1">
          {msg.content}
        </span>
        <div className={`flex-shrink-0 text-ink-400 transition-transform duration-300 ${expanded ? "rotate-180" : ""}`}>
          <ChevronDown className="w-3.5 h-3.5" />
        </div>
      </button>
      <div
        className="grid transition-[grid-template-rows] duration-300 ease-in-out"
        style={{ gridTemplateRows: expanded ? "1fr" : "0fr" }}
      >
        <div className="overflow-hidden">
          <div className="px-4 pb-3 border-t border-gray-100/60 pt-2">
            {msg.state && msg.nodeName && (
              <StateCard state={msg.state} nodeName={msg.nodeName} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function MessageList({ messages, loading, currentState, activeNode }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  useEffect(() => {
    if (messages.length === 0) return;
    const last = messages[messages.length - 1];
    if (last.role === "AI" && last.nodeName && last.nodeName !== "finalize" && last.state) {
      setExpandedId(last.id);
    }
  }, [messages]);

  return (
    <div className="flex-1 overflow-y-auto overflow-x-hidden space-y-4 py-4 scrollbar-hide">
      {messages.length === 0 && !loading && (
        <div className="h-full flex flex-col items-center justify-center gap-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <h1 className="text-xl font-semibold text-ink-100 tracking-tight">
              知识点总结 Agent
            </h1>
          </div>
          <p className="text-sm text-ink-400">
            输入知识点问题，AI 自动搜索、分析、总结
          </p>
        </div>
      )}
      {messages.map((msg) => (
        <div
          key={msg.id}
          className={`flex gap-3 ${msg.role === "human" ? "justify-end" : ""}`}
        >
          {msg.role === "AI" && (
            <div className="flex-shrink-0 w-7 h-7 rounded-full bg-accent flex items-center justify-center mt-0.5">
              <Bot className="w-4 h-4 text-white" />
            </div>
          )}
          <div
            className={`max-w-[80%] min-w-0 ${
              msg.role === "human"
                ? "glass-card px-4 py-2.5"
                : "w-full"
            }`}
          >
            {msg.role === "human" ? (
              <p className="text-sm text-ink-100 whitespace-pre-wrap break-words">
                {msg.content}
              </p>
            ) : msg.nodeName === "finalize" && msg.state ? (
              <ResultCard state={msg.state} />
            ) : msg.nodeName && msg.nodeName !== "finalize" && msg.state ? (
              <StepCard
                msg={msg}
                expanded={expandedId === msg.id}
                onToggle={() => setExpandedId(expandedId === msg.id ? null : msg.id)}
              />
            ) : (
              <div className="glass-card px-4 py-3">
                <MarkdownRenderer>{msg.content}</MarkdownRenderer>
                {msg.nodeName && (
                  <span className="text-[11px] text-ink-400 mt-2 block">
                    节点: {msg.nodeName}
                  </span>
                )}
              </div>
            )}
          </div>
          {msg.role === "human" && (
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
            <span className="text-xs">
              {[...(activeNode ? NODE_LOADING_TEXT[activeNode] ?? "正在处理" : "正在处理")].map((char, i) => (
                <span
                  key={`${activeNode}-${i}`}
                  className="wave-char"
                  style={{ animationDelay: `${i * 0.1}s, ${i * 0.12}s` }}
                >
                  {char === " " ? "\u00A0" : char}
                </span>
              ))}
            </span>
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
