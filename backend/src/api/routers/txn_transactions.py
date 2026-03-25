from fastapi import APIRouter, Depends
from api.deps import get_transaction_service
from services.transaction_service import TransactionService
from schemas.transaction import TransactionCreateDTO, TransactionResponseDTO

router = APIRouter()

@router.post("/transactions/expense", response_model=TransactionResponseDTO)
def record_expense(
    data: TransactionCreateDTO,
    service: TransactionService = Depends(get_transaction_service)
):
    return service.record_expense(data)
