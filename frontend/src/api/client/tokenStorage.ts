export interface TokenStorage {
  getAccessToken(): string | null;
  setAccessToken(token: string | null): void;
  getRefreshToken(): string | null;
  setRefreshToken(token: string | null): void;
  clear(): void;
  hasToken(): boolean;
}

const ACCESS_KEY = "access_token";
const REFRESH_KEY = "refresh_token";

/**
 * 基于 localStorage 的 token 存储，access_token 使用内存缓存减少 I/O
 */
export class LocalStorageTokenStorage implements TokenStorage {
  private _accessToken: string | null = localStorage.getItem(ACCESS_KEY);

  getAccessToken(): string | null {
    return this._accessToken;
  }

  setAccessToken(token: string | null): void {
    this._accessToken = token;
    if (token) localStorage.setItem(ACCESS_KEY, token);
    else localStorage.removeItem(ACCESS_KEY);
  }

  getRefreshToken(): string | null {
    return localStorage.getItem(REFRESH_KEY);
  }

  setRefreshToken(token: string | null): void {
    if (token) localStorage.setItem(REFRESH_KEY, token);
    else localStorage.removeItem(REFRESH_KEY);
  }

  clear(): void {
    this.setAccessToken(null);
    this.setRefreshToken(null);
  }

  hasToken(): boolean {
    return this._accessToken !== null;
  }
}

/**
 * 纯内存 token 存储，用于测试场景
 */
export class MemoryTokenStorage implements TokenStorage {
  private _accessToken: string | null = null;
  private _refreshToken: string | null = null;

  getAccessToken(): string | null {
    return this._accessToken;
  }

  setAccessToken(token: string | null): void {
    this._accessToken = token;
  }

  getRefreshToken(): string | null {
    return this._refreshToken;
  }

  setRefreshToken(token: string | null): void {
    this._refreshToken = token;
  }

  clear(): void {
    this._accessToken = null;
    this._refreshToken = null;
  }

  hasToken(): boolean {
    return this._accessToken !== null;
  }
}
