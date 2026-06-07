# 后端架构

## 启动流程

1. `run.py` → `uvicorn.run("src.service:app", port=4030, reload=True)`
2. `src/service/__init__.py` → `create_agent_service()` 创建 FastAPI 实例
3. `lifespan` 异步上下文管理器处理启动/关闭：
   - 创建 `AsyncConnectionPool`（psycopg）
   - 初始化 `AsyncPostgresSaver`（LangGraph Checkpoint）
   - 创建 Chat Agent → `app.state.agent`
   - 初始化数据库表 → `init_db(engine)`
   - 创建 FullAuth 实例 → `app.state.fullauth`
   - 初始化 Redis 客户端 → `init_redis()` → `app.state.redis`
   - 初始化 Milvus 客户端 → `get_milvus_client()`
   - 创建上传目录 → `ensure_upload_dir()`
4. 路由注册：`chat_router`、`upload_router`、`knowledge_router`（无前缀）、`auth_router`（前缀 `/api/v1`）

## 目录结构

```
src/
├── service/
│   ├── __init__.py          # FastAPI app 工厂 + lifespan
│   ├── result.py            # Result 统一响应包装
│   ├── error/               # 全局异常处理
│   │   ├── http_exception.py
│   │   └── validate_exception.py
│   ├── db/
│   │   ├── database.py      # AsyncEngine + session_maker + init_db
│   │   ├── db.py            # SQLModel 表定义（ChatSession, ChatMessage, FileUpload, KnowledgeEntry）
│   │   └── redis.py         # Redis 异步客户端单例 + init/close
│   ├── controller/
│   │   ├── ChatSession.py   # 会话 CRUD
│   │   ├── ChatMessage.py   # 消息 CRUD
│   │   ├── FileUpload.py    # 文件上传 CRUD（白名单校验、磁盘存储）
│   │   └── KnowledgeEntry.py # re-export 层（当前未使用）
│   ├── auth/                # 见认证系统记忆文件
│   └── routes/
│       ├── chat.py          # /chat/* 路由（SSE 流式 + CRUD）
│       ├── auth.py          # /api/v1/auth/* 路由
│       ├── sse.py           # SSE 事件生成器
│       ├── upload.py        # /upload/* 路由（文件上传管理）
│       └── knowledge.py     # /knowledge/* 路由（知识库 CRUD + 检索）
├── knowledge/               # 知识库核心引擎
│   ├── embedding.py         # ZhipuAI Embedding 单例工厂（embedding-3, 2048 维）
│   ├── parser.py            # 统一文档解析器（Docling + GLM-4V-Flash，单次遍历输出 DocumentElement[]）
│   ├── chunker.py           # 结构化分块器（基于 DocumentElement[]，不依赖 Docling）
│   ├── milvus.py            # Milvus 客户端单例 + v1/v2 Collection 管理
│   ├── search.py            # v1/v2 混合检索（dense IP + BM25 → RRF，v2 携带页码/章节元数据）
│   └── service.py           # 知识库业务服务（v1: save_entry; v2: save_entry_v2/delete_entry_v2/search_knowledge_v2）
├── tools/
│   ├── research.py          # 桥接 chat → research agent
│   ├── web_search.py        # Tavily 搜索
│   ├── web_fetch.py         # Tavily URL 内容提取
│   ├── knowledge_search.py  # 知识库检索工具 v2（带溯源信息）
│   ├── read_file.py         # 文件读取工具（@tool）
│   ├── read_pages.py        # 按文档读原文工具（@tool，读取 full.md 缓存）
│   ├── extract_tables.py    # 表格抽取工具（@tool，读取表格缓存）
│   └── save_to_knowledge.py # 存入知识库工具（@tool）
├── tools/
│   ├── research.py          # 桥接 chat → research agent
│   ├── web_search.py        # Tavily 搜索
│   ├── web_fetch.py         # Tavily URL 内容提取
│   ├── knowledge_search.py  # 知识库检索工具（@tool）
│   ├── read_file.py         # 文件读取工具（@tool）
│   └── save_to_knowledge.py # 存入知识库工具（@tool）
├── utils/
│   ├── __init__.py          # node_hook 装饰器
│   ├── agent.py             # 状态合并/恢复 + contextvars 用户 ID 注入
│   ├── pagination.py        # 通用分页工具（PaginatedResult[T]）
│   └── reader.py            # 文件读取器（支持 txt/md/html/docx；PDF 已迁移到 parser.py）
├── agent/                   # 见 Agent 系统记忆文件
├── config.py                # 类型定义（AgentState + DocumentElement + ChunkConfig + StructuredChunk）
└── llm.py                   # LLM 工厂
```

## Result 响应规范

所有 API 响应使用 `Result` 静态方法包装，返回 `ResultOptions`：

```python
class ResultOptions(BaseModel):
    code: int        # HTTP 状态码
    success: bool    # 是否成功
    result: Any      # 业务数据
    message: str     # 提示信息
    timeStamp: datetime
```

静态方法：
- `Result.success(result, message="success")` → code=200, success=True
- `Result.error(message)` → code=400, success=False
- `Result.serve_error(message)` → code=500, success=False
- `Result.un_authorized(message)` → code=401, success=False

**注意：** 登录失败返回 HTTP 200 + body 中 `code: 401`，不是 HTTP 401。

## 数据库模型

`src/service/db/database.py`：
- `engine`：从 `PGSQL_DB_URI` 创建的 AsyncEngine（asyncpg 驱动）
- `session_marker`：`async_sessionmaker` 实例
- `init_db(engine)`：`SQLModel.metadata.create_all`

`src/service/db/db.py`：
- `ChatSession(thread_id, title, user_id, create_at)` — `user_id` FK → `fullauth_users.id`
- `ChatMessage(id, thread_id, role, node_name, content, state, create_at)` — `thread_id` FK → `chatsession.thread_id`（CASCADE）
- `FileUpload(id, user_id, file_name, file_path, file_format, file_size, create_at)` — 文件上传记录
- `KnowledgeEntry(id, user_id, title, source_type, source_id, chunk_count, content_preview, create_at)` — 知识条目元数据

## 路由总览

### /chat（需认证）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /chat/sessions | 获取当前用户会话列表 |
| DELETE | /chat/{id} | 删除会话及其消息 |
| GET | /chat/{thread_id}/messages | 获取会话消息 |
| POST | /chat/start | 启动/继续聊天（SSE 流式，支持 file_ids） |
| POST | /chat/{thread_id}/stop | 停止运行中的任务 |
| POST | /chat/{session_id}/feedback | 人工反馈（human_gate 恢复） |

**注意：** `chat/start` 接受 `file_ids: Optional[list[str]]`，用于传递附件。路由中通过 `set_current_user_id()` 注入用户上下文。

### /upload（需认证）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /upload/file | 上传文件（multipart/form-data） |
| GET | /upload/files | 获取当前用户文件列表 |
| GET | /upload/files/{id}/content | 读取文件文本内容 |
| DELETE | /upload/files/{id} | 删除文件（磁盘 + 数据库） |

支持格式：.txt, .md, .html, .pdf, .docx

### /knowledge（需认证）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /knowledge/entries | 创建知识条目（content 或 file_id 二选一） |
| GET | /knowledge/entries | 分页列表（?page=1&size=20） |
| GET | /knowledge/entries/{id} | 知识条目详情 |
| DELETE | /knowledge/entries/{id} | 删除知识条目（Milvus chunks + PG 记录） |
| POST | /knowledge/search | 检索知识库（query, top_k） |

### /api/v1/auth

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /auth/register | 注册（email + user_name + password） |
| POST | /auth/login | 登录（login 字段支持 email 或 user_name） |
| POST | /auth/refresh | 刷新 token（rotation 模式） |
| POST | /auth/logout | 登出（需认证） |
| GET | /auth/me | 获取当前用户信息（需认证） |

## 知识库系统

### 核心流程（v2）

1. **存入**：文件/文本 → `parser.py`（Docling 解析 + GLM-4V-Flash 图片描述，单次遍历输出 `DocumentElement[]`）→ `chunker.py`（基于 DocumentElement 语义分块）→ `embedding` 向量化 → Milvus v2 存储 + PG 元数据
2. **检索**：query 向量化 → dense(IP) + BM25(sparse) 双路召回 → RRF 融合排序 → 返回带页码/章节/类型的 StructuredSearchHit
3. **删除**：Milvus v2 chunks 删除 + 缓存文件清理 + PG 记录删除

### 解析层

- `parser.py`：统一文档解析器，Docling 处理 PDF/DOCX/MD/HTML
  - `parse_document(file_path, entry_id)` → `ParsedDocument`（含 `elements: list[DocumentElement]`）
  - `_enrich_images()`：并发 GLM-4V-Flash 处理图片（asyncio.Semaphore(5)）
  - `_walk_and_cache()`：单次遍历 DoclingDocument，同时产出 DocumentElement[] + 缓存文件
  - `_extract_table_image()`：裁剪图片型表格（BOTTOMLEFT 坐标翻转）
  - 缓存：`uploads/parsed/{entry_id}/full.md` + `tables/T-001.md` + `tables/tables_meta.json` + `image_descriptions.json`

### 分块层

- `chunker.py`：`chunk_structured(elements: list[DocumentElement])` → `list[StructuredChunk]`
  - 不依赖 Docling API，纯基于中间表示
  - 标题作为分块边界（挂入 heading_path），表格/图片/代码独立成块，段落合并直到超过 max_chunk_size

### DocumentElement 数据类

`src/config.py`：
- `element_type`: heading / paragraph / table / image / code
- `text`: 文本内容
- `page_number`: 页码
- `heading_level`: 标题层级（仅 heading）
- `table_id`: 表格 ID（仅 table，如 T-001）

### Milvus Schema（v2）

每用户一个 v2 Collection（`knowledge_v2_{user_id}`）：
- v1 字段：`pk`, `entry_id`, `chunk_index`, `text`, `dense_vector`, `sparse_vector`
- v2 新增字段：`page_start`(INT64), `page_end`(INT64), `heading_path`(VARCHAR 512), `content_type`(VARCHAR 32), `table_id`(VARCHAR 64)

### 溯源引用格式

Agent 回答时引用知识库内容：（来源：《文档标题》第X页 "章节名"）

### 通用工具

**`pagination.py`** — `PaginatedResult[T]` dataclass：
- 字段：`items`, `total`, `page`, `size`, `pages`（`__post_init__` 计算）
- `pages = max(1, ceil(total / size))`
- **注意：** `pages` 必须是普通字段（不能是 `@property`），否则 FastAPI 序列化时会丢失

**`reader.py`** — 文件读取器：
- 支持 .txt/.md/.html/.pdf/.docx
- 自动编码检测（charset_normalizer）
- 50MB 大小限制

### 用户上下文传递

通过 `contextvars` 实现协程安全的 user_id 注入：
- `src/utils/agent.py`：`set_current_user_id()` / `get_current_user_id()`
- `chat.py` 路由在调用 agent 前设置
- 工具函数（knowledge_search, read_file, save_to_knowledge）通过 `get_current_user_id()` 读取

## SSE 事件格式

`event_generator`（`sse.py`）从 `agent.astream` 三种模式流式输出：
- `messages` → `stream_chunk` 事件（逐 token）
- `custom` → 研究节点状态持久化 + 转发
- `updates` → 节点更新持久化 + 转发
- `__interrupt__` → human_gate 暂停通知

## 错误处理

- HTTP 异常 → `{code, success: false, message}`
- 请求验证异常 → `{code: 422, success: false, message}`

## 环境变量

参考 `.env.example`，关键字段：
- `DEEPSEEK_API_KEY` / `TAVILY_API_KEY` — LLM 和搜索 API
- `LLM_BASE_URL` / `LLM_MODEL` — 默认 DeepSeek
- `FULLAUTH_SECRET_KEY` — JWT 签名密钥（>=32 字节，必须固定）
- `PGSQL_DB_URI` — PostgreSQL 连接串
- `REDIS_URL` — Redis 地址
- `MILVUS_URI` — Milvus 地址（默认 http://localhost:19530）
- `ZHIPU_API_KEY` — 智谱 Embedding API 密钥
- `UPLOAD_DIR` — 文件上传目录（默认 ./uploads）
