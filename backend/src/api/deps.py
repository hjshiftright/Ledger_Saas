"""FastAPI dependencies — auth, settings, DB session, and service injection."""

from __future__ import annotations

from typing import Annotated, Generator

from fastapi import Depends, Header, HTTPException, status
from jose import ExpiredSignatureError, JWTError, jwt
from sqlalchemy.orm import Session

from config import Settings, get_settings

ALGORITHM = "HS256"


# ── Settings dependency ───────────────────────────────────────────────────────

SettingsDep = Annotated[Settings, Depends(get_settings)]


# ── Database session dependency ───────────────────────────────────────────────

def get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session for one request (Unit of Work pattern)."""
    from db.engine import get_session
    yield from get_session()


DBSession = Annotated[Session, Depends(get_db)]


# ── Service dependencies (for the transaction-management routes) ──────────────

def get_account_service(session: Session = Depends(get_db)):
    from services.account_service import AccountService
    return AccountService(session)


def get_transaction_service(session: Session = Depends(get_db)):
    from services.transaction_service import TransactionService
    return TransactionService(session)


# ── JWT auth ──────────────────────────────────────────────────────────────────

# Default user_id injected automatically when the Authorization header is absent
# and APP_ENV=development.  Never active in staging or production.
DEV_DEFAULT_USER_ID = "1"


def get_current_user_id(
    authorization: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> str:
    """Decode and validate the JWT Bearer token; return the user_id string.

    In production this verifies the JWT signature and expiry using SECRET_KEY.

    Dev-mode shortcut: when APP_ENV=development and no Authorization header
    is sent, the request is accepted and user_id defaults to '1' (first user).
    This makes Swagger UI / curl testing easy without headers.
    """
    if not authorization:
        if settings.is_development():
            return DEV_DEFAULT_USER_ID
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "TOKEN_MISSING", "message": "Authorization header required."},
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "TOKEN_INVALID", "message": "Token must use Bearer scheme."},
        )

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "TOKEN_MISSING", "message": "Bearer token is empty."},
        )

    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        user_id: str | None = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "TOKEN_INVALID", "message": "Token payload missing subject."},
            )
        return user_id
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "TOKEN_EXPIRED", "message": "Token has expired. Please log in again."},
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "TOKEN_INVALID", "message": "Could not validate credentials."},
        )


CurrentUser = Annotated[str, Depends(get_current_user_id)]
