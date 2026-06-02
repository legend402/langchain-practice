# 认证系统

## 后端认证（fastapi-fullauth）

### 配置（`src/service/auth/auth.py`）

`create_fullauth(session_marker)` 创建 FullAuth 实例：
- JWT 密钥：`FULLAUTH_SECRET_KEY` 环境变量（**必须固定**，否则重启后所有 token 失效）
- Access Token 有效期：30 分钟
- Refresh Token 有效期：30 天，启用轮换（rotation）
- 密码哈希：argon2id，最短 8 位
- 登录字段：email
- Redis 黑名单/限流/锁定
- 登录锁定：5 次失败后锁定 15 分钟
- 限流：登录 5 次/小时，注册 3 次/小时

### 模型（`src/service/auth/auth_models.py`）

| 模型 | 说明 |
|------|------|
| `User(UserMixin, table=True)` | 用户表，含 `user_name` 字段 |
| `RefreshToken(RefreshTokenMixin, table=True)` | 刷新令牌存储 |
| `Role(RoleMixin, table=True)` | 角色表 |
| `UserRole(UserRoleMixin, table=True)` | 用户-角色关联 |
| `AppUserSchema(UserSchema)` | Pydantic schema，**含 `user_name: str = ""`** |
| `AppCreateUserSchema(CreateUserSchema)` | 注册 schema，含 `user_name: str = ""` |

**关键：** `AppUserSchema` 必须声明 `user_name` 字段，否则 `_to_schema()` 转换时会丢失该字段。

### 依赖注入（`src/service/auth/deps.py`）

```python
CurrentUser = Annotated[AppUserSchema, Depends(current_user)]
```

`current_user` 依赖解码 JWT → `get_user_by_id` → `_to_schema` 返回 `AppUserSchema`。

### 认证路由（`src/service/routes/auth.py`）

| 端点 | 认证 | 说明 |
|------|------|------|
| GET /auth/public-key | 无 | 获取 RSA 公钥，返回 `{ key_id, public_key(PEM), expires_at }` |
| POST /auth/register | 无 | 注册，返回 access + refresh + user |
| POST /auth/login | 无 | 登录（支持 email 或 user_name），登录失败返回 HTTP 200 + body.code=401 |
| POST /auth/refresh | 无 | 刷新 token（验证 refresh token 有效性，吊销旧的，签发新的） |
| POST /auth/logout | 需认证 | 吊销 refresh token |
| GET /auth/me | 需认证 | 返回当前用户信息 |

所有端点返回 `Result` 包装。

### 密码加密传输（RSA-OAEP）

login/register 的密码字段使用 RSA-OAEP + SHA-256 加密传输，防止明文暴露：
- 后端启动时生成 RSA 2048 密钥对，`key_id` 用 UUID 标识
- 私钥 PEM 序列化后存入 Redis（key: `rsa:key:{key_id}`），TTL 自动过期，多 worker 共享
- 公钥 PEM 从私钥推导，无需单独存储
- 前端通过 `GET /auth/public-key` 获取公钥，Web Crypto API 加密密码
- 请求体中 `password` 字段为 base64 编码的 RSA 密文，附带 `key_id`
- 后端根据 `key_id` 从 Redis 取私钥解密，得到明文后走原有 argon2id 验证逻辑

## 前端认证

### 类型（`frontend/src/types/auth.ts`）

```typescript
AuthUser          // { id, email, user_name, is_active, is_verified }
AuthTokens        // { access_token, refresh_token, token_type }
LoginRequest      // { login, password }
RegisterRequest   // { email, user_name, password }
AuthResponse      // AuthTokens + { user: AuthUser }
ApiResult<T>      // { code, success, result, message }
```

### API 客户端（`frontend/src/api/client/`）

**tokenStorage.ts** — `TokenStorage` 接口 + 两个实现：
- `LocalStorageTokenStorage`：localStorage + access token 内存缓存
- `MemoryTokenStorage`：纯内存，用于测试

**httpClient.ts** — `HttpClient` 类：
- `request<T>()`：标准 JSON 请求，自动解包 `Result` 包装（取 `.result`）
- `stream()`：SSE 请求，经过完整拦截器管道
- `raw()`：绕过拦截器，用于 login/register/refresh
- `get/post/delete`：`request<T>()` 的快捷方法

**authInterceptors.ts** — 拦截器工厂：
- 请求拦截器：注入 `Authorization: Bearer <token>`
- 响应拦截器：401 → 尝试 refresh → 重发原始请求（带并发去重）

### 密码加密（`frontend/src/api/passwordCrypto.ts`）

`encryptPassword(password)` — 使用 Web Crypto API（零依赖）：
- `fetchPublicKey()`：从后端获取 RSA 公钥，内存缓存，过期前 5 分钟自动刷新
- 用 `httpClient.raw()` 发起请求，复用 URL 解析
- 返回 `{ encrypted: string(base64密文), key_id: string }`

### Auth API（`frontend/src/api/authApi.ts`）

| 方法 | HTTP 方法 | 使用方式 |
|------|-----------|----------|
| `login(data)` | POST /auth/login | `raw()` + RSA 加密密码 |
| `register(data)` | POST /auth/register | `raw()` + RSA 加密密码 |
| `refresh()` | POST /auth/refresh | `raw()`（避免循环刷新） |
| `logout()` | POST /auth/logout | `post()`（经过拦截器） |
| `getMe()` | GET /auth/me | `get()`（经过拦截器） |

### Auth Hook（`frontend/src/hooks/useAuth.tsx`）

`AuthProvider` + `useAuth()`：
- 初始化流程：检查 token → getMe → 失败则 refresh → 再 getMe
- 提供 `login/register/logout` 方法
- `ProtectedRoute` 检测 `user === null` 时重定向 `/login`
- logout 后 `user` 变为 null，`ProtectedRoute` 自动重定向

## 常见问题

1. **重启后 token 全部失效** — `.env` 未配置 `FULLAUTH_SECRET_KEY`，每次启动随机生成新密钥
2. **user_name 为空** — `AppUserSchema` 未声明 `user_name` 字段（已修复）
3. **登录失败返回 200** — 后端用 body 中 `code: 401` 而非 HTTP 401，前端需检查 `body.success`
