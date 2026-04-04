"""Transaction propagation for SQLAlchemy 2.0 async + PostgreSQL + PgBouncer.

Provides Spring-style @Transactional semantics adapted for Python async:
  - Propagation enum with 7 modes
  - TransactionContext dataclass (ambient session + RLS metadata)
  - _active_tx ContextVar (task-local ambient transaction state)
  - transactional() async context manager
  - transactional_method() decorator
  - get_active_transaction() accessor

PgBouncer safety:
  All RLS config is applied via SET LOCAL (transaction-scoped), never SET
  (session-scoped).  SET LOCAL vars are cleared automatically on COMMIT /
  ROLLBACK, preventing tenant-context leakage across pooled server connections.

ContextVar semantics:
  Python's ContextVar is task-local: coroutines in the same asyncio task share
  the same Context automatically.  asyncio.create_task() copies the current
  Context into the child task (snapshot).  Mutations in the child do NOT affect
  the parent — see TestContextVarTaskIsolation.
"""

from __future__ import annotations

import enum
import functools
from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


# ── Propagation modes ─────────────────────────────────────────────────────────

class Propagation(enum.Enum):
    REQUIRED      = "REQUIRED"
    REQUIRES_NEW  = "REQUIRES_NEW"
    NESTED        = "NESTED"
    SUPPORTS      = "SUPPORTS"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    MANDATORY     = "MANDATORY"
    NEVER         = "NEVER"


# ── Exceptions ────────────────────────────────────────────────────────────────

class TransactionRequired(RuntimeError):
    """Raised by MANDATORY propagation when no active transaction exists."""


class TransactionProhibited(RuntimeError):
    """Raised by NEVER propagation when an active transaction exists."""


# ── TransactionContext ────────────────────────────────────────────────────────

@dataclass
class TransactionContext:
    """Ambient transaction state for the current async task.

    Fields:
        session:   The active AsyncSession. All repositories use this.
        tenant_id: RLS app.tenant_id value (str UUID or None).
        user_id:   RLS app.user_id value (str int or None).
        is_root:   True when this context created the transaction (owns commit).
        savepoint: The AsyncSessionTransaction returned by begin_nested(),
                   set only when Propagation.NESTED created a savepoint.
    """
    session: AsyncSession
    tenant_id: str | None = None
    user_id: str | None = None
    is_root: bool = True
    savepoint: Any | None = field(default=None, compare=False)


# ── ContextVar ────────────────────────────────────────────────────────────────

_active_tx: ContextVar[TransactionContext | None] = ContextVar(
    "_active_tx", default=None
)


def get_active_transaction() -> TransactionContext | None:
    """Return the ambient TransactionContext for the current async task, or None."""
    return _active_tx.get()


# ── Internal helpers ──────────────────────────────────────────────────────────

@asynccontextmanager
async def _new_root_transaction(
    tenant_id: str | None,
    user_id: str | None,
):
    """Open a new AsyncSession, begin a transaction, push ContextVar.

    Issues SET LOCAL for RLS when tenant_id is provided.
    Commits on clean exit; rolls back on any exception.
    Restores the previous ContextVar value on exit (even on error).
    """
    # Use a module-level attribute access (not a local binding) so that
    # patch("db.engine.SessionFactory") works correctly in tests.
    import db.engine as _db_engine  # noqa: PLC0415

    session = _db_engine.SessionFactory()
    ctx = TransactionContext(
        session=session,
        tenant_id=tenant_id,
        user_id=user_id,
        is_root=True,
    )
    token = _active_tx.set(ctx)
    try:
        if tenant_id is not None:
            await session.execute(
                text(
                    "SELECT set_config('app.tenant_id', :tid, TRUE),"
                    "       set_config('app.user_id',   :uid, TRUE)"
                ),
                {"tid": str(tenant_id), "uid": str(user_id or "0")},
            )
        yield ctx
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        try:
            _active_tx.reset(token)
        except ValueError:
            pass  # Teardown ran in a copied Context (e.g. FastAPI GC) — safe to ignore.
        await session.close()


@asynccontextmanager
async def _nested_savepoint(parent: TransactionContext):
    """Create a SAVEPOINT inside the parent transaction.

    Uses AsyncSession.begin_nested() which emits:
      SAVEPOINT <name>
    on enter, and either:
      RELEASE SAVEPOINT <name>   (success)
      ROLLBACK TO SAVEPOINT <name>  (exception)
    on exit.

    Safe with PgBouncer because savepoints live within a single transaction,
    which maps to a single server connection.
    """
    sp = await parent.session.begin_nested()
    ctx = TransactionContext(
        session=parent.session,
        tenant_id=parent.tenant_id,
        user_id=parent.user_id,
        is_root=False,
        savepoint=sp,
    )
    token = _active_tx.set(ctx)
    try:
        yield ctx
        await sp.commit()    # RELEASE SAVEPOINT
    except Exception:
        await sp.rollback()  # ROLLBACK TO SAVEPOINT
        raise
    finally:
        try:
            _active_tx.reset(token)
        except ValueError:
            pass  # Teardown ran in a copied Context — safe to ignore.


# ── Main context manager ──────────────────────────────────────────────────────

@asynccontextmanager
async def transactional(
    propagation: Propagation = Propagation.REQUIRED,
    *,
    tenant_id: str | None = None,
    user_id: str | None = None,
):
    """Async context manager implementing transaction propagation semantics.

    Usage — context manager::

        async with transactional(Propagation.REQUIRES_NEW):
            ctx = get_active_transaction()
            ctx.session.add(my_entity)

    Usage — see also transactional_method() for the decorator form.

    Args:
        propagation: One of the Propagation enum values (default: REQUIRED).
        tenant_id:   RLS tenant_id override (rarely needed; inherited by default).
        user_id:     RLS user_id override (rarely needed; inherited by default).

    Yields:
        TransactionContext | None  (None for SUPPORTS/NOT_SUPPORTED/NEVER when
        no session is managed by this call).

    Raises:
        TransactionRequired:   MANDATORY called without an active transaction.
        TransactionProhibited: NEVER called inside an active transaction.
    """
    current = _active_tx.get()

    match propagation:

        case Propagation.REQUIRED:
            if current is not None:
                # Join the existing transaction — caller does NOT own commit.
                yield current
            else:
                # No ambient tx → create a new root transaction.
                async with _new_root_transaction(tenant_id, user_id) as ctx:
                    yield ctx

        case Propagation.REQUIRES_NEW:
            # Always open an independent session, regardless of any ambient tx.
            # Inherit tenant/user from ambient context unless overridden.
            tid = tenant_id or (current.tenant_id if current else None)
            uid = user_id or (current.user_id if current else None)
            async with _new_root_transaction(tid, uid) as ctx:
                # Replace ContextVar so inner code sees the new session.
                token = _active_tx.set(ctx)
                try:
                    yield ctx
                finally:
                    # Restore outer context (may be None).
                    try:
                        _active_tx.reset(token)
                    except ValueError:
                        pass  # Teardown ran in a copied Context — safe to ignore.

        case Propagation.NESTED:
            if current is None:
                # No outer tx → fall back to REQUIRED (create root).
                async with _new_root_transaction(tenant_id, user_id) as ctx:
                    yield ctx
            else:
                # Outer tx exists → create a SAVEPOINT.
                async with _nested_savepoint(current) as ctx:
                    yield ctx

        case Propagation.SUPPORTS:
            if current is not None:
                yield current   # Join existing.
            else:
                yield None      # Run without transaction.

        case Propagation.NOT_SUPPORTED:
            # Suspend ambient transaction at the Python level.
            # The outer session remains open at the DB level (PostgreSQL has no
            # "suspend" primitive), but inner code cannot access it via ContextVar.
            token = _active_tx.set(None)
            try:
                yield None
            finally:
                try:
                    _active_tx.reset(token)
                except ValueError:
                    pass  # Teardown ran in a copied Context — safe to ignore.

        case Propagation.MANDATORY:
            if current is None:
                raise TransactionRequired(
                    "MANDATORY propagation requires an active transaction, but none exists."
                )
            yield current

        case Propagation.NEVER:
            if current is not None:
                raise TransactionProhibited(
                    "NEVER propagation forbids calling within an active transaction."
                )
            yield None


# ── Decorator form ────────────────────────────────────────────────────────────

def transactional_method(
    propagation: Propagation = Propagation.REQUIRED,
    **kwargs,
):
    """Decorator that wraps an async method with a transactional() context.

    Preserves the original function's __name__, __doc__, and signature
    via functools.wraps.

    Usage::

        class MyService:
            @transactional_method(Propagation.NESTED)
            async def do_work(self):
                ctx = get_active_transaction()
                ctx.session.add(some_entity)

        class AuditService:
            @transactional_method(Propagation.REQUIRES_NEW)
            async def log(self, event: str):
                ctx = get_active_transaction()
                ctx.session.add(AuditLog(event=event))
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kw):
            async with transactional(propagation, **kwargs):
                return await func(*args, **kw)
        return wrapper
    return decorator
