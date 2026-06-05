# 宝塔面板部署指南

本文档介绍如何在宝塔面板（BT Panel）上部署知识研究助手项目（FastAPI 后端 + React 前端）。

---

## 目录

1. [服务器基础环境](#1-服务器基础环境)
2. [安装依赖服务](#2-安装依赖服务)
3. [部署后端](#3-部署后端)
4. [部署前端](#4-部署前端)
5. [Nginx 反向代理配置](#5-nginx-反向代理配置)
6. [SSL 证书（可选）](#6-ssl-证书可选)
7. [常见问题](#7-常见问题)

---

## 1. 服务器基础环境

### 推荐配置

| 项目 | 最低要求 | 推荐配置 |
|------|---------|---------|
| 系统 | Ubuntu 20.04 / CentOS 7+ | Ubuntu 22.04 |
| CPU | 2 核 | 4 核 |
| 内存 | 4 GB | 8 GB |
| 磁盘 | 40 GB | 80 GB SSD |

### 安装宝塔面板

```bash
# Ubuntu/Debian
curl -sSO https://raw.githubusercontent.com/zhucaidan/btpanel-v7.7.0/main/install/install_panel.sh && bash install_panel.sh

# CentOS
yum install -y wget && wget -O install.sh https://raw.githubusercontent.com/zhucaidan/btpanel-v7.7.0/main/install/install_panel.sh && sh install.sh
```

安装完成后记录面板地址、用户名和密码。

### 通过宝塔面板安装基础软件

在宝塔「软件商店」中安装：

- **Nginx** 1.24+
- **Python 项目管理器**（或手动安装 Python 3.11+）
- **PostgreSQL** 14+
- **Redis** 7+

---

## 2. 安装依赖服务

### 2.1 PostgreSQL

1. 宝塔「软件商店」安装 PostgreSQL
2. 通过宝塔「数据库」菜单添加数据库：
   - 数据库名：`knowledge_agent`
   - 用户名：`knowledge_agent`
   - 密码：自行设置强密码
3. 记录连接串，格式为：

```
postgresql://knowledge_agent:你的密码@127.0.0.1:5432/knowledge_agent
```

### 2.2 Redis

1. 宝塔「软件商店」安装 Redis
2. 在 Redis 配置中设置密码（推荐）
3. 记录连接地址：

```
redis://:你的密码@127.0.0.1:6379/0
```

### 2.3 Milvus

Milvus 推荐使用 Docker 部署。

**安装 Docker**（宝塔「软件商店」→ Docker管理器）。

**方式一：Docker Standalone**

```bash
# 拉取 Milvus 镜像
docker pull milvusdb/milvus:v2.4-latest

# 创建数据目录
mkdir -p /opt/milvus/data

# 启动 Milvus Standalone
docker run -d \
  --name milvus-standalone \
  -p 19530:19530 \
  -p 9091:9091 \
  -v /opt/milvus/data:/var/lib/milvus \
  --restart=always \
  milvusdb/milvus:v2.4-latest
```

**方式二：Docker Compose（推荐生产环境）**

```bash
# 下载 docker-compose 配置
mkdir -p /opt/milvus && cd /opt/milvus
wget https://github.com/milvus-io/milvus/releases/download/v2.4.17/milvus-standalone-docker-compose.yml -O docker-compose.yml

# 启动
docker compose up -d
```

验证 Milvus 是否运行：

```bash
docker ps | grep milvus
```

---

## 3. 部署后端

### 3.1 上传代码

将项目代码上传至服务器，假设路径为 `/www/wwwroot/knowledge-agent`。

方式选择：
- **Git 拉取**（推荐）：在宝塔「终端」中 `git clone` 项目
- **宝塔文件管理器**：上传 zip 压缩包后解压

### 3.2 创建 Python 虚拟环境

```bash
cd /www/wwwroot/knowledge-agent

# 创建虚拟环境
python3.11 -m venv .venv

# 激活虚拟环境
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 3.3 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填写实际值：

```env
# LLM 配置
DEEPSEEK_API_KEY=你的DeepSeek密钥
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
LLM_API_KEY=你的DeepSeek密钥

# 搜索 API
TAVILY_API_KEY=你的Tavily密钥

# 向量数据库
MILVUS_URI=http://127.0.0.1:19530

# Embedding
ZHIPU_API_KEY=你的智谱API密钥

# 文件上传目录
UPLOAD_DIR=/www/wwwroot/knowledge-agent/uploads

# Redis
REDIS_URL=redis://:你的Redis密码@127.0.0.1:6379/0

# JWT 密钥（必须 >= 32 字节，生产环境请使用随机强密钥）
FULLAUTH_SECRET_KEY=你的随机密钥至少32字节长度请使用openssl生成

# PostgreSQL
PGSQL_DB_URI="postgresql://knowledge_agent:你的密码@127.0.0.1:5432/knowledge_agent?sslmode=disable"
```

生成随机密钥：

```bash
openssl rand -hex 32
```

### 3.4 创建上传目录

```bash
mkdir -p /www/wwwroot/knowledge-agent/uploads
chmod 755 /www/wwwroot/knowledge-agent/uploads
```

### 3.5 配置进程守护

**方式一：使用宝塔「Python 项目管理器」**

1. 在宝塔「软件商店」安装「Python 项目管理器」
2. 添加项目：
   - 项目名称：`knowledge-agent`
   - 项目路径：`/www/wwwroot/knowledge-agent`
   - Python 版本：3.11
   - 框架：`FastAPI`
   - 启动文件：`src/service/__init__.py` 或启动命令：
     ```
     /www/wwwroot/knowledge-agent/.venv/bin/uvicorn src.service:app --host 0.0.0.0 --port 4030
     ```
   - 勾选「开机启动」

**方式二：使用 Systemd 服务（推荐）**

创建服务文件 `/etc/systemd/system/knowledge-agent.service`：

```ini
[Unit]
Description=Knowledge Research Agent
After=network.target postgresql.service redis.service docker.service

[Service]
Type=simple
User=www
Group=www
WorkingDirectory=/www/wwwroot/knowledge-agent
ExecStart=/www/wwwroot/knowledge-agent/.venv/bin/uvicorn src.service:app --host 127.0.0.1 --port 4030 --workers 2
Restart=always
RestartSec=5
Environment=PATH=/www/wwwroot/knowledge-agent/.venv/bin:/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=multi-user.target
```

> **注意：** 使用 `--reload` 仅用于开发环境，生产环境请使用 `--workers N`（N 为 CPU 核心数）。

启动并设置开机自启：

```bash
systemctl daemon-reload
systemctl enable knowledge-agent
systemctl start knowledge-agent

# 查看状态
systemctl status knowledge-agent

# 查看日志
journalctl -u knowledge-agent -f
```

验证后端是否正常：

```bash
curl http://127.0.0.1:4030/docs
```

---

## 4. 部署前端

### 4.1 修改 API 地址

编辑 `frontend/src/api/client/httpClient.ts`，将 `BASE_URL` 改为实际后端地址：

```typescript
// 生产环境：使用相对路径，由 Nginx 反向代理处理
const BASE_URL = "";

// 或者指定完整域名
const BASE_URL = "https://你的域名/api";
```

> **推荐使用空字符串 + Nginx 反向代理**，避免跨域问题。

### 4.2 构建前端

在本地或服务器上执行：

```bash
cd /www/wwwroot/knowledge-agent/frontend

# 安装 Node.js（通过宝塔或 nvm）
# 推荐使用 Node.js 20+

# 安装依赖
npm install

# 构建
npm run build
```

构建产物在 `frontend/dist/` 目录中。

### 4.3 部署静态文件

将构建产物放到 Nginx 可访问的目录：

```bash
cp -r /www/wwwroot/knowledge-agent/frontend/dist /www/wwwroot/knowledge-agent-web
```

---

## 5. Nginx 反向代理配置

在宝塔「网站」中添加站点：

- 域名：填写你的域名（如 `ai.example.com`）
- 根目录：`/www/wwwroot/knowledge-agent-web`
- PHP 版本：纯静态

添加站点后，点击「设置」→「配置文件」，替换为以下配置：

```nginx
server {
    listen 80;
    server_name ai.example.com;

    # 前端静态文件
    root /www/wwwroot/knowledge-agent-web;
    index index.html;

    # 前端 SPA 路由（所有非文件请求回退到 index.html）
    location / {
        try_files $uri $uri/ /index.html;
    }

    # 后端 API 反向代理
    location /api/v1/ {
        proxy_pass http://127.0.0.1:4030;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 聊天 API 反向代理
    location /chat/ {
        proxy_pass http://127.0.0.1:4030;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 上传 API 反向代理
    location /upload/ {
        proxy_pass http://127.0.0.1:4030;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 文件上传大小限制（根据需要调整）
        client_max_body_size 50m;
    }

    # 知识库 API 反向代理
    location /knowledge/ {
        proxy_pass http://127.0.0.1:4030;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # SSE 流式接口 - 需要特殊配置
    location ~ ^/chat/start {
        proxy_pass http://127.0.0.1:4030;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE 关键配置
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
        chunked_transfer_encoding on;
    }

    # 静态资源缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # 禁止访问隐藏文件
    location ~ /\. {
        deny all;
    }

    access_log /www/wwwlogs/knowledge-agent.log;
    error_log /www/wwwlogs/knowledge-agent.error.log;
}
```

> **关键说明：** 前端 `httpClient.ts` 中 `BASE_URL` 需改为空字符串 `""`，使所有 API 请求都走相对路径，由 Nginx 代理转发到后端。

---

## 6. SSL 证书（可选）

1. 在宝塔「网站」→ 点击站点「设置」→「SSL」
2. 选择「Let's Encrypt」，勾选域名，申请免费证书
3. 开启「强制 HTTPS」

---

## 7. 常见问题

### 后端启动失败，报数据库连接错误

- 检查 PostgreSQL 是否运行：`systemctl status postgresql`
- 检查 `.env` 中 `PGSQL_DB_URI` 格式是否正确
- 确认数据库用户有权限访问对应数据库
- 首次启动会自动建表（`init_db`），确保数据库已创建

### Milvus 连接失败

- 检查 Docker 容器是否运行：`docker ps | grep milvus`
- 检查端口 19530 是否开放：`curl http://127.0.0.1:19530/healthz`
- 检查 `.env` 中 `MILVUS_URI` 是否正确

### SSE 流式响应中断

- 确认 Nginx 中 SSE location 段配置了 `proxy_buffering off`
- 检查 `proxy_read_timeout` 是否足够长（建议 300s+）
- 检查 Cloudflare 等 CDN 是否开启了缓冲（如使用 CDN 需关闭响应缓冲）

### 前端页面空白或 404

- 确认 Nginx 配置了 `try_files $uri $uri/ /index.html`
- 确认 `dist/` 目录中文件完整
- 检查浏览器控制台网络请求，确认 API 路径正确

### 文件上传失败

- 确认 `UPLOAD_DIR` 目录存在且有写权限
- 确认 Nginx 配置中 `client_max_body_size` 足够大
- 检查文件格式是否在支持列表中（.txt, .md, .html, .pdf, .docx）

### Redis 连接失败

- 检查 Redis 是否运行：`systemctl status redis`
- 如果设置了密码，确认 `REDIS_URL` 格式为 `redis://:密码@127.0.0.1:6379/0`

---

## 服务端口总览

| 服务 | 端口 | 说明 |
|------|------|------|
| Nginx | 80 / 443 | 对外服务 |
| FastAPI | 4030 | 仅监听 127.0.0.1 |
| PostgreSQL | 5432 | 仅监听 127.0.0.1 |
| Redis | 6379 | 仅监听 127.0.0.1 |
| Milvus | 19530 | 仅监听 127.0.0.1 |

> **安全建议：** 所有内部服务仅监听 `127.0.0.1`，仅通过 Nginx 暴露 80/443 端口。在宝塔「安全」菜单中确认防火墙只开放了 80、443 和宝塔面板端口。
