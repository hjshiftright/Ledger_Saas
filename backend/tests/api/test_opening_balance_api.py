"""
API-level tests for the Opening Balance onboarding module.

Endpoint coverage:
    POST /api/v1/onboarding/opening-balances       → single entry setup
    POST /api/v1/onboarding/opening-balances/bulk  → bulk entry setup
"""
import pytest
from datetime import date

OB_URL = "/api/v1/onboarding/opening-balances"


class TestSingleOpeningBalance:
    def test_set_opening_balance_returns_201(self, seeded_client):
        # We need an account to set a balance for. seeded_client has a profile and COA.
        # Let's assume asset account 1000 or similar exists; we will just use account_id=1 
        # (Assuming it's valid enough for the router to accept down to the service layer mock or real behavior)
        
        # Real in-memory repos require the account to exist actually. Let's create one.
        cat_resp = seeded_client.post("/api/v1/onboarding/coa/categories", json={"parent_id": 1, "name": "Test Asset"})
        acc_id = cat_resp.json()["id"]

        payload = {
            "account_id": acc_id,
            "amount": 1500.50,
            "as_of_date": date.today().isoformat()
        }
        resp = seeded_client.post(OB_URL, json=payload)
        assert resp.status_code == 201
        assert resp.json()["account_id"] == acc_id
        assert resp.json()["amount"] == 1500.50

    def test_set_opening_balance_invalid_account_returns_404(self, seeded_client):
        payload = {
            "account_id": 999999,
            "amount": 100.0,
            "as_of_date": date.today().isoformat()
        }
        resp = seeded_client.post(OB_URL, json=payload)
        assert resp.status_code == 404


class TestBulkOpeningBalance:
    def test_bulk_opening_balances_returns_201_and_summary(self, seeded_client):
        cat1 = seeded_client.post("/api/v1/onboarding/coa/categories", json={"parent_id": 1, "name": "Asset 1"}).json()
        cat2 = seeded_client.post("/api/v1/onboarding/coa/categories", json={"parent_id": 1, "name": "Asset 2"}).json()

        payload = {
            "balances": [
                {
                    "account_id": cat1["id"],
                    "amount": 1000.0,
                    "as_of_date": date.today().isoformat()
                },
                {
                    "account_id": cat2["id"],
                    "amount": 2000.0,
                    "as_of_date": date.today().isoformat()
                }
            ]
        }
        resp = seeded_client.post(f"{OB_URL}/bulk", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["total_processed"] == 2
        assert len(data["successful_entries"]) == 2
        assert len(data["failed_entries"]) == 0

    def test_bulk_opening_balances_with_some_invalid_returns_207_multi_status(self, seeded_client):
        cat1 = seeded_client.post("/api/v1/onboarding/coa/categories", json={"parent_id": 1, "name": "Asset 3"}).json()

        payload = {
            "balances": [
                {
                    "account_id": cat1["id"],
                    "amount": 1000.0,
                    "as_of_date": date.today().isoformat()
                },
                {
                    "account_id": 999999,  # Invalid
                    "amount": 2000.0,
                    "as_of_date": date.today().isoformat()
                }
            ]
        }
        resp = seeded_client.post(f"{OB_URL}/bulk", json=payload)
        # 207 Multi-Status is best practice for partial success in bulk APIs
        assert resp.status_code == 207
        data = resp.json()
        assert data["total_processed"] == 2
        assert len(data["successful_entries"]) == 1
        assert len(data["failed_entries"]) == 1
