FROM node:22-alpine AS builder

WORKDIR /app

# 启用 corepack 并安装 pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

# 设置 pnpm 配置
RUN pnpm config set registry https://registry.npmmirror.com && \
    pnpm config set store-dir /root/.pnpm-store

# 分层复制依赖文件和配置文件
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml turbo.json ./
COPY apps/web-antd/package.json apps/web-antd/
COPY packages/ packages/
COPY internal/ internal/

# 安装依赖
RUN pnpm install --frozen-lockfile --prefer-offline

# 复制源代码
COPY . .

# 构建应用
RUN pnpm build:antd

# 生产阶段 - 使用更轻量的镜像
FROM joseluisq/static-web-server:2.33-alpine

# 一次性安装所需工具，减少层数
RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.aliyun.com/g' /etc/apk/repositories && \
    apk add --no-cache jq && \
    rm -rf /var/cache/apk/*

# 复制脚本文件
COPY scripts/deploy/update-config.sh /update-config.sh
COPY scripts/deploy/docker-entrypoint.sh /docker-entrypoint.sh

# 设置执行权限
RUN chmod +x /update-config.sh /docker-entrypoint.sh

# 复制构建产物
COPY --from=builder /app/apps/web-antd/dist /public

ENTRYPOINT ["/docker-entrypoint.sh"]
