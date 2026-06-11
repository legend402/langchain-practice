# ============================
# Stage 1: 构建前端
# ============================
FROM node:20-slim AS frontend-build

WORKDIR /build

COPY frontend/package.json frontend/package-lock.json ./
run npm cli

COPY frontend/ ./
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build


# ============================
# Stage 2: 生产运行镜像
# ============================
FROM python:3.13-slim AS production

ENV PYTHONUNBUFFERED=1
    PYTHONDONTWRITEBYTECODE=1
  
WORKDIR /www/wwwroot/hanyj/web/langchain-practice

RUN apt-get update && \
    apt-get install -y --no-install-recommends nginx supervisor && \
    rm -rf /var/lib/apt/lists/*

COPY src/ ./src/
COPY --from=frontend-build /build/dist ./frontend/dist

COPY docker/nginx