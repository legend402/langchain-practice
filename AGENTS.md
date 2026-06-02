# 项目记忆文件索引

> 本文件是 agent 读取项目上下文的入口，按功能分文件记录，每个文件不超过 200 行。

## 项目概述

知识研究助手（Knowledge Research Agent），FastAPI 后端 + React 前端 SPA。
- 后端：LangGraph 多步研究 Agent + FastAPI SSE 流式输出 + JWT 认证
- 前端：React 19 + react-router-dom v7 + Tailwind CSS v4 + 自建 HTTP 客户端
- 数据库：PostgreSQL（SQLModel ORM + LangGraph Checkpoint）
- 搜索：Tavily API（web_search + web_fetch）
- 认证：fastapi-fullauth（JWT + Redis 黑名单/限流）

## 目录结构

```
research/
├── src/                        # Python 后端
│   ├── agent/                  # Agent 系统
│   │   ├── chat/               # 聊天 Agent（简单 ReAct）
│   │   └── research/           # 研究 Agent（多步状态机）
│   ├── service/                # FastAPI 服务层
│   │   ├── auth/               # 认证配置和模型
│   │   ├── controller/         # 业务逻辑
│   │   ├── db/                 # 数据库模型和连接
│   │   ├── error/              # 错误处理
│   │   └── routes/             # API 路由
│   ├── tools/                  # LangChain 工具
│   ├── utils/                  # 工具函数
│   ├── config.py               # 类型定义（AgentState 等）
│   └── llm.py                  # LLM 工厂
├── frontend/                   # React 前端
│   └── src/
│       ├── api/                # API 客户端（client/ + 业务 API）
│       ├── components/         # 可复用 UI 组件
│       ├── hooks/              # React 钩子
│       ├── layouts/            # 布局组件
│       ├── pages/              # 页面组件（auth/, chat/）
│       ├── routes/             # 路由配置和守卫
│       └── types/              # TypeScript 类型
├── docs/                       # 文档
└── .env.example                # 环境变量模板
```

## 记忆文件引用

> 按需加载：不要在会话开始时预读所有文件，而是根据当前任务的实际需要，读取对应的记忆文件。
> 记忆文件内容视为强制指令，加载后必须遵守。

| 文件 | 内容 | 何时加载 |
|------|------|---------|
| [后端架构](./.opencode/memory/backend.md) | 后端目录、启动流程、数据库、Result 规范 | 涉及后端代码、API 路由、数据库操作时 |
| [Agent 系统](./.opencode/memory/agent.md) | Chat Agent、Research Agent、图拓扑、节点说明 | 涉及 Agent 逻辑、工具调用、LangGraph 时 |
| [认证系统](./.opencode/memory/auth.md) | 前后端认证流程、token 管理、API 客户端 | 涉及登录、注册、token、权限相关时 |
| [前端架构](./.opencode/memory/frontend.md) | 路由、页面、组件、数据流 | 涉及前端代码、页面、组件、路由时 |

## 代码规范

- Git commit message 使用 Conventional Commits 规范，类型前缀用英文（feat/fix/refactor/docs/chore 等），描述用中文。示例：`feat: 添加用户登录功能`
- Git 提交必须按功能分批次提交，不同功能的改动分开提交（如：前端加密逻辑、后端 Redis 基础设施、记忆文件更新各为独立提交），禁止将不相关的改动混在一个 commit 中
- 定义函数必须添加函数注释，注释内容为函数的功能、参数、返回值等。注释必须使用中文
- 后端所有 API 响应使用 `Result` 包装（见 [后端架构](./.opencode/memory/backend.md)）

## 记忆文件维护

- **修改文件后**：检查是否需要同步更新对应的记忆文件描述（如新增/删除了文件、修改了接口签名、调整了目录结构等）
- **定期检查**：每隔一段时间主动审查记忆文件内容是否与当前代码一致，发现过时描述及时更新

## 关键端口和地址

- 后端服务：`http://localhost:4030`
- 前端开发：`http://localhost:5173`（Vite 默认）
- PostgreSQL：通过 `PGSQL_DB_URI` 环境变量配置
- Redis：`redis://localhost:6379/0`（默认）

## 环境变量

参考 `.env.example`，关键字段：
- `DEEPSEEK_API_KEY` / `TAVILY_API_KEY` — LLM 和搜索 API
- `LLM_BASE_URL` / `LLM_MODEL` — 默认 DeepSeek
- `FULLAUTH_SECRET_KEY` — JWT 签名密钥（>=32 字节，必须固定）
- `PGSQL_DB_URI` — PostgreSQL 连接串
- `REDIS_URL` — Redis 地址
