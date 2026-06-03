import { useState } from "react";
import MarkdownRenderer from "./MarkdownRenderer";
import type { AgentState } from "../types/agent";
import { BookOpen, BookmarkPlus, Check } from "lucide-react";
import { knowledgeApi } from "../api/knowledgeApi";

interface ResultCardProps {
  state: AgentState;
}

/**
 * 结果卡片组件，展示最终研究结果并支持保存到知识库
 * @param props.state - Agent 状态数据
 */
export default function ResultCard({ state }: ResultCardProps) {
  const knowledgeTags = state.knowledge_summary?.tags ?? state.tags;
  const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");

  /**
   * 将研究结果保存到知识库
   */
  async function handleSaveToKnowledge() {
    if (saveStatus !== "idle") return;
    setSaveStatus("saving");
    try {
      const title = knowledgeTags?.topic?.[0] ?? state.final_answer.slice(0, 30) + "...";
      await knowledgeApi.createEntry({
        title,
        content: state.final_answer,
        source_type: "chat",
      });
      setSaveStatus("saved");
    } catch {
      setSaveStatus("error");
      setTimeout(() => setSaveStatus("idle"), 2000);
    }
  }

  return (
    <div className="glass-card p-5">
      <div className="flex items-center gap-2 mb-3">
        <div className="w-6 h-6 rounded-md bg-green-50 flex items-center justify-center">
          <BookOpen className="w-3.5 h-3.5 text-success" />
        </div>
        <h3 className="text-sm font-semibold text-ink-100">最终结果</h3>
      </div>
      <MarkdownRenderer className="mb-4">{state.final_answer}</MarkdownRenderer>
      {knowledgeTags && (
        <div className="flex flex-wrap gap-1.5 mb-3">
          {knowledgeTags.domain.map((t) => (
            <span
              key={t}
              className="rounded-full bg-accent-bg px-2.5 py-0.5 text-[11px] text-accent"
            >
              {t}
            </span>
          ))}
          {knowledgeTags.topic.map((t) => (
            <span
              key={t}
              className="rounded-full bg-purple-50 px-2.5 py-0.5 text-[11px] text-purple-600"
            >
              {t}
            </span>
          ))}
        </div>
      )}
      {state.knowledge_summary?.sources &&
        state.knowledge_summary.sources.length > 0 && (
          <div className="text-[11px] text-ink-400">
            <span className="font-medium">来源:</span>{" "}
            {state.knowledge_summary.sources.map((s, i) => (
              <span key={i}>
                {i > 0 && " · "}
                <a
                  href={s}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-accent hover:underline"
                >
                  {s}
                </a>
              </span>
            ))}
          </div>
        )}
      {state.knowledge_summary && (
        <div className="text-[11px] text-ink-600 mt-2">
          置信度: {(state.knowledge_summary.confidence * 100).toFixed(0)}%
        </div>
      )}
      <div className="mt-3 pt-3 border-t border-white/10">
        {saveStatus === "saved" ? (
          <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm text-success pointer-events-none">
            <Check className="w-4 h-4" />
            已保存
          </span>
        ) : (
          <button
            onClick={handleSaveToKnowledge}
            disabled={saveStatus === "saving"}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm text-accent hover:bg-accent-bg transition-colors disabled:opacity-50"
          >
            <BookmarkPlus className="w-4 h-4" />
            {saveStatus === "saving" ? "保存中..." : saveStatus === "error" ? "保存失败" : "存入知识库"}
          </button>
        )}
      </div>
    </div>
  );
}
