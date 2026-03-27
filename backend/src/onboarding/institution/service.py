from typing import List
from repositories.protocols import InstitutionRepository
from common.exceptions import DuplicateError, NotFoundError, ValidationError
from .schemas import InstitutionCreateDTO, InstitutionResponse


def _attr(obj, key, default=None):
    if hasattr(obj, key):
        return getattr(obj, key)
    return obj.get(key, default) if isinstance(obj, dict) else default


class InstitutionService:
    def __init__(self, institution_repo: InstitutionRepository):
        self._repo = institution_repo

    def _to_response(self, inst) -> InstitutionResponse:
        return InstitutionResponse(
            id=_attr(inst, "id"),
            name=_attr(inst, "name"),
            institution_type=_attr(inst, "institution_type"),
            website_url=_attr(inst, "website"),
            notes=_attr(inst, "notes"),
        )

    async def add_institution(self, dto: InstitutionCreateDTO) -> InstitutionResponse:
        if not dto.name.strip():
            raise ValidationError("Institution name cannot be empty")

        existing = await self._repo.list()
        for idx in existing:
            if _attr(idx, "name", "").lower() == dto.name.lower():
                raise DuplicateError("Institution", dto.name)

        data = {
            "name": dto.name,
            "institution_type": dto.institution_type.value,
            "website_url": dto.website_url,
            "notes": dto.notes,
        }

        created = await self._repo.create(data)
        return self._to_response(created)

    async def get_institution(self, id: int) -> InstitutionResponse:
        inst = await self._repo.get(id)
        if not inst:
            raise NotFoundError("Institution", id)
        return self._to_response(inst)

    async def list_institutions(
        self,
        page: int = 1,
        size: int = 20,
        offset: int = None,
        limit: int = None,
        sort_by: str = None,
        sort_desc: bool = False,
        institution_type: str = None,
        search: str = None,
    ) -> dict:
        results = list(await self._repo.list())

        if institution_type:
            results = [r for r in results if _attr(r, "institution_type") == institution_type]
        if search:
            search_lower = search.lower()
            results = [r for r in results if search_lower in (_attr(r, "name") or "").lower()]

        if sort_by:
            results.sort(key=lambda x: _attr(x, sort_by) or "", reverse=sort_desc)
        else:
            results.sort(key=lambda x: _attr(x, "id", 0), reverse=sort_desc)

        total = len(results)

        if offset is not None and limit is not None:
            start = offset
            end = offset + limit
            actual_limit = limit
            actual_page = (offset // limit) + 1 if limit > 0 else 1
        else:
            start = (page - 1) * size
            end = start + size
            actual_limit = size
            actual_page = page
            offset = start

        paged_results = results[start:end]
        items = [self._to_response(idx) for idx in paged_results]

        pages = (total + actual_limit - 1) // actual_limit if actual_limit > 0 else 0
        return {
            "items": items,
            "total": total,
            "page": actual_page,
            "size": actual_limit,
            "pages": pages,
            "offset": offset,
            "has_next": end < total,
            "has_previous": start > 0,
        }

    async def delete_institution(self, institution_id: int) -> None:
        pass  # Deferred to Phase 2 (service layer implementation)

    async def update_institution(self, id: int, dto: InstitutionCreateDTO) -> InstitutionResponse:
        if not dto.name.strip():
            raise ValidationError("Institution name cannot be empty")

        inst = await self._repo.get(id)
        if not inst:
            raise NotFoundError("Institution", id)

        existing = await self._repo.list()
        for idx in existing:
            if _attr(idx, "name", "").lower() == dto.name.lower() and _attr(idx, "id") != id:
                raise DuplicateError("Institution", dto.name)

        updates = {
            "name": dto.name,
            "institution_type": dto.institution_type.value,
            "website_url": dto.website_url,
            "notes": dto.notes,
        }

        updated = await self._repo.update(id, updates)
        return self._to_response(updated)
