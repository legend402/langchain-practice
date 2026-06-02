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
4. 路由注册：`chat_router`（无前缀）、`auth_router`（前缀 `/api/v1`）

## 目录结构

```
src/service/
├── __init__.py          # FastAPI app 工厂 + lifespan
├── result.py            # Result 统一响应包装
├── error/               # 全局异常处理
│   ├── http_exception.py
│   └── validate_exception.py
├── db/
│   ├── database.py      # AsyncEngine + session_maker + init_db
│   ├── db.py            # SQLModel 表定义（ChatSession, ChatMessage）
│   └── redis.py         # Redis 异步客户端单例 + init/close
├── controller/
│   ├── ChatSession.py   # 会话 CRUD
│   └── ChatMessage.py   # 消息 CRUD
├── auth/                # 见认证系统记忆文件
└── routes/
    ├── chat.py          # /chat/* 路由（SSE 流式 + CRUD）
    ├── auth.py          # /api/v1/auth/* 路由
    └── sse.py           # SSE 事件生成器
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

## 路由总览

### /chat（需认证）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /chat/sessions | 获取当前用户会话列表 |
| DELETE | /chat/{id} | 删除会话及其消息 |
| GET | /chat/{thread_id}/messages | 获取会话消息 |
| POST | /chat/start | 启动/继续聊天（SSE 流式） |
| POST | /chat/{thread_id}/stop | 停止运行中的任务 |
| POST | /chat/{session_id}/feedback | 人工反馈（human_gate 恢复） |

**注意：** `delete_sessions`、`chat_messages`、`chat_stop`、`chat_feedback` 缺少 `CurrentUser` 依赖。

### /api/v1/auth

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /auth/register | 注册（email + user_name + password） |
| POST | /auth/login | 登录（login 字段支持 email 或 user_name） |
| POST | /auth/refresh | 刷新 token（rotation 模式） |
| POST | /auth/logout | 登出（需认证） |
| GET | /auth/me | 获取当前用户信息（需认证） |

## SSE 事件格式

`event_generator`（`sse.py`）从 `agent.astream` 三种模式流式输出：
- `messages` → `stream_chunk` 事件（逐 token）
- `custom` → 研究节点状态持久化 + 转发
- `updates` → 节点更新持久化 + 转发
- `__interrupt__` → human_gate 暂停通知

## 错误处理

- HTTP 异常 → `{code, success: false, message}`
- 请求验证异常 → `{code: 422, success: false, message}`
