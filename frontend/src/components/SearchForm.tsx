import { useState } from "react";
import { Search, Loader2 } from "lucide-react";

interface SearchFormProps {
  onSubmit: (query: string) => void;
  loading: boolean;
}

export default function SearchForm({ onSubmit, loading }: SearchFormProps) {
  const [input, setInput] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || loading) return;
    onSubmit(trimmed);
    setInput("");
  }

  return (
    <form onSubmit={handleSubmit} className="mb-4">
      <div className="glass-card flex items-center gap-2 px-4 py-3">
        <Search className="w-5 h-5 text-ink-400 flex-shrink-0" />
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="输入你要总结的知识点..."
          disabled={loading}
          className="flex-1 bg-transparent text-ink-100 text-[15px] placeholder:text-ink-600 focus:outline-none disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="flex items-center gap-1.5 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-light disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>处理中</span>
            </>
          ) : (
            "开始"
          )}
        </button>
      </div>
    </form>
  );
}
