from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.models.accounts import Account
from repositories.base import BaseRepository


class AccountRepository(BaseRepository[Account]):
    def __init__(self, session: AsyncSession):
        super().__init__(Account, session)

    async def create(self, account_data: dict) -> Account:
        data = account_data.copy()
        # Map legacy keys used by COA service
        if "type" in data and "account_type" not in data:
            data["account_type"] = data.pop("type")
        if "subtype" in data and "account_subtype" not in data:
            data["account_subtype"] = data.pop("subtype")
        acc = Account(**data)
        self.session.add(acc)
        await self.session.flush()
        return acc

    async def get(self, account_id: int) -> Optional[Account]:
        return await self.get_by_id(account_id)

    async def update(self, account_id: int, updates: dict) -> Optional[Account]:
        acc = await self.get(account_id)
        if acc:
            for key, value in updates.items():
                if hasattr(acc, key):
                    setattr(acc, key, value)
            await self.session.flush()
        return acc

    async def get_tree(self) -> List[Account]:
        """Return all tenant accounts ordered by code (RLS enforces tenant scoping)."""
        stmt = select(Account).order_by(Account.code)
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def get_children(self, account_id: int) -> List[Account]:
        stmt = select(Account).where(Account.parent_id == account_id).order_by(Account.code)
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def delete(self, entity: Account) -> None:
        await self.session.delete(entity)
        await self.session.flush()

    async def has_transactions(self, account_id: int) -> bool:
        return False

    async def find_by_code(self, code: str) -> Account | None:
        stmt = select(Account).where(Account.code == code)
        return await self.session.scalar(stmt)

    async def get_leaf_nodes_for_type(self, account_type: str) -> list[Account]:
        stmt = (
            select(Account)
            .where(Account.account_type == account_type)
            .where(Account.is_placeholder.is_(False))
            .where(Account.is_active.is_(True))
        )
        result = await self.session.scalars(stmt)
        return list(result.all())
