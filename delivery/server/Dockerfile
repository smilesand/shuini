# =============================================================================
# 交付①：Web/服务端一体化镜像（Debian / Linux 容器）
# -----------------------------------------------------------------------------
# 阶段一：Node 构建前端静态文件（同源访问 /api）
# 阶段二：Python + uvicorn 运行后端，并直接托管前端静态资源
#
# 构建上下文必须为「项目根目录」：
#   docker build -f delivery/server/Dockerfile -t wtcmd-web:latest .
# =============================================================================

# ── 阶段一：构建前端 ─────────────────────────────────────────────────────────
FROM node:20-bookworm AS frontend

WORKDIR /app/frontend

# 先装依赖以利用缓存
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# 复制前端源码并构建
COPY frontend/ ./
# 覆盖 .env.production 中写死的公网地址，改为「同源 /api」，
# 使前端请求发往容器所在主机自身，客户无需改任何地址。
RUN printf 'VITE_API_BASE=/api\n' > .env.production.local \
    && npm run build:web

# ── 阶段二：Python 运行时 ────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    SC_HOST=0.0.0.0 \
    SC_PORT=8000 \
    SC_EDITION=web \
    SC_FRONTEND_DIST=/app/frontend-dist \
    SC_DB_PATH=/data/data.db \
    SC_LOG_DIR=/data/logs

WORKDIR /app

# 安装后端依赖（numpy/scipy/cryptography 等均有 manylinux 预编译轮子，无需编译器）
COPY backend/requirements.txt ./
RUN pip install -r requirements.txt

# 复制后端源码
COPY backend/ ./

# 复制阶段一构建出的前端静态资源
COPY --from=frontend /app/frontend/dist ./frontend-dist

# 数据与日志目录（挂载卷持久化）
RUN mkdir -p /data/logs
VOLUME ["/data"]

EXPOSE 8000

# 健康检查：根路径应返回前端页面
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/', timeout=3).status==200 else 1)" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
