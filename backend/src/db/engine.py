from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
from config import get_settings

settings = get_settings()

# ── Primary engine (app_service role — RLS enforced) ──────────────────────────
# Used by all normal API requests. RLS isolates data per tenant.
engine = create_async_engine(
    settings.database_url,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={
        "server_settings": {
            "application_name": "ledger_api",
            "jit": "off",
        }
    },
)

SessionFactory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# ── Admin engine (superadmin role — bypasses RLS) ─────────────────────────────
# Used ONLY by admin API routes (auth, provisioning, billing support).
# NEVER expose this session through tenant-facing endpoints.
admin_engine = create_async_engine(
    settings.admin_database_url,
    pool_size=3,
    max_overflow=5,
    pool_pre_ping=True,
    connect_args={
        "server_settings": {
            "application_name": "ledger_admin",
        }
    },
)

AdminSessionFactory = async_sessionmaker(
    admin_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncSession:
    """Provides a raw async session without tenant context (for global tables)."""
    async with SessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_session_with_context(tenant_id: str, user_id: str = "0") -> AsyncSession:
    """FastAPI dependency: sets both app.tenant_id and app.user_id for RLS enforcement.

    Uses is_local=TRUE so the settings are transaction-scoped — safe with PgBouncer
    transaction-mode pooling (resets automatically on COMMIT/ROLLBACK).
    """
    async with SessionFactory() as session:
        await session.execute(
            text(
                "SELECT set_config('app.tenant_id', :tid, TRUE),"
                "       set_config('app.user_id',   :uid, TRUE)"
            ),
            {"tid": str(tenant_id), "uid": str(user_id)},
        )
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_admin_session() -> AsyncSession:
    """FastAPI dependency for admin routes — uses superadmin role, bypasses RLS.

    Only inject this into routes protected by require_admin_role().
    """
    async with AdminSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Create all tables that do not yet exist. Safe to call on every startup.

    Uses the admin engine (superadmin role) so it has DDL privileges.
    All model modules must be imported before calling this so that
    Base.metadata is fully populated — db.models.__init__ handles that.
    """
    import db.models  # noqa: F401 — registers all ORM classes on Base.metadata
    from db.models.base import Base

    async with admin_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
