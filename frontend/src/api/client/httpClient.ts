const BASE_URL = "http://localhost:4030";

export interface ApiResponse<T = unknown> {
  ok: boolean;
  data: T;
  status: number;
}

export class HttpException extends Error {
  readonly status: number;
  readonly detail: string;
  constructor(status: number, detail: string) {
    super(detail);
    this.name = "HttpException";
    this.status = status;
    this.detail = detail;
  }
}

export type RequestInterceptor = (
  url: string,
  init: RequestInit,
) => Promise<{ url: string; init: RequestInit }> | { url: string; init: RequestInit };

export type ResponseInterceptor = (
  response: Response,
  url: string,
  init: RequestInit,
  retry: (url: string, init: RequestInit) => Promise<Response>,
) => Promise<Response>;

/**
 * HTTP 客户端，支持可插拔拦截器管道
 * - request<T>(): 标准 JSON 请求，自动解析响应
 * - stream(): 返回原始 Response，用于 SSE 流式场景，经过拦截器管道
 * - raw(): 绕过所有拦截器，用于 refresh 等底层调用
 */
export class HttpClient {
  private readonly _requestInterceptors: RequestInterceptor[] = [];
  private readonly _responseInterceptors: ResponseInterceptor[] = [];

  /**
   * 注册请求拦截器，返回注销函数
   */
  useRequestInterceptor(interceptor: RequestInterceptor): () => void {
    this._requestInterceptors.push(interceptor);
    return () => {
      const idx = this._requestInterceptors.indexOf(interceptor);
      if (idx >= 0) this._requestInterceptors.splice(idx, 1);
    };
  }

  /**
   * 注册响应拦截器，返回注销函数
   */
  useResponseInterceptor(interceptor: ResponseInterceptor): () => void {
    this._responseInterceptors.push(interceptor);
    return () => {
      const idx = this._responseInterceptors.indexOf(interceptor);
      if (idx >= 0) this._responseInterceptors.splice(idx, 1);
    };
  }

  private resolveUrl(path: string): string {
    if (path.startsWith("http")) return path;
    return `${BASE_URL}${path}`;
  }

  private async applyRequestInterceptors(
    url: string,
    init: RequestInit,
  ): Promise<{ url: string; init: RequestInit }> {
    let result = { url, init };
    for (const interceptor of this._requestInterceptors) {
      result = await interceptor(result.url, result.init);
    }
    return result;
  }

  private async applyResponseInterceptors(
    response: Response,
    url: string,
    init: RequestInit,
  ): Promise<Response> {
    const retry = (retryUrl: string, retryInit: RequestInit) =>
      this.fetchWithInterceptors(retryUrl, retryInit);

    let result = response;
    for (const interceptor of this._responseInterceptors) {
      result = await interceptor(result, url, init, retry);
    }
    return result;
  }

  private async fetchWithInterceptors(
    url: string,
    init: RequestInit,
  ): Promise<Response> {
    const resolved = await this.applyRequestInterceptors(
      this.resolveUrl(url),
      init,
    );
    const response = await fetch(resolved.url, resolved.init);
    return this.applyResponseInterceptors(response, url, init);
  }

  private ensureJsonHeader(init: RequestInit): RequestInit {
    const headers =
      init.headers instanceof Headers
        ? init.headers
        : new Headers(init.headers as Record<string, string>);
    if (!headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
    return { ...init, headers };
  }

  /**
   * 标准 JSON 请求，自动解析 Result 包装
   */
  async request<T = unknown>(url: string, init: RequestInit = {}): Promise<ApiResponse<T>> {
    const response = await this.fetchWithInterceptors(url, this.ensureJsonHeader(init));
    if (!response.ok) {
      let detail = `请求失败: ${response.status}`;
      try {
        const body = await response.json();
        detail = body.message || body.detail || detail;
      } catch {}
      throw new HttpException(response.status, detail);
    }
    const body = await response.json();
    if (body && typeof body === "object" && "success" in body) {
      if (!body.success) {
        throw new HttpException(body.code || response.status, body.message || "请求失败");
      }
      return { ok: true, data: body.result as T, status: response.status };
    }
    return { ok: true, data: body as T, status: response.status };
  }

  async get<T = unknown>(url: string): Promise<ApiResponse<T>> {
    return this.request<T>(url, { method: "GET" });
  }

  async post<T = unknown>(url: string, body?: unknown): Promise<ApiResponse<T>> {
    return this.request<T>(url, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  async delete<T = unknown>(url: string): Promise<ApiResponse<T>> {
    return this.request<T>(url, { method: "DELETE" });
  }

  /**
   * SSE 流式请求，返回原始 Response，仍经过拦截器管道
   */
  async stream(url: string, body?: unknown, init: RequestInit = {}): Promise<Response> {
    return this.fetchWithInterceptors(
      url,
      this.ensureJsonHeader({
        ...init,
        method: "POST",
        body: body ? JSON.stringify(body) : undefined,
      }),
    );
  }

  /**
   * 文件上传，经过拦截器管道但不强制 Content-Type（浏览器自动设置 multipart/form-data boundary）
   */
  async upload(url: string, formData: FormData, init: RequestInit = {}): Promise<Response> {
    return this.fetchWithInterceptors(url, {
      ...init,
      method: "POST",
      body: formData,
    });
  }

  /**
   * 完全绕过拦截器，用于 refresh/login/register 等底层调用
   */
  raw(url: string, init: RequestInit = {}): Promise<Response> {
    return fetch(this.resolveUrl(url), init);
  }
}
