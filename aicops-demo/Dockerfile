# AICloudOps — 多阶段构建
# Stage 1: 前端构建
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile
COPY frontend/ .
RUN pnpm build

# Stage 2: 后端运行
FROM python:3.11-slim AS production
LABEL maintainer="AICloudOps Team"
LABEL description="面向麒麟操作系统的安全智能运维 Agent"

# 不生成 .pyc，stdout 直接输出（12-Factor）
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    APP_DEBUG=false

WORKDIR /app

# 系统依赖（psutil 编译需要 gcc）
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖（利用缓存层）
COPY pyproject.toml ./
RUN pip install --no-cache-dir . && \
    pip install --no-cache-dir gunicorn

# 复制后端源码
COPY backend/ backend/
COPY config/ config/

# 从前端构建阶段复制产物
COPY --from=frontend-build /app/frontend/dist frontend/dist

# 数据目录
RUN mkdir -p data/backups logs

# 非 root 用户运行
RUN useradd -r -s /sbin/nologin safeops && \
    chown -R safeops:safeops /app
USER safeops

EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import httpx; r=httpx.get('http://localhost:8000/api/v1/health'); exit(0 if r.status_code==200 else 1)"

CMD ["gunicorn", "backend.main:app", \
     "-w", "4", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "-b", "0.0.0.0:8000", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
