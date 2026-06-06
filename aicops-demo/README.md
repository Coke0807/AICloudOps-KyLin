# AICloudOps - 面向麒麟操作系统的安全智能运维 Agent

> 第十五届中国软件杯大赛 A2 赛题作品

## 项目简介

AICloudOps 是一套部署于操作系统的智能运维 Agent，通过自然语言对话实现系统监控、故障排查和运维操作。系统采用 MCP (Model Context Protocol) 协议架构，集成安全护栏机制，确保运维操作的安全性和可控性。

## 核心特性

### 1. OS 环境深度感知
- 实时采集 CPU、内存、磁盘、进程、网络等系统指标
- 支持网络接口统计、磁盘 I/O、系统负载、僵尸进程检测
- 支持 journalctl 日志查询、systemctl 服务状态检查
- 基于 psutil + /proc 文件系统的深度系统感知

### 2. MCP 运维插件化（18 个工具）
- 基于 MCP 协议的工具插件架构，支持灵活扩展
- **系统监控**: 系统状态、进程列表、进程详情、系统运行时间
- **磁盘文件**: 磁盘使用、大文件扫描
- **网络端口**: 网络连接、端口占用检查
- **内存分析**: 内存详情、内存 Top 消耗者
- **日志分析**: journalctl 查询、日志文件搜索
- **服务管理**: 服务状态查询、失败服务列表
- **安全审计**: 失败登录检查
- **进程操作**: 进程打开文件、安全终止进程（需确认）
- **通用命令**: 白名单安全命令执行

### 3. 五层纵深安全护栏
- **L1 输入净化**: Unicode 同形字检测、零宽字符移除、控制字符过滤
- **L2 意图分类**: 加权关键词匹配，分类为查询/诊断/修改/危险
- **L3 风险评分**: 0.0-1.0 量化评分，30+ 危险命令模式识别
- **L4 参数校验**: 路径白名单/黑名单、PID 安全校验
- **L5 注入检测**: 中英文 Prompt Injection 检测、Base64/Hex 编码攻击检测

### 4. 最小权限代理执行
- 命令白名单机制（20+ 安全命令）
- 高风险操作（kill_process）强制二次确认
- 20+ 受保护路径黑名单
- 遵循最小权限原则

### 5. 推理链路溯源
- 完整记录推理决策全过程（6 个阶段）
- 闭环日志：接收指令 → 感知环境 → 意图分析 → 安全校验 → 工具执行 → 最终决策
- 支持异常回溯和审计
- 多步推理链路（最多 3 轮工具调用）

### 6. 智能对话交互
- 集成 DeepSeek/Qwen3 等国产大模型
- 支持流式响应
- 上下文感知的多轮对话
- 多步工具调用推理

## 技术架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    前端 (Vue 3 + Element Plus)                    │
│         对话界面 │ 系统监控 │ 安全护栏 │ 推理溯源 │ 历史          │
├─────────────────────────────────────────────────────────────────┤
│                    API 网关 (FastAPI + SSE)                       │
├───────────────┬───────────────┬───────────────┬─────────────────┤
│    感知层      │    决策层      │    护栏层      │     存储层      │
│  (OS Sensor)  │  (LLM Agent)  │  (5-Layer)    │   (SQLite)     │
│  · psutil     │  · 多步推理    │  · L1 输入净化 │   · 会话       │
│  · /proc      │  · 工具调用    │  · L2 意图分类 │   · 消息       │
│  · journalctl │  · 上下文管理  │  · L3 风险评分 │   · 审计日志   │
│  · systemctl  │               │  · L4 参数校验 │   · 工具执行   │
│               │               │  · L5 注入检测 │                │
├───────────────┴───────────────┴───────────────┴─────────────────┤
│                    MCP Server (18 Tools)                         │
│  系统监控 │ 磁盘文件 │ 网络端口 │ 内存分析 │ 日志 │ 服务 │ 安全  │
└─────────────────────────────────────────────────────────────────┘
```

## 技术栈

| 层级 | 技术选型 |
|------|----------|
| 前端 | Vue 3 + Vite + Element Plus + Pinia |
| 后端 | Python + FastAPI + Uvicorn |
| 数据库 | SQLite |
| 大模型 | DeepSeek / Qwen (国产开源模型) |
| 系统监控 | psutil |
| 协议 | MCP (Model Context Protocol) |

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- pnpm (推荐) 或 npm

### 1. 克隆项目

```bash
cd aicops-demo
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置大模型 API Key：

```env
LLM_API_KEY=your_deepseek_api_key
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

> 💡 DeepSeek API Key 申请地址: https://platform.deepseek.com/

### 3. 安装后端依赖

```bash
pip install -e .
```

### 4. 安装前端依赖

```bash
cd frontend
pnpm install
```

### 5. 构建前端

```bash
pnpm build
```

### 6. 启动服务

```bash
# 方式一：直接运行
python -m backend.main

# 方式二：开发模式
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 7. 访问系统

- API 文档: http://localhost:8000/docs
- 前端界面: http://localhost:3000 (开发模式)

## 项目结构

```
aicops-demo/
├── backend/                    # 后端代码
│   ├── api/                    # API 路由
│   │   └── routes.py           # 路由定义（含安全事件接口）
│   ├── core/                   # 核心功能
│   │   ├── agent.py            # AI Agent（多步推理 + 审计集成）
│   │   ├── llm_client.py       # 大模型客户端
│   │   └── os_sensor.py        # OS 深度感知（13 个数据源）
│   ├── mcp/                    # MCP 协议工具
│   │   └── tools.py            # 18 个运维工具
│   ├── safety/                 # 五层安全护栏
│   │   ├── validator.py        # 5 层纵深防御引擎
│   │   └── rules.py            # 安全规则库（30+ 危险命令模式）
│   ├── utils/                  # 工具类
│   │   └── audit_logger.py     # 推理链路审计
│   ├── config.py               # 配置管理（含安全配置）
│   ├── database.py             # SQLite 数据库
│   └── main.py                 # 应用入口
├── frontend/                   # 前端代码
│   ├── src/
│   │   ├── api/                # API 请求封装
│   │   ├── components/         # 通用组件
│   │   ├── router/             # 路由配置
│   │   ├── stores/             # Pinia 状态管理
│   │   ├── styles/             # 全局样式
│   │   └── views/              # 页面组件
│   │       ├── ChatView.vue    # 智能对话
│   │       ├── DashboardView.vue # 系统监控
│   │       ├── SafetyView.vue  # 安全护栏面板
│   │       ├── ToolsView.vue   # MCP 工具集
│   │       ├── TracesView.vue  # 推理溯源
│   │       └── HistoryView.vue # 对话历史
│   ├── index.html
│   └── package.json
├── data/                       # SQLite 数据库文件
├── logs/                       # 推理链路日志
├── .env.example                # 环境变量示例
├── pyproject.toml              # Python 项目配置
└── README.md
```

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/v1/health` | GET | 健康检查 |
| `/api/v1/system/status` | GET | 获取系统状态快照 |
| `/api/v1/system/processes` | GET | 获取进程列表 |
| `/api/v1/system/disks` | GET | 获取磁盘信息 |
| `/api/v1/tools` | GET | 列出 18 个 MCP 工具 |
| `/api/v1/tools/execute` | POST | 执行指定工具 |
| `/api/v1/agent/process` | POST | Agent 处理请求（含多步推理） |
| `/api/v1/agent/stream` | POST | Agent 流式处理请求 |
| `/api/v1/history` | GET | 获取对话历史 |
| `/api/v1/traces` | GET | 获取推理链路列表 |
| `/api/v1/traces/{id}` | GET | 获取单条推理链路详情 |
| `/api/v1/safety/events` | GET | 获取安全事件列表 |
| `/api/v1/safety/stats` | GET | 获取安全统计数据 |

## 安全特性

### 五层纵深防御

| 层级 | 名称 | 功能 |
|------|------|------|
| L1 | 输入净化 | Unicode 同形字、零宽字符、控制字符检测 |
| L2 | 意图分类 | 查询/诊断/修改/危险 四级分类 |
| L3 | 风险评分 | 30+ 危险命令模式，0.0-1.0 量化评分 |
| L4 | 参数校验 | 路径白名单/黑名单，PID 安全校验 |
| L5 | 注入检测 | 中英文 Prompt Injection，Base64/Hex 编码攻击 |

### 危险命令检测（30+ 模式）
- `rm -rf /` - 递归删除根目录
- `mkfs` - 格式化文件系统
- `chmod 777 /` - 危险权限设置
- `dd if=` - 磁盘写入操作
- Fork Bomb - 拒绝服务攻击
- `wget | sh` / `curl | bash` - 远程代码执行
- `nc -l` - 反弹 Shell
- `iptables -F` - 清空防火墙规则

### 受保护路径（20+ 规则）
- `/etc` - 系统配置文件
- `/boot` - 启动文件
- `/dev` - 设备文件
- `/proc` - 进程信息
- `/sys` - 系统信息
- `/root` - root 用户目录
- `/usr/lib/systemd` - 系统服务文件

## 评分对应

| 评分项 | 占比 | 实现情况 |
|--------|------|----------|
| OS 感知与 MCP 插件实现 | 15% | ✅ 18 个 MCP 工具 + 13 个 OS 数据源 |
| 自然语言交互与准确性 | 15% | ✅ DeepSeek/Qwen3 + 多步推理 |
| 安全护栏与风险控制 | 15% | ✅ 五层纵深防御 + 30+ 危险命令检测 |
| 智能化根因分析能力 | 10% | ✅ 多步工具调用 + 环境感知分析 |
| 创新与实用性 | 25% | ✅ 五层安全架构 + 推理链可视化 |
| 文档与演示 | 20% | ✅ 完整文档 + 演示视频 |

## 开发说明

### 前端开发

```bash
cd frontend
pnpm dev
```

### 后端开发

```bash
uvicorn backend.main:app --reload
```

### 代码规范

- 前端：ESLint + Prettier
- 后端：Black + Ruff

## 许可证

本项目仅供学习和比赛使用。

## 致谢

- DeepSeek - 提供大模型 API
- Element Plus - UI 组件库
- FastAPI - Web 框架
- psutil - 系统监控库
