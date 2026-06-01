# 前端架构

## 技术栈

- React 19 + TypeScript 6 + Vite 8
- react-router-dom v7（`createBrowserRouter` + `RouterProvider`）
- Tailwind CSS v4（通过 `@tailwindcss/vite` 插件）
- 无额外状态管理库，纯 React hooks + Context
- 自建 HTTP 客户端（拦截器管道模式）

## 目录结构

```
frontend/src/
├── main.tsx              # 入口：StrictMode + AuthProvider + App
├── App.tsx               # RouterProvider 渲染
├── index.css             # Tailwind + 自定义样式（玻璃态、侧栏、动画）
├── routes/               # 路由配置
│   ├── index.tsx         # createBrowserRouter 路由表
│   ├── ProtectedRoute.tsx  # 认证守卫
│   └── GuestRoute.tsx      # 访客守卫
├── layouts/              # 布局组件
│   ├── AuthLayout.tsx    # 居中卡片（login/register 共用）
│   └── AppLayout.tsx     # 最小外层壳（已认证页面）
├── pages/                # 页面组件
│   ├── auth/
│   │   ├── LoginPage.tsx    # 登录
│   │   └── RegisterPage.tsx # 注册
│   ├── chat/
│   │   └── ChatPage.tsx     # 聊天主页
│   └── NotFound.tsx         # 404
├── components/           # 可复用 UI 组件
│   ├── SessionSidebar.tsx   # 侧栏（会话列表 + 用户信息）
│   ├── SearchForm.tsx       # 搜索输入框
│   ├── MessageList.tsx      # 消息列表
│   ├── MarkdownRenderer.tsx # Markdown 渲染
│   ├── ResultCard.tsx       # 最终结果卡片
│   ├── StateCard.tsx        # 节点状态卡片
│   ├── Header.tsx
│   └── WorkflowStepper.tsx
├── hooks/
│   ├── useAuth.tsx       # 认证上下文
│   └── useAgentChat.ts   # 聊天状态管理
├── api/
│   ├── client/           # HTTP 客户端基础设施
│   │   ├── index.ts         # 单例创建 + 拦截器注册
│   │   ├── httpClient.ts    # HttpClient 类
│   │   ├── tokenStorage.ts  # Token 存储抽象
│   │   └── authInterceptors.ts  # 认证拦截器
│   ├── authApi.ts        # 认证 API
│   └── agentApi.ts       # 聊天/Agent API
└── types/
    ├── auth.ts           # 认证类型
    └── agent.ts          # Agent/聊天类型
```

## 路由表

| 路径 | 守卫 | 布局 | 页面 |
|------|------|------|------|
| `/login` | GuestRoute | AuthLayout | LoginPage |
| `/register` | GuestRoute | AuthLayout | RegisterPage |
| `/` | ProtectedRoute | AppLayout | ChatPage |
| `*` | 无 | 无 | NotFound |

- **GuestRoute**：已登录 → 重定向 `/`
- **ProtectedRoute**：未登录 → 重定向 `/login`，loading 时显示加载中

## 数据流

```
main.tsx (AuthProvider)
  └── App.tsx (RouterProvider)
        ├── GuestRoute → AuthLayout → LoginPage / RegisterPage
        │                    └── useAuth() → authApi → httpClient.raw()
        ├── ProtectedRoute → AppLayout → ChatPage
        │                              ├── useAgentChat() → agentApi → httpClient.stream()
        │                              └── useAuth() → authApi → httpClient
        └── NotFound
```

## 核心 Hooks

### useAgentChat

聊天状态管理核心，管理消息、会话列表、SSE 流式处理。

状态：
- `messages: ChatMessage[]` — 对话消息
- `currentState: AgentState | null` — 累积的 Agent 状态
- `loading: boolean` — 是否有请求进行中
- `sessions: ChatSession[]` — 侧栏会话列表
- `activeThreadId: string | null` — 当前会话 ID
- `sidebarCollapsed: boolean` — 侧栏折叠状态
- `activeNode: string` — 当前执行的 Agent 节点

方法：`submit()`, `stop()`, `loadSession()`, `startNewSession()`, `deleteSession()`, `toggleSidebar()`

SSE 事件处理：
1. `stream_chunk` → 追加到最后一条消息（实时流式）
2. `node_update`（research）→ 累积状态 + 添加步骤摘要消息
3. `stopped` / `error` → 结束 loading

### useAuth

见 [认证系统](./auth.md) 前端部分。

## 组件 Props

### SessionSidebar

```typescript
{ sessions, activeThreadId, onSelect, onNew, onDelete,
  collapsed, onToggle, userEmail?, onLogout }
```

### SearchForm

```typescript
{ onSubmit: (query: string) => void, onStop: () => void, loading: boolean }
```

### MessageList

```typescript
{ messages: ChatMessage[], loading: boolean,
  currentState: AgentState | null, activeNode: string }
```

渲染逻辑：Human → 右对齐气泡；AI finalize → ResultCard；AI 有 nodeName → StepCard；AI 无 nodeName → MarkdownRenderer。

## 构建命令

- `npm run dev` — 开发服务器
- `npm run build` — `tsc -b && vite build`
- `npm run lint` — ESLint
