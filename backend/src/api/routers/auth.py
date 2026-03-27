"""Authentication endpoints — signup, login, tenant selection, logout.

Multi-tenant auth flow (M:N user ↔ tenant):

  1. POST /auth/signup       — Create user + first tenant + OWNER membership.
                               Returns user info and list of accessible tenants.
  2. POST /auth/login        — Authenticate with email + password.
                               Returns user info and list of accessible tenants.
  3. POST /auth/select-tenant — Pick which tenant to work in.
                               Returns a scoped JWT containing tenant_id and role.
  4. POST /auth/logout        — Client discards its token (stateless).

The scoped JWT from step 3 must be sent as:
  Authorization: Bearer <token>
on every subsequent request. FastAPI will decode it, set app.tenant_id and
app.user_id in the database session, and RLS will enforce isolation.

Endpoints:
    GET  /api/v1/auth/status          — Check if any users exist
    POST /api/v1/auth/signup          — Create a new user account + first tenant
    POST /api/v1/auth/login           — Authenticate; receive tenant list
    POST /api/v1/auth/select-tenant   — Choose active tenant; receive scoped JWT
    POST /api/v1/auth/logout          — Acknowledge logout (client discards token)
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config import Settings, get_settings
from db.models.tenants import Tenant, TenantMembership
from db.models.users import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])

ALGORITHM = "HS256"


# ── Request / Response schemas ────────────────────────────────────────────────

class AuthStatusResponse(BaseModel):
    has_users: bool
    user_count: int


class SignupRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=4, max_length=128)
    full_name: str | None = Field(None, max_length=255)
    tenant_name: str | None = Field(None, description="Display name for the first tenant (defaults to email)")
    entity_type: str = Field("PERSONAL", description="PERSONAL | SOLE_PROPRIETOR | PARTNERSHIP | PRIVATE_LIMITED | LLP | TRUST | HUF | OTHER")
    llm_provider_name: str | None = Field(None, description="e.g. gemini, openai, anthropic")
    llm_api_key: str | None = Field(None, description="API key for the LLM provider")


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)


class TenantInfo(BaseModel):
    tenant_id: str
    name: str
    entity_type: str
    role: str


class AuthListResponse(BaseModel):
    """Returned after signup or login — client shows a tenant picker if len(tenants) > 1."""
    user_id: int
    email: str
    tenants: list[TenantInfo]
    message: str


class SelectTenantRequest(BaseModel):
    tenant_id: str = Field(..., description="UUID of the tenant to activate")


class TokenResponse(BaseModel):
    """Scoped JWT carrying user_id, tenant_id, and role."""
    access_token: str
    token_type: str = "bearer"
    user_id: int
    tenant_id: str
    role: str


class LogoutResponse(BaseModel):
    message: str


# ── JWT helpers ───────────────────────────────────────────────────────────────

def _create_scoped_jwt(
    user_id: int,
    email: str,
    tenant_id: str,
    role: str,
    settings: Settings,
) -> str:
    """Create a tenant-scoped JWT containing user identity, active tenant, and role."""
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expiry_hours)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "tenant_id": tenant_id,
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


# ── Password helpers ──────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ── Admin session dependency ──────────────────────────────────────────────────

async def _admin_session() -> AsyncSession:
    """Auth endpoints need the admin (superadmin) session to read/write global tables."""
    from db.engine import get_admin_session
    async for session in get_admin_session():
        yield session


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/status", response_model=AuthStatusResponse, summary="Check auth status")
async def auth_status(session: AsyncSession = Depends(_admin_session)):
    """Returns whether any users exist in the database."""
    count = await session.scalar(select(func.count()).select_from(User)) or 0
    return AuthStatusResponse(has_users=count > 0, user_count=count)


@router.post("/signup", response_model=AuthListResponse, status_code=201, summary="Create a new user + first tenant")
async def signup(
    request: SignupRequest,
    session: AsyncSession = Depends(_admin_session),
    settings: Settings = Depends(get_settings),
):
    """Create a new user account, a first tenant, and an OWNER membership atomically.

    If the email already exists, returns 409 Conflict.
    The caller should then call POST /auth/select-tenant to get a scoped JWT.
    """
    existing = await session.scalar(select(User).where(User.email == request.email))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "DUPLICATE_USER", "message": f"User '{request.email}' already exists."},
        )

    # 1. Create the global user record
    user = User(
        email=request.email,
        hashed_password=hash_password(request.password),
        full_name=request.full_name,
        is_active=True,
        is_email_verified=False,
    )
    session.add(user)
    await session.flush()  # obtain user.id

    # 2. Create the first tenant
    tenant_name = request.tenant_name or f"{request.email.split('@')[0]}'s Account"
    tenant = Tenant(
        name=tenant_name,
        entity_type=request.entity_type,
        created_by_user_id=user.id,
        status="ACTIVE",
        plan="FREE",
    )
    session.add(tenant)
    await session.flush()  # obtain tenant.id

    # 3. Grant OWNER membership (auto-accepted — user created this tenant)
    membership = TenantMembership(
        tenant_id=tenant.id,
        user_id=user.id,
        role="OWNER",
        is_active=True,
        accepted_at=datetime.now(timezone.utc),
    )
    session.add(membership)
    await session.flush()

    # 4. Seed default Chart of Accounts for the new tenant
    _seed_tenant_coa(session, user.id, tenant.id)

    # 5. Optionally register LLM provider
    if request.llm_provider_name and request.llm_api_key:
        _register_llm_provider(session, str(user.id), request.llm_provider_name, request.llm_api_key)

    logger.info("User signed up: %s (id=%d) → tenant %s", request.email, user.id, tenant.id)

    return AuthListResponse(
        user_id=user.id,
        email=user.email,
        tenants=[TenantInfo(
            tenant_id=str(tenant.id),
            name=tenant.name,
            entity_type=tenant.entity_type,
            role="OWNER",
        )],
        message="Account created successfully. Call /auth/select-tenant to receive your access token.",
    )


@router.post("/login", response_model=AuthListResponse, summary="Authenticate and list accessible tenants")
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(_admin_session),
):
    """Authenticate with email and password.

    Returns the list of tenants the user can access. The client should display
    a tenant picker if there is more than one, then call POST /auth/select-tenant.
    """
    user = await session.scalar(select(User).where(User.email == request.email))
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

    # Fetch all active memberships with their tenant details
    result = await session.execute(
        select(TenantMembership)
        .options(selectinload(TenantMembership.tenant))
        .where(TenantMembership.user_id == user.id)
        .where(TenantMembership.is_active == True)  # noqa: E712
    )
    memberships = result.scalars().all()

    tenants = [
        TenantInfo(
            tenant_id=str(m.tenant_id),
            name=m.tenant.name,
            entity_type=m.tenant.entity_type,
            role=m.role,
        )
        for m in memberships
        if m.tenant and m.tenant.status == "ACTIVE"
    ]

    # Update last_login_at
    user.last_login_at = datetime.now(timezone.utc)

    logger.info("User logged in: %s (id=%d), %d tenant(s)", user.email, user.id, len(tenants))

    return AuthListResponse(
        user_id=user.id,
        email=user.email,
        tenants=tenants,
        message="Login successful. Call /auth/select-tenant to receive your access token.",
    )


@router.post("/select-tenant", response_model=TokenResponse, summary="Select active tenant and receive scoped JWT")
async def select_tenant(
    body: SelectTenantRequest,
    authorization: str | None = None,
    session: AsyncSession = Depends(_admin_session),
    settings: Settings = Depends(get_settings),
):
    """Verify the user's membership in the requested tenant and issue a scoped JWT.

    The JWT embeds ``tenant_id`` and ``role``, which the API uses to set
    ``app.tenant_id`` on every subsequent request so PostgreSQL RLS can enforce isolation.

    To call this endpoint after login, pass the ``user_id`` in the request body or
    authenticate via a pre-scoped token in the Authorization header.
    """
    # Resolve who is calling: either from a prior token or via the Authorization header
    user_id_str: str | None = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        if token:
            try:
                payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
                user_id_str = payload.get("sub")
            except Exception:
                pass

    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "TOKEN_MISSING", "message": "Authorization header with Bearer token required."},
        )

    try:
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"error": "TOKEN_INVALID"})

    # Verify membership exists and is active
    result = await session.execute(
        select(TenantMembership)
        .options(selectinload(TenantMembership.tenant))
        .where(TenantMembership.user_id == user_id)
        .where(TenantMembership.tenant_id == body.tenant_id)
        .where(TenantMembership.is_active == True)  # noqa: E712
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "NO_TENANT_ACCESS", "message": "No active membership for this tenant."},
        )
    if membership.tenant and membership.tenant.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "TENANT_INACTIVE", "message": "This tenant account is not active."},
        )

    # Fetch the user's email for the JWT
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"error": "USER_NOT_FOUND"})

    # Update last_accessed_at on the membership
    membership.last_accessed_at = datetime.now(timezone.utc)

    token = _create_scoped_jwt(
        user_id=user.id,
        email=user.email,
        tenant_id=str(membership.tenant_id),
        role=membership.role,
        settings=settings,
    )

    logger.info(
        "Tenant selected: user_id=%d → tenant=%s (role=%s)",
        user.id, membership.tenant_id, membership.role,
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        tenant_id=str(membership.tenant_id),
        role=membership.role,
    )


@router.post("/logout", response_model=LogoutResponse, summary="Logout (client-side token discard)")
def logout():
    """Signals a logout. The client should discard its stored JWT.

    JWTs are stateless; the token remains technically valid until expiry,
    but the client will no longer send it.
    """
    return LogoutResponse(message="Logged out successfully. Please discard your token.")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _seed_tenant_coa(session: AsyncSession, user_id: int, tenant_id) -> None:
    """Seed the default Chart of Accounts for a newly-created tenant (best-effort)."""
    try:
        from repositories.sqla_account_repo import AccountRepository
        from onboarding.coa.service import COASetupService
        COASetupService(AccountRepository(session)).create_default_coa(user_id=user_id)
        logger.info("Seeded default CoA for tenant_id=%s", tenant_id)
    except Exception as exc:
        # Non-fatal: user can set up CoA manually via onboarding flow
        logger.warning("Failed to seed CoA for tenant_id=%s: %s", tenant_id, exc)


def _register_llm_provider(session: AsyncSession, user_id: str, provider_name: str, api_key: str) -> None:
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
        logger.info("Registered LLM provider '%s' for user_id=%s during signup", provider_name, user_id)
    except Exception as exc:
        logger.warning("Failed to register LLM provider during signup: %s", exc)
