# 前端路由化改造设计

## 目标

将前端从组件条件切换改为基于 react-router-dom v7 的路由导航，同时重构目录结构以支持未来页面扩展（设置页、公开页面等）。

## 技术选型

- **react-router-dom v7** — `createBrowserRouter` + `RouterProvider` 模式
- 不选 TanStack Router：当前项目规模不需要其类型安全路由的额外复杂度

## 目录结构

```
frontend/src/
  api/                    # 不变
    client/
    agentApi.ts
    authApi.ts
  components/             # 可复用 UI 组件，保留不变
    Header.tsx
    MarkdownRenderer.tsx
    MessageList.tsx
    ResultCard.tsx
    SearchForm.tsx
    SessionSidebar.tsx
    StateCard.tsx
    WorkflowStepper.tsx
  hooks/                  # 不变
    useAgentChat.ts
    useAuth.tsx
  types/                  # 不变
    agent.ts
    auth.ts
  pages/                  # 【新增】路由级页面组件
    auth/
      LoginPage.tsx         # 从 components/LoginPage.tsx 迁移
      RegisterPage.tsx      # 从 components/RegisterPage.tsx 迁移
    chat/
      ChatPage.tsx          # 从 App.tsx 中的 ChatApp 提取
    NotFound.tsx            # 404 页面
  layouts/                # 【新增】布局组件
    AuthLayout.tsx          # 居中卡片布局，login/register 共用
    AppLayout.tsx           # 侧栏+主区域布局，chat/设置页等共用
  routes/                 # 【新增】路由配置
    index.tsx               # createBrowserRouter 路由表
    ProtectedRoute.tsx      # 认证守卫：未登录重定向 /login
    GuestRoute.tsx          # 访客守卫：已登录重定向 /
  App.tsx                  # 精简为 RouterProvider 渲染
  main.tsx                 # 不变：AuthProvider 包裹
  index.css                # 不变
```

## 路由表

| 路径 | 守卫 | 页面 | 布局 |
|------|------|------|------|
| `/login` | GuestRoute | LoginPage | AuthLayout |
| `/register` | GuestRoute | RegisterPage | AuthLayout |
| `/` | ProtectedRoute | ChatPage | AppLayout |
| `*` | 无 | NotFound | AuthLayout |

## 组件设计

### 路由配置 `routes/index.tsx`

使用 `createBrowserRouter` 定义嵌套路由树：

```
Router
├── GuestRoute (path="/")
│   ├── LoginPage (path="login")
│   └── RegisterPage (path="register")
├── ProtectedRoute (path="/")
│   └── AppLayout
│       ├── ChatPage (index)
│       └── (未来: SettingsPage, ProfilePage)
└── NotFound (path="*")
```

### ProtectedRoute

- 读取 `useAuth()` 的 `user` 和 `loading` 状态
- `loading` 时显示全屏 loading
- `user` 为 null 时 `<Navigate to="/login" replace />`
- 否则 `<Outlet />`

### GuestRoute

- 反向守卫：已登录用户访问 `/login` 或 `/register` 时重定向到 `/`
- 未登录时 `<Outlet />`

### AuthLayout

- 居中全屏布局，包含 `<Outlet />`
- login 和 register 页面共用

### AppLayout

- 侧栏 + 主区域布局，包含 `<Outlet />`
- 从 `App.tsx` 中的 `ChatApp` 提取骨架部分（SessionSidebar + flex 容器）
- 各页面组件通过 `<Outlet />` 渲染

### ChatPage

- 从 `App.tsx` 中的 `ChatApp` 函数体提取
- 使用 `useAgentChat()` 和 `useAuth()`
- 只负责消息列表和搜索表单的区域

### LoginPage / RegisterPage

- 从 `components/` 迁移到 `pages/auth/`
- 移除 `onSwitchToRegister` / `onSwitchToLogin` 回调 props
- 改用 `useNavigate()` + `<Link>` 进行页面跳转

### NotFound

- 简单的 404 提示页，带返回首页链接

## App.tsx 改造

从 ~73 行精简为 ~10 行：

```tsx
import { RouterProvider } from "react-router-dom";
import { router } from "./routes";

export default function App() {
  return <RouterProvider router={router} />;
}
```

`main.tsx` 不变，`AuthProvider` 仍在最外层包裹。

## 文件迁移清单

| 操作 | 源 | 目标 |
|------|------|------|
| 迁移 | `components/LoginPage.tsx` | `pages/auth/LoginPage.tsx` |
| 迁移 | `components/RegisterPage.tsx` | `pages/auth/RegisterPage.tsx` |
| 提取 | `App.tsx` 中 `ChatApp` | `pages/chat/ChatPage.tsx` |
| 新建 | — | `layouts/AuthLayout.tsx` |
| 新建 | — | `layouts/AppLayout.tsx` |
| 新建 | — | `routes/index.tsx` |
| 新建 | — | `routes/ProtectedRoute.tsx` |
| 新建 | — | `routes/GuestRoute.tsx` |
| 新建 | — | `pages/NotFound.tsx` |
| 重写 | `App.tsx` | 精简为 RouterProvider |

## 依赖变更

新增 `react-router-dom`（v7）。

## 验证标准

1. `npm run build` 通过（tsc + vite）
2. 所有页面路径可正常访问
3. 未登录访问 `/` 自动跳转 `/login`
4. 已登录访问 `/login` 自动跳转 `/`
5. 登录/注册成功后跳转到 `/`
6. 登出后跳转到 `/login`
