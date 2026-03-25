from typing import Optional, Sequence
from sqlalchemy.orm import Session
from sqlalchemy import select
from db.models.accounts import FinancialInstitution
from repositories.base import BaseRepository


class SqlAlchemyInstitutionRepository(BaseRepository[FinancialInstitution]):
    def __init__(self, session: Session):
        super().__init__(FinancialInstitution, session)

    def create(self, institution_data: dict) -> FinancialInstitution:
        data = self._map_data(institution_data)
        inst = FinancialInstitution(**data)
        self.session.add(inst)
        self.session.flush()
        return inst

    def get(self, institution_id: int) -> Optional[FinancialInstitution]:
        return self.get_by_id(institution_id)

    def list(self) -> Sequence[FinancialInstitution]:
        stmt = select(FinancialInstitution).where(FinancialInstitution.is_active == True)
        return self.session.scalars(stmt).all()

    def update(self, institution_id: int, updates: dict) -> Optional[FinancialInstitution]:
        inst = self.get(institution_id)
        if inst:
            data = self._map_data(updates)
            for key, value in data.items():
                if hasattr(inst, key):
                    setattr(inst, key, value)
            self.session.flush()
        return inst

    def _map_data(self, data: dict) -> dict:
        mapped = data.copy()
        if "website_url" in mapped:
            mapped["website"] = mapped.pop("website_url")
        if "type" in mapped:
            mapped["institution_type"] = mapped.pop("type")
        return mapped
