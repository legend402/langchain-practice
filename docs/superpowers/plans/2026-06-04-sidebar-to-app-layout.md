# 侧边栏提升到 AppLayout 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 SessionSidebar 从 ChatPage 提升到 AppLayout，使所有认证页面（聊天、知识库）共享侧边栏和导航。

**Architecture:** AppLayout 负责渲染 SessionSidebar 和管理折叠状态，通过 React Context 向子页面暴露侧边栏状态。ChatPage 和 KnowledgePage 只负责各自的内容区域，不再管理侧边栏。

**Tech Stack:** React 19, react-router-dom v7, Tailwind CSS v4

---

## 文件变更清单

| 操作 | 文件 | 职责 |
|------|------|------|
| 新建 | `frontend/src/contexts/SidebarContext.tsx` | 侧边栏状态 Context |
| 修改 | `frontend/src/layouts/AppLayout.tsx` | 渲染侧边栏 + Provider |
| 修改 | `frontend/src/components/SessionSidebar.tsx` | 导航菜单改为聊天/知识库两项 |
| 修改 | `frontend/src/pages/chat/ChatPage.tsx` | 移除侧边栏，只保留聊天内容 |
| 修改 | `frontend/src/pages/knowledge/KnowledgePage.tsx` | 移除独立 header，适配布局 |
| 修改 | `frontend/src/hooks/useAgentChat.ts` | 移除 sidebarCollapsed 状态 |

---

### Task 1: 创建 SidebarContext

**Files:**
- 创建: `frontend/src/contexts/SidebarContext.tsx`

- [ ] **Step 1: 创建 SidebarContext 文件**

```tsx
import { createContext, useContext, useState, useCallback, type ReactNode } from "react";

interface SidebarContextValue {
  collapsed: boolean;
  toggle: () => void;
}

const SidebarContext = createContext<SidebarContextValue | null>(null);

/**
 * 侧边栏状态 Context，提供折叠/展开控制
 */
export function SidebarProvider({ children }: { children: ReactNode }) {
  const [collapsed, setCollapsed] = useState(() => window.innerWidth < 768);
  const toggle = useCallback(() => setCollapsed((v) => !v), []);

  return (
    <SidebarContext.Provider value={{ collapsed, toggle }}>
      {children}
    </SidebarContext.Provider>
  );
}

/**
 * 获取侧边栏状态，必须在 SidebarProvider 内使用
 */
export function useSidebar(): SidebarContextValue {
  const ctx = useContext(SidebarContext);
  if (!ctx) throw new Error("useSidebar 必须在 SidebarProvider 内使用");
  return ctx;
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/contexts/SidebarContext.tsx
git commit -m "feat: 添加 SidebarContext 管理侧边栏折叠状态"
```

---

### Task 2: 改造 AppLayout — 渲染侧边栏

**Files:**
- 修改: `frontend/src/layouts/AppLayout.tsx`

- [ ] **Step 1: 改写 AppLayout**

将 `AppLayout.tsx` 全部内容替换为：

```tsx
import { Outlet } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { useAgentChat } from "../hooks/useAgentChat";
import { SidebarProvider, useSidebar } from "../contexts/SidebarContext";
import SessionSidebar from "../components/SessionSidebar";

/**
 * 应用主布局：侧边栏 + 内容区，所有认证页面共享
 */
function AppLayoutInner() {
  const auth = useAuth();
  const chat = useAgentChat();
  const sidebar = useSidebar();

  return (
    <>
      <SessionSidebar
        sessions={chat.sessions}
        activeThreadId={chat.activeThreadId}
        onSelect={(threadId) => {
          chat.loadSession(threadId);
        }}
        onNew={chat.startNewSession}
        onDelete={chat.deleteSession}
        collapsed={sidebar.collapsed}
        onToggle={sidebar.toggle}
        userEmail={auth.user?.email}
        onLogout={auth.logout}
      />
      <div className="h-screen">
        <Outlet />
      </div>
    </>
  );
}

/**
 * 应用主布局：包裹 SidebarProvider
 */
export default function AppLayout() {
  return (
    <div className="h-screen bg-background">
      <SidebarProvider>
        <AppLayoutInner />
      </SidebarProvider>
    </div>
  );
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/layouts/AppLayout.tsx
git commit -m "refactor: AppLayout 渲染 SessionSidebar 并包裹 SidebarProvider"
```

---

### Task 3: SessionSidebar 导航菜单改为聊天/知识库两项

**Files:**
- 修改: `frontend/src/components/SessionSidebar.tsx`

- [ ] **Step 1: 更新 import 和导航部分**

在 import 中将 `BookOpen` 替换为 `MessageSquare`：

```tsx
import { MessageSquarePlus, Trash2, PanelLeftClose, PanelLeft, BookOpen, MessageSquare } from "lucide-react";
```

将原来的单个知识库导航按钮（第 71-81 行）替换为双导航菜单：

```tsx
        <div className="px-2 pb-2 space-y-0.5">
          <button
            onClick={() => navigate("/")}
            className={`sidebar-item w-full ${location.pathname === "/" ? "active" : ""}`}
          >
            <MessageSquare className="w-4 h-4 shrink-0" />
            <span className="text-sm text-ink-100">聊天</span>
          </button>
          <button
            onClick={() => navigate("/knowledge")}
            className={`sidebar-item w-full ${isKnowledgeActive ? "active" : ""}`}
          >
            <BookOpen className="w-4 h-4 shrink-0" />
            <span className="text-sm text-ink-100">知识库</span>
          </button>
        </div>
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/components/SessionSidebar.tsx
git commit -m "refactor: SessionSidebar 导航菜单改为聊天/知识库两项"
```

---

### Task 4: ChatPage 瘦身 — 移除侧边栏

**Files:**
- 修改: `frontend/src/pages/chat/ChatPage.tsx`

- [ ] **Step 1: 移除 SessionSidebar 和折叠状态**

将 `ChatPage.tsx` 全部内容替换为：

```tsx
import { useState } from "react";
import { useAgentChat } from "../../hooks/useAgentChat";
import { useSidebar } from "../../contexts/SidebarContext";
import type { FileUpload } from "../../types/knowledge";

import SearchForm from "../../components/SearchForm";
import MessageList from "../../components/MessageList";

/**
 * 聊天主页面：消息列表和搜索表单（侧边栏由 AppLayout 管理）
 */
export default function ChatPage() {
  const chat = useAgentChat();
  const sidebar = useSidebar();
  const [attachments, setAttachments] = useState<FileUpload[]>([]);

  /**
   * 添加文件附件
   * @param file - 文件上传记录
   */
  function handleAddAttachment(file: FileUpload) {
    setAttachments((prev) => [...prev, file]);
  }

  /**
   * 移除文件附件
   * @param fileId - 文件 ID
   */
  function handleRemoveAttachment(fileId: string) {
    setAttachments((prev) => prev.filter((f) => f.id !== fileId));
  }

  /**
   * 提交消息并附带文件 ID
   * @param query - 用户输入的查询内容
   */
  async function handleSubmit(query: string) {
    const fileIds = attachments.length > 0 ? attachments.map((f) => f.id) : undefined;
    setAttachments([]);
    await chat.submit(query, fileIds);
  }

  return (
    <div
      className={`flex-1 flex flex-col min-w-0 h-screen main-area ${
        sidebar.collapsed ? "sidebar-collapsed" : "sidebar-expanded"
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
          <SearchForm
            onSubmit={handleSubmit}
            onStop={chat.stop}
            loading={chat.loading}
            attachments={attachments}
            onAddAttachment={handleAddAttachment}
            onRemoveAttachment={handleRemoveAttachment}
          />
        </div>
      </main>
    </div>
  );
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/pages/chat/ChatPage.tsx
git commit -m "refactor: ChatPage 移除侧边栏，使用 SidebarContext 控制布局"
```

---

### Task 5: KnowledgePage 适配新布局

**Files:**
- 修改: `frontend/src/pages/knowledge/KnowledgePage.tsx`

- [ ] **Step 1: 添加侧边栏适配**

在 import 中新增：

```tsx
import { useSidebar } from "../../contexts/SidebarContext";
```

在组件内部，`const isInitialLoading = ...` 之后新增：

```tsx
  const sidebar = useSidebar();
```

将最外层 `<div className="min-h-screen flex flex-col">` 替换为：

```tsx
    <div
      className={`min-h-screen flex flex-col main-area ${
        sidebar.collapsed ? "sidebar-collapsed" : "sidebar-expanded"
      }`}
    >
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/pages/knowledge/KnowledgePage.tsx
git commit -m "refactor: KnowledgePage 适配侧边栏布局"
```

---

### Task 6: useAgentChat 移除 sidebarCollapsed 状态

**Files:**
- 修改: `frontend/src/hooks/useAgentChat.ts`

- [ ] **Step 1: 移除侧边栏相关代码**

删除第 122 行的 `sidebarCollapsed` 状态声明：

```diff
-  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => window.innerWidth < 768);
```

删除 return 对象中的 `sidebarCollapsed` 和 `toggleSidebar`（第 365-369 行）：

```diff
-    sidebarCollapsed,
-    ...
-    toggleSidebar: () => setSidebarCollapsed((v) => !v),
```

注意：return 对象中保留 `sessions`、`activeThreadId`、`loadSession`、`startNewSession`、`deleteSession`，这些仍被 AppLayout 使用。

- [ ] **Step 2: 提交**

```bash
git add frontend/src/hooks/useAgentChat.ts
git commit -m "refactor: useAgentChat 移除 sidebarCollapsed 状态（由 SidebarContext 管理）"
```

---

## 验证步骤

完成所有 Task 后，启动前端开发服务器，依次验证：

1. `http://localhost:5173` — 聊天页面显示侧边栏，会话列表正常
2. 点击侧边栏「知识库」— 切换到知识库页面，侧边栏保持显示
3. 点击侧边栏「聊天」— 切换回聊天页面，侧边栏保持显示
4. 折叠/展开侧边栏 — 在两个页面都能正常折叠和展开
5. 知识库页面的搜索、添加、删除功能正常
6. 聊天页面的发送消息、会话切换功能正常
7. 移动端（窗口宽度 < 768px）侧边栏默认折叠，点击展开后显示 overlay
