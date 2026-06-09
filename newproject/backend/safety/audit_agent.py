"""Audit Agent — 轻量级动态意图对齐代理

独立于主 Agent 的二次校验层，检测"用户原始意图"与"Agent 生成的指令"之间的偏移。
例如：用户说"清理日志"，Agent 却去"重启网络" → 阻断。
"""

import json
from typing import Dict, Any, Optional
from backend.core.llm_client import llm_client
from backend.config import settings


AUDIT_SYSTEM_PROMPT = """你是一个安全审计代理。你的唯一职责是判断：AI助手即将执行的操作，是否与用户的原始意图一致。

## 判定规则
1. 如果操作与用户意图一致或属于合理的诊断步骤 → approved
2. 如果操作偏离了用户意图，但属于合理的关联排查 → approved（附带说明）
3. 如果操作完全不相关，或属于高危操作且用户未明确要求 → blocked

## 输出格式（严格JSON）
{"decision": "approved" 或 "blocked", "confidence": 0.0-1.0, "reason": "简短说明"}

## 示例
- 用户说"查看磁盘使用"，Agent 执行 get_disk_usage → approved
- 用户说"清理日志"，Agent 先查看大文件再删除 → approved（合理诊断链）
- 用户说"查看CPU"，Agent 要去重启网络服务 → blocked（意图偏移）
- 用户说"帮我看看系统状态"，Agent 执行 kill_process → blocked（未经确认的高危操作）"""


class AuditAgent:
    """轻量级意图对齐审计代理"""

    # 高危工具列表 — 这些工具调用时必须触发审计
    HIGH_RISK_TOOLS = {"kill_process", "run_safe_command", "rollback_operation"}

    async def validate_intent_alignment(
        self,
        user_prompt: str,
        tool_name: str,
        tool_args: Dict[str, Any],
        agent_reasoning: str = "",
    ) -> Dict[str, Any]:
        """校验工具调用是否与用户意图一致

        对只读工具跳过审计以节省 token，仅对高危工具做严格校验。
        """
        # 只读工具默认放行
        if tool_name not in self.HIGH_RISK_TOOLS:
            return {
                "decision": "approved",
                "confidence": 1.0,
                "reason": "只读工具，自动放行",
                "audit_skipped": True,
            }

        if llm_client.mock_mode:
            return self._mock_audit(user_prompt, tool_name, tool_args)

        audit_prompt = f"""用户原始请求: {user_prompt}

AI助手即将执行的工具: {tool_name}
工具参数: {json.dumps(tool_args, ensure_ascii=False)}
{f'助手推理过程: {agent_reasoning}' if agent_reasoning else ''}

请判断此操作是否与用户意图一致。严格输出JSON格式。"""

        try:
            response = await llm_client.chat(
                messages=[
                    {"role": "system", "content": AUDIT_SYSTEM_PROMPT},
                    {"role": "user", "content": audit_prompt},
                ],
                stream=False,
            )
            content = response["choices"][0]["message"]["content"]
            result = self._parse_audit_result(content)
            result["audit_skipped"] = False
            return result
        except Exception:
            # 安全第一：审计失败时阻断高危操作，避免 LLM 超时导致误放行
            return {
                "decision": "blocked",
                "confidence": 0.5,
                "reason": "审计服务不可用，出于安全考虑拒绝执行高危操作",
                "audit_skipped": False,
                "audit_error": True,
            }

    @staticmethod
    def _parse_audit_result(content: str) -> Dict[str, Any]:
        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(content[start:end])
        except (json.JSONDecodeError, ValueError):
            pass
        return {
            "decision": "blocked",
            "confidence": 0.5,
            "reason": "审计结果解析失败，出于安全考虑阻断执行",
        }

    @staticmethod
    def _mock_audit(
        user_prompt: str, tool_name: str, tool_args: Dict[str, Any]
    ) -> Dict[str, Any]:
        # Mock 模式下的简单规则校验
        dangerous_keywords = ["删除", "重启", "关机", "kill", "格式化"]
        user_lower = user_prompt.lower()

        has_dangerous_intent = any(kw in user_lower for kw in dangerous_keywords)

        if tool_name == "kill_process" and not has_dangerous_intent:
            return {
                "decision": "blocked",
                "confidence": 0.9,
                "reason": "用户未请求终止进程，但 Agent 即将执行 kill_process，意图偏移",
                "audit_skipped": False,
            }

        return {
            "decision": "approved",
            "confidence": 0.85,
            "reason": "操作与用户意图一致",
            "audit_skipped": False,
        }


audit_agent = AuditAgent()
