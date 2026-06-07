/** 文件上传记录 */
export interface FileUpload {
  id: string;
  file_name: string;
  file_format: string;
  file_size: number;
  create_at: string;
}

/** 知识条目 */
export interface KnowledgeEntry {
  id: string;
  user_id: string;
  title: string;
  source_type: string;
  source_id: string | null;
  chunk_count: number;
  content_preview: string;
  create_at: string;
}

/** 创建知识条目请求 */
export interface CreateEntryRequest {
  title: string;
  content?: string;
  file_id?: string;
  source_type?: string;
  source_id?: string;
}

/** 知识库检索请求 */
export interface SearchRequest {
  query: string;
  top_k?: number;
}

/** 分页结果 */
export interface PaginatedResult<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

/** 解析任务状态 */
export type ParseTaskStatus =
  | "pending"
  | "parsing"
  | "enriching_images"
  | "walking_cache"
  | "chunking"
  | "embedding"
  | "storing"
  | "completed"
  | "failed";

/** 解析任务进度 */
export interface ParseTask {
  task_id: string;
  status: ParseTaskStatus;
  detail: string;
  entry_id: string;
}

/** 异步上传响应 */
export interface AsyncEntryResponse {
  task_id: string;
}

/** 解析状态中文映射 */
export const PARSE_STATUS_LABELS: Record<ParseTaskStatus, string> = {
  pending: "等待解析",
  parsing: "文档解析中",
  enriching_images: "图片描述中",
  walking_cache: "结构化遍历中",
  chunking: "分块中",
  embedding: "向量化中",
  storing: "写入中",
  completed: "解析完成",
  failed: "解析失败",
};
