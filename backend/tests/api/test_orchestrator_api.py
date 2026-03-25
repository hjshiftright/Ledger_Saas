"""
API-level tests for the Onboarding Orchestrator module.

Endpoint coverage:
    GET  /api/v1/onboarding/state          → retrieve current step and completion status
    POST /api/v1/onboarding/start          → set up basic initial onboarding data
    POST /api/v1/onboarding/steps/complete → complete specific step
    POST /api/v1/onboarding/steps/skip     → skip optional step
    POST /api/v1/onboarding/complete       → mark entire onboarding flow as done
"""
import pytest
from unittest.mock import patch, MagicMock

ORCH_URL = "/api/v1/onboarding"


class TestOrchestratorAPI:
    def test_get_state_returns_200(self, client):
        resp = client.get(f"{ORCH_URL}/state")
        assert resp.status_code == 200
        
        data = resp.json()
        assert "current_step" in data
        assert "is_completed" in data
        assert "completed_steps" in data

    def test_start_onboarding_returns_200(self, client):
        # Starts the process - sets current step to PROFILE typically
        resp = client.post(f"{ORCH_URL}/start")
        assert resp.status_code == 200
        
        data = resp.json()
        assert data["current_step"] == "PROFILE"

    def test_complete_step_returns_200(self, client):
        payload = {"step_name": "PROFILE"}
        resp = client.post(f"{ORCH_URL}/steps/complete", json=payload)
        assert resp.status_code == 200
        assert "PROFILE" in resp.json()["completed_steps"]

    def test_skip_step_returns_200(self, client):
        payload = {"step_name": "OPENING_BALANCE"}
        resp = client.post(f"{ORCH_URL}/steps/skip", json=payload)
        assert resp.status_code == 200

    def test_complete_onboarding_returns_200(self, client):
        # We assume validation in service might fail if steps aren't actually done,
        # but the test setup is just checking router and basic mocking logic in tests or if the logic allows forcing.
        # Given this is TDD, let's see how the base implementation behaves. It should probably return 200.
        resp = client.post(f"{ORCH_URL}/complete")
        assert resp.status_code == 200
        assert resp.json()["is_completed"] is True
