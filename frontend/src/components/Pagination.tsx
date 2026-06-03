import { ChevronLeft, ChevronRight } from "lucide-react";

interface PaginationProps {
  page: number;
  pages: number;
  onChange: (page: number) => void;
}

/**
 * 分页导航组件
 * @param page 当前页码
 * @param pages 总页数
 * @param onChange 页码变化回调
 */
export default function Pagination({ page, pages, onChange }: PaginationProps) {
  if (pages <= 1) return null;

  function getPageNumbers(): (number | "...")[] {
    if (pages <= 7) {
      return Array.from({ length: pages }, (_, i) => i + 1);
    }
    const result: (number | "...")[] = [1];
    if (page > 3) result.push("...");
    const start = Math.max(2, page - 1);
    const end = Math.min(pages - 1, page + 1);
    for (let i = start; i <= end; i++) result.push(i);
    if (page < pages - 2) result.push("...");
    result.push(pages);
    return result;
  }

  const pageNums = getPageNumbers();

  return (
    <div className="flex items-center gap-1">
      <button
        disabled={page <= 1}
        onClick={() => onChange(page - 1)}
        className="w-8 h-8 rounded-lg text-sm flex items-center justify-center text-ink-400 hover:bg-white/40 disabled:text-ink-600/40 disabled:cursor-not-allowed transition-colors"
      >
        <ChevronLeft className="w-4 h-4" />
      </button>
      {pageNums.map((p, i) =>
        p === "..." ? (
          <span key={`ellipsis-${i}`} className="w-8 h-8 flex items-center justify-center text-ink-600 text-sm">
            ...
          </span>
        ) : (
          <button
            key={p}
            onClick={() => onChange(p)}
            className={`w-8 h-8 rounded-lg text-sm flex items-center justify-center transition-colors ${
              p === page
                ? "bg-accent text-white"
                : "text-ink-400 hover:bg-white/40"
            }`}
          >
            {p}
          </button>
        )
      )}
      <button
        disabled={page >= pages}
        onClick={() => onChange(page + 1)}
        className="w-8 h-8 rounded-lg text-sm flex items-center justify-center text-ink-400 hover:bg-white/40 disabled:text-ink-600/40 disabled:cursor-not-allowed transition-colors"
      >
        <ChevronRight className="w-4 h-4" />
      </button>
    </div>
  );
}
