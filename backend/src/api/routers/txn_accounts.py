from fastapi import APIRouter, Depends
from api.deps import get_account_service
from services.account_service import AccountService
from schemas.account import AccountCreateDTO, AccountResponseDTO

router = APIRouter()

@router.post("/accounts", response_model=AccountResponseDTO)
def create_account(
    data: AccountCreateDTO,
    service: AccountService = Depends(get_account_service)
):
    return service.create_new_account(data)
