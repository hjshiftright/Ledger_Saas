from fastapi import APIRouter, Depends, HTTPException, Response
from typing import List

from common.schemas import ErrorResponse
from api.deps import TenantDBSession
from repositories.sqla_transaction_repo import TransactionRepository
from repositories.sqla_account_repo import AccountRepository
from .schemas import (
    OpeningBalanceDTO, BulkOpeningBalanceDTO,
    OpeningBalanceResponse, BulkOpeningBalanceResponse
)
from .service import OpeningBalanceService
from common.exceptions import NotFoundError

router = APIRouter(prefix="/api/v1/onboarding/opening-balances", tags=["opening_balances"])

def get_ob_service(session: TenantDBSession) -> OpeningBalanceService:
    return OpeningBalanceService(TransactionRepository(session), AccountRepository(session))

@router.post(
    "",
    response_model=OpeningBalanceResponse,
    status_code=201,
    summary="Set Opening Balance",
    description="Set the opening balance for a specific account.",
    operation_id="setOpeningBalance",
    responses={
        201: {"description": "Opening balance set successfully"},
        404: {"description": "Account not found", "model": ErrorResponse},
    }
)
async def set_opening_balance(request: OpeningBalanceDTO, service: OpeningBalanceService = Depends(get_ob_service)):
    try:
        await service.set_opening_balance(request)
        return {"account_id": request.account_id, "amount": request.balance_amount}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post(
    "/bulk",
    response_model=BulkOpeningBalanceResponse,
    status_code=201,
    summary="Set Bulk Opening Balances",
    description="Set opening balances for multiple accounts at once. Returns 207 Multi-Status if some entries fail.",
    operation_id="setBulkOpeningBalances",
    responses={
        201: {"description": "All opening balances set successfully"},
        207: {"description": "Multi-Status: Some balances were set, others failed"},
    }
)
async def set_opening_balances_bulk(request: BulkOpeningBalanceDTO, response: Response, service: OpeningBalanceService = Depends(get_ob_service)):
    successful = []
    failed = []

    for entry in request.balances:
        try:
            await service.set_opening_balance(entry)
            successful.append({"account_id": entry.account_id, "amount": entry.balance_amount})
        except NotFoundError as e:
            failed.append({"account_id": entry.account_id, "error": str(e)})

    if failed:
        response.status_code = 207

    return {
        "total_processed": len(request.balances),
        "successful_entries": successful,
        "failed_entries": failed
    }
