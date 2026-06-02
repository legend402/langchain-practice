# Redis 接入设计

## 目标

为后端提供统一的 Redis 客户端，供 RSA 密钥存储等业务主动使用。

## 现状

- `redis 8.0.0` 已安装，但仅被 `fastapi-fullauth` 内部使用
- 后端没有自己的 Redis 客户端实例
- `REDIS_URL` 环境变量已定义（`redis://localhost:6379/0`）

## 方案

### 新增文件：`src/service/db/redis.py`

与 `database.py` 风格一致：模块级单例 + 初始化/关闭函数。

职责：提供全局 `redis.asyncio.Redis` 客户端，不封装业务逻辑。

核心接口：
- `get_redis()` — 获取 Redis 客户端实例（模块级单例）
- `init_redis()` — 创建连接，lifespan 启动时调用
- `close_redis()` — 关闭连接，lifespan 关闭时调用

### 目录结构变更

```
src/service/db/
├── database.py     # PostgreSQL（现有）
├── db.py           # SQLModel 表定义（现有）
└── redis.py        # Redis 客户端（新增）
```

### lifespan 改动（`src/service/__init__.py`）

```python
from src.service.db.redis import init_redis, close_redis, get_redis

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... 现有 PostgreSQL 初始化 ...
    
    await init_redis()
    app.state.redis = get_redis()
    
    yield
    
    await close_redis()
    await pool.close()
```

### 使用示例

```python
from src.service.db.redis import get_redis

# RSA 密钥存储
redis = get_redis()
await redis.set("rsa:key:abc", private_key_pem, ex=3600)
pem = await redis.get("rsa:key:abc")
```

## 设计原则

- 不封装业务逻辑，只提供底层客户端（YAGNI）
- 与 `database.py` 风格一致：模块级单例 + 初始化/关闭函数
- 业务代码直接操作 `redis` 客户端
