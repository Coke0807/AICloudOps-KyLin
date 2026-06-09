#!/usr/bin/env python3
"""
重置演示数据脚本
清理旧数据并重新初始化，确保拦截率显示为 15%-30%
"""

import os
import sys

# 添加 backend 到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import database as db_module
from backend.init_demo_data import insert_demo_data, generate_audit_logs, verify_data_integrity

# 获取数据库实例
db = db_module.db


def clear_existing_data():
    """清理现有演示数据"""
    print("[Clear] 正在清理现有演示数据...")

    with db.get_connection() as conn:
        # 删除演示会话相关的消息
        demo_session_ids = [
            "demo-session-001", "demo-session-002", "demo-session-003",
            "demo-session-004", "demo-session-005", "demo-session-006",
            "demo-session-007", "demo-session-008",
        ]

        for session_id in demo_session_ids:
            conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            print(f"  [-] 清理会话: {session_id}")

        # 删除演示相关的审计日志
        demo_trace_ids = [
            "trace-001", "trace-002", "trace-003", "trace-004",
            "trace-005", "trace-006", "trace-007", "trace-008",
        ]

        for trace_id in demo_trace_ids:
            conn.execute("DELETE FROM audit_logs WHERE trace_id = ?", (trace_id,))
            print(f"  [-] 清理审计日志: {trace_id}")

    print("[OK] 现有数据清理完成！")


def main():
    """主函数"""
    print("=" * 60)
    print("🔄 AICloudOps 演示数据重置工具")
    print("=" * 60)

    # 1. 清理旧数据
    clear_existing_data()

    # 2. 插入新数据
    print()
    insert_demo_data()

    # 3. 生成审计日志
    print()
    generate_audit_logs()

    # 4. 验证数据完整性
    print()
    verify_data_integrity()

    print()
    print("=" * 60)
    print("✅ 演示数据重置完成！")
    print("=" * 60)
    print()
    print("📊 新的拦截率统计：")
    print("   - 总场景数：8")
    print("   - 安全通过：6 (75%)")
    print("   - 被拦截：2 (25%)")
    print()
    print("🚀 请重启后端服务以应用新的演示数据")


if __name__ == "__main__":
    main()
