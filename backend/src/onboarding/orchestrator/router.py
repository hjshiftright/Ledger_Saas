import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import DBSession
from repositories.sqla_settings_repo import SqlAlchemySettingsRepository
from .schemas import OnboardingStateDTO, StepRequestDTO

router = APIRouter(prefix="/api/v1/onboarding", tags=["orchestrator"])


class _SimpleState:
    """Thin wrapper that stores onboarding state as JSON in app_settings."""

    def __init__(self, repo: SqlAlchemySettingsRepository):
        self._repo = repo

    def get_state(self) -> OnboardingStateDTO:
        curr = self._repo.get("onboarding.current_step") or "PROFILE"
        completed_raw = self._repo.get("onboarding.completed_steps")
        completed = json.loads(completed_raw) if completed_raw else []
        is_done_raw = self._repo.get("onboarding.is_completed")
        is_done = json.loads(is_done_raw) if is_done_raw else False
        return OnboardingStateDTO(current_step=curr, completed_steps=completed, is_completed=bool(is_done))

    def start(self) -> OnboardingStateDTO:
        self._repo.set("onboarding.current_step", "PROFILE")
        self._repo.set("onboarding.completed_steps", json.dumps([]))
        self._repo.set("onboarding.is_completed", json.dumps(False))
        return self.get_state()

    def complete_step(self, step: str) -> OnboardingStateDTO:
        completed_raw = self._repo.get("onboarding.completed_steps")
        completed = json.loads(completed_raw) if completed_raw else []
        if step not in completed:
            completed.append(step)
            self._repo.set("onboarding.completed_steps", json.dumps(completed))
        return self.get_state()

    def set_done(self) -> OnboardingStateDTO:
        self._repo.set("onboarding.is_completed", json.dumps(True))
        return self.get_state()


def get_orchestrator_service(session: DBSession) -> _SimpleState:
    return _SimpleState(SqlAlchemySettingsRepository(session))


@router.get("/state", response_model=OnboardingStateDTO)
def get_state(service: _SimpleState = Depends(get_orchestrator_service)):
    return service.get_state()

@router.post("/start", response_model=OnboardingStateDTO)
def start_onboarding(service: _SimpleState = Depends(get_orchestrator_service)):
    return service.start()

@router.post("/steps/complete", response_model=OnboardingStateDTO)
def complete_step(req: StepRequestDTO, service: _SimpleState = Depends(get_orchestrator_service)):
    return service.complete_step(req.step_name)

@router.post("/steps/skip", response_model=OnboardingStateDTO)
def skip_step(req: StepRequestDTO, service: _SimpleState = Depends(get_orchestrator_service)):
    return service.complete_step(req.step_name)

@router.post("/complete", response_model=OnboardingStateDTO)
def complete_onboarding(service: _SimpleState = Depends(get_orchestrator_service)):
    return service.set_done()
