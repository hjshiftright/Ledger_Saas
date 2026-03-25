"""
Shared fixtures for all onboarding API-level tests.

Provides a TestClient with fresh in-memory SQLite state per test, plus
pre-seeded variants for modules that depend on profile/COA/institutions.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db.models.base import Base
from db.engine import get_session
from api.deps import get_db
from main import app

# Import all models to ensure they are registered with Base.metadata
from db.models import (  # noqa: F401
    accounts, budgets, categories, goals, imports,
    recurring, reporting, securities, system, tax,
    transactions, users,
)

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionFactory = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)


def override_get_session():
    """FastAPI Dependency override: use in-memory SQLite per test."""
    session = TestSessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# Apply the dependency override for both possible entry points
app.dependency_overrides[get_session] = override_get_session
app.dependency_overrides[get_db] = override_get_session


@pytest.fixture(autouse=True)
def setup_database():
    """Create all tables before each test and drop them after."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    """FastAPI TestClient with fresh in-memory database per test."""
    return TestClient(app)


@pytest.fixture
def raw_session():
    """Direct DB session for inserting test fixture data into the same in-memory engine.

    Use this to pre-populate tables (transactions, accounts, etc.) without going
    through the HTTP API.  The session shares the same StaticPool engine as the
    TestClient, so data is immediately visible to API calls within the same test.
    """
    s = TestSessionFactory()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


@pytest.fixture
def seeded_client(client):
    """TestClient with profile + COA already initialised.

    Many modules (accounts, opening balances, net worth) require these
    to exist before they can function.
    """
    # 1) Create profile
    client.post("/api/v1/onboarding/profiles", json={
        "display_name": "Test User",
        "base_currency": "INR",
        "financial_year_start_month": 4,
        "tax_regime": "NEW",
        "date_format": "DD/MM/YYYY",
        "number_format": "INDIAN",
    })

    # 2) Initialise COA
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

