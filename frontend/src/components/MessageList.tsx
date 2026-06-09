import { useRef, useEffect, useState, useCallback, memo } from "react";
import type { AgentState, ChatMessage } from "../types/agent";
import { NODE_LABELS, NODE_LOADING_TEXT } from "../types/agent";
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
} from "lucide-react";

interface MessageListProps {
  messages: ChatMessage[];
  loading: boolean;
  currentState: AgentState | null;
  activeNode: string;
  activeThreadId?: string | null;
}

const NODE_ICON: Record<string, React.ComponentType<{ className?: string }>> = {
  chat: Bot,
  search: Search,
  read: BookOpen,
  analyze: FlaskConical,
  tag: Tags,
  knowledge: Lightbulb,
  review: ClipboardCheck,
  supervisor: ListChecks,
};

const StepCard = memo(function StepCard({
  msg,
  expanded,
  onToggle,
  fallbackState,
}: {
  msg: ChatMessage;
  expanded: boolean;
  onToggle: () => void;
  fallbackState?: AgentState | null;
}) {
  const Icon = msg.nodeName ? NODE_ICON[msg.nodeName] ?? Bot : Bot;
  const nodeLabel = msg.nodeName ? NODE_LABELS[msg.nodeName] ?? msg.nodeName : "";
  const displayState = msg.state ?? fallbackState;

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
            {displayState && msg.nodeName && (
              <StateCard state={displayState} nodeName={msg.nodeName} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
});

function isNearBottom(el: HTMLElement, threshold = 80): boolean {
  return el.scrollHeight - el.scrollTop - el.clientHeight < threshold;
}

export default function MessageList({ messages, loading, currentState, activeNode, activeThreadId }: MessageListProps) {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const prevMsgCountRef = useRef(messages.length);
  const prevThreadIdRef = useRef(activeThreadId);

  const forceScrollToBottom = useCallback(() => {
    const el = scrollContainerRef.current;
    if (!el) return;
    requestAnimationFrame(() => {
      el.scrollTop = el.scrollHeight;
    });
  }, []);

  const forceNextScrollRef = useRef(false);

  useEffect(() => {
    if (messages.length === 0) return;
    forceScrollToBottom();
  }, [messages.length, forceScrollToBottom]);

  useEffect(() => {
    if (prevThreadIdRef.current === activeThreadId) return;
    prevThreadIdRef.current = activeThreadId;
    forceNextScrollRef.current = true;
    forceScrollToBottom();
  }, [activeThreadId, forceScrollToBottom]);

  useEffect(() => {
    const el = scrollContainerRef.current;
    if (!el || messages.length === 0) return;
    if (isNearBottom(el)) {
      forceScrollToBottom();
    }
  }, [messages, forceScrollToBottom]);

  useEffect(() => {
    const el = scrollContainerRef.current;
    if (!el) return;
    const observer = new ResizeObserver(() => {
      if (forceNextScrollRef.current || isNearBottom(el, 150)) {
        forceNextScrollRef.current = false;
        el.scrollTop = el.scrollHeight;
      }
    });
    Array.from(el.children).forEach((child) => observer.observe(child));
    return () => observer.disconnect();
  }, [messages.length]);

  if (messages.length !== prevMsgCountRef.current) {
    prevMsgCountRef.current = messages.length;
    if (messages.length > 0) {
      const last = messages[messages.length - 1];
      if (last.role === "ai" && last.nodeName && last.nodeName !== "finalize") {
        setExpandedId(last.id);
      }
    }
  }

  const isStreaming = loading && !!activeNode;

  return (
    <div ref={scrollContainerRef} className="flex-1 overflow-y-auto overflow-x-hidden space-y-4 py-4 scrollbar-hide">
      {messages.map((msg, idx) => (
        <div
          key={msg.id}
          className={`flex gap-3 ${msg.role === "human" ? "justify-end" : ""}`}
          style={{
            containIntrinsicSize: "0 80px",
          }}
        >
          {msg.role === "ai" && (
            <div className="flex-shrink-0 w-7 h-7 rounded-full bg-accent flex items-center justify-center mt-0.5">
              <Bot className="w-4 h-4 text-white" />
            </div>
          )}
          <div
            className={`max-w-[80%] min-w-0 ${msg.role === "human"
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
            ) : msg.stepSummary ? (
              <StepCard
                msg={msg}
                expanded={expandedId === msg.id}
                onToggle={() => setExpandedId(expandedId === msg.id ? null : msg.id)}
                fallbackState={currentState}
              />
            ) : (
              <div className="glass-card px-4 py-3">
                <MarkdownRenderer streaming={isStreaming && idx === messages.length - 1}>
                  {msg.content}
                </MarkdownRenderer>
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
            <span className="text-xs text-ink-400 animate-pulse">
              {activeNode ? NODE_LOADING_TEXT[activeNode] ?? "正在处理" : "正在处理"}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
