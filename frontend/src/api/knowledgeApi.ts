import { httpClient } from "./client";
import type {
  KnowledgeEntry,
  CreateEntryRequest,
  PaginatedResult,
  SearchRequest,
  SearchHit,
} from "../types/knowledge";

/**
 * 创建知识条目
 * @param body - 创建知识条目请求体
 * @returns 新创建的知识条目
 */
async function createEntry(body: CreateEntryRequest): Promise<KnowledgeEntry> {
  const { data } = await httpClient.post<KnowledgeEntry>("/knowledge/entries", body);
  return data;
}

/**
 * 获取知识条目列表（分页）
 * @param page - 页码，默认 1
 * @param size - 每页条数，默认 20
 * @returns 分页知识条目结果
 */
async function listEntries(
  page: number = 1,
  size: number = 20,
): Promise<PaginatedResult<KnowledgeEntry>> {
  const { data } = await httpClient.get<PaginatedResult<KnowledgeEntry>>(
    `/knowledge/entries?page=${page}&size=${size}`,
  );
  return data;
}

/**
 * 获取单个知识条目详情
 * @param id - 知识条目 ID
 * @returns 知识条目详情
 */
async function getEntry(id: string): Promise<KnowledgeEntry> {
  const { data } = await httpClient.get<KnowledgeEntry>(`/knowledge/entries/${id}`);
  return data;
}

/**
 * 删除知识条目
 * @param id - 知识条目 ID
 */
async function deleteEntry(id: string): Promise<void> {
  await httpClient.delete(`/knowledge/entries/${id}`);
}

/**
 * 检索知识库
 * @param body - 检索请求体
 * @returns 检索结果列表
 */
async function search(body: SearchRequest): Promise<SearchHit[]> {
  const { data } = await httpClient.post<SearchHit[]>("/knowledge/search", body);
  return data;
}

export const knowledgeApi = {
  createEntry,
  listEntries,
  getEntry,
  deleteEntry,
  search,
};
