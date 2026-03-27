from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from db.models.system import Profile
from repositories.base import BaseRepository


class SqlAlchemyProfileRepository(BaseRepository[Profile]):
    def __init__(self, session: AsyncSession):
        super().__init__(Profile, session)

    async def create(self, profile_data: dict) -> Profile:
        profile = Profile(**profile_data)
        self.session.add(profile)
        await self.session.flush()
        return profile

    async def get(self, profile_id: int) -> Optional[Profile]:
        return await self.session.get(Profile, profile_id)

    async def get_by_name(self, name: str) -> Optional[Profile]:
        stmt = select(Profile).where(Profile.display_name == name)
        return await self.session.scalar(stmt)

    async def list(
        self,
        limit: int = 10,
        offset: int = 0,
        sort_by: str = "id",
        sort_desc: bool = False,
        filters: dict = None,
    ) -> List[Profile]:
        stmt = select(Profile)
        if filters:
            for key, value in filters.items():
                if hasattr(Profile, key):
                    stmt = stmt.where(getattr(Profile, key) == value)
        attr = getattr(Profile, sort_by, Profile.id)
        stmt = stmt.order_by(attr.desc() if sort_desc else attr.asc())
        stmt = stmt.limit(limit).offset(offset)
        return list((await self.session.scalars(stmt)).all())

    async def update(self, profile_id: int, updates: dict) -> Optional[Profile]:
        profile = await self.get(profile_id)
        if profile:
            for key, value in updates.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)
            await self.session.flush()
        return profile

    async def delete(self, profile_id: int) -> bool:
        profile = await self.get(profile_id)
        if profile:
            await self.session.delete(profile)
            await self.session.flush()
            return True
        return False

    async def count(self, filters: dict = None) -> int:
        stmt = select(func.count()).select_from(Profile)
        if filters:
            for key, value in filters.items():
                if hasattr(Profile, key):
                    stmt = stmt.where(getattr(Profile, key) == value)
        return await self.session.scalar(stmt) or 0
