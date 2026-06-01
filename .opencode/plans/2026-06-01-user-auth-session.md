# 用户认证与会话管理 — 实施计划

> **给 Agent 执行者：** 必须使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 按任务逐步执行。步骤使用 checkbox（`- [ ]`）语法追踪。

**目标：** 为现有问答系统接入用户认证（注册/登录支持邮箱和用户名）和会话管理，为后续个人知识库功能做准备。

**架构：** 使用 `fastapi-fullauth[sqlmodel,redis]` 库，通过 SQLModel 适配器连接现有 PostgreSQL。Redis 负责令牌黑名单。由于该库的 `LOGIN_FIELD` 只支持单一字段，我们编写自定义登录端点来检测输入是邮箱还是用户名。使用 `fullauth.bind(app)`（而非 `init_app`）以便控制路由注册。ChatSession 表新增 `user_id` 外键实现数据隔离。

**技术栈：** fastapi-fullauth v0.11.0、SQLModel、PostgreSQL (asyncpg)、Redis (Docker)、React 19、TypeScript、Vite、Tailwind CSS v4

---

## 文件结构

### 后端 — 新建文件
| 文件 | 职责 |
|------|------|
| `src/service/db/auth_models.py` | 用户、刷新令牌、角色、用户角色 SQLModel 表 + 自定义 Schema |
| `src/service/auth.py` | FullAuth 实例创建和配置 |
| `src/service/deps.py` | 类型化的 FastAPI 依赖注入（CurrentUser） |
| `src/service/routes/auth.py` | 自定义登录（邮箱或用户名）、注册、刷新、登出、获取当前用户 |

### 后端 — 修改文件
| 文件 | 变更内容 |
|------|----------|
| `src/service/db/db.py` | ChatSession 新增 `user_id: Optional[UUID]` 字段 |
| `src/service/db/database.py` | 导出 `session_maker`，导入认证模型以确保建表 |
| `src/service/__init__.py` | 创建 FullAuth 实例、调用 `bind()`、注册自定义认证路由 |
| `src/service/routes/chat.py` | 所有端点加入 `user: CurrentUser` 参数，按 `user_id` 过滤会话 |
| `src/service/controller/ChatSession.py` | `create_session()` 接收并存储 `user_id` |
| `requirements.txt` | 添加 `fastapi-fullauth[sqlmodel,redis]` |
| `.env.example` | 添加 `REDIS_URL`、`FULLAUTH_SECRET_KEY` |

### 前端 — 新建文件
| 文件 | 职责 |
|------|------|
| `frontend/src/types/auth.ts` | 认证相关 TypeScript 类型 |
| `frontend/src/api/tokenStore.ts` | 令牌存储（access/refresh 的 get/set/clear），仅负责读写 |
| `frontend/src/api/http.ts` | 统一 HTTP 客户端：自动注入 Authorization、401 自动刷新重试、请求/响应拦截 |
| `frontend/src/api/authApi.ts` | 认证 API（注册、登录、刷新、登出、获取用户），基于 http 客户端 |
| `frontend/src/hooks/useAuth.tsx` | AuthProvider 上下文 + useAuth Hook |
| `frontend/src/components/LoginPage.tsx` | 登录页面（邮箱/用户名 + 密码） |
| `frontend/src/components/RegisterPage.tsx` | 注册页面（邮箱 + 用户名 + 密码） |

### 前端 — 修改文件
| 文件 | 变更内容 |
|------|----------|
| `frontend/src/main.tsx` | 用 AuthProvider 包裹 App |
| `frontend/src/App.tsx` | 路由守卫：未登录显示登录页，已登录显示聊天页 |
| `frontend/src/api/agentApi.ts` | 用 http 客户端替代手动 fetch，删除所有 token 拼接逻辑 |
| `frontend/src/components/SessionSidebar.tsx` | 显示用户邮箱 + 登出按钮 |

---

## 任务 1：基础设施 — Redis + Python 依赖

**涉及文件：**
- 修改：`requirements.txt`
- 修改：`.env.example`

- [ ] **步骤 1：启动 Redis Docker 容器**

```bash
docker run -d --name redis -p 6379:6379 redis --appendonly yes
```

运行：`docker ps`
预期：看到 `redis` 容器状态为 `Up`。

- [ ] **步骤 2：安装 Python 依赖**

```bash
pip install "fastapi-fullauth[sqlmodel,redis]"
```

注：之前已安装过，如未安装则执行此命令。

- [ ] **步骤 3：更新 requirements.txt**

在 `requirements.txt` 末尾添加：

```
fastapi-fullauth[sqlmodel,redis]
```

- [ ] **步骤 4：更新 .env.example**

在 `.env.example` 末尾添加：

```
REDIS_URL=redis://localhost:6379/0
FULLAUTH_SECRET_KEY=your-secret-key-at-least-32-bytes-long
```

- [ ] **步骤 5：提交**

```bash
git add requirements.txt .env.example
git commit -m "chore: add fastapi-fullauth and redis to dependencies"
```

---

## 任务 2：后端 — 认证数据模型

**涉及文件：**
- 新建：`src/service/db/auth_models.py`

此文件定义认证相关的数据库表和自定义 Pydantic Schema。`UserMixin` 自带 `id`（UUID7）、`email`、`hashed_password`、`is_active`、`is_verified`、`is_superuser`、`created_at` 字段，我们额外添加 `username` 自定义字段。

自定义的 `CreateUserSchema` 子类包含 `username` 字段，这样 `adapter.create_user(data, hashed_password)` 会通过 `data.model_dump(exclude={"email", "password"})` 提取 `username` 并作为 kwargs 传给 SQLModel 构造函数。

- [ ] **步骤 1：创建 auth_models.py**

```python
from pydantic import Field
from sqlmodel import Relationship

from fastapi_fullauth.models.sqlmodel import (
    RefreshTokenMixin,
    RoleMixin,
    UserMixin,
    UserRoleMixin,
)
from fastapi_fullauth.types import CreateUserSchema, UserSchema


class RefreshToken(RefreshTokenMixin, table=True):
    pass


class Role(RoleMixin, table=True):
    pass


class UserRole(UserRoleMixin, table=True):
    pass


class User(UserMixin, table=True):
    username: str = Field(default="", max_length=50, index=True)
    roles: list[Role] = Relationship(link_model=UserRole)
    refresh_tokens: list[RefreshToken] = Relationship()


class AppUserSchema(UserSchema):
    username: str = ""


class AppCreateUserSchema(CreateUserSchema):
    username: str = ""
```

- [ ] **步骤 2：提交**

```bash
git add src/service/db/auth_models.py
git commit -m "feat: add auth data models with username field"
```

---

## 任务 3：后端 — ChatSession 新增 user_id

**涉及文件：**
- 修改：`src/service/db/db.py`

- [ ] **步骤 1：为 ChatSession 添加 user_id 外键**

在 `src/service/db/db.py` 中，import 区域新增 `from uuid import UUID`，并给 `ChatSession` 添加 `user_id` 字段。

完整文件如下：

```python
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID
from sqlalchemy import Column, ForeignKey, Integer, Identity
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class ChatSession(SQLModel, table=True):
    thread_id: str = Field(primary_key=True)
    title: Optional[str] = None
    user_id: Optional[UUID] = Field(
        default=None,
        foreign_key="fullauth_users.id",
    )
    create_at: datetime = Field(default_factory=datetime.now)


class Roles(Enum):
    HUMAN = "human"
    AI = "ai"


class ChatMessage(SQLModel, table=True):
    id: Optional[int] = Field(
        default=None, sa_column=Column("id", Integer, Identity(), primary_key=True)
    )
    thread_id: str = Field(
        default=None,
        sa_column=Column(
            "thread_id", ForeignKey("chatsession.thread_id", ondelete="CASCADE")
        ),
    )
    role: str
    node_name: Optional[str] = None
    content: Optional[str] = None
    state: Optional[dict] = Field(default=None, sa_column=Column("state", JSONB))
    create_at: datetime = Field(default_factory=datetime.now)
```

- [ ] **步骤 2：提交**

```bash
git add src/service/db/db.py
git commit -m "feat: add user_id foreign key to ChatSession"
```

---

## 任务 4：后端 — FullAuth 配置

**涉及文件：**
- 新建：`src/service/auth.py`

此模块创建 `FullAuth` 实例，使用 `SQLModelAdapter` 和完整配置。传入自定义的 `AppUserSchema` 和 `AppCreateUserSchema`，使库的响应包含 `username` 字段。

`SQLModelAdapter` 需要 `session_maker`（`async_sessionmaker` 实例）和 `user_model`。通过 `user_schema` 和 `create_user_schema` 参数传入自定义 Schema。

- [ ] **步骤 1：创建 auth.py**

```python
import os

from sqlalchemy.ext.asyncio import async_sessionmaker

from fastapi_fullauth import FullAuth, FullAuthConfig
from fastapi_fullauth.adapters import SQLModelAdapter

from src.service.db.auth_models import (
    AppCreateUserSchema,
    AppUserSchema,
    RefreshToken,
    Role,
    User,
    UserRole,
)


def create_fullauth(session_maker: async_sessionmaker) -> FullAuth:
    return FullAuth(
        adapter=SQLModelAdapter(
            session_maker=session_maker,
            user_model=User,
            refresh_token_model=RefreshToken,
            role_model=Role,
            user_role_model=UserRole,
            user_schema=AppUserSchema,
            create_user_schema=AppCreateUserSchema,
        ),
        config=FullAuthConfig(
            SECRET_KEY=os.getenv("FULLAUTH_SECRET_KEY"),
            ACCESS_TOKEN_EXPIRE_MINUTES=30,
            REFRESH_TOKEN_EXPIRE_DAYS=30,
            REFRESH_TOKEN_ROTATION=True,
            PASSWORD_HASH_ALGORITHM="argon2id",
            PASSWORD_MIN_LENGTH=8,
            LOGIN_FIELD="email",
            BLACKLIST_ENABLED=True,
            BLACKLIST_BACKEND="redis",
            REDIS_URL=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            LOCKOUT_ENABLED=True,
            MAX_LOGIN_ATTEMPTS=5,
            LOCKOUT_DURATION_MINUTES=15,
            AUTH_RATE_LIMIT_ENABLED=True,
            AUTH_RATE_LIMIT_LOGIN=5,
            AUTH_RATE_LIMIT_REGISTER=3,
            API_PREFIX="/api/v1",
        ),
    )
```

- [ ] **步骤 2：提交**

```bash
git add src/service/auth.py
git commit -m "feat: add FullAuth configuration with Redis blacklist"
```

---

## 任务 5：后端 — 类型化依赖注入

**涉及文件：**
- 新建：`src/service/deps.py`

`fastapi_fullauth.dependencies` 的 `current_user` 依赖从 `app.state.fullauth` 获取 FullAuth 实例，从 `Authorization: Bearer <token>` 提取 JWT，解码后查找用户并返回 `UserSchema`。我们用自定义的 `AppUserSchema` 标注，获得完整的 IDE 类型提示。

- [ ] **步骤 1：创建 deps.py**

```python
from typing import Annotated

from fastapi import Depends
from fastapi_fullauth.dependencies import current_user

from src.service.db.auth_models import AppUserSchema

CurrentUser = Annotated[AppUserSchema, Depends(current_user)]
```

- [ ] **步骤 2：提交**

```bash
git add src/service/deps.py
git commit -m "feat: add typed CurrentUser dependency"
```

---

## 任务 6：后端 — 自定义认证路由

**涉及文件：**
- 新建：`src/service/routes/auth.py`

这是最核心的文件。由于 `LOGIN_FIELD` 只支持单字段，我们编写自定义登录逻辑：
1. 检测输入是邮箱（包含 `@`）还是用户名
2. 使用 `adapter.get_user_by_field()` 查找用户
3. 使用 `adapter.get_hashed_password()` 获取密码哈希
4. 使用 `fastapi_fullauth.core.crypto` 的 `verify_password()` 验证
5. 使用 `token_engine.create_token_pair()` 生成令牌对
6. 使用 `adapter.store_refresh_token()` 持久化刷新令牌

注册流程直接调用库的 `register()` flow 函数，然后创建令牌。刷新和登出也使用库的内部方法。

- [ ] **步骤 1：创建认证路由**

```python
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr

from src.service.deps import CurrentUser

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    login: str
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


def _is_email(value: str) -> bool:
    return "@" in value


def _get_fullauth():
    from src.service import get_app
    return get_app().state.fullauth


@router.post("/register")
async def register(body: RegisterRequest):
    fullauth = _get_fullauth()
    adapter = fullauth.adapter

    from fastapi_fullauth.flows.register import register as do_register

    schema = adapter._create_user_schema(
        email=body.email, password=body.password, username=body.username
    )
    user = await do_register(
        adapter=adapter,
        data=schema,
        hash_algorithm=fullauth.config.PASSWORD_HASH_ALGORITHM,
        password_validator=fullauth.password_validator,
    )

    roles = await adapter.get_user_roles(user.id)
    extra = await fullauth.get_custom_claims(user)
    access, refresh_meta = fullauth.token_engine.create_token_pair(
        user_id=str(user.id), roles=roles, extra=extra,
    )

    from fastapi_fullauth.types import RefreshToken as RT

    await adapter.store_refresh_token(
        RT(
            token=refresh_meta.token,
            user_id=user.id,
            expires_at=refresh_meta.expires_at,
            family_id=refresh_meta.family_id,
        )
    )

    await fullauth.hooks.trigger("after_register", user)

    return {
        "access_token": access,
        "refresh_token": refresh_meta.token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "username": getattr(user, "username", ""),
            "is_active": user.is_active,
            "is_verified": user.is_verified,
        },
    }


@router.post("/login")
async def login(body: LoginRequest):
    fullauth = _get_fullauth()
    adapter = fullauth.adapter

    if _is_email(body.login):
        user = await adapter.get_user_by_field("email", body.login)
    else:
        user = await adapter.get_user_by_field("username", body.login)

    hashed = await adapter.get_hashed_password(user.id) if user else None

    if user is None or hashed is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    from fastapi_fullauth.core.crypto import verify_password

    if not verify_password(body.password, hashed):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用",
        )

    roles = await adapter.get_user_roles(user.id)
    extra = await fullauth.get_custom_claims(user)
    access, refresh_meta = fullauth.token_engine.create_token_pair(
        user_id=str(user.id), roles=roles, extra=extra,
    )

    from fastapi_fullauth.types import RefreshToken as RT

    await adapter.store_refresh_token(
        RT(
            token=refresh_meta.token,
            user_id=user.id,
            expires_at=refresh_meta.expires_at,
            family_id=refresh_meta.family_id,
        )
    )

    await fullauth.hooks.trigger("after_login", user)

    return {
        "access_token": access,
        "refresh_token": refresh_meta.token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "username": getattr(user, "username", ""),
            "is_active": user.is_active,
            "is_verified": user.is_verified,
        },
    }


@router.post("/refresh")
async def refresh(body: RefreshRequest):
    fullauth = _get_fullauth()
    adapter = fullauth.adapter

    try:
        payload = await fullauth.token_engine.decode_token(body.refresh_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="刷新令牌无效或已过期",
        )

    if payload.type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌类型错误",
        )

    stored = await adapter.get_refresh_token(body.refresh_token)
    if stored is None or stored.revoked:
        if stored and stored.family_id:
            await adapter.revoke_refresh_token_family(stored.family_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="刷新令牌已被吊销",
        )

    user = await adapter.get_user_by_id(payload.sub)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已禁用",
        )

    await adapter.revoke_refresh_token(body.refresh_token)

    roles = await adapter.get_user_roles(user.id)
    extra = await fullauth.get_custom_claims(user)
    access, refresh_meta = fullauth.token_engine.create_token_pair(
        user_id=str(user.id), roles=roles, extra=extra, family_id=stored.family_id,
    )

    from fastapi_fullauth.types import RefreshToken as RT

    await adapter.store_refresh_token(
        RT(
            token=refresh_meta.token,
            user_id=user.id,
            expires_at=refresh_meta.expires_at,
            family_id=refresh_meta.family_id,
        )
    )

    return {
        "access_token": access,
        "refresh_token": refresh_meta.token,
        "token_type": "bearer",
    }


@router.post("/logout")
async def logout(user: CurrentUser, body: RefreshRequest):
    fullauth = _get_fullauth()
    await fullauth.adapter.revoke_refresh_token(body.refresh_token)
    await fullauth.hooks.trigger("after_logout", str(user.id))
    return {"message": "已成功登出"}


@router.get("/me")
async def get_me(user: CurrentUser):
    return {
        "id": str(user.id),
        "email": user.email,
        "username": getattr(user, "username", ""),
        "is_active": user.is_active,
        "is_verified": user.is_verified,
    }
```

- [ ] **步骤 2：提交**

```bash
git add src/service/routes/auth.py
git commit -m "feat: add custom auth routes (login with email/username, register, refresh, logout)"
```

---

## 任务 7：后端 — 更新 database.py 导出 session_maker

**涉及文件：**
- 修改：`src/service/db/database.py`

需要导出 `session_maker`（`async_sessionmaker` 实例）供 FullAuth 的 `SQLModelAdapter` 使用。同时导入认证模型，使 `SQLModel.metadata.create_all` 能一并创建认证相关表。

- [ ] **步骤 1：更新 database.py**

```python
import os
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from src.service.db.auth_models import RefreshToken, Role, User, UserRole
from src.service.db.db import ChatMessage, ChatSession


def create_engine(db_uri: str) -> AsyncEngine:
    async_uri = db_uri.replace("postgresql://", "postgresql+asyncpg://")
    return create_async_engine(async_uri, echo=False)


async def init_db(engine):
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


engine = create_engine(os.getenv("PGSQL_DB_URI"))
session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session():
    async with session_maker() as session:
        yield session
```

关键变更：导入了认证模型、用 `async_sessionmaker` 创建了 `session_maker`、`get_session` 改用 `session_maker`。

- [ ] **步骤 2：提交**

```bash
git add src/service/db/database.py
git commit -m "refactor: export session_maker, import auth models for table creation"
```

---

## 任务 8：后端 — 将 FullAuth 接入 FastAPI 应用

**涉及文件：**
- 修改：`src/service/__init__.py`

使用 `fullauth.bind(app)` 而非 `fullauth.init_app(app)`，这样库不会自动注册任何路由。我们只注册自定义认证路由。`bind()` 调用会设置 `app.state.fullauth`，这是 `current_user` 依赖正常工作的前提。

- [ ] **步骤 1：更新 \_\_init\_\_.py**

```python
import warnings
from contextlib import asynccontextmanager

import langchain_core._api.deprecation
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

import os

from src.agent.chat.create_agent import create_chat_agent
from src.service.auth import create_fullauth
from src.service.db.database import engine, init_db, session_maker
from src.service.routes.auth import router as auth_router
from src.service.routes.chat import router as chat_router

load_dotenv()

warnings.filterwarnings("ignore", message=".*allowed_objects.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="langgraph")

DB_URI = os.getenv("PGSQL_DB_URI")

_app: FastAPI | None = None


def get_app() -> FastAPI:
    return _app


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _app
    pool = AsyncConnectionPool(
        DB_URI, min_size=2, max_size=10, kwargs={"autocommit": True}, open=False
    )
    await pool.open()
    checkpointer = AsyncPostgresSaver(pool)
    await checkpointer.setup()
    app.state.agent = create_chat_agent(checkpointer)
    await init_db(engine)
    app.state.engine = engine
    app.state.sessions = {}

    fullauth = create_fullauth(session_maker)
    fullauth.bind(app)

    _app = app
    yield
    await pool.close()


def create_agent_service():
    app = FastAPI(lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(chat_router)
    return app


app = create_agent_service()
```

- [ ] **步骤 2：提交**

```bash
git add src/service/__init__.py
git commit -m "feat: wire FullAuth into FastAPI app lifecycle with bind()"
```

---

## 任务 9：后端 — 为聊天路由添加认证保护

**涉及文件：**
- 修改：`src/service/routes/chat.py`
- 修改：`src/service/controller/ChatSession.py`

- [ ] **步骤 1：更新 ChatSession 控制器**

修改 `src/service/controller/ChatSession.py`：

```python
from uuid import UUID
from sqlmodel.ext.asyncio.session import AsyncSession

from src.service.db.db import ChatSession


async def create_session(session: AsyncSession, thread_id: str, title: str, user_id: UUID):
    session.add(
        ChatSession(
            thread_id=thread_id,
            title=title,
            user_id=user_id,
        )
    )
    await session.commit()
```

- [ ] **步骤 2：更新聊天路由**

修改 `src/service/routes/chat.py`。在 import 中添加 `from src.service.deps import CurrentUser`，然后为每个端点的第一个参数加上 `user: CurrentUser`，查询时按 `user_id` 过滤。

完整更新文件：

```python
from typing import Any, Optional
from uuid import uuid4
from asyncio import Task

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, delete

from src.agent.chat.config import recover_chat_state
from src.service.controller.ChatMessage import create_message, get_messages
from src.service.controller.ChatSession import create_session
from src.service.db.database import get_session, engine
from src.service.db.db import ChatSession, ChatMessage
from src.service.deps import CurrentUser
from src.service.result import Result
from src.service.routes.sse import event_generator
from src.utils.agent import get_initial_state, recover_state

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatStart(BaseModel):
    query: str
    thread_id: Optional[str] = None


class ChatFeedback(BaseModel):
    decision: str
    comment: str
    additional_material: str | None = None


@router.get("/sessions")
async def chat_sessions(user: CurrentUser, session: AsyncSession = Depends(get_session)):
    result = await session.exec(
        select(ChatSession)
        .where(ChatSession.user_id == user.id)
        .order_by(ChatSession.create_at.desc())
    )
    return Result.success(result.all())


@router.delete("/{id}")
async def delete_sessions(id: str, user: CurrentUser, session: AsyncSession = Depends(get_session)):
    result = await session.get(ChatSession, id)
    if not result or result.user_id != user.id:
        return Result.error(f"未找到id为{id}的数据")
    await session.exec(delete(ChatMessage).where(ChatMessage.thread_id == id))
    await session.delete(result)
    await session.commit()
    return Result.success(message="删除成功")


@router.get("/{thread_id}/messages")
async def chat_messages(thread_id: str, user: CurrentUser, session: AsyncSession = Depends(get_session)):
    sess = await session.get(ChatSession, thread_id)
    if not sess or sess.user_id != user.id:
        return Result.error("未找到该会话")
    list_ = await get_messages(session, thread_id)
    return Result.success(list_)


@router.post("/start")
async def chat_start(body: ChatStart, user: CurrentUser, session: AsyncSession = Depends(get_session)):
    from src.service import get_app

    app = get_app()
    agent = app.state.agent
    thread_id = body.thread_id or str(uuid4())

    state = {"user_query": body.query}
    if body.thread_id is None:
        await create_session(
            session=session, thread_id=thread_id, title=body.query[:50], user_id=user.id
        )
    elif session.get(ChatSession, thread_id):
        messages = await get_messages(session, thread_id)
        state = recover_chat_state(messages)
        state["messages"] = state["messages"] + [("human", body.query)]

    await create_message(
        session=session, thread_id=thread_id, role="human", content=body.query
    )
    await session.commit()

    initial_state = get_initial_state(state)

    return StreamingResponse(
        event_generator(
            agent=agent,
            initial_state=initial_state,
            session_id=thread_id,
            engine=engine,
            sessions=app.state.sessions,
            create_message_fn=create_message,
        ),
        media_type="text/events-stream",
    )


@router.post("/{thread_id}/stop")
async def chat_stop(thread_id: str, user: CurrentUser):
    from src.service import get_app

    app = get_app()
    task: Task[Any] = app.state.sessions.get(thread_id)
    if task and not task.done():
        task.cancel()
        return Result.success(message="已停止")
    return Result.success(message="未找到正在运行中的任务")


@router.post("/{session_id}/feedback")
async def chat_feedback(session_id: str, body: ChatFeedback, user: CurrentUser):
    from src.service import get_app
    from langgraph.types import Command

    app = get_app()
    agent = app.state.agent

    return StreamingResponse(
        event_generator(
            agent=agent,
            initial_state=Command(resume=body.model_dump()),
            session_id=session_id,
            engine=engine,
            sessions=app.state.sessions,
            create_message_fn=create_message,
        ),
        media_type="text/events-stream",
    )
```

- [ ] **步骤 3：提交**

```bash
git add src/service/routes/chat.py src/service/controller/ChatSession.py
git commit -m "feat: protect all chat routes with auth, filter by user_id"
```

---

## 任务 10：后端 — 验证认证端点

- [ ] **步骤 1：启动 Redis**

```bash
docker start redis
```

- [ ] **步骤 2：启动后端服务**

```bash
python run.py
```

- [ ] **步骤 3：测试注册**

```bash
curl -s -X POST http://localhost:4030/api/v1/auth/register -H "Content-Type: application/json" -d "{\"email\": \"test@example.com\", \"username\": \"testuser\", \"password\": \"securepass123\"}"
```

预期：返回 JSON 包含 `access_token`、`refresh_token`、`user` 对象。

- [ ] **步骤 4：测试邮箱登录**

```bash
curl -s -X POST http://localhost:4030/api/v1/auth/login -H "Content-Type: application/json" -d "{\"login\": \"test@example.com\", \"password\": \"securepass123\"}"
```

预期：同上响应格式。

- [ ] **步骤 5：测试用户名登录**

```bash
curl -s -X POST http://localhost:4030/api/v1/auth/login -H "Content-Type: application/json" -d "{\"login\": \"testuser\", \"password\": \"securepass123\"}"
```

预期：同上响应格式。

- [ ] **步骤 6：测试 /auth/me**

```bash
curl -s http://localhost:4030/api/v1/auth/me -H "Authorization: Bearer <ACCESS_TOKEN>"
```

预期：`{"id": "...", "email": "test@example.com", "username": "testuser", ...}`

- [ ] **步骤 7：测试无令牌访问受保护端点**

```bash
curl -s http://localhost:4030/chat/sessions
```

预期：`401 Unauthorized`。

- [ ] **步骤 8：测试带令牌访问受保护端点**

```bash
curl -s http://localhost:4030/chat/sessions -H "Authorization: Bearer <ACCESS_TOKEN>"
```

预期：`{"code": 200, "success": true, "result": [], ...}`

- [ ] **步骤 9：提交修复（如有）**

```bash
git add -A
git commit -m "fix: address backend auth issues found during testing"
```

---

## 任务 11：前端 — 认证类型定义

**涉及文件：**
- 新建：`frontend/src/types/auth.ts`

- [ ] **步骤 1：创建认证类型**

```typescript
export interface AuthUser {
  id: string;
  email: string;
  username: string;
  is_active: boolean;
  is_verified: boolean;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface LoginRequest {
  login: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  username: string;
  password: string;
}

export interface AuthResponse extends AuthTokens {
  user: AuthUser;
}

export interface RefreshResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}
```

- [ ] **步骤 2：提交**

```bash
git add frontend/src/types/auth.ts
git commit -m "feat: add auth TypeScript types"
```

---

## 任务 12：前端 — 令牌存储模块

**涉及文件：**
- 新建：`frontend/src/api/tokenStore.ts`

职责单一：只管 token 的读写，不管网络请求。

- [ ] **步骤 1：创建 tokenStore.ts**

```typescript
const ACCESS_KEY = "access_token";
const REFRESH_KEY = "refresh_token";

let _accessToken: string | null = localStorage.getItem(ACCESS_KEY);

export function getAccessToken(): string | null {
  return _accessToken;
}

export function setAccessToken(token: string | null) {
  _accessToken = token;
  if (token) localStorage.setItem(ACCESS_KEY, token);
  else localStorage.removeItem(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY);
}

export function setRefreshToken(token: string | null) {
  if (token) localStorage.setItem(REFRESH_KEY, token);
  else localStorage.removeItem(REFRESH_KEY);
}

export function clearTokens() {
  setAccessToken(null);
  setRefreshToken(null);
}

export function hasToken(): boolean {
  return _accessToken !== null;
}
```

- [ ] **步骤 2：提交**

```bash
git add frontend/src/api/tokenStore.ts
git commit -m "feat: add token storage module"
```

---

## 任务 13：前端 — 统一 HTTP 客户端

**涉及文件：**
- 新建：`frontend/src/api/http.ts`

这是前端请求层的核心。封装 `fetch`，提供三个关键能力：
1. **自动注入 Authorization 请求头** — 所有经过 `http.get/post` 发出的请求自动带上 Bearer token
2. **401 自动刷新 + 重试** — 收到 401 时自动调用 refresh 接口，成功后重发原请求；刷新也失败则清除 token
3. **防并发刷新** — 多个请求同时 401 时，只发一次 refresh，其余请求排队等待同一个 refresh Promise

设计说明：
- `http.get/post` 返回解析后的 JSON（`ApiResponse<T>`）
- `http.stream` 返回原始 `Response`（用于 SSE 流式场景，不做 JSON 解析）
- `http.raw` 返回原始 `Response`（完全不做任何拦截，用于特殊场景）
- 所有认证相关接口（login/register/refresh/logout）通过 `http.raw` 或 `skipAuth` 参数跳过自动注入，避免循环依赖

- [ ] **步骤 1：创建 http.ts**

```typescript
import * as tokenStore from "./tokenStore";

const BASE_URL = "http://localhost:4030";

export interface HttpError {
  status: number;
  detail: string;
}

export interface ApiResponse<T = unknown> {
  ok: boolean;
  data: T;
  status: number;
}

export class HttpException extends Error {
  status: number;
  detail: string;
  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

let refreshPromise: Promise<boolean> | null = null;

async function refreshTokens(): Promise<boolean> {
  const refreshToken = tokenStore.getRefreshToken();
  if (!refreshToken) return false;
  try {
    const res = await fetch(`${BASE_URL}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) {
      tokenStore.clearTokens();
      return false;
    }
    const data = await res.json();
    tokenStore.setAccessToken(data.access_token);
    tokenStore.setRefreshToken(data.refresh_token);
    return true;
  } catch {
    tokenStore.clearTokens();
    return false;
  }
}

async function ensureRefreshed(): Promise<boolean> {
  if (refreshPromise) return refreshPromise;
  refreshPromise = refreshTokens().finally(() => {
    refreshPromise = null;
  });
  return refreshPromise;
}

async function authFetch(
  url: string,
  init?: RequestInit,
  options?: { skipAuth?: boolean },
): Promise<Response> {
  const token = tokenStore.getAccessToken();
  const headers = new Headers(init?.headers);
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (token && !options?.skipAuth) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(url, { ...init, headers });

  if (response.status === 401 && token && !options?.skipAuth) {
    const refreshed = await ensureRefreshed();
    if (refreshed) {
      const newToken = tokenStore.getAccessToken();
      headers.set("Authorization", `Bearer ${newToken}`);
      return fetch(url, { ...init, headers });
    }
    tokenStore.clearTokens();
  }

  return response;
}

async function handleResponse<T>(response: Response): Promise<ApiResponse<T>> {
  if (!response.ok) {
    let detail = `请求失败: ${response.status}`;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {}
    throw new HttpException(response.status, detail);
  }
  const data: T = await response.json();
  return { ok: true, data, status: response.status };
}

function fullUrl(path: string): string {
  if (path.startsWith("http")) return path;
  return `${BASE_URL}${path}`;
}

export const http = {
  async get<T = unknown>(path: string): Promise<ApiResponse<T>> {
    const res = await authFetch(fullUrl(path));
    return handleResponse<T>(res);
  },

  async post<T = unknown>(
    path: string,
    body?: unknown,
    options?: { skipAuth?: boolean },
  ): Promise<ApiResponse<T>> {
    const res = await authFetch(fullUrl(path), {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    }, options);
    return handleResponse<T>(res);
  },

  async delete<T = unknown>(path: string): Promise<ApiResponse<T>> {
    const res = await authFetch(fullUrl(path), { method: "DELETE" });
    return handleResponse<T>(res);
  },

  async stream(path: string, body?: unknown, init?: RequestInit): Promise<Response> {
    const token = tokenStore.getAccessToken();
    const headers = new Headers(init?.headers);
    if (!headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
    return fetch(fullUrl(path), {
      ...init,
      method: "POST",
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
  },

  raw(path: string, init?: RequestInit): Promise<Response> {
    return fetch(fullUrl(path), init);
  },
};
```

- [ ] **步骤 2：提交**

```bash
git add frontend/src/api/http.ts
git commit -m "feat: add unified HTTP client with auto auth and 401 refresh"
```

---

## 任务 14：前端 — 认证 API 层

**涉及文件：**
- 新建：`frontend/src/api/authApi.ts`

基于 `http` 客户端实现，不再手动管理 token 注入。

- [ ] **步骤 1：创建 authApi.ts**

```typescript
import { http } from "./http";
import * as tokenStore from "./tokenStore";
import type {
  AuthResponse,
  AuthUser,
  LoginRequest,
  RegisterRequest,
} from "../types/auth";

export { tokenStore };

export async function register(data: RegisterRequest): Promise<AuthResponse> {
  const { data: result } = await http.post<AuthResponse>(
    "/api/v1/auth/register",
    data,
    { skipAuth: true },
  );
  tokenStore.setAccessToken(result.access_token);
  tokenStore.setRefreshToken(result.refresh_token);
  return result;
}

export async function login(data: LoginRequest): Promise<AuthResponse> {
  const { data: result } = await http.post<AuthResponse>(
    "/api/v1/auth/login",
    data,
    { skipAuth: true },
  );
  tokenStore.setAccessToken(result.access_token);
  tokenStore.setRefreshToken(result.refresh_token);
  return result;
}

export async function getMe(): Promise<AuthUser> {
  const { data } = await http.get<AuthUser>("/api/v1/auth/me");
  return data;
}

export async function refresh(): Promise<boolean> {
  const refreshToken = tokenStore.getRefreshToken();
  if (!refreshToken) return false;
  try {
    const { data } = await http.post<{ access_token: string; refresh_token: string }>(
      "/api/v1/auth/refresh",
      { refresh_token: refreshToken },
      { skipAuth: true },
    );
    tokenStore.setAccessToken(data.access_token);
    tokenStore.setRefreshToken(data.refresh_token);
    return true;
  } catch {
    tokenStore.clearTokens();
    return false;
  }
}

export async function logout(): Promise<void> {
  const refreshToken = tokenStore.getRefreshToken();
  if (refreshToken) {
    try {
      await http.post("/api/v1/auth/logout", { refresh_token: refreshToken });
    } catch {}
  }
  tokenStore.clearTokens();
}
```

- [ ] **步骤 2：提交**

```bash
git add frontend/src/api/authApi.ts
git commit -m "feat: add auth API layer based on unified HTTP client"
```

---

## 任务 15：前端 — useAuth Hook 和 AuthProvider

**涉及文件：**
- 新建：`frontend/src/hooks/useAuth.tsx`

- [ ] **步骤 1：创建 useAuth.tsx**

```tsx
import {
  useState,
  useCallback,
  useEffect,
  createContext,
  useContext,
  type ReactNode,
} from "react";
import type { AuthUser, LoginRequest, RegisterRequest } from "../types/auth";
import * as authApi from "../api/authApi";

interface AuthState {
  user: AuthUser | null;
  loading: boolean;
  initialized: boolean;
}

interface AuthContextValue extends AuthState {
  login: (data: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    loading: true,
    initialized: false,
  });

  useEffect(() => {
    if (!authApi.tokenStore.hasToken()) {
      setState({ user: null, loading: false, initialized: true });
      return;
    }
    authApi
      .getMe()
      .then((user) => setState({ user, loading: false, initialized: true }))
      .catch(async () => {
        const refreshed = await authApi.refresh();
        if (refreshed) {
          const user = await authApi.getMe();
          setState({ user, loading: false, initialized: true });
        } else {
          setState({ user: null, loading: false, initialized: true });
        }
      });
  }, []);

  const loginFn = useCallback(async (data: LoginRequest) => {
    const result = await authApi.login(data);
    setState({ user: result.user, loading: false, initialized: true });
  }, []);

  const registerFn = useCallback(async (data: RegisterRequest) => {
    const result = await authApi.register(data);
    setState({ user: result.user, loading: false, initialized: true });
  }, []);

  const logoutFn = useCallback(async () => {
    await authApi.logout();
    setState({ user: null, loading: false, initialized: true });
  }, []);

  return (
    <AuthContext.Provider
      value={{ ...state, login: loginFn, register: registerFn, logout: logoutFn }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth 必须在 AuthProvider 内使用");
  return ctx;
}
```

- [ ] **步骤 2：提交**

```bash
git add frontend/src/hooks/useAuth.tsx
git commit -m "feat: add AuthProvider context and useAuth hook"
```

---

## 任务 16：前端 — 登录和注册页面

**涉及文件：**
- 新建：`frontend/src/components/LoginPage.tsx`
- 新建：`frontend/src/components/RegisterPage.tsx`

- [ ] **步骤 1：创建 LoginPage.tsx**

```tsx
import { useState, type FormEvent } from "react";
import { useAuth } from "../hooks/useAuth";

interface LoginPageProps {
  onSwitchToRegister: () => void;
}

export default function LoginPage({ onSwitchToRegister }: LoginPageProps) {
  const { login } = useAuth();
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
    } catch (err) {
      setError(err instanceof Error ? err.message : "登录失败");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
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
          <button onClick={onSwitchToRegister} className="text-accent hover:underline cursor-pointer">
            注册
          </button>
        </p>
      </div>
    </div>
  );
}
```

- [ ] **步骤 2：创建 RegisterPage.tsx**

```tsx
import { useState, type FormEvent } from "react";
import { useAuth } from "../hooks/useAuth";

interface RegisterPageProps {
  onSwitchToLogin: () => void;
}

export default function RegisterPage({ onSwitchToLogin }: RegisterPageProps) {
  const { register } = useAuth();
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
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
      await register({ email, username, password });
    } catch (err) {
      setError(err instanceof Error ? err.message : "注册失败");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
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
              value={username}
              onChange={(e) => setUsername(e.target.value)}
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
          <button onClick={onSwitchToLogin} className="text-accent hover:underline cursor-pointer">
            登录
          </button>
        </p>
      </div>
    </div>
  );
}
```

- [ ] **步骤 3：提交**

```bash
git add frontend/src/components/LoginPage.tsx frontend/src/components/RegisterPage.tsx
git commit -m "feat: add login and register page components"
```

---

## 任务 17：前端 — 接入认证到应用 + 改造 agentApi

**涉及文件：**
- 修改：`frontend/src/main.tsx`
- 修改：`frontend/src/App.tsx`
- 修改：`frontend/src/api/agentApi.ts`
- 修改：`frontend/src/components/SessionSidebar.tsx`

- [ ] **步骤 1：更新 main.tsx**

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.tsx";
import { AuthProvider } from "./hooks/useAuth.tsx";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AuthProvider>
      <App />
    </AuthProvider>
  </StrictMode>
);
```

- [ ] **步骤 2：更新 App.tsx**

```tsx
import { useState } from "react";
import { useAuth } from "./hooks/useAuth";
import { useAgentChat } from "./hooks/useAgentChat";

import SearchForm from "./components/SearchForm";
import MessageList from "./components/MessageList";
import SessionSidebar from "./components/SessionSidebar";
import LoginPage from "./components/LoginPage";
import RegisterPage from "./components/RegisterPage";

export default function App() {
  const auth = useAuth();
  const [showRegister, setShowRegister] = useState(false);

  if (auth.loading || !auth.initialized) {
    return (
      <div className="h-screen flex items-center justify-center bg-background">
        <div className="text-ink-400 text-sm">加载中...</div>
      </div>
    );
  }

  if (!auth.user) {
    if (showRegister) {
      return <RegisterPage onSwitchToLogin={() => setShowRegister(false)} />;
    }
    return <LoginPage onSwitchToRegister={() => setShowRegister(true)} />;
  }

  return <ChatApp />;
}

function ChatApp() {
  const chat = useAgentChat();
  const auth = useAuth();

  return (
    <div className="h-screen bg-background flex">
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

- [ ] **步骤 3：改造 agentApi.ts — 使用 http 客户端**

改造思路：
- 删除所有手动 `getAccessToken()` + 拼接 `Authorization` header 的代码
- `getSessions`、`getMessages`、`deleteSession`、`stopChat` 用 `http.get/post/delete` 替代，认证和 401 刷新完全由 http 客户端自动处理
- `submitSSETask` 用 `http.stream` 获取原始 Response（因为 SSE 需要自己读取流），认证自动注入

在 `frontend/src/api/agentApi.ts` 顶部替换原来的 import 和 `API_BASE`，添加：

```typescript
import { http, HttpException } from "./http";
```

删除 `const API_BASE = "http://localhost:4030";`。

替换 `submitSSETask` 方法：

```typescript
    agentApi.abort.abort();
    agentApi.abort = new AbortController();
    const response = await http.stream("/chat/start", request, {
      signal: agentApi.abort.signal,
    });

    if (response.status === 401) {
      agentApi.abort = new AbortController();
      const retryResponse = await http.stream("/chat/start", request, {
        signal: agentApi.abort.signal,
      });
      await agentApi.dispatchEvent(events, retryResponse);
      return;
    }
```

替换 `getSessions`：

```typescript
  async getSessions(): Promise<ChatSession[]> {
    const { data } = await http.get<ChatSession[]>("/chat/sessions");
    return (data as { result?: ChatSession[] }).result ?? data;
  },
```

替换 `getMessages`：

```typescript
  async getMessages(threadId: string): Promise<ChatMessage[]> {
    const { data } = await http.get<ChatMessage[]>(`/chat/${threadId}/messages`);
    const rows: ChatMessageFromDB[] = (data as { result?: ChatMessageFromDB[] }).result ?? data;
    return parseMessages(rows);
  },
```

替换 `deleteSession`：

```typescript
  async deleteSession(threadId: string): Promise<void> {
    await http.delete(`/chat/${threadId}`);
  },
```

替换 `stopChat`：

```typescript
  async stopChat(session_id: string) {
    agentApi.abort.abort();
    const { data } = await http.post(`/chat/${session_id}/stop`);
    return data;
  },
```

- [ ] **步骤 4：更新 SessionSidebar.tsx — 添加用户信息和登出按钮**

添加 `userEmail` 和 `onLogout` 属性：

```tsx
interface SessionSidebarProps {
  sessions: ChatSession[];
  activeThreadId: string | null;
  onSelect: (threadId: string) => void;
  onNew: () => void;
  onDelete: (threadId: string) => void;
  collapsed: boolean;
  onToggle: () => void;
  userEmail?: string;
  onLogout: () => void;
}
```

在解构的 props 中加入 `userEmail` 和 `onLogout`，然后在 `</aside>` 结束标签前添加用户区域：

```tsx
        <div className="px-3 py-3 border-t border-white/30 mt-auto">
          <div className="flex items-center justify-between">
            <span className="text-xs text-ink-400 truncate">{userEmail}</span>
            <button
              onClick={onLogout}
              className="text-xs text-ink-400 hover:text-red-500 transition-colors cursor-pointer"
            >
              退出
            </button>
          </div>
        </div>
```

- [ ] **步骤 5：提交**

```bash
git add frontend/src/main.tsx frontend/src/App.tsx frontend/src/api/agentApi.ts frontend/src/components/SessionSidebar.tsx
git commit -m "feat: wire auth into app, refactor agentApi to use unified HTTP client"
```

---

## 任务 15：端到端验证

- [ ] **步骤 1：启动 Redis**

```bash
docker start redis
```

- [ ] **步骤 2：启动后端**

```bash
python run.py
```

- [ ] **步骤 3：启动前端**

```bash
cd frontend && npm run dev
```

- [ ] **步骤 4：测试注册流程**

1. 浏览器打开 `http://localhost:5173`
2. 应看到登录页面
3. 点击「注册」
4. 填写邮箱、用户名、密码、确认密码
5. 提交 → 应跳转到聊天页面
6. 确认侧栏底部显示用户邮箱

- [ ] **步骤 5：测试邮箱登录**

1. 点击「退出」
2. 应跳转到登录页面
3. 用邮箱登录
4. 应跳转到聊天页面

- [ ] **步骤 6：测试用户名登录**

1. 登出
2. 用用户名（非邮箱）登录
3. 应跳转到聊天页面

- [ ] **步骤 7：测试会话隔离**

1. 创建聊天会话，发送一条消息
2. 登出
3. 注册第二个用户
4. 确认看不到第一个用户的任何会话

- [ ] **步骤 8：提交修复（如有）**

```bash
git add -A
git commit -m "fix: address e2e auth issues"
```

---

## API 端点总览

| 方法 | 路径 | 需认证 | 说明 |
|------|------|--------|------|
| POST | `/api/v1/auth/register` | 否 | 注册（邮箱 + 用户名 + 密码） |
| POST | `/api/v1/auth/login` | 否 | 登录（支持邮箱或用户名） |
| POST | `/api/v1/auth/refresh` | 否 | 刷新访问令牌 |
| POST | `/api/v1/auth/logout` | 是 | 登出并吊销令牌 |
| GET | `/api/v1/auth/me` | 是 | 获取当前用户信息 |
| GET | `/chat/sessions` | 是 | 获取用户的聊天会话列表 |
| POST | `/chat/start` | 是 | 开始/恢复聊天 |
| GET | `/chat/{id}/messages` | 是 | 获取聊天消息 |
| DELETE | `/chat/{id}` | 是 | 删除聊天会话 |
| POST | `/chat/{id}/stop` | 是 | 停止正在运行的聊天任务 |
| POST | `/chat/{id}/feedback` | 是 | 提交人工反馈 |
