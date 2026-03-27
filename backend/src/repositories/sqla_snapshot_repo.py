from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from db.models.reporting import NetWorthHistory
from repositories.base import BaseRepository


class SqlAlchemySnapshotRepository(BaseRepository[NetWorthHistory]):
    def __init__(self, session: AsyncSession):
        super().__init__(NetWorthHistory, session)

    async def save_net_worth(self, data: dict) -> NetWorthHistory:
        from datetime import date
        mapped = data.copy()
        if isinstance(mapped.get("snapshot_date"), str):
            mapped["snapshot_date"] = date.fromisoformat(mapped["snapshot_date"])

        snapshot = NetWorthHistory(**mapped)
        self.session.add(snapshot)
        await self.session.flush()
        return snapshot
