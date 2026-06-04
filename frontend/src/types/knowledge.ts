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
