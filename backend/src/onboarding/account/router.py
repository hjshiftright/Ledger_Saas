from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional

from common.schemas import PaginatedResponse, ErrorResponse
from api.deps import TenantDBSession
from repositories.sqla_account_repo import AccountRepository
from repositories.sqla_institution_repo import SqlAlchemyInstitutionRepository
from repositories.sqla_account_detail_repo import SqlAlchemyAccountDetailRepository
from .schemas import (
    BankAccountSetupDTO, CreditCardSetupDTO, LoanSetupDTO,
    BrokerageSetupDTO, FixedDepositSetupDTO, CashWalletSetupDTO,
    AccountResponse
)
from .service import AccountSetupService

router = APIRouter(prefix="/api/v1/onboarding/accounts", tags=["accounts"])

def get_account_service(session: TenantDBSession) -> AccountSetupService:
    return AccountSetupService(
        AccountRepository(session),
        SqlAlchemyInstitutionRepository(session),
        SqlAlchemyAccountDetailRepository(session),
    )

def _format_response(result: dict) -> dict:
    """Combines created COA node and detail into AccountResponse format."""
    coa = result["coa"]
    detail = result.get("detail")

    detail_dict = None
    if detail:
        if hasattr(detail, "__table__"):
            detail_dict = {c.name: getattr(detail, c.name) for c in detail.__table__.columns}
            # Map back to API field names
            if "branch_name" in detail_dict:
                detail_dict["branch"] = detail_dict.pop("branch_name")
            if "card_number_masked" in detail_dict:
                detail_dict["last_four_digits"] = detail_dict.pop("card_number_masked")
            if "deposit_date" in detail_dict:
                detail_dict["start_date"] = detail_dict.pop("deposit_date")
            if "disbursement_date" in detail_dict:
                detail_dict["start_date"] = detail_dict.pop("disbursement_date")
            if "account_identifier" in detail_dict:
                detail_dict["demat_id"] = detail_dict.pop("account_identifier")
        elif isinstance(detail, dict):
            detail_dict = detail

    return {
        "id": coa.id,
        "name": coa.name,
        "account_type": coa.account_type,
        "subtype": coa.account_subtype,
        "institution_id": getattr(detail, "institution_id", None) if detail else None,
        "detail": detail_dict
    }

@router.post(
    "/bank",
    response_model=AccountResponse,
    status_code=201,
    summary="Create bank account",
    operation_id="createBankAccount",
)
async def add_bank_account(request: BankAccountSetupDTO, service: AccountSetupService = Depends(get_account_service)):
    return _format_response(await service.add_bank_account(request))

@router.post(
    "/credit-card",
    response_model=AccountResponse,
    status_code=201,
    summary="Create credit card",
    operation_id="createCreditCard",
)
async def add_credit_card(request: CreditCardSetupDTO, service: AccountSetupService = Depends(get_account_service)):
    return _format_response(await service.add_credit_card(request))

@router.post(
    "/loan",
    response_model=AccountResponse,
    status_code=201,
    summary="Create loan account",
    operation_id="createLoanAccount",
)
async def add_loan(request: LoanSetupDTO, service: AccountSetupService = Depends(get_account_service)):
    return _format_response(await service.add_loan(request))

@router.post(
    "/brokerage",
    response_model=AccountResponse,
    status_code=201,
    summary="Create brokerage account",
    operation_id="createBrokerageAccount",
)
async def add_brokerage_account(request: BrokerageSetupDTO, service: AccountSetupService = Depends(get_account_service)):
    return _format_response(await service.add_brokerage_account(request))

@router.post(
    "/fixed-deposit",
    response_model=AccountResponse,
    status_code=201,
    summary="Create fixed deposit",
    operation_id="createFixedDeposit",
)
async def add_fixed_deposit(request: FixedDepositSetupDTO, service: AccountSetupService = Depends(get_account_service)):
    return _format_response(await service.add_fixed_deposit(request))

@router.post(
    "/cash",
    response_model=AccountResponse,
    status_code=201,
    summary="Create cash wallet",
    operation_id="createCashWallet",
)
async def add_cash_wallet(request: CashWalletSetupDTO, service: AccountSetupService = Depends(get_account_service)):
    return _format_response(await service.add_cash_wallet(request))

@router.get(
    "",
    response_model=PaginatedResponse[AccountResponse],
    summary="List accounts",
    operation_id="listAccounts",
)
async def list_accounts(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1),
    account_type: Optional[str] = None,
    institution_id: Optional[int] = None,
    service: AccountSetupService = Depends(get_account_service),
):
    return {
        "items": [], "total": 0, "page": page, "size": size, "pages": 0,
        "offset": 0, "has_next": False, "has_previous": False
    }

@router.get(
    "/{account_id}",
    response_model=AccountResponse,
    summary="Get account by ID",
    operation_id="getAccount",
    responses={404: {"model": ErrorResponse}}
)
async def get_account(account_id: int, service: AccountSetupService = Depends(get_account_service)):
    raise HTTPException(status_code=404, detail="Awaiting service layer")

@router.delete(
    "/{account_id}",
    status_code=204,
    summary="Delete account",
    operation_id="deleteAccount",
    responses={404: {"model": ErrorResponse}}
)
async def delete_account(account_id: int, service: AccountSetupService = Depends(get_account_service)):
    pass
