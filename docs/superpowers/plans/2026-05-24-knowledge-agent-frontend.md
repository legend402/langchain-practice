# 知识点总结 Agent 前端实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建 React 前端应用，提供聊天式界面与知识点总结 Agent 交互，含工作流可视化、人工反馈、结果展示。

**Architecture:** Vite + React 19 SPA，通过抽象 API 层与后端通信（内置 mock 模式开发调试）。核心状态由 `useAgentChat` hook 管理，驱动 WorkflowBar、MessageList、FeedbackPanel 等组件更新。

**Tech Stack:** React 19, TypeScript 5, Vite 6, Tailwind CSS 4 (Vite 插件模式), react-markdown, remark-gfm, react-syntax-highlighter

---

## 文件结构

```
frontend/
├── index.html                              # HTML 入口
├── package.json                            # 依赖管理
├── tsconfig.json                           # TypeScript 配置
├── vite.config.ts                          # Vite 配置 + Tailwind 插件
├── src/
│   ├── main.tsx                            # React 入口，挂载 App
│   ├── App.tsx                             # 根组件，布局容器
│   ├── index.css                           # Tailwind 入口样式
│   ├── types/
│   │   └── agent.ts                        # AgentState 等类型定义
│   ├── api/
│   │   └── agentApi.ts                     # 抽象 API 层 + mock 实现
│   ├── hooks/
│   │   └── useAgentChat.ts                 # 核心通信 hook
│   ├── components/
│   │   ├── Sidebar.tsx                     # 左侧会话列表
│   │   ├── ChatPanel.tsx                   # 主聊天区域
│   │   ├── WorkflowBar.tsx                 # 工作流节点状态条
│   │   ├── MessageList.tsx                 # 消息列表
│   │   ├── UserMessage.tsx                 # 用户消息气泡
│   │   ├── AgentMessage.tsx                # Agent 消息气泡
│   │   ├── InputBar.tsx                    # 底部输入框
│   │   ├── FeedbackPanel.tsx               # 人工反馈交互面板
│   │   ├── ResultCard.tsx                  # 最终结果 Markdown 展示
│   │   └── StateCard.tsx                   # 中间状态查看卡片
```

---

### Task 1: 项目脚手架初始化

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/index.html`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/src/index.css`
- Create: `frontend/src/main.tsx`

- [ ] **Step 1: 创建 frontend 目录并初始化 package.json**

```bash
mkdir -p /Users/hanyangjing/Desktop/self-space/research/frontend/src
```

`frontend/package.json`:
```json
{
  "name": "knowledge-agent-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^19.1.0",
    "react-dom": "^19.1.0",
    "react-markdown": "^10.1.0",
    "react-syntax-highlighter": "^15.6.1",
    "remark-gfm": "^4.0.0"
  },
  "devDependencies": {
    "@tailwindcss/vite": "^4.1.0",
    "@types/react": "^19.1.0",
    "@types/react-dom": "^19.1.0",
    "@types/react-syntax-highlighter": "^15.5.13",
    "@vitejs/plugin-react": "^4.4.0",
    "tailwindcss": "^4.1.0",
    "typescript": "^5.8.0",
    "vite": "^6.3.0"
  }
}
```

- [ ] **Step 2: 创建 index.html**

`frontend/index.html`:
```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>知识点总结 Agent</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 3: 创建 tsconfig.json**

`frontend/tsconfig.json`:
```json
{
  "compilerOptions": {
    "tsBuildInfoFile": "./node_modules/.tmp/tsconfig.app.tsbuildinfo",
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedIndexedAccess": true
  },
  "include": ["src"]
}
```

- [ ] **Step 4: 创建 vite.config.ts**

`frontend/vite.config.ts`:
```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
});
```

- [ ] **Step 5: 创建 index.css**

`frontend/src/index.css`:
```css
@import "tailwindcss";

@theme {
  --color-primary: #4f46e5;
  --color-primary-light: #818cf8;
  --color-success: #22c55e;
  --color-warning: #f59e0b;
  --color-error: #ef4444;
  --font-sans: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
}

@keyframes pulse-blue {
  0%,
  100% {
    box-shadow: 0 0 0 0 rgba(79, 70, 229, 0.4);
  }
  50% {
    box-shadow: 0 0 0 8px rgba(79, 70, 229, 0);
  }
}

.pulse-node {
  animation: pulse-blue 2s infinite;
}
```

- [ ] **Step 6: 创建 main.tsx**

`frontend/src/main.tsx`:
```typescript
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
```

- [ ] **Step 7: 安装依赖并验证 dev server 启动**

Run: `npm install`
Run: `npm run dev`

Expected: Vite dev server 在 localhost:5173 启动（页面空白但无报错）

- [ ] **Step 8: Commit**

```bash
git add frontend/
git commit -m "feat: 初始化前端项目脚手架"
```

---

### Task 2: 类型定义

**Files:**
- Create: `frontend/src/types/agent.ts`

- [ ] **Step 1: 创建类型定义文件**

`frontend/src/types/agent.ts`:
```typescript
export interface SearchResult {
  title: string;
  url: string;
  relevance: number;
  credibility: number;
}

export interface ReadingNote {
  key_points: string[];
  definitions: string[];
  examples: string[];
}

export interface AnalysisResult {
  core_concepts: string[];
  knowledge_structure: string;
  relationships: string[];
}

export interface TagResult {
  domain: string[];
  topic: string[];
  difficulty: string;
  related_fields: string[];
}

export interface ReviewResult {
  status: "pass" | "replan" | "need_human";
  feedback: string;
}

export interface HumanFeedback {
  action: "approved" | "revise" | "extra_input";
  comment: string;
  additional_material?: string;
}

export interface AgentState {
  session_id: string;
  query: string;
  next: string;
  search_results: SearchResult[];
  reading_notes: ReadingNote;
  analysis: AnalysisResult;
  tags: TagResult;
  knowledge_summary: string;
  review_result: ReviewResult | null;
  human_message: string;
  human_feedback: HumanFeedback | null;
  final_answer: string;
  sources: string[];
  error: string;
}

export interface SubmitRequest {
  query: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "agent";
  content: string;
  state?: AgentState;
  stateSnapshot?: Partial<AgentState>;
  nodeName?: string;
  timestamp: number;
}
```

- [ ] **Step 2: 验证 TypeScript 编译**

Run: `npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/
git commit -m "feat: 添加 AgentState 类型定义"
```

---

### Task 3: 抽象 API 层 + Mock 实现

**Files:**
- Create: `frontend/src/api/agentApi.ts`

- [ ] **Step 1: 创建 API 层**

`frontend/src/api/agentApi.ts`:
```typescript
import type {
  AgentState,
  HumanFeedback,
  SubmitRequest,
  SearchResult,
  ReadingNote,
  AnalysisResult,
  TagResult,
  ReviewResult,
} from "../types/agent";

export interface AgentApi {
  submitTask: (request: SubmitRequest) => Promise<AgentState>;
  submitFeedback: (
    sessionId: string,
    feedback: HumanFeedback,
  ) => Promise<AgentState>;
  getState: (sessionId: string) => Promise<AgentState>;
}

function createMockState(
  sessionId: string,
  query: string,
  next: string,
  overrides?: Partial<AgentState>,
): AgentState {
  return {
    session_id: sessionId,
    query,
    next,
    search_results: [],
    reading_notes: { key_points: [], definitions: [], examples: [] },
    analysis: { core_concepts: [], knowledge_structure: "", relationships: [] },
    tags: { domain: [], topic: [], difficulty: "", related_fields: [] },
    knowledge_summary: "",
    review_result: null,
    human_message: "",
    human_feedback: null,
    final_answer: "",
    sources: [],
    error: "",
    ...overrides,
  };
}

const mockSearchResults: SearchResult[] = [
  {
    title: "React 官方文档",
    url: "https://react.dev",
    relevance: 0.95,
    credibility: 0.98,
  },
  {
    title: "TypeScript 入门指南",
    url: "https://typescriptlang.org/docs",
    relevance: 0.88,
    credibility: 0.95,
  },
];

const mockReadingNote: ReadingNote = {
  key_points: ["组件化开发", "单向数据流", "虚拟 DOM"],
  definitions: ["React 是一个用于构建用户界面的 JavaScript 库"],
  examples: ["function App() { return <div>Hello</div> }"],
};

const mockAnalysis: AnalysisResult = {
  core_concepts: ["组件", "状态", "属性"],
  knowledge_structure: "组件树 → 状态管理 → 渲染",
  relationships: ["组件包含状态", "属性传递数据"],
};

const mockTags: TagResult = {
  domain: ["前端开发"],
  topic: ["React", "TypeScript"],
  difficulty: "中级",
  related_fields: ["Web 开发", "UI 设计"],
};

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function uuid(): string {
  return Math.random().toString(36).substring(2, 10);
}

const mockApi: AgentApi = {
  async submitTask(request: SubmitRequest): Promise<AgentState> {
    const sessionId = uuid();

    await delay(800);
    const afterSearch = createMockState(sessionId, request.query, "read", {
      search_results: mockSearchResults,
    });

    await delay(600);
    const afterRead = {
      ...afterSearch,
      next: "analyze",
      reading_notes: mockReadingNote,
    };

    await delay(700);
    const afterAnalyze = {
      ...afterRead,
      next: "tag",
      analysis: mockAnalysis,
    };

    await delay(500);
    const afterTag = {
      ...afterAnalyze,
      next: "knowledge",
      tags: mockTags,
    };

    await delay(900);
    const afterKnowledge = {
      ...afterTag,
      next: "review",
      knowledge_summary:
        "## 知识点总结\n\nReact 是 Facebook 开发的声明式 UI 库，核心概念包括组件化、虚拟 DOM 和单向数据流。",
    };

    await delay(400);
    const reviewResult: ReviewResult = {
      status: "need_human",
      feedback: "总结内容基本完整，建议补充实际应用案例。",
    };
    const afterReview = {
      ...afterKnowledge,
      next: "human",
      review_result: reviewResult,
      human_message: "总结内容已生成，请审阅后选择操作：通过、修改或补充资料。",
    };

    return afterReview;
  },

  async submitFeedback(
    sessionId: string,
    feedback: HumanFeedback,
  ): Promise<AgentState> {
    await delay(600);

    if (feedback.action === "approved") {
      return createMockState(sessionId, "", "finalize", {
        final_answer:
          "## React 知识点总结\n\n### 核心概念\n- **组件化**：将 UI 拆分为独立、可复用的组件\n- **虚拟 DOM**：通过 diff 算法高效更新真实 DOM\n- **单向数据流**：数据从父组件通过 props 向子组件传递\n\n### TypeScript 集成\n- 类型安全的组件定义\n- 接口与类型别名\n- 泛型组件\n\n### 最佳实践\n- 保持组件小巧聚焦\n- 合理使用 hooks\n- 状态提升到最近的共同父组件",
        sources: [
          "https://react.dev",
          "https://typescriptlang.org/docs",
        ],
        tags: mockTags,
        review_result: { status: "pass", feedback: "用户已确认" },
      });
    }

    if (feedback.action === "revise") {
      return createMockState(sessionId, "", "supervisor", {
        human_feedback: feedback,
        human_message: "",
        review_result: { status: "replan", feedback: feedback.comment },
      });
    }

    return createMockState(sessionId, "", "supervisor", {
      human_feedback: feedback,
      human_message: "",
      review_result: { status: "replan", feedback: feedback.comment },
    });
  },

  async getState(sessionId: string): Promise<AgentState> {
    await delay(300);
    return createMockState(sessionId, "", "review", {
      knowledge_summary: "## 当前知识点总结\n\n（从服务器获取的状态）",
    });
  },
};

function createRealApi(): AgentApi {
  return {
    async submitTask(request: SubmitRequest): Promise<AgentState> {
      const res = await fetch("/api/task", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });
      return res.json();
    },

    async submitFeedback(
      sessionId: string,
      feedback: HumanFeedback,
    ): Promise<AgentState> {
      const res = await fetch(`/api/task/${sessionId}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(feedback),
      });
      return res.json();
    },

    async getState(sessionId: string): Promise<AgentState> {
      const res = await fetch(`/api/task/${sessionId}`);
      return res.json();
    },
  };
}

const apiMode = import.meta.env.VITE_API_MODE ?? "mock";

export const agentApi: AgentApi =
  apiMode === "mock" ? mockApi : createRealApi();
```

- [ ] **Step 2: 验证 TypeScript 编译**

Run: `npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/
git commit -m "feat: 添加抽象 API 层和 mock 实现"
```

---

### Task 4: useAgentChat Hook

**Files:**
- Create: `frontend/src/hooks/useAgentChat.ts`

- [ ] **Step 1: 创建核心通信 hook**

`frontend/src/hooks/useAgentChat.ts`:
```typescript
import { useState, useCallback } from "react";
import type { AgentState, ChatMessage, HumanFeedback } from "../types/agent";
import { agentApi } from "../api/agentApi";

function uuid(): string {
  return Math.random().toString(36).substring(2, 10) + Date.now().toString(36);
}

const WORKFLOW_NODES = [
  "supervisor",
  "search",
  "read",
  "analyze",
  "tag",
  "knowledge",
  "review",
  "human",
  "finalize",
] as const;

export { WORKFLOW_NODES };

export function useAgentChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [currentState, setCurrentState] = useState<AgentState | null>(null);
  const [loading, setLoading] = useState(false);

  const addMessage = useCallback((msg: ChatMessage) => {
    setMessages((prev) => [...prev, msg]);
  }, []);

  const submit = useCallback(
    async (query: string) => {
      const userMsg: ChatMessage = {
        id: uuid(),
        role: "user",
        content: query,
        timestamp: Date.now(),
      };
      addMessage(userMsg);
      setLoading(true);

      try {
        const state = await agentApi.submitTask({ query });
        setCurrentState(state);

        const agentMsg: ChatMessage = {
          id: uuid(),
          role: "agent",
          content: state.human_message || state.knowledge_summary || state.error || "处理完成",
          state,
          nodeName: state.next,
          timestamp: Date.now(),
        };
        addMessage(agentMsg);
      } catch (err) {
        const errMsg: ChatMessage = {
          id: uuid(),
          role: "agent",
          content: `请求失败: ${err instanceof Error ? err.message : "未知错误"}`,
          timestamp: Date.now(),
        };
        addMessage(errMsg);
      } finally {
        setLoading(false);
      }
    },
    [addMessage],
  );

  const submitFeedback = useCallback(
    async (feedback: HumanFeedback) => {
      if (!currentState) return;
      setLoading(true);

      const feedbackMsg: ChatMessage = {
        id: uuid(),
        role: "user",
        content: `[${feedback.action}] ${feedback.comment}`,
        timestamp: Date.now(),
      };
      addMessage(feedbackMsg);

      try {
        const state = await agentApi.submitFeedback(
          currentState.session_id,
          feedback,
        );
        setCurrentState(state);

        const agentMsg: ChatMessage = {
          id: uuid(),
          role: "agent",
          content:
            state.final_answer ||
            state.human_message ||
            state.knowledge_summary ||
            "处理完成",
          state,
          nodeName: state.next,
          timestamp: Date.now(),
        };
        addMessage(agentMsg);
      } catch (err) {
        const errMsg: ChatMessage = {
          id: uuid(),
          role: "agent",
          content: `反馈提交失败: ${err instanceof Error ? err.message : "未知错误"}`,
          timestamp: Date.now(),
        };
        addMessage(errMsg);
      } finally {
        setLoading(false);
      }
    },
    [currentState, addMessage],
  );

  const showFeedbackPanel =
    currentState?.next === "human" ||
    currentState?.review_result?.status === "need_human";

  const showResultCard = !!currentState?.final_answer;

  return {
    messages,
    currentState,
    loading,
    submit,
    submitFeedback,
    showFeedbackPanel,
    showResultCard,
  };
}
```

- [ ] **Step 2: 验证 TypeScript 编译**

Run: `npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/
git commit -m "feat: 添加 useAgentChat 核心通信 hook"
```

---

### Task 5: 基础组件 — UserMessage + AgentMessage + InputBar

**Files:**
- Create: `frontend/src/components/UserMessage.tsx`
- Create: `frontend/src/components/AgentMessage.tsx`
- Create: `frontend/src/components/InputBar.tsx`

- [ ] **Step 1: 创建 UserMessage**

`frontend/src/components/UserMessage.tsx`:
```typescript
import type { ChatMessage } from "../types/agent";

interface UserMessageProps {
  message: ChatMessage;
}

export default function UserMessage({ message }: UserMessageProps) {
  return (
    <div className="flex justify-end mb-4">
      <div className="max-w-[70%] rounded-2xl rounded-br-sm bg-indigo-600 text-white px-4 py-3">
        <p className="whitespace-pre-wrap">{message.content}</p>
        <span className="text-xs text-indigo-200 mt-1 block text-right">
          {new Date(message.timestamp).toLocaleTimeString("zh-CN")}
        </span>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 创建 AgentMessage**

`frontend/src/components/AgentMessage.tsx`:
```typescript
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage } from "../types/agent";

interface AgentMessageProps {
  message: ChatMessage;
}

export default function AgentMessage({ message }: AgentMessageProps) {
  return (
    <div className="flex justify-start mb-4">
      <div className="max-w-[70%] rounded-2xl rounded-bl-sm bg-gray-100 dark:bg-gray-800 px-4 py-3">
        <div className="prose prose-sm dark:prose-invert max-w-none">
          <Markdown remarkPlugins={[remarkGfm]}>{message.content}</Markdown>
        </div>
        {message.nodeName && (
          <span className="text-xs text-gray-400 mt-1 block">
            节点: {message.nodeName}
          </span>
        )}
        <span className="text-xs text-gray-400 mt-1 block">
          {new Date(message.timestamp).toLocaleTimeString("zh-CN")}
        </span>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: 创建 InputBar**

`frontend/src/components/InputBar.tsx`:
```typescript
import { useState } from "react";

interface InputBarProps {
  onSubmit: (query: string) => void;
  disabled: boolean;
}

export default function InputBar({ onSubmit, disabled }: InputBarProps) {
  const [input, setInput] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    setInput("");
  }

  return (
    <form onSubmit={handleSubmit} className="border-t border-gray-200 dark:border-gray-700 p-4">
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="输入你要总结的知识点..."
          disabled={disabled}
          className="flex-1 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={disabled || !input.trim()}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          发送
        </button>
      </div>
    </form>
  );
}
```

- [ ] **Step 4: 验证 TypeScript 编译**

Run: `npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/UserMessage.tsx frontend/src/components/AgentMessage.tsx frontend/src/components/InputBar.tsx
git commit -m "feat: 添加 UserMessage、AgentMessage、InputBar 基础组件"
```

---

### Task 6: StateCard + ResultCard + FeedbackPanel

**Files:**
- Create: `frontend/src/components/StateCard.tsx`
- Create: `frontend/src/components/ResultCard.tsx`
- Create: `frontend/src/components/FeedbackPanel.tsx`

- [ ] **Step 1: 创建 StateCard**

`frontend/src/components/StateCard.tsx`:
```typescript
import { useState } from "react";
import type { AgentState } from "../types/agent";

interface StateCardProps {
  state: Partial<AgentState>;
  nodeName: string;
}

export default function StateCard({ state, nodeName }: StateCardProps) {
  const [expanded, setExpanded] = useState(false);

  const nodeLabels: Record<string, string> = {
    supervisor: "规划",
    search: "搜索",
    read: "阅读",
    analyze: "分析",
    tag: "标签",
    knowledge: "总结",
    review: "审核",
    human: "人工审核",
    finalize: "完成",
  };

  function renderContent() {
    switch (nodeName) {
      case "search":
        return (
          <div className="space-y-2">
            {state.search_results?.map((r, i) => (
              <div key={i} className="flex items-start gap-2 text-sm">
                <span className="text-indigo-500 font-medium min-w-[24px]">
                  {i + 1}.
                </span>
                <div>
                  <a
                    href={r.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-indigo-600 dark:text-indigo-400 hover:underline"
                  >
                    {r.title}
                  </a>
                  <div className="text-xs text-gray-400">
                    相关性: {(r.relevance * 100).toFixed(0)}% | 可信度:{" "}
                    {(r.credibility * 100).toFixed(0)}%
                  </div>
                </div>
              </div>
            ))}
          </div>
        );
      case "read":
        return (
          <div className="space-y-2 text-sm">
            {state.reading_notes?.key_points.length ? (
              <>
                <div>
                  <span className="font-medium text-gray-700 dark:text-gray-300">
                    关键点:
                  </span>
                  <ul className="list-disc list-inside text-gray-600 dark:text-gray-400">
                    {state.reading_notes.key_points.map((p, i) => (
                      <li key={i}>{p}</li>
                    ))}
                  </ul>
                </div>
                {state.reading_notes.definitions.length > 0 && (
                  <div>
                    <span className="font-medium text-gray-700 dark:text-gray-300">
                      定义:
                    </span>
                    <ul className="list-disc list-inside text-gray-600 dark:text-gray-400">
                      {state.reading_notes.definitions.map((d, i) => (
                        <li key={i}>{d}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </>
            ) : (
              <p className="text-gray-400">暂无阅读笔记</p>
            )}
          </div>
        );
      case "analyze":
        return (
          <div className="space-y-2 text-sm">
            {state.analysis?.core_concepts.length ? (
              <>
                <div>
                  <span className="font-medium text-gray-700 dark:text-gray-300">
                    核心概念:
                  </span>{" "}
                  {state.analysis.core_concepts.join("、")}
                </div>
                <div>
                  <span className="font-medium text-gray-700 dark:text-gray-300">
                    知识结构:
                  </span>{" "}
                  {state.analysis.knowledge_structure}
                </div>
              </>
            ) : (
              <p className="text-gray-400">暂无分析结果</p>
            )}
          </div>
        );
      case "tag":
        return state.tags ? (
          <div className="flex flex-wrap gap-2 text-sm">
            {state.tags.domain.map((t) => (
              <span
                key={t}
                className="rounded-full bg-blue-100 dark:bg-blue-900 px-3 py-1 text-blue-700 dark:text-blue-300"
              >
                {t}
              </span>
            ))}
            {state.tags.topic.map((t) => (
              <span
                key={t}
                className="rounded-full bg-purple-100 dark:bg-purple-900 px-3 py-1 text-purple-700 dark:text-purple-300"
              >
                {t}
              </span>
            ))}
            <span className="rounded-full bg-amber-100 dark:bg-amber-900 px-3 py-1 text-amber-700 dark:text-amber-300">
              {state.tags.difficulty}
            </span>
          </div>
        ) : (
          <p className="text-sm text-gray-400">暂无标签</p>
        );
      case "knowledge":
        return (
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {state.knowledge_summary || "暂无总结"}
          </p>
        );
      default:
        return (
          <p className="text-sm text-gray-400">暂无该节点的状态数据</p>
        );
    }
  }

  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-gray-50 dark:hover:bg-gray-750 transition-colors"
      >
        <span className="font-medium text-sm text-gray-700 dark:text-gray-300">
          {nodeLabels[nodeName] || nodeName} - 详细信息
        </span>
        <span className="text-gray-400 text-xs">{expanded ? "收起" : "展开"}</span>
      </button>
      {expanded && <div className="px-4 pb-3">{renderContent()}</div>}
    </div>
  );
}
```

- [ ] **Step 2: 创建 ResultCard**

`frontend/src/components/ResultCard.tsx`:
```typescript
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { AgentState } from "../types/agent";

interface ResultCardProps {
  state: AgentState;
}

export default function ResultCard({ state }: ResultCardProps) {
  return (
    <div className="rounded-xl border border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-950 p-5 mb-4">
      <h3 className="text-lg font-semibold text-green-700 dark:text-green-300 mb-3">
        最终结果
      </h3>
      <div className="prose prose-sm dark:prose-invert max-w-none mb-4">
        <Markdown remarkPlugins={[remarkGfm]}>{state.final_answer}</Markdown>
      </div>
      {state.tags && (
        <div className="flex flex-wrap gap-2 mb-3">
          {state.tags.domain.map((t) => (
            <span
              key={t}
              className="rounded-full bg-blue-100 dark:bg-blue-900 px-3 py-1 text-xs text-blue-700 dark:text-blue-300"
            >
              {t}
            </span>
          ))}
          {state.tags.topic.map((t) => (
            <span
              key={t}
              className="rounded-full bg-purple-100 dark:bg-purple-900 px-3 py-1 text-xs text-purple-700 dark:text-purple-300"
            >
              {t}
            </span>
          ))}
        </div>
      )}
      {state.sources.length > 0 && (
        <div className="text-xs text-gray-500 dark:text-gray-400">
          <span className="font-medium">来源:</span>{" "}
          {state.sources.map((s, i) => (
            <span key={i}>
              {i > 0 && " · "}
              <a
                href={s}
                target="_blank"
                rel="noopener noreferrer"
                className="text-indigo-500 hover:underline"
              >
                {s}
              </a>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: 创建 FeedbackPanel**

`frontend/src/components/FeedbackPanel.tsx`:
```typescript
import { useState } from "react";
import type { AgentState, HumanFeedback } from "../types/agent";

interface FeedbackPanelProps {
  state: AgentState;
  onSubmit: (feedback: HumanFeedback) => void;
  disabled: boolean;
}

export default function FeedbackPanel({
  state,
  onSubmit,
  disabled,
}: FeedbackPanelProps) {
  const [action, setAction] = useState<HumanFeedback["action"]>("approved");
  const [comment, setComment] = useState("");
  const [additionalMaterial, setAdditionalMaterial] = useState("");

  function handleSubmit() {
    if (disabled) return;
    const feedback: HumanFeedback = { action, comment };
    if (action === "extra_input" && additionalMaterial.trim()) {
      feedback.additional_material = additionalMaterial.trim();
    }
    onSubmit(feedback);
    setComment("");
    setAdditionalMaterial("");
  }

  return (
    <div className="rounded-xl border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950 p-5 mb-4">
      {state.human_message && (
        <p className="text-sm text-amber-800 dark:text-amber-200 mb-4">
          {state.human_message}
        </p>
      )}
      {state.review_result?.feedback && (
        <p className="text-xs text-amber-600 dark:text-amber-400 mb-3">
          审核意见: {state.review_result.feedback}
        </p>
      )}
      <div className="flex gap-2 mb-3">
        {(
          [
            { value: "approved", label: "通过" },
            { value: "revise", label: "修改" },
            { value: "extra_input", label: "补充资料" },
          ] as const
        ).map((btn) => (
          <button
            key={btn.value}
            onClick={() => setAction(btn.value)}
            className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
              action === btn.value
                ? "bg-indigo-600 text-white"
                : "bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700"
            }`}
          >
            {btn.label}
          </button>
        ))}
      </div>
      <textarea
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        placeholder="输入你的意见..."
        rows={3}
        className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
      />
      {action === "extra_input" && (
        <textarea
          value={additionalMaterial}
          onChange={(e) => setAdditionalMaterial(e.target.value)}
          placeholder="输入补充资料..."
          rows={3}
          className="w-full mt-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
        />
      )}
      <button
        onClick={handleSubmit}
        disabled={disabled}
        className="mt-3 rounded-lg bg-indigo-600 px-6 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        提交反馈
      </button>
    </div>
  );
}
```

- [ ] **Step 4: 验证 TypeScript 编译**

Run: `npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/StateCard.tsx frontend/src/components/ResultCard.tsx frontend/src/components/FeedbackPanel.tsx
git commit -m "feat: 添加 StateCard、ResultCard、FeedbackPanel 组件"
```

---

### Task 7: WorkflowBar

**Files:**
- Create: `frontend/src/components/WorkflowBar.tsx`

- [ ] **Step 1: 创建 WorkflowBar 组件**

`frontend/src/components/WorkflowBar.tsx`:
```typescript
import { useState } from "react";
import type { AgentState } from "../types/agent";
import StateCard from "./StateCard";

interface WorkflowBarProps {
  state: AgentState | null;
}

interface NodeDef {
  name: string;
  label: string;
}

const MAIN_NODES: NodeDef[] = [
  { name: "supervisor", label: "规划" },
  { name: "search", label: "搜索" },
  { name: "read", label: "阅读" },
  { name: "analyze", label: "分析" },
  { name: "tag", label: "标签" },
  { name: "knowledge", label: "总结" },
  { name: "review", label: "审核" },
];

const REVIEW_BRANCHES = [
  { status: "pass", label: "通过", target: "finalize" },
  { status: "replan", label: "重规划", target: "supervisor" },
  { status: "need_human", label: "人工审核", target: "human" },
];

const HUMAN_BRANCHES = [
  { status: "approved", label: "通过", target: "finalize" },
  { status: "revise", label: "修改", target: "supervisor" },
];

type NodeStatus = "completed" | "current" | "pending";

export default function WorkflowBar({ state }: WorkflowBarProps) {
  const [expandedNode, setExpandedNode] = useState<string | null>(null);

  if (!state) return null;

  const currentNode = state.next || "";

  const executedNodes = new Set<string>();

  if (state.search_results?.length) executedNodes.add("search");
  if (state.reading_notes?.key_points?.length) executedNodes.add("read");
  if (state.analysis?.core_concepts?.length) executedNodes.add("analyze");
  if (state.tags?.domain?.length) executedNodes.add("tag");
  if (state.knowledge_summary) executedNodes.add("knowledge");
  if (state.review_result) executedNodes.add("review");
  if (currentNode === "finalize" || state.final_answer) executedNodes.add("finalize");

  if (currentNode === "supervisor" && executedNodes.size === 0) {
    executedNodes.add("supervisor");
  }

  function getNodeStatus(name: string): NodeStatus {
    if (name === currentNode) return "current";
    if (executedNodes.has(name)) return "completed";
    return "pending";
  }

  const activeReviewBranch = state.review_result?.status ?? null;
  const activeHumanBranch =
    state.human_feedback?.action ?? null;
  const showHumanGate = activeReviewBranch === "need_human" || currentNode === "human";

  function renderNode(def: NodeDef) {
    const status = getNodeStatus(def.name);
    const isExpanded = expandedNode === def.name;

    const baseClasses =
      "flex items-center justify-center w-8 h-8 rounded-full text-xs font-bold border-2 cursor-pointer transition-all";

    const statusClasses: Record<NodeStatus, string> = {
      completed:
        "bg-green-500 border-green-500 text-white hover:scale-110",
      current:
        "bg-indigo-600 border-indigo-600 text-white pulse-node",
      pending:
        "bg-transparent border-gray-300 dark:border-gray-600 text-gray-400 cursor-default",
    };

    const handleClick = () => {
      if (status === "completed") {
        setExpandedNode(isExpanded ? null : def.name);
      }
    };

    return (
      <div key={def.name} className="flex flex-col items-center">
        <div
          className={`${baseClasses} ${statusClasses[status]}`}
          onClick={handleClick}
          title={def.label}
        >
          {def.label.charAt(0)}
        </div>
        <span className="text-xs mt-1 text-gray-500 dark:text-gray-400 whitespace-nowrap">
          {def.label}
        </span>
        {isExpanded && (
          <div className="mt-2 w-48 z-10">
            <StateCard
              state={state}
              nodeName={def.name}
            />
          </div>
        )}
      </div>
    );
  }

  function renderArrow() {
    return (
      <div className="flex items-center text-gray-300 dark:text-gray-600 mx-1">
        →
      </div>
    );
  }

  function renderBranch(
    branches: { status: string; label: string; target: string }[],
    activeBranch: string | null,
    sourceLabel: string,
  ) {
    return (
      <div className="flex flex-col items-start gap-1 ml-2 pl-2 border-l-2 border-gray-200 dark:border-gray-700">
        {branches.map((b) => {
          const isActive = activeBranch === b.status;
          const isLoop = b.target === "supervisor";
          return (
            <div
              key={b.status}
              className={`flex items-center gap-1 text-xs ${
                isActive
                  ? "text-indigo-600 dark:text-indigo-400 font-medium"
                  : "text-gray-400"
              }`}
            >
              {isLoop && <span>↩</span>}
              <span>{b.label}</span>
              {!isLoop && <span>→ {b.target === "finalize" ? "完成" : b.target}</span>}
              {isLoop && <span>回到规划</span>}
            </div>
          );
        })}
      </div>
    );
  }

  return (
    <div className="border-b border-gray-200 dark:border-gray-700 p-4 overflow-x-auto">
      <div className="flex items-start gap-0 min-w-max">
        {MAIN_NODES.map((def, i) => (
          <div key={def.name} className="flex items-start">
            {i > 0 && renderArrow()}
            {renderNode(def)}
            {def.name === "review" && (
              <div className="ml-1">
                {renderBranch(REVIEW_BRANCHES, activeReviewBranch, "审核")}
                {showHumanGate && (
                  <div className="mt-2">
                    <div className="flex items-center gap-1 mb-1">
                      <span className="text-xs text-gray-500">↓</span>
                      <span className="text-xs font-medium text-gray-600 dark:text-gray-400">
                        人工审核
                      </span>
                    </div>
                    {renderBranch(HUMAN_BRANCHES, activeHumanBranch, "人工审核")}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 验证 TypeScript 编译**

Run: `npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/WorkflowBar.tsx
git commit -m "feat: 添加 WorkflowBar 工作流可视化组件"
```

---

### Task 8: MessageList + Sidebar

**Files:**
- Create: `frontend/src/components/MessageList.tsx`
- Create: `frontend/src/components/Sidebar.tsx`

- [ ] **Step 1: 创建 MessageList**

`frontend/src/components/MessageList.tsx`:
```typescript
import { useRef, useEffect } from "react";
import type { ChatMessage } from "../types/agent";
import UserMessage from "./UserMessage";
import AgentMessage from "./AgentMessage";

interface MessageListProps {
  messages: ChatMessage[];
}

export default function MessageList({ messages }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  return (
    <div className="flex-1 overflow-y-auto p-4">
      {messages.length === 0 && (
        <div className="flex items-center justify-center h-full text-gray-400 dark:text-gray-500">
          <p>输入知识点问题开始对话</p>
        </div>
      )}
      {messages.map((msg) =>
        msg.role === "user" ? (
          <UserMessage key={msg.id} message={msg} />
        ) : (
          <AgentMessage key={msg.id} message={msg} />
        ),
      )}
      <div ref={bottomRef} />
    </div>
  );
}
```

- [ ] **Step 2: 创建 Sidebar**

`frontend/src/components/Sidebar.tsx`:
```typescript
interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export default function Sidebar({ collapsed, onToggle }: SidebarProps) {
  return (
    <div
      className={`border-r border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 transition-all duration-200 ${
        collapsed ? "w-0 overflow-hidden" : "w-[260px]"
      }`}
    >
      <div className="flex flex-col h-full">
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <button className="w-full rounded-lg bg-indigo-600 text-white px-4 py-2 text-sm font-medium hover:bg-indigo-700 transition-colors">
            + 新建会话
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-2">
          <p className="text-xs text-gray-400 dark:text-gray-500 px-2 py-2">
            会话历史
          </p>
          <div className="text-center py-8">
            <p className="text-sm text-gray-400 dark:text-gray-500">
              暂无历史会话
            </p>
          </div>
        </div>
        <div className="p-3 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={onToggle}
            className="w-full rounded-lg text-sm text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 px-3 py-2 transition-colors"
          >
            {collapsed ? "展开侧栏" : "收起侧栏"}
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: 验证 TypeScript 编译**

Run: `npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/MessageList.tsx frontend/src/components/Sidebar.tsx
git commit -m "feat: 添加 MessageList 和 Sidebar 组件"
```

---

### Task 9: ChatPanel + App 组装

**Files:**
- Create: `frontend/src/components/ChatPanel.tsx`
- Create: `frontend/src/App.tsx`

- [ ] **Step 1: 创建 ChatPanel**

`frontend/src/components/ChatPanel.tsx`:
```typescript
import type { AgentState, ChatMessage, HumanFeedback } from "../types/agent";
import WorkflowBar from "./WorkflowBar";
import MessageList from "./MessageList";
import InputBar from "./InputBar";
import FeedbackPanel from "./FeedbackPanel";
import ResultCard from "./ResultCard";

interface ChatPanelProps {
  messages: ChatMessage[];
  currentState: AgentState | null;
  loading: boolean;
  showFeedbackPanel: boolean;
  showResultCard: boolean;
  onSubmit: (query: string) => void;
  onSubmitFeedback: (feedback: HumanFeedback) => void;
}

export default function ChatPanel({
  messages,
  currentState,
  loading,
  showFeedbackPanel,
  showResultCard,
  onSubmit,
  onSubmitFeedback,
}: ChatPanelProps) {
  return (
    <div className="flex flex-col h-full flex-1">
      <header className="flex items-center justify-between border-b border-gray-200 dark:border-gray-700 px-6 py-3">
        <h1 className="text-lg font-semibold text-gray-800 dark:text-gray-200">
          知识点总结 Agent
        </h1>
        {loading && (
          <span className="text-sm text-indigo-600 dark:text-indigo-400">
            处理中...
          </span>
        )}
      </header>
      <WorkflowBar state={currentState} />
      <div className="flex-1 overflow-hidden flex flex-col">
        <MessageList messages={messages} />
        {showResultCard && currentState && (
          <div className="px-4">
            <ResultCard state={currentState} />
          </div>
        )}
        {showFeedbackPanel && currentState && (
          <div className="px-4">
            <FeedbackPanel
              state={currentState}
              onSubmit={onSubmitFeedback}
              disabled={loading}
            />
          </div>
        )}
      </div>
      <InputBar onSubmit={onSubmit} disabled={loading} />
    </div>
  );
}
```

- [ ] **Step 2: 创建 App.tsx**

`frontend/src/App.tsx`:
```typescript
import { useState } from "react";
import { useAgentChat } from "./hooks/useAgentChat";
import Sidebar from "./components/Sidebar";
import ChatPanel from "./components/ChatPanel";

export default function App() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const chat = useAgentChat();

  return (
    <div className="flex h-screen bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100">
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
      />
      <ChatPanel
        messages={chat.messages}
        currentState={chat.currentState}
        loading={chat.loading}
        showFeedbackPanel={chat.showFeedbackPanel}
        showResultCard={chat.showResultCard}
        onSubmit={chat.submit}
        onSubmitFeedback={chat.submitFeedback}
      />
    </div>
  );
}
```

- [ ] **Step 3: 验证 TypeScript 编译**

Run: `npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 4: 启动 dev server 验证页面**

Run: `npm run dev`
Expected: 浏览器访问 localhost:5173 看到完整布局，输入文字可发送，mock 模式下可走通完整流程

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ChatPanel.tsx frontend/src/App.tsx
git commit -m "feat: 组装 ChatPanel 和 App 根组件"
```

---

### Task 10: 最终验证与构建

**Files:**
- 无新文件

- [ ] **Step 1: 完整 TypeScript 编译检查**

Run: `npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 2: 生产构建**

Run: `npm run build`
Expected: 构建成功，输出到 `frontend/dist/`

- [ ] **Step 3: 最终 Commit**

```bash
git add -A
git commit -m "feat: 知识点总结 Agent 前端应用完成"
```
