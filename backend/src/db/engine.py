from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import get_settings

_settings = get_settings()

_is_postgres = _settings.database_url.startswith("postgresql")

# PostgreSQL gets a proper connection pool; SQLite gets check_same_thread=False
# so it works safely with FastAPI's multi-threaded request handling.
_engine_kwargs: dict = {"pool_pre_ping": True}
if _is_postgres:
    _engine_kwargs.update({
        "pool_size": 5,
        "max_overflow": 10,
        "pool_timeout": 30,
        "pool_recycle": 1800,
    })
else:
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(_settings.database_url, **_engine_kwargs)
SessionFactory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session():
    """FastAPI Dependency enforcing Unit of Work pattern (1 transaction / request)."""
    session = SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(bind_engine=None) -> None:
    """Create all database tables. Safe to call multiple times (uses CREATE IF NOT EXISTS)."""
    # Import all model modules so their classes are registered with Base.metadata
    from db.models import (  # noqa: F401
        accounts, budgets, categories, goals, imports,
        recurring, reporting, securities, system, tax,
        transactions, users,
    )
    from db.models.base import Base
    Base.metadata.create_all(bind=bind_engine or engine)
