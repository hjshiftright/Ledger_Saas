from typing import List, Optional
from pydantic import BaseModel
from common.enums import OnboardingStep, OnboardingStepStatus


class StepRequestDTO(BaseModel):
    step_name: str


class OnboardingStateDTO(BaseModel):
    current_step: str
    is_completed: bool
    completed_steps: List[str]


class StepStateDTO(BaseModel):
    step: OnboardingStep
    status: OnboardingStepStatus


class OrchestratorStateDTO(BaseModel):
    is_complete: bool
    progress_percentage: int
    steps: List[StepStateDTO]
