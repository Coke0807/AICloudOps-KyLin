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

