"""
repositories
============
Single authoritative package for all repository implementations.

SQLAlchemy-backed repositories are injected per-request via FastAPI Depends.
Instantiate them by passing a Session:

    from repositories.sqla_account_repo import AccountRepository
    repo = AccountRepository(session)
"""
from repositories.sqla_account_repo import AccountRepository
from repositories.sqla_transaction_repo import TransactionRepository
from repositories.sqla_institution_repo import SqlAlchemyInstitutionRepository
from repositories.sqla_account_detail_repo import SqlAlchemyAccountDetailRepository
from repositories.sqla_snapshot_repo import SqlAlchemySnapshotRepository
from repositories.sqla_settings_repo import SqlAlchemySettingsRepository
from repositories.sqla_profile_repo import SqlAlchemyProfileRepository

from repositories.sqla_goal_repo import SqlAlchemyGoalRepository

__all__ = [
    "AccountRepository",
    "TransactionRepository",
    "SqlAlchemyInstitutionRepository",
    "SqlAlchemyAccountDetailRepository",
    "SqlAlchemySnapshotRepository",
    "SqlAlchemySettingsRepository",
    "SqlAlchemyProfileRepository",
    "SqlAlchemyGoalRepository",
]

