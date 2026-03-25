"""Shared fixtures for unit tests — in-memory SQLite backed SQLAlchemy session."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from db.models.base import Base
from db.models import (  # noqa: F401 — registers all models with Base.metadata
    accounts, budgets, categories, goals, imports,
    recurring, reporting, securities, system, tax,
    transactions, users,
)


@pytest.fixture
def session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionFactory = sessionmaker(bind=engine, autoflush=True, expire_on_commit=False)
    sess = SessionFactory()
    yield sess
    sess.close()
    Base.metadata.drop_all(bind=engine)
