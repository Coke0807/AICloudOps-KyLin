import json
import asyncio
from typing import Dict, Any, Optional, AsyncGenerator, List
from backend.core.os_sensor import OSSensor
from backend.core.llm_client import llm_client
from backend.core.planner import task_planner
from backend.core.demo_engine import demo_engine
from backend.safety.validator import SafetyGuardrail
from backend.safety.audit_agent import audit_agent
from backend.safety.rbac import UserContext, Role, check_permission, get_missing_permission_message
from backend.safety.sandbox import sandbox_executor
from backend.database import db
from backend.mcp.tools import execute_tool, MCPTools
from backend.utils.audit_logger import AuditLogger
from backend.config import settings


class AIOpsAgent:
    SYSTEM_PROMPT = """你是一个安全感知的智能运维Agent，运行在麒麟操作系统(Kylin OS)上。你的核心使命是帮助运维人员安全、高效地完成系统运维任务。

## 身份与职责
- **安全运维专家**：你始终将系统安全放在首位
- **麒麟OS专家**：你熟悉国产麒麟操作系统的特性和运维实践
- **智能分析助手**：你能进行多步推理，逐步分析问题并给出解决方案

## 可用工具列表（共20个）

### 系统监控类
1. **get_system_status** - 获取完整的系统状态快照（CPU、内存、磁盘、进程、网络）
2. **get_process_list** - 获取运行中的进程列表，支持排序
3. **get_process_detail** - 根据PID获取单个进程的详细信息
4. **get_memory_usage** - 获取详细的内存使用信息（物理内存、swap、/proc/meminfo）
5. **get_memory_top_consumers** - 获取内存占用最高的进程列表
6. **get_system_uptime** - 获取系统运行时间和负载均衡信息

### 磁盘与文件类
7. **get_disk_usage** - 获取所有挂载点的磁盘使用情况
8. **get_large_files** - 查找指定路径下超过给定大小的文件
9. **get_open_files** - 获取指定进程打开的文件列表

### 网络与端口类
10. **get_network_connections** - 获取当前活跃的网络连接列表
11. **check_port_usage** - 检查指定端口的使用情况和监听进程

### 日志分析类
12. **query_journal** - 查询systemd journal日志
13. **search_log_file** - 在/var/log下的日志文件中搜索匹配模式的行

### 服务管理类
14. **get_service_status** - 查看systemd服务的运行状态
15. **list_failed_services** - 列出所有失败的systemd服务

### 安全审计类
16. **check_failed_logins** - 检查最近1小时内的SSH失败登录尝试

### 进程操作类（高危）
17. **kill_process** - 向指定进程发送信号（默认SIGTERM），需要确认

### 通用命令类
18. **run_safe_command** - 执行白名单内的安全系统命令

### 配置管理类
19. **backup_config** - 备份指定配置文件（高危操作前自动调用，支持一键回滚）
20. **rollback_operation** - 回滚指定操作的备份文件（一键恢复修改前状态）

## 安全规则（必须严格遵守）

### 绝对禁止
- **绝不执行危险命令**：如 rm -rf /、mkfs、chmod 777、dd if=/dev/zero 等
- **绝不修改关键系统配置**：/etc、/boot、/sys、/proc 等目录
- **绝不执行未经授权的特权操作**：sudo、su、chown root 等
- **绝不执行网络攻击工具**：nmap、tcpdump（对非本地接口）、iptables 等

### 必须遵守
- **最小权限原则**：只执行完成任务所必需的操作
- **二次确认原则**：高风险操作（如kill_process）前必须提醒用户确认
- **路径白名单**：文件操作仅限于 /tmp、/var/log、/home、/opt 等安全路径
- **命令白名单**：run_safe_command 仅允许：ls, ps, df, du, free, uptime, whoami, hostname, uname, date, echo, cat, ss, netstat, ip, iostat, vmstat

## 思维模式（多步推理）

面对用户问题时，请按以下步骤思考：

### 第一步：理解问题
- 仔细分析用户的真实意图
- 识别问题的类型：监控查询、故障排查、性能优化、安全审计
- 判断问题的紧急程度和潜在风险

### 第二步：信息收集
- 使用工具获取必要的系统信息
- 优先使用无副作用的只读工具（get_*、check_*、query_*、list_*）
- 只在必要时才使用有副作用的工具（kill_process、run_safe_command）

### 第三步：分析诊断
- 综合多个工具的结果进行分析
- 识别异常指标和潜在问题
- 关联不同维度的信息（CPU、内存、进程、日志）

### 第四步：给出建议
- 清晰地解释问题的根本原因
- 提供具体的、可操作的解决方案
- 对于高风险操作，明确说明风险并请求确认

## 响应格式
- 使用清晰的中文回答
- 先解释你的分析思路，再给出结论
- 提供具体的数据支撑你的判断
- 对于复杂问题，分步骤说明
- 如果检测到异常，提供解决方案和预防建议
- 始终保持专业、严谨的态度"""

    def __init__(self):
        self._guardrail = SafetyGuardrail()
        self._audit = AuditLogger()

    def _build_tools_schema(self) -> list[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_system_status",
                    "description": "获取完整的系统状态快照，包括CPU、内存、磁盘、进程和网络信息",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_process_list",
                    "description": "获取运行中的进程列表，支持按CPU、内存、PID、名称排序",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "limit": {"type": "integer", "description": "返回的进程数量限制，默认20"},
                            "sort_by": {"type": "string", "enum": ["cpu_percent", "memory_rss", "pid", "name"], "description": "排序字段，默认cpu_percent"},
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_process_detail",
                    "description": "根据PID获取单个进程的详细信息，包括状态、命令行、内存等",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "pid": {"type": "integer", "description": "进程ID"},
                        },
                        "required": ["pid"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_open_files",
                    "description": "获取指定进程打开的文件列表（使用lsof）",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "pid": {"type": "integer", "description": "进程ID"},
                        },
                        "required": ["pid"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "kill_process",
                    "description": "向指定进程发送信号（默认SIGTERM），高危操作需确认",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "pid": {"type": "integer", "description": "进程ID"},
                            "signal": {"type": "integer", "description": "信号编号，默认15(SIGTERM)"},
                            "force_confirm": {"type": "boolean", "description": "必须为True才执行"},
                        },
                        "required": ["pid"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_network_connections",
                    "description": "获取当前活跃的网络连接列表",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "check_port_usage",
                    "description": "检查指定端口的使用情况和监听进程",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "port": {"type": "integer", "description": "端口号"},
                        },
                        "required": ["port"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_disk_usage",
                    "description": "获取所有挂载点的磁盘使用情况",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_large_files",
                    "description": "查找指定路径下超过给定大小的文件",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "size_mb": {"type": "integer", "description": "大小阈值(MB)，默认100"},
                            "search_path": {"type": "string", "description": "搜索路径，默认/"},
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_memory_usage",
                    "description": "获取详细的内存使用信息，包括物理内存、swap和/proc/meminfo",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_memory_top_consumers",
                    "description": "获取内存占用最高的进程列表",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "limit": {"type": "integer", "description": "返回数量限制，默认10"},
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "query_journal",
                    "description": "查询systemd journal日志",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "since": {"type": "string", "description": "起始时间，默认'1 hour ago'"},
                            "lines": {"type": "integer", "description": "返回行数，默认50"},
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_log_file",
                    "description": "在/var/log下的日志文件中搜索匹配模式的行",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filepath": {"type": "string", "description": "日志文件路径（必须在/var/log下）"},
                            "pattern": {"type": "string", "description": "搜索模式"},
                        },
                        "required": ["filepath", "pattern"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_service_status",
                    "description": "查看systemd服务的运行状态",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "service_name": {"type": "string", "description": "服务名称"},
                        },
                        "required": ["service_name"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_failed_services",
                    "description": "列出所有失败的systemd服务",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "check_failed_logins",
                    "description": "检查最近1小时内的SSH失败登录尝试",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_system_uptime",
                    "description": "获取系统运行时间和负载均衡信息",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "run_safe_command",
                    "description": "执行白名单内的安全系统命令（ls, ps, df, du, free, uptime, whoami, hostname, uname, date, echo, cat, ss, netstat, ip, iostat, vmstat）",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "要执行的命令字符串"},
                        },
                        "required": ["command"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "backup_config",
                    "description": "备份指定配置文件（高危操作前自动调用，支持一键回滚）",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string", "description": "要备份的文件路径"},
                            "operation_id": {"type": "string", "description": "操作标识，默认'manual'"},
                        },
                        "required": ["file_path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "rollback_operation",
                    "description": "回滚指定操作的备份文件（一键恢复修改前状态，需admin权限）",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "operation_id": {"type": "string", "description": "要回滚的操作标识"},
                        },
                        "required": ["operation_id"],
                    },
                },
            },
        ]

    def _execute_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        try:
            if isinstance(arguments, str):
                arguments = json.loads(arguments)
            result = execute_tool(tool_name, arguments)
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    async def _execute_tool_async(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """在线程池中执行工具调用，避免阻塞事件循环"""
        return await asyncio.to_thread(self._execute_tool_call, tool_name, arguments)

    @staticmethod
    def _build_sandbox_command(tool_name: str, arguments: Dict[str, Any]) -> Optional[str]:
        """将高危工具调用转换为可在沙箱中执行的命令字符串

        仅对 run_safe_command（用户自定义命令）和 kill_process（信号发送）构建。
        rollback_operation 等纯 Python 操作不走沙箱。
        """
        if tool_name == "run_safe_command":
            return arguments.get("command", "")
        if tool_name == "kill_process":
            pid = arguments.get("pid", "")
            signal = arguments.get("signal", 15)
            if pid:
                return f"kill -{signal} {pid}"
        return None

    async def _process_single_tool(
        self, tool_call: Dict, tool_name: str, arguments_dict: Dict,
        user_prompt: str, trace_id: str, user_context: UserContext,
    ) -> Dict[str, Any]:
        """处理单个工具调用的完整流程：RBAC → 安全校验 → 审计代理 → 执行

        返回 {"tool_call_id": ..., "content": ..., "tool_result": ...|None}
        """
        tool_call_id = tool_call["id"]

        # 1) RBAC 权限检查
        if not check_permission(user_context, tool_name):
            perm_error = get_missing_permission_message(user_context, tool_name)
            self._audit.log_tool_execution(trace_id, tool_name, arguments_dict, {"blocked": True, "reason": "rbac_denied"})
            return {"tool_call_id": tool_call_id, "content": json.dumps({"error": perm_error, "blocked": True}, ensure_ascii=False), "tool_result": None}

        # 2) 五层安全护栏（仅高危命令）
        command_to_check = None
        if tool_name == "run_safe_command":
            command_to_check = arguments_dict.get("command", "")
        elif tool_name == "kill_process":
            command_to_check = f"kill -{arguments_dict.get('signal', 15)} {arguments_dict.get('pid', '')}"

        if command_to_check:
            safety_result = self._guardrail.validate(user_prompt, command_to_check)
            self._audit.log_safety_validation(trace_id, {"tool": tool_name, "command": command_to_check, "result": safety_result})
            if not safety_result["is_safe"]:
                blocked_reason = []
                for layer_name, layer_data in safety_result["layers"].items():
                    if not layer_data.get("passed", True):
                        if layer_name == "risk_scorer":
                            blocked_reason.extend(layer_data.get("reasons", []))
                        elif layer_name == "param_validator":
                            blocked_reason.extend(layer_data.get("violations", []))
                error_msg = f"安全拦截：工具 {tool_name} 的执行被阻止。原因：{'; '.join(blocked_reason) if blocked_reason else '安全检查未通过'}"
                self._audit.log_tool_execution(trace_id, tool_name, arguments_dict, {"blocked": True, "reason": blocked_reason})
                return {"tool_call_id": tool_call_id, "content": json.dumps({"error": error_msg, "blocked": True}, ensure_ascii=False), "tool_result": None}

        # 3) 审计代理：动态意图对齐（仅高危工具）
        if settings.SAFETY.ENABLE_AUDIT_AGENT and tool_name in audit_agent.HIGH_RISK_TOOLS:
            audit_result = await audit_agent.validate_intent_alignment(user_prompt, tool_name, arguments_dict)
            self._audit.log_safety_validation(trace_id, {"layer": "audit_agent", "tool": tool_name, "result": audit_result})
            if audit_result.get("decision") == "blocked":
                error_msg = f"审计代理拦截：{audit_result.get('reason', '意图偏移')}"
                return {"tool_call_id": tool_call_id, "content": json.dumps({"error": error_msg, "blocked": True}, ensure_ascii=False), "tool_result": None}

        # 4) 沙箱隔离执行（高危工具走沙箱，其他走标准执行）
        if tool_name in audit_agent.HIGH_RISK_TOOLS and settings.SAFETY.ENABLE_SANDBOX:
            # 构建可执行命令字符串，通过沙箱隔离运行
            sandbox_cmd = self._build_sandbox_command(tool_name, arguments_dict)
            if sandbox_cmd:
                sandbox_result = await asyncio.to_thread(
                    sandbox_executor.execute_in_sandbox, sandbox_cmd, settings.SAFETY.COMMAND_TIMEOUT,
                )
                # 将沙箱结果包装为标准工具返回格式
                if sandbox_result.get("returncode") == 0 and not sandbox_result.get("timed_out"):
                    parsed = {
                        "sandbox": sandbox_result.get("sandbox", "unknown"),
                        "stdout": sandbox_result.get("stdout", ""),
                        "tool": tool_name,
                        "status": "executed_in_sandbox",
                    }
                    tool_result = json.dumps(parsed, ensure_ascii=False)
                    self._audit.log_tool_execution(trace_id, tool_name, arguments_dict, parsed)
                    db.add_tool_execution(tool_name, arguments_dict, parsed, "sandbox_success")
                    return {"tool_call_id": tool_call_id, "content": tool_result, "tool_result": tool_result}
                else:
                    error_msg = f"沙箱执行失败: {sandbox_result.get('stderr', '未知错误')}"
                    parsed = {"error": error_msg, "sandbox": sandbox_result.get("sandbox", "unknown"), "blocked": False}
                    self._audit.log_tool_execution(trace_id, tool_name, arguments_dict, parsed)
                    return {"tool_call_id": tool_call_id, "content": json.dumps(parsed, ensure_ascii=False), "tool_result": None}

        # 降级：标准执行（在线程池中运行，避免阻塞）
        tool_result = await self._execute_tool_async(tool_name, arguments_dict)
        parsed = json.loads(tool_result)
        self._audit.log_tool_execution(trace_id, tool_name, arguments_dict, parsed)
        db.add_tool_execution(tool_name, arguments_dict, parsed, "success")
        return {"tool_call_id": tool_call_id, "content": tool_result, "tool_result": tool_result}

    async def process_request(
        self,
        user_prompt: str,
        session_id: Optional[str] = None,
        max_tool_rounds: int = 5,
        user_context: UserContext = None,
    ) -> Dict[str, Any]:
        if not session_id:
            session_id = db.create_session(user_prompt[:50])

        # RBAC 用户上下文（默认 operator 角色）
        if user_context is None:
            user_context = UserContext()

        db.add_message(session_id, "user", user_prompt)

        trace_id = self._audit.start_trace(user_prompt)

        system_snapshot = OSSensor.get_full_snapshot()
        self._audit.log_environment_sensing(trace_id, system_snapshot)

        # ── Demo Mode：在安全校验之前介入，绕过输入级拦截 ──
        if settings.DEMO_MODE:
            scenario = demo_engine.match_scenario(user_prompt)
            if scenario:
                result = await demo_engine.generate_response(scenario, trace_id, session_id)
                db.add_message(session_id, "assistant", result["response"], safety_report=result.get("safety_report"))
                return result

        intent_analysis = self._guardrail.validate(user_prompt)
        self._audit.log_intent_analysis(trace_id, intent_analysis)
        self._audit.log_safety_validation(trace_id, intent_analysis)

        if not intent_analysis["is_safe"]:
            reasons = []
            for layer_name, layer_data in intent_analysis["layers"].items():
                if not layer_data.get("passed", True):
                    if layer_name == "intent":
                        reasons.append(f"检测到危险意图: {layer_data.get('intent', 'unknown')}")
                    elif layer_name == "injection":
                        reasons.append(f"检测到注入攻击: {layer_data.get('patterns_found', [])}")
                    elif layer_name == "risk_scorer":
                        reasons.append(f"高风险命令: {layer_data.get('reasons', [])}")
                    elif layer_name == "param_validator":
                        reasons.append(f"参数违规: {layer_data.get('violations', [])}")

            response = f"安全警告：您的请求被安全系统拦截。\n\n原因：{'; '.join(reasons) if reasons else '安全检查未通过'}\n\n建议：请重新组织您的请求，确保不包含危险指令或注入攻击。"

            self._audit.log_final_decision(trace_id, {"blocked": True, "reason": reasons})
            self._audit.end_trace(trace_id, {"blocked": True, "response": response})

            db.add_message(session_id, "assistant", response, safety_report=intent_analysis)
            return {
                "session_id": session_id,
                "response": response,
                "safety_report": intent_analysis,
                "blocked": True,
                "trace_id": trace_id,
            }

        context_message = f"""当前系统状态概览：
- CPU使用率: {system_snapshot['cpu']['overall']}%
- 内存使用率: {system_snapshot['memory']['percent']}%
- 磁盘数量: {len(system_snapshot['disks'])}
- 进程数量: {len(system_snapshot['processes'])}

用户问题: {user_prompt}"""

        history_msgs = db.get_session_messages(session_id)
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
        ]
        if len(history_msgs) > 1:
            for msg in history_msgs[:-1]:
                if msg["role"] in ["user", "assistant"]:
                    messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": context_message})

        try:
            tools = self._build_tools_schema()
            final_content = ""

            for round_num in range(max_tool_rounds):
                response = await llm_client.chat(messages, tools=tools)

                assistant_message = response["choices"][0]["message"]
                messages.append(assistant_message)

                if not assistant_message.get("tool_calls"):
                    final_content = assistant_message.get("content", "")
                    break

                # 解析所有工具调用
                tool_calls_parsed = []
                for tc in assistant_message["tool_calls"]:
                    fn = tc["function"]
                    args_raw = fn.get("arguments", "{}")
                    args_dict = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
                    tool_calls_parsed.append((tc, fn["name"], args_dict))

                # 并行执行所有工具调用（安全检查包含在 _process_single_tool 内）
                tasks = [
                    self._process_single_tool(tc, name, args, user_prompt, trace_id, user_context)
                    for tc, name, args in tool_calls_parsed
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for result in results:
                    if isinstance(result, Exception):
                        messages.append({"role": "tool", "tool_call_id": "error", "content": json.dumps({"error": str(result)}, ensure_ascii=False)})
                    else:
                        messages.append({"role": "tool", "tool_call_id": result["tool_call_id"], "content": result["content"]})

            if not final_content:
                final_response = await llm_client.chat(messages)
                final_content = final_response["choices"][0]["message"]["content"]

            self._audit.log_final_decision(trace_id, {"response": final_content})
            self._audit.end_trace(trace_id, {"response": final_content})

            db.add_message(session_id, "assistant", final_content, safety_report=intent_analysis)

            return {
                "session_id": session_id,
                "response": final_content,
                "safety_report": intent_analysis,
                "blocked": False,
                "trace_id": trace_id,
            }

        except Exception as e:
            error_response = f"处理请求时发生错误: {str(e)}"

            self._audit.log_final_decision(trace_id, {"error": str(e)})
            self._audit.end_trace(trace_id, {"error": str(e)})

            db.add_message(session_id, "assistant", error_response)
            return {
                "session_id": session_id,
                "response": error_response,
                "error": str(e),
                "trace_id": trace_id,
            }

    async def stream_request(
        self,
        user_prompt: str,
        session_id: Optional[str] = None,
        max_tool_rounds: int = 5,
        user_context: UserContext = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        if not session_id:
            session_id = db.create_session(user_prompt[:50])

        if user_context is None:
            user_context = UserContext()

        db.add_message(session_id, "user", user_prompt)

        trace_id = self._audit.start_trace(user_prompt)

        system_snapshot = OSSensor.get_full_snapshot()
        self._audit.log_environment_sensing(trace_id, system_snapshot)

        # ── Demo Mode：在安全校验之前介入，绕过输入级拦截 ──
        if settings.DEMO_MODE:
            scenario = demo_engine.match_scenario(user_prompt)
            if scenario:
                async for chunk in demo_engine.generate_stream(scenario, trace_id, session_id):
                    yield chunk
                return

        intent_analysis = self._guardrail.validate(user_prompt)
        self._audit.log_intent_analysis(trace_id, intent_analysis)
        self._audit.log_safety_validation(trace_id, intent_analysis)

        if not intent_analysis["is_safe"]:
            reasons = []
            for layer_name, layer_data in intent_analysis["layers"].items():
                if not layer_data.get("passed", True):
                    if layer_name == "intent":
                        reasons.append(f"检测到危险意图: {layer_data.get('intent', 'unknown')}")
                    elif layer_name == "injection":
                        reasons.append(f"检测到注入攻击: {layer_data.get('patterns_found', [])}")
                    elif layer_name == "risk_scorer":
                        reasons.append(f"高风险命令: {layer_data.get('reasons', [])}")
                    elif layer_name == "param_validator":
                        reasons.append(f"参数违规: {layer_data.get('violations', [])}")

            response = f"安全警告：您的请求被安全系统拦截。\n\n原因：{'; '.join(reasons) if reasons else '安全检查未通过'}\n\n建议：请重新组织您的请求，确保不包含危险指令或注入攻击。"

            self._audit.log_final_decision(trace_id, {"blocked": True, "reason": reasons})
            self._audit.end_trace(trace_id, {"blocked": True, "response": response})

            db.add_message(session_id, "assistant", response, safety_report=intent_analysis)
            yield {"content": response, "done": True, "session_id": session_id, "safety_report": intent_analysis, "trace_id": trace_id}
            return

        context_message = f"""当前系统状态概览：
- CPU使用率: {system_snapshot['cpu']['overall']}%
- 内存使用率: {system_snapshot['memory']['percent']}%
- 磁盘数量: {len(system_snapshot['disks'])}
- 进程数量: {len(system_snapshot['processes'])}

用户问题: {user_prompt}"""

        history_msgs = db.get_session_messages(session_id)
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
        ]
        if len(history_msgs) > 1:
            for msg in history_msgs[:-1]:
                if msg["role"] in ["user", "assistant"]:
                    messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": context_message})

        try:
            tools = self._build_tools_schema()
            final_content = ""

            for round_num in range(max_tool_rounds):
                response = await llm_client.chat(messages, tools=tools, stream=True)

                tool_calls_buffer = []
                content_buffer = ""

                async for chunk in response:
                    if isinstance(chunk, str):
                        content_buffer += chunk
                        yield {"content": chunk, "done": False, "session_id": session_id, "trace_id": trace_id}
                    elif isinstance(chunk, dict):
                        if chunk.get("type") == "reasoning":
                            yield {"reasoning": chunk["content"], "done": False, "session_id": session_id, "trace_id": trace_id}
                        elif chunk.get("tool_calls"):
                            for tc in chunk["tool_calls"]:
                                while len(tool_calls_buffer) <= tc.get("index", 0):
                                    tool_calls_buffer.append({"id": "", "function": {"name": "", "arguments": ""}})
                                idx = tc.get("index", 0)
                                if tc.get("id"):
                                    tool_calls_buffer[idx]["id"] = tc["id"]
                                if tc.get("function", {}).get("name"):
                                    tool_calls_buffer[idx]["function"]["name"] = tc["function"]["name"]
                                if tc.get("function", {}).get("arguments"):
                                    tool_calls_buffer[idx]["function"]["arguments"] += tc["function"]["arguments"]

                if not tool_calls_buffer:
                    final_content = content_buffer
                    break

                # 通知前端即将执行工具调用
                tool_names = [tc["function"]["name"] for tc in tool_calls_buffer]
                yield {
                    "status": "tool_calls",
                    "tools": tool_names,
                    "done": False,
                    "session_id": session_id,
                    "trace_id": trace_id,
                }

                assistant_message = {"role": "assistant", "content": content_buffer or None, "tool_calls": tool_calls_buffer}
                messages.append(assistant_message)

                tool_calls_parsed = []
                for tc in tool_calls_buffer:
                    fn = tc["function"]
                    args_raw = fn.get("arguments", "{}")
                    args_dict = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
                    tool_calls_parsed.append((tc, fn["name"], args_dict))

                tasks = [
                    self._process_single_tool(tc, name, args, user_prompt, trace_id, user_context)
                    for tc, name, args in tool_calls_parsed
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # 收集工具执行结果并推送给前端（实时显示工具详情）
                tool_details_batch = []
                for result in results:
                    if isinstance(result, Exception):
                        messages.append({"role": "tool", "tool_call_id": "error", "content": json.dumps({"error": str(result)}, ensure_ascii=False)})
                    else:
                        messages.append({"role": "tool", "tool_call_id": result["tool_call_id"], "content": result["content"]})
                        if result.get("tool_result"):
                            try:
                                parsed_result = json.loads(result["tool_result"])
                                tool_details_batch.append({
                                    "name": next((n for tc, n, _ in tool_calls_parsed if tc["id"] == result["tool_call_id"]), "unknown"),
                                    "args": next((a for tc, _, a in tool_calls_parsed if tc["id"] == result["tool_call_id"]), {}),
                                    "result": parsed_result,
                                })
                            except (json.JSONDecodeError, StopIteration):
                                pass

                if tool_details_batch:
                    yield {
                        "tool_details": tool_details_batch,
                        "done": False,
                        "session_id": session_id,
                        "trace_id": trace_id,
                    }

            if not final_content:
                final_response = await llm_client.chat(messages, stream=True)
                async for chunk in final_response:
                    if isinstance(chunk, str):
                        final_content += chunk
                        yield {"content": chunk, "done": False, "session_id": session_id, "trace_id": trace_id}
                    elif isinstance(chunk, dict):
                        if chunk.get("type") == "reasoning":
                            yield {"reasoning": chunk["content"], "done": False, "session_id": session_id, "trace_id": trace_id}

            self._audit.log_final_decision(trace_id, {"response": final_content})
            self._audit.end_trace(trace_id, {"response": final_content})

            db.add_message(session_id, "assistant", final_content, safety_report=intent_analysis)
            yield {"content": "", "done": True, "session_id": session_id, "safety_report": intent_analysis, "trace_id": trace_id}

        except Exception as e:
            error_msg = f"错误: {str(e)}"

            self._audit.log_final_decision(trace_id, {"error": str(e)})
            self._audit.end_trace(trace_id, {"error": str(e)})

            db.add_message(session_id, "assistant", error_msg)
            yield {"content": error_msg, "done": True, "session_id": session_id, "error": str(e), "trace_id": trace_id}


agent = AIOpsAgent()