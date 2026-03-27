"""Integration test conftest.

Overrides get_tenant_db and get_db with an aiosqlite in-memory session so
that integration tests don't require a live PostgreSQL instance.
"""
import uuid

import pytest
from sqlalchemy import event as sa_event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from api.deps import get_db, get_tenant_db
from db.models.base import Base
from db.models import (  # noqa: F401
    accounts, budgets, categories, goals, imports,
    recurring, reporting, securities, system, tax,
    transactions, users,
)
from main import app

TEST_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
_TEST_ENGINE = None
_SESSION_FACTORY = None


def _get_engine():
    global _TEST_ENGINE, _SESSION_FACTORY
    if _TEST_ENGINE is None:
        _TEST_ENGINE = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False,
        )
        _SESSION_FACTORY = async_sessionmaker(
            bind=_TEST_ENGINE,
            autoflush=True,
            expire_on_commit=False,
            class_=AsyncSession,
        )
    return _TEST_ENGINE, _SESSION_FACTORY


async def _create_tables():
    engine, _ = _get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _override_get_tenant_db():
    _, factory = _get_engine()
    async with factory() as sess:
        @sa_event.listens_for(sess.sync_session, "before_flush")
        def _auto_tenant(session, ctx, instances):
            for obj in session.new:
                if hasattr(obj, "tenant_id") and obj.tenant_id is None:
                    obj.tenant_id = TEST_TENANT_ID
        try:
            yield sess
            await sess.commit()
        except Exception:
            await sess.rollback()
            raise


async def _override_get_db():
    _, factory = _get_engine()
    async with factory() as sess:
        try:
            yield sess
            await sess.commit()
        except Exception:
            await sess.rollback()
            raise


@pytest.fixture(scope="session", autouse=True)
async def _setup_integration_db():
    """Create tables once for the entire integration test session."""
    await _create_tables()
    app.dependency_overrides[get_tenant_db] = _override_get_tenant_db
    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()
