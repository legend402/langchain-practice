# 前端路由化改造实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将前端从组件条件切换改为 react-router-dom v7 路由导航，重构目录结构以支持未来页面扩展。

**Architecture:** react-router-dom v7 的 `createBrowserRouter` + `RouterProvider` 模式。三层路由守卫（ProtectedRoute / GuestRoute），布局组件（AuthLayout / AppLayout），页面组件按功能分目录（pages/auth/, pages/chat/）。

**Tech Stack:** React 19, react-router-dom v7, TypeScript 6, Vite 8, Tailwind CSS v4

---

## File Structure

| 操作 | 文件路径 | 职责 |
|------|----------|------|
| 新建 | `frontend/src/routes/GuestRoute.tsx` | 访客守卫：已登录重定向 / |
| 新建 | `frontend/src/routes/ProtectedRoute.tsx` | 认证守卫：未登录重定向 /login |
| 新建 | `frontend/src/layouts/AuthLayout.tsx` | 居中卡片布局，login/register 共用 |
| 新建 | `frontend/src/layouts/AppLayout.tsx` | 最小外层壳，已认证页面共用 |
| 新建 | `frontend/src/pages/NotFound.tsx` | 404 页面 |
| 新建 | `frontend/src/pages/chat/ChatPage.tsx` | 从 App.tsx ChatApp 提取 |
| 新建 | `frontend/src/pages/auth/LoginPage.tsx` | 从 components/LoginPage.tsx 迁移 |
| 新建 | `frontend/src/pages/auth/RegisterPage.tsx` | 从 components/RegisterPage.tsx 迁移 |
| 新建 | `frontend/src/routes/index.tsx` | 路由表定义 |
| 重写 | `frontend/src/App.tsx` | 精简为 RouterProvider |
| 修改 | `frontend/src/hooks/useAuth.tsx` | logout 不再需要导航逻辑 |
| 删除 | `frontend/src/components/LoginPage.tsx` | 已迁移到 pages/auth/ |
| 删除 | `frontend/src/components/RegisterPage.tsx` | 已迁移到 pages/auth/ |

---

### Task 1: 安装 react-router-dom

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: 安装依赖**

Run: `cd frontend && npm install react-router-dom`

- [ ] **Step 2: 验证安装**

Run: `cd frontend && npm ls react-router-dom`
Expected: 显示 `react-router-dom@7.x.x`

---

### Task 2: 创建路由守卫

**Files:**
- Create: `frontend/src/routes/GuestRoute.tsx`
- Create: `frontend/src/routes/ProtectedRoute.tsx`

- [ ] **Step 1: 创建 routes 目录**

Run: `mkdir -p frontend/src/routes`

- [ ] **Step 2: 创建 GuestRoute**

```tsx
// frontend/src/routes/GuestRoute.tsx
import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

/**
 * 访客路由守卫：已登录用户重定向到首页，未登录用户正常渲染子路由
 */
export default function GuestRoute() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-background">
        <div className="text-ink-400 text-sm">加载中...</div>
      </div>
    );
  }

  if (user) {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}
```

- [ ] **Step 3: 创建 ProtectedRoute**

```tsx
// frontend/src/routes/ProtectedRoute.tsx
import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

/**
 * 认证路由守卫：未登录用户重定向到登录页，已登录用户正常渲染子路由
 */
export default function ProtectedRoute() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-background">
        <div className="text-ink-400 text-sm">加载中...</div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
```

---

### Task 3: 创建布局组件

**Files:**
- Create: `frontend/src/layouts/AuthLayout.tsx`
- Create: `frontend/src/layouts/AppLayout.tsx`

- [ ] **Step 1: 创建 layouts 目录**

Run: `mkdir -p frontend/src/layouts`

- [ ] **Step 2: 创建 AuthLayout**

```tsx
// frontend/src/layouts/AuthLayout.tsx
import { Outlet } from "react-router-dom";

/**
 * 认证页面布局：居中全屏布局，供登录和注册页面共用
 */
export default function AuthLayout() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <Outlet />
    </div>
  );
}
```

- [ ] **Step 3: 创建 AppLayout**

```tsx
// frontend/src/layouts/AppLayout.tsx
import { Outlet } from "react-router-dom";

/**
 * 应用主布局：已认证页面的外层壳，未来可扩展侧栏等共享元素
 */
export default function AppLayout() {
  return (
    <div className="h-screen bg-background">
      <Outlet />
    </div>
  );
}
```

---

### Task 4: 创建 NotFound 页面

**Files:**
- Create: `frontend/src/pages/NotFound.tsx`

- [ ] **Step 1: 创建 pages 目录**

Run: `mkdir -p frontend/src/pages`

- [ ] **Step 2: 创建 NotFound 页面**

```tsx
// frontend/src/pages/NotFound.tsx
import { Link } from "react-router-dom";

/**
 * 404 页面：显示错误提示和返回首页链接
 */
export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-ink-400 mb-4">404</h1>
        <p className="text-ink-400 mb-6">页面不存在</p>
        <Link
          to="/"
          className="px-6 py-2.5 rounded-xl bg-accent text-white font-medium text-sm hover:bg-accent-light transition-colors"
        >
          返回首页
        </Link>
      </div>
    </div>
  );
}
```

---

### Task 5: 创建 ChatPage

**Files:**
- Create: `frontend/src/pages/chat/ChatPage.tsx`

- [ ] **Step 1: 创建 pages/chat 目录**

Run: `mkdir -p frontend/src/pages/chat`

- [ ] **Step 2: 创建 ChatPage**

从 `App.tsx` 中的 `ChatApp` 函数提取，不变量：使用 `useAgentChat()` 和 `useAuth()`。

```tsx
// frontend/src/pages/chat/ChatPage.tsx
import { useAuth } from "../../hooks/useAuth";
import { useAgentChat } from "../../hooks/useAgentChat";

import SearchForm from "../../components/SearchForm";
import MessageList from "../../components/MessageList";
import SessionSidebar from "../../components/SessionSidebar";

/**
 * 聊天主页面：包含侧栏、消息列表和搜索表单
 */
export default function ChatPage() {
  const chat = useAgentChat();
  const auth = useAuth();

  return (
    <div className="h-screen flex">
      <SessionSidebar
        sessions={chat.sessions}
        activeThreadId={chat.activeThreadId}
        onSelect={chat.loadSession}
        onNew={chat.startNewSession}
        onDelete={chat.deleteSession}
        collapsed={chat.sidebarCollapsed}
        onToggle={chat.toggleSidebar}
        userEmail={auth.user?.email}
        onLogout={auth.logout}
      />

      <div
        className={`flex-1 flex flex-col min-w-0 h-screen main-area ${
          chat.sidebarCollapsed ? "sidebar-collapsed" : "sidebar-expanded"
        }`}
      >
        <main
          className="flex-1 flex flex-col max-w-3xl w-full mx-auto px-4 overflow-hidden"
          style={{ height: "calc(100vh)" }}
        >
          <MessageList
            messages={chat.messages}
            loading={chat.loading}
            currentState={chat.currentState}
            activeNode={chat.activeNode}
          />
          <div className="shrink-0 pb-4 pt-0 space-y-3">
            <SearchForm onSubmit={chat.submit} onStop={chat.stop} loading={chat.loading} />
          </div>
        </main>
      </div>
    </div>
  );
}
```

---

### Task 6: 迁移 LoginPage

**Files:**
- Create: `frontend/src/pages/auth/LoginPage.tsx`

- [ ] **Step 1: 创建 pages/auth 目录**

Run: `mkdir -p frontend/src/pages/auth`

- [ ] **Step 2: 创建 LoginPage**

从 `components/LoginPage.tsx` 迁移，移除 `onSwitchToRegister` prop，改用 `useNavigate()` 和 `Link`。

```tsx
// frontend/src/pages/auth/LoginPage.tsx
import { useState, type FormEvent } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";

/**
 * 登录页面：提供邮箱/用户名和密码登录表单
 */
export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [loginField, setLoginField] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await login({ login: loginField, password });
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "登录失败");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="glass-card w-full max-w-md p-8">
      <h1 className="text-2xl font-semibold text-ink-100 mb-6 text-center">登录</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm text-ink-400 mb-1">邮箱 / 用户名</label>
          <input
            type="text"
            value={loginField}
            onChange={(e) => setLoginField(e.target.value)}
            className="w-full px-4 py-2.5 rounded-xl glass-input text-ink-100 outline-none focus:ring-2 focus:ring-accent/30 text-sm"
            placeholder="输入邮箱或用户名"
            required
          />
        </div>
        <div>
          <label className="block text-sm text-ink-400 mb-1">密码</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-4 py-2.5 rounded-xl glass-input text-ink-100 outline-none focus:ring-2 focus:ring-accent/30 text-sm"
            placeholder="输入密码"
            required
          />
        </div>
        {error && <p className="text-sm text-red-500 text-center">{error}</p>}
        <button
          type="submit"
          disabled={submitting}
          className="w-full py-2.5 rounded-xl bg-accent text-white font-medium text-sm hover:bg-accent-light transition-colors disabled:opacity-50 cursor-pointer"
        >
          {submitting ? "登录中..." : "登录"}
        </button>
      </form>
      <p className="text-sm text-ink-400 text-center mt-4">
        还没有账号？{" "}
        <Link to="/register" className="text-accent hover:underline">
          注册
        </Link>
      </p>
    </div>
  );
}
```

---

### Task 7: 迁移 RegisterPage

**Files:**
- Create: `frontend/src/pages/auth/RegisterPage.tsx`

- [ ] **Step 1: 创建 RegisterPage**

从 `components/RegisterPage.tsx` 迁移，移除 `onSwitchToLogin` prop，改用 `useNavigate()` 和 `Link`。

```tsx
// frontend/src/pages/auth/RegisterPage.tsx
import { useState, type FormEvent } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";

/**
 * 注册页面：提供邮箱、用户名、密码注册表单
 */
export default function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [userName, setUserName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (password !== confirmPassword) {
      setError("两次密码不一致");
      return;
    }
    if (password.length < 8) {
      setError("密码至少 8 位");
      return;
    }
    setSubmitting(true);
    try {
      await register({ email, user_name: userName, password });
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "注册失败");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="glass-card w-full max-w-md p-8">
      <h1 className="text-2xl font-semibold text-ink-100 mb-6 text-center">注册</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm text-ink-400 mb-1">邮箱</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full px-4 py-2.5 rounded-xl glass-input text-ink-100 outline-none focus:ring-2 focus:ring-accent/30 text-sm"
            placeholder="输入邮箱"
            required
          />
        </div>
        <div>
          <label className="block text-sm text-ink-400 mb-1">用户名</label>
          <input
            type="text"
            value={userName}
            onChange={(e) => setUserName(e.target.value)}
            className="w-full px-4 py-2.5 rounded-xl glass-input text-ink-100 outline-none focus:ring-2 focus:ring-accent/30 text-sm"
            placeholder="输入用户名"
            required
          />
        </div>
        <div>
          <label className="block text-sm text-ink-400 mb-1">密码</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-4 py-2.5 rounded-xl glass-input text-ink-100 outline-none focus:ring-2 focus:ring-accent/30 text-sm"
            placeholder="至少 8 位"
            required
          />
        </div>
        <div>
          <label className="block text-sm text-ink-400 mb-1">确认密码</label>
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className="w-full px-4 py-2.5 rounded-xl glass-input text-ink-100 outline-none focus:ring-2 focus:ring-accent/30 text-sm"
            placeholder="再次输入密码"
            required
          />
        </div>
        {error && <p className="text-sm text-red-500 text-center">{error}</p>}
        <button
          type="submit"
          disabled={submitting}
          className="w-full py-2.5 rounded-xl bg-accent text-white font-medium text-sm hover:bg-accent-light transition-colors disabled:opacity-50 cursor-pointer"
        >
          {submitting ? "注册中..." : "注册"}
        </button>
      </form>
      <p className="text-sm text-ink-400 text-center mt-4">
        已有账号？{" "}
        <Link to="/login" className="text-accent hover:underline">
          登录
        </Link>
      </p>
    </div>
  );
}
```

---

### Task 8: 创建路由表

**Files:**
- Create: `frontend/src/routes/index.tsx`

- [ ] **Step 1: 创建路由配置**

```tsx
// frontend/src/routes/index.tsx
import { createBrowserRouter } from "react-router-dom";
import GuestRoute from "./GuestRoute";
import ProtectedRoute from "./ProtectedRoute";
import AuthLayout from "../layouts/AuthLayout";
import AppLayout from "../layouts/AppLayout";
import LoginPage from "../pages/auth/LoginPage";
import RegisterPage from "../pages/auth/RegisterPage";
import ChatPage from "../pages/chat/ChatPage";
import NotFound from "../pages/NotFound";

/**
 * 应用路由表：定义所有路由、守卫和布局的嵌套关系
 */
export const router = createBrowserRouter([
  {
    element: <GuestRoute />,
    children: [
      {
        element: <AuthLayout />,
        children: [
          { path: "/login", element: <LoginPage /> },
          { path: "/register", element: <RegisterPage /> },
        ],
      },
    ],
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppLayout />,
        children: [{ path: "/", element: <ChatPage /> }],
      },
    ],
  },
  {
    path: "*",
    element: <NotFound />,
  },
]);
```

---

### Task 9: 重写 App.tsx

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: 替换 App.tsx 全部内容**

从 ~73 行精简为 ~10 行：

```tsx
// frontend/src/App.tsx
import { RouterProvider } from "react-router-dom";
import { router } from "./routes";

export default function App() {
  return <RouterProvider router={router} />;
}
```

---

### Task 10: 更新 useAuth 的 logout 逻辑

**Files:**
- Modify: `frontend/src/hooks/useAuth.tsx`

- [ ] **Step 1: 修改 logoutFn**

当前 `logoutFn` 只清除了状态，需要在 logout 后让 SessionSidebar 触发导航。由于 SessionSidebar 已经调用 `auth.logout()`，而 `ProtectedRoute` 会检测 `user` 为 null 并重定向到 `/login`，所以 `useAuth.tsx` 不需要修改导航逻辑。

`useAuth.tsx` 保持不变。`ProtectedRoute` 的守卫机制会自动处理：logout → user 变为 null → ProtectedRoute 渲染 `<Navigate to="/login" />`。

---

### Task 11: 删除旧的页面组件

**Files:**
- Delete: `frontend/src/components/LoginPage.tsx`
- Delete: `frontend/src/components/RegisterPage.tsx`

- [ ] **Step 1: 删除已迁移的文件**

Run: `rm frontend/src/components/LoginPage.tsx frontend/src/components/RegisterPage.tsx`

---

### Task 12: 验证构建

- [ ] **Step 1: 运行 TypeScript 类型检查**

Run: `cd frontend && npx tsc -b`
Expected: 无错误

- [ ] **Step 2: 运行完整构建**

Run: `cd frontend && npm run build`
Expected: 构建成功，无 TypeScript 错误

- [ ] **Step 3: 提交**

```bash
git add -A
git commit -m "重构：前端改为 react-router-dom 路由导航，重组目录结构"
```
