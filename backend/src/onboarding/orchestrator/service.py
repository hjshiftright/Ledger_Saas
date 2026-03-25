import json
from typing import Optional
from repositories.protocols import SettingsRepository
from common.enums import OnboardingStep, OnboardingStepStatus
from common.exceptions import OnboardingSequenceError
from common.events import event_bus
from .schemas import OrchestratorStateDTO, StepStateDTO

MANDATORY_STEPS = {
    OnboardingStep.PROFILE,
    OnboardingStep.COA_SETUP,
    OnboardingStep.ACCOUNT_SETUP
}

STEP_ORDER = [
    OnboardingStep.PROFILE,
    OnboardingStep.COA_SETUP,
    OnboardingStep.INSTITUTION_SETUP,
    OnboardingStep.ACCOUNT_SETUP,
    OnboardingStep.OPENING_BALANCES,
    OnboardingStep.GOAL_PLANNING,
    OnboardingStep.BUDGET_SETUP,
    OnboardingStep.RECURRING_SETUP,
    OnboardingStep.NETWORTH_REVIEW
]

class OrchestratorService:
    def __init__(self, settings_repo: SettingsRepository):
        self._settings = settings_repo

    def get_state(self) -> OrchestratorStateDTO:
        state_str = self._settings.get("onboarding.state")
        if state_str:
            raw_state = json.loads(state_str)
            steps = [StepStateDTO(**s) for s in raw_state.get("steps", [])]
            is_complete = raw_state.get("is_complete", False)
        else:
            steps = [StepStateDTO(step=s, status=OnboardingStepStatus.PENDING) for s in STEP_ORDER]
            is_complete = False

        completed_count = sum(1 for s in steps if s.status in [OnboardingStepStatus.COMPLETED, OnboardingStepStatus.SKIPPED])
        progress = int((completed_count / len(STEP_ORDER)) * 100)

        return OrchestratorStateDTO(
            is_complete=is_complete,
            progress_percentage=progress,
            steps=steps
        )

    def _save_state(self, state: OrchestratorStateDTO):
        raw = {"is_complete": state.is_complete, "steps": [s.model_dump() for s in state.steps]}
        self._settings.set("onboarding.state", json.dumps(raw))

    def start_step(self, step: OnboardingStep) -> OrchestratorStateDTO:
        state = self.get_state()
        
        idx = STEP_ORDER.index(step)
        if idx > 0:
            prev_status = state.steps[idx - 1].status
            if prev_status not in [OnboardingStepStatus.COMPLETED, OnboardingStepStatus.SKIPPED]:
                raise OnboardingSequenceError(f"Cannot start {step} before previous step is completed or skipped.")

        state.steps[idx].status = OnboardingStepStatus.IN_PROGRESS
        self._save_state(state)
        return self.get_state()

    def complete_step(self, step: OnboardingStep) -> OrchestratorStateDTO:
        state = self.get_state()
        idx = STEP_ORDER.index(step)
        if state.steps[idx].status == OnboardingStepStatus.PENDING:
             raise OnboardingSequenceError(f"Cannot complete {step} before starting it.")
        
        state.steps[idx].status = OnboardingStepStatus.COMPLETED
        self._save_state(state)
        return self.get_state()

    def skip_step(self, step: OnboardingStep) -> OrchestratorStateDTO:
        if step in MANDATORY_STEPS:
            raise OnboardingSequenceError(f"Cannot skip mandatory step: {step}.")
            
        state = self.get_state()
        idx = STEP_ORDER.index(step)
        state.steps[idx].status = OnboardingStepStatus.SKIPPED
        self._save_state(state)
        return self.get_state()

    def get_next_step(self) -> Optional[OnboardingStep]:
        state = self.get_state()
        for s in state.steps:
            if s.status in [OnboardingStepStatus.PENDING, OnboardingStepStatus.IN_PROGRESS]:
                return s.step
        return None

    def complete_onboarding(self) -> None:
        state = self.get_state()
        for step in MANDATORY_STEPS:
            idx = STEP_ORDER.index(step)
            if state.steps[idx].status != OnboardingStepStatus.COMPLETED:
                raise OnboardingSequenceError(f"Mandatory step {step} is not completed.")
                
        state.is_complete = True
        self._save_state(state)
        event_bus.publish("onboarding.completed", {})
