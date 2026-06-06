import json
import asyncio
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
from backend.safety.rbac import UserContext, Role, TOOL_ROLE_REQUIREMENTS

router = APIRouter()


class AgentRequest(BaseModel):
    prompt: str
    session_id: Optional[str] = None


class ToolExecuteRequest(BaseModel):
    tool_name: str
    params: Optional[Dict[str, Any]] = None


@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "AICloudOps"}


@router.get("/system/status")
async def get_system_status():
    return {"data": OSSensor.get_full_snapshot()}


@router.get("/system/processes")
async def get_processes(limit: int = 20):
    return {"data": OSSensor.get_process_list(limit)}


@router.get("/system/disks")
async def get_disks():
    return {"data": OSSensor.get_disk_info()}


@router.get("/tools")
async def list_tools():
    return MCPTools.list_available_tools()


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
    # RBAC: rollback 是高危操作，需要 admin 权限
    user_ctx = UserContext(role=Role.ADMIN)
    if not check_permission(user_ctx, "rollback_operation"):
        raise HTTPException(status_code=403, detail="仅管理员可执行回滚操作")
    result = config_backup.rollback(operation_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "回滚失败"))
    return result


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

