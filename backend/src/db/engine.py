from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import get_settings

_settings = get_settings()

engine = create_engine(
    _settings.database_url,
    pool_pre_ping=True
)
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
