from fastapi import APIRouter, Depends
from .schemas import DashboardSaveRequest, DashboardDataResponse
from .service import DashboardService
from api.deps import DBSession, CurrentUser
from repositories.sqla_account_repo import AccountRepository
from repositories.sqla_transaction_repo import TransactionRepository
from repositories.sqla_profile_repo import SqlAlchemyProfileRepository
from repositories.sqla_goal_repo import SqlAlchemyGoalRepository

router = APIRouter(prefix="/api/v1/onboarding/dashboard", tags=["onboarding_dashboard"])

def get_dashboard_service(session: DBSession) -> DashboardService:
    return DashboardService(
        AccountRepository(session),
        TransactionRepository(session),
        SqlAlchemyProfileRepository(session),
        SqlAlchemyGoalRepository(session)
    )

@router.post("/save", response_model=DashboardDataResponse)
def save_dashboard(
    request: DashboardSaveRequest,
    user_id: CurrentUser,
    service: DashboardService = Depends(get_dashboard_service)
):
    return service.save_dashboard(request, user_id)

@router.get("", response_model=DashboardDataResponse)
def get_dashboard(
    user_id: CurrentUser,
    service: DashboardService = Depends(get_dashboard_service)
):
    return service.get_dashboard(user_id)
