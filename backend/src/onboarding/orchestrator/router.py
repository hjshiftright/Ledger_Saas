import json
from fastapi import APIRouter, Depends

from api.deps import TenantDBSession
from repositories.sqla_settings_repo import SqlAlchemySettingsRepository
from .schemas import OnboardingStateDTO, StepRequestDTO

router = APIRouter(prefix="/api/v1/onboarding", tags=["orchestrator"])


class _SimpleState:
    """Thin wrapper that stores onboarding state as JSON in app_settings."""

    def __init__(self, repo: SqlAlchemySettingsRepository):
        self._repo = repo

    async def get_state(self) -> OnboardingStateDTO:
        curr = await self._repo.get("onboarding.current_step") or "PROFILE"
        completed_raw = await self._repo.get("onboarding.completed_steps")
        completed = json.loads(completed_raw) if completed_raw else []
        is_done_raw = await self._repo.get("onboarding.is_completed")
        is_done = json.loads(is_done_raw) if is_done_raw else False
        return OnboardingStateDTO(current_step=curr, completed_steps=completed, is_completed=bool(is_done))

    async def start(self) -> OnboardingStateDTO:
        await self._repo.set("onboarding.current_step", "PROFILE")
        await self._repo.set("onboarding.completed_steps", json.dumps([]))
        await self._repo.set("onboarding.is_completed", json.dumps(False))
        return await self.get_state()

    async def complete_step(self, step: str) -> OnboardingStateDTO:
        completed_raw = await self._repo.get("onboarding.completed_steps")
        completed = json.loads(completed_raw) if completed_raw else []
        if step not in completed:
            completed.append(step)
            await self._repo.set("onboarding.completed_steps", json.dumps(completed))
        return await self.get_state()

    async def set_done(self) -> OnboardingStateDTO:
        await self._repo.set("onboarding.is_completed", json.dumps(True))
        return await self.get_state()


def get_orchestrator_service(session: TenantDBSession) -> _SimpleState:
    return _SimpleState(SqlAlchemySettingsRepository(session))


@router.get("/state", response_model=OnboardingStateDTO)
async def get_state(service: _SimpleState = Depends(get_orchestrator_service)):
    return await service.get_state()

@router.post("/start", response_model=OnboardingStateDTO)
async def start_onboarding(service: _SimpleState = Depends(get_orchestrator_service)):
    return await service.start()

@router.post("/steps/complete", response_model=OnboardingStateDTO)
async def complete_step(req: StepRequestDTO, service: _SimpleState = Depends(get_orchestrator_service)):
    return await service.complete_step(req.step_name)

@router.post("/steps/skip", response_model=OnboardingStateDTO)
async def skip_step(req: StepRequestDTO, service: _SimpleState = Depends(get_orchestrator_service)):
    return await service.complete_step(req.step_name)

@router.post("/complete", response_model=OnboardingStateDTO)
async def complete_onboarding(service: _SimpleState = Depends(get_orchestrator_service)):
    return await service.set_done()
