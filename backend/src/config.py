"""Application configuration — loaded from environment variables or .env file.

Usage:
    from config import get_settings
    settings = get_settings()
    print(settings.gemini_api_key)

Environment variables (can also be placed in a .env file at project root):

    # LLM providers
    GEMINI_API_KEY=AIza...
    GEMINI_TEXT_MODEL=gemini-2.0-flash
    GEMINI_VISION_MODEL=gemini-2.0-flash

    OPENAI_API_KEY=sk-...
    OPENAI_TEXT_MODEL=gpt-4o
    OPENAI_VISION_MODEL=gpt-4o
    OPENAI_BASE_URL=             # Optional: override for Azure / local proxies

    ANTHROPIC_API_KEY=sk-ant-...
    ANTHROPIC_TEXT_MODEL=claude-3-7-sonnet-20250219
    ANTHROPIC_VISION_MODEL=claude-3-7-sonnet-20250219

    # Which provider to use by default (GOOGLE | OPENAI | ANTHROPIC)
    DEFAULT_LLM_PROVIDER=GOOGLE

    # Google OAuth (Sign-In)
    GOOGLE_CLIENT_ID=          # From Google Cloud Console → APIs & Services → Credentials

    # FastAPI / server
    APP_ENV=development          # development | staging | production
    APP_HOST=0.0.0.0
    APP_PORT=8000
    APP_DEBUG=true
    SECRET_KEY=change-me         # JWT signing key
    ALLOWED_ORIGINS=*            # Comma-separated CORS origins

    # File storage
    STORAGE_BACKEND=local        # local | s3
    STORAGE_BASE_PATH=./storage
    MAX_UPLOAD_SIZE_MB=50

    # Parser
    CONFIDENCE_THRESHOLD=0.75
    OCR_LANGUAGE=eng+hin
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Absolute path anchored to src/ so the DB is always at backend/src/ledger.db
# regardless of cwd (running from repo root, backend/, or backend/src/).
_SRC_DIR = Path(__file__).parent
_REPO_ROOT = _SRC_DIR.parent.parent
_REPO_DOTENV = _REPO_ROOT / ".env"
# Prefer repo-root .env so Alembic (cwd=backend/) and uvicorn (cwd=repo root) share one file.
_ENV_FILE = str(_REPO_DOTENV) if _REPO_DOTENV.is_file() else ".env"
_DEFAULT_DB_URL = "postgresql+asyncpg://app_service:password@localhost:6432/ledger"


class Settings(BaseSettings):
    """All application settings sourced from environment variables.

    Pydantic-settings automatically reads from:
    1. Environment variables (highest priority)
    2. .env file (if present at project root)
    3. Default values defined here
    """

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Google OAuth ─────────────────────────────────────────────────────────

    google_client_id: str = Field(default="", description="Google OAuth 2.0 Client ID for Sign-In")

    # ── Application ───────────────────────────────────────────────────────────

    app_env: str = Field(default="development", description="Environment: development | staging | production")
    app_host: str = Field(default="0.0.0.0", description="Bind host")
    app_port: int = Field(default=8000, description="Bind port")
    app_debug: bool = Field(default=False, description="Enable FastAPI debug mode")
    secret_key: str = Field(default="change-me-in-production", description="JWT signing secret key")
    jwt_expiry_hours: int = Field(default=720, description="JWT token expiry in hours (default 30 days)")
    allowed_origins: str = Field(default="*", description="Comma-separated CORS allowed origins")

    @property
    def cors_origins(self) -> list[str]:
        """Parse allowed_origins into a list."""
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    # ── LLM — Google Gemini ───────────────────────────────────────────────────

    gemini_api_key: str = Field(default="", description="Google AI Studio / Vertex API key")
    gemini_text_model: str = Field(default="gemini-3-flash-preview", description="Gemini model ID for text extraction")
    gemini_vision_model: str = Field(default="gemini-3-flash-preview", description="Gemini model ID for vision extraction")

    # ── LLM — OpenAI ─────────────────────────────────────────────────────────

    openai_api_key: str = Field(default="", description="OpenAI API key")
    openai_text_model: str = Field(default="gpt-4o", description="OpenAI model ID for text extraction")
    openai_vision_model: str = Field(default="gpt-4o", description="OpenAI model ID for vision extraction")
    openai_base_url: str | None = Field(default=None, description="Optional base URL override (Azure / proxy)")

    # ── LLM — Anthropic ───────────────────────────────────────────────────────

    anthropic_api_key: str = Field(default="", description="Anthropic API key")
    anthropic_text_model: str = Field(default="claude-3-5-sonnet-20241022", description="Anthropic model for text extraction")
    anthropic_vision_model: str = Field(default="claude-3-5-sonnet-20241022", description="Anthropic model for vision extraction")

    # ── LLM routing ───────────────────────────────────────────────────────────

    default_llm_provider: str = Field(default="GOOGLE", description="Default provider: GOOGLE | OPENAI | ANTHROPIC")

    # ── File storage ──────────────────────────────────────────────────────────

    storage_backend: str = Field(default="local", description="Storage backend: local | s3")
    storage_base_path: str = Field(default="./storage", description="Base directory for local file storage")
    max_upload_size_mb: int = Field(default=50, description="Maximum upload file size in MB")

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    # ── Parser ────────────────────────────────────────────────────────────────

    confidence_threshold: float = Field(default=0.75, ge=0.0, le=1.0, description="Minimum confidence for parse success")
    ocr_language: str = Field(default="eng+hin", description="Tesseract language string (e.g. 'eng+hin')")

    # ── Observability ─────────────────────────────────────────────────────────

    log_level: str = Field(default="INFO", description="Logging level: DEBUG | INFO | WARNING | ERROR")

    # ── Database ──────────────────────────────────────────────────────────────

    database_url: str = Field(
        default=_DEFAULT_DB_URL,
        description="SQLAlchemy database URL for app_service role (with RLS enforced)",
    )
    admin_database_url: str = Field(
        default="postgresql+asyncpg://superadmin:password@localhost:5432/ledger",
        description="SQLAlchemy database URL for superadmin role (bypasses RLS; admin routes only)",
    )

    def is_development(self) -> bool:
        return self.app_env.lower() == "development"

    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    def has_gemini(self) -> bool:
        return bool(self.gemini_api_key)

    def has_openai(self) -> bool:
        return bool(self.openai_api_key)

    def has_anthropic(self) -> bool:
        return bool(self.anthropic_api_key)

    def has_any_llm(self) -> bool:
        return self.has_gemini() or self.has_openai() or self.has_anthropic()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached settings singleton.

    Use this in FastAPI dependencies:
        from config import get_settings
        Depends(get_settings)
    """
    return Settings()
