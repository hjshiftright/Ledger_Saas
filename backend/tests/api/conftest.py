"""
Shared fixtures for all onboarding API-level tests.

Provides a TestClient with fresh in-memory aiosqlite state per test,
plus pre-seeded variants for modules that depend on profile/COA/institutions.
All fixtures are async (asyncio_mode = auto handles the bridge to sync tests).
"""
import uuid
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event as sa_event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from api.deps import get_db, get_tenant_db
from db.models.base import Base

# Mock the admin_engine BEFORE importing main to prevent PostgreSQL connection
# during module initialization. We'll provide a proper override in the client fixture.
import db.engine as engine_module
_test_engine_mock = MagicMock()
engine_module.admin_engine = _test_engine_mock
engine_module.AdminSessionFactory = MagicMock()

from main import app

# Import all models to ensure they are registered with Base.metadata
from db.models import (  # noqa: F401
    accounts, budgets, categories, goals, imports,
    recurring, reporting, securities, system, tax,
    transactions, users,
)
from db.models.users import User

TEST_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
# Matches the hardcoded _DEV_USER_ID in api/deps.py
_DEV_USER_ID = 1


@pytest.fixture
async def _engine():
    """Shared in-memory SQLite engine for a single test."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    async with engine.begin() as conn:
        # Enable FK enforcement so tests catch constraint violations the same
        # way PostgreSQL would.
        await conn.execute(text("PRAGMA foreign_keys = ON"))
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def _dev_user(_engine):
    """Insert the dev user (id=1) required by the dev-mode auth fallback.

    The dev fallback in api/deps.py always resolves to user_id=1.  Without a
    matching row in the ``users`` table any insert that references users.id via
    a FK (profiles, etc.) would fail under strict FK enforcement.
    """
    SessionFactory = async_sessionmaker(
        bind=_engine,
        autoflush=True,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    async with SessionFactory() as sess:
        user = User(
            email="dev@ledger.local",
            hashed_password="dev-hash",
            is_active=True,
        )
        sess.add(user)
        await sess.commit()
        await sess.refresh(user)
        return user


@pytest.fixture
async def client(_engine, _dev_user):
    """FastAPI TestClient backed by fresh in-memory aiosqlite per test."""
    SessionFactory = async_sessionmaker(
        bind=_engine,
        autoflush=True,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    async def override_get_tenant_db():
        async with SessionFactory() as sess:
            @sa_event.listens_for(sess.sync_session, "before_flush")
            def _auto_tenant(session, ctx, instances):
                for obj in session.new:
                    if hasattr(obj, "tenant_id"):
                        if obj.tenant_id is None:
                            obj.tenant_id = TEST_TENANT_ID
                        elif isinstance(obj.tenant_id, str):
                            obj.tenant_id = uuid.UUID(obj.tenant_id)
            try:
                yield sess
                await sess.commit()
            except Exception:
                await sess.rollback()
                raise

    async def override_get_db():
        async with SessionFactory() as sess:
            try:
                yield sess
                await sess.commit()
            except Exception:
                await sess.rollback()
                raise

    async def override_admin_session():
        """Override admin session to use the test SQLite session instead of PostgreSQL."""
        async with SessionFactory() as sess:
            # Auto-set tenant_id for inserted objects
            @sa_event.listens_for(sess.sync_session, "before_flush")
            def _auto_tenant(session, ctx, instances):
                for obj in session.new:
                    if hasattr(obj, "tenant_id"):
                        if obj.tenant_id is None:
                            obj.tenant_id = TEST_TENANT_ID
                        elif isinstance(obj.tenant_id, str):
                            obj.tenant_id = uuid.UUID(obj.tenant_id)
            try:
                yield sess
                await sess.commit()
            except Exception:
                await sess.rollback()
                raise

    from api.routers.auth import _admin_session

    app.dependency_overrides[get_tenant_db] = override_get_tenant_db
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[_admin_session] = override_admin_session

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
async def raw_session(_engine):
    """Direct async DB session for inserting test fixture data.

    Shares the same StaticPool engine as the TestClient, so data is
    immediately visible to API calls within the same test.
    """
    SessionFactory = async_sessionmaker(
        bind=_engine,
        autoflush=True,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    async with SessionFactory() as sess:
        # Auto-set tenant_id for inserted objects
        @sa_event.listens_for(sess.sync_session, "before_flush")
        def _auto_tenant(session, ctx, instances):
            for obj in session.new:
                if hasattr(obj, "tenant_id") and obj.tenant_id is None:
                    obj.tenant_id = TEST_TENANT_ID
        yield sess


@pytest.fixture
async def seeded_client(client):
    """TestClient with profile + COA already initialised."""
    client.post("/api/v1/onboarding/profiles", json={
        "display_name": "Test User",
        "base_currency": "INR",
        "financial_year_start_month": 4,
        "tax_regime": "NEW",
        "date_format": "DD/MM/YYYY",
        "number_format": "INDIAN",
    })
    client.post("/api/v1/onboarding/coa/initialize")
    return client


# ── Helper factories ────────────────────────────────────────────────────


def create_institution(client, name="Test Bank", institution_type="BANK", **kw):
    """Shorthand to POST an institution and return the JSON response."""
    payload = {"name": name, "institution_type": institution_type, **kw}
    resp = client.post("/api/v1/onboarding/institutions", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def create_bank_account(client, institution_id, display_name="HDFC Savings"):
    """Shorthand to POST a bank account and return the JSON response."""
    payload = {
        "display_name": display_name,
        "institution_id": institution_id,
        "account_number_masked": "X1234",
        "bank_account_type": "SAVINGS",
    }
    resp = client.post("/api/v1/onboarding/accounts/bank", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()
