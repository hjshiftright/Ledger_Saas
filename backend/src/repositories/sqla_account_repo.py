from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import or_, select
from db.models.accounts import Account
from repositories.base import BaseRepository


class AccountRepository(BaseRepository[Account]):
    def __init__(self, session: AsyncSession, user_id: int | None = None):
        super().__init__(Account, session)
        # When set, queries are scoped to this user_id.
        # System accounts (user_id IS NULL) are always included.
        self._user_id = user_id

    async def _user_filter(self):
        """Return a SQLAlchemy filter that includes the user's accounts + system accounts."""
        if self._user_id is None:
            return None  # No filter — caller sees everything
        return or_(Account.user_id == self._user_id, Account.user_id.is_(None))

    async def create(self, account_data: dict) -> Account:
        data = account_data.copy()
        # Map legacy keys used by COA service
        if "type" in data and "account_type" not in data:
            data["account_type"] = data.pop("type")
        if "subtype" in data and "account_subtype" not in data:
            data["account_subtype"] = data.pop("subtype")
        # Inject user_id if provided and not already set
        if self._user_id is not None and "user_id" not in data:
            data["user_id"] = self._user_id
        acc = Account(**data)
        self.session.add(acc)
        await self.session.flush()
        return acc

    async def get(self, account_id: int) -> Optional[Account]:
        acc = self.get_by_id(account_id)
        if acc is None:
            return None
        uf = self._user_filter()
        if uf is not None:
            # Validate ownership: user's account or system account
            if acc.user_id is not None and self._user_id is not None and acc.user_id != self._user_id:
                return None
        return acc

    async def update(self, account_id: int, updates: dict) -> Optional[Account]:
        acc = self.get(account_id)
        if acc:
            for key, value in updates.items():
                if hasattr(acc, key):
                    setattr(acc, key, value)
            await self.session.flush()
        return acc

    async def get_tree(self) -> List[Account]:
        """Return accounts scoped by user, ordered by code; service layer handles nesting."""
        stmt = select(Account).order_by(Account.code)
        uf = self._user_filter()
        if uf is not None:
            stmt = stmt.where(uf)
        return list(self.session.scalars(stmt).all())

    async def get_children(self, account_id: int) -> List[Account]:
        stmt = select(Account).where(Account.parent_id == account_id).order_by(Account.code)
        uf = self._user_filter()
        if uf is not None:
            stmt = stmt.where(uf)
        return list(self.session.scalars(stmt).all())

    async def has_transactions(self, account_id: int) -> bool:
        return False

    async def find_by_code(self, code: str) -> Account | None:
        stmt = select(Account).where(Account.code == code)
        uf = self._user_filter()
        if uf is not None:
            stmt = stmt.where(uf)
        return await self.session.scalar(stmt)

    async def get_leaf_nodes_for_type(self, account_type: str) -> list[Account]:
        stmt = (
            select(Account)
            .where(Account.account_type == account_type)
            .where(Account.is_placeholder.is_(False))
            .where(Account.is_active.is_(True))
        )
        uf = self._user_filter()
        if uf is not None:
            stmt = stmt.where(uf)
        return list(self.session.scalars(stmt).all())
