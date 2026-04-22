# ============================================================
# app/core/config.py
# THE SINGLE SOURCE OF TRUTH FOR ALL CONFIGURATION
#
# HOW IT WORKS:
# 1. You add your keys to the .env file ONCE
# 2. Every file in the project imports:
#       from app.core.config import settings
# 3. Then uses: settings.OPENAI_API_KEY, settings.DATABASE_URL etc.
#
# You NEVER hardcode keys anywhere else.
# ============================================================

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """
    All configuration is loaded from the .env file automatically.
    Add your OpenAI key to .env once — it's available everywhere.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────
    APP_NAME: str = "Smart Document Q&A"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # ── OpenAI ── SET THIS ONCE IN .env ─────────────────────
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    OPENAI_MAX_TOKENS: int = 1000
    OPENAI_TEMPERATURE: float = 0.1

    # ── Database ─────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://user:password@db:5432/docqa"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # ── Redis / Celery ───────────────────────────────────────
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/1"

    # ── Embeddings ───────────────────────────────────────────
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384

    # ── FAISS ────────────────────────────────────────────────
    FAISS_INDEX_PATH: str = "/app/data/faiss"

    # ── Chunking ─────────────────────────────────────────────
    CHUNK_SIZE: int = 600
    CHUNK_OVERLAP: int = 120
    MAX_RETRIEVAL_K: int = 10
    RERANK_TOP_N: int = 5

    # ── Validation ───────────────────────────────────────────
    CONFIDENCE_THRESHOLD: float = 0.45
    HALLUCINATION_CHECK: bool = True

    # ── Rate Limiting ────────────────────────────────────────
    RATE_LIMIT_UPLOAD: str = "10/minute"
    RATE_LIMIT_QUERY: str = "30/minute"

    # ── File Upload ──────────────────────────────────────────
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: list[str] = [".pdf", ".docx"]


@lru_cache()
def get_settings() -> Settings:
    """
    Cached settings instance.
    Use this in FastAPI dependency injection:
        settings: Settings = Depends(get_settings)
    Or import directly:
        from app.core.config import settings
    """
    return Settings()


# Global singleton — import this anywhere
settings = get_settings()
