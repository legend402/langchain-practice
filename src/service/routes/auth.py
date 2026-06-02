import base64
import time
from uuid import uuid4
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding as asym_padding
from fastapi import APIRouter
from fastapi_fullauth import CreateUserSchema, FullAuth, UserSchema
from pydantic import BaseModel, EmailStr

from src.service.auth.deps import CurrentUser
from src.service.db.redis import get_redis
from src.service.result import Result

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    login: str
    password: str
    key_id: str


class RegisterRequest(BaseModel):
    email: EmailStr
    user_name: str
    password: str
    key_id: str


class RefreshRequest(BaseModel):
    refresh_token: str


def _is_email(value: str):
    return "@" in value


def _get_fullauth() -> FullAuth[UserSchema, CreateUserSchema]:
    from src.service import get_app

    return get_app().state.fullauth


@router.post("/register")
async def register(body: RegisterRequest):
    # 解密密码
    redis = get_redis()
    private_pem = await redis.get(f"rsa:key:{body.key_id}")
    if not private_pem:
        return Result.error("密钥已过期，请刷新页面")
    
    private_key = serialization.load_pem_private_key(
        private_pem.encode(), password=None
    )
    try:
        password = private_key.decrypt(
            base64.b64decode(body.password),
            asym_padding.OAEP(
                mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        ).decode()
    except:
        return Result.error("密码解密失败")

    fullauth = _get_fullauth()
    adapter = fullauth.adapter

    from fastapi_fullauth.flows.register import register as do_register

    schema = adapter._create_user_schema(
        email=body.email, password=password, user_name=body.user_name
    )
    user = await do_register(
        adapter=adapter,
        data=schema,
        hash_algorithm=fullauth.config.PASSWORD_HASH_ALGORITHM,
        password_validator=fullauth.password_validator,
    )

    access, refresh_meta = await generate_token(fullauth=fullauth, user=user)

    await fullauth.hooks.emit("after_register", user=user)

    return Result.success(
        {
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
        }
    )


@router.post("/login")
async def login(body: LoginRequest):
    # 解密密码
    redis = get_redis()
    private_pem = await redis.get(f"rsa:key:{body.key_id}")
    if not private_pem:
        return Result.error("密钥已过期，请刷新页面")
    
    private_key = serialization.load_pem_private_key(
        private_pem.encode(), password=None
    )
    try:
        password = private_key.decrypt(
            base64.b64decode(body.password),
            asym_padding.OAEP(
                mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        ).decode()
    except:
        return Result.error("密码解密失败")
    
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

    if not verify_password(password, hashed):
        return Result.un_authorized("用户名或密码错误")

    if not user.is_active:
        return Result.un_authorized("账号已被禁用")

    access, refresh_meta = await generate_token(fullauth=fullauth, user=user)

    await fullauth.hooks.emit("after_login", user=user)

    return Result.success(
        {
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
        }
    )


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

    return Result.success(
        {
            "access_token": access,
            "refresh_token": refresh_meta.token,
            "token_type": "bearer",
        }
    )


@router.post("/logout")
async def logout(user: CurrentUser, body: RefreshRequest):
    fullauth = _get_fullauth()
    await fullauth.adapter.revoke_refresh_token(body.refresh_token)
    await fullauth.hooks.emit("after_logout", user_id=str(user.id))
    return Result.success(message="已成功登出")


@router.get("/me")
def me(user: CurrentUser):
    print(user)
    return Result.success(
        {
            "id": str(user.id),
            "email": user.email,
            "user_name": getattr(user, "user_name", ""),
            "is_active": user.is_active,
            "is_verified": user.is_verified,
        }
    )

@router.get("/public-key")
async def public_key():
    redis = get_redis()
    # 遍历已有的密钥，找到未过期的直接返回
    async for key in redis.scan_iter("rsa:key:*"):
        ttl = await redis.ttl(key)
        if ttl and ttl > 300: 
            key_id = key.split(":")[-1]
            private_pem = await redis.get(key)
            private_key = serialization.load_pem_private_key(
                private_pem.encode(), password=None
            )
            public_pem = private_key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            return Result.success({
                "public_key": public_pem,
                "key_id": key_id,
                "expires_at": int(time.time()) + ttl,
            })
    # 生成密钥对
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    uuid = str(uuid4())
    ttl = 3600
    await redis.set(f"rsa:key:${uuid}", private_pem, ex=ttl)

    return Result.success({
        "public_key": public_pem,
        "key_id": uuid,
        "expired_at": int(time.time()) + ttl
    })

async def generate_token(
    fullauth: FullAuth[UserSchema, CreateUserSchema], user: UserSchema
):
    adapter = fullauth.adapter

    roles = await adapter.get_user_roles(user.id)
    extra = await fullauth.get_custom_claims(user)
    access, refresh_meta = fullauth.token_engine.create_token_pair(
        user_id=str(user.id),
        roles=roles,
        extra=extra,
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
    return (access, refresh_meta)
