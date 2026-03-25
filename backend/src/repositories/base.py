from typing import TypeVar, Generic, Type, Sequence, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from db.models.base import Base

T = TypeVar("T", bound=Base)

class BaseRepository(Generic[T]):
    """Generic repository mapping standard CRUD ops to object entities."""
    def __init__(self, model: Type[T], session: Session):
        self.model = model
        self.session = session

    def get_by_id(self, entity_id: int) -> Optional[T]:
        return self.session.get(self.model, entity_id)

    def get_by_id_or_raise(self, entity_id: int) -> T:
        entity = self.get_by_id(entity_id)
        if entity is None:
            raise ValueError(f"{self.model.__name__} with ID {entity_id} not found")
        return entity

    def count(self) -> int:
        stmt = select(func.count()).select_from(self.model)
        return self.session.scalar(stmt) or 0

    def list_paginated(self, offset: int = 0, limit: int = 100) -> Sequence[T]:
        stmt = select(self.model).offset(offset).limit(limit)
        return self.session.scalars(stmt).all()

    def create(self, entity: T) -> T:
        """Create operation using Python Objects"""
        self.session.add(entity)
        self.session.flush() # Securely assigns ID without committing txn
        return entity

    def create_many(self, entities: list[T]) -> list[T]:
        self.session.add_all(entities)
        self.session.flush()
        return entities

    def update(self, entity: T) -> T:
        """Update operation using Python Objects"""
        merged = self.session.merge(entity)
        self.session.flush()
        return merged

    def delete(self, entity: T) -> None:
        """Delete operation using Python Objects"""
        self.session.delete(entity)
        self.session.flush()

    def delete_by_id(self, entity_id: int) -> None:
        entity = self.get_by_id_or_raise(entity_id)
        self.delete(entity)
