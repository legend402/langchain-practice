export interface SearchResult {
  id: string;
  title: string;
  url: string | null;
  snippet: string;
  content: string;
  source_type: "official_doc" | "paper" | "book" | "article" | "blog" | "unknown";
  relevance: number;
  credibility: "high" | "medium" | "low";
}

export interface SourceIndexItem {
  id: string;
  title: string;
  url: string | null;
  source_type: string;
  credibility: "high" | "medium" | "low";
  used_by: string[];
}

export interface ReadNote {
  source_id: string;
  title: string;
  key_points: string[];
  definitions: string[];
  examples: string[];
  uncertainties: string[];
}

export interface EvidenceItem {
  source_id: string;
  claim: string;
  support: string;
  confidence: number;
}

export interface StructureNode {
  topic: string;
  children: string[];
}

export interface Relationship {
  from: string;
  to: string;
  relation: string;
}

export interface AnalysisResult {
  core_concepts: string[];
  structure: StructureNode[];
  relationships: Relationship[];
  key_insights: string[];
  difficult_points: string[];
  missing_information: string[];
  open_questions: string[];
}

export interface Tags {
  domain: string[];
  topic: string[];
  difficulty: "beginner" | "intermediate" | "advanced";
  knowledge_type: string[];
  keywords: string[];
}

export interface KnowledgeDetail {
  heading: string;
  content: string;
}

export interface KnowledgeSummary {
  title: string;
  summary: string;
  key_points: string[];
  details: KnowledgeDetail[];
  examples: string[];
  common_misunderstandings: string[];
  tags: Tags;
  sources: string[];
  confidence: number;
}

export interface ReviewResult {
  status: "pass" | "replan";
  issues: string[];
  suggestions: string[];
  next_action_hint: string | null;
  confidence: number;
}

export interface AgentState {
  session_id: string;
  next: string;
  supervisor_reason: string;

  search_results: SearchResult[];
  source_index: SourceIndexItem[];

  read_notes: ReadNote[];
  read_notes_summary: string;
  evidence_items: EvidenceItem[];

  analysis_result: AnalysisResult | null;
  analysis_summary: string;

  tags: Tags | null;
  knowledge_summary: KnowledgeSummary | null;

  review_result: ReviewResult | null;

  final_answer: string;
  errors: string[];
}

export interface SubmitRequest {
  query: string;
  thread_id?: string;
  file_ids?: string[];
}

export interface ChatSession {
  thread_id: string;
  title: string | null;
  create_at: string;
}

export interface ChatMessage {
  id: string;
  role: "human" | "ai";
  content: string;
  state?: AgentState;
  nodeName?: string;
  stepSummary?: boolean;
  timestamp: number;
}

export interface ChatMessageFromDB {
  id: number;
  thread_id: string;
  role: string;
  node_name: string | null;
  content: string | null;
  state: Record<string, unknown> | null;
  create_at: string;
}

export interface ResponseResult<T = void> {
  success: boolean;
  result: T;
  message: string;
  code: number;
  timestamp: number;
}

export interface HumanOption {
  label: string;
  description: string;
}

export interface HumanItem {
  title: string;
  description: string;
  options?: HumanOption[];
}

export interface HumanInterrupt {
  type: "confirm" | "choose" | "question_list";
  items: HumanItem[];
}

export interface FeedbackSelection {
  item_index: number;
  confirmed?: boolean;
  selected_option_index?: number;
  comment?: string;
}

export interface FeedbackRequest {
  type: "confirm" | "choose" | "question_list";
  items: FeedbackSelection[];
}

export type SSEEventData = {
  stream_chunk: { chunk: string; node_output_key: NodeKey | "chat" | "tools" };
  source?: "research" | "chat";
  type?: "node_update" | "research_start" | "research_end";
  node?: string;
  state?: Record<string, unknown>;
  result?: string;
  human?: HumanInterrupt;
  supervisor?: { supervisor_reason: string; next: string };
  search?: {
    search_results: SearchResult[];
    source_index: SourceIndexItem[];
    trace: string[];
  };
  read?: {
    read_notes: ReadNote[];
    read_notes_summary: string;
    evidence_items: EvidenceItem[];
    trace: string[];
  };
  analyze?: {
    analysis_result: AnalysisResult;
    analysis_summary: string;
    trace: string[];
  };
  tag?: { tags: Tags; trace: string[]; next: string };
  knowledge?: { knowledge_summary: KnowledgeSummary; trace: string[] };
  review?: { review_result: ReviewResult; trace: string[] };
  finalize?: { final_answer: string; trace: string[] };
  session_id?: string;
};

export type SSEEventHandler = {
  onMessage?: (event: SSEEventData) => void;
  onError?: (error: Error) => void;
  onClose?: () => void;
};

const NODE_KEYS = [
  "supervisor",
  "search",
  "read",
  "analyze",
  "tag",
  "knowledge",
  "review",
  "finalize",
] as const;

export type NodeKey = (typeof NODE_KEYS)[number];

export function getNodeKey(event: SSEEventData): NodeKey | undefined {
  return NODE_KEYS.find((k) => k in event && event[k] !== undefined);
}

export function createInitialState(): AgentState {
  return {
    session_id: "",
    next: "",
    supervisor_reason: "",
    search_results: [],
    source_index: [],
    read_notes: [],
    read_notes_summary: "",
    evidence_items: [],
    analysis_result: null,
    analysis_summary: "",
    tags: null,
    knowledge_summary: null,
    review_result: null,
    final_answer: "",
    errors: [],
  };
}

export const NODE_LABELS: Record<string, string> = {
  supervisor: "规划",
  search: "搜索",
  read: "阅读",
  analyze: "分析",
  tag: "标签",
  knowledge: "总结",
  review: "审核",
  finalize: "完成",
  chat: "对话",
};

export const NODE_LOADING_TEXT: Record<string, string> = {
  chat: "正在思考",
  supervisor: "正在规划研究路径",
  search: "正在获取相关资料",
  read: "正在阅读并提取内容",
  analyze: "正在分析知识结构",
  tag: "正在提取标签和关键词",
  knowledge: "正在生成知识总结",
  review: "正在审核内容质量",
  finalize: "正在生成最终回答",
};

export function getNodeSummary(nodeName: string, nodeData: Record<string, unknown>): string {
  switch (nodeName) {
    case "search":
      return `搜索完成，找到 ${(nodeData.search_results as unknown[])?.length ?? 0} 篇相关资料`;
    case "read":
      return `阅读完成，提取了 ${(nodeData.read_notes as unknown[])?.length ?? 0} 条笔记`;
    case "analyze":
      return "分析完成，已构建知识结构";
    case "tag":
      return "标签生成完成";
    case "knowledge":
      return "知识总结已生成";
    case "review": {
      const r = nodeData.review_result as { status: string } | undefined;
      return r?.status === "pass" ? "审核通过" : r?.status === "need_human" ? "需要人工审核" : "审核建议修改";
    }
    case "finalize":
      return (nodeData.final_answer as string) ?? "最终总结已生成";
    default:
      return "处理完成";
  }
}
