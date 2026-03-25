from fastapi import APIRouter, Depends, Query, HTTPException, Response
from typing import Optional
from .schemas import ProfileSetupRequest, ProfileResponse, ProfileStatusResponse, ProfileUpdatePartialRequest
from common.schemas import ErrorResponse
from common.exceptions import NotFoundError, ValidationError, DuplicateError
from api.deps import DBSession, CurrentUser

def _parse_user_id(user: str) -> int:
    try: return int(user)
    except: return 0
from repositories.sqla_profile_repo import SqlAlchemyProfileRepository
from .service import ProfileService

router = APIRouter(prefix="/api/v1/onboarding/profiles", tags=["profile"])


def get_profile_service(session: DBSession) -> ProfileService:
    return ProfileService(SqlAlchemyProfileRepository(session))


@router.post(
    "",
    response_model=ProfileResponse,
    status_code=201,
    summary="Create user profile",
    responses={
        201: {"description": "Profile created successfully"},
        409: {"description": "Duplicate profile", "model": ErrorResponse},
        422: {"description": "Validation error", "model": ErrorResponse},
    },
)
def create_profile(request: ProfileSetupRequest, user: CurrentUser, service: ProfileService = Depends(get_profile_service)):
    uid = _parse_user_id(user)
    try:
        return service.setup_profile(request, uid)
    except DuplicateError as e:
        return Response(
            status_code=409,
            content=ErrorResponse(error_code=e.error_code, message=str(e)).model_dump_json(),
            media_type="application/json",
        )
    except ValidationError as e:
        return Response(
            status_code=422,
            content=ErrorResponse(error_code=e.error_code, message=str(e)).model_dump_json(),
            media_type="application/json",
        )


@router.get("", summary="List profiles")
def list_profiles(
    fields: Optional[str] = Query(None),
    limit: int = Query(10, ge=1),
    offset: int = Query(0, ge=0),
    sort: Optional[str] = Query(None),
    base_currency: Optional[str] = Query(None),
    service: ProfileService = Depends(get_profile_service),
):
    sort_by = "id"
    sort_desc = False
    if sort:
        if ":" in sort:
            sort_by, order = sort.split(":", 1)
            sort_desc = order.lower() == "desc"
        else:
            sort_by = sort

    filters = {}
    if base_currency:
        filters["base_currency"] = base_currency

    items = service.list_profiles(limit, offset, sort_by, sort_desc, filters)
    total = service.count_profiles(filters)

    if fields:
        allowed = {f.strip() for f in fields.split(",")} | {"id"}
        items_out = [{k: v for k, v in item.model_dump().items() if k in allowed} for item in items]
    else:
        items_out = [item.model_dump() for item in items]

    return {
        "items": items_out,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_next": (offset + limit) < total,
        "pages": (total + limit - 1) // limit if total > 0 else 0,
    }


@router.get("/{profile_id}", response_model=ProfileResponse)
def get_profile(profile_id: int, service: ProfileService = Depends(get_profile_service)):
    try:
        return service.get_profile(profile_id)
    except NotFoundError:
        return Response(
            status_code=404,
            content=ErrorResponse(error_code="NOT_FOUND", message="Profile not found").model_dump_json(),
            media_type="application/json",
        )


@router.put("/{profile_id}", response_model=ProfileResponse)
def update_profile(profile_id: int, request: ProfileSetupRequest, user: CurrentUser, service: ProfileService = Depends(get_profile_service)):
    uid = _parse_user_id(user)
    try:
        return service.setup_profile(request, uid, profile_id)
    except NotFoundError:
        return Response(
            status_code=404,
            content=ErrorResponse(error_code="NOT_FOUND", message="Profile not found").model_dump_json(),
            media_type="application/json",
        )


@router.patch("/{profile_id}", response_model=ProfileResponse)
def patch_profile(profile_id: int, request: ProfileUpdatePartialRequest, user: CurrentUser, service: ProfileService = Depends(get_profile_service)):
    uid = _parse_user_id(user)
    try:
        existing = service.get_profile(profile_id)
        update_data = request.model_dump(exclude_unset=True)
        dumped = existing.model_dump()
        dumped.update(update_data)
        return service.setup_profile(ProfileSetupRequest(**dumped), uid, profile_id)
    except NotFoundError:
        return Response(
            status_code=404,
            content=ErrorResponse(error_code="NOT_FOUND", message="Profile not found").model_dump_json(),
            media_type="application/json",
        )


@router.delete("/{profile_id}", status_code=204)
def delete_profile(profile_id: int, service: ProfileService = Depends(get_profile_service)):
    try:
        service.delete_profile(profile_id)
    except NotFoundError:
        return Response(
            status_code=404,
            content=ErrorResponse(error_code="NOT_FOUND", message="Profile not found").model_dump_json(),
            media_type="application/json",
        )
    return Response(status_code=204)


@router.get("/{profile_id}/status", response_model=ProfileStatusResponse)
def get_status(profile_id: int, service: ProfileService = Depends(get_profile_service)):
    try:
        complete = service.is_profile_complete(profile_id)
        return ProfileStatusResponse(complete=complete)
    except NotFoundError:
        return Response(
            status_code=404,
            content=ErrorResponse(error_code="NOT_FOUND", message="Profile not found").model_dump_json(),
            media_type="application/json",
        )


    # If it's in DB, we consider it configured
    return ProfileStatusResponse(complete=True)
