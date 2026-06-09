"""
Redis 集成示例 - 展示如何在 API 路由中使用缓存和限流

此文件为示例代码，展示最佳实践
"""
from fastapi import HTTPException, Request
from backend.redis_client import redis_client
from backend.config import get_settings


# ============================================================
# 示例 1: LLM API 限流
# ============================================================

async def check_llm_rate_limit(user_id: int) -> None:
    """
    检查 LLM API 调用频率限制
    
    Args:
        user_id: 用户 ID
    
    Raises:
        HTTPException: 超过限流阈值时抛出 429 错误
    """
    settings = get_settings()
    
    if not settings.LLM_RATE_LIMIT_ENABLED:
        return
    
    rate_key = f"rate_limit:user_{user_id}:llm_call"
    
    result = await redis_client.rate_limit(
        key=rate_key,
        limit=settings.LLM_RATE_LIMIT_PER_HOUR,
        window=3600  # 1 小时
    )
    
    if not result["allowed"]:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limit_exceeded",
                "message": f"LLM API 调用次数已达上限（{settings.LLM_RATE_LIMIT_PER_HOUR}次/小时）",
                "reset_at": result["reset_at"],
                "remaining": 0
            }
        )
    
    # 可以在响应头中返回剩余配额
    # response.headers["X-RateLimit-Remaining"] = str(result["remaining"])


# ============================================================
# 示例 2: 用户权限缓存
# ============================================================

async def get_user_permissions_with_cache(user_id: int) -> dict:
    """
    获取用户权限（带缓存）
    
    Args:
        user_id: 用户 ID
    
    Returns:
        用户权限字典
    """
    # 1. 尝试从 Redis 缓存读取
    cached_permissions = await redis_client.get_user_permissions(user_id)
    
    if cached_permissions:
        return cached_permissions
    
    # 2. 缓存未命中，从数据库查询
    # 这里应该调用实际的数据库查询函数
    permissions = {
        "roles": ["admin"],
        "permissions": ["read", "write", "execute"],
        "tools": ["check_process", "kill_process"]
    }
    
    # 3. 写入缓存（5 分钟过期）
    await redis_client.cache_user_permissions(user_id, permissions, expire=300)
    
    return permissions


async def invalidate_user_permission_cache(user_id: int) -> None:
    """
    清除用户权限缓存（当权限变更时调用）
    
    Args:
        user_id: 用户 ID
    """
    await redis_client.invalidate_user_permissions(user_id)


# ============================================================
# 示例 3: 系统监控数据缓存
# ============================================================

async def get_system_metrics_with_cache() -> dict:
    """
    获取系统监控数据（带缓存）
    
    Returns:
        系统指标字典
    """
    # 1. 尝试从缓存读取
    cached_metrics = await redis_client.get_system_metrics()
    
    if cached_metrics:
        return cached_metrics
    
    # 2. 缓存未命中，实时采集
    from backend.core.os_sensor import OSSensor
    sensor = OSSensor()
    metrics = sensor.get_system_metrics()
    
    # 3. 写入缓存（5 秒过期）
    await redis_client.cache_system_metrics(metrics, expire=5)
    
    return metrics


# ============================================================
# 示例 4: 会话数据缓存
# ============================================================

async def cache_session_data(session_id: str, data: dict) -> None:
    """
    缓存会话数据
    
    Args:
        session_id: 会话 ID
        data: 会话数据
    """
    settings = get_settings()
    await redis_client.set_session(
        session_id,
        data,
        expire=settings.REDIS_SESSION_EXPIRE
    )


async def get_cached_session(session_id: str) -> dict | None:
    """
    获取缓存的会话数据
    
    Args:
        session_id: 会话 ID
    
    Returns:
        会话数据或 None
    """
    return await redis_client.get_session(session_id)


# ============================================================
# 示例 5: 在 FastAPI 路由中集成
# ============================================================

from fastapi import APIRouter, Depends

router = APIRouter()


@router.post("/chat")
async def chat(
    request: Request,
    message: str,
    user_id: int = 1  # 实际应从认证中间件获取
):
    """聊天接口（带限流和缓存）"""
    
    # 1. 检查限流
    await check_llm_rate_limit(user_id)
    
    # 2. 检查用户权限（带缓存）
    permissions = await get_user_permissions_with_cache(user_id)
    
    # 3. 调用 LLM Agent
    # ... 实际业务逻辑
    
    return {
        "response": "This is a sample response",
        "permissions": permissions
    }


@router.get("/system/metrics")
async def get_metrics():
    """获取系统指标（带缓存）"""
    metrics = await get_system_metrics_with_cache()
    return metrics


@router.post("/permissions/{user_id}/refresh")
async def refresh_permissions(user_id: int):
    """刷新用户权限缓存"""
    await invalidate_user_permission_cache(user_id)
    return {"message": "权限缓存已刷新"}
