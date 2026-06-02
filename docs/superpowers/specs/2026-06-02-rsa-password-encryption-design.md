# RSA 密码加密传输设计

## 目标

对前端登录/注册时的密码进行 RSA 非对称加密传输，防止密码明文在网络上暴露（即使 HTTPS 被中间人代理也无法获取明文密码）。

## 技术选型

- 加密算法：RSA-OAEP + SHA-256
- 密钥长度：2048 bit
- 前端：浏览器原生 `crypto.subtle` API（零依赖）
- 后端：Python `cryptography` 库
- 密钥存储：Redis（多 worker 共享，TTL 自动过期）

## 整体流程

```
前端                                    后端
  │                                       │
  │  GET /api/v1/auth/public-key          │
  │  ──────────────────────────────────>  │
  │  <──────────────────────────────────  │  { key_id, public_key(PEM), expires_at }
  │                                       │
  │  导入 PEM → crypto.subtle 加密密码    │
  │  = encrypted_password (base64)        │
  │                                       │
  │  POST /api/v1/auth/login              │
  │  { login, password(密文), key_id }    │
  │  ──────────────────────────────────>  │
  │                                       │  key_id 从 Redis 取私钥 → RSA-OAEP 解密
  │                                       │  得到明文 → 原有 argon2id 验证
  │  <──────────────────────────────────  │
```

## 后端接口规范

### 1. 获取公钥

`GET /api/v1/auth/public-key`

响应：
```json
{
  "code": 200,
  "success": true,
  "result": {
    "key_id": "uuid-string",
    "public_key": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----",
    "expires_at": "2026-06-02T12:00:00Z"
  },
  "message": "操作成功"
}
```

### 2. 密钥管理（Redis）

- 启动时检查 Redis 是否已有密钥，无则生成 RSA 2048 密钥对
- `key_id` 用 UUID 标识，私钥 PEM 序列化后存入 Redis
- Redis key 格式：`rsa:key:{key_id}` → 私钥 PEM 字符串
- TTL 与 `expires_at` 一致（如 1 小时），过期自动删除
- 公钥 PEM 可从私钥实时推导，无需单独存储
- 密钥轮换：生成新密钥对后旧密钥依靠 TTL 自然过期，过渡期内新旧 key_id 都能解密
- 多 worker 共享同一 Redis，无需担心密钥不一致

### 3. 请求体变更

**Login**（增加 `key_id`，`password` 变为 base64 密文）：
```json
{ "login": "user@example.com", "password": "base64_rsa_ciphertext...", "key_id": "uuid" }
```

**Register**（同理）：
```json
{ "email": "user@example.com", "user_name": "alice", "password": "base64_rsa_ciphertext...", "key_id": "uuid" }
```

### 4. 后端解密流程

在 login/register 路由中：
1. 根据 `key_id` 从 Redis 查找对应私钥（`rsa:key:{key_id}`）
2. 找不到 → 返回 400（`key_id` 无效或已过期）
3. 反序列化私钥，用 `RSA-OAEP + SHA-256` 解密 base64 密文，得到明文密码
4. 走原有 argon2id 验证/注册逻辑

## 前端实现

### 1. 新增文件：`frontend/src/api/passwordCrypto.ts`

- `fetchPublicKey()` — 获取公钥并缓存到内存，过期前 5 分钟自动刷新
- `encryptPassword(password: string)` — RSA-OAEP 加密，返回 `{ encrypted: string, key_id: string }`
- 使用 `httpClient.raw()` 发起请求
- 使用 `crypto.subtle.importKey` 导入 PEM 公钥
- 使用 `crypto.subtle.encrypt` 加密

### 2. 修改文件：`frontend/src/api/authApi.ts`

- login/register 方法中，发送请求前先调用 `encryptPassword` 加密密码
- 请求体中 `password` 替换为密文，附带 `key_id`

## 错误处理

| 场景 | 前端行为 | 后端行为 |
|------|---------|---------|
| 公钥获取失败 | 抛出错误，页面提示刷新 | - |
| key_id 过期/无效 | 收到 400 后重新获取公钥重试 | 返回 400 |
| 密文损坏 | 同上 | 解密失败返回 400 |

## 安全性说明

- 私钥存储在 Redis 中，TTL 到期自动销毁，不持久化到磁盘
- RSA-OAEP 带 OAEP padding，防 chosen-ciphertext 攻击
- 密钥轮换机制确保长期安全
- 不影响现有密码存储（argon2id hash）逻辑
