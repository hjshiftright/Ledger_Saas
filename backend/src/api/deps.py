"""FastAPI dependencies — auth, settings, DB session, and service injection."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from jose import ExpiredSignatureError, JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from config import Settings, get_settings

ALGORITHM = "HS256"


# ── Settings dependency ───────────────────────────────────────────────────────

SettingsDep = Annotated[Settings, Depends(get_settings)]


# ── JWT payload dataclass ─────────────────────────────────────────────────────

class UserTokenPayload:
    """Decoded JWT payload for a tenant-scoped request.

    Attributes:
        user_id:   Numeric user ID (from ``sub`` claim).
        tenant_id: Active tenant UUID string (from ``tenant_id`` claim).
        role:      Tenant-level role string, e.g. OWNER, ADMIN, MEMBER (from ``role`` claim).
    """

    __slots__ = ("user_id", "tenant_id", "role")

    def __init__(self, user_id: str, tenant_id: str, role: str) -> None:
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.role = role


# ── JWT auth helpers ──────────────────────────────────────────────────────────

# Default user/tenant injected automatically in development when no auth header is sent.
_DEV_USER_ID = "1"
_DEV_TENANT_ID = "00000000-0000-0000-0000-000000000001"
_DEV_ROLE = "OWNER"


def get_current_user_id(
    authorization: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> str:
    """Return the raw ``user_id`` string from a valid JWT.

    Kept for backwards-compatibility with routes that only need user_id.
    For tenant-aware routes use ``get_current_user_payload`` instead.
    """
    return _decode_token(authorization, settings).user_id


def get_current_user_payload(
    authorization: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> UserTokenPayload:
    """Decode and validate the JWT; return the full payload (user_id + tenant_id + role).

    In production verifies signature and expiry using SECRET_KEY.

    Dev-mode shortcut: when APP_ENV=development and no Authorization header is sent,
    returns a default payload so Swagger / curl testing works without headers.
    """
    return _decode_token(authorization, settings)


def _decode_token(
    authorization: str | None,
    settings: Settings,
) -> UserTokenPayload:
    if not authorization:
        if settings.is_development():
            return UserTokenPayload(_DEV_USER_ID, _DEV_TENANT_ID, _DEV_ROLE)
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
        tenant_id: str | None = payload.get("tenant_id")
        role: str | None = payload.get("role", "MEMBER")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "TOKEN_INVALID", "message": "Token payload missing subject."},
            )
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "TOKEN_NO_TENANT",
                    "message": "Token does not contain an active tenant. Call /auth/select-tenant first.",
                },
            )
        return UserTokenPayload(user_id, tenant_id, role)

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


# ── Role guard ────────────────────────────────────────────────────────────────

def require_role(*allowed_roles: str):
    """FastAPI dependency factory: raise 403 if the caller's role is not in allowed_roles.

    Usage::

        @router.delete("/transactions/{id}")
        async def delete_txn(
            _auth: Annotated[UserTokenPayload, require_role("OWNER", "ADMIN")],
            ...
        ):
    """
    def _guard(
        token_payload: UserTokenPayload = Depends(get_current_user_payload),
    ) -> UserTokenPayload:
        if token_payload.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "INSUFFICIENT_ROLE",
                    "message": f"This action requires one of: {', '.join(allowed_roles)}.",
                },
            )
        return token_payload

    return Depends(_guard)


# ── Tenant-scoped DB session dependency ──────────────────────────────────────

async def get_tenant_db(
    token_payload: UserTokenPayload = Depends(get_current_user_payload),
) -> AsyncSession:
    """Open an async session and set both app.tenant_id and app.user_id for RLS.

    Inject this into any route that reads/writes tenant-scoped tables.
    RLS policies on PostgreSQL enforce isolation automatically — no WHERE clauses needed.
    """
    from db.engine import get_session_with_context
    async for session in get_session_with_context(
        tenant_id=token_payload.tenant_id,
        user_id=token_payload.user_id,
    ):
        yield session


TenantDBSession = Annotated[AsyncSession, Depends(get_tenant_db)]

# ── Legacy / global DB session (no tenant context) ────────────────────────────

async def get_db() -> AsyncSession:
    """Yield an async session without tenant context (global tables: users, tenants, etc.)."""
    from db.engine import get_session
    async for session in get_session():
        yield session


DBSession = Annotated[AsyncSession, Depends(get_db)]

# Annotated shorthand for the common case of just needing the decoded payload
CurrentUser = Annotated[str, Depends(get_current_user_id)]
CurrentUserPayload = Annotated[UserTokenPayload, Depends(get_current_user_payload)]
