import { httpClient, tokenStorage } from "./client";
import type { FileUpload } from "../types/knowledge";

/**
 * 上传文件
 * @param file - 要上传的文件
 * @returns 文件上传记录
 */
async function uploadFile(file: File): Promise<FileUpload> {
  const token = tokenStorage.getAccessToken();
  const formData = new FormData();
  formData.append("file", file);
  const res = await httpClient.raw("/upload/file", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  });
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
  const body = await res.json();
  return body.result;
}

/**
 * 获取当前用户的所有上传文件列表
 * @returns 文件上传记录数组
 */
async function getFiles(): Promise<FileUpload[]> {
  const { data } = await httpClient.get<FileUpload[]>("/upload/files");
  return data;
}

/**
 * 获取文件的文本内容
 * @param id - 文件 ID
 * @returns 文件文本内容
 */
async function getFileContent(id: string): Promise<{ text: string }> {
  const { data } = await httpClient.get<{ text: string }>(`/upload/files/${id}/content`);
  return data;
}

/**
 * 删除已上传的文件
 * @param id - 文件 ID
 */
async function deleteFile(id: string): Promise<void> {
  await httpClient.delete(`/upload/files/${id}`);
}

export const uploadApi = {
  uploadFile,
  getFiles,
  getFileContent,
  deleteFile,
};
