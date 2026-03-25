from contextlib import contextmanager
from sqlalchemy.orm import Session
from db.engine import SessionFactory

@contextmanager
def unit_of_work(existing_session: Session | None = None):
    if existing_session is not None:
        yield existing_session
        return

    session = SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
