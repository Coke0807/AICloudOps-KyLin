# AICloudOps — 面向麒麟操作系统的安全智能运维 Agent

## 1. 项目概述

- **项目定位与核心功能**: AICloudOps 是一个面向麒麟操作系统（Kylin OS）的安全智能运维 Agent 平台。核心能力包括：LLM 驱动的自然语言运维交互、20+ 系统运维工具集（进程/磁盘/网络/日志/服务）、五层安全防护体系（输入清洗→意图分类→风险评分→参数校验→注入检测）、RBAC 角色权限控制、沙箱执行环境、配置备份与一键回滚、审计日志全链路追踪。
- **目标用户与使用场景**: 面向运维工程师和系统管理员，通过自然语言对话完成系统监控、故障排查、日志分析、进程管理等日常运维任务，同时内置安全护栏防止高危操作误执行。
- **技术栈与依赖环境**:
  - 核心语言/版本: Python >= 3.10（后端）、TypeScript（前端，Node >= 20）
  - 运行时环境: FastAPI + Uvicorn（后端）、Vite + Vue 3（前端）
  - 核心框架: FastAPI、Vue 3.5、Ant Design Vue 4.x、Vben Admin Pro v5.2.2
  - 关键依赖: pydantic-settings（配置管理）、httpx（异步 HTTP 客户端）、psutil（系统监控）、Pinia（状态管理）、Vue Router 4、ECharts 5、xterm（终端模拟）
  - 包管理器: pnpm >= 9（前端）、pip/uv（后端）
  - 构建工具: Turborepo（前端 monorepo）、Hatchling（Python 包构建）
- **快速开始指南**:
  ```bash
  # 1. 后端启动
  cd backend
  pip install -r requirements.txt          # 安装依赖
  # 或: pip install -e ".[dev]"            # 使用 pyproject.toml（含开发依赖）
  # 配置 .env 文件（从 .env.example 复制，填入 LLM_API_KEY）
  python -m uvicorn backend.main:app --reload --port 8000

  # 2. 前端启动
  cd frontend
  pnpm install                             # 安装依赖
  pnpm dev                                 # 启动开发服务器（端口 5666）

  # 3. 访问
  # 前端: http://localhost:5666
  # 后端 API: http://localhost:8000/api/v1
  # API 文档: http://localhost:8000/docs
  ```

## 2. 目录结构

- **关键目录说明**:
  ```
  newproject/
  ├── .env.example              # 后端环境变量模板
  ├── .env                      # 后端实际环境变量（含 API Key，勿提交）
  ├── pyproject.toml            # Python 项目元数据与依赖声明
  ├── pytest.ini                # pytest 配置（asyncio_mode=auto）
  │
  ├── backend/                  # Python FastAPI 后端服务
  │   ├── main.py               # FastAPI 应用入口（CORS、路由挂载、静态文件）
  │   ├── config.py             # Pydantic Settings 配置（LLM、安全参数）
  │   ├── database.py           # SQLite 单例数据库（会话/消息/审计/工具执行）
  │   ├── requirements.txt      # Python 依赖清单
  │   ├── api/
  │   │   └── routes.py         # 全部 API 路由（Agent/工具/历史/安全/RBAC）
  │   ├── core/
  │   │   ├── agent.py          # ReAct Agent 核心（意图分析→安全校验→工具调用→结果汇总）
  │   │   ├── llm_client.py     # LLM API 客户端（httpx，重试机制，Mock 模式）
  │   │   ├── os_sensor.py      # 操作系统数据采集（psutil，模拟麒麟 V11 环境）
  │   │   └── planner.py        # Plan-Execute 任务规划器（简单/中等/复杂三级）
  │   ├── mcp/
  │   │   └── tools.py          # 20 个 MCP 运维工具定义与调度器
  │   ├── safety/
  │   │   ├── audit_agent.py    # 审计代理（高危工具意图对齐校验）
  │   │   ├── rbac.py           # RBAC 角色权限（viewer/operator/admin 三级）
  │   │   ├── rules.py          # 安全规则库（危险命令/注入模式/路径黑白名单）
  │   │   ├── sandbox.py        # 沙箱执行器（Docker 隔离 or 受限子进程）+ 配置备份回滚
  │   │   └── validator.py      # 五层安全护栏（清洗→分类→评分→校验→注入检测）
  │   └── utils/
  │       └── audit_logger.py   # 审计日志写入
  │
  └── frontend/                 # Vue 3 + Vben Admin Pro 前端
      ├── package.json          # monorepo 根配置（Turbo + pnpm workspace）
      ├── pnpm-workspace.yaml   # pnpm 工作空间声明
      ├── turbo.json            # Turborepo 任务编排
      ├── Dockerfile            # 多阶段构建（Node 22 → static-web-server）
      ├── apps/
      │   └── web-antd/         # 主应用（Ant Design Vue）
      │       ├── src/
      │       │   ├── main.ts   # 应用入口
      │       │   ├── api/      # API 调用层（auth、user、k8s、prometheus、aiops）
      │       │   ├── router/   # 路由（动态模块、权限守卫）
      │       │   ├── store/    # Pinia 状态管理（auth）
      │       │   ├── views/    # 页面组件（ai/k8s/prometheus/dashboard/workorder）
      │       │   └── locales/  # 国际化（zh-CN / en-US）
      │       └── .env*         # 前端环境变量（开发/生产/分析）
      ├── packages/             # 共享业务包（@vben/ 作用域）
      │   ├── @core/            # 核心功能（base/composables/preferences/ui-kit）
      │   ├── effects/          # 副作用包（access/layouts/plugins/request/hooks）
      │   ├── stores/           # Pinia stores（access/user/lock/tabbar）
      │   ├── locales/          # 国际化包
      │   └── ...
      ├── internal/             # 内部工具包（lint-configs/tsconfig/vite-config/tailwind-config）
      └── scripts/              # 部署与工具脚本
  ```

- **文件组织方式**: 前后端分离架构。后端为单体 FastAPI 服务，按功能域分层（api/core/mcp/safety/utils）。前端为 pnpm + Turborepo monorepo，通过 `@vben/` 作用域包实现高度模块化，主应用 `apps/web-antd` 组合所有共享包。
- **配置文件位置**:
  - 后端: `backend/config.py`（Pydantic Settings，读取 `.env`）
  - 前端: `frontend/apps/web-antd/.env.*`（Vite 环境变量）、`vite.config.mts`（代理/别名）
  - 全局: `pyproject.toml`（Python）、`turbo.json`（构建编排）、`eslint.config.mjs`（Lint）
- **资源文件位置**: `frontend/apps/web-antd/public/`（静态资源）、`frontend/Dockerfile`（容器化配置）

## 3. 开发规范

- **代码风格与格式要求**:
  - **Python**: 使用 Black 格式化，遵循 PEP 8。所有函数/类需有 docstring。严格类型注解（`list[Dict[str, str]]` 风格）。
  - **TypeScript/Vue**: 使用 ESLint + Prettier + Stylelint。TS 严格模式开启（`strict: true`、`noImplicitAny`、`strictNullChecks`）。Vue 组件使用 `<script lang="ts" setup>` 语法。
  - **Import 排序**: 前端使用 `eslint-plugin-perfectionist` 自动排序导入。
- **命名规范与约定**:
  - Python: 模块/函数 `snake_case`，类 `PascalCase`，常量 `UPPER_SNAKE_CASE`
  - TypeScript: 文件名 `kebab-case`，组件 `PascalCase`，composables `useXxx`，stores `useXxxStore`
  - 路径别名: 前端 `#/*` → `./src/*`（Vite resolve.alias）
  - 包作用域: 前端共享包统一使用 `@vben/` 命名空间
- **Git 提交规范**: [TBD: 需团队补充隐式知识] — 项目已集成 Husky + lint-staged，但未检测到 commitlint 配置。建议采用 Conventional Commits 格式（`feat:`, `fix:`, `docs:` 等）。
- **安全注意事项**:
  - **API Key 隔离**: `.env` 文件包含真实密钥，**严禁提交到 Git**。本地开发使用 `.env`，部署使用环境变量注入。
  - **CORS 白名单**: 生产环境必须配置 `SAFETY.ALLOWED_ORIGINS`，禁止使用 `*`。
  - **LLM 注入防护**: 用户输入经过 28 种注入模式检测（中英文），包含 prompt injection、角色扮演、编码绕过等。
  - **工具执行沙箱**: 高危命令（kill_process/run_safe_command/rollback_operation）必须经过 RBAC + 五层安全护栏 + 审计代理三重校验。
  - **前端 Token 安全**: 使用 `pinia-plugin-persistedstate` 持久化 Token，支持自动刷新和过期处理。

## 4. 常用命令

- **安装和启动命令**:
  ```bash
  # === 后端 ===
  pip install -r backend/requirements.txt                    # 安装后端依赖
  pip install -e ".[dev]"                                    # 安装含开发依赖
  python -m uvicorn backend.main:app --reload --port 8000    # 开发模式启动

  # === 前端 ===
  cd frontend
  pnpm install                                               # 安装前端依赖
  pnpm dev                                                   # 启动开发服务器（端口 5666）
  pnpm dev:antd                                              # 同上，显式指定应用
  ```

- **测试和检查命令**:
  ```bash
  # === 后端测试 ===
  pytest                                                     # 运行所有测试（testpaths=tests, asyncio_mode=auto）
  pytest -v                                                  # 详细输出
  pytest --cov=backend                                       # 覆盖率报告

  # === 前端检查 ===
  cd frontend
  pnpm test:unit                                             # Vitest 单元测试
  pnpm lint                                                  # ESLint + Stylelint 检查
  pnpm format                                                # 自动格式化
  pnpm typecheck                                             # TypeScript 类型检查
  pnpm check                                                 # 完整检查（类型 + 依赖 + 循环依赖 + 拼写）
  ```

- **构建和部署命令**:
  ```bash
  # === 前端构建 ===
  cd frontend
  pnpm build                                                 # 生产构建（全部应用）
  pnpm build:antd                                            # 仅构建 web-antd
  pnpm build:docker                                          # 构建 Docker 镜像
  pnpm preview                                               # 预览生产构建

  # === Docker 部署 ===
  # 前端: 多阶段构建 → Node 22 编译 → static-web-server 托管
  # 后端: 直接 uvicorn 启动
  ```

- **环境变量配置**:

  **后端环境变量**（`.env`）:

  | 变量 | 说明 | 示例 |
  |------|------|------|
  | `APP_NAME` | 应用名称 | `AICloudOps` |
  | `APP_ENV` | 运行环境 | `development` |
  | `APP_DEBUG` | 调试模式 | `true` |
  | `HOST` | 监听地址 | `0.0.0.0` |
  | `PORT` | 监听端口 | `8000` |
  | `LLM_API_KEY` | LLM API 密钥 | `your_api_key_here` |
  | `LLM_BASE_URL` | LLM API 地址 | `https://api.deepseek.com/v1` |
  | `LLM_MODEL` | 模型名称 | `deepseek-chat` |
  | `LLM_TEMPERATURE` | 生成温度 | `0.3` |
  | `LLM_MAX_TOKENS` | 最大 Token | `2048` |
  | `DATABASE_URL` | 数据库连接 | `sqlite:///./data/aicops.db` |

  **前端环境变量**（`apps/web-antd/.env*`）:

  | 变量 | 说明 | 示例 |
  |------|------|------|
  | `VITE_PORT` | 开发服务器端口 | `5666` |
  | `VITE_BASE` | 路由基础路径 | `/` |
  | `VITE_GLOB_API_URL` | API 代理路径 | `/api` |
  | `VITE_GLOB_AIOPS_URL` | AIOps 后端路径 | `/api/v1` |
  | `VITE_APP_TITLE` | 页面标题 | `AI-CloudOps` |
  | `VITE_NITRO_MOCK` | Mock 服务开关 | `false` |
  | `VITE_DEVTOOLS` | DevTools 开关 | `false` |
  | `VITE_ROUTER_HISTORY` | 路由模式 | `hash` |
  | `VITE_COMPRESS` | 压缩算法 | `none` |

## 5. 技术决策

- **架构设计原因**:
  - **前后端分离**: 后端专注 LLM Agent 推理与系统操作，前端提供富交互 UI（终端模拟、监控图表、对话界面）。前端通过 Vite proxy 将 `/api/v1` 请求转发到后端 `localhost:8000`。
  - **五层安全护栏**: 鉴于运维操作的高风险性（误执行 `rm -rf` 可能导致系统瘫痪），采用纵深防御策略：输入清洗 → 意图分类 → 风险评分 → 参数校验 → 注入检测，逐层过滤危险操作。
  - **Mock 模式**: LLM 客户端内置 Mock 模式（无 API Key 时自动启用），支持在无 LLM 服务的环境下进行前端开发和功能演示。
  - **Plan-Execute 模式**: 复杂运维任务（如"系统很卡"）不是直接调用单个工具，而是先由规划器拆解为多步骤子任务，按依赖顺序执行，最终综合分析。

- **技术选型理由**:
  - **FastAPI**: 原生 async 支持，适合 LLM 流式响应和并发工具调用；自带 OpenAPI 文档生成。
  - **Vben Admin Pro**: 成熟的 Vue 3 企业级管理后台框架，内置权限管理、主题切换、国际化等开箱即用能力。
  - **SQLite**: 轻量级，零配置，适合单机部署的运维工具，数据文件存储在 `data/aicops.db`。
  - **httpx**: 异步 HTTP 客户端，支持流式响应（SSE），适配 LLM API 的 streaming 场景。
  - **Turborepo**: 前端 monorepo 构建加速，支持增量构建和任务缓存。

- **重要设计模式**:
  - **单例模式**: `Database` 类使用 `__new__` 实现单例，确保全局唯一数据库连接管理。
  - **ReAct 模式**: Agent 核心采用 Reasoning-Acting 循环，LLM 推理 → 工具调用 → 结果反馈 → 继续推理。
  - **策略模式**: 安全验证器（`SafetyGuardrail`）组合多个独立验证层，每层可独立启用/禁用。
  - **沙箱降级**: Docker 不可用时自动降级为受限子进程执行（命令白名单 + 超时控制）。
  - **Token 刷新队列**: 前端 `RequestClient` 实现 Token 刷新时的请求排队，避免并发刷新。

- **历史包袱说明**:
  - `os_sensor.py` 中硬编码了麒麟 V11 系统信息（龙芯3A5000），用于演示目的。生产环境需替换为实际 `psutil` 采集。
  - 后端 `database.py` 使用原始 `sqlite3` 而非 ORM（如 SQLAlchemy），在数据模型复杂化后可能需要重构。
  - [TBD: 需团队补充隐式知识] — 如有其他技术债务或待迁移模块请补充。

## 6. 工作流程

- **开发流程步骤**:
  1. 从 `main` 分支创建功能分支
  2. 后端修改：编辑 `backend/` 下的模块，运行 `pytest` 验证
  3. 前端修改：编辑 `frontend/apps/web-antd/src/` 或共享包，运行 `pnpm lint && pnpm typecheck`
  4. 使用 `pnpm dev` 启动前端 + `uvicorn --reload` 启动后端进行联调
  5. 提交前运行完整检查：`pnpm check`（前端）、`pytest`（后端）
  6. 推送分支并创建 PR

- **PR 审核标准**:
  - [TBD: 需团队补充隐式知识] — 建议基线标准：
    - ESLint / TypeCheck / pytest 全部通过
    - 安全相关变更需额外审查（`safety/` 模块、RBAC 规则、工具定义）
    - 新增 API 端点需附带 OpenAPI 文档说明
    - 前端新增页面需适配亮色/暗色主题

- **发布流程说明**:
  - 前端 Docker 构建：`pnpm build:docker`（多阶段构建 → static-web-server）
  - 后端部署：直接 `uvicorn backend.main:app` 启动，或配合 Docker
  - 版本管理：前端使用 Changesets（`@changesets/cli`），Python 版本在 `pyproject.toml`
  - [TBD: 需团队补充隐式知识] — 如有 CI/CD pipeline、发布节奏等请补充

- **问题排查指南**:
  - **LLM 无响应**: 检查 `.env` 中 `LLM_API_KEY` 和 `LLM_BASE_URL` 配置。无 Key 时自动进入 Mock 模式（控制台会打印 mock 日志）。
  - **前端代理失败**: 确认后端运行在 `localhost:8000`。Vite 开发服务器通过 `vite.config.mts` 中的 proxy 配置转发 `/api/v1`。
  - **安全拦截误报**: 检查 `backend/safety/rules.py` 中的规则定义，可通过调整 `RISK_SCORE_THRESHOLDS` 阈值或在白名单中添加例外。
  - **数据库锁定**: SQLite 单写入者限制。若出现 `database is locked`，检查是否有多个进程同时写入 `data/aicops.db`。
  - **前端构建内存不足**: 构建命令已配置 `NODE_OPTIONS=--max-old-space-size=8192`，若仍不足可增大此值。
  - **依赖安装失败**: 前端使用 `pnpm`，确保 Node >= 20 且 pnpm >= 9。后端使用 `pip`，确保 Python >= 3.10。
