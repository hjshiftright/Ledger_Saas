from typing import Optional, List
from datetime import date as _date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from db.models.goals import Goal
from repositories.base import BaseRepository

_DATE_FIELDS = ("start_date", "target_date", "achieved_date")


class SqlAlchemyGoalRepository(BaseRepository[Goal]):
    def __init__(self, session: AsyncSession):
        super().__init__(Goal, session)

    async def create(self, goal_data: dict) -> Goal:
        data = goal_data.copy()
        # Coerce ISO date strings → Python date objects (SQLite rejects strings)
        for field in _DATE_FIELDS:
            val = data.get(field)
            if isinstance(val, str):
                data[field] = _date.fromisoformat(val)
        goal = Goal(**data)
        self.session.add(goal)
        await self.session.flush()
        return goal

    async def get(self, goal_id: int, user_id: int | None = None) -> Optional[Goal]:
        goal = self.session.get(Goal, goal_id)
        if goal is None:
            return None
        if user_id is not None and goal.user_id != user_id:
            return None
        return goal

    async def list(self, user_id: int | None = None) -> List[Goal]:
        stmt = select(Goal)
        if user_id is not None:
            stmt = stmt.where(Goal.user_id == user_id)
        return list(self.session.scalars(stmt).all())

    async def delete_all(self, user_id: int | None = None):
        stmt = delete(Goal)
        if user_id is not None:
            stmt = stmt.where(Goal.user_id == user_id)
        await self.session.execute(stmt)
        await self.session.flush()

    async def update(self, goal_id: int, updates: dict, user_id: int | None = None) -> Optional[Goal]:
        goal = self.get(goal_id, user_id=user_id)
        if goal:
            for key, value in updates.items():
                if hasattr(goal, key):
                    setattr(goal, key, value)
            await self.session.flush()
        return goal
