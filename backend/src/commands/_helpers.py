"""Shared helpers used across all CLI command modules."""
from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path


# ── Colour / formatting ───────────────────────────────────────────────────────

def _bold(s: str) -> str:   return f"\033[1m{s}\033[0m"
def _dim(s: str) -> str:    return f"\033[2m{s}\033[0m"
def _green(s: str) -> str:  return f"\033[32m{s}\033[0m"
def _yellow(s: str) -> str: return f"\033[33m{s}\033[0m"
def _red(s: str) -> str:    return f"\033[31m{s}\033[0m"
def _blue(s: str) -> str:   return f"\033[34m{s}\033[0m"


def _band_colour(band: str) -> str:
    b = band.upper()
    if b == "GREEN":  return _green(b)
    if b == "YELLOW": return _yellow(b)
    return _red(b)


_CURRENCY_SYMBOLS: dict[str, str] = {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£"}


def _fmt_amount(amount: Decimal | None, currency: str = "INR") -> str:
    if amount is None:
        return "—"
    sym = _CURRENCY_SYMBOLS.get(str(currency), str(currency) + " ")
    return f"{sym}{amount:,.2f}"


def _truncate(s: str, n: int = 42) -> str:
    return s if len(s) <= n else s[:n - 1] + "…"


def _safe_uid(user_id: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in user_id)


# ── Database / repositories ───────────────────────────────────────────────────

def _get_db_session():
    """Return a SQLAlchemy Session connected to the shared SQLite DB."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from db.engine import init_db
    from config import get_settings

    db_url = get_settings().database_url
    if db_url.startswith("sqlite:///"):
        Path(db_url[len("sqlite:///"):]).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    init_db(engine)
    Session = sessionmaker(bind=engine, autoflush=True, autocommit=False)
    return Session()


def _repos(store_dir: Path, user_id: str):
    """Return (settings_repo, account_repo, institution_repo)."""
    from repositories.sqla_settings_repo import SqlAlchemySettingsRepository
    from repositories.sqla_account_repo import AccountRepository
    from repositories.sqla_institution_repo import SqlAlchemyInstitutionRepository

    session = _get_db_session()
    return (
        SqlAlchemySettingsRepository(session),
        AccountRepository(session),
        SqlAlchemyInstitutionRepository(session),
    )


def _load_profile(store_dir: Path, user_id: str) -> tuple[str, str]:
    """Return (display_name, base_currency). Falls back to (user_id, 'INR')."""
    try:
        from repositories.sqla_profile_repo import SqlAlchemyProfileRepository
        session = _get_db_session()
        repo = SqlAlchemyProfileRepository(session)
        profiles = repo.list(limit=1, sort_by="id")
        if profiles:
            p = profiles[0]
            return p.display_name, str(p.base_currency)
    except Exception:
        pass
    return user_id, "INR"


def _store_stats_line() -> str:
    from modules.store import store_stats
    s = store_stats()
    return s["store_dir"]


def _resolve_llm_provider(session, user_id: str, provider_id: str | None = None):
    """Return a configured LLM provider instance from the database, or None."""
    try:
        from sqlalchemy import select  # noqa: PLC0415
        from db.models.system import LlmProvider  # noqa: PLC0415

        if provider_id:
            stmt = select(LlmProvider).where(
                LlmProvider.provider_id == provider_id,
                LlmProvider.user_id == user_id,
            )
        else:
            stmt = select(LlmProvider).where(
                LlmProvider.user_id == user_id,
                LlmProvider.is_default.is_(True),
            )
        row = session.scalar(stmt)

        if row is None:
            # Fall back to first active provider
            stmt = select(LlmProvider).where(
                LlmProvider.user_id == user_id,
                LlmProvider.is_active.is_(True),
            )
            row = session.scalar(stmt)

        if row is None:
            return None

        name       = (row.provider_name or "").lower()
        api_key    = row.api_key or ""
        text_model = row.text_model or ""

        if "gemini" in name or "google" in name:
            from modules.llm.providers.gemini import GeminiProvider  # noqa: PLC0415
            return GeminiProvider(api_key=api_key, text_model=text_model or "gemini-3-flash-preview")
        if "openai" in name:
            from modules.llm.providers.openai_provider import OpenAIProvider  # noqa: PLC0415
            return OpenAIProvider(api_key=api_key, text_model=text_model or "gpt-4o-mini")
        if "anthropic" in name:
            from modules.llm.providers.anthropic_provider import AnthropicProvider  # noqa: PLC0415
            return AnthropicProvider(api_key=api_key, text_model=text_model or "claude-3-haiku-20240307")
    except Exception:
        pass
    return None
