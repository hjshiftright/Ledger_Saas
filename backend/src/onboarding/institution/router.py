from fastapi import APIRouter, Depends, Query
from typing import Optional
from .schemas import InstitutionCreateDTO, InstitutionResponse
from common.schemas import PaginatedResponse, ErrorResponse
from .service import InstitutionService
from api.deps import TenantDBSession
from repositories.sqla_institution_repo import SqlAlchemyInstitutionRepository


router = APIRouter(prefix="/api/v1/onboarding/institutions", tags=["institutions"])


def get_institution_service(session: TenantDBSession) -> InstitutionService:
    return InstitutionService(SqlAlchemyInstitutionRepository(session))


@router.post(
    "",
    response_model=InstitutionResponse,
    status_code=201,
    summary="Create institution",
    description="Registers a new financial institution (Bank, Brokerage, NBFC, etc.).",
    operation_id="createInstitution",
    responses={
        201: {"description": "Institution created"},
        409: {"description": "Institution with this name already exists", "model": ErrorResponse},
        422: {"description": "Validation error", "model": ErrorResponse},
    },
)
async def add_institution(
    request: InstitutionCreateDTO,
    service: InstitutionService = Depends(get_institution_service),
):
    return await service.add_institution(request)


@router.get(
    "/{institution_id}",
    response_model=InstitutionResponse,
    summary="Get institution by ID",
    operation_id="getInstitution",
    responses={
        200: {"description": "Institution retrieved"},
        404: {"description": "Institution not found", "model": ErrorResponse},
    },
)
async def get_institution(
    institution_id: int,
    service: InstitutionService = Depends(get_institution_service),
):
    return await service.get_institution(institution_id)


@router.get(
    "",
    response_model=PaginatedResponse[InstitutionResponse],
    summary="List institutions",
    description="Retrieve a paginated list of institutions with optional sorting and filtering.",
    operation_id="listInstitutions",
)
async def list_institutions(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: Optional[int] = Query(None, ge=0, description="Override page/size with absolute offset"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Max items to return when using offset"),
    sort_by: Optional[str] = Query(None, description="Field to sort by (e.g. name)"),
    sort_desc: bool = Query(False, description="Sort descending"),
    institution_type: Optional[str] = Query(None, description="Filter by exact type (e.g. BANK)"),
    search: Optional[str] = Query(None, description="Partial match search term for name"),
    service: InstitutionService = Depends(get_institution_service),
):
    result = await service.list_institutions(
        page=page,
        size=size,
        offset=offset,
        limit=limit,
        sort_by=sort_by,
        sort_desc=sort_desc,
        institution_type=institution_type,
        search=search,
    )
    return PaginatedResponse(**result)


@router.put(
    "/{institution_id}",
    response_model=InstitutionResponse,
    summary="Update institution",
    description="Update the details of an existing institution.",
    operation_id="updateInstitution",
    responses={
        200: {"description": "Institution updated"},
        404: {"description": "Institution not found", "model": ErrorResponse},
        409: {"description": "Name collision with another institution", "model": ErrorResponse},
        422: {"description": "Validation error", "model": ErrorResponse},
    },
)
async def update_institution(
    institution_id: int,
    request: InstitutionCreateDTO,
    service: InstitutionService = Depends(get_institution_service),
):
    return await service.update_institution(institution_id, request)


@router.delete(
    "/{institution_id}",
    status_code=204,
    summary="Delete institution",
    description="Soft-delete an institution. Deletion is restricted if accounts are linked.",
    operation_id="deleteInstitution",
    responses={
        204: {"description": "Institution deleted"},
        404: {"description": "Institution not found", "model": ErrorResponse},
    },
)
async def delete_institution(
    institution_id: int,
    service: InstitutionService = Depends(get_institution_service),
):
    await service.delete_institution(institution_id)
