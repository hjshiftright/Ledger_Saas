from typing import Optional, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.models.accounts import FinancialInstitution
from repositories.base import BaseRepository


class SqlAlchemyInstitutionRepository(BaseRepository[FinancialInstitution]):
    def __init__(self, session: AsyncSession):
        super().__init__(FinancialInstitution, session)

    async def create(self, institution_data: dict) -> FinancialInstitution:
        data = self._map_data(institution_data)
        inst = FinancialInstitution(**data)
        self.session.add(inst)
        await self.session.flush()
        return inst

    async def get(self, institution_id: int) -> Optional[FinancialInstitution]:
        return await self.get_by_id(institution_id)

    async def list(self) -> Sequence[FinancialInstitution]:
        stmt = select(FinancialInstitution).where(FinancialInstitution.is_active == True)
        return (await self.session.scalars(stmt)).all()

    async def update(self, institution_id: int, updates: dict) -> Optional[FinancialInstitution]:
        inst = await self.get(institution_id)
        if inst:
            data = self._map_data(updates)
            for key, value in data.items():
                if hasattr(inst, key):
                    setattr(inst, key, value)
            await self.session.flush()
        return inst

    def _map_data(self, data: dict) -> dict:
        mapped = data.copy()
        if "website_url" in mapped:
            mapped["website"] = mapped.pop("website_url")
        if "type" in mapped:
            mapped["institution_type"] = mapped.pop("type")
        return mapped
