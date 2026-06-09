from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from dotenv import load_dotenv
import os
import atexit

load_dotenv()

app = FastAPI(
    title="AICloudOps",
    description="面向麒麟操作系统的安全智能运维 Agent",
    version="1.0.0",
)


# ============================================================
# 应用生命周期管理
# ============================================================

@app.on_event("startup")
async def startup_event():
    """应用启动时初始化资源"""
    from backend.config import get_settings
    from backend.utils.audit_logger import audit_logger
    
    settings = get_settings()
    
    # 初始化 Redis
    if settings.REDIS_ENABLED:
        try:
            from backend.redis_client import redis_client
            await redis_client.initialize()
            audit_logger.log_system_event("redis_initialized", {
                "url": settings.REDIS_URL.split('@')[-1]
            })
        except Exception as e:
            audit_logger.log_system_event("redis_init_failed", {
                "error": str(e),
                "fallback": "memory_cache"
            })
    
    # 初始化 MySQL（如果配置为 MySQL）
    if settings.DATABASE_TYPE == "mysql":
        try:
            from backend.database_mysql import mysql_db
            await mysql_db.initialize()
            audit_logger.log_system_event("mysql_initialized", {
                "host": settings.MYSQL_HOST,
                "database": settings.MYSQL_DATABASE
            })
        except Exception as e:
            audit_logger.log_system_event("mysql_init_failed", {
                "error": str(e),
                "fallback": "sqlite"
            })

    # P9: Demo Mode 启动预热 — 预生成审计日志和 trace 数据
    if settings.DEMO_MODE:
        try:
            from backend.core.demo_engine import demo_engine
            await demo_engine.warmup()
            audit_logger.log_system_event("demo_warmup_completed", {})
        except Exception as e:
            audit_logger.log_system_event("demo_warmup_failed", {
                "error": str(e)
            })


@app.on_event("shutdown")
async def shutdown_event():
    """应用退出时清理资源"""
    from backend.core.llm_client import llm_client
    from backend.config import get_settings
    
    # 关闭 LLM 客户端
    await llm_client.close()
    
    # 关闭 Redis 连接
    settings = get_settings()
    if settings.REDIS_ENABLED:
        try:
            from backend.redis_client import redis_client
            await redis_client.close()
        except Exception:
            pass
    
    # 关闭 MySQL 连接池
    if settings.DATABASE_TYPE == "mysql":
        try:
            from backend.database_mysql import mysql_db
            await mysql_db.close()
        except Exception:
            pass


from backend.config import settings as app_settings

# CORS 安全加固：从配置读取允许的源，不再使用 "*"
_allowed_origins = app_settings.SAFETY.ALLOWED_ORIGINS or [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:5666",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5666",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)

from backend.api.routes import router, auth_router
app.include_router(auth_router, prefix="/api")
app.include_router(router, prefix="/api/v1")

frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="static")


@app.get("/api")
async def root():
    return {
        "service": "AICloudOps",
        "version": "1.0.0",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host=host, port=port)
