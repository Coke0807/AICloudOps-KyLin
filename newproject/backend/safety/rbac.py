"""RBAC 权限模型 — 基于角色的最小权限控制"""

from enum import Enum
from typing import Dict, Set
from dataclasses import dataclass, field


class Role(Enum):
    VIEWER = "viewer"
    OPERATOR = "operator"
    ADMIN = "admin"


ROLE_HIERARCHY: Dict[Role, int] = {
    Role.VIEWER: 0,
    Role.OPERATOR: 1,
    Role.ADMIN: 2,
}


# 每个工具所需的最低角色
TOOL_ROLE_REQUIREMENTS: Dict[str, Role] = {
    # 只读工具 — viewer 即可
    "get_system_status": Role.VIEWER,
    "get_process_list": Role.VIEWER,
    "get_process_detail": Role.VIEWER,
    "get_open_files": Role.VIEWER,
    "get_network_connections": Role.VIEWER,
    "check_port_usage": Role.VIEWER,
    "get_disk_usage": Role.VIEWER,
    "get_large_files": Role.VIEWER,
    "get_memory_usage": Role.VIEWER,
    "get_memory_top_consumers": Role.VIEWER,
    "get_system_uptime": Role.VIEWER,
    "list_available_tools": Role.VIEWER,
    "query_journal": Role.VIEWER,
    "search_log_file": Role.VIEWER,
    "get_service_status": Role.VIEWER,
    "list_failed_services": Role.VIEWER,
    "check_failed_logins": Role.VIEWER,
    # 操作类工具 — 需要 operator
    "run_safe_command": Role.OPERATOR,
    "backup_config": Role.OPERATOR,
    # 高危工具 — 需要 admin
    "kill_process": Role.ADMIN,
    "rollback_operation": Role.ADMIN,
}


@dataclass
class UserContext:
    """当前请求的用户上下文

    默认角色为 OPERATOR，支持执行大部分运维工具。
    高危操作（kill_process/rollback_operation）需要 ADMIN 权限。
    """
    user_id: str = "default_operator"
    role: Role = Role.OPERATOR
    ip_address: str = "127.0.0.1"


def check_permission(user: UserContext, tool_name: str) -> bool:
    """检查用户是否有权限调用指定工具"""
    required = TOOL_ROLE_REQUIREMENTS.get(tool_name, Role.ADMIN)
    return ROLE_HIERARCHY[user.role] >= ROLE_HIERARCHY[required]


def get_missing_permission_message(user: UserContext, tool_name: str) -> str:
    required = TOOL_ROLE_REQUIREMENTS.get(tool_name, Role.ADMIN)
    return (
        f"权限不足：工具 '{tool_name}' 需要 '{required.value}' 角色，"
        f"当前用户 '{user.user_id}' 为 '{user.role.value}' 角色"
    )
