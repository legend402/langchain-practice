from fastapi import APIRouter
from fastapi_fullauth import CreateUserSchema, FullAuth, UserSchema
from pydantic import BaseModel, EmailStr

from src.service.auth.deps import CurrentUser
from src.service.result import Result

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
  login: str
  password: str

class RegisterRequest(BaseModel):
  email: EmailStr
  user_name: str
  password: str

class RefreshRequest(BaseModel):
  refresh_token: str

def _is_email(value: str):
  return "@" in value

def _get_fullauth() -> FullAuth[UserSchema, CreateUserSchema]:
  from src.service import get_app
  return get_app().state.fullauth

@router.post("/register")
async def register(body: RegisterRequest):
  fullauth = _get_fullauth()
  adapter = fullauth.adapter

  from fastapi_fullauth.flows.register import register as do_register

  schema = adapter._create_user_schema(
    email=body.email, password=body.password, user_name=body.user_name
  )
  user = await do_register(
    adapter=adapter,
    data=schema,
    hash_algorithm=fullauth.config.PASSWORD_HASH_ALGORITHM,
    password_validator=fullauth.password_validator,
  )

  access, refresh_meta = await generate_token(fullauth=fullauth, user=user)

  await fullauth.hooks.emit("after_register", user=user)

  return Result.success({
    "access_token": access,
    "refresh_token": refresh_meta.token,
    "token_type": "bearer",
    "user": {
      "id": str(user.id),
      "email": user.email,
      "user_name": getattr(user, "user_name", ""),
      "is_active": user.is_active,
      "is_verified": user.is_verified,
    },
  })

@router.post("/login")
async def login(body: LoginRequest):
  fullauth = _get_fullauth()
  adapter = fullauth.adapter

  if _is_email(body.login):
    user = await adapter.get_user_by_field("email", body.login)
  else:
    user = await adapter.get_user_by_field("user_name", body.login)

  hashed = await adapter.get_hashed_password(user.id) if user else None

  if user is None or hashed is None:
    return Result.un_authorized("用户名或密码错误")
  
  from fastapi_fullauth.core.crypto import verify_password

  if not verify_password(body.password, hashed):
    return Result.un_authorized("用户名或密码错误")
  
  if not user.is_active:
    return Result.un_authorized("账号已被禁用")

  access, refresh_meta = await generate_token(fullauth=fullauth, user=user)

  await fullauth.hooks.emit("after_login", user=user)


  return Result.success({
    "access_token": access,
    "refresh_token": refresh_meta.token,
    "token_type": "bearer",
    "user": {
      "id": str(user.id),
      "email": user.email,
      "user_name": getattr(user, "user_name", ""),
      "is_active": user.is_active,
      "is_verified": user.is_verified,
    },
  })

@router.post("/refresh")
async def refresh(body: RefreshRequest):
  fullauth = _get_fullauth()
  adapter = fullauth.adapter

  try:
    payload = await fullauth.token_engine.decode_token(body.refresh_token)
  except Exception:
    return Result.un_authorized("刷新令牌无效或已过期")
  
  if payload.type != "refresh":
    return Result.un_authorized("令牌类型错误")
  
  stored = await adapter.get_refresh_token(body.refresh_token)
  if stored is None or stored.revoked:
    # 直接根据family_id吊销所有关联token
    if stored and stored.family_id:
      await adapter.revoke_refresh_token_family(stored.family_id)
    return Result.un_authorized("刷新令牌已被吊销")
  
  user = await adapter.get_user_by_id(payload.sub)
  if not user or not user.is_active:
    return Result.un_authorized("用户不存在或已禁用")
    
  await adapter.revoke_refresh_token(body.refresh_token)
  access, refresh_meta = await generate_token(fullauth=fullauth, user=user)

  return Result.success({
    "access_token": access,
    "refresh_token": refresh_meta.token,
    "token_type": "bearer"
  })

@router.post("/logout")
async def logout(user: CurrentUser, body: RefreshRequest):
  fullauth = _get_fullauth()
  await fullauth.adapter.revoke_refresh_token(body.refresh_token)
  await fullauth.hooks.emit("after_logout", user_id=str(user.id))
  return Result.success(message="已成功登出")

async def generate_token(fullauth: FullAuth[UserSchema, CreateUserSchema], user: UserSchema):
  adapter = fullauth.adapter

  roles = await adapter.get_user_roles(user.id)
  extra = await fullauth.get_custom_claims(user)
  access, refresh_meta = fullauth.token_engine.create_token_pair(
    user_id=str(user.id), roles=roles, extra=extra,
  )

  from fastapi_fullauth.types import RefreshToken as RT

  await adapter.store_refresh_token(
    RT(
      token=access,
      user_id=user.id,
      expires_at=refresh_meta.expires_at,
      family_id=refresh_meta.family_id,
    )
  )
  return (access, refresh_meta)