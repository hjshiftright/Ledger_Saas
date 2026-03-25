from fastapi import APIRouter, Depends, Query
from typing import Optional
from datetime import date

from .schemas import NetWorthResponse
from .service import NetWorthService
from api.deps import DBSession
from repositories.sqla_snapshot_repo import SqlAlchemySnapshotRepository
from repositories.sqla_account_repo import AccountRepository
from repositories.sqla_transaction_repo import TransactionRepository

router = APIRouter(prefix="/api/v1/onboarding/networth", tags=["net_worth"])

def get_networth_service(session: DBSession) -> NetWorthService:
    return NetWorthService(
        SqlAlchemySnapshotRepository(session),
        AccountRepository(session),
        TransactionRepository(session),
    )

@router.get(
    "",
    response_model=NetWorthResponse,
    summary="Compute Net Worth",
    description="Compute the user's total net worth as of a specific date. Defaults to today.",
    operation_id="computeNetWorth"
)
def compute_net_worth(
    as_of_date: Optional[str] = Query(None, description="Compute net worth as of this date (YYYY-MM-DD). Defaults to today."),
    service: NetWorthService = Depends(get_networth_service)
):
    if not as_of_date:
        as_of_date = date.today().isoformat()
    return service.compute_initial_net_worth(as_of_date)
