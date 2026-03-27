"""Shared fixtures for unit tests — in-memory async SQLite backed SQLAlchemy session."""
import uuid
import pytest
import pytest_asyncio
from sqlalchemy import event as sa_event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from db.models.base import Base
from db.models import (  # noqa: F401 — registers all models with Base.metadata
    accounts, budgets, categories, goals, imports,
    recurring, reporting, securities, system, tax,
    transactions, users,
)

TEST_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionFactory = async_sessionmaker(
        bind=engine, autoflush=True, expire_on_commit=False, class_=AsyncSession
    )
    async with SessionFactory() as sess:
        # Auto-set tenant_id on any new tenant-scoped object (SQLite has no RLS/session var)
        @sa_event.listens_for(sess.sync_session, "before_flush")
        def _auto_tenant_id(session, flush_context, instances):
            for obj in session.new:
                if hasattr(obj, "tenant_id") and obj.tenant_id is None:
                    obj.tenant_id = TEST_TENANT_ID

        yield sess

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
