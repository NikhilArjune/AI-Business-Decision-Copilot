"""
AI Business Decision Copilot - Backend Configuration
"""

from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "AI Business Decision Copilot"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./copilot.db"

    # JWT Auth
    JWT_SECRET_KEY: str = "dev-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # File Upload
    MAX_UPLOAD_SIZE_MB: int = 50
    UPLOAD_DIR: str = "./uploads"

    # Google Gemini
    GOOGLE_API_KEY: str = ""

    # Backend
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
