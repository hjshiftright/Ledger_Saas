from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from db.models.system import Profile
from repositories.base import BaseRepository


class SqlAlchemyProfileRepository(BaseRepository[Profile]):
    def __init__(self, session: Session):
        super().__init__(Profile, session)

    def create(self, profile_data: dict) -> Profile:
        profile = Profile(**profile_data)
        self.session.add(profile)
        self.session.flush()
        return profile

    def get(self, profile_id: int) -> Optional[Profile]:
        return self.session.get(Profile, profile_id)

    def get_by_name(self, name: str) -> Optional[Profile]:
        stmt = select(Profile).where(Profile.display_name == name)
        return self.session.scalar(stmt)

    def list(
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
        return list(self.session.scalars(stmt).all())

    def update(self, profile_id: int, updates: dict) -> Optional[Profile]:
        profile = self.get(profile_id)
        if profile:
            for key, value in updates.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)
            self.session.flush()
        return profile

    def delete(self, profile_id: int) -> bool:
        profile = self.get(profile_id)
        if profile:
            self.session.delete(profile)
            self.session.flush()
            return True
        return False

    def count(self, filters: dict = None) -> int:
        stmt = select(func.count()).select_from(Profile)
        if filters:
            for key, value in filters.items():
                if hasattr(Profile, key):
                    stmt = stmt.where(getattr(Profile, key) == value)
        return self.session.scalar(stmt) or 0
