import os
from fastapi_fullauth import FullAuth, FullAuthConfig
from fastapi_fullauth.adapters import SQLModelAdapter
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.service.auth.auth_models import AppCreateUserSchema, AppUserSchema, RefreshToken, Role, User, UserRole


def create_fullauth(session_marker: async_sessionmaker) -> FullAuth:
  return FullAuth(
    adapter=SQLModelAdapter(
      session_maker=session_marker,
      user_model=User,
      refresh_token_model=RefreshToken,
      role_model=Role,
      user_role_model=UserRole,
      user_schema=AppUserSchema,
      create_user_schema=AppCreateUserSchema,
    ),
    config=FullAuthConfig(
      # token生成的密钥
      SECRET_KEY=os.getenv("FULLAUTH_SECRET_KEY"),
      # token 过期时间
      ACCESS_TOKEN_EXPIRE_MINUTES=30,
      # refresh_token 过期天数
      REFRESH_TOKEN_EXPIRE_DAYS=30,
      # 是否开启令牌轮换(用refresh_token换新的token)
      REFRESH_TOKEN_ROTATION=True,
      # 密码加密方式
      PASSWORD_HASH_ALGORITHM="argon2id",
      # 密码最短限制
      PASSWORD_MIN_LENGTH=8,
      # 登录字段
      LOGIN_FIELD="email",
      # 是否开启黑名单功能
      BLACKLIST_ENABLED=True,
      # 黑名单用什么方式实现
      BLACKLIST_BACKEND="redis",
      # 用户账号锁用什么方式实现
      LOCKOUT_BACKEND="redis",
      # 黑名单用什么方式实现
      RATE_LIMIT_BACKEND="redis",
      # redis链接地址
      REDIS_URL=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
      # 是否开启登录锁定
      LOCKOUT_ENABLED=True,
      # 最大登录次数
      MAX_LOGIN_ATTEMPTS=5,
      # 锁定登录时长
      LOCKOUT_DURATION_MINUTES=15,
      # 是否开启权限验证次数限制
      AUTH_RATE_LIMIT_ENABLED=True,
      # 登录权限验证次数
      AUTH_RATE_LIMIT_LOGIN=5,
      # 注册权限验证次数
      AUTH_RATE_LIMIT_REGISTER=3,
      # 权限接口的前缀地址
      API_PREFIX="/"
    )
  )