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

export type SSEEventData = {
  stream_chunk: { chunk: string; node_output_key: NodeKey | "chat" | "tools" };
  source?: "research" | "chat";
  type?: "node_update" | "research_start" | "research_end";
  node?: string;
  state?: Record<string, unknown>;
  result?: string;
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
