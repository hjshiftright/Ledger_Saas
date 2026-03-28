from fastapi import APIRouter, Depends
from .schemas import DashboardSaveRequest, DashboardDataResponse
from .service import DashboardService
from api.deps import TenantDBSession, CurrentUserPayload
from repositories.sqla_account_repo import AccountRepository
from repositories.sqla_transaction_repo import TransactionRepository
from repositories.sqla_profile_repo import SqlAlchemyProfileRepository
from repositories.sqla_goal_repo import SqlAlchemyGoalRepository

router = APIRouter(prefix="/api/v1/onboarding/dashboard", tags=["onboarding_dashboard"])

def get_dashboard_service(session: TenantDBSession) -> DashboardService:
    return DashboardService(
        AccountRepository(session),
        TransactionRepository(session),
        SqlAlchemyProfileRepository(session),
        SqlAlchemyGoalRepository(session)
    )

@router.post("/save", response_model=DashboardDataResponse)
async def save_dashboard(
    request: DashboardSaveRequest,
    auth: CurrentUserPayload,
    service: DashboardService = Depends(get_dashboard_service)
):
    return await service.save_dashboard(request, int(auth.user_id), str(auth.tenant_id))

@router.get("", response_model=DashboardDataResponse)
async def get_dashboard(
    auth: CurrentUserPayload,
    service: DashboardService = Depends(get_dashboard_service)
):
    return await service.get_dashboard(int(auth.user_id))
