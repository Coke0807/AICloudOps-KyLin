#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""快速测试API响应速度"""

import requests
import time

BASE_URL = "http://localhost:8000/api/v1"

def test_basic_apis():
    """测试基础API响应"""
    print("="*60)
    print("基础API响应测试")
    print("="*60)
    
    # 测试健康检查
    print("\n1. 健康检查API")
    start = time.time()
    resp = requests.get(f"{BASE_URL}/health", timeout=5)
    elapsed = time.time() - start
    print(f"   耗时: {elapsed:.2f}s")
    print(f"   响应: {resp.json()}")
    
    # 测试工具列表
    print("\n2. 工具列表API")
    start = time.time()
    resp = requests.get(f"{BASE_URL}/tools", timeout=5)
    elapsed = time.time() - start
    tools = resp.json().get("tools", [])
    print(f"   耗时: {elapsed:.2f}s")
    print(f"   工具数量: {len(tools)}")
    
    # 测试系统状态
    print("\n3. 系统状态API")
    start = time.time()
    resp = requests.get(f"{BASE_URL}/system/status", timeout=5)
    elapsed = time.time() - start
    data = resp.json().get("data", {})
    cpu_count = data.get("cpu", {}).get("count", 0)
    print(f"   耗时: {elapsed:.2f}s")
    print(f"   CPU核心数: {cpu_count}")
    
    # 测试Agent简单请求
    print("\n4. Agent简单请求 (测试超时)")
    start = time.time()
    try:
        resp = requests.post(
            f"{BASE_URL}/agent/process",
            json={"prompt": "你好", "session_id": "test_quick"},
            timeout=10
        )
        elapsed = time.time() - start
        print(f"   耗时: {elapsed:.2f}s")
        print(f"   状态码: {resp.status_code}")
        if resp.status_code == 200:
            result = resp.json()
            print(f"   步骤数: {len(result.get('steps', []))}")
            print(f"   答案长度: {len(result.get('final_answer', ''))}")
    except requests.exceptions.Timeout:
        elapsed = time.time() - start
        print(f"   ⚠️  请求超时 ({elapsed:.2f}s)")
    except Exception as e:
        elapsed = time.time() - start
        print(f"   ✗ 错误 ({elapsed:.2f}s): {e}")

if __name__ == "__main__":
    test_basic_apis()
