import { httpClient, tokenStorage } from "./client";
import type {
  AuthResponse,
  AuthUser,
  LoginRequest,
  RegisterRequest,
  ApiResult,
} from "../types/auth";

export { tokenStorage };

/**
 * 处理绕过拦截器的原始响应（login/register），解析 Result 包装
 */
async function handleRawResult<T>(res: Response): Promise<T> {
  const body = await res.json();
  if (body && typeof body === "object" && "success" in body) {
    if (!body.success) {
      throw new Error(body.message || `请求失败: ${body.code}`);
    }
    return body.result as T;
  }
  return body as T;
}

export const authApi = {
  /**
   * 登录，支持邮箱或用户名
   */
  async login(data: LoginRequest): Promise<AuthResponse> {
    const res = await httpClient.raw("/api/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    const result = await handleRawResult<AuthResponse>(res);
    tokenStorage.setAccessToken(result.access_token);
    tokenStorage.setRefreshToken(result.refresh_token);
    return result;
  },

  /**
   * 注册新用户
   */
  async register(data: RegisterRequest): Promise<AuthResponse> {
    const res = await httpClient.raw("/api/v1/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    const result = await handleRawResult<AuthResponse>(res);
    tokenStorage.setAccessToken(result.access_token);
    tokenStorage.setRefreshToken(result.refresh_token);
    return result;
  },

  /**
   * 刷新 token 对
   */
  async refresh(): Promise<boolean> {
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
  },

  /**
   * 登出并吊销 refresh token
   */
  async logout(): Promise<void> {
    const refreshToken = tokenStorage.getRefreshToken();
    if (refreshToken) {
      try {
        await httpClient.post<ApiResult>("/api/v1/auth/logout", {
          refresh_token: refreshToken,
        });
      } catch {}
    }
    tokenStorage.clear();
  },

  /**
   * 获取当前用户信息
   */
  async getMe(): Promise<AuthUser> {
    const { data } = await httpClient.get<AuthUser>("/api/v1/auth/me");
    return data;
  },
};
