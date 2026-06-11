# Docker 容器化部署实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为知识研究助手项目创建完整的 Docker 容器化部署方案，包含多阶段构建的 Dockerfile、Nginx 反向代理、以及编排所有服务的 docker-compose.yml。

**Architecture:** 单 Dockerfile 多阶段构建：Stage 1 用 Node 20 构建前端静态文件，Stage 2 用 Python 3.13-slim 运行后端。最终镜像内 Nginx 作为反向代理（端口 6020），同时通过 supervisord 管理 uvicorn（端口 7900）。docker-compose 编排 app + PostgreSQL + Redis + Milvus（含 etcd + minio）六个服务。

**Tech Stack:** Docker multi-stage build, Nginx, supervisord, Python 3.13, Node 20, PostgreSQL 16, Redis 7, Milvus v2.4

---

## 文件结构

| 操作 | 文件路径 | 职责 |
|------|----------|------|
| 创建 | `.dockerignore` | 排除不需要进入镜像的文件 |
| 创建 | `Dockerfile` | 多阶段构建：前端编译 → 后端运行 |
| 创建 | `docker/nginx/nginx.conf` | Nginx 反向代理配置，含 SSE 和文件上传支持 |
| 创建 | `docker/supervisord.conf` | 进程管理：nginx + uvicorn |
| 创建 | `docker-compose.yml` | 编排 app、PostgreSQL、Redis、Milvus |
| 创建 | `.env.docker` | Docker 环境变量模板 |

**无需修改代码：** 前端 `httpClient.ts:1` 使用 `??` 运算符，`VITE_API_BASE_URL=""` 时 `BASE_URL` 为空字符串，请求自动走相对路径（同源 Nginx），无需改动。

---

### Task 1: 创建 `.dockerignore`

**Files:**
- Create: `.dockerignore`

- [ ] **Step 1: 创建 `.dockerignore` 文件**

```
.git
.gitignore
.venv
venv
__pycache__
*.pyc
*.pyo
.env
.env.local
node_modules
frontend/node_modules
frontend/dist
uploads
docs
*.md
.opencode
.vscode
.idea
test.py
loop_win.py
servers_config.json
```

- [ ] **Step 2: 提交**

```bash
git add .dockerignore
git commit -m "chore: 添加 .dockerignore 文件"
```

---

### Task 2: 创建 Nginx 配置文件

**Files:**
- Create: `docker/nginx/nginx.conf`

- [ ] **Step 1: 创建 `docker/nginx/` 目录并编写配置**

```nginx
# docker/nginx/nginx.conf

worker_processes auto;
pid /tmp/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    sendfile        on;
    keepalive_timeout  65;
    client_max_body_size 50m;

    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
    gzip_min_length 1000;

    server {
        listen 6020;
        server_name _;

        root /www/wwwroot/hanyj/web/langchain-practice/frontend/dist;
        index index.html;

        location ~ ^/(api/|chat/|knowledge/|upload/) {
            proxy_pass http://127.0.0.1:7900;
            proxy_http_version 1.1;

            proxy_set_header Host              $host;
            proxy_set_header X-Real-IP         $remote_addr;
            proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            proxy_set_header Connection '';
            proxy_buffering off;
            chunked_transfer_encoding off;
            proxy_read_timeout 3600s;
        }

        location / {
            try_files $uri $uri/ /index.html;
        }
    }
}
```

- [ ] **Step 2: 提交**

```bash
git add docker/nginx/nginx.conf
git commit -m "feat: 添加 Nginx 反向代理配置（含 SSE 和文件上传支持）"
```

---

### Task 3: 创建 Supervisord 配置

**Files:**
- Create: `docker/supervisord.conf`

- [ ] **Step 1: 创建 supervisord 配置**

```ini
; docker/supervisord.conf
[supervisord]
nodaemon=true
logfile=/tmp/supervisord.log
pidfile=/tmp/supervisord.pid

[program:nginx]
command=nginx -g "daemon off;"
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:uvicorn]
command=uvicorn src.service:app --host 127.0.0.1 --port 7900 --workers 2
directory=/www/wwwroot/hanyj/web/langchain-practice
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
environment=PYTHONUNBUFFERED="1"
```

- [ ] **Step 2: 提交**

```bash
git add docker/supervisord.conf
git commit -m "feat: 添加 supervisord 进程管理配置"
```

---

### Task 4: 创建 Dockerfile

**Files:**
- Create: `Dockerfile`

- [ ] **Step 1: 创建多阶段 Dockerfile**

```dockerfile
# ============================
# Stage 1: 构建前端
# ============================
FROM node:20-slim AS frontend-build

WORKDIR /build

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build


# ============================
# Stage 2: 生产运行镜像
# ============================
FROM python:3.13-slim AS production

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /www/wwwroot/hanyj/web/langchain-practice

RUN apt-get update && \
    apt-get install -y --no-install-recommends nginx supervisor && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

COPY --from=frontend-build /build/dist ./frontend/dist

COPY docker/nginx/nginx.conf /etc/nginx/nginx.conf
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

RUN mkdir -p /www/wwwroot/hanyj/web/langchain-practice/uploads

EXPOSE 6020

CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
```

- [ ] **Step 2: 提交**

```bash
git add Dockerfile
git commit -m "feat: 添加多阶段 Dockerfile（Node 前端构建 + Python 后端运行）"
```

---

### Task 5: 创建 `.env.docker` 环境变量模板

**Files:**
- Create: `.env.docker`

- [ ] **Step 1: 创建 Docker 环境变量模板**

```env
# ===== 外部 API 密钥 =====
DEEPSEEK_API_KEY=your_deepseek_api_key
TAVILY_API_KEY=your_tavily_api_key
LLM_API_KEY=your_llm_api_key
ZHIPU_API_KEY=your_zhipu_api_key

# ===== LLM 配置 =====
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash

# ===== 数据库（docker-compose 内部网络，使用服务名） =====
PGSQL_DB_URI=postgresql://postgres:postgres123@postgres:5432/postgres?sslmode=disable

# ===== Redis（docker-compose 内部网络） =====
REDIS_URL=redis://redis:6379/0

# ===== Milvus（docker-compose 内部网络） =====
MILVUS_URI=http://milvus:19530

# ===== 认证 =====
FULLAUTH_SECRET_KEY=change-me-to-a-secret-at-least-32-bytes-long

# ===== 上传目录（容器内路径） =====
UPLOAD_DIR=/www/wwwroot/hanyj/web/langchain-practice/uploads
```

- [ ] **Step 2: 提交**

```bash
git add .env.docker
git commit -m "chore: 添加 Docker 环境变量模板"
```

---

### Task 6: 创建 `docker-compose.yml`

**Files:**
- Create: `docker-compose.yml`

- [ ] **Step 1: 创建 docker-compose 编排文件**

```yaml
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "6020:6020"
    env_file:
      - .env.docker
    volumes:
      - upload_data:/www/wwwroot/hanyj/web/langchain-practice/uploads
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      milvus:
        condition: service_started
    restart: unless-stopped

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres123
      POSTGRES_DB: postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  milvus:
    image: milvusdb/milvus:v2.4.17
    ports:
      - "19530:19530"
      - "9091:9091"
    volumes:
      - milvus_data:/var/lib/milvus
    environment:
      ETCD_ENDPOINTS: etcd:2379
      MINIO_ADDRESS: minio:9000
    depends_on:
      - etcd
      - minio
    restart: unless-stopped

  etcd:
    image: quay.io/coreos/etcd:v3.5.18
    environment:
      ETCD_AUTO_COMPACTION_MODE: revision
      ETCD_AUTO_COMPACTION_RETENTION: "1000"
      ETCD_QUOTA_BACKEND_BYTES: "4294967296"
      ETCD_SNAPSHOT_COUNT: "50000"
    volumes:
      - etcd_data:/etcd
    command:
      - etcd
      - --advertise-client-urls=http://127.0.0.1:2379
      - --listen-client-urls=http://0.0.0.0:2379
      - --data-dir=/etcd
    healthcheck:
      test: ["CMD", "etcdctl", "endpoint", "health"]
      interval: 30s
      timeout: 20s
      retries: 3
    restart: unless-stopped

  minio:
    image: minio/minio:RELEASE.2024-09-22T00-33-43Z
    environment:
      MINIO_ACCESS_KEY: minioadmin
      MINIO_SECRET_KEY: minioadmin
    volumes:
      - minio_data:/minio_data
    command: minio server /minio_data --console-address ":9001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  milvus_data:
  etcd_data:
  minio_data:
  upload_data:
```

- [ ] **Step 2: 提交**

```bash
git add docker-compose.yml
git commit -m "feat: 添加 docker-compose.yml 编排全部服务"
```

---

### Task 7: 验证构建与运行

- [ ] **Step 1: 构建 Docker 镜像**

```bash
docker compose build
```

预期：镜像成功构建，无报错。

- [ ] **Step 2: 启动全部服务**

```bash
docker compose up -d
```

预期：所有容器启动成功。

- [ ] **Step 3: 检查服务状态**

```bash
docker compose ps
```

预期：所有服务状态为 `Up` 或 `healthy`。

- [ ] **Step 4: 验证前端页面**

浏览器访问 `http://localhost:6020`，预期看到前端登录页面。

- [ ] **Step 5: 验证 API 代理**

```bash
curl http://localhost:6020/api/v1/auth/me
```

预期：返回 401 未授权（说明请求已到达后端）。

- [ ] **Step 6: 查看应用日志**

```bash
docker compose logs -f app
```

预期：看到 uvicorn 启动日志和 nginx 访问日志，无报错。

- [ ] **Step 7: 停止服务**

```bash
docker compose down
```

如需同时清除数据卷（谨慎）：

```bash
docker compose down -v
```
