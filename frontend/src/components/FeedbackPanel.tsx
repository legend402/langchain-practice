import { useState } from "react";
import type { AgentState, HumanFeedback } from "../types/agent";
import { Check, RotateCcw, FileText, Send } from "lucide-react";

interface FeedbackPanelProps {
  state: AgentState;
  onSubmit: (feedback: HumanFeedback) => void;
  disabled: boolean;
}

export default function FeedbackPanel({
  state,
  onSubmit,
  disabled,
}: FeedbackPanelProps) {
  const [decision, setDecision] = useState<HumanFeedback["decision"]>("approved");
  const [comment, setComment] = useState("");
  const [additionalMaterial, setAdditionalMaterial] = useState("");

  function handleSubmit() {
    if (disabled) return;
    const feedback: HumanFeedback = { decision, comment };
    if (decision === "extra_input" && additionalMaterial.trim()) {
      feedback.additional_material = additionalMaterial.trim();
    }
    onSubmit(feedback);
    setComment("");
    setAdditionalMaterial("");
  }

  const actions = [
    { value: "approved" as const, label: "通过", icon: Check },
    { value: "revise" as const, label: "修改", icon: RotateCcw },
    { value: "extra_input" as const, label: "补充资料", icon: FileText },
  ];

  const humanMessage =
    state.human_message as string | undefined ??
    state.review_result?.need_human_reason ??
    "请审阅当前总结，选择下一步操作。";

  return (
    <div className="glass-card p-4 border-l-4 border-l-warning">
      <p className="text-sm text-ink-100 mb-3">{humanMessage}</p>
      {state.review_result && state.review_result.issues.length > 0 && (
        <div className="text-xs text-ink-400 mb-3">
          <span className="font-medium">审核问题:</span>
          <ul className="list-disc list-inside mt-0.5">
            {state.review_result.issues.map((issue, i) => (
              <li key={i}>{issue}</li>
            ))}
          </ul>
        </div>
      )}
      <div className="flex gap-2 mb-3">
        {actions.map((btn) => {
          const Icon = btn.icon;
          return (
            <button
              key={btn.value}
              onClick={() => setDecision(btn.value)}
              className={`flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-medium transition-all ${
                decision === btn.value
                  ? "bg-accent text-white shadow-sm"
                  : "bg-white/50 text-ink-400 hover:bg-white/80"
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {btn.label}
            </button>
          );
        })}
      </div>
      <textarea
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        placeholder="输入你的意见..."
        rows={2}
        className="w-full glass-input rounded-xl px-3 py-2 text-sm text-ink-100 placeholder:text-ink-600 focus:outline-none focus:ring-1 focus:ring-accent/30 resize-none mb-2"
      />
      {decision === "extra_input" && (
        <textarea
          value={additionalMaterial}
          onChange={(e) => setAdditionalMaterial(e.target.value)}
          placeholder="输入补充资料..."
          rows={2}
          className="w-full glass-input rounded-xl px-3 py-2 text-sm text-ink-100 placeholder:text-ink-600 focus:outline-none focus:ring-1 focus:ring-accent/30 resize-none mb-2"
        />
      )}
      <button
        onClick={handleSubmit}
        disabled={disabled}
        className="flex items-center gap-1.5 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-light disabled:opacity-40 transition-colors"
      >
        <Send className="w-3.5 h-3.5" />
        提交反馈
      </button>
    </div>
  );
}
