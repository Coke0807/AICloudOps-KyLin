import os
from pydantic_settings import BaseSettings
from functools import lru_cache


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
    ALLOWED_ORIGINS: list = None

    def __post_init__(self):
        if self.ALLOWED_ORIGINS is None:
            self.ALLOWED_ORIGINS = ["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000"]


class Settings(BaseSettings):
    APP_NAME: str = "AICloudOps"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True

    HOST: str = "0.0.0.0"
    PORT: int = 8000

    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.deepseek.com/v1"
    LLM_MODEL: str = "deepseek-chat"
    LLM_TEMPERATURE: float = 0.3
    LLM_MAX_TOKENS: int = 2048
    LLM_MAX_RETRIES: int = 3

    DATABASE_URL: str = "sqlite:///./data/aicops.db"

    SAFETY: SafetyConfig = SafetyConfig()

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
