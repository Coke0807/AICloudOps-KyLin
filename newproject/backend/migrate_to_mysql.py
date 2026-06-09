"""
SQLite → MySQL 数据迁移脚本

用途：将现有 SQLite 数据库中的数据迁移到 MySQL
"""
import sqlite3
import json
import asyncio
from datetime import datetime
from pathlib import Path


async def migrate_to_mysql():
    """从 SQLite 迁移数据到 MySQL"""
    
    print("=" * 60)
    print("  SQLite → MySQL 数据迁移工具")
    print("=" * 60)
    print()
    
    # 1. 检查 SQLite 数据库是否存在
    sqlite_path = Path("data/aicops.db")
    if not sqlite_path.exists():
        print("[错误] SQLite 数据库不存在: data/aicops.db")
        return
    
    print(f"[1/5] 找到 SQLite 数据库: {sqlite_path}")
    
    # 2. 连接 SQLite
    sqlite_conn = sqlite3.connect(str(sqlite_path))
    sqlite_conn.row_factory = sqlite3.Row
    print("[2/5] SQLite 连接成功")
    
    # 3. 连接 MySQL
    try:
        from backend.database_mysql import mysql_db
        await mysql_db.initialize()
        print("[3/5] MySQL 连接成功")
    except Exception as e:
        print(f"[错误] MySQL 连接失败: {e}")
        print("[提示] 请确保 MySQL 容器已启动: docker-compose up -d mysql")
        return
    
    # 4. 迁移数据
    print("[4/5] 开始迁移数据...")
    
    # 迁移会话数据
    sessions = sqlite_conn.execute("SELECT * FROM sessions").fetchall()
    print(f"  - 会话数据: {len(sessions)} 条")
    
    async with mysql_db.get_connection() as mysql_conn:
        async with mysql_conn.cursor() as cursor:
            for session in sessions:
                await cursor.execute(
                    """INSERT IGNORE INTO sessions (id, title, created_at, updated_at)
                       VALUES (%s, %s, %s, %s)""",
                    (
                        session["id"],
                        session["title"],
                        datetime.fromisoformat(session["created_at"].replace("Z", "")),
                        datetime.fromisoformat(session["updated_at"].replace("Z", ""))
                    )
                )
    
    # 迁移消息数据
    messages = sqlite_conn.execute("SELECT * FROM messages").fetchall()
    print(f"  - 消息数据: {len(messages)} 条")
    
    async with mysql_db.get_connection() as mysql_conn:
        async with mysql_conn.cursor() as cursor:
            for msg in messages:
                await cursor.execute(
                    """INSERT IGNORE INTO messages 
                       (id, session_id, role, content, trace_id, safety_report, tool_result, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        msg["id"],
                        msg["session_id"],
                        msg["role"],
                        msg["content"],
                        msg["trace_id"],
                        msg["safety_report"],
                        msg["tool_result"],
                        datetime.fromisoformat(msg["created_at"].replace("Z", ""))
                    )
                )
    
    # 迁移审计日志
    audit_logs = sqlite_conn.execute("SELECT * FROM audit_logs").fetchall()
    print(f"  - 审计日志: {len(audit_logs)} 条")
    
    async with mysql_db.get_connection() as mysql_conn:
        async with mysql_conn.cursor() as cursor:
            for log in audit_logs:
                await cursor.execute(
                    """INSERT IGNORE INTO audit_logs (trace_id, step, step_order, data, created_at)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (
                        log["trace_id"],
                        log["step"],
                        log["step_order"],
                        log["data"],
                        datetime.fromisoformat(log["created_at"].replace("Z", ""))
                    )
                )
    
    # 迁移工具执行记录
    tool_executions = sqlite_conn.execute("SELECT * FROM tool_executions").fetchall()
    print(f"  - 工具执行记录: {len(tool_executions)} 条")
    
    async with mysql_db.get_connection() as mysql_conn:
        async with mysql_conn.cursor() as cursor:
            for exec in tool_executions:
                await cursor.execute(
                    """INSERT IGNORE INTO tool_executions 
                       (trace_id, tool_name, params, result, status, executed_at)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (
                        exec["trace_id"],
                        exec["tool_name"],
                        exec["params"],
                        exec["result"],
                        exec["status"],
                        datetime.fromisoformat(exec["executed_at"].replace("Z", ""))
                    )
                )
    
    # 5. 完成
    sqlite_conn.close()
    await mysql_db.close()
    
    print("[5/5] 迁移完成！")
    print()
    print("=" * 60)
    print("  数据迁移成功！")
    print("=" * 60)
    print()
    print("下一步：")
    print("  1. 修改 .env 文件: DATABASE_TYPE=mysql")
    print("  2. 重启后端服务: python -m uvicorn backend.main:app --reload")
    print()


if __name__ == "__main__":
    asyncio.run(migrate_to_mysql())
