import { useState } from "react";
import { Check, ChevronRight, CircleCheck } from "lucide-react";
import type { HumanInterrupt, FeedbackRequest, FeedbackSelection } from "../types/agent";

interface HumanFeedbackPanelProps {
  interrupt: HumanInterrupt;
  onSubmit: (feedback: FeedbackRequest) => void;
  loading: boolean;
}

/**
 * 人工干预反馈面板，根据类型显示不同的选择界面
 * @param interrupt 人工中断数据
 * @param onSubmit 提交回调
 * @param loading 是否加载中
 */
export default function HumanFeedbackPanel({ interrupt, onSubmit, loading }: HumanFeedbackPanelProps) {
  const { type, items } = interrupt;

  if (type === "confirm") {
    return <ConfirmPanel items={items} onSubmit={onSubmit} loading={loading} />;
  }
  if (type === "choose") {
    return <ChoosePanel items={items} onSubmit={onSubmit} loading={loading} />;
  }
  if (type === "question_list") {
    return <QuestionListPanel items={items} onSubmit={onSubmit} loading={loading} />;
  }
  return null;
}

function ConfirmPanel({
  items,
  onSubmit,
  loading,
}: {
  items: HumanInterrupt["items"];
  onSubmit: (feedback: FeedbackRequest) => void;
  loading: boolean;
}) {
  const [comment, setComment] = useState("");
  const item = items[0];
  if (!item) return null;

  return (
    <div className="glass-card px-5 py-4">
      <h3 className="text-base font-semibold text-ink-100 mb-1">{item.title}</h3>
      <p className="text-sm text-ink-400 mb-4">{item.description}</p>
      <textarea
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        placeholder="补充说明（可选）"
        disabled={loading}
        rows={2}
        className="w-full bg-white/50 border border-white/60 rounded-xl px-4 py-2.5 text-sm text-ink-100 placeholder:text-ink-600 focus:outline-none focus:border-accent/50 disabled:opacity-50 resize-none mb-3"
      />
      <div className="flex gap-3">
        <button
          onClick={() => onSubmit({ type: "confirm", items: [{ item_index: 0, confirmed: true, comment: comment.trim() || undefined }] })}
          disabled={loading}
          className="flex-1 px-4 py-2.5 rounded-xl bg-accent text-white text-sm font-medium hover:bg-accent-light transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          确认
        </button>
        <button
          onClick={() => onSubmit({ type: "confirm", items: [{ item_index: 0, confirmed: false, comment: comment.trim() || undefined }] })}
          disabled={loading}
          className="flex-1 px-4 py-2.5 rounded-xl bg-white/50 text-ink-400 text-sm font-medium hover:bg-white/70 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          取消
        </button>
      </div>
    </div>
  );
}

function ChoosePanel({
  items,
  onSubmit,
  loading,
}: {
  items: HumanInterrupt["items"];
  onSubmit: (feedback: FeedbackRequest) => void;
  loading: boolean;
}) {
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [comment, setComment] = useState("");
  const item = items[0];
  if (!item) return null;

  const handleOptionSelect = (idx: number) => {
    setSelectedIndex(idx);
    setComment("");
  };

  const handleCommentChange = (value: string) => {
    setComment(value);
    if (value.trim()) {
      setSelectedIndex(null);
    }
  };

  const canSubmit = selectedIndex !== null || comment.trim().length > 0;

  const handleSubmit = () => {
    if (!canSubmit) return;
    const selection: FeedbackSelection = { item_index: 0 };
    if (selectedIndex !== null) {
      selection.selected_option_index = selectedIndex;
    }
    if (comment.trim()) {
      selection.comment = comment.trim();
    }
    onSubmit({ type: "choose", items: [selection] });
  };

  return (
    <div className="glass-card px-5 py-4">
      <h3 className="text-base font-semibold text-ink-100 mb-1">{item.title}</h3>
      <p className="text-sm text-ink-400 mb-4">{item.description}</p>
      {item.options && item.options.length > 0 && (
        <div className="space-y-2 max-h-64 overflow-y-auto scrollbar-hide mb-4">
          {item.options.map((opt, idx) => (
            <button
              key={idx}
              onClick={() => handleOptionSelect(idx)}
              disabled={loading}
              className={`w-full text-left px-4 py-3 rounded-xl border transition-all ${
                selectedIndex === idx
                  ? "border-accent bg-accent-bg"
                  : "border-transparent bg-white/30 hover:bg-white/50"
              } disabled:opacity-50 disabled:cursor-not-allowed`}
            >
              <div className="flex items-center gap-3">
                <div
                  className={`w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-colors ${
                    selectedIndex === idx ? "border-accent bg-accent" : "border-ink-600"
                  }`}
                >
                  {selectedIndex === idx && <Check className="w-3 h-3 text-white" />}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-ink-100">{opt.label}</p>
                  <p className="text-xs text-ink-400 mt-0.5 line-clamp-2">{opt.description}</p>
                </div>
                <ChevronRight className={`w-4 h-4 flex-shrink-0 transition-colors ${
                  selectedIndex === idx ? "text-accent" : "text-ink-600"
                }`} />
              </div>
            </button>
          ))}
        </div>
      )}
      <div className="relative mb-3">
        <textarea
          value={comment}
          onChange={(e) => handleCommentChange(e.target.value)}
          placeholder="或输入自定义回复..."
          disabled={loading}
          rows={2}
          className="w-full bg-white/50 border border-white/60 rounded-xl px-4 py-2.5 text-sm text-ink-100 placeholder:text-ink-600 focus:outline-none focus:border-accent/50 disabled:opacity-50 resize-none"
        />
      </div>
      <button
        onClick={handleSubmit}
        disabled={!canSubmit || loading}
        className="w-full px-4 py-2.5 rounded-xl bg-accent text-white text-sm font-medium hover:bg-accent-light transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        确认
      </button>
    </div>
  );
}

function QuestionListPanel({
  items,
  onSubmit,
  loading,
}: {
  items: HumanInterrupt["items"];
  onSubmit: (feedback: FeedbackRequest) => void;
  loading: boolean;
}) {
  const [activeTab, setActiveTab] = useState(0);
  const [selections, setSelections] = useState<Record<number, number>>({});
  const [comments, setComments] = useState<Record<number, string>>({});
  const [slideDirection, setSlideDirection] = useState<"left" | "right">("left");
  const [isAnimating, setIsAnimating] = useState(false);

  const handleTabChange = (newTab: number) => {
    if (newTab === activeTab || isAnimating) return;
    setSlideDirection(newTab > activeTab ? "left" : "right");
    setIsAnimating(true);
    setTimeout(() => {
      setActiveTab(newTab);
      setIsAnimating(false);
    }, 150);
  };

  const handleSelect = (itemIndex: number, optionIndex: number) => {
    setSelections((prev) => ({ ...prev, [itemIndex]: optionIndex }));
    setComments((prev) => ({ ...prev, [itemIndex]: "" }));
  };

  const handleCommentChange = (itemIndex: number, value: string) => {
    setComments((prev) => ({ ...prev, [itemIndex]: value }));
    if (value.trim()) {
      setSelections((prev) => {
        const next = { ...prev };
        delete next[itemIndex];
        return next;
      });
    }
  };

  const isItemAnswered = (idx: number) => {
    return selections[idx] !== undefined || (comments[idx]?.trim().length ?? 0) > 0;
  };

  const handleSubmit = () => {
    const feedbackItems: FeedbackSelection[] = items.map((_, idx) => {
      const selection: FeedbackSelection = { item_index: idx };
      if (selections[idx] !== undefined) {
        selection.selected_option_index = selections[idx];
      }
      if (comments[idx]?.trim()) {
        selection.comment = comments[idx].trim();
      }
      return selection;
    });
    onSubmit({ type: "question_list", items: feedbackItems });
  };

  const allAnswered = items.every((_, idx) => isItemAnswered(idx));
  const currentItem = items[activeTab];

  return (
    <div className="glass-card overflow-hidden">
      <div className="px-5 pt-4 pb-2">
        <div className="flex gap-1 border-b border-white/40">
          {items.map((item, idx) => {
            const answered = isItemAnswered(idx);
            const isActive = activeTab === idx;
            return (
              <button
                key={idx}
                onClick={() => handleTabChange(idx)}
                disabled={loading}
                className={`relative px-4 py-2.5 text-sm font-medium transition-colors disabled:opacity-50 ${
                  isActive
                    ? "text-accent"
                    : "text-ink-400 hover:text-ink-100"
                }`}
              >
                <span className="flex items-center gap-1.5">
                  {item.title}
                  {answered && (
                    <CircleCheck className="w-3.5 h-3.5 text-success" />
                  )}
                </span>
                {isActive && (
                  <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-accent rounded-full" />
                )}
              </button>
            );
          })}
        </div>
      </div>

      <div className="relative overflow-hidden">
        <div
          className={`transition-all duration-150 ease-out ${
            isAnimating
              ? slideDirection === "left"
                ? "-translate-x-4 opacity-0"
                : "translate-x-4 opacity-0"
              : "translate-x-0 opacity-100"
          }`}
        >
          {currentItem && (
            <div className="px-5 py-4">
              <p className="text-sm text-ink-400 mb-4">{currentItem.description}</p>
              {currentItem.options && currentItem.options.length > 0 && (
                <div className="grid grid-cols-3 gap-2 mb-3">
                  {currentItem.options.map((opt, optIdx) => (
                    <button
                      key={optIdx}
                      onClick={() => handleSelect(activeTab, optIdx)}
                      disabled={loading}
                      className={`px-3 py-3 rounded-xl border text-center transition-all ${
                        selections[activeTab] === optIdx
                          ? "border-accent bg-accent-bg"
                          : "border-transparent bg-white/30 hover:bg-white/50"
                      } disabled:opacity-50 disabled:cursor-not-allowed`}
                    >
                      <p className={`text-xs font-medium ${
                        selections[activeTab] === optIdx ? "text-accent" : "text-ink-100"
                      }`}>
                        {opt.label}
                      </p>
                      <p className="text-[10px] text-ink-400 mt-1 line-clamp-2">{opt.description}</p>
                    </button>
                  ))}
                </div>
              )}
              <textarea
                value={comments[activeTab] ?? ""}
                onChange={(e) => handleCommentChange(activeTab, e.target.value)}
                placeholder="或输入自定义回复..."
                disabled={loading}
                rows={2}
                className="w-full bg-white/50 border border-white/60 rounded-xl px-4 py-2.5 text-sm text-ink-100 placeholder:text-ink-600 focus:outline-none focus:border-accent/50 disabled:opacity-50 resize-none"
              />
            </div>
          )}
        </div>
      </div>

      <div className="px-5 pb-4">
        <div className="flex items-center justify-between gap-3">
          <div className="flex gap-1">
            {items.map((_, idx) => (
              <span
                key={idx}
                className={`w-1.5 h-1.5 rounded-full transition-colors ${
                  isItemAnswered(idx) ? "bg-success" : "bg-ink-600/40"
                }`}
              />
            ))}
          </div>
          <button
            onClick={handleSubmit}
            disabled={!allAnswered || loading}
            className="px-6 py-2.5 rounded-xl bg-accent text-white text-sm font-medium hover:bg-accent-light transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            确认全部
          </button>
        </div>
      </div>
    </div>
  );
}
