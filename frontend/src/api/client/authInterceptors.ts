import type { TokenStorage } from "./tokenStorage";
import type { RequestInterceptor, ResponseInterceptor } from "./httpClient";
import { httpClient } from ".";

/**
 * 创建认证拦截器：请求拦截器注入 Bearer token，响应拦截器处理 401 自动刷新
 * @param tokenStorage - token 存储实例
 */
export function createAuthInterceptors(tokenStorage: TokenStorage): {
  requestInterceptor: RequestInterceptor;
  responseInterceptor: ResponseInterceptor;
} {
  let refreshPromise: Promise<boolean> | null = null;

  /**
   * 使用 refresh token 获取新的 token 对
   */
  async function refreshTokens(): Promise<boolean> {
    const refreshToken = tokenStorage.getRefreshToken();
    if (!refreshToken) return false;
    try {
      const res = await httpClient.raw("/api/v1/auth/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!res.ok) {
        tokenStorage.clear();
        return false;
      }
      const body = await res.json();
      const data = body.result ?? body;
      if (!data.access_token) {
        tokenStorage.clear();
        return false;
      }
      tokenStorage.setAccessToken(data.access_token);
      tokenStorage.setRefreshToken(data.refresh_token);
      return true;
    } catch {
      tokenStorage.clear();
      return false;
    }
  }

  /**
   * 防并发：多个请求同时 401 时共享同一个刷新 Promise
   */
  async function ensureRefreshed(): Promise<boolean> {
    if (refreshPromise) return refreshPromise;
    refreshPromise = refreshTokens().finally(() => {
      refreshPromise = null;
    });
    return refreshPromise;
  }

  const requestInterceptor: RequestInterceptor = (url, init) => {
    const token = tokenStorage.getAccessToken();
    if (!token) return { url, init };
    const headers =
      init.headers instanceof Headers
        ? init.headers
        : new Headers(init.headers as Record<string, string>);
    headers.set("Authorization", `Bearer ${token}`);
    return { url, init: { ...init, headers } };
  };

  const responseInterceptor: ResponseInterceptor = async (
    response,
    url,
    init,
    retry,
  ) => {
    if (response.status !== 401) return response;
    if (!tokenStorage.hasToken()) return response;

    const refreshed = await ensureRefreshed();
    if (!refreshed) return response;

    const newToken = tokenStorage.getAccessToken();
    const headers =
      init.headers instanceof Headers
        ? init.headers
        : new Headers(init.headers as Record<string, string>);
    if (newToken) headers.set("Authorization", `Bearer ${newToken}`);

    return retry(url, { ...init, headers });
  };

  return { requestInterceptor, responseInterceptor };
}
