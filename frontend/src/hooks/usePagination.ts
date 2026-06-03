import { useState, useEffect, useCallback } from "react";
import type { PaginatedResult } from "../types/knowledge";

interface UsePaginationOptions<T> {
  initialPage?: number;
  initialSize?: number;
  fetchFn: (page: number, size: number) => Promise<PaginatedResult<T>>;
}

interface UsePaginationReturn<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
  loading: boolean;
  error: string | null;
  goPage: (page: number) => void;
  refresh: () => void;
}

/**
 * 分页状态管理 Hook
 * @param options 配置项，包含初始页码、每页数量和请求函数
 * @returns 分页状态和操作方法
 */
export function usePagination<T>({
  initialPage = 1,
  initialSize = 20,
  fetchFn,
}: UsePaginationOptions<T>): UsePaginationReturn<T> {
  const [page, setPage] = useState(initialPage);
  const [size] = useState(initialSize);
  const [items, setItems] = useState<T[]>([]);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async (targetPage: number) => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchFn(targetPage, size);
      setItems(result.items);
      setTotal(result.total);
      setPages(result.pages);
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "请求失败";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [fetchFn, size]);

  useEffect(() => {
    fetchData(page);
  }, [page, fetchData]);

  function goPage(n: number) {
    setPage(n);
  }

  function refresh() {
    fetchData(page);
  }

  return { items, total, page, size, pages, loading, error, goPage, refresh };
}
