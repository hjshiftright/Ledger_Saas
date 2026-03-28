"""
API-level tests for POST /api/v1/onboarding/dashboard/save
and  GET  /api/v1/onboarding/dashboard
"""
import pytest

DASHBOARD_SAVE_URL = "/api/v1/onboarding/dashboard/save"
DASHBOARD_GET_URL  = "/api/v1/onboarding/dashboard"

# Minimal valid payload matching DashboardSaveRequest
MINIMAL_PAYLOAD = {
    "name": "Test User",
    "age": 30,
    "monthly_income": 100000,
    "monthly_expenses": 50000,
    "assets": {
        "banks": [{"id": 1, "name": "HDFC Savings", "balance": 200000}],
    },
    "liabilities": {},
    "goals": [],
}

PAYLOAD_WITH_GOALS = {
    "name": "Priya",
    "age": 28,
    "monthly_income": 0,
    "monthly_expenses": 60000,
    "assets": {
        "banks": [{"id": 1, "name": "SBI Salary", "balance": 100000}],
        "providentFund": [{"id": "epf", "name": "EPF", "balance": 850000}],
    },
    "liabilities": {
        "creditCards": [{"id": 1, "name": "HDFC Regalia", "balance": 15000}],
    },
    "goals": [
        {"id": "emergency", "name": "Emergency Fund", "target": 360000, "years": 1, "current": 0},
        {"id": "retire",    "name": "Retirement",     "target": 5000000, "years": 32, "current": 850000},
    ],
}


class TestDashboardSave:
    def test_save_returns_200_with_response(self, seeded_client):
        resp = seeded_client.post(DASHBOARD_SAVE_URL, json=MINIMAL_PAYLOAD)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["name"] == "Test User"
        assert "assets" in data
        assert "liabilities" in data
        assert "goals" in data

    def test_save_persists_bank_account(self, seeded_client):
        resp = seeded_client.post(DASHBOARD_SAVE_URL, json=MINIMAL_PAYLOAD)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        banks = data["assets"].get("banks", [])
        assert len(banks) == 1
        assert banks[0]["name"] == "HDFC Savings"
        assert banks[0]["balance"] == 200000.0

    def test_save_with_goals(self, seeded_client):
        resp = seeded_client.post(DASHBOARD_SAVE_URL, json=PAYLOAD_WITH_GOALS)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert len(data["goals"]) == 2

    def test_save_with_liability(self, seeded_client):
        resp = seeded_client.post(DASHBOARD_SAVE_URL, json=PAYLOAD_WITH_GOALS)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        cards = data["liabilities"].get("creditCards", [])
        assert len(cards) == 1
        assert cards[0]["balance"] == 15000.0

    def test_save_idempotent_on_second_call(self, seeded_client):
        seeded_client.post(DASHBOARD_SAVE_URL, json=MINIMAL_PAYLOAD)
        resp = seeded_client.post(DASHBOARD_SAVE_URL, json=MINIMAL_PAYLOAD)
        assert resp.status_code == 200, resp.text

    def test_save_missing_required_field_returns_422(self, seeded_client):
        bad = {k: v for k, v in MINIMAL_PAYLOAD.items() if k != "name"}
        resp = seeded_client.post(DASHBOARD_SAVE_URL, json=bad)
        assert resp.status_code == 422


class TestDashboardGet:
    def test_get_returns_200_after_save(self, seeded_client):
        seeded_client.post(DASHBOARD_SAVE_URL, json=MINIMAL_PAYLOAD)
        resp = seeded_client.get(DASHBOARD_GET_URL)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "assets" in data
        assert "liabilities" in data

    def test_get_returns_200_without_prior_save(self, seeded_client):
        # Should return empty/default structure, not 404
        resp = seeded_client.get(DASHBOARD_GET_URL)
        assert resp.status_code == 200, resp.text
