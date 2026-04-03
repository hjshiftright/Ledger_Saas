"""Backward-compatible unit_of_work context manager.

Existing callers that pass ``existing_session`` explicitly continue to work
unchanged.  New callers that pass nothing get REQUIRED propagation semantics
via the ContextVar-based transactional() system.

Prefer transactional() directly for new code.
"""
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession

from db.transaction import Propagation, get_active_transaction, transactional


@asynccontextmanager
async def unit_of_work(existing_session: AsyncSession | None = None):
    """Open or join a database transaction.

    Args:
        existing_session: If provided, yield it directly (legacy call-site
                          compatibility — the caller owns commit/rollback).
                          If None, use the ambient ContextVar session
                          (REQUIRED propagation: join if exists, create if not).

    Yields:
        AsyncSession | None
    """
    if existing_session is not None:
        # Legacy path: explicit session passed in — do not touch commit/rollback.
        yield existing_session
        return

    # New path: defer to the propagation system.
    async with transactional(Propagation.REQUIRED) as ctx:
        if ctx is not None:
            yield ctx.session
        else:
            yield None
