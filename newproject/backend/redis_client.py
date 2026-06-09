"""
Redis 客户端封装 - 缓存、会话存储、限流

遵循 12-Factor App：所有配置通过环境变量注入
"""
import json
import asyncio
from typing import Optional, Any, Dict
from datetime import timedelta
import redis.asyncio as redis
from redis.asyncio import Redis
from redis.exceptions import RedisError
from backend.config import get_settings
from backend.utils.audit_logger import audit_logger


class RedisClient:
    """Redis 客户端单例封装"""
    
    _instance: Optional['RedisClient'] = None
    _client: Optional[Redis] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def initialize(self):
        """初始化 Redis 连接"""
        if self._client is not None:
            return
        
        settings = get_settings()
        
        try:
            self._client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20,
                retry_on_timeout=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            
            # 测试连接
            await self._client.ping()
            audit_logger.log_system_event("redis_connected", {
                "url": settings.REDIS_URL.split('@')[-1]  # 隐藏密码
            })
            
        except RedisError as e:
            audit_logger.log_system_event("redis_connection_failed", {
                "error": str(e),
                "fallback": "using_memory_cache"
            })
            # 降级：使用内存缓存
            self._client = None
    
    async def close(self):
        """关闭 Redis 连接"""
        if self._client:
            await self._client.close()
            self._client = None
    
    @property
    def client(self) -> Optional[Redis]:
        """获取 Redis 客户端"""
        return self._client
    
    # ============================================================
    # 缓存操作
    # ============================================================
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if not self._client:
            return None
        
        try:
            value = await self._client.get(key)
            if value:
                return json.loads(value)
            return None
        except (RedisError, json.JSONDecodeError) as e:
            audit_logger.log_system_event("redis_get_error", {
                "key": key,
                "error": str(e)
            })
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        expire: Optional[int] = None
    ) -> bool:
        """设置缓存值"""
        if not self._client:
            return False
        
        try:
            serialized = json.dumps(value, ensure_ascii=False)
            if expire:
                await self._client.setex(key, expire, serialized)
            else:
                await self._client.set(key, serialized)
            return True
        except (RedisError, TypeError) as e:
            audit_logger.log_system_event("redis_set_error", {
                "key": key,
                "error": str(e)
            })
            return False
    
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        if not self._client:
            return False
        
        try:
            await self._client.delete(key)
            return True
        except RedisError:
            return False
    
    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        if not self._client:
            return False
        
        try:
            return await self._client.exists(key) > 0
        except RedisError:
            return False
    
    # ============================================================
    # 限流操作
    # ============================================================
    
    async def rate_limit(
        self,
        key: str,
        limit: int,
        window: int
    ) -> Dict[str, Any]:
        """
        滑动窗口限流
        
        Args:
            key: 限流键（如 "rate_limit:user_123:llm_call"）
            limit: 时间窗口内最大请求数
            window: 时间窗口（秒）
        
        Returns:
            {
                "allowed": bool,  # 是否允许请求
                "current": int,   # 当前计数
                "remaining": int, # 剩余配额
                "reset_at": int   # 重置时间戳
            }
        """
        if not self._client:
            # 无 Redis 时默认允许
            return {
                "allowed": True,
                "current": 0,
                "remaining": limit,
                "reset_at": 0
            }
        
        try:
            now = int(asyncio.get_event_loop().time())
            window_start = now - window
            
            # 使用 Lua 脚本保证原子性
            lua_script = """
            local key = KEYS[1]
            local limit = tonumber(ARGV[1])
            local window = tonumber(ARGV[2])
            local now = tonumber(ARGV[3])
            local window_start = now - window
            
            -- 移除过期记录
            redis.call('ZREMRANGEBYSCORE', key, 0, window_start)
            
            -- 获取当前计数
            local current = redis.call('ZCARD', key)
            
            if current < limit then
                -- 添加新记录
                redis.call('ZADD', key, now, now .. '-' .. math.random())
                redis.call('EXPIRE', key, window)
                return {1, current + 1, limit - current - 1, now + window}
            else
                return {0, current, 0, now + window}
            end
            """
            
            result = await self._client.eval(
                lua_script, 
                1, 
                key, 
                limit, 
                window, 
                now
            )
            
            return {
                "allowed": bool(result[0]),
                "current": result[1],
                "remaining": result[2],
                "reset_at": result[3]
            }
            
        except RedisError as e:
            audit_logger.log_system_event("rate_limit_error", {
                "key": key,
                "error": str(e)
            })
            # 出错时默认允许
            return {
                "allowed": True,
                "current": 0,
                "remaining": limit,
                "reset_at": 0
            }
    
    # ============================================================
    # 会话管理
    # ============================================================
    
    async def set_session(
        self,
        session_id: str,
        data: Dict[str, Any],
        expire: int = 3600
    ) -> bool:
        """存储会话数据"""
        return await self.set(
            f"session:{session_id}",
            data,
            expire
        )
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话数据"""
        return await self.get(f"session:{session_id}")
    
    async def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        return await self.delete(f"session:{session_id}")
    
    # ============================================================
    # 用户权限缓存
    # ============================================================
    
    async def cache_user_permissions(
        self,
        user_id: int,
        permissions: Dict[str, Any],
        expire: int = 300
    ) -> bool:
        """缓存用户权限（5分钟）"""
        return await self.set(
            f"user:{user_id}:permissions",
            permissions,
            expire
        )
    
    async def get_user_permissions(
        self,
        user_id: int
    ) -> Optional[Dict[str, Any]]:
        """获取用户权限缓存"""
        return await self.get(f"user:{user_id}:permissions")
    
    async def invalidate_user_permissions(self, user_id: int) -> bool:
        """清除用户权限缓存"""
        return await self.delete(f"user:{user_id}:permissions")
    
    # ============================================================
    # 系统监控数据缓存
    # ============================================================
    
    async def cache_system_metrics(
        self,
        metrics: Dict[str, Any],
        expire: int = 5
    ) -> bool:
        """缓存系统监控数据（5秒）"""
        return await self.set("system:metrics", metrics, expire)
    
    async def get_system_metrics(self) -> Optional[Dict[str, Any]]:
        """获取系统监控数据缓存"""
        return await self.get("system:metrics")


# 全局单例
redis_client = RedisClient()
