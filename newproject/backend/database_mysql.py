"""
MySQL 数据库封装 - 支持异步操作

遵循 12-Factor App：通过环境变量切换数据库类型
"""
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

try:
    import aiomysql
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False

from backend.config import get_settings
from backend.utils.audit_logger import audit_logger


class MySQLDatabase:
    """MySQL 异步数据库封装"""
    
    _instance: Optional['MySQLDatabase'] = None
    _pool: Optional[aiomysql.Pool] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    async def initialize(self):
        """初始化 MySQL 连接池"""
        if self._initialized:
            return
        
        if not MYSQL_AVAILABLE:
            raise RuntimeError("aiomysql 未安装，请运行: pip install aiomysql")
        
        settings = get_settings()
        
        try:
            # 解析 MySQL 连接 URL
            # 格式: mysql://user:password@host:port/database
            url = settings.DATABASE_URL.replace('mysql://', '').replace('mysql+aiomysql://', '')
            user_pass, host_port_db = url.split('@')
            user, password = user_pass.split(':')
            host_port, database = host_port_db.split('/')
            
            if ':' in host_port:
                host, port = host_port.split(':')
                port = int(port)
            else:
                host = host_port
                port = 3306
            
            # 创建连接池
            self._pool = await aiomysql.create_pool(
                host=host,
                port=port,
                user=user,
                password=password,
                db=database,
                minsize=5,
                maxsize=20,
                autocommit=False,
                charset='utf8mb4',
                cursorclass=aiomysql.DictCursor
            )
            
            # 初始化表结构
            await self._init_db()
            
            self._initialized = True
            
            audit_logger.log_system_event("mysql_connected", {
                "host": host,
                "database": database,
                "pool_size": 20
            })
            
        except Exception as e:
            audit_logger.log_system_event("mysql_connection_failed", {
                "error": str(e)
            })
            raise
    
    async def close(self):
        """关闭连接池"""
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
    
    @asynccontextmanager
    async def get_connection(self):
        """获取数据库连接"""
        if not self._pool:
            raise RuntimeError("MySQL 连接池未初始化")
        
        async with self._pool.acquire() as conn:
            try:
                yield conn
                await conn.commit()
            except Exception:
                await conn.rollback()
                raise
    
    async def _init_db(self):
        """初始化数据库表结构"""
        async with self.get_connection() as conn:
            async with conn.cursor() as cursor:
                # 创建表（MySQL 语法）
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        id VARCHAR(36) PRIMARY KEY,
                        title VARCHAR(255),
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME NOT NULL,
                        INDEX idx_updated_at (updated_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
                
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        session_id VARCHAR(36) NOT NULL,
                        role VARCHAR(50) NOT NULL,
                        content TEXT NOT NULL,
                        trace_id VARCHAR(36),
                        safety_report JSON,
                        tool_result JSON,
                        created_at DATETIME NOT NULL,
                        FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
                        INDEX idx_session_created (session_id, created_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
                
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS audit_logs (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        trace_id VARCHAR(36) NOT NULL,
                        step VARCHAR(100) NOT NULL,
                        step_order INT NOT NULL,
                        data JSON NOT NULL,
                        created_at DATETIME NOT NULL,
                        INDEX idx_trace (trace_id, step_order)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
                
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS tool_executions (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        trace_id VARCHAR(36),
                        tool_name VARCHAR(100) NOT NULL,
                        params JSON,
                        result JSON,
                        status VARCHAR(50) NOT NULL,
                        executed_at DATETIME NOT NULL,
                        INDEX idx_trace (trace_id),
                        INDEX idx_tool_status (tool_name, status)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
    
    # ============================================================
    # 会话管理
    # ============================================================
    
    async def create_session(self, title: str = None) -> str:
        """创建新会话"""
        session_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        async with self.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "INSERT INTO sessions (id, title, created_at, updated_at) VALUES (%s, %s, %s, %s)",
                    (session_id, title or "新对话", now, now)
                )
        
        return session_id
    
    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        trace_id: str = None,
        safety_report: Dict = None,
        tool_result: Dict = None,
    ) -> int:
        """添加消息"""
        now = datetime.utcnow()
        
        async with self.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """INSERT INTO messages 
                       (session_id, role, content, trace_id, safety_report, tool_result, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (
                        session_id,
                        role,
                        content,
                        trace_id,
                        json.dumps(safety_report) if safety_report else None,
                        json.dumps(tool_result) if tool_result else None,
                        now,
                    )
                )
                message_id = cursor.lastrowid
                
                # 更新会话时间
                await cursor.execute(
                    "UPDATE sessions SET updated_at = %s WHERE id = %s",
                    (now, session_id)
                )
                
                return message_id
    
    async def get_session_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """获取会话消息列表"""
        async with self.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT * FROM messages WHERE session_id = %s ORDER BY created_at",
                    (session_id,)
                )
                rows = await cursor.fetchall()
                
                return [
                    {
                        "id": row["id"],
                        "role": row["role"],
                        "content": row["content"],
                        "trace_id": row["trace_id"],
                        "safety_report": json.loads(row["safety_report"]) if row["safety_report"] else None,
                        "tool_result": json.loads(row["tool_result"]) if row["tool_result"] else None,
                        "timestamp": row["created_at"].isoformat() + "Z",
                    }
                    for row in rows
                ]
    
    async def get_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取会话列表"""
        async with self.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """SELECT s.*, 
                              (SELECT COUNT(*) FROM messages WHERE session_id = s.id) as message_count,
                              (SELECT content FROM messages WHERE session_id = s.id ORDER BY created_at DESC LIMIT 1) as last_message
                       FROM sessions s 
                       ORDER BY s.updated_at DESC 
                       LIMIT %s""",
                    (limit,)
                )
                rows = await cursor.fetchall()
                
                return [
                    {
                        "id": row["id"],
                        "title": row["title"],
                        "message_count": row["message_count"],
                        "preview": row["last_message"][:100] if row["last_message"] else None,
                        "created_at": row["created_at"].isoformat() + "Z",
                        "updated_at": row["updated_at"].isoformat() + "Z",
                    }
                    for row in rows
                ]
    
    async def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        async with self.get_connection() as conn:
            async with conn.cursor() as cursor:
                # 外键级联删除会自动删除消息
                await cursor.execute(
                    "DELETE FROM sessions WHERE id = %s",
                    (session_id,)
                )
                return cursor.rowcount > 0
    
    # ============================================================
    # 审计日志
    # ============================================================
    
    async def add_audit_log(
        self,
        trace_id: str,
        step: str,
        step_order: int,
        data: Dict[str, Any]
    ):
        """添加审计日志"""
        now = datetime.utcnow()
        
        async with self.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "INSERT INTO audit_logs (trace_id, step, step_order, data, created_at) VALUES (%s, %s, %s, %s, %s)",
                    (trace_id, step, step_order, json.dumps(data), now)
                )
    
    async def get_audit_logs(self, trace_id: str) -> List[Dict[str, Any]]:
        """获取审计日志"""
        async with self.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT * FROM audit_logs WHERE trace_id = %s ORDER BY step_order",
                    (trace_id,)
                )
                rows = await cursor.fetchall()
                
                return [
                    {
                        "step": row["step"],
                        "step_order": row["step_order"],
                        "data": json.loads(row["data"]),
                        "timestamp": row["created_at"].isoformat() + "Z",
                    }
                    for row in rows
                ]
    
    # ============================================================
    # 工具执行记录
    # ============================================================
    
    async def add_tool_execution(
        self,
        tool_name: str,
        params: Dict,
        result: Dict,
        status: str,
        trace_id: str = None,
    ):
        """添加工具执行记录"""
        now = datetime.utcnow()
        
        async with self.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """INSERT INTO tool_executions 
                       (trace_id, tool_name, params, result, status, executed_at)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (trace_id, tool_name, json.dumps(params), json.dumps(result), status, now)
                )


# 全局单例
mysql_db = MySQLDatabase()
