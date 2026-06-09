"""
测试 LLM 配置是否正常工作
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
import httpx

# 加载环境变量
load_dotenv()

def test_llm_config():
    """测试 LLM 配置"""
    print("=" * 60)
    print("📋 LLM 配置信息")
    print("=" * 60)
    
    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL")
    model = os.getenv("LLM_MODEL")
    temperature = os.getenv("LLM_TEMPERATURE")
    max_tokens = os.getenv("LLM_MAX_TOKENS")
    
    print(f"API Key: {api_key[:20]}...{api_key[-10:] if api_key else 'None'}")
    print(f"Base URL: {base_url}")
    print(f"Model: {model}")
    print(f"Temperature: {temperature}")
    print(f"Max Tokens: {max_tokens}")
    print()
    
    if not api_key or not base_url or not model:
        print("❌ 配置不完整，请检查 .env 文件")
        return False
    
    print("=" * 60)
    print("🧪 测试 LLM API 调用")
    print("=" * 60)
    
    try:
        # 构造请求
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": "你好，请用一句话介绍你自己。"}
            ],
            "temperature": float(temperature) if temperature else 0.3,
            "max_tokens": int(max_tokens) if max_tokens else 2048,
            "stream": False
        }
        
        print(f"📤 发送请求到: {base_url}/chat/completions")
        print(f"📝 请求内容: {payload['messages'][0]['content']}")
        print()
        
        # 发送请求
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            
            print(f"📊 响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                
                # 提取响应内容
                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"]["content"]
                    print()
                    print("✅ LLM 响应成功!")
                    print("=" * 60)
                    print("🤖 LLM 回复:")
                    print("=" * 60)
                    print(content)
                    print()
                    
                    # 显示使用情况
                    if "usage" in result:
                        usage = result["usage"]
                        print("=" * 60)
                        print("📈 Token 使用情况:")
                        print(f"  - Prompt Tokens: {usage.get('prompt_tokens', 'N/A')}")
                        print(f"  - Completion Tokens: {usage.get('completion_tokens', 'N/A')}")
                        print(f"  - Total Tokens: {usage.get('total_tokens', 'N/A')}")
                    
                    return True
                else:
                    print("❌ 响应格式异常:")
                    print(result)
                    return False
            else:
                print(f"❌ 请求失败: {response.status_code}")
                print(f"错误信息: {response.text}")
                return False
                
    except httpx.TimeoutException:
        print("❌ 请求超时，请检查网络连接或 API 地址")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_backend_llm_client():
    """测试后端 LLM 客户端"""
    print()
    print("=" * 60)
    print("🔧 测试后端 LLM 客户端")
    print("=" * 60)
    
    try:
        from backend.core.llm_client import LLMClient
        from backend.config import settings
        
        print(f"✅ 成功导入 LLM 客户端")
        print(f"   API Key: {settings.LLM_API_KEY[:20]}...")
        print(f"   Base URL: {settings.LLM_BASE_URL}")
        print(f"   Model: {settings.LLM_MODEL}")
        print()
        
        # 创建客户端
        client = LLMClient()
        
        # 测试调用
        print("📤 发送测试请求...")
        response = client.chat("你好，请用一句话介绍你自己。")
        
        print()
        print("✅ LLM 客户端调用成功!")
        print("=" * 60)
        print("🤖 LLM 回复:")
        print("=" * 60)
        print(response)
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ 后端客户端测试失败: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # 测试 1: 直接 API 调用
    success1 = test_llm_config()
    
    # 测试 2: 后端客户端调用
    success2 = test_backend_llm_client()
    
    print()
    print("=" * 60)
    print("📊 测试总结")
    print("=" * 60)
    print(f"直接 API 调用: {'✅ 通过' if success1 else '❌ 失败'}")
    print(f"后端客户端调用: {'✅ 通过' if success2 else '❌ 失败'}")
    print()
    
    if success1 and success2:
        print("🎉 所有测试通过！LLM 配置正常工作。")
        sys.exit(0)
    else:
        print("⚠️ 部分测试失败，请检查配置。")
        sys.exit(1)
