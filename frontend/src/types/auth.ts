export interface AuthUser {
  id: string;
  email: string;
  user_name: string;
  is_active: boolean;
  is_verified: boolean;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface LoginRequest {
  login: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  user_name: string;
  password: string;
}

export interface AuthResponse extends AuthTokens {
  user: AuthUser;
}

export interface RefreshResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface ApiResult<T = unknown> {
  code: number;
  success: boolean;
  result: T;
  message: string | null;
}
