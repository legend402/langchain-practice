import { httpClient } from "./client";
import { tokenStorage } from "./client";
import type {
  KnowledgeEntry,
  CreateEntryRequest,
  PaginatedResult,
  SearchRequest,
  AsyncEntryResponse,
  ParseTask,
} from "../types/knowledge";

async function createEntry(body: CreateEntryRequest): Promise<KnowledgeEntry> {
  const { data } = await httpClient.post<KnowledgeEntry>("/knowledge/entries", body);
  return data;
}

async function createEntryAsync(body: CreateEntryRequest): Promise<AsyncEntryResponse> {
  const { data } = await httpClient.post<AsyncEntryResponse>("/knowledge/entries/async", body);
  return data;
}

async function listEntries(
  page: number = 1,
  size: number = 20,
): Promise<PaginatedResult<KnowledgeEntry>> {
  const { data } = await httpClient.get<PaginatedResult<KnowledgeEntry>>(
    `/knowledge/entries?page=${page}&size=${size}`,
  );
  return data;
}

async function getEntry(id: string): Promise<KnowledgeEntry> {
  const { data } = await httpClient.get<KnowledgeEntry>(`/knowledge/entries/${id}`);
  return data;
}

async function deleteEntry(id: string): Promise<void> {
  await httpClient.delete(`/knowledge/entries/${id}`);
}

async function search(body: SearchRequest): Promise<KnowledgeEntry[]> {
  const { data } = await httpClient.post<KnowledgeEntry[]>("/knowledge/search", body);
  return data;
}

async function listActiveTasks(): Promise<ParseTask[]> {
  const { data } = await httpClient.get<ParseTask[]>("/knowledge/tasks/active");
  return data;
}

function watchTaskProgress(taskId: string): EventSource {
  const token = tokenStorage.getAccessToken();
  const url = `${httpClient.getBaseUrl()}/knowledge/tasks/${taskId}/progress?token=${token}`;
  return new EventSource(url);
}

export const knowledgeApi = {
  createEntry,
  createEntryAsync,
  listEntries,
  getEntry,
  deleteEntry,
  search,
  listActiveTasks,
  watchTaskProgress,
};
