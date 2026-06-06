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

# 资源清理: 应用退出时关闭 httpx 异步客户端，防止连接泄漏
@app.on_event("shutdown")
async def shutdown_event():
    from backend.core.llm_client import llm_client
    await llm_client.close()

from backend.config import settings as app_settings

# CORS 安全加固：从配置读取允许的源，不再使用 "*"
_allowed_origins = app_settings.SAFETY.ALLOWED_ORIGINS or [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)

from backend.api.routes import router
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
