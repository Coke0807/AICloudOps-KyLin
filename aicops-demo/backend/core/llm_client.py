import httpx
import json
import asyncio
from typing import AsyncGenerator, Dict, Any, Optional
from backend.config import settings


class LLMClient:
    def __init__(self):
        self.api_key = settings.LLM_API_KEY
        self.base_url = settings.LLM_BASE_URL
        self.model = settings.LLM_MODEL
        # 增加超时时间到 180 秒（3分钟）
        self.client = httpx.AsyncClient(timeout=180.0)
        self.max_retries = 3
        self.retry_delay = 2.0  # 重试间隔2秒
        # Mock mode: if no API key, use mock responses
        self.mock_mode = not self.api_key or self.api_key == "your_deepseek_api_key_here"

    async def chat(
        self,
        messages: list[Dict[str, str]],
        tools: Optional[list[Dict[str, Any]]] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        if self.mock_mode:
            return await self._mock_chat(messages, tools)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2048,
            "stream": stream,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        if stream:
            return self._stream_chat(headers, payload)

        # 重试机制
        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = await self.client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=120.0,  # 单次请求超时 120 秒
                )
                response.raise_for_status()
                return response.json()
            except httpx.TimeoutException as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                raise Exception(f"API 请求超时（已重试{self.max_retries}次），请检查网络连接或稍后重试")
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    raise Exception("API Key 无效，请检查配置")
                elif e.response.status_code == 429:
                    raise Exception("API 请求过于频繁，请稍后再试")
                elif e.response.status_code >= 500:
                    # 服务器错误，尝试重试
                    last_error = e
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                        continue
                    raise Exception(f"API 服务器错误: {e.response.status_code}")
                else:
                    raise Exception(f"API 错误: {e.response.status_code}")
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                raise Exception(f"请求失败: {str(e)}")

        raise Exception(f"请求失败（已重试{self.max_retries}次）: {str(last_error)}")

    async def _mock_chat(
        self, messages: list[Dict[str, str]], tools: Optional[list[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Mock mode: return simulated responses without calling real API"""
        await asyncio.sleep(0.5)  # Simulate network delay

        user_message = messages[-1]["content"] if messages else ""

        # Check if tools are needed
        if tools and any(keyword in user_message.lower() for keyword in ["状态", "cpu", "内存", "磁盘", "进程"]):
            # Return a tool call
            return {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{
                            "id": "call_mock_001",
                            "type": "function",
                            "function": {
                                "name": "get_system_status",
                                "arguments": "{}"
                            }
                        }]
                    }
                }]
            }

        # Generate mock response based on user input
        mock_responses = {
            "你能帮我做什么": "我是 AICloudOps 智能运维助手，可以帮您：\n\n1. **系统监控** - 查看 CPU、内存、磁盘、进程状态\n2. **故障排查** - 分析系统异常、识别资源瓶颈\n3. **运维操作** - 执行安全的系统命令\n4. **日志分析** - 查看推理链路、审计记录\n\n请告诉我您需要什么帮助？",
            "帮助": "我可以帮您进行以下运维操作：\n\n- 查看系统整体状态\n- 检查 CPU 和内存使用情况\n- 查看磁盘空间占用\n- 列出运行中的进程\n- 执行安全的系统命令\n\n直接告诉我您的需求即可！",
            "状态": "我来帮您查看系统状态。",
            "cpu": "我来检查 CPU 使用情况。",
            "内存": "我来查看内存使用状态。",
            "磁盘": "我来检查磁盘空间。",
            "进程": "我来列出当前运行的进程。",
        }

        response_content = "您好！我是您的智能运维助手。我可以帮您监控系统状态、排查故障、执行运维操作。请问有什么可以帮您的？"

        for keyword, response in mock_responses.items():
            if keyword in user_message:
                response_content = response
                break

        return {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": response_content
                }
            }]
        }

    async def _stream_chat(
        self, headers: Dict[str, str], payload: Dict[str, Any]
    ) -> AsyncGenerator[Dict[str, str] | str, None]:
        if self.mock_mode:
            reasoning_chunks = ["分析用户请求...", "检查系统状态指标...", "综合判断后生成回复。"]
            for chunk in reasoning_chunks:
                await asyncio.sleep(0.15)
                yield {"type": "reasoning", "content": chunk}
            content_chunks = ["这是", "Mock", "模式", "的", "流式", "响应", "。"]
            for word in content_chunks:
                await asyncio.sleep(0.1)
                yield word
            return

        # buffer 用于处理跨 chunk 边界的 SSE 行
        buffer = ""
        async with self.client.stream(
            "POST",
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=120.0,
        ) as response:
            response.raise_for_status()
            async for raw_chunk in response.aiter_text():
                buffer += raw_chunk
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line.startswith("data: "):
                        continue
                    data = line[6:]
                    if data == "[DONE]":
                        return
                    try:
                        chunk = json.loads(data)
                        if chunk.get("choices"):
                            delta = chunk["choices"][0].get("delta", {})
                            # DeepSeek 等模型的思考链字段
                            if delta.get("reasoning_content"):
                                yield {"type": "reasoning", "content": delta["reasoning_content"]}
                            if delta.get("content"):
                                yield delta["content"]
                            if delta.get("tool_calls"):
                                yield {"tool_calls": delta["tool_calls"]}
                    except json.JSONDecodeError:
                        continue

    async def close(self):
        await self.client.aclose()


llm_client = LLMClient()
