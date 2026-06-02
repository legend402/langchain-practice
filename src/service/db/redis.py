import os

import redis.asyncio as aioredis
from redis.backoff import ExponentialBackoff
from redis.retry import Retry
from redis.exceptions import ConnectionError, TimeoutError

_pool: aioredis.ConnectionPool | None = None
_redis: aioredis.Redis | None = None

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


def get_redis() -> aioredis.Redis:
    """
    获取全局 Redis 异步客户端实例

    必须在 init_redis() 之后调用。

    Returns:
        redis.asyncio.Redis: 基于 ConnectionPool 的 Redis 异步客户端
    """
    if _redis is None:
        raise RuntimeError("Redis 未初始化，请先调用 init_redis()")
    return _redis


async def init_redis() -> None:
    """
    初始化 Redis 连接池和客户端

    从 REDIS_URL 环境变量创建 ConnectionPool，再基于连接池创建 Redis 客户端。
    在 FastAPI lifespan 启动时调用。
    """
    global _pool, _redis
    _pool = aioredis.ConnectionPool.from_url(
        REDIS_URL,
        decode_responses=True,
        max_connections=10,
        socket_keepalive=True,
        health_check_interval=30
    )
    retry_strategy = Retry(
        backoff=ExponentialBackoff(cap=10, base=1),
        retries=3,
        supported_errors=(ConnectionError, TimeoutError)
    )
    _redis = aioredis.Redis(
        connection_pool=_pool,
        retry=retry_strategy,
        retry_on_error=[ConnectionError, TimeoutError]
    )


async def close_redis() -> None:
    """
    关闭 Redis 连接池

    断开客户端并释放连接池中所有连接，在 FastAPI lifespan 关闭时调用。
    """
    global _pool, _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
    if _pool is not None:
        await _pool.disconnect()
        _pool = None
