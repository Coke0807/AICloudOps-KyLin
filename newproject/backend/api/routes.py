import json
import asyncio
from datetime import datetime
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from backend.core.agent import agent
from backend.core.os_sensor import OSSensor
from backend.database import db
from backend.mcp.tools import MCPTools, execute_tool
from backend.safety.validator import SafetyGuardrail
# CORS is configured in main.py via CORSMiddleware using origins from config
from backend.safety.sandbox import config_backup, sandbox_executor
from backend.safety.audit_agent import audit_agent
from backend.safety.rbac import UserContext, Role, TOOL_ROLE_REQUIREMENTS, check_permission, get_missing_permission_message

router = APIRouter()
# 认证/用户路由 — 挂载到 /api 前缀，与 /api/v1 业务路由分离
auth_router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshTokenRequest(BaseModel):
    refreshToken: str


class UserProfile(BaseModel):
    id: int
    username: str
    real_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    avatar: Optional[str] = None
    roles: List[str] = []
    permissions: List[str] = []


# ============================================================
# 用户认证路由 (兼容前端 /api 前缀)
# ============================================================

@auth_router.post("/auth/login")
async def login(request: LoginRequest):
    """用户登录接口（兼容 /api/auth/login 路径）"""
    return {
        "accessToken": "mock_access_token_12345",
        "refreshToken": "mock_refresh_token_67890",
        "expires": 3600,
    }


@auth_router.post("/auth/refresh")
async def refresh_token(request: RefreshTokenRequest):
    """刷新 Token 接口"""
    return {
        "success": True,
        "data": "mock_new_access_token_54321",
    }


@auth_router.get("/user/profile")
async def get_user_profile():
    """获取当前登录用户信息
    前端 getUserInfoApi 直接使用返回值作为 UserInfo，
    不经过 success/data 解包。
    """
    return {
        "id": 1,
        "username": "admin",
        "real_name": "系统管理员",
        "email": "admin@aicops.local",
        "phone": "13800138000",
        "avatar": "",
        "roles": ["admin"],
        "homePath": "/dashboard",
        "permissions": [
            "read", "write", "delete", "admin",
        ],
    }


@auth_router.post("/user/change_password")
async def change_password():
    """修改密码"""
    return {"success": True, "message": "密码修改成功"}


@auth_router.post("/user/logout")
async def user_logout():
    """退出登录（前端标准路径）"""
    return {"success": True}


@auth_router.get("/user/codes")
async def get_user_codes():
    """获取用户权限码列表"""
    return ["read", "write", "delete", "admin"]


@auth_router.post("/user/login")
async def user_login(request: LoginRequest):
    """用户登录（前端标准路径）
    前端 auth store 直接解构 { accessToken, refreshToken }，
    因此 token 必须在顶层，不能嵌套在 data 里。
    """
    return {
        "accessToken": "mock_access_token_12345",
        "refreshToken": "mock_refresh_token_67890",
        "desc": "登录成功",
        "realName": "系统管理员",
        "userId": "1",
        "username": request.username,
    }


@auth_router.post("/user/refresh_token")
async def user_refresh_token(request: RefreshTokenRequest):
    """刷新 Token（前端标准路径）"""
    return {
        "success": True,
        "data": {
            "data": "mock_new_access_token_54321",
            "status": 0,
        },
    }


@auth_router.get("/system/info")
async def get_system_info():
    """获取系统硬件信息"""
    from backend.core.os_sensor import OSSensor as _sensor
    return {"success": True, "data": _sensor.get_full_snapshot()}


@auth_router.get("/system/metrics")
async def get_system_metrics():
    """获取系统实时指标"""
    from backend.core.os_sensor import OSSensor as _sensor
    return {"success": True, "data": _sensor.get_full_snapshot()}


@auth_router.post("/system/refresh")
async def refresh_system_info():
    """强制刷新系统信息"""
    from backend.core.os_sensor import OSSensor as _sensor
    return {"success": True, "data": _sensor.get_full_snapshot()}


class AgentRequest(BaseModel):
    prompt: str
    session_id: Optional[str] = None


class ToolExecuteRequest(BaseModel):
    tool_name: str
    params: Optional[Dict[str, Any]] = None


@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "AICloudOps"}


@router.get("/demo/status")
async def demo_status():
    """返回 Demo Mode 状态和可用场景列表，供前端适配 UI"""
    from backend.config import settings as _settings
    from backend.core.demo_engine import demo_engine as _engine

    if not _settings.DEMO_MODE:
        return {"enabled": False, "scenarios": []}

    scenarios = [
        {"name": s.name, "keywords": s.trigger_keywords}
        for s in _engine._scenarios
    ]
    return {"enabled": True, "scenarios": scenarios}


@router.get("/system/status")
async def get_system_status():
    from backend.config import settings as _settings
    # Demo Mode 返回麒麟 V11 Mock 快照，避免泄露真实 Windows 信息
    if _settings.DEMO_MODE:
        from backend.core.demo_engine import demo_engine as _engine
        return {"data": _engine.get_mock_snapshot()}
    # OSSensor.get_full_snapshot() 内含 psutil.cpu_percent(interval=0.5) 等同步阻塞调用，
    # 必须放到线程池执行，避免阻塞 uvicorn 事件循环
    snapshot = await asyncio.to_thread(OSSensor.get_full_snapshot)
    return {"data": snapshot}


@router.get("/system/processes")
async def get_processes(limit: int = 20):
    return {"data": await asyncio.to_thread(OSSensor.get_process_list, limit)}


@router.get("/system/disks")
async def get_disks():
    return {"data": await asyncio.to_thread(OSSensor.get_disk_info)}


@router.get("/tools")
async def list_tools():
    # MCPTools.list_available_tools() 返回 {"tool":..., "status":..., "data":[...]}
    # 前端期望 {tools: [...]}，这里解包 data 字段以对齐格式
    result = MCPTools.list_available_tools()
    return {"tools": result.get("data", [])}


@router.post("/tools/execute")
async def execute_tool_endpoint(request: ToolExecuteRequest):
    # RBAC: 使用默认 operator 角色校验工具调用权限
    user_ctx = UserContext()
    if not check_permission(user_ctx, request.tool_name):
        raise HTTPException(
            status_code=403,
            detail=get_missing_permission_message(user_ctx, request.tool_name),
        )
    # 高危工具需经安全护栏校验
    HIGH_RISK_TOOLS = {"kill_process", "run_safe_command", "rollback_operation"}
    if request.tool_name in HIGH_RISK_TOOLS:
        guardrail = SafetyGuardrail()
        command_to_check = ""
        params = request.params or {}
        if request.tool_name == "run_safe_command":
            command_to_check = params.get("command", "")
        elif request.tool_name == "kill_process":
            command_to_check = f"kill -{params.get('signal', 15)} {params.get('pid', '')}"
        if command_to_check:
            safety = guardrail.validate(command_to_check)
            if not safety["is_safe"]:
                raise HTTPException(status_code=403, detail=f"安全拦截: {command_to_check}")
    result = execute_tool(request.tool_name, request.params or {})
    return result


@router.post("/agent/process")
async def process_request(request: AgentRequest):
    try:
        result = await agent.process_request(request.prompt, request.session_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agent/stream")
async def stream_request(request: AgentRequest):
    async def generate():
        async for chunk in agent.stream_request(request.prompt, request.session_id):
            import json
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/history")
async def list_sessions(limit: int = 50):
    sessions = db.get_sessions(limit)
    return {"sessions": sessions}


@router.get("/history/{session_id}")
async def get_session(session_id: str):
    messages = db.get_session_messages(session_id)
    return {"messages": messages}


@router.delete("/history/{session_id}")
async def delete_session(session_id: str):
    success = db.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True}


@router.get("/traces")
async def list_traces(limit: int = 50):
    from pathlib import Path
    import json

    logs_dir = Path("logs")
    trace_files = sorted(logs_dir.glob("trace_*.json"), reverse=True)[:limit]
    traces = []
    for f in trace_files:
        try:
            with open(f, "r", encoding="utf-8") as tf:
                traces.append(json.load(tf))
        except Exception as exc:
            import logging
            logging.warning("加载推理链路文件失败 %s: %s", f.name, exc)
            continue
    return {"traces": traces}


@router.get("/traces/{trace_id}")
async def get_trace(trace_id: str):
    from pathlib import Path

    trace_file = Path("logs") / f"trace_{trace_id}.json"
    if not trace_file.exists():
        raise HTTPException(status_code=404, detail="Trace not found")
    with open(trace_file, "r", encoding="utf-8") as f:
        return {"trace": json.load(f)}


@router.get("/safety/events")
async def get_safety_events(limit: int = 100):
    with db.get_connection() as conn:
        rows = conn.execute(
            """SELECT * FROM audit_logs
               WHERE step = 'SAFETY_VALIDATION'
               ORDER BY created_at DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()

    events = []
    for row in rows:
        data = json.loads(row["data"])
        validation = data.get("validation") or data.get("result")
        is_safe = True
        risk_level = "safe"
        if validation:
            is_safe = validation.get("is_safe", True)
            risk_level = validation.get("overall_risk", "safe")

        events.append({
            "id": row["id"],
            "trace_id": row["trace_id"],
            "step": row["step"],
            "data": data,
            "is_safe": is_safe,
            "risk_level": risk_level,
            "created_at": row["created_at"],
        })

    return {"events": events, "total": len(events)}


@router.get("/safety/stats")
async def get_safety_stats():
    with db.get_connection() as conn:
        rows = conn.execute(
            """SELECT data FROM audit_logs WHERE step = 'SAFETY_VALIDATION'"""
        ).fetchall()

    total_checks = len(rows)
    blocked_count = 0
    risk_distribution = {"safe": 0, "low": 0, "medium": 0, "high": 0, "critical": 0}

    for row in rows:
        data = json.loads(row["data"])
        validation = data.get("validation") or data.get("result")
        if validation:
            is_safe = validation.get("is_safe", True)
            risk_level = validation.get("overall_risk", "safe")
            if not is_safe:
                blocked_count += 1
            if risk_level in risk_distribution:
                risk_distribution[risk_level] += 1

    return {
        "total_checks": total_checks,
        "blocked_count": blocked_count,
        "passed_count": total_checks - blocked_count,
        "block_rate": round(blocked_count / total_checks, 4) if total_checks > 0 else 0,
        "risk_distribution": risk_distribution,
    }


@router.get("/security/rbac/roles")
async def get_rbac_roles():
    """获取RBAC角色和工具权限映射"""
    roles = [
        {"name": "viewer", "level": 0, "description": "只读权限 - 可查看系统状态、进程、磁盘等信息"},
        {"name": "operator", "level": 1, "description": "运维权限 - 可执行安全命令、备份配置"},
        {"name": "admin", "level": 2, "description": "管理员权限 - 可执行高危操作（kill进程、回滚）"},
    ]
    tool_mapping = {k: v.value for k, v in TOOL_ROLE_REQUIREMENTS.items()}
    return {"roles": roles, "tool_requirements": tool_mapping}


@router.get("/security/sandbox/status")
async def get_sandbox_status():
    """获取沙箱执行环境状态"""
    return {
        "docker_available": sandbox_executor.docker_available,
        "sandbox_mode": "docker" if sandbox_executor.docker_available else "restricted",
        "enabled": True,
    }


@router.get("/security/backups")
async def list_backups():
    """获取配置备份历史"""
    return {"backups": config_backup.get_backup_history()}


@router.post("/security/rollback")
async def rollback_operation(operation_id: str):
    """回滚指定操作 — 仅 admin 角色可执行"""
    user_ctx = UserContext(role=Role.ADMIN)
    if not check_permission(user_ctx, "rollback_operation"):
        raise HTTPException(status_code=403, detail="仅管理员可执行回滚操作")
    result = config_backup.rollback(operation_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "回滚失败"))
    return result


@router.get("/assistant/info")
async def get_assistant_info():
    """获取服务信息"""
    return {
        "service": "AICloudOps",
        "version": "1.0.0",
        "description": "面向麒麟操作系统的安全智能运维 Agent 平台",
        "capabilities": [
            "自然语言运维交互",
            "20+ 系统运维工具集",
            "五层安全防护体系",
            "RBAC 角色权限控制",
            "沙箱执行环境",
            "配置备份与一键回滚",
            "审计日志全链路追踪",
        ],
        "endpoints": {
            "agent_process": "/api/v1/agent/process",
            "agent_stream": "/api/v1/agent/stream",
            "system_status": "/api/v1/system/status",
            "safety_stats": "/api/v1/safety/stats",
            "rbac_roles": "/api/v1/security/rbac/roles",
            "mcp_jsonrpc": "/api/v1/mcp/jsonrpc",
        },
        "constraints": {
            "python_version": ">=3.10",
            "required_packages": "psutil, httpx, pydantic-settings",
        },
        "status": "online",
    }


# ============================================================
# 知识库管理 API
# ============================================================

# 内存知识库存储
_knowledge_docs: List[Dict[str, Any]] = []
_knowledge_doc_counter = 0

_knowledge_sample_docs = [
    {
        "id": "doc_001",
        "title": "Linux 系统性能调优指南",
        "file_name": "linux-performance-tuning.md",
        "content": """# Linux 系统性能调优指南

## CPU 性能优化

### 1. CPU 频率调节
Linux 系统支持多种 CPU 频率调节器（governor）：
- **performance**: 锁定在最高频率，适合计算密集型任务
- **powersave**: 锁定在最低频率，适合节能场景
- **ondemand**: 根据负载动态调整频率（推荐）
- **schedutil**: 利用内核调度器数据调整频率，延迟更低

查看当前 governor：
```bash
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

### 2. CPU 亲和性绑定
将关键进程绑定到特定 CPU 核心，减少缓存未命中：
```bash
taskset -c 0-3 <command>
```

## 内存优化

### 1. 透明大页（THP）
透明大页可能引发内存延迟峰值。建议关闭或设为 madvise 模式：
```bash
echo madvise > /sys/kernel/mm/transparent_hugepage/enabled
```

### 2. OOM 调整
通过 `/proc/<pid>/oom_score_adj` 调整进程的 OOM 优先级（-1000 到 1000）。

## 磁盘 I/O 优化

### 1. I/O 调度器选择
- **mq-deadline**: 通用场景推荐
- **bfq**: 适合机械硬盘
- **kyber**: 适合 NVMe SSD

查看当前调度器：
```bash
cat /sys/block/sda/queue/scheduler
```

### 2. 文件系统参数
ext4 挂载参数优化：
```bash
mount -o defaults,noatime,nodiratime,data=ordered /dev/sda1 /mountpoint
```

## 网络优化

### TCP 参数调优
```bash
# 增加连接队列长度
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535

# TIME_WAIT 快速回收
net.ipv4.tcp_tw_reuse = 1

# 增大端口范围
net.ipv4.ip_local_port_range = 1024 65535
```""",
        "created_at": "2026-06-07T10:00:00Z",
        "updated_at": "2026-06-07T10:00:00Z",
        "status": "indexed",
    },
    {
        "id": "doc_002",
        "title": "Kubernetes 故障排查手册",
        "file_name": "k8s-troubleshooting.md",
        "content": """# Kubernetes 故障排查手册

## Pod 状态排查

### 1. Pod 处于 Pending 状态
常见原因：
- **资源不足**: 集群中没有足够的 CPU/内存资源调度 Pod
  ```bash
  kubectl describe pod <pod-name> -n <namespace>
  # 查看 Events 部分的 FailedScheduling 原因
  ```
- **节点选择器不匹配**: nodeSelector / nodeAffinity 没有匹配的节点
  ```bash
  kubectl get nodes --show-labels
  kubectl describe pod <pod-name> -n <namespace> | grep -A5 "Node-Selectors"
  ```
- **PersistentVolumeClaim 未绑定**: PV 不足或 StorageClass 不存在
  ```bash
  kubectl get pvc -n <namespace>
  kubectl describe pvc <pvc-name> -n <namespace>
  ```

### 2. Pod 处于 CrashLoopBackOff 状态
```bash
# 查看最近日志
kubectl logs <pod-name> -n <namespace> --tail=100

# 查看上一次崩溃的日志
kubectl logs <pod-name> -n <namespace> --previous

# 进入调试容器
kubectl debug -it <pod-name> -n <namespace> --image=busybox
```

### 3. Pod 处于 ImagePullBackOff 状态
- 检查镜像名称和 tag 是否正确
- 检查节点是否能访问镜像仓库
- 如果是私有仓库，检查 imagePullSecrets 配置

## Service 排查

### Service 无法访问
```bash
# 检查 Service 的 Endpoints 是否关联了 Pod
kubectl get endpoints <service-name> -n <namespace>

# 检查 Pod 标签是否与 Service 的 selector 匹配
kubectl get pods -n <namespace> --show-labels

# 使用 CoreDNS 检查域名解析
kubectl run dns-test --image=busybox:1.28 --restart=Never --rm -it -- nslookup <service-name>.<namespace>.svc.cluster.local
```

## Node 排查

### Node 处于 NotReady 状态
```bash
kubectl describe node <node-name>

# 常见原因：
# 1. kubelet 未运行: systemctl status kubelet
# 2. 磁盘压力: df -h
# 3. 内存压力: free -m
# 4. 网络插件异常: kubectl get pods -n kube-system
```""",
        "created_at": "2026-06-06T14:30:00Z",
        "updated_at": "2026-06-06T14:30:00Z",
        "status": "indexed",
    },
    {
        "id": "doc_003",
        "title": "Nginx 安全加固配置指南",
        "file_name": "nginx-security-hardening.md",
        "content": """# Nginx 安全加固配置指南

## 1. 隐藏版本信息
默认情况下 Nginx 会在响应头和错误页面中暴露版本信息：
```nginx
server_tokens off;
```

## 2. 配置安全响应头
```nginx
# 防止点击劫持
add_header X-Frame-Options "SAMEORIGIN" always;

# XSS 防护
add_header X-XSS-Protection "1; mode=block" always;

# 内容类型嗅探防护
add_header X-Content-Type-Options "nosniff" always;

# 严格的传输安全 (需 HTTPS)
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

# 内容安全策略
add_header Content-Security-Policy "default-src 'self'" always;

# Referrer 策略
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
```

## 3. SSL/TLS 加固
```nginx
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
ssl_prefer_server_ciphers on;

# 启用 OCSP Stapling
ssl_stapling on;
ssl_stapling_verify on;
resolver 8.8.8.8 8.8.4.4 valid=300s;

# 会话缓存
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;
```

## 4. 请求限制
```nginx
# 限制请求大小（防止大文件上传攻击）
client_max_body_size 10m;

# 限制请求头大小
large_client_header_buffers 4 8k;

# 限制单个 IP 连接数
limit_conn_zone $binary_remote_addr zone=addr:10m;
limit_conn addr 100;

# 限制请求频率
limit_req_zone $binary_remote_addr zone=req_limit:10m rate=10r/s;
limit_req zone=req_limit burst=20 nodelay;
```

## 5. 目录遍历防护
```nginx
# 禁止目录浏览
autoindex off;

# 禁止访问隐藏文件
location ~ /\. {
    deny all;
    access_log off;
    log_not_found off;
}

# 禁止访问备份文件
location ~* \.(bak|old|swp|dist|config)$ {
    deny all;
}
```

## 6. 访问控制
```nginx
# IP 白名单
location /admin/ {
    allow 10.0.0.0/8;
    allow 172.16.0.0/12;
    allow 192.168.0.0/16;
    deny all;
}

# 基本认证
location /private/ {
    auth_basic "Restricted Area";
    auth_basic_user_file /etc/nginx/.htpasswd;
}
```""",
        "created_at": "2026-06-05T09:15:00Z",
        "updated_at": "2026-06-05T09:15:00Z",
        "status": "indexed",
    },
    {
        "id": "doc_004",
        "title": "MySQL 数据库运维规范",
        "file_name": "mysql-ops-standards.md",
        "content": """# MySQL 数据库运维规范

## 1. 备份策略

### 全量备份
```bash
# 使用 mysqldump（适合中小规模数据库）
mysqldump --single-transaction --routines --triggers --events \\
    --all-databases > /backup/mysql_full_$(date +%Y%m%d).sql

# 使用 XtraBackup（适合大规模数据库）
xtrabackup --backup --target-dir=/backup/xtrabackup_$(date +%Y%m%d)
```

### 增量备份
```bash
# 基于 binlog 的增量恢复
mysqlbinlog --start-datetime="2026-06-07 00:00:00" \\
    --stop-datetime="2026-06-07 12:00:00" \\
    mysql-bin.000001 > /backup/incremental.sql
```

### 备份验证
```bash
# 恢复测试
mysql -u root -p < /backup/mysql_full_20260607.sql

# 校验备份完整性
mysqlcheck --all-databases --check --extended
```

## 2. 性能监控

### 慢查询日志
```sql
-- 开启慢查询日志
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL slow_query_log_file = '/var/log/mysql/slow.log';
SET GLOBAL long_query_time = 2;

-- 查看慢查询配置
SHOW VARIABLES LIKE '%slow_query%';
```

### 常用性能指标
```sql
-- 连接数使用率
SELECT (COUNT(*) / @@max_connections) * 100 AS connection_usage_pct
FROM information_schema.processlist;

-- 表锁等待
SHOW STATUS LIKE 'Table_locks_waited';

-- InnoDB 缓冲池命中率
SELECT 
    ROUND((1 - Innodb_buffer_pool_reads / Innodb_buffer_pool_read_requests) * 100, 2) AS hit_rate_pct
FROM information_schema.INNODB_BUFFER_POOL_STATS;

-- 索引使用情况
SELECT 
    table_schema, table_name, index_name,
    seq_in_index, cardinality
FROM information_schema.STATISTICS
WHERE table_schema NOT IN ('mysql', 'information_schema', 'performance_schema');
```

## 3. 安全管理

### 用户权限管理
```sql
-- 创建只读用户
CREATE USER 'readonly'@'%' IDENTIFIED BY 'strong_password';
GRANT SELECT ON mydb.* TO 'readonly'@'%';
FLUSH PRIVILEGES;

-- 撤销权限
REVOKE ALL PRIVILEGES ON *.* FROM 'user'@'host';

-- 查看用户权限
SHOW GRANTS FOR 'user'@'host';
```

### 密码策略
```sql
-- 启用密码复杂度要求
INSTALL COMPONENT 'file://component_validate_password';
SET GLOBAL validate_password.policy = 'MEDIUM';
SET GLOBAL validate_password.length = 12;
```

## 4. 常见故障处理

### 连接数耗尽
```sql
-- 查看当前连接
SHOW PROCESSLIST;

-- 查看最大连接数
SHOW VARIABLES LIKE 'max_connections';

-- 临时增加连接数
SET GLOBAL max_connections = 500;
```

### 锁等待超时
```sql
-- 查看当前锁等待
SELECT * FROM information_schema.INNODB_LOCK_WAITS;

-- 终止阻塞的会话
KILL <process_id>;
```""",
        "created_at": "2026-06-04T16:45:00Z",
        "updated_at": "2026-06-04T16:45:00Z",
        "status": "indexed",
    },
    {
        "id": "doc_005",
        "title": "Prometheus + Grafana 监控部署指南",
        "file_name": "prometheus-grafana-setup.md",
        "content": """# Prometheus + Grafana 监控部署指南

## 1. Prometheus 部署

### Docker Compose 部署
```yaml
# docker-compose.yml
version: '3'
services:
  prometheus:
    image: prom/prometheus:v2.47.0
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'

volumes:
  prometheus_data:
```

### prometheus.yml 配置
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'node'
    static_configs:
      - targets: ['localhost:9100']

  - job_name: 'mysql'
    static_configs:
      - targets: ['localhost:9104']
```

## 2. Grafana 部署

### Docker 部署
```yaml
  grafana:
    image: grafana/grafana:10.1.0
    container_name: grafana
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin123
      - GF_USERS_ALLOW_SIGN_UP=false
```

## 3. Node Exporter 部署

```bash
# 安装
wget https://github.com/prometheus/node_exporter/releases/download/v1.6.1/node_exporter-1.6.1.linux-amd64.tar.gz
tar xvf node_exporter-1.6.1.linux-amd64.tar.gz
cp node_exporter-1.6.1.linux-amd64/node_exporter /usr/local/bin/

# 创建 systemd 服务
cat > /etc/systemd/system/node_exporter.service << 'EOF'
[Unit]
Description=Node Exporter
After=network.target

[Service]
User=prometheus
ExecStart=/usr/local/bin/node_exporter
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable node_exporter
systemctl start node_exporter
```

## 4. 常用告警规则

```yaml
# alert_rules.yml
groups:
  - name: node_alerts
    rules:
      - alert: HighCPUUsage
        expr: 100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 90
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "CPU 使用率过高 ({{ $value }}%)"

      - alert: HighMemoryUsage
        expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100 > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "内存使用率过高 ({{ $value }}%)"

      - alert: DiskSpaceLow
        expr: (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) * 100 < 15
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "磁盘空间不足 (剩余 {{ $value }}%)"
```

## 5. Grafana Dashboard 推荐

| Dashboard | 用途 | ID |
|-----------|------|-----|
| Node Exporter Full | 主机监控总览 | 1860 |
| MySQL Overview | MySQL 性能监控 | 7362 |
| Nginx Traffic | Nginx 流量监控 | 12558 |
| Docker Monitoring | Docker 容器监控 | 179 |""",
        "created_at": "2026-06-03T11:20:00Z",
        "updated_at": "2026-06-03T11:20:00Z",
        "status": "indexed",
    },
    {
        "id": "doc_006",
        "title": "Docker 容器安全最佳实践",
        "file_name": "docker-security-best-practices.md",
        "content": """# Docker 容器安全最佳实践

## 1. 镜像安全

### 使用最小基础镜像
```dockerfile
# 推荐使用 Alpine 或 Distroless 镜像
FROM gcr.io/distroless/static-debian12
COPY --from=builder /app/server /server
CMD ["/server"]
```

### 镜像扫描
```bash
# 使用 Trivy 扫描镜像漏洞
trivy image myapp:latest

# 使用 Grype 扫描
grype myapp:latest

# CI/CD 集成扫描
trivy image --exit-code 1 --severity HIGH,CRITICAL myapp:latest
```

## 2. 运行时安全

### 只读文件系统
```bash
docker run --read-only --tmpfs /tmp:rw,noexec,nosuid myapp:latest
```

### 非 root 用户运行
```dockerfile
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser
```

### 资源限制
```bash
docker run --memory=512m --cpus=1.0 --pids-limit=100 myapp:latest
```

## 3. 网络安全

### 自定义网络隔离
```bash
docker network create --internal backend-net
docker run --network=backend-net myapp:latest
```

## 4. Secrets 管理
```bash
# 使用 Docker Secrets（Swarm 模式）
echo "my_secret" | docker secret create db_password -

# 使用环境变量加密
docker run --env-file .env.encrypted myapp:latest
```""",
        "created_at": "2026-06-02T15:30:00Z",
        "updated_at": "2026-06-02T15:30:00Z",
        "status": "indexed",
    },
    {
        "id": "doc_007",
        "title": "Redis 高可用架构与运维",
        "file_name": "redis-ha-operations.md",
        "content": """# Redis 高可用架构与运维

## 1. Redis Sentinel 高可用

### 架构原理
Sentinel 是 Redis 的高可用解决方案，提供监控、通知和自动故障转移。

### 配置示例
```conf
# sentinel.conf
sentinel monitor mymaster 127.0.0.1 6379 2
sentinel down-after-milliseconds mymaster 5000
sentinel failover-timeout mymaster 60000
sentinel parallel-syncs mymaster 1
```

### 故障转移测试
```bash
redis-cli -p 26379 sentinel get-master-addr-by-name mymaster
# 手动触发故障转移
redis-cli -p 26379 sentinel failover mymaster
```

## 2. Redis Cluster 集群

### 创建集群
```bash
redis-cli --cluster create \\
    127.0.0.1:7000 127.0.0.1:7001 127.0.0.1:7002 \\
    127.0.0.1:7003 127.0.0.1:7004 127.0.0.1:7005 \\
    --cluster-replicas 1
```

### 集群管理
```bash
# 查看集群状态
redis-cli cluster info
redis-cli cluster nodes

# 添加节点
redis-cli --cluster add-node 127.0.0.1:7006 127.0.0.1:7000

# 迁移槽位
redis-cli --cluster reshard 127.0.0.1:7000
```

## 3. 性能优化

### 内存优化
```conf
maxmemory 4gb
maxmemory-policy allkeys-lru
hash-max-ziplist-entries 512
hash-max-ziplist-value 64
```

### 慢查询日志
```conf
slowlog-log-slower-than 10000
slowlog-max-len 128
```""",
        "created_at": "2026-06-01T09:00:00Z",
        "updated_at": "2026-06-01T09:00:00Z",
        "status": "indexed",
    },
    {
        "id": "doc_008",
        "title": "ELK 日志分析平台搭建指南",
        "file_name": "elk-stack-setup.md",
        "content": """# ELK 日志分析平台搭建指南

## 1. 架构概述

ELK Stack = Elasticsearch + Logstash + Kibana + Beats

## 2. Elasticsearch 部署

### Docker Compose 部署
```yaml
version: '3'
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.10.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms2g -Xmx2g"
    ports:
      - "9200:9200"
    volumes:
      - es_data:/usr/share/elasticsearch/data
```

### 索引管理
```bash
# 创建索引模板
curl -X PUT "localhost:9200/_index_template/logs" \\
  -H 'Content-Type: application/json' -d '{
    "index_patterns": ["logs-*"],
    "template": {
      "settings": { "number_of_shards": 3 },
      "mappings": {
        "properties": {
          "@timestamp": { "type": "date" },
          "message": { "type": "text" },
          "level": { "type": "keyword" }
        }
      }
    }
  }'
```

## 3. Logstash 配置

```ruby
# logstash.conf
input {
  beats {
    port => 5044
  }
}

filter {
  grok {
    match => { "message" => "%{TIMESTAMP_ISO8601:timestamp} %{LOGLEVEL:level} %{GREEDYDATA:msg}" }
  }
  date {
    match => [ "timestamp", "yyyy-MM-dd HH:mm:ss" ]
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "logs-%{+YYYY.MM.dd}"
  }
}
```

## 4. Filebeat 配置

```yaml
# filebeat.yml
filebeat.inputs:
  - type: log
    paths:
      - /var/log/nginx/access.log
    fields:
      type: nginx

output.logstash:
  hosts: ["logstash:5044"]
```""",
        "created_at": "2026-05-30T14:20:00Z",
        "updated_at": "2026-05-30T14:20:00Z",
        "status": "indexed",
    },
    {
        "id": "doc_009",
        "title": "Ansible 自动化运维实战",
        "file_name": "ansible-automation-guide.md",
        "content": """# Ansible 自动化运维实战

## 1. 基础配置

### inventory 文件
```ini
# inventory/hosts.ini
[webservers]
web1 ansible_host=192.168.1.10
web2 ansible_host=192.168.1.11

[dbservers]
db1 ansible_host=192.168.1.20

[all:vars]
ansible_user=deploy
ansible_ssh_private_key_file=~/.ssh/deploy_key
```

### ansible.cfg
```ini
[defaults]
inventory = inventory/hosts.ini
remote_user = deploy
host_key_checking = False
retry_files_enabled = False
timeout = 30

[privilege_escalation]
become = True
become_method = sudo
become_user = root
```

## 2. Playbook 示例

### 部署 Web 应用
```yaml
---
- name: Deploy Web Application
  hosts: webservers
  vars:
    app_version: "1.2.3"
    app_port: 8080
  tasks:
    - name: Install dependencies
      apt:
        name: [nginx, python3, supervisor]
        state: present
        update_cache: yes

    - name: Deploy application
      copy:
        src: "dist/app-{{ app_version }}.tar.gz"
        dest: /opt/app/
      notify: restart app

    - name: Configure Nginx
      template:
        src: templates/nginx.conf.j2
        dest: /etc/nginx/conf.d/app.conf
      notify: reload nginx

  handlers:
    - name: restart app
      supervisorctl:
        name: myapp
        state: restarted

    - name: reload nginx
      service:
        name: nginx
        state: reloaded
```

## 3. Role 组织

```yaml
# roles/nginx/tasks/main.yml
- name: Install Nginx
  apt:
    name: nginx
    state: present

- name: Deploy config
  template:
    src: nginx.conf.j2
    dest: /etc/nginx/nginx.conf
  notify: reload nginx
```""",
        "created_at": "2026-05-28T10:15:00Z",
        "updated_at": "2026-05-28T10:15:00Z",
        "status": "indexed",
    },
    {
        "id": "doc_010",
        "title": "VPN 与零信任网络接入方案",
        "file_name": "vpn-zero-trust-access.md",
        "content": """# VPN 与零信任网络接入方案

## 1. WireGuard VPN 部署

### 服务端配置
```ini
# /etc/wireguard/wg0.conf
[Interface]
Address = 10.0.0.1/24
ListenPort = 51820
PrivateKey = <server_private_key>
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

[Peer]
PublicKey = <client_public_key>
AllowedIPs = 10.0.0.2/32
```

### 客户端配置
```ini
[Interface]
Address = 10.0.0.2/24
PrivateKey = <client_private_key>
DNS = 8.8.8.8

[Peer]
PublicKey = <server_public_key>
Endpoint = vpn.example.com:51820
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
```

## 2. 零信任架构

### 核心原则
- **永不信任，始终验证**: 所有请求都需要认证和授权
- **最小权限原则**: 仅授予完成工作所需的最小访问权限
- **微分段**: 将网络划分为细粒度的安全区域

### 实现方案
```
用户设备 → 身份验证 → 设备信任评估 → 动态授权 → 应用访问
```""",
        "created_at": "2026-05-25T16:40:00Z",
        "updated_at": "2026-05-25T16:40:00Z",
        "status": "indexed",
    },
    {
        "id": "doc_011",
        "title": "PostgreSQL 数据库性能调优",
        "file_name": "postgresql-performance-tuning.md",
        "content": """# PostgreSQL 数据库性能调优

## 1. 内存配置

```sql
-- postgresql.conf
shared_buffers = '4GB'            -- 总内存的 25%
effective_cache_size = '12GB'     -- 总内存的 75%
work_mem = '64MB'                 -- 每个连接的排序/哈希操作内存
maintenance_work_mem = '512MB'    -- 维护操作内存
wal_buffers = '64MB'
```

## 2. 查询优化

### 慢查询分析
```sql
-- 开启慢查询日志
ALTER SYSTEM SET log_min_duration_statement = 1000;  -- 超过1秒
ALTER SYSTEM SET log_statement = 'none';
ALTER SYSTEM SET log_duration = off;

-- 查看执行计划
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT * FROM orders WHERE user_id = 12345;
```

### 索引优化
```sql
-- 创建合适的索引
CREATE INDEX CONCURRENTLY idx_orders_user_id ON orders(user_id);
CREATE INDEX CONCURRENTLY idx_orders_created_at ON orders(created_at DESC);

-- 部分索引
CREATE INDEX idx_active_users ON users(email) WHERE status = 'active';

-- 查看索引使用情况
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

## 3. 连接池配置

```yaml
# pgbouncer.ini
[databases]
mydb = host=127.0.0.1 port=5432 dbname=mydb

[pgbouncer]
listen_port = 6432
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 50
reserve_pool_size = 10
```

## 4. 备份策略

```bash
# 使用 pg_basebackup
pg_basebackup -h localhost -U replicator -D /backup/base -Ft -z -P

# WAL 归档配置
archive_mode = on
archive_command = 'cp %p /archive/%f'
```""",
        "created_at": "2026-05-22T11:30:00Z",
        "updated_at": "2026-05-22T11:30:00Z",
        "status": "indexed",
    },
    {
        "id": "doc_012",
        "title": "CI/CD 流水线最佳实践",
        "file_name": "cicd-pipeline-best-practices.md",
        "content": """# CI/CD 流水线最佳实践

## 1. GitLab CI/CD

### .gitlab-ci.yml 示例
```yaml
stages:
  - build
  - test
  - security
  - deploy

variables:
  DOCKER_REGISTRY: registry.example.com

build:
  stage: build
  script:
    - docker build -t $DOCKER_REGISTRY/$CI_PROJECT_NAME:$CI_COMMIT_SHA .
    - docker push $DOCKER_REGISTRY/$CI_PROJECT_NAME:$CI_COMMIT_SHA

test:
  stage: test
  services:
    - postgres:15
    - redis:7
  variables:
    POSTGRES_DB: test_db
    POSTGRES_PASSWORD: test_pass
  script:
    - pytest --cov=app tests/

security_scan:
  stage: security
  script:
    - trivy image --exit-code 1 --severity HIGH $DOCKER_REGISTRY/$CI_PROJECT_NAME:$CI_COMMIT_SHA
    - bandit -r app/ -ll

deploy_staging:
  stage: deploy
  script:
    - kubectl set image deployment/$CI_PROJECT_NAME app=$DOCKER_REGISTRY/$CI_PROJECT_NAME:$CI_COMMIT_SHA
  environment:
    name: staging
  only:
    - develop
```

## 2. GitHub Actions

```yaml
# .github/workflows/ci.yml
name: CI Pipeline
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest --cov=app tests/
```""",
        "created_at": "2026-05-20T08:45:00Z",
        "updated_at": "2026-05-20T08:45:00Z",
        "status": "indexed",
    },
    {
        "id": "doc_013",
        "title": "Linux 网络故障排查手册",
        "file_name": "linux-network-troubleshooting.md",
        "content": """# Linux 网络故障排查手册

## 1. 常用排查工具

### 连通性测试
```bash
# Ping 测试
ping -c 4 8.8.8.8

# MTR 路由追踪
mtr -r -c 100 8.8.8.8

# Telnet 测试端口
telnet 192.168.1.100 3306

# Nmap 端口扫描
nmap -sT -p 1-65535 target_ip
```

### 抓包分析
```bash
# TCPDump 抓包
tcpdump -i eth0 port 80 -w capture.pcap

# 过滤特定流量
tcpdump -i eth0 'host 192.168.1.100 and port 443'

# 分析抓包文件
tshark -r capture.pcap -Y "http" -T fields -e http.host -e http.request.uri
```

## 2. DNS 问题排查

```bash
# DNS 解析测试
dig example.com
dig +trace example.com

# 检查 DNS 配置
cat /etc/resolv.conf

# 测试 DNS 响应时间
time dig example.com @8.8.8.8
```

## 3. TCP 连接问题

```bash
# 查看连接状态
ss -tunap | grep :80
netstat -tunap | grep ESTABLISHED

# TCP 重传统计
netstat -s | grep -i retrans

# TIME_WAIT 过多处理
echo 1 > /proc/sys/net/ipv4/tcp_tw_reuse
```

## 4. 防火墙排查

```bash
# iptables 规则查看
iptables -L -n -v
iptables -L -n -v --line-numbers

# firewalld 管理
firewall-cmd --list-all
firewall-cmd --add-port=8080/tcp --permanent
firewall-cmd --reload
```""",
        "created_at": "2026-05-18T13:10:00Z",
        "updated_at": "2026-05-18T13:10:00Z",
        "status": "indexed",
    },
    {
        "id": "doc_014",
        "title": "容器编排 Helm Chart 开发指南",
        "file_name": "helm-chart-development.md",
        "content": """# 容器编排 Helm Chart 开发指南

## 1. Chart 结构

```
mychart/
  Chart.yaml
  values.yaml
  charts/
  templates/
    deployment.yaml
    service.yaml
    ingress.yaml
    configmap.yaml
    secrets.yaml
    _helpers.tpl
    hpa.yaml
    serviceaccount.yaml
```

## 2. 模板语法

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "mychart.fullname" . }}
  labels:
    {{- include "mychart.labels" . | nindent 4 }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      {{- include "mychart.selectorLabels" . | nindent 6 }}
  template:
    spec:
      containers:
        - name: {{ .Chart.Name }}
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          ports:
            - containerPort: {{ .Values.service.targetPort }}
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
```

## 3. 常用命令

```bash
# 打包 Chart
helm package mychart/

# 安装
helm install my-release mychart/ -f values-prod.yaml

# 升级
helm upgrade my-release mychart/ --set image.tag=1.2.0

# 回滚
helm rollback my-release 1

# 模板渲染测试
helm template my-release mychart/ -f values-prod.yaml
```""",
        "created_at": "2026-05-15T10:20:00Z",
        "updated_at": "2026-05-15T10:20:00Z",
        "status": "indexed",
    },
    {
        "id": "doc_015",
        "title": "MongoDB 运维与优化指南",
        "file_name": "mongodb-operations-guide.md",
        "content": """# MongoDB 运维与优化指南

## 1. 副本集部署

### 初始化副本集
```javascript
// 连接主节点后执行
rs.initiate({
  _id: "rs0",
  members: [
    { _id: 0, host: "mongo1:27017", priority: 2 },
    { _id: 1, host: "mongo2:27017", priority: 1 },
    { _id: 2, host: "mongo3:27017", priority: 1 }
  ]
})
```

### 查看副本集状态
```javascript
rs.status()
rs.conf()
db.getReplicationInfo()
```

## 2. 性能优化

### 索引优化
```javascript
// 创建复合索引
db.orders.createIndex({ user_id: 1, created_at: -1 })

// 查看索引使用情况
db.orders.aggregate([{ $indexStats: {} }])

// 慢查询分析
db.setProfilingLevel(1, { slowms: 100 })
db.system.profile.find().sort({ ts: -1 }).limit(10)
```

### 内存优化
```javascript
// 查看内存使用
db.serverStatus().wiredTiger.cache

// 预热索引
db.collection.reIndex()
```

## 3. 备份恢复

```bash
# 使用 mongodump
mongodump --uri="mongodb://user:pass@host:27017/mydb" --out=/backup/

# 使用 mongorestore
mongorestore --uri="mongodb://host:27017" --dir=/backup/mydb

# Oplog 恢复
mongorestore --oplogReplay --oplogLimit="1686000000:1"
```""",
        "created_at": "2026-05-12T14:55:00Z",
        "updated_at": "2026-05-12T14:55:00Z",
        "status": "indexed",
    },
    {
        "id": "doc_016",
        "title": "Kubernetes Ingress Controller 配置指南",
        "file_name": "k8s-ingress-guide.md",
        "content": """# Kubernetes Ingress Controller 配置指南

## 1. Nginx Ingress 部署

```bash
# 安装 Ingress Controller
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm install ingress-nginx ingress-nginx/ingress-nginx \\
  --namespace ingress-nginx --create-namespace
```

## 2. Ingress 资源配置

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - app.example.com
      secretName: app-tls
  rules:
    - host: app.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: web-service
                port:
                  number: 80
```

## 3. 路由策略

```yaml
# 基于路径的路由
spec:
  rules:
    - http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: api-service
                port:
                  number: 8080
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend-service
                port:
                  number: 80
```""",
        "created_at": "2026-05-10T09:30:00Z",
        "updated_at": "2026-05-10T09:30:00Z",
        "status": "indexed",
    },
    {
        "id": "doc_017",
        "title": "Linux 磁盘管理与LVM实战",
        "file_name": "linux-disk-lvm-guide.md",
        "content": """# Linux 磁盘管理与LVM实战

## 1. 磁盘分区管理

```bash
# 查看磁盘信息
lsblk
fdisk -l
parted -l

# GPT 分区
gdisk /dev/sdb
# 或使用 parted
parted /dev/sdb mklabel gpt
parted /dev/sdb mkpart primary ext4 0% 100%
```

## 2. LVM 管理

### 创建逻辑卷
```bash
# 创建物理卷
pvcreate /dev/sdb1 /dev/sdc1

# 创建卷组
vgcreate data_vg /dev/sdb1 /dev/sdc1

# 创建逻辑卷
lvcreate -L 100G -n data_lv data_vg

# 格式化并挂载
mkfs.ext4 /dev/data_vg/data_lv
mount /dev/data_vg/data_lv /data
```

### 扩容操作
```bash
# 扩展逻辑卷
lvextend -L +50G /dev/data_vg/data_lv

# 扩展文件系统
resize2fs /dev/data_vg/data_lv    # ext4
xfs_growfs /data                    # xfs
```

### 快照管理
```bash
# 创建快照
lvcreate -L 10G -s -n data_snap /dev/data_vg/data_lv

# 恢复快照
lvconvert --merge /dev/data_vg/data_snap
```

## 3. RAID 配置

```bash
# 创建 RAID 5
mdadm --create /dev/md0 --level=5 --raid-devices=3 /dev/sd{b,c,d}1

# 查看状态
cat /proc/mdstat
mdadm --detail /dev/md0

# 保存配置
mdadm --detail --scan >> /etc/mdadm.conf
```""",
        "created_at": "2026-05-08T16:20:00Z",
        "updated_at": "2026-05-08T16:20:00Z",
        "status": "indexed",
    },
    {
        "id": "doc_018",
        "title": "容器化微服务部署规范",
        "file_name": "containerized-microservices-deployment.md",
        "content": """# 容器化微服务部署规范

## 1. Dockerfile 编写规范

```dockerfile
# 多阶段构建
FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o server ./cmd/server

FROM alpine:3.18
RUN apk --no-cache add ca-certificates tzdata
COPY --from=builder /app/server /server
COPY --from=builder /app/configs /configs
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s \\
  CMD wget -qO- http://localhost:8080/health || exit 1
ENTRYPOINT ["/server"]
```

## 2. K8s 资源配额

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: team-quota
spec:
  hard:
    requests.cpu: "20"
    requests.memory: 40Gi
    limits.cpu: "40"
    limits.memory: 80Gi
    pods: "50"
```

## 3. 服务网格 Istio

```yaml
# 流量管理
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: my-service
spec:
  hosts:
    - my-service
  http:
    - route:
        - destination:
            host: my-service
            subset: v1
          weight: 90
        - destination:
            host: my-service
            subset: v2
          weight: 10
```""",
        "created_at": "2026-05-05T11:45:00Z",
        "updated_at": "2026-05-05T11:45:00Z",
        "status": "indexed",
    },
    {
        "id": "doc_019",
        "title": "Kafka 消息队列运维指南",
        "file_name": "kafka-operations-guide.md",
        "content": """# Kafka 消息队列运维指南

## 1. 集群部署

### Docker Compose 部署
```yaml
version: '3'
services:
  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181

  kafka:
    image: confluentinc/cp-kafka:7.5.0
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_NUM_PARTITIONS: 3
      KAFKA_DEFAULT_REPLICATION_FACTOR: 1
```

## 2. Topic 管理

```bash
# 创建 Topic
kafka-topics.sh --create --topic orders \\
  --bootstrap-server localhost:9092 \\
  --partitions 6 --replication-factor 3

# 查看 Topic
kafka-topics.sh --describe --topic orders \\
  --bootstrap-server localhost:9092

# 修改分区数
kafka-topics.sh --alter --topic orders \\
  --partitions 12 --bootstrap-server localhost:9092
```

## 3. 消费者组监控

```bash
# 查看消费者组
kafka-consumer-groups.sh --list --bootstrap-server localhost:9092

# 查看消费进度
kafka-consumer-groups.sh --describe --group my-group \\
  --bootstrap-server localhost:9092
```""",
        "created_at": "2026-05-02T08:30:00Z",
        "updated_at": "2026-05-02T08:30:00Z",
        "status": "indexed",
    },
    {
        "id": "doc_020",
        "title": "Elasticsearch 集群运维手册",
        "file_name": "elasticsearch-cluster-operations.md",
        "content": """# Elasticsearch 集群运维手册

## 1. 集群健康检查

```bash
# 查看集群状态
curl -s localhost:9200/_cluster/health?pretty

# 节点状态
curl -s localhost:9200/_cat/nodes?v

# 索引状态
curl -s localhost:9200/_cat/indices?v&s=store.size:desc
```

## 2. 索引生命周期管理

```json
PUT _index_template/logs-template
{
  "index_patterns": ["logs-*"],
  "template": {
    "settings": {
      "number_of_shards": 3,
      "index.lifecycle.name": "logs-policy",
      "index.lifecycle.rollover_alias": "logs"
    }
  }
}

PUT _ilm/policy/logs-policy
{
  "policy": {
    "phases": {
      "hot": {
        "actions": {
          "rollover": {
            "max_size": "50gb",
            "max_age": "1d"
          }
        }
      },
      "warm": {
        "min_age": "7d",
        "actions": {
          "shrink": { "number_of_shards": 1 },
          "forcemerge": { "max_num_segments": 1 }
        }
      },
      "delete": {
        "min_age": "30d",
        "actions": { "delete": {} }
      }
    }
  }
}
```

## 3. 性能优化

```bash
# 线程池状态
curl -s localhost:9200/_cat/thread_pool?v

# 热点线程
curl -s localhost:9200/_nodes/hot_threads

# 分片重分配
curl -X POST localhost:9200/_cluster/reroute?retry_failed=true
```""",
        "created_at": "2026-04-28T15:10:00Z",
        "updated_at": "2026-04-28T15:10:00Z",
        "status": "indexed",
    },
    {
        "id": "doc_021",
        "title": "SSH 安全加固与密钥管理",
        "file_name": "ssh-security-key-management.md",
        "content": """# SSH 安全加固与密钥管理

## 1. SSH 服务加固

### 修改 /etc/ssh/sshd_config
```
# 禁用密码登录
PasswordAuthentication no
ChallengeResponseAuthentication no

# 限制登录用户
AllowUsers deploy admin

# 修改默认端口
Port 22222

# 禁用 root 登录
PermitRootLogin no

# 启用公钥认证
PubkeyAuthentication yes
AuthorizedKeysFile .ssh/authorized_keys

# 超时设置
ClientAliveInterval 300
ClientAliveCountMax 2

# 限制登录尝试
MaxAuthTries 3
LoginGraceTime 60
```

## 2. SSH 密钥管理

```bash
# 生成 Ed25519 密钥（推荐）
ssh-keygen -t ed25519 -C "admin@example.com"

# 使用 ssh-agent 管理密钥
eval $(ssh-agent -s)
ssh-add ~/.ssh/id_ed25519

# SSH 跳板机配置
Host jump
    HostName jump.example.com
    Port 22222
    User deploy

Host target
    HostName 10.0.0.100
    User deploy
    ProxyJump jump
```

## 3. SSH 审计

```bash
# 查看 SSH 日志
journalctl -u sshd --since "1 hour ago"

# 暴力破解检测
grep "Failed password" /var/log/auth.log | awk '{print $11}' | sort | uniq -c | sort -rn
```""",
        "created_at": "2026-04-25T09:15:00Z",
        "updated_at": "2026-04-25T09:15:00Z",
        "status": "indexed",
    },
    {
        "id": "doc_022",
        "title": "系统日志分析与故障诊断",
        "file_name": "system-log-analysis.md",
        "content": """# 系统日志分析与故障诊断

## 1. systemd 日志管理

```bash
# 查看服务日志
journalctl -u nginx --since "2 hours ago"

# 实时跟踪
journalctl -u nginx -f

# 按优先级过滤
journalctl -p err -b    # 本次启动的错误日志

# 导出日志
journalctl -u nginx --since "2026-06-01" --until "2026-06-09" > nginx.log
```

## 2. 常用日志分析

```bash
# 统计 HTTP 状态码
awk '{print $9}' access.log | sort | uniq -c | sort -rn

# 统计访问最多的 IP
awk '{print $1}' access.log | sort | uniq -c | sort -rn | head -20

# 分析响应时间
awk '{print $NF, $7}' access.log | sort -rn | head -20

# 错误日志分析
grep -E "ERROR|FATAL|Exception" app.log | tail -100
```

## 3. 日志轮转配置

```conf
# /etc/logrotate.d/myapp
/var/log/myapp/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
    dateext
    dateformat -%Y%m%d
}
```""",
        "created_at": "2026-04-22T14:30:00Z",
        "updated_at": "2026-04-22T14:30:00Z",
        "status": "indexed",
    },
    {
        "id": "doc_023",
        "title": "Nginx 高性能负载均衡配置",
        "file_name": "nginx-load-balancing.md",
        "content": """# Nginx 高性能负载均衡配置

## 1. 负载均衡算法

```nginx
# 轮询（默认）
upstream backend {
    server 10.0.0.1:8080;
    server 10.0.0.2:8080;
}

# 加权轮询
upstream backend {
    server 10.0.0.1:8080 weight=3;
    server 10.0.0.2:8080 weight=1;
}

# IP 哈希（会话保持）
upstream backend {
    ip_hash;
    server 10.0.0.1:8080;
    server 10.0.0.2:8080;
}

# 最少连接
upstream backend {
    least_conn;
    server 10.0.0.1:8080;
    server 10.0.0.2:8080;
}
```

## 2. 健康检查

```nginx
upstream backend {
    server 10.0.0.1:8080 max_fails=3 fail_timeout=30s;
    server 10.0.0.2:8080 max_fails=3 fail_timeout=30s;
}

proxy_next_upstream error timeout http_502 http_503;
proxy_next_upstream_tries 3;
```

## 3. 缓存配置

```nginx
# 缓存路径
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=my_cache:100m max_size=10g;

server {
    location /api/ {
        proxy_cache my_cache;
        proxy_cache_valid 200 10m;
        proxy_cache_valid 404 1m;
        proxy_cache_key "$scheme$request_method$host$request_uri";
        add_header X-Cache-Status $upstream_cache_status;
    }
}
```""",
        "created_at": "2026-04-19T10:50:00Z",
        "updated_at": "2026-04-19T10:50:00Z",
        "status": "indexed",
    },
    {
        "id": "doc_024",
        "title": "etcd 集群部署与运维",
        "file_name": "etcd-cluster-operations.md",
        "content": """# etcd 集群部署与运维

## 1. 集群部署

### 二进制部署
```bash
# 启动 etcd 节点
etcd --name etcd1 \\
    --initial-advertise-peer-urls https://10.0.0.1:2380 \\
    --listen-peer-urls https://10.0.0.1:2380 \\
    --listen-client-urls https://10.0.0.1:2379,https://127.0.0.1:2379 \\
    --advertise-client-urls https://10.0.0.1:2379 \\
    --initial-cluster-token etcd-cluster-1 \\
    --initial-cluster etcd1=https://10.0.0.1:2380,etcd2=https://10.0.0.2:2380,etcd3=https://10.0.0.3:2380 \\
    --initial-cluster-state new
```

## 2. 健康检查

```bash
# 成员列表
etcdctl member list --write-out=table

# 集群健康
etcdctl endpoint health --cluster

# 端点状态
etcdctl endpoint status --cluster --write-out=table
```

## 3. 数据维护

```bash
# 备份
etcdctl snapshot save /backup/etcd-snapshot-$(date +%Y%m%d).db

# 恢复
etcdctl snapshot restore /backup/etcd-snapshot.db --data-dir=/var/lib/etcd-restored

# 碎片整理
etcdctl defrag --cluster
```""",
        "created_at": "2026-04-15T16:25:00Z",
        "updated_at": "2026-04-15T16:25:00Z",
        "status": "indexed",
    },
    {
        "id": "doc_025",
        "title": "容器镜像仓库 Harbor 部署指南",
        "file_name": "harbor-registry-deployment.md",
        "content": """# 容器镜像仓库 Harbor 部署指南

## 1. 安装部署

### 下载与配置
```bash
# 下载 Harbor
wget https://github.com/goharbor/harbor/releases/download/v2.9.0/harbor-offline-installer-v2.9.0.tgz
tar xzf harbor-offline-installer-v2.9.0.tgz
cd harbor

# 复制并修改配置
cp harbor.yml.tmpl harbor.yml
```

### harbor.yml 关键配置
```yaml
hostname: harbor.example.com
http:
  port: 80
https:
  port: 443
  certificate: /etc/ssl/certs/harbor.crt
  private_key: /etc/ssl/private/harbor.key
harbor_admin_password: Harbor12345
database:
  password: root123
data_volume: /data/harbor
```

## 2. 镜像同步

```bash
# 登录 Harbor
docker login harbor.example.com

# 推送镜像
docker tag myapp:latest harbor.example.com/myproject/myapp:latest
docker push harbor.example.com/myproject/myapp:latest

# 使用 Skopeo 同步
skopeo sync docker://harbor-src.example.com/app docker://harbor-dst.example.com/app
```

## 3. 项目管理

```bash
# 使用 Harbor API 创建项目
curl -k -u admin:Harbor12345 -X POST \\
  https://harbor.example.com/api/v2.0/projects \\
  -H "Content-Type: application/json" \\
  -d '{"project_name": "production", "public": false}'
```""",
        "created_at": "2026-04-12T12:00:00Z",
        "updated_at": "2026-04-12T12:00:00Z",
        "status": "indexed",
    },
    {
        "id": "doc_026",
        "title": "TCP/IP 协议与网络编程基础",
        "file_name": "tcpip-network-programming.md",
        "content": """# TCP/IP 协议与网络编程基础

## 1. TCP 三次握手与四次挥手

### 三次握手
```
Client → SYN → Server
Client ← SYN+ACK ← Server
Client → ACK → Server
```

### 四次挥手
```
Client → FIN → Server
Client ← ACK ← Server
Client ← FIN ← Server
Client → ACK → Server
```

## 2. Socket 编程示例

### Python TCP Server
```python
import socket

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(('0.0.0.0', 8080))
server.listen(5)

while True:
    conn, addr = server.accept()
    data = conn.recv(4096)
    conn.sendall(b'HTTP/1.1 200 OK\\r\\n\\r\\nHello')
    conn.close()
```

## 3. 网络性能调优

```bash
# TCP 缓冲区
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216

# TCP BBR 拥塞控制
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr
```""",
        "created_at": "2026-04-10T09:35:00Z",
        "updated_at": "2026-04-10T09:35:00Z",
        "status": "indexed",
    },
    {
        "id": "doc_027",
        "title": "Kubernetes Pod 调度策略详解",
        "file_name": "k8s-pod-scheduling.md",
        "content": """# Kubernetes Pod 调度策略详解

## 1. nodeSelector

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: gpu-pod
spec:
  nodeSelector:
    accelerator: nvidia-tesla-v100
  containers:
    - name: gpu-app
      image: myapp:latest
```

## 2. Affinity 亲和性

```yaml
spec:
  affinity:
    # 节点亲和性
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
          - matchExpressions:
              - key: topology.kubernetes.io/zone
                operator: In
                values: ["zone-a", "zone-b"]

    # Pod 反亲和性（分散部署）
    podAntiAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
        - weight: 100
          podAffinityTerm:
            labelSelector:
              matchExpressions:
                - key: app
                  operator: In
                  values: ["web"]
            topologyKey: kubernetes.io/hostname
```

## 3. Taint 与 Toleration

```bash
# 给节点添加 Taint
kubectl taint nodes node1 dedicated=gpu:NoSchedule

# Pod 配置 Toleration
spec:
  tolerations:
    - key: "dedicated"
      operator: "Equal"
      value: "gpu"
      effect: "NoSchedule"
```

## 4. 资源请求与限制

```yaml
containers:
  - name: app
    resources:
      requests:
        cpu: "500m"
        memory: "256Mi"
      limits:
        cpu: "1"
        memory: "512Mi"
```""",
        "created_at": "2026-04-08T11:20:00Z",
        "updated_at": "2026-04-08T11:20:00Z",
        "status": "indexed",
    },
    {
        "id": "doc_028",
        "title": "系统安全基线检查清单",
        "file_name": "security-baseline-checklist.md",
        "content": """# 系统安全基线检查清单

## 1. 账户安全

### 密码策略
```bash
# /etc/login.defs
PASS_MAX_DAYS   90
PASS_MIN_DAYS   7
PASS_MIN_LEN    12
PASS_WARN_AGE   14

# 检查空密码账户
awk -F: '($2 == "") {print $1}' /etc/shadow

# 检查 UID 为 0 的账户
awk -F: '($3 == 0) {print $1}' /etc/passwd
```

### 登录限制
```bash
# /etc/pam.d/sshd
auth required pam_tally2.so deny=5 unlock_time=900

# 超时自动注销
# /etc/profile
TMOUT=600
export TMOUT
```

## 2. 文件权限

```bash
# 关键文件权限检查
stat -c "%a %U %G" /etc/passwd /etc/shadow /etc/sudoers

# 查找 SUID 文件
find / -perm -4000 -type f 2>/dev/null

# 查找 world-writable 文件
find / -perm -0002 -type f 2>/dev/null
```

## 3. 服务安全

```bash
# 禁用不必要的服务
systemctl disable avahi-daemon
systemctl disable cups
systemctl disable rpcbind

# 检查监听端口
ss -tlnp
```""",
        "created_at": "2026-04-05T14:40:00Z",
        "updated_at": "2026-04-05T14:40:00Z",
        "status": "indexed",
    },
    {
        "id": "doc_029",
        "title": "Terraform 基础设施即代码实践",
        "file_name": "terraform-iac-practice.md",
        "content": """# Terraform 基础设施即代码实践

## 1. Provider 配置

```hcl
# main.tf
terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  backend "s3" {
    bucket = "terraform-state"
    key    = "prod/terraform.tfstate"
    region = "ap-east-1"
  }
}

provider "aws" {
  region = "ap-east-1"
}
```

## 2. 资源定义

```hcl
# EC2 实例
resource "aws_instance" "web" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.micro"
  key_name      = aws_key_pair.deployer.key_name

  vpc_security_group_ids = [aws_security_group.web_sg.id]

  tags = {
    Name = "web-server"
  }
}

# 安全组
resource "aws_security_group" "web_sg" {
  name        = "web-sg"
  description = "Web server security group"

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
```

## 3. 常用命令

```bash
terraform init
terraform plan -out=tfplan
terraform apply tfplan
terraform state list
terraform destroy
```""",
        "created_at": "2026-04-02T10:10:00Z",
        "updated_at": "2026-04-02T10:10:00Z",
        "status": "indexed",
    },
    {
        "id": "doc_030",
        "title": "Kubernetes HPA 自动伸缩配置",
        "file_name": "k8s-hpa-autoscaling.md",
        "content": """# Kubernetes HPA 自动伸缩配置

## 1. 基于 CPU 的 HPA

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

## 2. 基于内存的 HPA

```yaml
metrics:
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## 3. 基于自定义指标

```yaml
metrics:
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "100"
```

## 4. PodDisruptionBudget

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: web
```""",
        "created_at": "2026-03-30T15:45:00Z",
        "updated_at": "2026-03-30T15:45:00Z",
        "status": "indexed",
    },
    {
        "id": "doc_031",
        "title": "MySQL 主从复制配置指南",
        "file_name": "mysql-replication-setup.md",
        "content": """# MySQL 主从复制配置指南

## 1. 主库配置

### my.cnf 配置
```ini
[mysqld]
server-id = 1
log-bin = mysql-bin
binlog-format = ROW
binlog-do-db = mydb
sync_binlog = 1
innodb_flush_log_at_trx_commit = 1
```

### 创建复制用户
```sql
CREATE USER 'repl_user'@'%' IDENTIFIED BY 'strong_password';
GRANT REPLICATION SLAVE ON *.* TO 'repl_user'@'%';
FLUSH PRIVILEGES;

-- 查看主库状态
SHOW MASTER STATUS;
```

## 2. 从库配置

### my.cnf 配置
```ini
[mysqld]
server-id = 2
relay-log = relay-bin
read_only = 1
super_read_only = 1
```

### 配置复制
```sql
CHANGE MASTER TO
    MASTER_HOST = '10.0.0.1',
    MASTER_USER = 'repl_user',
    MASTER_PASSWORD = 'strong_password',
    MASTER_LOG_FILE = 'mysql-bin.000001',
    MASTER_LOG_POS = 154;

START SLAVE;
SHOW SLAVE STATUS\\G
```

## 3. 复制监控

```sql
-- 检查从库状态
SHOW SLAVE STATUS\\G
-- 关注: Slave_IO_Running, Slave_SQL_Running, Seconds_Behind_Master

-- 主库查看从库连接
SHOW SLAVE HOSTS;
```""",
        "created_at": "2026-03-28T09:20:00Z",
        "updated_at": "2026-03-28T09:20:00Z",
        "status": "indexed",
    },
    {
        "id": "doc_032",
        "title": "Linux 进程管理与调试技巧",
        "file_name": "linux-process-management.md",
        "content": """# Linux 进程管理与调试技巧

## 1. 进程监控

```bash
# 查看进程
ps aux | grep nginx
ps -eo pid,ppid,%cpu,%mem,cmd --sort=-%cpu | head -20

# 实时监控
top -Hp <pid>    # 查看线程
htop              # 增强版 top

# 进程树
pstree -p <pid>
```

## 2. 进程调试

```bash
# strace 跟踪系统调用
strace -p <pid> -e trace=network
strace -f -p <pid> -o trace.log

# ltrace 跟踪库调用
ltrace -p <pid>

# gdb 调试
gdb -p <pid>
(gdb) bt          # 查看调用栈
(gdb) info threads  # 查看所有线程
```

## 3. 信号管理

```bash
# 常用信号
kill -15 <pid>    # SIGTERM 正常终止
kill -9 <pid>     # SIGKILL 强制终止
kill -1 <pid>     # SIGHUP 重载配置

# 查看信号
kill -l
```""",
        "created_at": "2026-03-25T14:10:00Z",
        "updated_at": "2026-03-25T14:10:00Z",
        "status": "indexed",
    },
    {
        "id": "doc_033",
        "title": "Git 分支管理与工作流",
        "file_name": "git-branch-workflow.md",
        "content": """# Git 分支管理与工作流

## 1. 分支策略

### Git Flow
```
main (production)
  └── develop
       ├── feature/login
       ├── feature/dashboard
       ├── release/v1.2.0
       └── hotfix/fix-login
```

### Trunk-Based Development
```
main (trunk)
  ├── feature/short-lived-1
  └── feature/short-lived-2
```

## 2. 常用命令

```bash
# 创建并切换分支
git checkout -b feature/new-api
git switch -c feature/new-api

# 合并分支
git merge --no-ff feature/new-api

# 变基
git rebase main

# Cherry-pick
git cherry-pick <commit-hash>

# 暂存
git stash
git stash pop
git stash list
```

## 3. 冲突解决

```bash
# 查看冲突
git status

# 解决后标记为已解决
git add <resolved-file>
git commit
```""",
        "created_at": "2026-03-22T11:35:00Z",
        "updated_at": "2026-03-22T11:35:00Z",
        "status": "indexed",
    },
    {
        "id": "doc_034",
        "title": "Ceph 分布式存储运维指南",
        "file_name": "ceph-storage-operations.md",
        "content": """# Ceph 分布式存储运维指南

## 1. 集群监控

```bash
# 集群状态
ceph -s
ceph health detail

# OSD 列表
ceph osd tree
ceph osd df

# 存储池
ceph osd pool ls detail
ceph df
```

## 2. 存储池管理

```bash
# 创建存储池
ceph osd pool create mypool 64 64 replicated

# 设置副本数
ceph osd pool set mypool size 3

# 启用 rbd
ceph osd pool application enable mypool rbd
```

## 3. RBD 管理

```bash
# 创建镜像
rbd create mypool/disk1 --size 100G

# 列出镜像
rbd ls mypool

# 调整大小
rbd resize mypool/disk1 --size 200G

# 快照
rbd snap create mypool/disk1@snap1
rbd snap rollback mypool/disk1@snap1
```""",
        "created_at": "2026-03-20T16:55:00Z",
        "updated_at": "2026-03-20T16:55:00Z",
        "status": "indexed",
    },
    {
        "id": "doc_035",
        "title": "Web 应用常见漏洞与防护",
        "file_name": "web-app-vulnerabilities-protection.md",
        "content": """# Web 应用常见漏洞与防护

## 1. SQL 注入防护

```python
# 参数化查询（推荐）
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))

# ORM 查询
user = User.objects.get(id=user_id)
```

## 2. XSS 防护

```html
<!-- 输出编码 -->
<div>{{ user_input | escape }}</div>

<!-- CSP 头 -->
Content-Security-Policy: default-src 'self'; script-src 'self'
```

## 3. CSRF 防护

```python
# Django CSRF Token
{% csrf_token %}

# 请求验证
@csrf_protect
def my_view(request):
    pass
```

## 4. 文件上传安全

```python
# 文件类型验证
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg'}
def allowed_file(filename):
    return '.' in filename and \\
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 文件大小限制
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
```""",
        "created_at": "2026-03-18T10:25:00Z",
        "updated_at": "2026-03-18T10:25:00Z",
        "status": "indexed",
    },
    {
        "id": "doc_036",
        "title": "容器日志收集与分析方案",
        "file_name": "container-log-collection-analysis.md",
        "content": """# 容器日志收集与分析方案

## 1. 日志驱动配置

### Docker 日志配置
```json
// /etc/docker/daemon.json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

### K8s 日志收集
```yaml
# DaemonSet 部署 Fluentd
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluentd
spec:
  selector:
    matchLabels:
      app: fluentd
  template:
    spec:
      containers:
        - name: fluentd
          image: fluent/fluentd-kubernetes-daemonset:v1.16-debian-elasticsearch8
          volumeMounts:
            - name: varlog
              mountPath: /var/log
            - name: containers
              mountPath: /var/lib/docker/containers
              readOnly: true
```

## 2. 日志格式规范

```json
{
  "timestamp": "2026-06-09T10:30:00Z",
  "level": "INFO",
  "service": "user-api",
  "trace_id": "abc123def456",
  "message": "User login successful",
  "metadata": {
    "user_id": "12345",
    "ip": "192.168.1.100"
  }
}
```""",
        "created_at": "2026-03-15T13:50:00Z",
        "updated_at": "2026-03-15T13:50:00Z",
        "status": "indexed",
    },
    {
        "id": "doc_037",
        "title": "系统性能压测与基准测试",
        "file_name": "performance-benchmark-testing.md",
        "content": """# 系统性能压测与基准测试

## 1. CPU 压测

```bash
# sysbench CPU
sysbench cpu --threads=4 --time=60 run

# stress-ng
stress-ng --cpu 4 --timeout 60s --metrics-brief
```

## 2. 内存压测

```bash
# sysbench 内存
sysbench memory --memory-block-size=1M --memory-total-size=10G run

# dd 测试
dd if=/dev/zero of=/tmp/test bs=1M count=1024 oflag=direct
```

## 3. 磁盘 I/O 压测

```bash
# fio 随机读写
fio --name=randread --ioengine=libaio --iodepth=16 \\
    --rw=randread --bs=4k --direct=1 --size=1G --numjobs=4

# dd 顺序写入
dd if=/dev/zero of=/tmp/test bs=1M count=1024
```

## 4. 网络压测

```bash
# iperf3
# 服务端
iperf3 -s

# 客户端
iperf3 -c 10.0.0.1 -t 30 -P 4
```""",
        "created_at": "2026-03-12T09:15:00Z",
        "updated_at": "2026-03-12T09:15:00Z",
        "status": "indexed",
    },
    {
        "id": "doc_038",
        "title": "Prometheus 告警规则编写指南",
        "file_name": "prometheus-alerting-rules.md",
        "content": """# Prometheus 告警规则编写指南

## 1. 告警规则模板

```yaml
# alert_rules.yml
groups:
  - name: application_alerts
    rules:
      - alert: HighErrorRate
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[5m]))
          /
          sum(rate(http_requests_total[5m]))
          > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "HTTP 5xx 错误率超过 5%"
          description: "当前错误率: {{ $value | humanizePercentage }}"

      - alert: HighLatency
        expr: |
          histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le)) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "P95 延迟超过 2 秒"
          description: "当前 P95: {{ $value }}s"
```

## 2. Alertmanager 配置

```yaml
route:
  group_by: ['alertname', 'severity']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'slack-notifications'

receivers:
  - name: 'slack-notifications'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/xxx'
        channel: '#alerts'
        text: "{{ .CommonAnnotations.summary }}"
```""",
        "created_at": "2026-03-10T14:30:00Z",
        "updated_at": "2026-03-10T14:30:00Z",
        "status": "indexed",
    },
    {
        "id": "doc_039",
        "title": "Kubernetes 服务网格 Istio 实践",
        "file_name": "istio-service-mesh-practice.md",
        "content": """# Kubernetes 服务网格 Istio 实践

## 1. 安装 Istio

```bash
# 下载 Istio
curl -L https://istio.io/downloadIstio | sh -
cd istio-*
export PATH=$PWD/bin:$PATH

# 安装
istioctl install --set profile=demo -y
```

## 2. 流量管理

```yaml
# 金丝雀发布
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
    - reviews
  http:
    - route:
        - destination:
            host: reviews
            subset: v1
          weight: 90
        - destination:
            host: reviews
            subset: v2
          weight: 10
```

## 3. 安全策略

```yaml
# mTLS 强制
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT

# 授权策略
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: reviews-viewer
spec:
  selector:
    matchLabels:
      app: reviews
  rules:
    - from:
        - source:
            principals: ["cluster.local/ns/default/sa/bookinfo-productpage"]
```""",
        "created_at": "2026-03-08T11:45:00Z",
        "updated_at": "2026-03-08T11:45:00Z",
        "status": "indexed",
    },
    {
        "id": "doc_040",
        "title": "数据库连接池配置与优化",
        "file_name": "database-connection-pool-tuning.md",
        "content": """# 数据库连接池配置与优化

## 1. HikariCP 配置（Java）

```yaml
spring:
  datasource:
    hikari:
      minimum-idle: 5
      maximum-pool-size: 20
      idle-timeout: 30000
      max-lifetime: 1800000
      connection-timeout: 30000
      pool-name: MyHikariCP
```

## 2. SQLAlchemy 连接池（Python）

```python
from sqlalchemy import create_engine

engine = create_engine(
    "postgresql://user:pass@localhost/db",
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True
)
```

## 3. 连接池监控

```sql
-- MySQL 查看连接
SHOW STATUS LIKE 'Threads_connected';
SHOW PROCESSLIST;

-- PostgreSQL
SELECT count(*) FROM pg_stat_activity;
SELECT state, count(*) FROM pg_stat_activity GROUP BY state;
```""",
        "created_at": "2026-03-05T16:20:00Z",
        "updated_at": "2026-03-05T16:20:00Z",
        "status": "indexed",
    },
]


@router.post("/assistant/refresh")
async def refresh_knowledge_base():
    """刷新知识库状态"""
    global _knowledge_docs
    # 如果知识库为空，加载示例文档
    if not _knowledge_docs:
        _knowledge_docs = _knowledge_sample_docs.copy()

    return {
        "refreshed": True,
        "documents_count": len(_knowledge_docs),
        "vector_count": len(_knowledge_docs) * 100,  # 模拟向量数
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "message": "知识库已刷新，文档索引已更新",
    }


@router.post("/assistant/upload-knowledge-file")
async def upload_knowledge_file():
    """上传知识库文件（Demo 模式下返回模拟结果）"""
    return {
        "uploaded": True,
        "document_id": f"doc_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "filename": "uploaded-file.txt",
        "file_size": 2048,
        "message": "文件上传成功，已加入知识索引",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@router.post("/assistant/add-document")
async def add_knowledge_document():
    """手动添加文档到知识库"""
    global _knowledge_doc_counter, _knowledge_docs
    _knowledge_doc_counter += 1
    doc_id = f"doc_{_knowledge_doc_counter:03d}"

    _knowledge_docs.append({
        "id": doc_id,
        "title": "新文档",
        "file_name": "new-document.txt",
        "content": "文档内容",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "status": "indexed",
    })

    return {
        "added": True,
        "document_id": doc_id,
        "message": "文档添加成功，已加入知识索引",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@router.get("/assistant/config")
async def get_assistant_config():
    """获取配置参数"""
    from backend.config import settings as _settings
    return {
        "service": "AICloudOps",
        "config": {
            "app_name": _settings.APP_NAME,
            "app_env": _settings.APP_ENV,
            "debug": _settings.APP_DEBUG,
            "demo_mode": _settings.DEMO_MODE,
            "llm_model": _settings.LLM_MODEL,
            "llm_temperature": _settings.LLM_TEMPERATURE,
            "llm_max_tokens": _settings.LLM_MAX_TOKENS,
            "safety": {
                "risk_threshold_block": _settings.SAFETY.RISK_THRESHOLD_BLOCK,
                "risk_threshold_confirm": _settings.SAFETY.RISK_THRESHOLD_CONFIRM,
                "risk_threshold_warn": _settings.SAFETY.RISK_THRESHOLD_WARN,
                "injection_detection_enabled": _settings.SAFETY.ENABLE_INJECTION_DETECTION,
                "parameter_validation_enabled": _settings.SAFETY.ENABLE_PARAMETER_VALIDATION,
                "sandbox_enabled": _settings.SAFETY.ENABLE_SANDBOX,
                "command_timeout": _settings.SAFETY.COMMAND_TIMEOUT,
            },
        },
        "version": "1.0.0",
        "timestamp": "2026-06-07T00:00:00Z",
    }


class JSONRPCRequest(BaseModel):
    """MCP JSON-RPC 2.0 请求"""
    jsonrpc: str = "2.0"
    id: int | str
    method: str
    params: Optional[Dict[str, Any]] = None


class JSONRPCResponse(BaseModel):
    """MCP JSON-RPC 2.0 响应"""
    jsonrpc: str = "2.0"
    id: int | str
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


MCP_METHODS = {
    "tools/list": lambda params: MCPTools.list_available_tools(),
    "tools/call": lambda params: execute_tool(
        params.get("name", ""), params.get("arguments", {})
    ),
    "system/status": lambda params: OSSensor.get_full_snapshot(),
    "health": lambda params: {"status": "ok", "service": "AICloudOps"},
}


@router.post("/mcp/jsonrpc")
async def mcp_jsonrpc_endpoint(request: JSONRPCRequest):
    """MCP JSON-RPC 2.0 标准端点 — 兼容标准 MCP 协议客户端"""
    handler = MCP_METHODS.get(request.method)
    if not handler:
        return JSONRPCResponse(
            id=request.id,
            error={"code": -32601, "message": f"Method not found: {request.method}"},
        )
    try:
        result = handler(request.params or {})
        return JSONRPCResponse(id=request.id, result=result)
    except Exception as e:
        return JSONRPCResponse(
            id=request.id,
            error={"code": -32000, "message": str(e)},
        )


# ============================================================
# WebSocket 实时推送
# ============================================================

class ConnectionManager:
    """WebSocket 连接管理器 — 支持多客户端实时推送"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        dead = []
        for conn in self.active_connections:
            try:
                await conn.send_json(message)
            except Exception:
                dead.append(conn)
        for conn in dead:
            self.active_connections.remove(conn)


ws_manager = ConnectionManager()


@router.websocket("/ws/monitor")
async def websocket_monitor(websocket: WebSocket):
    """WebSocket 实时监控端点 — 推送系统状态和 Agent 事件"""
    # 安全加固: 校验 API Key 查询参数，防止未授权访问系统信息
    api_key = websocket.query_params.get("api_key", "")
    from backend.config import settings as _cfg
    if _cfg.LLM_API_KEY and api_key != _cfg.LLM_API_KEY:
        await websocket.close(code=4003, reason="Unauthorized")
        return
    await ws_manager.connect(websocket)
    try:
        while True:
            # 接收客户端消息（心跳或指令）
            data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
            if data == "ping":
                await websocket.send_json({"type": "pong"})
            elif data == "status":
                snapshot = OSSensor.get_full_snapshot()
                await websocket.send_json({"type": "system_status", "data": snapshot})
    except (WebSocketDisconnect, asyncio.TimeoutError):
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)

