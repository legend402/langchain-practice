import { useState, useRef, useEffect } from "react";
import { Loader2, ArrowUp } from "lucide-react";

interface SearchFormProps {
  onSubmit: (query: string) => void;
  loading: boolean;
}

const MAX_ROWS = 6;
const LINE_HEIGHT = 24;

/**
 * 自动增长的输入框组件，按钮内嵌右下角
 * @param onSubmit 提交回调
 * @param loading 是否加载中
 */
export default function SearchForm({ onSubmit, loading }: SearchFormProps) {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const composingRef = useRef(false);

  /**
   * 根据内容自动调整输入框高度
   */
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    const maxHeight = LINE_HEIGHT * MAX_ROWS;
    el.style.height = Math.min(el.scrollHeight, maxHeight) + "px";
  }, [input]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || loading) return;
    onSubmit(trimmed);
    setInput("");
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey && !composingRef.current) {
      e.preventDefault();
      handleSubmit(e);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <div className="glass-card relative px-5 py-4">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onCompositionStart={() => { composingRef.current = true; }}
          onCompositionEnd={() => { composingRef.current = false; }}
          onKeyDown={handleKeyDown}
          placeholder="输入你要总结的知识点..."
          disabled={loading}
          rows={3}
          className="w-full bg-transparent text-ink-100 text-base placeholder:text-ink-600 focus:outline-none disabled:opacity-50 resize-none leading-7 scrollbar-hide pr-12"
          style={{ maxHeight: LINE_HEIGHT * MAX_ROWS + 'px', height: LINE_HEIGHT * 3 + 'px' }}
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="absolute right-4 bottom-4 w-9 h-9 rounded-full bg-accent flex items-center justify-center text-white hover:bg-accent-light disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <ArrowUp className="w-4 h-4" />
          )}
        </button>
      </div>
    </form>
  );
}
