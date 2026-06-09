# AICloudOps

## 1. 项目概述
- **项目定位与核心功能**: 面向麒麟操作系统的安全智能运维 Agent 演示项目。核心能力包括环境感知（系统诊断）、安全护栏（高危操作拦截）、抗提示词注入攻击检测。
- **目标用户与使用场景**: 信创生态运维人员、安全审计人员；用于视频录制、功能演示、安全运维场景展示。
- **技术栈与依赖环境**: 
  - 核心语言/版本: Python >=3.10 / TypeScript 5.5 / Node >=20
  - 运行时环境: Uvicorn (ASGI) / Vite 5.4
  - 核心框架: FastAPI 0.110+ / Vue 3.5 + Vben Admin Pro 5.2.2
  - 关键依赖: Pydantic 2.6+ / Ant Design Vue 4.2 / Tailwind CSS 3.4 / Redis 7 / MySQL 8.4
- **快速开始指南**: 
  ```powershell
  # 1. 启动基础设施（Redis + MySQL）
  .\scripts\start-services.ps1  # 选择选项 2
  
  # 2. 初始化演示数据
  python backend\init_demo_data.py
  
  # 3. 启动后端
  python -m uvicorn backend.main:app --reload --port 8000
  
  # 4. 启动前端（另一个终端）
  cd frontend && pnpm dev
  ```

## 2. 目录结构
- **关键目录说明**:
  ```
  backend/                    # FastAPI 后端
  ├── api/routes.py          # 统一路由入口（认证 + 业务）
  ├── core/                  # 核心业务逻辑
  │   ├── agent.py          # AIOpsAgent 主 Agent 类
  │   ├── demo_engine.py    # Demo Mode 演示引擎
  │   └── llm_client.py     # LLM API 客户端
  ├── safety/                # 安全护栏系统（核心亮点）
  │   ├── validator.py      # 输入验证 + 风险评估
  │   ├── sandbox.py        # 命令沙箱执行器
  │   ├── rbac.py           # RBAC 权限控制
  │   └── audit_agent.py    # 审计 Agent
  ├── mcp/tools.py          # 20+ 系统运维工具定义
  ├── database.py           # SQLite 数据库封装（默认）
  ├── database_mysql.py     # MySQL 异步数据库封装
  └── config.py             # 配置管理（pydantic-settings）
  
  frontend/                  # Vue 3 Monorepo 前端
  ├── apps/web-antd/        # 主应用（Ant Design Vue 版本）
  ├── packages/             # 共享包
  │   ├── @core/           # 核心模块（UI Kit、Composables）
  │   ├── effects/         # 业务效果层（权限、请求、布局）
  │   └── utils/           # 工具函数
  └── internal/            # 内部工具（Lint 配置、Vite 配置）
  
  data/backups/             # 配置备份目录（沙箱执行前备份）
  logs/                     # 事件日志 + 追踪日志（JSON 格式）
  scripts/start-services.ps1 # Docker 服务启动脚本
  docker-compose.yml        # Redis + MySQL 服务编排
  ```

- **文件组织方式**: 
  - 后端采用分层架构：API 路由 → 核心业务 → 安全护栏 → MCP 工具
  - 前端采用 Monorepo 架构：pnpm workspace + Turbo 编排
- **配置文件位置**: 
  - 后端: `backend/config.py`（pydantic-settings，支持 `.env` 注入）
  - 前端: `frontend/apps/web-antd/.env.development`
  - Docker: 根目录 `.env`（从 `.env.example` 复制）
- **资源文件位置**: 
  - 初始化脚本: `backend/init-scripts/01-init.sql`
  - 演示数据: `backend/init_demo_data.py`

## 3. 开发规范
- **代码风格与格式要求**: 
  - Python: 遵循 PEP 8，使用 `snake_case` 命名函数/变量
  - TypeScript: ESLint 9 Flat Config，使用 `kebab-case` 命名文件
  - 注释: 复杂逻辑前添加 **Why** 注释块，使用 `# ============================================================` 分隔符
- **命名规范与约定**: 
  - Python 类名: `PascalCase`（如 `AIOpsAgent`, `SafetyGuardrail`）
  - Vue 组件: `kebab-case.vue`（如 `access-control.vue`）
  - 组合式函数: `use` 前缀（如 `useAccess()`）
  - 内部包: `@vben/` 前缀（如 `@vben/hooks`）
- **Git 提交规范**: 项目未配置 commitlint，建议遵循 Conventional Commits（`feat:`, `fix:`, `docs:`）
- **安全注意事项**: 
  - ⚠️ `.env.example` 包含默认密码，生产环境必须修改
  - 使用 `.env.local` 覆盖敏感配置，确保已加入 `.gitignore`
  - 禁止在代码中硬编码 API Key、密码等敏感信息

## 4. 常用命令
- **安装和启动命令**: 
  | 场景 | 命令 |
  |------|------|
  | 启动 Docker 服务 | `.\scripts\start-services.ps1` |
  | 启动后端（开发） | `py -3 -m uvicorn backend.main:app --reload --port 8000` |
  | 启动前端 | `cd frontend && pnpm dev` |
  | 初始化演示数据 | `py -3 backend\init_demo_data.py` |
  | 迁移到 MySQL | `py -3 backend\migrate_to_mysql.py` |

- **测试和检查命令**: 
  | 场景 | 命令 |
  |------|------|
  | 后端测试 | `py -3 -m pytest` |
  | 前端类型检查 | `cd frontend && pnpm check:type` |
  | 前端 Lint | `cd frontend && pnpm lint` |
  | 前端完整检查 | `cd frontend && pnpm check` |

- **构建和部署命令**: 
  | 场景 | 命令 |
  |------|------|
  | 构建前端 | `cd frontend && pnpm build` |
  | 构建 Docker 镜像 | `cd frontend && pnpm build:docker` |
  | 预览构建产物 | `cd frontend && pnpm preview` |

- **环境变量配置**: 
  | 变量名 | 默认值 | 说明 |
  |--------|--------|------|
  | `LLM_API_KEY` | - | LLM API 密钥（**必填**） |
  | `LLM_BASE_URL` | `https://api.deepseek.com/v1` | LLM API 地址 |
  | `LLM_MODEL` | `deepseek-chat` | 模型名称 |
  | `DATABASE_TYPE` | `sqlite` | 数据库类型（`sqlite`/`mysql`） |
  | `MYSQL_HOST` | `localhost` | MySQL 主机 |
  | `MYSQL_PORT` | `3306` | MySQL 端口 |
  | `MYSQL_USER` | `aicops` | MySQL 用户名 |
  | `MYSQL_PASSWORD` | `aicops_pass_2024` | MySQL 密码 |
  | `MYSQL_DATABASE` | `aicops` | MySQL 数据库名 |
  | `REDIS_URL` | `redis://localhost:6379/0` | Redis 连接 URL |
  | `REDIS_ENABLED` | `true` | Redis 开关 |
  | `DEMO_MODE` | `false` | 演示模式开关 |

## 5. 技术决策
- **架构设计原因**: 
  - **双数据库架构**: SQLite 用于单机开发/演示，MySQL 用于生产环境，通过 `DATABASE_TYPE` 环境变量切换
  - **安全护栏系统**: 自研 5 层防护（意图分类 → 风险评分 → 参数校验 → 注入检测 → 沙箱执行），适配信创安全合规要求
  - **MCP 协议**: 基于 Model Context Protocol 的工具调用机制，支持 20+ 系统运维工具
- **技术选型理由**: 
  - **FastAPI**: 高性能异步框架，原生支持 WebSocket（流式对话）
  - **Vue Vben Admin**: 企业级 Monorepo 模板，开箱即用的权限/布局/请求封装
  - **Redis**: 会话存储、系统指标缓存、限流计数器
- **重要设计模式**: 
  - **Agent 模式**: `AIOpsAgent` 封装感知-规划-执行循环
  - **沙箱模式**: 最小权限代理执行，配置自动备份
  - **审计模式**: 全链路追踪（`trace_id` 关联推理步骤）
- **历史包袱说明**: [TBD: 需团队补充隐式知识]

## 6. 工作流程
- **开发流程步骤**: 
  1. 启动 Docker 服务（`.\scripts\start-services.ps1` 选择选项 2）
  2. 配置 `.env.local`（复制 `.env.example` 并修改敏感配置）
  3. 初始化演示数据（`py -3 backend\init_demo_data.py`）
  4. 启动后端 + 前端开发服务器
  5. 访问 `http://localhost:5555` 查看演示场景
- **PR 审核标准**: [TBD: 需团队补充隐式知识]
- **发布流程说明**: [TBD: 需团队补充隐式知识]
- **问题排查指南**: 
  - **Redis 连接失败**: 检查 Docker 容器状态 `docker-compose ps`，确认端口 6379 未被占用
  - **MySQL 连接失败**: 检查容器健康状态 `docker-compose logs mysql`，确认初始化脚本已执行
  - **前端构建失败**: 清理缓存 `pnpm clean`，重新安装 `pnpm reinstall`
  - **LLM 调用失败**: 检查 `LLM_API_KEY` 是否配置，检查 `LLM_BASE_URL` 是否可访问
