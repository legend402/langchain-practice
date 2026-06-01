import { MessageSquarePlus, Trash2, PanelLeftClose, PanelLeft } from "lucide-react";
import type { ChatSession } from "../types/agent";

interface SessionSidebarProps {
  sessions: ChatSession[];
  activeThreadId: string | null;
  onSelect: (threadId: string) => void;
  onNew: () => void;
  onDelete: (threadId: string) => void;
  collapsed: boolean;
  onToggle: () => void;
  userEmail?: string;
  onLogout: () => void;
}

function formatTime(iso: string) {
  const d = new Date(iso);
  const now = new Date();
  const isToday = d.toDateString() === now.toDateString();
  if (isToday) return d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
  return d.toLocaleDateString("zh-CN", { month: "short", day: "numeric" });
}

export default function SessionSidebar({
  sessions,
  activeThreadId,
  onSelect,
  onNew,
  onDelete,
  collapsed,
  onToggle,
  userEmail,
  onLogout,
}: SessionSidebarProps) {
  return (
    <>
      {!collapsed && (
        <div
          className="fixed inset-0 bg-black/20 z-30 md:hidden"
          onClick={onToggle}
        />
      )}
      <aside className={`sidebar-panel ${collapsed ? "sidebar-collapsed" : ""}`}>
        <div className="flex items-center justify-between px-4 pt-4 pb-2">
          <span className="text-sm font-semibold text-ink-100 uppercase tracking-wider sidebar-label">
            历史会话
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={onNew}
              className="w-7 h-7 rounded-lg flex items-center justify-center text-ink-400 hover:text-accent hover:bg-accent-bg transition-all cursor-pointer"
              title="新建会话"
            >
              <MessageSquarePlus className="w-[18px] h-[18px]" />
            </button>
            <button
              onClick={onToggle}
              className="w-7 h-7 rounded-lg flex items-center justify-center text-ink-400 hover:text-ink-100 hover:bg-white/40 transition-all cursor-pointer"
              title="收起侧栏"
            >
              <PanelLeftClose className="w-[18px] h-[18px]" />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto overflow-x-hidden px-2 pb-3 sidebar-content">
          {sessions.length === 0 ? (
            <p className="text-xs text-ink-400 text-center py-8">暂无会话</p>
          ) : (
            <div className="space-y-0.5">
              {sessions.map((s) => (
                <div
                  key={s.thread_id}
                  onClick={() => onSelect(s.thread_id)}
                  className={`sidebar-item group ${
                    activeThreadId === s.thread_id ? "active" : ""
                  }`}
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-ink-100 truncate">
                      {s.title || "无标题"}
                    </p>
                    <p className="text-[11px] text-ink-400 mt-0.5">
                      {formatTime(s.create_at)}
                    </p>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDelete(s.thread_id);
                    }}
                    className="sidebar-delete"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="px-3 py-3 border-t border-white/30 mt-auto">
          <div className="flex items-center justify-between">
            <span className="text-xs text-ink-400 truncate">{userEmail}</span>
            <button
              onClick={onLogout}
              className="text-xs text-ink-400 hover:text-red-500 transition-colors cursor-pointer"
            >
              退出
            </button>
          </div>
        </div>
      </aside>

      {collapsed && (
        <button
          onClick={onToggle}
          className="sidebar-toggle-btn"
        >
          <PanelLeft className="w-4 h-4" />
        </button>
      )}
    </>
  );
}
