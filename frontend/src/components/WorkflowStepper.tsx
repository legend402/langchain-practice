import { useState } from "react";
import type { AgentState } from "../types/agent";
import {
  ListChecks,
  Search,
  BookOpen,
  FlaskConical,
  Tags,
  Lightbulb,
  ClipboardCheck,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import StateCard from "./StateCard";

interface WorkflowStepperProps {
  state: AgentState | null;
}

interface NodeDef {
  name: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

const NODES: NodeDef[] = [
  { name: "supervisor", label: "规划", icon: ListChecks },
  { name: "search", label: "搜索", icon: Search },
  { name: "read", label: "阅读", icon: BookOpen },
  { name: "analyze", label: "分析", icon: FlaskConical },
  { name: "tag", label: "标签", icon: Tags },
  { name: "knowledge", label: "总结", icon: Lightbulb },
  { name: "review", label: "审核", icon: ClipboardCheck },
];

type NodeStatus = "completed" | "current" | "pending";

export default function WorkflowStepper({ state }: WorkflowStepperProps) {
  const [expandedNode, setExpandedNode] = useState<string | null>(null);

  if (!state) return null;

  const currentNode = state.next || "";
  const executedNodes = new Set<string>();

  if (state.search_results?.length) executedNodes.add("search");
  if (state.read_notes?.length) executedNodes.add("read");
  if (state.analysis_result) executedNodes.add("analyze");
  if (state.tags) executedNodes.add("tag");
  if (state.knowledge_summary) executedNodes.add("knowledge");
  if (state.review_result) executedNodes.add("review");
  if (currentNode === "finalize" || state.final_answer) executedNodes.add("finalize");
  if (currentNode === "supervisor" && executedNodes.size === 0) executedNodes.add("supervisor");

  function getNodeStatus(name: string): NodeStatus {
    if (name === currentNode) return "current";
    if (executedNodes.has(name)) return "completed";
    return "pending";
  }

  const activeReviewBranch = state.review_result?.status ?? null;
  const activeHumanBranch = state.human_feedback?.decision ?? null;
  const showHumanGate = activeReviewBranch === "need_human" || currentNode === "human";

  return (
    <div className="glass-card p-4 mb-4">
      <div className="flex items-center gap-1 overflow-x-auto pb-1">
        {NODES.map((def, i) => {
          const status = getNodeStatus(def.name);
          const Icon = def.icon;
          const isExpanded = expandedNode === def.name;

          return (
            <div key={def.name} className="flex items-center">
              {i > 0 && (
                <div
                  className={`w-5 h-0.5 mx-0.5 ${
                    status === "pending" ? "bg-gray-200" : "bg-green-300"
                  }`}
                />
              )}
              <div
                className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-all whitespace-nowrap ${
                  status === "completed"
                    ? "bg-green-50 text-green-700 cursor-pointer hover:bg-green-100"
                    : status === "current"
                    ? "bg-accent-bg text-accent border border-accent-border animate-pulse-glow"
                    : "bg-gray-50 text-ink-600"
                }`}
                onClick={() => {
                  if (status === "completed") {
                    setExpandedNode(isExpanded ? null : def.name);
                  }
                }}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{def.label}</span>
                {status === "completed" &&
                  (isExpanded ? (
                    <ChevronUp className="w-3 h-3" />
                  ) : (
                    <ChevronDown className="w-3 h-3" />
                  ))}
              </div>
            </div>
          );
        })}
      </div>

      {(activeReviewBranch || showHumanGate) && (
        <div className="mt-3 pt-3 border-t border-gray-200/60 flex items-center gap-3 text-xs">
          <span className="text-ink-400">审核分支:</span>
          {activeReviewBranch && (
            <span className="px-2.5 py-0.5 rounded-full bg-accent-bg text-accent font-medium">
              {activeReviewBranch === "pass"
                ? "通过 → 完成"
                : activeReviewBranch === "replan"
                ? "↩ 重规划"
                : "人工审核"}
            </span>
          )}
          {showHumanGate && activeHumanBranch && (
            <span className="px-2.5 py-0.5 rounded-full bg-amber-50 text-warning-text font-medium">
              {activeHumanBranch === "approved" ? "通过 → 完成" : "↩ 修改"}
            </span>
          )}
        </div>
      )}

      {expandedNode && (
        <div className="mt-3 pt-3 border-t border-gray-200/60">
          <StateCard state={state} nodeName={expandedNode} />
        </div>
      )}
    </div>
  );
}
