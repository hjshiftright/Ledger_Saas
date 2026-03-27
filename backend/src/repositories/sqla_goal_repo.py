from typing import Optional, List
from datetime import date as _date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from db.models.goals import Goal
from repositories.base import BaseRepository

_DATE_FIELDS = ("target_date",)


class SqlAlchemyGoalRepository(BaseRepository[Goal]):
    def __init__(self, session: AsyncSession):
        super().__init__(Goal, session)

    async def create(self, goal_data: dict) -> Goal:
        data = goal_data.copy()
        for field in _DATE_FIELDS:
            val = data.get(field)
            if isinstance(val, str):
                data[field] = _date.fromisoformat(val)
        goal = Goal(**data)
        self.session.add(goal)
        await self.session.flush()
        return goal

    async def get(self, goal_id: int) -> Optional[Goal]:
        return await self.session.get(Goal, goal_id)

    async def list(self) -> List[Goal]:
        """Return all goals for the current tenant (RLS enforces tenant scoping)."""
        result = await self.session.scalars(select(Goal))
        return list(result.all())

    async def update(self, goal_id: int, updates: dict) -> Optional[Goal]:
        goal = await self.get(goal_id)
        if goal:
            for key, value in updates.items():
                if hasattr(goal, key):
                    setattr(goal, key, value)
            await self.session.flush()
        return goal

    async def delete_all(self):
        """Delete all goals for the current tenant (RLS enforces scoping)."""
        await self.session.execute(delete(Goal))
        await self.session.flush()
