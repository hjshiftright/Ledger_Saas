from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
from config import get_settings

settings = get_settings()

# ── Primary engine (app_service role — routes through PgBouncer) ──────────────
# DATABASE_URL points to PgBouncer (:6432), which multiplexes connections to PostgreSQL.
#
# Key PgBouncer-compatibility settings:
#   statement_cache_size=0  — asyncpg caches prepared statements per-connection by default.
#                             PgBouncer (transaction mode) reassigns server connections between
#                             transactions, so a cached statement from connection A may be sent
#                             to connection B → protocol error. Disabling the cache prevents this.
#   ssl=False               — app and PgBouncer share a private Docker bridge network.
#                             SSL on this segment adds TLS handshake overhead with no security
#                             benefit (traffic never leaves the host). PgBouncer handles its own
#                             SSL to PostgreSQL independently via server_tls_sslmode in pgbouncer.ini.
#
# NOTE: do not add custom server_settings (e.g. jit=off) here — PgBouncer rejects any
#       startup parameter not in its ignore_startup_parameters whitelist with a
#       ProtocolViolationError before the connection even reaches PostgreSQL.
#
# Pool sizing rationale:
#   PgBouncer caps real PostgreSQL connections at default_pool_size=10 regardless of how many
#   client-side connections the app opens. Reducing pool_size/max_overflow here lowers the
#   number of persistent TCP sockets between the app and PgBouncer (75% reduction vs. before).
engine = create_async_engine(
    settings.database_url,
    pool_size=5,             # reduced: PgBouncer multiplexes these into 10 server connections
    max_overflow=10,         # reduced: burst headroom is now handled by PgBouncer's reserve pool
    pool_pre_ping=True,      # validate client→pgbouncer connections before reuse
    pool_recycle=7200,       # relaxed: PgBouncer manages server-side recycling via server_lifetime
    connect_args={
        "statement_cache_size": 0,           # REQUIRED for PgBouncer transaction mode
        "prepared_statement_cache_size": 0,  # asyncpg >=0.29 alias
        "ssl": False,                        # no SSL on private Docker network (app → pgbouncer)
        "server_settings": {
            "application_name": "ledger_api",
        },
    },
)

SessionFactory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# ── Admin engine (superadmin role — bypasses PgBouncer, direct to PostgreSQL) ─
# ADMIN_DATABASE_URL points directly to PostgreSQL (:5432).
#
# Why bypass PgBouncer:
#   - DDL statements (CREATE TABLE, ALTER, REINDEX) need a stable session connection.
#   - Alembic migrations use NullPool + admin_database_url; they must never go through PgBouncer.
#   - Superadmin operations (provisioning, billing, schema introspection) are low-frequency
#     and do not benefit from connection multiplexing.
#
# NEVER expose AdminSessionFactory through tenant-facing API endpoints.
admin_engine = create_async_engine(
    settings.admin_database_url,
    pool_size=3,
    max_overflow=5,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={
        "server_settings": {
            "application_name": "ledger_admin",
        },
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
    transaction-mode pooling (resets automatically on COMMIT/ROLLBACK, no tenant
    context leaks to the next client that reuses the server connection).
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


async def get_session_with_rls_and_context(
    tenant_id: str,
    user_id: str = "0",
) -> AsyncSession:
    """FastAPI generator: session + RLS + TransactionContext in ContextVar.

    Replaces get_session_with_context() for routes that use the propagation
    system.  Services can call get_active_transaction() instead of receiving
    the session as a constructor argument.

    SET LOCAL ensures RLS vars are transaction-scoped (PgBouncer safe).
    """
    from db.transaction import TransactionContext, _active_tx  # noqa: PLC0415

    async with SessionFactory() as session:
        await session.execute(
            text(
                "SELECT set_config('app.tenant_id', :tid, TRUE),"
                "       set_config('app.user_id',   :uid, TRUE)"
            ),
            {"tid": str(tenant_id), "uid": str(user_id)},
        )
        ctx = TransactionContext(
            session=session,
            tenant_id=tenant_id,
            user_id=user_id,
            is_root=True,
        )
        token = _active_tx.set(ctx)
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            _active_tx.reset(token)


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
