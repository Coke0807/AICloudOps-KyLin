"""Plan-Execute 任务规划器 — 将复杂运维任务拆解为有序子任务"""

import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
from backend.core.llm_client import llm_client


class TaskComplexity(Enum):
    SIMPLE = "simple"       # 直接 ReAct: 查看CPU、查看内存
    MODERATE = "moderate"   # 需要 2-3 步: 排查磁盘满
    COMPLEX = "complex"     # 需要全局规划: 系统性能全面诊断


PLANNER_PROMPT = """你是一个运维任务规划器。根据用户请求，判断任务复杂度并生成执行计划。

## 可用工具
- get_system_status: 完整系统状态快照
- get_process_list: 进程列表
- get_process_detail: 单个进程详情
- get_memory_usage: 内存详情
- get_memory_top_consumers: 内存 Top 进程
- get_disk_usage: 磁盘使用
- get_large_files: 查找大文件
- get_network_connections: 瑞网连接
- check_port_usage: 端口检查
- query_journal: 系统日志
- search_log_file: 搜索日志文件
- get_service_status: 服务状态
- list_failed_services: 失败服务
- check_failed_logins: SSH 登录检查
- get_system_uptime: 运行时间
- run_safe_command: 安全命令执行

## 输出格式（严格JSON）
{
  "complexity": "simple" 或 "moderate" 或 "complex",
  "requires_plan": true/false,
  "plan": [
    {"step": 1, "tool": "工具名", "args": {}, "purpose": "目的说明"},
    {"step": 2, "tool": "工具名", "args": {}, "purpose": "目的说明", "depends_on": [1]}
  ],
  "reasoning": "规划思路说明"
}

## 判断规则
- simple（requires_plan=false）: 单步查询，如"查看CPU"、"列出进程"
- moderate（requires_plan=true）: 需要 2-3 步，如"磁盘满了帮我看看" → 查磁盘 → 找大文件 → 分析日志
- complex（requires_plan=true）: 系统性诊断，如"系统很卡帮我排查" → 查CPU → 查内存 → 查进程 → 查日志 → 综合分析"""


class TaskPlanner:
    """任务规划器 — 识别复杂度并生成执行计划"""

    async def plan(
        self, user_prompt: str, system_context: str = ""
    ) -> Dict[str, Any]:
        if llm_client.mock_mode:
            return self._mock_plan(user_prompt)

        context = f"当前系统上下文:\n{system_context}\n\n" if system_context else ""
        prompt = f"{context}用户请求: {user_prompt}\n\n请判断任务复杂度并生成执行计划。严格输出JSON。"

        try:
            response = await llm_client.chat(
                messages=[
                    {"role": "system", "content": PLANNER_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                stream=False,
            )
            content = response["choices"][0]["message"]["content"]
            return self._parse_plan(content)
        except Exception:
            return {
                "complexity": "simple",
                "requires_plan": False,
                "plan": [],
                "reasoning": "规划器调用失败，降级为直接执行",
            }

    @staticmethod
    def _parse_plan(content: str) -> Dict[str, Any]:
        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                result = json.loads(content[start:end])
                if "complexity" in result and "requires_plan" in result:
                    return result
        except (json.JSONDecodeError, ValueError):
            pass
        return {
            "complexity": "simple",
            "requires_plan": False,
            "plan": [],
            "reasoning": "解析失败，降级为简单模式",
        }

    @staticmethod
    def _mock_plan(user_prompt: str) -> Dict[str, Any]:
        prompt_lower = user_prompt.lower()

        # 复杂任务模式
        complex_patterns = ["系统很卡", "性能诊断", "全面检查", "全面排查", "系统体检"]
        if any(p in prompt_lower for p in complex_patterns):
            return {
                "complexity": "complex",
                "requires_plan": True,
                "plan": [
                    {"step": 1, "tool": "get_system_status", "args": {}, "purpose": "获取系统整体状态快照"},
                    {"step": 2, "tool": "get_process_list", "args": {"limit": 10, "sort_by": "cpu_percent"}, "purpose": "识别 CPU 消耗最高的进程"},
                    {"step": 3, "tool": "get_memory_top_consumers", "args": {"limit": 5}, "purpose": "识别内存消耗最高的进程", "depends_on": [1]},
                    {"step": 4, "tool": "get_disk_usage", "args": {}, "purpose": "检查磁盘空间使用"},
                    {"step": 5, "tool": "list_failed_services", "args": {}, "purpose": "检查是否有失败的服务"},
                ],
                "reasoning": "用户请求全面系统诊断，需要多维度采集数据后综合分析",
            }

        # 中等任务模式
        moderate_patterns = ["磁盘满", "磁盘使用", "排查", "为什么", "原因", "日志分析"]
        if any(p in prompt_lower for p in moderate_patterns):
            return {
                "complexity": "moderate",
                "requires_plan": True,
                "plan": [
                    {"step": 1, "tool": "get_disk_usage", "args": {}, "purpose": "查看磁盘空间使用情况"},
                    {"step": 2, "tool": "get_large_files", "args": {"size_mb": 100}, "purpose": "定位大文件", "depends_on": [1]},
                    {"step": 3, "tool": "query_journal", "args": {"since": "1 hour ago", "lines": 30}, "purpose": "检查近期系统日志"},
                ],
                "reasoning": "用户请求排查磁盘问题，按磁盘 → 大文件 → 日志的顺序诊断",
            }

        # 简单任务
        return {
            "complexity": "simple",
            "requires_plan": False,
            "plan": [],
            "reasoning": "简单查询任务，直接使用 ReAct 模式处理",
        }


task_planner = TaskPlanner()
