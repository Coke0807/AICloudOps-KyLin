import os
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Literal


class SafetyConfig:
    MAX_TOOL_ROUNDS: int = 5
    RISK_THRESHOLD_BLOCK: float = 0.9
    RISK_THRESHOLD_CONFIRM: float = 0.6
    RISK_THRESHOLD_WARN: float = 0.3
    ENABLE_INJECTION_DETECTION: bool = True
    ENABLE_PARAMETER_VALIDATION: bool = True
    ENABLE_AUDIT_AGENT: bool = True
    ENABLE_SANDBOX: bool = True
    SAFEOPS_USER: str = "safeops"
    COMMAND_TIMEOUT: int = 30
    MAX_OUTPUT_LENGTH: int = 10000
    BACKUP_DIR: str = "data/backups"
    # 直接初始化默认值，避免 __post_init__ 不被调用的问题
    ALLOWED_ORIGINS: list = None  # None 时由 main.py 兜底


class Settings(BaseSettings):
    APP_NAME: str = "AICloudOps"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True

    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ============================================================
    # LLM 配置
    # ============================================================
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.deepseek.com/v1"
    LLM_MODEL: str = "deepseek-chat"
    LLM_TEMPERATURE: float = 0.3
    LLM_MAX_TOKENS: int = 2048
    LLM_MAX_RETRIES: int = 3
    
    # LLM 限流配置
    LLM_RATE_LIMIT_ENABLED: bool = True
    LLM_RATE_LIMIT_PER_HOUR: int = 100  # 每小时最大调用次数

    # ============================================================
    # 数据库配置
    # ============================================================
    DATABASE_TYPE: Literal["sqlite", "mysql"] = "sqlite"
    DATABASE_URL: str = "sqlite:///./data/aicops.db"
    
    # MySQL 配置（当 DATABASE_TYPE=mysql 时使用）
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "aicops"
    MYSQL_PASSWORD: str = "aicops_pass_2024"
    MYSQL_DATABASE: str = "aicops"

    # ============================================================
    # Redis 配置
    # ============================================================
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_ENABLED: bool = True
    
    # Redis 缓存配置
    REDIS_CACHE_EXPIRE: int = 300  # 默认缓存过期时间（秒）
    REDIS_SESSION_EXPIRE: int = 3600  # 会话过期时间（秒）
    REDIS_METRICS_EXPIRE: int = 5  # 系统指标缓存时间（秒）

    # ============================================================
    # 安全配置
    # ============================================================
    SAFETY: SafetyConfig = SafetyConfig()

    # ============================================================
    # 演示模式（Demo Mode）
    # ============================================================
    # 开启后，对预设 prompt 返回编排好的固定响应，绕过 LLM 和输入级安全拦截
    # 用于视频录制、功能演示等需要 100% 可复现结果的场景
    DEMO_MODE: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # 容忍 .env 中来自 Docker Compose 的额外变量（REDIS_PORT 等）
        extra = "ignore"
    
    def get_mysql_url(self) -> str:
        """构建 MySQL 连接 URL"""
        return f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
