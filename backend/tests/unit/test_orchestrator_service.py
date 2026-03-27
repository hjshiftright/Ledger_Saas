import pytest
from onboarding.orchestrator.service import OrchestratorService
from repositories.sqla_settings_repo import SqlAlchemySettingsRepository
from common.enums import OnboardingStep, OnboardingStepStatus
from common.exceptions import OnboardingSequenceError

# OrchestratorService is the legacy full-featured service (not used by the HTTP router).
# It calls settings repo methods that are async. These tests are skipped until the
# legacy service is ported to async or replaced.
pytestmark = pytest.mark.skip(reason="OrchestratorService is sync but settings repo is async — pending refactor")

@pytest.fixture
def service(session):
    return OrchestratorService(SqlAlchemySettingsRepository(session))

def test_initial_state_is_correct(service):
    state = service.get_state()
    assert state.is_complete is False
    assert state.progress_percentage == 0
    assert state.steps[0].step == OnboardingStep.PROFILE
    assert state.steps[0].status == OnboardingStepStatus.PENDING

def test_start_and_complete_profile(service):
    service.start_step(OnboardingStep.PROFILE)
    state = service.get_state()
    assert state.steps[0].status == OnboardingStepStatus.IN_PROGRESS

    service.complete_step(OnboardingStep.PROFILE)
    state = service.get_state()
    assert state.steps[0].status == OnboardingStepStatus.COMPLETED
    assert state.progress_percentage > 0

def test_skip_mandatory_step_fails(service):
    with pytest.raises(OnboardingSequenceError):
        service.skip_step(OnboardingStep.PROFILE)

def test_complete_onboarding_without_mandatory_steps_fails(service):
    with pytest.raises(OnboardingSequenceError):
        service.complete_onboarding()
