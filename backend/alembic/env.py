# backend/alembic/env.py
import asyncio
import sys
from pathlib import Path

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import pool

# Put backend/src on the path so all app modules are importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import get_settings

# Import every model module so Base.metadata is fully populated before
# Alembic compares it against the live database schema.
from db.models import (  # noqa: F401
    users, tenants, accounts, transactions,
    goals, budgets, imports, recurring,
    reporting, categories, system, tax, securities,
)
from db.models.base import Base

settings = get_settings()
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit SQL to stdout without connecting to the database.
    Useful for reviewing what will be applied before running it.
    """
    context.configure(
        url=settings.admin_database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Apply migrations against a live database via the async engine."""
    engine = create_async_engine(
        settings.admin_database_url,
        poolclass=pool.NullPool,  # migrations should not pool connections
    )
    async with engine.begin() as conn:
        await conn.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
