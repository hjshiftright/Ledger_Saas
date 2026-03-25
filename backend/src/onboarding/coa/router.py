from fastapi import APIRouter, Depends, HTTPException
from typing import List

from common.schemas import ErrorResponse
from api.deps import DBSession
from repositories.sqla_account_repo import AccountRepository
from .schemas import (
    AccountNodeResponse, COARenameRequest, COACategoryAddRequest,
    COAStatusResponse
)
from .service import COASetupService

router = APIRouter(prefix="/api/v1/onboarding/coa", tags=["coa"])

def get_coa_service(session: DBSession) -> COASetupService:
    return COASetupService(AccountRepository(session))

@router.post(
    "/initialize",
    response_model=List[AccountNodeResponse],
    status_code=201,
    summary="Initialize Chart of Accounts",
    description="Creates the default system Chart of Accounts tree structure for the user.",
    operation_id="initializeCOA",
    responses={
        201: {"description": "COA initialized"},
        409: {"description": "COA already initialized", "model": ErrorResponse},
    }
)
def initialize_coa(service: COASetupService = Depends(get_coa_service)):
    # Need to protect against double initialization
    if service.is_coa_ready():
        raise HTTPException(status_code=409, detail="COA already initialized")
    return service.create_default_coa()

@router.get(
    "/tree",
    response_model=List[AccountNodeResponse],
    summary="Get COA Tree",
    description="Retrieve the entire Chart of Accounts in a hierarchical tree structure.",
    operation_id="getCOATree"
)
def get_coa_tree(service: COASetupService = Depends(get_coa_service)):
    # The existing method returns {"items": [...]}. The test wants a List, so we extract items.
    tree_response = service.get_coa_tree()
    return tree_response.items

@router.get(
    "/accounts/{account_id}",
    response_model=AccountNodeResponse,
    summary="Get COA Node",
    description="Retrieve a single Chart of Accounts node by its ID.",
    operation_id="getCOAAccount",
    responses={
        200: {"description": "Account found"},
        404: {"description": "Account not found", "model": ErrorResponse},
    }
)
def get_account(account_id: int, service: COASetupService = Depends(get_coa_service)):
    node = service._accounts.get(account_id)
    if not node:
        raise HTTPException(status_code=404, detail="Account not found")
    return service._to_response(node)

@router.post(
    "/categories",
    response_model=AccountNodeResponse,
    status_code=201,
    summary="Create custom category",
    description="Add a custom category (grouping node) to the Chart of Accounts.",
    operation_id="createCOACategory",
    responses={
        201: {"description": "Category created"},
        404: {"description": "Parent category not found", "model": ErrorResponse},
        422: {"description": "Validation error", "model": ErrorResponse},
    }
)
def add_custom_category(req: COACategoryAddRequest, service: COASetupService = Depends(get_coa_service)):
    return service.add_custom_category(req.parent_id, req.name)

@router.put(
    "/accounts/{account_id}/rename",
    response_model=AccountNodeResponse,
    summary="Rename COA Node",
    description="Rename a custom Chart of Accounts node. System nodes cannot be renamed.",
    operation_id="renameCOAAccount",
    responses={
        200: {"description": "Account renamed"},
        403: {"description": "Cannot rename a system account", "model": ErrorResponse},
        404: {"description": "Account not found", "model": ErrorResponse},
    }
)
def rename_account(account_id: int, req: COARenameRequest, service: COASetupService = Depends(get_coa_service)):
    try:
        return service.rename_account(account_id, req.new_name)
    except Exception as e:
        if "System accounts cannot be renamed" in str(e):
            raise HTTPException(status_code=403, detail="SYSTEM_ACCOUNT")
        raise

@router.delete(
    "/accounts/{account_id}",
    status_code=204,
    summary="Delete COA Node",
    description="Deactivate a custom COA node. System nodes cannot be deleted.",
    operation_id="deleteCOAAccount",
    responses={
        204: {"description": "Account deleted/deactivated"},
        403: {"description": "Cannot delete a system account", "model": ErrorResponse},
        404: {"description": "Account not found", "model": ErrorResponse},
    }
)
def deactivate_account(account_id: int, service: COASetupService = Depends(get_coa_service)):
    try:
        service.deactivate_category(account_id)
    except Exception as e:
        if "System accounts cannot be deactivated" in str(e):
            raise HTTPException(status_code=403, detail="SYSTEM_ACCOUNT")
        raise

@router.get(
    "/status",
    response_model=COAStatusResponse,
    summary="Check COA initialization status",
    description="Returns whether the Chart of Accounts has been initialized.",
    operation_id="getCOAStatus",
)
def get_coa_status(service: COASetupService = Depends(get_coa_service)):
    return COAStatusResponse(ready=service.is_coa_ready())
