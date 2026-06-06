import os
import platform
import psutil
import subprocess
import time
from typing import Dict, Any, List


class OSSensor:
    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        info = {
            "os": platform.system(),
            "os_version": platform.version(),
            "os_release": platform.release(),
            "architecture": platform.machine(),
            "hostname": platform.node(),
            "cpu_count_physical": psutil.cpu_count(logical=False),
            "cpu_count_logical": psutil.cpu_count(logical=True),
            "memory_total": psutil.virtual_memory().total,
            "boot_time": psutil.boot_time(),
        }
        try:
            info["cpu_freq"] = psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
        except Exception:
            info["cpu_freq"] = None
        return info

    @staticmethod
    def get_cpu_usage() -> Dict[str, Any]:
        per_cpu = psutil.cpu_percent(interval=0.5, percpu=True)
        overall = sum(per_cpu) / len(per_cpu) if per_cpu else 0.0
        result: Dict[str, Any] = {
            "overall": overall,
            "per_core": per_cpu,
        }
        try:
            times = psutil.cpu_times_percent(interval=0)
            result["times_percent"] = {
                "user": times.user,
                "system": times.system,
                "idle": times.idle,
                "iowait": getattr(times, "iowait", 0.0),
            }
        except Exception:
            pass
        try:
            result["ctx_switches"] = psutil.cpu_stats().ctx_switches
            result["interrupts"] = psutil.cpu_stats().interrupts
        except Exception:
            pass
        return result

    @staticmethod
    def get_memory_info() -> Dict[str, Any]:
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return {
            "total": mem.total,
            "available": mem.available,
            "used": mem.used,
            "free": mem.free,
            "percent": mem.percent,
            "buffers": getattr(mem, "buffers", 0),
            "cached": getattr(mem, "cached", 0),
            "shared": getattr(mem, "shared", 0),
            "swap_total": swap.total,
            "swap_used": swap.used,
            "swap_free": swap.free,
            "swap_percent": swap.percent,
        }

    @staticmethod
    def get_disk_info() -> List[Dict[str, Any]]:
        disks = []
        for part in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(part.mountpoint)
                disks.append({
                    "device": part.device,
                    "mountpoint": part.mountpoint,
                    "fstype": part.fstype,
                    "opts": part.opts,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent,
                })
            except (PermissionError, FileNotFoundError, OSError):
                continue
        return disks

    @staticmethod
    def get_process_list(limit: int = 20) -> List[Dict[str, Any]]:
        processes = []
        for proc in psutil.process_iter(["pid", "name", "username", "cpu_percent", "memory_info", "status", "create_time"]):
            try:
                info = proc.info
                processes.append({
                    "pid": info["pid"],
                    "name": info["name"],
                    "username": info["username"],
                    "cpu_percent": info["cpu_percent"],
                    "memory_rss": info["memory_info"].rss if info["memory_info"] else 0,
                    "memory_vms": info["memory_info"].vms if info["memory_info"] else 0,
                    "status": info["status"],
                    "create_time": info["create_time"],
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return sorted(processes, key=lambda x: x["cpu_percent"], reverse=True)[:limit]

    @staticmethod
    def get_network_connections() -> List[Dict[str, Any]]:
        connections = []
        for conn in psutil.net_connections():
            try:
                connections.append({
                    "fd": conn.fd,
                    "family": conn.family.name,
                    "type": conn.type.name,
                    "local_address": f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None,
                    "remote_address": f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None,
                    "status": conn.status,
                    "pid": conn.pid,
                })
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                continue
        return connections

    @staticmethod
    def get_memory_detail() -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        if platform.system() == "Linux":
            try:
                meminfo: Dict[str, int] = {}
                with open("/proc/meminfo", "r") as f:
                    for line in f:
                        parts = line.split(":")
                        if len(parts) == 2:
                            key = parts[0].strip()
                            val = parts[1].strip().split()[0]
                            meminfo[key] = int(val) * 1024

                fields = [
                    "MemTotal", "MemFree", "MemAvailable", "Buffers", "Cached",
                    "SwapTotal", "SwapFree", "Slab", "PageTables",
                ]
                for field in fields:
                    if field in meminfo:
                        result[field] = meminfo[field]

                if "MemTotal" in result and result["MemTotal"] > 0:
                    result["MemUsed"] = result["MemTotal"] - result.get("MemFree", 0)
                    result["MemUsedPercent"] = round(result["MemUsed"] / result["MemTotal"] * 100, 2)

                if "SwapTotal" in result and result["SwapTotal"] > 0:
                    result["SwapUsed"] = result["SwapTotal"] - result.get("SwapFree", 0)
                    result["SwapUsedPercent"] = round(result["SwapUsed"] / result["SwapTotal"] * 100, 2)
                else:
                    result["SwapUsed"] = 0
                    result["SwapUsedPercent"] = 0.0
            except Exception:
                mem = psutil.virtual_memory()
                swap = psutil.swap_memory()
                result = {
                    "MemTotal": mem.total,
                    "MemFree": mem.free,
                    "MemAvailable": mem.available,
                    "Buffers": getattr(mem, "buffers", 0),
                    "Cached": getattr(mem, "cached", 0),
                    "SwapTotal": swap.total,
                    "SwapFree": swap.free,
                    "Slab": 0,
                    "PageTables": 0,
                    "MemUsed": mem.used,
                    "MemUsedPercent": mem.percent,
                    "SwapUsed": swap.used,
                    "SwapUsedPercent": swap.percent,
                }
        else:
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            result = {
                "MemTotal": mem.total,
                "MemFree": mem.free,
                "MemAvailable": mem.available,
                "Buffers": getattr(mem, "buffers", 0),
                "Cached": getattr(mem, "cached", 0),
                "SwapTotal": swap.total,
                "SwapFree": swap.free,
                "Slab": 0,
                "PageTables": 0,
                "MemUsed": mem.used,
                "MemUsedPercent": mem.percent,
                "SwapUsed": swap.used,
                "SwapUsedPercent": swap.percent,
            }
        return result

    @staticmethod
    def get_network_interfaces() -> List[Dict[str, Any]]:
        interfaces = []
        try:
            counters = psutil.net_io_counters(pernic=True)
            addrs = psutil.net_if_addrs()
            for iface_name, stats in counters.items():
                iface: Dict[str, Any] = {
                    "name": iface_name,
                    "bytes_sent": stats.bytes_sent,
                    "bytes_recv": stats.bytes_recv,
                    "packets_sent": stats.packets_sent,
                    "packets_recv": stats.packets_recv,
                    "errin": stats.errin,
                    "errout": stats.errout,
                    "dropin": stats.dropin,
                    "dropout": stats.dropout,
                }
                if iface_name in addrs:
                    iface["addresses"] = [
                        {"family": addr.family.name, "address": addr.address, "netmask": addr.netmask}
                        for addr in addrs[iface_name]
                    ]
                interfaces.append(iface)
        except Exception:
            pass
        return interfaces

    @staticmethod
    def get_system_load() -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "cpu_count": psutil.cpu_count(logical=True),
        }
        try:
            load1, load5, load15 = os.getloadavg()
            result["load_1min"] = load1
            result["load_5min"] = load5
            result["load_15min"] = load15
        except (OSError, AttributeError):
            try:
                load1, load5, load15 = psutil.getloadavg()
                result["load_1min"] = load1
                result["load_5min"] = load5
                result["load_15min"] = load15
            except Exception:
                cpu_pct = psutil.cpu_percent(interval=0.1)
                result["load_1min"] = round(cpu_pct / 100 * psutil.cpu_count(logical=True), 2)
                result["load_5min"] = 0.0
                result["load_15min"] = 0.0
                result["estimated"] = True
        return result

    @staticmethod
    def get_disk_io() -> List[Dict[str, Any]]:
        disks = []
        try:
            counters = psutil.disk_io_counters(perdisk=True)
            for disk_name, stats in counters.items():
                disks.append({
                    "name": disk_name,
                    "read_count": stats.read_count,
                    "write_count": stats.write_count,
                    "read_bytes": stats.read_bytes,
                    "write_bytes": stats.write_bytes,
                    "read_time": stats.read_time,
                    "write_time": stats.write_time,
                })
        except Exception:
            pass
        return disks

    @staticmethod
    def get_top_resource_consumers(n: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        procs = []
        for proc in psutil.process_iter(["pid", "name", "username", "cpu_percent", "memory_percent", "memory_info"]):
            try:
                info = proc.info
                procs.append({
                    "pid": info["pid"],
                    "name": info["name"],
                    "username": info["username"],
                    "cpu_percent": info["cpu_percent"] or 0.0,
                    "memory_percent": info["memory_percent"] or 0.0,
                    "memory_rss": info["memory_info"].rss if info["memory_info"] else 0,
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        top_cpu = sorted(procs, key=lambda x: x["cpu_percent"], reverse=True)[:n]
        top_mem = sorted(procs, key=lambda x: x["memory_percent"], reverse=True)[:n]
        return {
            "top_cpu": top_cpu,
            "top_memory": top_mem,
        }

    @staticmethod
    def get_zombie_processes() -> List[Dict[str, Any]]:
        zombies = []
        for proc in psutil.process_iter(["pid", "name", "ppid", "status"]):
            try:
                if proc.info["status"] == psutil.STATUS_ZOMBIE:
                    zombies.append({
                        "pid": proc.info["pid"],
                        "name": proc.info["name"],
                        "ppid": proc.info["ppid"],
                        "status": proc.info["status"],
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return zombies

    @staticmethod
    def get_system_uptime() -> Dict[str, Any]:
        boot = psutil.boot_time()
        uptime_sec = time.time() - boot

        days = int(uptime_sec // 86400)
        hours = int((uptime_sec % 86400) // 3600)
        minutes = int((uptime_sec % 3600) // 60)
        seconds = int(uptime_sec % 60)

        parts = []
        if days > 0:
            parts.append(f"{days}天")
        if hours > 0:
            parts.append(f"{hours}小时")
        if minutes > 0:
            parts.append(f"{minutes}分钟")
        if not parts:
            parts.append(f"{seconds}秒")

        return {
            "boot_time": boot,
            "uptime_seconds": int(uptime_sec),
            "uptime_human": "".join(parts),
        }

    @staticmethod
    def run_system_command(cmd: str, timeout: int = 10) -> Dict[str, Any]:
        try:
            proc = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return {
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "returncode": proc.returncode,
                "timed_out": False,
            }
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": f"Command timed out after {timeout}s",
                "returncode": -1,
                "timed_out": True,
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
                "timed_out": False,
            }

    @staticmethod
    def _safe_call(func, default=None):
        """故障隔离: 单个传感器异常不影响整体快照"""
        try:
            return func()
        except Exception:
            return default if default is not None else {"error": "sensor unavailable"}

    @staticmethod
    def get_full_snapshot() -> Dict[str, Any]:
        _call = OSSensor._safe_call
        return {
            "system_info": _call(OSSensor.get_system_info, {}),
            "cpu": _call(OSSensor.get_cpu_usage, {}),
            "memory": _call(OSSensor.get_memory_info, {}),
            "memory_detail": _call(OSSensor.get_memory_detail, {}),
            "disks": _call(OSSensor.get_disk_info, []),
            "disk_io": _call(OSSensor.get_disk_io, []),
            "processes": _call(OSSensor.get_process_list, []),
            "network_connections": _call(OSSensor.get_network_connections, []),
            "network_interfaces": _call(OSSensor.get_network_interfaces, []),
            "system_load": _call(OSSensor.get_system_load, {}),
            "top_consumers": _call(OSSensor.get_top_resource_consumers, {}),
            "zombie_processes": _call(OSSensor.get_zombie_processes, []),
            "uptime": _call(OSSensor.get_system_uptime, {}),
        }
