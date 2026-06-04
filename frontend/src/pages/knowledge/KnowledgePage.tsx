import { useState, useEffect, useCallback } from "react";
import { BookOpen, Plus, Search, Trash2, FileText, Type } from "lucide-react";
import { usePagination } from "../../hooks/usePagination";
import { useSidebar } from "../../contexts/SidebarContext";
import { knowledgeApi } from "../../api/knowledgeApi";
import Pagination from "../../components/Pagination";
import AddKnowledgeModal from "./AddKnowledgeModal";
import type { KnowledgeEntry } from "../../types/knowledge";

/**
 * 格式化时间为相对时间描述
 * @param dateStr ISO 时间字符串
 * @returns 格式化后的时间描述
 */
function formatTime(dateStr: string): string {
  const d = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffSec < 60) return "刚刚";
  if (diffMin < 60) return `${diffMin}分钟前`;
  if (diffHour < 24) return `${diffHour}小时前`;
  if (diffDay < 2) return "昨天";
  if (diffDay < 30) return `${diffDay}天前`;
  return d.toLocaleDateString("zh-CN", { year: "numeric", month: "short", day: "numeric" });
}

const sourceTypeMap: Record<string, { label: string; icon: typeof FileText }> = {
  manual: { label: "手动", icon: Type },
  file: { label: "文件", icon: FileText },
};

/**
 * 知识库管理页面：展示知识条目列表，支持搜索、添加和删除
 */
export default function KnowledgePage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<KnowledgeEntry[]>([]);
  const [searching, setSearching] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);

  const {
    items,
    total,
    page,
    pages,
    loading,
    goPage,
    refresh,
  } = usePagination<KnowledgeEntry>({
    fetchFn: knowledgeApi.listEntries,
    initialSize: 12,
  });

  const doSearch = useCallback(async (query: string) => {
    if (!query.trim()) {
      setSearchResults([]);
      setSearching(false);
      return;
    }
    setSearching(true);
    try {
      const hits = await knowledgeApi.search({ query: query.trim(), top_k: 50 });
      const entryIds = [...new Set(hits.map((h) => h.entry_id))];
      const entries: KnowledgeEntry[] = [];
      for (const id of entryIds) {
        try {
          const entry = await knowledgeApi.getEntry(id);
          entries.push(entry);
        } catch {
          // skip entries that fail to load
        }
      }
      setSearchResults(entries);
    } catch {
      setSearchResults([]);
    }
    setSearching(false);
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      doSearch(searchQuery);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery, doSearch]);

  async function handleDelete(id: string) {
    if (!window.confirm("确定要删除该知识条目吗？")) return;
    try {
      await knowledgeApi.deleteEntry(id);
      refresh();
    } catch {
      // ignore delete errors
    }
  }

  const displayItems = searchQuery.trim() ? searchResults : items;
  const isSearching = searchQuery.trim().length > 0;

  function handlePageChange(n: number) {
    goPage(n);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  const isInitialLoading = items.length === 0 && loading && !isSearching;
  const sidebar = useSidebar();

  return (
    <div className={`min-h-screen flex flex-col main-area ${sidebar.collapsed ? "sidebar-collapsed" : "sidebar-expanded"}`}>
      <header className="sticky top-0 z-10 px-6 py-5 flex items-center justify-between gap-4 border-b border-white/10 bg-background/80 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <BookOpen className="w-6 h-6 text-accent" />
          <h1 className="text-2xl font-semibold text-ink-100">知识库</h1>
          {!isSearching && (
            <span className="text-sm text-ink-400 ml-1">共 {total} 条</span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-600" />
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="搜索知识..."
              className="glass-card pl-9 pr-3 py-2 text-sm text-ink-100 placeholder:text-ink-600 outline-none focus:ring-1 focus:ring-accent/50 w-56"
            />
          </div>
          <button
            onClick={() => setModalOpen(true)}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-accent text-white text-sm font-medium hover:bg-accent/90 transition-colors"
          >
            <Plus className="w-4 h-4" />
            添加知识
          </button>
        </div>
      </header>

      <main className="flex-1 px-6 py-6">
        {isInitialLoading && (
          <div className="flex items-center justify-center py-20">
            <div className="w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          </div>
        )}

        {searching && (
          <div className="flex items-center justify-center py-20">
            <div className="w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          </div>
        )}

        {displayItems.length === 0 && !loading && !searching && (
          <div className="flex flex-col items-center justify-center py-20 text-ink-400">
            <BookOpen className="w-12 h-12 mb-3 opacity-40" />
            <p className="text-lg">暂无知识条目</p>
            <p className="text-sm mt-1">点击右上角按钮添加第一条知识</p>
          </div>
        )}

        {displayItems.length > 0 && (
          <div className="relative">
            {loading && (
              <div className="absolute inset-0 bg-background/50 backdrop-blur-sm z-10 flex items-center justify-center rounded-xl">
                <div className="w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
              </div>
            )}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {displayItems.map((entry) => {
                const sourceInfo = sourceTypeMap[entry.source_type] || {
                  label: entry.source_type,
                  icon: FileText,
                };
                const SourceIcon = sourceInfo.icon;
                return (
                  <div key={entry.id} className="glass-card p-4 relative group">
                    <button
                      onClick={() => handleDelete(entry.id)}
                      className="absolute top-3 right-3 w-7 h-7 rounded-lg flex items-center justify-center text-ink-600 hover:text-red-400 hover:bg-red-400/10 transition-all opacity-0 group-hover:opacity-100"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>

                    <div className="flex items-start gap-2 mb-2 pr-8">
                      <h3 className="text-sm font-medium text-ink-100 truncate flex-1">
                        {entry.title}
                      </h3>
                    </div>

                    <div className="flex items-center gap-2 mb-2">
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-accent-bg text-accent">
                        <SourceIcon className="w-3 h-3" />
                        {sourceInfo.label}
                      </span>
                      {entry.chunk_count > 0 && (
                        <span className="text-[11px] text-ink-600">
                          {entry.chunk_count} 个片段
                        </span>
                      )}
                    </div>

                    {entry.content_preview && (
                      <p className="text-sm text-ink-400 line-clamp-2 mb-3">
                        {entry.content_preview}
                      </p>
                    )}

                    <p className="text-[11px] text-ink-600">
                      {formatTime(entry.create_at)}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {!isSearching && pages > 0 && (
          <div className="flex justify-center mt-6">
            <Pagination page={page} pages={pages} onChange={handlePageChange} />
          </div>
        )}
      </main>

      <AddKnowledgeModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSuccess={refresh}
      />
    </div>
  );
}
