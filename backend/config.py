"""Application configuration.

All configuration is sourced from environment variables (see .env.example).
Nothing in this module hardcodes secrets or environment-specific paths, so the
same image can run locally, on Render, or anywhere else that supplies
env vars.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings, loaded once and cached."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- App ---
    app_name: str = "ReceiptMind"
    environment: str = Field(default="development")  # development | production
    log_level: str = Field(default="INFO")

    # --- CORS ---
    # Comma-separated list of allowed origins, e.g. the deployed Vercel URL.
    cors_origins: str = Field(default="http://localhost:5173")

    # --- Vision provider (receipt extraction) ---
    vision_provider: str = Field(default="gemini")
    gemini_api_key: str = Field(default="")
    gemini_vision_model: str = Field(default="gemini-2.5-flash")

    openrouter_api_key: str = ""
    openrouter_model: str = "openrouter/free"

    # --- Embedding provider (semantic search) ---
    # API-based by default: no local ML model is loaded, so the backend stays
    # a thin, fast container with no torch/sentence-transformers dependency.
    embedding_provider: str = Field(default="gemini")
    gemini_embedding_model: str = Field(default="gemini-embedding-001")
    embedding_dimensions: int = Field(default=768)

    # --- Database ---
    # SQLite locally; use Supabase's Postgres connection string in production.
    database_url: str = Field(default="sqlite:///./data/receiptmind.db")

    # --- Receipt image storage ---
    upload_dir: str = Field(default="./data/uploads")
    supabase_url: str = Field(default="")
    supabase_service_role_key: str = Field(default="")
    supabase_storage_bucket: str = Field(default="receipts")
    max_upload_mb: int = Field(default=15)

    # --- Extraction ---
    extraction_max_retries: int = Field(default=2)
    extraction_timeout_seconds: int = Field(default=45)

    @field_validator("cors_origins")
    @classmethod
    def _strip_origins(cls, v: str) -> str:
        return v.strip()

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @model_validator(mode="after")
    def _validate_production_storage(self) -> Settings:
        if bool(self.supabase_url.strip()) != bool(self.supabase_service_role_key.strip()):
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set together")
        if self.environment.lower() == "production" and not self.database_url.startswith("postgres"):
            raise ValueError("Production requires a Supabase Postgres DATABASE_URL")
        if self.database_url.startswith("postgres") and not self.supabase_storage_enabled:
            raise ValueError("Postgres deployments require Supabase Storage configuration")
        return self

    @property
    def sqlite_path(self) -> Path:
        """Filesystem path of the sqlite DB, derived from database_url."""
        if not self.database_url.startswith("sqlite:"):
            raise ValueError("sqlite_path is only available when DATABASE_URL uses SQLite")
        raw = self.database_url.split("sqlite:///", 1)[-1]
        return Path(raw)

    @property
    def supabase_storage_enabled(self) -> bool:
        return bool(self.supabase_url.strip() and self.supabase_service_role_key.strip())

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
