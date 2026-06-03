# 前端架构

## 技术栈

- React 19 + TypeScript 6 + Vite 8
- react-router-dom v7（`createBrowserRouter` + `RouterProvider`）
- Tailwind CSS v4（通过 `@tailwindcss/vite` 插件）
- @headlessui/react ^2.2.10（无障碍 UI 组件）
- lucide-react（图标库）
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
│   │   └── ChatPage.tsx     # 聊天主页（管理附件状态）
│   ├── knowledge/
│   │   ├── KnowledgePage.tsx    # 知识库管理页（搜索、卡片网格、分页）
│   │   └── AddKnowledgeModal.tsx # 添加知识模态框（手动/上传）
│   └── NotFound.tsx         # 404
├── components/           # 可复用 UI 组件
│   ├── SessionSidebar.tsx   # 侧栏（会话列表 + 知识库导航 + 用户信息）
│   ├── SearchForm.tsx       # 搜索输入框（支持文件附件上传）
│   ├── MessageList.tsx      # 消息列表
│   ├── MarkdownRenderer.tsx # Markdown 渲染
│   ├── ResultCard.tsx       # 最终结果卡片（含"存入知识库"按钮）
│   ├── StateCard.tsx        # 节点状态卡片
│   ├── Modal.tsx            # 通用模态框（Headless UI Dialog + Transition）
│   ├── FileUploader.tsx     # 文件上传组件（拖拽 + 点击 + 进度指示）
│   ├── Pagination.tsx       # 分页导航（智能省略号）
│   ├── Header.tsx
│   └── WorkflowStepper.tsx
├── hooks/
│   ├── useAuth.tsx       # 认证上下文
│   ├── useAgentChat.ts   # 聊天状态管理（submit 支持 fileIds）
│   └── usePagination.ts  # 通用分页状态管理 Hook
├── api/
│   ├── client/           # HTTP 客户端基础设施
│   │   ├── index.ts         # 单例创建 + 拦截器注册
│   │   ├── httpClient.ts    # HttpClient 类
│   │   ├── tokenStorage.ts  # Token 存储抽象
│   │   └── authInterceptors.ts  # 认证拦截器
│   ├── passwordCrypto.ts  # RSA 密码加密（Web Crypto API，零依赖）
│   ├── authApi.ts        # 认证 API
│   ├── agentApi.ts       # 聊天/Agent API
│   ├── uploadApi.ts      # 文件上传 API（使用 raw + 手动 token 注入）
│   └── knowledgeApi.ts   # 知识库 CRUD + 搜索 API
└── types/
    ├── auth.ts           # 认证类型
    ├── agent.ts          # Agent/聊天类型（SubmitRequest 含 file_ids）
    └── knowledge.ts      # 知识库类型（FileUpload, KnowledgeEntry, PaginatedResult 等）
```

## 路由表

| 路径 | 守卫 | 布局 | 页面 |
|------|------|------|------|
| `/login` | GuestRoute | AuthLayout | LoginPage |
| `/register` | GuestRoute | AuthLayout | RegisterPage |
| `/` | ProtectedRoute | AppLayout | ChatPage |
| `/knowledge` | ProtectedRoute | AppLayout | KnowledgePage |
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
        ├── ProtectedRoute → AppLayout → KnowledgePage
        │                              └── usePagination() → knowledgeApi → httpClient
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

方法：`submit(query, fileIds?)`, `stop()`, `loadSession()`, `startNewSession()`, `deleteSession()`, `toggleSidebar()`

**submit 签名**：`async (query: string, fileIds?: string[]) => void` — 支持传递附件 ID

SSE 事件处理：
1. `stream_chunk` → 追加到最后一条消息（实时流式）
2. `node_update`（research）→ 累积状态 + 添加步骤摘要消息
3. `stopped` / `error` → 结束 loading

### usePagination

通用分页状态管理 Hook。

```typescript
function usePagination<T>(options: {
  initialPage?: number;    // 默认 1
  initialSize?: number;    // 默认 20
  fetchFn: (page: number, size: number) => Promise<PaginatedResult<T>>;
}): {
  items, total, page, size, pages, loading, error,
  goPage: (n: number) => void,
  refresh: () => void,
}
```

### useAuth

见 [认证系统](./auth.md) 前端部分。

## 组件 Props

### SessionSidebar

```typescript
{ sessions, activeThreadId, onSelect, onNew, onDelete,
  collapsed, onToggle, userEmail?, onLogout }
```

包含"知识库"导航按钮（`BookOpen` 图标），点击导航到 `/knowledge`，使用 `useLocation` 高亮当前路由。

### SearchForm

```typescript
{ onSubmit: (query: string) => void, onStop: () => void, loading: boolean,
  attachments?: FileUpload[], onAddAttachment?: (file) => void,
  onRemoveAttachment?: (fileId: string) => void }
```

支持文件附件上传：回形针按钮 → 隐藏 file input → `uploadApi.uploadFile()` → 附件 pills 显示。

### MessageList

```typescript
{ messages: ChatMessage[], loading: boolean,
  currentState: AgentState | null, activeNode: string }
```

渲染逻辑：Human → 右对齐气泡；AI finalize → ResultCard；AI 有 nodeName → StepCard；AI 无 nodeName → MarkdownRenderer。

### Modal

```typescript
{ open: boolean, onClose: () => void, title: string,
  children: React.ReactNode, size?: "sm" | "md" | "lg" }
```

基于 @headlessui/react 的 Dialog + Transition，玻璃态风格。

### FileUploader

```typescript
{ onUploadComplete: (file: FileUpload) => void,
  onRemove: (fileId: string) => void,
  files: FileUpload[], accept?: string }
```

拖拽/点击上传，上传 spinner，文件 pills 列表，3 秒错误自动消失。

### Pagination

```typescript
{ page: number, pages: number, onChange: (page: number) => void }
```

智能省略号逻辑（>7 页时折叠），`pages <= 1` 时返回 null。

### ResultCard

```typescript
{ state: AgentState }
```

展示最终研究结果，底部含"存入知识库"按钮（`BookmarkPlus` 图标），点击调用 `knowledgeApi.createEntry()`，保存后显示"已保存"。

## 知识库类型（`types/knowledge.ts`）

| 类型 | 说明 |
|------|------|
| `FileUpload` | 文件上传记录（id, file_name, file_format, file_size, create_at） |
| `KnowledgeEntry` | 知识条目（id, user_id, title, source_type, source_id, chunk_count, content_preview, create_at） |
| `CreateEntryRequest` | 创建请求（title, content?, file_id?, source_type?, source_id?） |
| `SearchRequest` | 检索请求（query, top_k?） |
| `SearchHit` | 检索结果（entry_id, chunk_index, text, score） |
| `PaginatedResult<T>` | 分页结果（items, total, page, size, pages） |

## API 客户端

### uploadApi

| 方法 | HTTP | 说明 |
|------|------|------|
| `uploadFile(file)` | POST /upload/file | FormData，用 `httpClient.raw()` + 手动 token |
| `getFiles()` | GET /upload/files | 文件列表 |
| `getFileContent(id)` | GET /upload/files/{id}/content | 文件文本内容 |
| `deleteFile(id)` | DELETE /upload/files/{id} | 删除文件 |

**注意：** 文件上传必须用 `httpClient.raw()` 因为 `request()` 会强制设 Content-Type 为 JSON。

### knowledgeApi

| 方法 | HTTP | 说明 |
|------|------|------|
| `createEntry(body)` | POST /knowledge/entries | 创建知识条目 |
| `listEntries(page, size)` | GET /knowledge/entries | 分页列表 |
| `getEntry(id)` | GET /knowledge/entries/{id} | 条目详情 |
| `deleteEntry(id)` | DELETE /knowledge/entries/{id} | 删除条目 |
| `search(body)` | POST /knowledge/search | 检索知识库 |

所有方法使用标准 `httpClient.get/post/delete`（自动解包 Result）。

## 构建命令

- `npm run dev` — 开发服务器
- `npm run build` — `tsc -b && vite build`
- `npm run lint` — ESLint
