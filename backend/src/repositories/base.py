from typing import TypeVar, Generic, Type, Sequence, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from db.models.base import Base

T = TypeVar("T", bound=Base)

class BaseRepository(Generic[T]):
    """Generic repository mapping standard CRUD ops to object entities."""
    def __init__(self, model: Type[T], session: AsyncSession):
        self.model = model
        self.session = session

    async def get_by_id(self, entity_id: int) -> Optional[T]:
        return await self.session.get(self.model, entity_id)

    async def get_by_id_or_raise(self, entity_id: int) -> T:
        entity = await self.get_by_id(entity_id)
        if entity is None:
            raise ValueError(f"{self.model.__name__} with ID {entity_id} not found")
        return entity

    async def count(self) -> int:
        stmt = select(func.count()).select_from(self.model)
        res = await self.session.scalar(stmt)
        return res or 0

    async def list_paginated(self, offset: int = 0, limit: int = 100) -> Sequence[T]:
        stmt = select(self.model).offset(offset).limit(limit)
        res = await self.session.scalars(stmt)
        return res.all()

    async def create(self, entity: T) -> T:
        """Create operation using Python Objects"""
        self.session.add(entity)
        await self.session.flush() # Securely assigns ID without committing txn
        return entity

    async def create_many(self, entities: list[T]) -> list[T]:
        self.session.add_all(entities)
        await self.session.flush()
        return entities

    async def update(self, entity: T) -> T:
        """Update operation using Python Objects"""
        merged = await self.session.merge(entity)
        await self.session.flush()
        return merged

    async def delete(self, entity: T) -> None:
        """Delete operation using Python Objects"""
        await self.session.delete(entity)
        await self.session.flush()

    async def delete_by_id(self, entity_id: int) -> None:
        entity = await self.get_by_id_or_raise(entity_id)
        await self.delete(entity)
