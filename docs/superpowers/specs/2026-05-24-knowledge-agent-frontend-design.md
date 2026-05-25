# 知识点总结 Agent 前端设计

## 背景

当前知识点总结 Agent 是 Python CLI 应用，基于 LangGraph 构建，包含 supervisor → search → read → analyze → tag → knowledge → review → human_gate → finalize 的工作流。需要搭建一个 React 前端页面用于接入该 Agent。

后端 API 由用户自行实现，前端只负责搭好架子并提供抽象 API 层。

## 技术栈

- React 19 + TypeScript 5
- Vite 6
- Tailwind CSS 4（Vite 插件模式）
- react-markdown + remark-gfm + react-syntax-highlighter

## 整体布局

聊天式左右布局：

```
┌──────────────────────────────────────────────┐
│  Header: 知识点总结 Agent                     │
├────────────┬─────────────────────────────────┤
│            │  ChatPanel (主区域)              │
│  Sidebar   │  ┌─────────────────────────┐    │
│            │  │ WorkflowBar              │    │
│  会话列表   │  │ 节点状态 + 条件分支      │    │
│            │  └─────────────────────────┘    │
│  + 新建会话 │  ┌─────────────────────────┐    │
│            │  │ MessageList              │    │
│  会话1     │  │ 用户消息 / Agent 回复    │    │
│  会话2     │  │ (含 StateCard 卡片)      │    │
│  ...       │  │                          │    │
│            │  │ [FeedbackPanel]          │    │
│            │  │ [ResultCard]             │    │
│            │  └─────────────────────────┘    │
│            │  ┌─────────────────────────┐    │
│            │  │ InputBar                │    │
│            │  └─────────────────────────┘    │
└────────────┴─────────────────────────────────┘
```

- Sidebar：可折叠，宽度 260px，显示会话历史列表
- ChatPanel：主聊天区域，纵向排列消息流
- WorkflowBar：聊天区顶部的节点状态条，高亮当前节点
- 消息流中按需插入：StateCard、FeedbackPanel、ResultCard

## 项目结构

```
frontend/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.ts
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── types/
│   │   └── agent.ts          # AgentState TypeScript 类型定义
│   ├── api/
│   │   └── agentApi.ts       # 抽象 API 层
│   ├── hooks/
│   │   └── useAgentChat.ts   # 核心通信 hook
│   ├── components/
│   │   ├── Sidebar.tsx       # 左侧会话列表
│   │   ├── ChatPanel.tsx     # 主聊天区域
│   │   ├── WorkflowBar.tsx   # 工作流节点状态条
│   │   ├── MessageList.tsx   # 消息列表
│   │   ├── UserMessage.tsx   # 用户消息气泡
│   │   ├── AgentMessage.tsx  # Agent 消息气泡
│   │   ├── InputBar.tsx      # 底部输入框
│   │   ├── FeedbackPanel.tsx # 人工反馈交互面板
│   │   ├── ResultCard.tsx    # 最终结果 Markdown 展示
│   │   └── StateCard.tsx     # 中间状态查看卡片
│   └── index.css             # Tailwind 入口
```

## API 抽象层

`api/agentApi.ts` 定义三个核心接口：

```typescript
// 提交任务
submitTask(request: SubmitRequest): Promise<AgentState>

// 人工反馈
submitFeedback(sessionId: string, feedback: HumanFeedback): Promise<AgentState>

// 查询当前状态
getState(sessionId: string): Promise<AgentState>
```

接口具体实现留空，由用户后续填充 fetch/SSE/WebSocket。

内置 mock 实现，通过环境变量 `VITE_API_MODE=mock|api` 切换。

## 数据流

```
用户输入 → InputBar → useAgentChat.submit() → agentApi.submitTask()
                                                    ↓
                                              AgentState 更新
                                                    ↓
                            ┌──────────────────────┼──────────────────────┐
                            ↓                      ↓                      ↓
                      WorkflowBar            MessageList 更新        FeedbackPanel
                    (当前节点高亮)         (插入中间状态/结果)        (human_gate 时显示)
```

- `useAgentChat` 持有 `AgentState`，每次 API 返回后更新
- 根据 `state.next` 判断当前节点，驱动 WorkflowBar 高亮
- 根据 `state.human_feedback` 和 `state.review_result` 判断是否显示 FeedbackPanel
- 根据 `state.final_answer` 判断是否显示 ResultCard

## WorkflowBar 设计

### 主干流程（线性展示）

```
[supervisor] → [search] → [read] → [analyze] → [tag] → [knowledge] → [review]
```

### review 之后的条件分支

```
review ── pass ──→ [finalize]
      ├── replan ──→ (回到 supervisor)
      └── need_human ──→ [human_gate] ──→ approved → [finalize]
                                    └── revise/extra_input → (回到 supervisor)
```

渲染规则：
- 已执行节点：绿色 + 实心
- 当前节点：蓝色 + 脉冲动画
- 未执行节点：灰色 + 空心
- review 右侧显示三条带标签的短分支线（pass / replan / need_human）
- 当前走了哪条分支，该路径高亮
- replan 和 revise 路径用回环箭头 + 文字"回到 supervisor"表示
- human_gate 附近显示 approved / revise 两条分支

### 点击交互

点击已执行节点可展开 StateCard 查看该步骤的中间状态。

## FeedbackPanel

触发条件：`review_result.status === "need_human"` 或 `next === "human"`

包含：
- 显示 `human_message`（Agent 提问）
- 三个操作按钮：通过（approved）/ 修改（revise）/ 补充资料（extra_input）
- 文本输入框（comment）
- 可选附件输入（additional_material）

## StateCard

可折叠卡片，嵌入消息流中，展示各节点的中间输出：
- search：搜索结果列表（标题、链接、相关性、可信度）
- read：阅读笔记摘要（关键点、定义、例子）
- analyze：核心概念、知识结构、关系
- tag：标签分类（domain、topic、difficulty 等）
- knowledge：知识点总结预览

## ResultCard

最终结果展示卡片：
- Markdown 渲染 `final_answer`
- 附带 tags 标签
- 附带 sources 来源列表

## 视觉风格

### 主题

- 明暗两套主题，默认跟随系统，可通过 Header 切换
- 配色：主色靛蓝（indigo-600），成功绿（green-500），警告黄（amber-500），错误红（red-500）
- 中文界面，使用系统默认字体栈（`-apple-system, "PingFang SC", "Microsoft YaHei", sans-serif`）

### Markdown 渲染

- react-markdown + remark-gfm 渲染 final_answer
- 代码块用 react-syntax-highlighter 高亮

## Mock 模式

- agentApi.ts 内置 mock 实现，用 setTimeout 模拟节点流转
- 开发时可脱离后端独立调试前端
- 通过环境变量 `VITE_API_MODE=mock|api` 切换

## 前端项目位置

位于 `research/frontend/` 子目录。

## 界面语言

全部中文。
