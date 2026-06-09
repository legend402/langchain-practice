import type { AgentState } from "../types/agent";
import { NODE_LABELS } from "../types/agent";

interface StateCardProps {
  state: Partial<AgentState>;
  nodeName: string;
}

const CREDIBILITY_LABEL: Record<string, string> = {
  high: "高",
  medium: "中",
  low: "低",
};

export default function StateCard({ state, nodeName }: StateCardProps) {

  function renderContent() {
    switch (nodeName) {
      case "supervisor":
        return (
          <div className="space-y-1 text-sm">
            <div>
              <span className="font-medium text-ink-100">决策:</span>{" "}
              <span className="text-accent">{state.next}</span>
            </div>
            <div className="text-ink-400">{state.supervisor_reason}</div>
          </div>
        );
      case "search":
        return (
          <div className="space-y-2">
            {state.search_results?.map((r, i) => (
              <div key={r.id ?? i} className="flex items-start gap-2 text-sm">
                <span className="text-accent font-medium min-w-[20px]">
                  {i + 1}.
                </span>
                <div className="min-w-0">
                  {r.url ? (
                    <a
                      href={r.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-accent hover:underline break-all"
                    >
                      {r.title}
                    </a>
                  ) : (
                    <span className="text-ink-100">{r.title}</span>
                  )}
                  <div className="text-[11px] text-ink-400 mt-0.5">
                    相关性: {(r.relevance * 100).toFixed(0)}% | 可信度:{" "}
                    {CREDIBILITY_LABEL[r.credibility] ?? r.credibility} | 类型:{" "}
                    {r.source_type}
                  </div>
                  {r.snippet && (
                    <p className="text-[11px] text-ink-600 mt-0.5 line-clamp-2">
                      {r.snippet}
                    </p>
                  )}
                </div>
              </div>
            ))}
            {(!state.search_results || state.search_results.length === 0) && (
              <p className="text-sm text-ink-400">暂无搜索结果</p>
            )}
          </div>
        );
      case "read":
        return (
          <div className="space-y-3 text-sm">
            {state.read_notes_summary && (
              <div>
                <span className="font-medium text-ink-100">摘要:</span>
                <p className="text-ink-400 mt-0.5">
                  {state.read_notes_summary}
                </p>
              </div>
            )}
            {state.read_notes?.map((note, i) => (
              <div key={note.source_id ?? i} className="border-t border-gray-100 pt-2 first:border-t-0 first:pt-0">
                <p className="font-medium text-ink-100 mb-1">{note.title}</p>
                {note.key_points.length > 0 && (
                  <div>
                    <span className="text-ink-400 text-xs">关键点:</span>
                    <ul className="list-disc list-inside text-ink-400 text-xs mt-0.5">
                      {note.key_points.map((p, j) => (
                        <li key={j}>{p}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {note.definitions.length > 0 && (
                  <div className="mt-1">
                    <span className="text-ink-400 text-xs">定义:</span>
                    <ul className="list-disc list-inside text-ink-400 text-xs mt-0.5">
                      {note.definitions.map((d, j) => (
                        <li key={j}>{d}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
            {(!state.read_notes || state.read_notes.length === 0) && (
              <p className="text-ink-400">暂无阅读笔记</p>
            )}
          </div>
        );
      case "analyze":
        return state.analysis_result ? (
          <div className="space-y-2 text-sm">
            <div>
              <span className="font-medium text-ink-100">核心概念:</span>{" "}
              <span className="text-ink-400">
                {state.analysis_result.core_concepts.join("、")}
              </span>
            </div>
            {state.analysis_result.structure.length > 0 && (
              <div>
                <span className="font-medium text-ink-100">知识结构:</span>
                <div className="mt-1 space-y-1">
                  {state.analysis_result.structure.map((s, i) => (
                    <div key={i} className="pl-2 border-l-2 border-accent/30">
                      <span className="text-ink-100 font-medium text-xs">
                        {s.topic}
                      </span>
                      {s.children.length > 0 && (
                        <div className="text-ink-400 text-[11px] ml-2">
                          {s.children.join("、")}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
            {state.analysis_result.key_insights.length > 0 && (
              <div>
                <span className="font-medium text-ink-100">关键洞察:</span>
                <ul className="list-disc list-inside text-ink-400 text-xs mt-0.5">
                  {state.analysis_result.key_insights.map((k, i) => (
                    <li key={i}>{k}</li>
                  ))}
                </ul>
              </div>
            )}
            {state.analysis_summary && (
              <div className="text-[11px] text-ink-600 border-t border-gray-100 pt-1.5 mt-1.5">
                {state.analysis_summary}
              </div>
            )}
          </div>
        ) : (
          <p className="text-sm text-ink-400">暂无分析结果</p>
        );
      case "tag":
        return state.tags ? (
          <div className="flex flex-wrap gap-1.5">
            {state.tags.domain.map((t) => (
              <span
                key={t}
                className="rounded-full bg-accent-bg px-2.5 py-0.5 text-xs text-accent"
              >
                {t}
              </span>
            ))}
            {state.tags.topic.map((t) => (
              <span
                key={t}
                className="rounded-full bg-purple-50 px-2.5 py-0.5 text-xs text-purple-600"
              >
                {t}
              </span>
            ))}
            {state.tags.knowledge_type.map((t) => (
              <span
                key={t}
                className="rounded-full bg-blue-50 px-2.5 py-0.5 text-xs text-blue-600"
              >
                {t}
              </span>
            ))}
            <span className="rounded-full bg-amber-50 px-2.5 py-0.5 text-xs text-warning-text">
              {state.tags.difficulty}
            </span>
            {state.tags.keywords.map((k) => (
              <span
                key={k}
                className="rounded-full bg-gray-100 px-2.5 py-0.5 text-[11px] text-ink-400"
              >
                {k}
              </span>
            ))}
          </div>
        ) : (
          <p className="text-sm text-ink-400">暂无标签</p>
        );
      case "knowledge":
        return state.knowledge_summary ? (
          <div className="space-y-2 text-sm">
            <div className="font-medium text-ink-100">
              {state.knowledge_summary.title}
            </div>
            <p className="text-ink-400 text-xs">
              {state.knowledge_summary.summary}
            </p>
            {state.knowledge_summary.key_points.length > 0 && (
              <div>
                <span className="text-ink-100 text-xs font-medium">
                  关键知识点:
                </span>
                <ul className="list-disc list-inside text-ink-400 text-xs mt-0.5">
                  {state.knowledge_summary.key_points.map((p, i) => (
                    <li key={i}>{p}</li>
                  ))}
                </ul>
              </div>
            )}
            <div className="text-[11px] text-ink-600">
              置信度: {(state.knowledge_summary.confidence * 100).toFixed(0)}%
            </div>
          </div>
        ) : (
          <p className="text-sm text-ink-400">暂无知识总结</p>
        );
      case "review":
        return state.review_result ? (
          <div className="space-y-2 text-sm">
            <div>
              <span className="font-medium text-ink-100">状态:</span>{" "}
              <span
                className={
                  state.review_result.status === "pass"
                    ? "text-success"
                    : "text-accent"
                }
              >
                {state.review_result.status === "pass"
                  ? "通过"
                  : "建议修改"}
              </span>
            </div>
            {state.review_result.issues.length > 0 && (
              <div>
                <span className="font-medium text-ink-100">问题:</span>
                <ul className="list-disc list-inside text-ink-400 text-xs mt-0.5">
                  {state.review_result.issues.map((issue, i) => (
                    <li key={i}>{issue}</li>
                  ))}
                </ul>
              </div>
            )}
            {state.review_result.suggestions.length > 0 && (
              <div>
                <span className="font-medium text-ink-100">建议:</span>
                <ul className="list-disc list-inside text-ink-400 text-xs mt-0.5">
                  {state.review_result.suggestions.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
              </div>
            )}
            <div className="text-[11px] text-ink-600">
              置信度: {(state.review_result.confidence * 100).toFixed(0)}%
            </div>
          </div>
        ) : (
          <p className="text-sm text-ink-400">暂无审核结果</p>
        );
      default:
        return (
          <p className="text-sm text-ink-400">
            暂无该节点的状态数据
          </p>
        );
    }
  }

  return (
    <div className="rounded-xl bg-white/30 border border-white/60 px-1 py-0">
      <span className="text-xs font-medium text-ink-100">
        {NODE_LABELS[nodeName] || nodeName} - 详细信息
      </span>
      <div className="mt-1">{renderContent()}</div>
    </div>
  );
}
