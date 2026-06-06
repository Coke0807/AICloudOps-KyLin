import os
import shlex
import psutil
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, List

from backend.core.os_sensor import OSSensor
from backend.safety.sandbox import config_backup
from backend.config import settings


class MCPTools:
    @staticmethod
    def get_system_status() -> Dict[str, Any]:
        return {
            "tool": "get_system_status",
            "status": "success",
            "data": OSSensor.get_full_snapshot(),
            "risk_level": "safe",
        }

    @staticmethod
    def get_process_list(limit: int = 20, sort_by: str = "cpu_percent") -> Dict[str, Any]:
        valid_sort_keys = {"cpu_percent", "memory_rss", "pid", "name"}
        if sort_by not in valid_sort_keys:
            return {
                "tool": "get_process_list",
                "status": "error",
                "error": f"Invalid sort_by: {sort_by}. Valid: {sorted(valid_sort_keys)}",
                "risk_level": "safe",
            }
        processes = []
        for proc in psutil.process_iter(["pid", "name", "username", "cpu_percent", "memory_info"]):
            try:
                processes.append({
                    "pid": proc.info["pid"],
                    "name": proc.info["name"],
                    "username": proc.info["username"],
                    "cpu_percent": proc.info["cpu_percent"],
                    "memory_rss": proc.info["memory_info"].rss if proc.info["memory_info"] else 0,
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        reverse = sort_by != "name"
        processes.sort(key=lambda x: x.get(sort_by, 0), reverse=reverse)
        return {
            "tool": "get_process_list",
            "status": "success",
            "data": processes[:limit],
            "risk_level": "safe",
        }

    @staticmethod
    def get_process_detail(pid: int) -> Dict[str, Any]:
        proc_path = Path(f"/proc/{pid}")
        if not proc_path.exists():
            return {
                "tool": "get_process_detail",
                "status": "error",
                "error": f"Process {pid} not found",
                "risk_level": "safe",
            }
        data: Dict[str, Any] = {"pid": pid}
        try:
            status_file = proc_path / "status"
            if status_file.exists():
                for line in status_file.read_text().splitlines():
                    if ":" in line:
                        key, val = line.split(":", 1)
                        data[key.strip().lower()] = val.strip()
        except (PermissionError, FileNotFoundError):
            pass
        try:
            cmdline_file = proc_path / "cmdline"
            if cmdline_file.exists():
                data["cmdline"] = cmdline_file.read_bytes().replace(b"\x00", b" ").decode().strip()
        except (PermissionError, FileNotFoundError):
            pass
        try:
            proc = psutil.Process(pid)
            data["status"] = proc.status()
            data["create_time"] = proc.create_time()
            data["cpu_percent"] = proc.cpu_percent()
            mem = proc.memory_info()
            data["memory_rss"] = mem.rss
            data["memory_vms"] = mem.vms
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
        return {
            "tool": "get_process_detail",
            "status": "success",
            "data": data,
            "risk_level": "safe",
        }

    @staticmethod
    def get_open_files(pid: int) -> Dict[str, Any]:
        try:
            result = subprocess.run(
                ["lsof", "-p", str(pid)],
                capture_output=True, text=True, timeout=10,
            )
            lines = [l for l in result.stdout.strip().splitlines() if l]
            return {
                "tool": "get_open_files",
                "status": "success",
                "data": {"pid": pid, "count": max(0, len(lines) - 1), "output": lines},
                "risk_level": "safe",
            }
        except FileNotFoundError:
            return {
                "tool": "get_open_files",
                "status": "error",
                "error": "lsof command not available",
                "risk_level": "safe",
            }
        except subprocess.TimeoutExpired:
            return {
                "tool": "get_open_files",
                "status": "error",
                "error": "Command timed out",
                "risk_level": "safe",
            }
        except Exception as e:
            return {
                "tool": "get_open_files",
                "status": "error",
                "error": str(e),
                "risk_level": "safe",
            }

    @staticmethod
    def kill_process(pid: int, signal: int = 15, force_confirm: bool = False) -> Dict[str, Any]:
        if not force_confirm:
            return {
                "tool": "kill_process",
                "status": "error",
                "error": "This is a dangerous operation. Set force_confirm=True to proceed.",
                "risk_level": "high",
                "requires_confirmation": True,
            }
        try:
            proc = psutil.Process(pid)
            proc_name = proc.name()
            os.kill(pid, signal)
            return {
                "tool": "kill_process",
                "status": "success",
                "data": {"pid": pid, "name": proc_name, "signal": signal},
                "risk_level": "high",
                "requires_confirmation": True,
            }
        except ProcessLookupError:
            return {
                "tool": "kill_process",
                "status": "error",
                "error": f"Process {pid} not found",
                "risk_level": "high",
                "requires_confirmation": True,
            }
        except PermissionError:
            return {
                "tool": "kill_process",
                "status": "error",
                "error": f"Permission denied to kill process {pid}",
                "risk_level": "high",
                "requires_confirmation": True,
            }
        except Exception as e:
            return {
                "tool": "kill_process",
                "status": "error",
                "error": str(e),
                "risk_level": "high",
                "requires_confirmation": True,
            }

    @staticmethod
    def get_network_connections() -> Dict[str, Any]:
        return {
            "tool": "get_network_connections",
            "status": "success",
            "data": OSSensor.get_network_connections(),
            "risk_level": "safe",
        }

    @staticmethod
    def check_port_usage(port: int) -> Dict[str, Any]:
        try:
            result = subprocess.run(
                ["ss", "-tlnp"],
                capture_output=True, text=True, timeout=10,
            )
            matches = [
                line for line in result.stdout.splitlines()
                if f":{port} " in line or f":{port}\t" in line or line.endswith(f":{port}")
            ]
            return {
                "tool": "check_port_usage",
                "status": "success",
                "data": {"port": port, "in_use": len(matches) > 0, "listeners": matches},
                "risk_level": "safe",
            }
        except FileNotFoundError:
            return {
                "tool": "check_port_usage",
                "status": "error",
                "error": "ss command not available",
                "risk_level": "safe",
            }
        except subprocess.TimeoutExpired:
            return {
                "tool": "check_port_usage",
                "status": "error",
                "error": "Command timed out",
                "risk_level": "safe",
            }
        except Exception as e:
            return {
                "tool": "check_port_usage",
                "status": "error",
                "error": str(e),
                "risk_level": "safe",
            }

    @staticmethod
    def get_disk_usage() -> Dict[str, Any]:
        return {
            "tool": "get_disk_usage",
            "status": "success",
            "data": OSSensor.get_disk_info(),
            "risk_level": "safe",
        }

    @staticmethod
    def get_large_files(size_mb: int = 100, search_path: str = "/") -> Dict[str, Any]:
        if not Path(search_path).exists():
            return {
                "tool": "get_large_files",
                "status": "error",
                "error": f"Path does not exist: {search_path}",
                "risk_level": "low",
            }
        try:
            result = subprocess.run(
                ["find", search_path, "-maxdepth", "3", "-size", f"+{size_mb}M", "-type", "f"],
                capture_output=True, text=True, timeout=15,
            )
            files = [f for f in result.stdout.strip().splitlines() if f]
            return {
                "tool": "get_large_files",
                "status": "success",
                "data": {"size_threshold_mb": size_mb, "search_path": search_path, "files": files, "count": len(files)},
                "risk_level": "low",
            }
        except FileNotFoundError:
            return {
                "tool": "get_large_files",
                "status": "error",
                "error": "find command not available",
                "risk_level": "low",
            }
        except subprocess.TimeoutExpired:
            return {
                "tool": "get_large_files",
                "status": "error",
                "error": "Search timed out (15s limit)",
                "risk_level": "low",
            }
        except Exception as e:
            return {
                "tool": "get_large_files",
                "status": "error",
                "error": str(e),
                "risk_level": "low",
            }

    @staticmethod
    def get_memory_usage() -> Dict[str, Any]:
        mem = psutil.virtual_memory()
        data: Dict[str, Any] = {
            "total": mem.total,
            "available": mem.available,
            "used": mem.used,
            "percent": mem.percent,
            "buffers": getattr(mem, "buffers", None),
            "cached": getattr(mem, "cached", None),
            "shared": getattr(mem, "shared", None),
        }
        meminfo_path = Path("/proc/meminfo")
        if meminfo_path.exists():
            try:
                meminfo = {}
                for line in meminfo_path.read_text().splitlines():
                    if ":" in line:
                        key, val = line.split(":", 1)
                        meminfo[key.strip()] = val.strip()
                data["meminfo_raw"] = meminfo
            except (PermissionError, FileNotFoundError):
                pass
        swap = psutil.swap_memory()
        data["swap"] = {
            "total": swap.total,
            "used": swap.used,
            "free": swap.free,
            "percent": swap.percent,
        }
        return {
            "tool": "get_memory_usage",
            "status": "success",
            "data": data,
            "risk_level": "safe",
        }

    @staticmethod
    def get_memory_top_consumers(limit: int = 10) -> Dict[str, Any]:
        processes = []
        for proc in psutil.process_iter(["pid", "name", "username", "memory_info", "memory_percent"]):
            try:
                mem_info = proc.info["memory_info"]
                processes.append({
                    "pid": proc.info["pid"],
                    "name": proc.info["name"],
                    "username": proc.info["username"],
                    "memory_rss": mem_info.rss if mem_info else 0,
                    "memory_vms": mem_info.vms if mem_info else 0,
                    "memory_percent": proc.info["memory_percent"] or 0,
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        processes.sort(key=lambda x: x["memory_rss"], reverse=True)
        return {
            "tool": "get_memory_top_consumers",
            "status": "success",
            "data": processes[:limit],
            "risk_level": "safe",
        }

    @staticmethod
    def query_journal(since: str = "1 hour ago", lines: int = 50) -> Dict[str, Any]:
        try:
            result = subprocess.run(
                ["journalctl", f"--since={since}", "-n", str(lines), "--no-pager"],
                capture_output=True, text=True, timeout=10,
            )
            return {
                "tool": "query_journal",
                "status": "success",
                "data": {"since": since, "lines_requested": lines, "output": result.stdout.strip()},
                "risk_level": "low",
            }
        except FileNotFoundError:
            return {
                "tool": "query_journal",
                "status": "error",
                "error": "journalctl not available (systemd required)",
                "risk_level": "low",
            }
        except subprocess.TimeoutExpired:
            return {
                "tool": "query_journal",
                "status": "error",
                "error": "Query timed out",
                "risk_level": "low",
            }
        except Exception as e:
            return {
                "tool": "query_journal",
                "status": "error",
                "error": str(e),
                "risk_level": "low",
            }

    @staticmethod
    def search_log_file(filepath: str, pattern: str) -> Dict[str, Any]:
        resolved = Path(filepath).resolve()
        allowed_root = Path("/var/log").resolve()
        if not str(resolved).startswith(str(allowed_root)):
            return {
                "tool": "search_log_file",
                "status": "error",
                "error": f"Access denied: filepath must be under /var/log, got: {filepath}",
                "risk_level": "medium",
            }
        if not resolved.exists():
            return {
                "tool": "search_log_file",
                "status": "error",
                "error": f"File not found: {filepath}",
                "risk_level": "medium",
            }
        try:
            result = subprocess.run(
                ["grep", "-n", pattern, str(resolved)],
                capture_output=True, text=True, timeout=10,
            )
            lines = result.stdout.strip().splitlines()[:50]
            return {
                "tool": "search_log_file",
                "status": "success",
                "data": {"filepath": str(resolved), "pattern": pattern, "matches": len(lines), "lines": lines},
                "risk_level": "medium",
            }
        except subprocess.TimeoutExpired:
            return {
                "tool": "search_log_file",
                "status": "error",
                "error": "Search timed out",
                "risk_level": "medium",
            }
        except Exception as e:
            return {
                "tool": "search_log_file",
                "status": "error",
                "error": str(e),
                "risk_level": "medium",
            }

    @staticmethod
    def get_service_status(service_name: str) -> Dict[str, Any]:
        try:
            result = subprocess.run(
                ["systemctl", "status", service_name, "--no-pager"],
                capture_output=True, text=True, timeout=10,
            )
            return {
                "tool": "get_service_status",
                "status": "success",
                "data": {"service": service_name, "returncode": result.returncode, "output": result.stdout.strip()},
                "risk_level": "low",
            }
        except FileNotFoundError:
            return {
                "tool": "get_service_status",
                "status": "error",
                "error": "systemctl not available (systemd required)",
                "risk_level": "low",
            }
        except subprocess.TimeoutExpired:
            return {
                "tool": "get_service_status",
                "status": "error",
                "error": "Query timed out",
                "risk_level": "low",
            }
        except Exception as e:
            return {
                "tool": "get_service_status",
                "status": "error",
                "error": str(e),
                "risk_level": "low",
            }

    @staticmethod
    def list_failed_services() -> Dict[str, Any]:
        try:
            result = subprocess.run(
                ["systemctl", "--failed", "--no-pager"],
                capture_output=True, text=True, timeout=10,
            )
            return {
                "tool": "list_failed_services",
                "status": "success",
                "data": {"output": result.stdout.strip()},
                "risk_level": "low",
            }
        except FileNotFoundError:
            return {
                "tool": "list_failed_services",
                "status": "error",
                "error": "systemctl not available (systemd required)",
                "risk_level": "low",
            }
        except subprocess.TimeoutExpired:
            return {
                "tool": "list_failed_services",
                "status": "error",
                "error": "Query timed out",
                "risk_level": "low",
            }
        except Exception as e:
            return {
                "tool": "list_failed_services",
                "status": "error",
                "error": str(e),
                "risk_level": "low",
            }

    @staticmethod
    def check_failed_logins() -> Dict[str, Any]:
        try:
            result = subprocess.run(
                ["journalctl", "-u", "sshd", "--since", "1 hour ago", "--no-pager"],
                capture_output=True, text=True, timeout=10,
            )
            lines = result.stdout.splitlines()
            failed_lines = [
                line for line in lines
                if "failed" in line.lower() or "invalid" in line.lower()
            ][-20:]
            return {
                "tool": "check_failed_logins",
                "status": "success",
                "data": {"count": len(failed_lines), "entries": failed_lines},
                "risk_level": "low",
            }
        except FileNotFoundError:
            return {
                "tool": "check_failed_logins",
                "status": "error",
                "error": "journalctl not available (systemd required)",
                "risk_level": "low",
            }
        except subprocess.TimeoutExpired:
            return {
                "tool": "check_failed_logins",
                "status": "error",
                "error": "Query timed out",
                "risk_level": "low",
            }
        except Exception as e:
            return {
                "tool": "check_failed_logins",
                "status": "error",
                "error": str(e),
                "risk_level": "low",
            }

    @staticmethod
    def get_system_uptime() -> Dict[str, Any]:
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time
        data: Dict[str, Any] = {
            "boot_time": boot_time,
            "uptime_seconds": uptime_seconds,
        }
        if hasattr(os, "getloadavg"):
            load1, load5, load15 = os.getloadavg()
            data["load_average"] = {"1min": load1, "5min": load5, "15min": load15}
        return {
            "tool": "get_system_uptime",
            "status": "success",
            "data": data,
            "risk_level": "safe",
        }

    @staticmethod
    def run_safe_command(command: str) -> Dict[str, Any]:
        allowed_commands = [
            "ls", "ps", "df", "du", "free", "uptime", "whoami",
            "hostname", "uname", "date", "echo", "cat", "ss",
            "netstat", "ip", "iostat", "vmstat",
        ]
        cmd_parts = command.split()
        if not cmd_parts:
            return {
                "tool": "run_safe_command",
                "status": "error",
                "error": "Empty command",
                "risk_level": "medium",
            }
        base_cmd = cmd_parts[0]
        if base_cmd not in allowed_commands:
            return {
                "tool": "run_safe_command",
                "status": "error",
                "error": f"Command '{base_cmd}' not in allowed list. Allowed: {allowed_commands}",
                "risk_level": "medium",
            }
        if base_cmd == "cat" and len(cmd_parts) > 1:
            target = cmd_parts[1]
            resolved = Path(target).resolve()
            allowed_roots = [Path("/proc").resolve(), Path("/var/log").resolve()]
            if not any(str(resolved).startswith(str(root)) for root in allowed_roots):
                return {
                    "tool": "run_safe_command",
                    "status": "error",
                    "error": f"cat is restricted to /proc and /var/log paths, got: {target}",
                    "risk_level": "medium",
                }
        # 安全加固：禁止 shell 元字符，防止命令注入
        DANGEROUS_CHARS = set(";|&$`()>{}!#\n\\")
        if any(c in DANGEROUS_CHARS for c in command):
            return {
                "tool": "run_safe_command",
                "status": "error",
                "error": "命令包含非法字符（;|&$`等），已拦截",
                "risk_level": "high",
            }
        try:
            cmd_parts = shlex.split(command)
            result = subprocess.run(
                cmd_parts,
                shell=False,
                capture_output=True,
                text=True,
                timeout=settings.SAFETY.COMMAND_TIMEOUT,
            )
            return {
                "tool": "run_safe_command",
                "status": "success",
                "data": {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                },
                "risk_level": "medium",
            }
        except subprocess.TimeoutExpired:
            return {
                "tool": "run_safe_command",
                "status": "error",
                "error": "Command timed out",
                "risk_level": "medium",
            }
        except Exception as e:
            return {
                "tool": "run_safe_command",
                "status": "error",
                "error": str(e),
                "risk_level": "medium",
            }

    @staticmethod
    def backup_config(file_path: str, operation_id: str = "manual") -> Dict[str, Any]:
        """备份指定配置文件，在修改前自动调用"""
        result = config_backup.backup_file(file_path, operation_id)
        return {
            "tool": "backup_config",
            "status": "success" if result.get("success") else "error",
            "data": result,
            "risk_level": "low",
        }

    @staticmethod
    def rollback_operation(operation_id: str) -> Dict[str, Any]:
        """回滚指定操作的备份文件"""
        result = config_backup.rollback(operation_id)
        return {
            "tool": "rollback_operation",
            "status": "success" if result.get("success") else "error",
            "data": result,
            "risk_level": "high",
        }

    @staticmethod
    def list_available_tools() -> Dict[str, Any]:
        return {
            "tool": "list_available_tools",
            "status": "success",
            "data": [
                {
                    "name": "get_system_status",
                    "description": "获取完整的系统状态快照，包括CPU、内存、磁盘、进程和网络信息",
                    "params": {},
                    "risk_level": "safe",
                },
                {
                    "name": "get_process_list",
                    "description": "获取运行中的进程列表，支持按CPU、内存、PID、名称排序",
                    "params": {"limit": "int, 返回数量限制，默认20", "sort_by": "str, 排序字段: cpu_percent|memory_rss|pid|name，默认cpu_percent"},
                    "risk_level": "safe",
                },
                {
                    "name": "get_process_detail",
                    "description": "根据PID获取单个进程的详细信息，包括状态、命令行、内存等",
                    "params": {"pid": "int, 进程ID"},
                    "risk_level": "safe",
                },
                {
                    "name": "get_open_files",
                    "description": "获取指定进程打开的文件列表（使用lsof）",
                    "params": {"pid": "int, 进程ID"},
                    "risk_level": "safe",
                },
                {
                    "name": "kill_process",
                    "description": "向指定进程发送信号（默认SIGTERM），高危操作需确认",
                    "params": {"pid": "int, 进程ID", "signal": "int, 信号编号，默认15(SIGTERM)", "force_confirm": "bool, 必须为True才执行"},
                    "risk_level": "high",
                },
                {
                    "name": "get_network_connections",
                    "description": "获取当前活跃的网络连接列表",
                    "params": {},
                    "risk_level": "safe",
                },
                {
                    "name": "check_port_usage",
                    "description": "检查指定端口的使用情况和监听进程",
                    "params": {"port": "int, 端口号"},
                    "risk_level": "safe",
                },
                {
                    "name": "get_disk_usage",
                    "description": "获取所有挂载点的磁盘使用情况",
                    "params": {},
                    "risk_level": "safe",
                },
                {
                    "name": "get_large_files",
                    "description": "查找指定路径下超过给定大小的文件",
                    "params": {"size_mb": "int, 大小阈值(MB)，默认100", "search_path": "str, 搜索路径，默认/"},
                    "risk_level": "low",
                },
                {
                    "name": "get_memory_usage",
                    "description": "获取详细的内存使用信息，包括物理内存、swap和/proc/meminfo",
                    "params": {},
                    "risk_level": "safe",
                },
                {
                    "name": "get_memory_top_consumers",
                    "description": "获取内存占用最高的进程列表",
                    "params": {"limit": "int, 返回数量限制，默认10"},
                    "risk_level": "safe",
                },
                {
                    "name": "query_journal",
                    "description": "查询systemd journal日志",
                    "params": {"since": "str, 起始时间，默认'1 hour ago'", "lines": "int, 返回行数，默认50"},
                    "risk_level": "low",
                },
                {
                    "name": "search_log_file",
                    "description": "在/var/log下的日志文件中搜索匹配模式的行",
                    "params": {"filepath": "str, 日志文件路径（必须在/var/log下）", "pattern": "str, 搜索模式"},
                    "risk_level": "medium",
                },
                {
                    "name": "get_service_status",
                    "description": "查看systemd服务的运行状态",
                    "params": {"service_name": "str, 服务名称"},
                    "risk_level": "low",
                },
                {
                    "name": "list_failed_services",
                    "description": "列出所有失败的systemd服务",
                    "params": {},
                    "risk_level": "low",
                },
                {
                    "name": "check_failed_logins",
                    "description": "检查最近1小时内的SSH失败登录尝试",
                    "params": {},
                    "risk_level": "low",
                },
                {
                    "name": "get_system_uptime",
                    "description": "获取系统运行时间和负载均衡信息",
                    "params": {},
                    "risk_level": "safe",
                },
                {
                    "name": "run_safe_command",
                    "description": "执行白名单内的安全系统命令",
                    "params": {"command": "str, 命令字符串"},
                    "risk_level": "medium",
                },
                {
                    "name": "backup_config",
                    "description": "备份指定配置文件（在修改前自动调用，支持一键回滚）",
                    "params": {"file_path": "str, 要备份的文件路径", "operation_id": "str, 操作标识，默认'manual'"},
                    "risk_level": "low",
                },
                {
                    "name": "rollback_operation",
                    "description": "回滚指定操作的备份文件（一键恢复修改前状态）",
                    "params": {"operation_id": "str, 要回滚的操作标识"},
                    "risk_level": "high",
                },
            ],
        }


def execute_tool(tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    tool_map = {
        "get_system_status": MCPTools.get_system_status,
        "get_process_list": MCPTools.get_process_list,
        "get_process_detail": MCPTools.get_process_detail,
        "get_open_files": MCPTools.get_open_files,
        "kill_process": MCPTools.kill_process,
        "get_network_connections": MCPTools.get_network_connections,
        "check_port_usage": MCPTools.check_port_usage,
        "get_disk_usage": MCPTools.get_disk_usage,
        "get_large_files": MCPTools.get_large_files,
        "get_memory_usage": MCPTools.get_memory_usage,
        "get_memory_top_consumers": MCPTools.get_memory_top_consumers,
        "query_journal": MCPTools.query_journal,
        "search_log_file": MCPTools.search_log_file,
        "get_service_status": MCPTools.get_service_status,
        "list_failed_services": MCPTools.list_failed_services,
        "check_failed_logins": MCPTools.check_failed_logins,
        "get_system_uptime": MCPTools.get_system_uptime,
        "run_safe_command": MCPTools.run_safe_command,
        "backup_config": MCPTools.backup_config,
        "rollback_operation": MCPTools.rollback_operation,
        "list_available_tools": MCPTools.list_available_tools,
    }
    if tool_name not in tool_map:
        return {
            "tool": tool_name,
            "status": "error",
            "error": f"Unknown tool: {tool_name}",
        }
    try:
        return tool_map[tool_name](**params)
    except Exception as e:
        return {
            "tool": tool_name,
            "status": "error",
            "error": str(e),
        }
