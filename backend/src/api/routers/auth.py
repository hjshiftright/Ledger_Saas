"""Authentication endpoints — signup, login, logout, status check.

Provides local authentication using bcrypt-hashed passwords and signed JWTs.
Tokens are returned to the client and stored in localStorage; the client sends
  Authorization: Bearer <token>
on every subsequent request.

Endpoints:
    GET  /api/v1/auth/status   — Check if any users exist
    POST /api/v1/auth/signup   — Create a new user account
    POST /api/v1/auth/login    — Authenticate with email + password
    POST /api/v1/auth/logout   — Acknowledge logout (client discards token)
    POST /api/v1/auth/reset-db — Delete DB and reinitialize (DEV ONLY)
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.deps import get_db
from config import Settings, get_settings
from db.models.users import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class AuthStatusResponse(BaseModel):
    has_users: bool
    user_count: int


class SignupRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=4, max_length=128)
    llm_provider_name: str | None = Field(None, description="e.g. gemini, openai, anthropic")
    llm_api_key: str | None = Field(None, description="API key for the LLM provider")


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)


class AuthResponse(BaseModel):
    user_id: int
    email: str
    token: str
    message: str


class LogoutResponse(BaseModel):
    message: str


class ResetDbRequest(BaseModel):
    confirm: bool = Field(..., description="Must be true to proceed")


class ResetDbResponse(BaseModel):
    message: str
    status: str


# ── JWT helpers ───────────────────────────────────────────────────────────────

ALGORITHM = "HS256"


def _create_jwt(user_id: int, settings: Settings) -> str:
    """Create a signed JWT for the given user_id."""
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expiry_hours)
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


# ── Password hashing ──────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/status", response_model=AuthStatusResponse, summary="Check auth status")
def auth_status(session: Session = Depends(get_db)):
    """Returns whether any users exist in the database."""
    count = session.scalar(select(func.count()).select_from(User)) or 0
    return AuthStatusResponse(has_users=count > 0, user_count=count)


@router.post("/signup", response_model=AuthResponse, status_code=201, summary="Create a new user")
def signup(
    request: SignupRequest,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Create a new user account with email + password, then seed that user's default CoA."""
    existing = session.scalar(select(User).where(User.email == request.email))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "DUPLICATE_USER", "message": f"User '{request.email}' already exists."},
        )

    user = User(
        email=request.email,
        hashed_password=hash_password(request.password),
        is_active=True,
    )
    session.add(user)
    session.flush()  # get user.id before seeding

    # Seed per-user default CoA
    _seed_user_coa(session, user.id)

    # Optionally register LLM provider
    if request.llm_provider_name and request.llm_api_key:
        _register_llm_provider(session, str(user.id), request.llm_provider_name, request.llm_api_key)

    token = _create_jwt(user.id, settings)
    logger.info("User signed up: %s (id=%d)", request.email, user.id)

    return AuthResponse(
        user_id=user.id,
        email=user.email,
        token=token,
        message="Account created successfully.",
    )


@router.post("/login", response_model=AuthResponse, summary="Login with email + password")
def login(
    request: LoginRequest,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Authenticate with email and password; return a signed JWT."""
    user = session.scalar(select(User).where(User.email == request.email))
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "INVALID_CREDENTIALS", "message": "Invalid email or password."},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "ACCOUNT_DISABLED", "message": "This account is disabled."},
        )

    token = _create_jwt(user.id, settings)
    logger.info("User logged in: %s (id=%d)", user.email, user.id)

    return AuthResponse(
        user_id=user.id,
        email=user.email,
        token=token,
        message="Login successful.",
    )


@router.post("/logout", response_model=LogoutResponse, summary="Logout (client-side token discard)")
def logout():
    """Signals a logout. The client should discard its stored JWT.
    JWTs are stateless; the token remains technically valid until expiry
    but the client will no longer send it.
    """
    return LogoutResponse(message="Logged out successfully. Please discard your token.")


@router.post("/reset-db", response_model=ResetDbResponse, summary="Reset database (DEV ONLY)")
def reset_db(request: ResetDbRequest, settings: Settings = Depends(get_settings)):
    """Delete the SQLite database file and reinitialize it.

    DESTRUCTIVE — only available when APP_ENV=development.
    """
    if not settings.is_development():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "FORBIDDEN", "message": "Database reset is only available in development mode."},
        )
    if not request.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "CONFIRMATION_REQUIRED", "message": "Set confirm=true to proceed."},
        )

    db_url = settings.database_url
    if not db_url.startswith("sqlite:///"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "UNSUPPORTED", "message": "Database reset only supported for SQLite."},
        )

    db_path = Path(db_url.replace("sqlite:///", ""))

    from db.engine import engine
    engine.dispose()

    if db_path.exists():
        os.remove(db_path)
        logger.info("Deleted database file: %s", db_path)

    from db.engine import init_db
    init_db()

    return ResetDbResponse(message="Database has been reset and reinitialized.", status="ok")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _seed_user_coa(session: Session, user_id: int) -> None:
    """Seed the default Chart of Accounts for a newly-created user."""
    try:
        from repositories.sqla_account_repo import AccountRepository
        from onboarding.coa.service import COASetupService
        COASetupService(AccountRepository(session)).create_default_coa(user_id=user_id)
        logger.info("Seeded default CoA for user_id=%d", user_id)
    except Exception as exc:
        # Non-fatal: user can set up CoA manually
        logger.warning("Failed to seed CoA for user_id=%d: %s", user_id, exc)


def _register_llm_provider(session: Session, user_id: str, provider_name: str, api_key: str) -> None:
    """Register an LLM provider during signup (best-effort)."""
    try:
        import uuid
        from db.models.system import LlmProvider
        row = LlmProvider(
            provider_id=str(uuid.uuid4()),
            user_id=user_id,
            provider_name=provider_name.lower(),
            api_key=api_key,
            display_name=provider_name.title(),
            is_default=True,
        )
        session.add(row)
        session.flush()
        logger.info("Registered LLM provider '%s' for user_id=%s during signup", provider_name, user_id)
    except Exception as exc:
        logger.warning("Failed to register LLM provider during signup: %s", exc)
