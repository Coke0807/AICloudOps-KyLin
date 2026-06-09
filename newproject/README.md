# AICloudOps 项目启动指南

## 项目概述

AICloudOps 是一个面向麒麟操作系统的安全智能运维 Agent 平台，采用前后端分离架构：
- **后端**: Python FastAPI (端口 8000)
- **前端**: Vue 3 + Vite (端口 5666)

## 环境要求

- Python >= 3.10
- Node.js >= 20
- pnpm >= 9

## 快速启动

### 1. 启动后端服务

```powershell
# 进入项目根目录
cd d:\User\Desktop\demo\newproject

# 启动 FastAPI 服务
python -m uvicorn backend.main:app --reload --port 8000
```

后端服务将运行在: http://127.0.0.1:8000

### 2. 启动前端服务

```powershell
# 进入前端应用目录
cd d:\User\Desktop\demo\newproject\frontend\apps\web-antd

# 启动 Vite 开发服务器
node "d:\User\Desktop\demo\newproject\frontend\node_modules\vite\bin\vite.js" --mode development
```

前端服务将运行在: http://localhost:5666

## 常见问题与解决方案

### 问题1: 前端页面空白 (404 Not Found)

**原因**: 未在正确的工作目录启动前端服务

**解决**: 确保在 `frontend/apps/web-antd` 目录下启动 Vite，而不是在项目根目录

### 问题2: PostCSS 插件缺失错误

**错误信息**:
```
Error: Loading PostCSS Plugin failed: Cannot find module 'postcss-antd-fixes'
Error: Loading PostCSS Plugin failed: Cannot find module 'postcss-import'
Error: Loading PostCSS Plugin failed: Cannot find module 'postcss-preset-env'
```

**解决**: 安装缺失的依赖

```powershell
cd d:\User\Desktop\demo\newproject\frontend\apps\web-antd

# 安装 PostCSS 相关依赖
pnpm add -D postcss-antd-fixes
pnpm add -D postcss-import
pnpm add -D postcss-preset-env
```

### 问题3: 端口被占用

**解决**: 查找并终止占用进程

```powershell
# 检查端口占用
netstat -ano | findstr :5666
netstat -ano | findstr :8000

# 终止占用进程 (将 <PID> 替换为实际的进程ID)
taskkill /F /PID <PID>
```

## 服务地址

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端页面 | http://localhost:5666 | 主要用户界面 |
| 后端 API | http://127.0.0.1:8000/api/v1 | REST API 接口 |
| API 文档 | http://127.0.0.1:8000/docs | Swagger 文档 |
| 健康检查 | http://127.0.0.1:8000/api/v1/system/status | 系统状态 |

## 项目结构

```
newproject/
├── backend/                  # Python FastAPI 后端
│   ├── main.py              # 应用入口
│   ├── config.py            # 配置文件
│   ├── api/                 # API 路由
│   ├── core/                # 核心业务逻辑
│   ├── safety/              # 安全护栏系统
│   └── mcp/                 # MCP 工具定义
├── frontend/                 # Vue 3 前端
│   ├── apps/
│   │   └── web-antd/        # 主应用
│   └── packages/            # 共享包
├── data/                     # 数据备份
├── logs/                     # 日志文件
└── scripts/                  # 启动脚本
```

## 环境变量配置

项目使用 `.env` 文件进行配置，主要变量包括：

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| LLM_API_KEY | - | 大模型 API 密钥 |
| LLM_BASE_URL | https://token-plan-cn.xiaomimimo.com/v1 | API 地址 |
| LLM_MODEL | mimo-v2.5 | 模型名称 |
| DATABASE_TYPE | sqlite | 数据库类型 |
| REDIS_URL | redis://localhost:6379/0 | Redis 连接 |

## 注意事项

1. **工作目录**: 启动前端时必须在 `frontend/apps/web-antd` 目录下
2. **依赖安装**: 首次启动前确保已安装所有依赖
3. **端口冲突**: 如遇端口占用，先终止相关进程再启动
4. **热重载**: 后端支持文件变更自动重启 (--reload 参数)

## 停止服务

- **后端**: 在终端按 `Ctrl+C`
- **前端**: 在终端按 `Ctrl+C` 或终止 Node.js 进程

## 技术支持

如有问题，请检查：
1. 各服务日志输出
2. 端口占用情况
3. 环境变量配置
4. 依赖完整性
