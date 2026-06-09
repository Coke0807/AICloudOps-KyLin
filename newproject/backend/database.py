import sqlite3
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
from contextlib import contextmanager


class Database:
    """SQLite 数据库封装（默认）"""
    
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.db_path = Path("data/aicops.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._initialized = True

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        with self.get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    trace_id TEXT,
                    safety_report TEXT,
                    tool_result TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                );

                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trace_id TEXT NOT NULL,
                    step TEXT NOT NULL,
                    step_order INTEGER NOT NULL,
                    data TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS tool_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trace_id TEXT,
                    tool_name TEXT NOT NULL,
                    params TEXT,
                    result TEXT,
                    status TEXT NOT NULL,
                    executed_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
                CREATE INDEX IF NOT EXISTS idx_audit_trace ON audit_logs(trace_id);
                CREATE INDEX IF NOT EXISTS idx_tool_trace ON tool_executions(trace_id);
            """)

    def create_session(self, title: str = None) -> str:
        session_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat() + "Z"
        with self.get_connection() as conn:
            conn.execute(
                "INSERT INTO sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (session_id, title or "新对话", now, now),
            )
        return session_id

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        trace_id: str = None,
        safety_report: Dict = None,
        tool_result: Dict = None,
    ) -> int:
        now = datetime.utcnow().isoformat() + "Z"
        with self.get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO messages (session_id, role, content, trace_id, safety_report, tool_result, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    session_id,
                    role,
                    content,
                    trace_id,
                    json.dumps(safety_report) if safety_report else None,
                    json.dumps(tool_result) if tool_result else None,
                    now,
                ),
            )
            conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (now, session_id),
            )
            return cursor.lastrowid

    def get_session_messages(self, session_id: str) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at",
                (session_id,),
            ).fetchall()
            return [
                {
                    "id": row["id"],
                    "role": row["role"],
                    "content": row["content"],
                    "trace_id": row["trace_id"],
                    "safety_report": json.loads(row["safety_report"]) if row["safety_report"] else None,
                    "tool_result": json.loads(row["tool_result"]) if row["tool_result"] else None,
                    "timestamp": row["created_at"],
                }
                for row in rows
            ]

    def get_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                """SELECT s.*, 
                          (SELECT COUNT(*) FROM messages WHERE session_id = s.id) as message_count,
                          (SELECT content FROM messages WHERE session_id = s.id ORDER BY created_at DESC LIMIT 1) as last_message
                   FROM sessions s 
                   ORDER BY s.updated_at DESC 
                   LIMIT ?""",
                (limit,),
            ).fetchall()
            return [
                {
                    "id": row["id"],
                    "title": row["title"],
                    "message_count": row["message_count"],
                    "preview": row["last_message"][:100] if row["last_message"] else None,
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
                for row in rows
            ]

    def delete_session(self, session_id: str) -> bool:
        with self.get_connection() as conn:
            conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            cursor = conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            return cursor.rowcount > 0

    def add_audit_log(self, trace_id: str, step: str, step_order: int, data: Dict[str, Any]):
        now = datetime.utcnow().isoformat() + "Z"
        with self.get_connection() as conn:
            conn.execute(
                "INSERT INTO audit_logs (trace_id, step, step_order, data, created_at) VALUES (?, ?, ?, ?, ?)",
                (trace_id, step, step_order, json.dumps(data), now),
            )

    def get_audit_logs(self, trace_id: str) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM audit_logs WHERE trace_id = ? ORDER BY step_order",
                (trace_id,),
            ).fetchall()
            return [
                {
                    "step": row["step"],
                    "step_order": row["step_order"],
                    "data": json.loads(row["data"]),
                    "timestamp": row["created_at"],
                }
                for row in rows
            ]

    def add_tool_execution(
        self,
        tool_name: str,
        params: Dict,
        result: Dict,
        status: str,
        trace_id: str = None,
    ):
        now = datetime.utcnow().isoformat() + "Z"
        with self.get_connection() as conn:
            conn.execute(
                """INSERT INTO tool_executions (trace_id, tool_name, params, result, status, executed_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (trace_id, tool_name, json.dumps(params), json.dumps(result), status, now),
            )


# SQLite 单例
db = Database()


# ============================================================
# 数据库工厂函数 - 根据配置选择数据库类型
# ============================================================

def get_database():
    """
    获取数据库实例（工厂函数）
    
    根据环境变量 DATABASE_TYPE 选择数据库：
    - sqlite: 使用 SQLite（默认，单机部署）
    - mysql: 使用 MySQL（生产环境，多实例部署）
    
    Returns:
        Database 或 MySQLDatabase 实例
    """
    from backend.config import get_settings
    
    settings = get_settings()
    
    if settings.DATABASE_TYPE == "mysql":
        # 延迟导入，避免未安装 aiomysql 时报错
        from backend.database_mysql import mysql_db
        return mysql_db
    else:
        return db


# 兼容性导出
__all__ = ['Database', 'db', 'get_database']
