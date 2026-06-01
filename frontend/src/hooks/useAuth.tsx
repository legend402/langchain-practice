import {
  useState,
  useCallback,
  useEffect,
  createContext,
  useContext,
  type ReactNode,
} from "react";
import type { AuthUser, LoginRequest, RegisterRequest } from "../types/auth";
import { authApi, tokenStorage } from "../api/authApi";

interface AuthState {
  user: AuthUser | null;
  loading: boolean;
  initialized: boolean;
}

interface AuthContextValue extends AuthState {
  login: (data: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

/**
 * 认证上下文提供者，管理用户状态和认证操作
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    loading: true,
    initialized: false,
  });

  useEffect(() => {
    if (!tokenStorage.hasToken()) {
      setState({ user: null, loading: false, initialized: true });
      return;
    }
    authApi
      .getMe()
      .then((user) => setState({ user, loading: false, initialized: true }))
      .catch(async () => {
        const refreshed = await authApi.refresh();
        if (refreshed) {
          const user = await authApi.getMe();
          setState({ user, loading: false, initialized: true });
        } else {
          setState({ user: null, loading: false, initialized: true });
        }
      });
  }, []);

  const loginFn = useCallback(async (data: LoginRequest) => {
    const result = await authApi.login(data);
    setState({ user: result.user, loading: false, initialized: true });
  }, []);

  const registerFn = useCallback(async (data: RegisterRequest) => {
    const result = await authApi.register(data);
    setState({ user: result.user, loading: false, initialized: true });
  }, []);

  const logoutFn = useCallback(async () => {
    await authApi.logout();
    setState({ user: null, loading: false, initialized: true });
  }, []);

  return (
    <AuthContext.Provider
      value={{ ...state, login: loginFn, register: registerFn, logout: logoutFn }}
    >
      {children}
    </AuthContext.Provider>
  );
}

/**
 * 获取认证上下文，必须在 AuthProvider 内使用
 */
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth 必须在 AuthProvider 内使用");
  return ctx;
}
