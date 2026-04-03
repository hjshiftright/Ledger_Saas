from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from db.engine import SessionFactory

@asynccontextmanager
async def unit_of_work(existing_session: AsyncSession | None = None):
    if existing_session is not None:
        yield existing_session
        return

    session = SessionFactory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
