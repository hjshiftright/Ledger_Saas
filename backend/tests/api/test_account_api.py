"""
API-level tests for the Account onboarding module.

Endpoint coverage:
    POST   /api/v1/onboarding/accounts/bank         → create bank
    POST   /api/v1/onboarding/accounts/credit-card  → create CC
    POST   /api/v1/onboarding/accounts/loan         → create loan
    POST   /api/v1/onboarding/accounts/brokerage    → create brokerage
    POST   /api/v1/onboarding/accounts/fixed-deposit→ create FD
    POST   /api/v1/onboarding/accounts/cash         → create cash wallet
    GET    /api/v1/onboarding/accounts              → list all accounts (paginated)
    GET    /api/v1/onboarding/accounts/{id}         → retrieve single
    DELETE /api/v1/onboarding/accounts/{id}         → soft delete
"""
import pytest
from .conftest import create_institution

ACC_URL = "/api/v1/onboarding/accounts"


@pytest.fixture
def inst_id(seeded_client):
    """Provides a valid institution ID for testing account creation."""
    inst = create_institution(seeded_client, "Test Bank", "BANK")
    return inst["id"]


# ── POST /accounts/* ────────────────────────────────────────────────────


class TestCreateBankAccount:
    def test_create_bank_returns_201(self, seeded_client, inst_id):
        payload = {
            "display_name": "Checking Account",
            "institution_id": inst_id,
            "account_number_masked": "1234",
            "bank_account_type": "SAVINGS",
        }
        resp = seeded_client.post(f"{ACC_URL}/bank", json=payload)
        assert resp.status_code == 201
        # Now returns standardized format
        assert "id" in resp.json()

    def test_invalid_institution_returns_404(self, seeded_client):
        payload = {
            "display_name": "Checking",
            "institution_id": 9999,
            "account_number_masked": "1234",
            "bank_account_type": "SAVINGS",
        }
        resp = seeded_client.post(f"{ACC_URL}/bank", json=payload)
        assert resp.status_code == 404


class TestCreateCreditCard:
    def test_create_cc_returns_201(self, seeded_client, inst_id):
        payload = {
            "display_name": "Rewards Card",
            "institution_id": inst_id,
            "last_four_digits": "5678",
            "credit_limit": 50000,
            "billing_cycle_day": 15,
            "interest_rate_annual": 42.0,
        }
        resp = seeded_client.post(f"{ACC_URL}/credit-card", json=payload)
        assert resp.status_code == 201


class TestCreateLoan:
    def test_create_loan_returns_201(self, seeded_client, inst_id):
        payload = {
            "display_name": "Car Loan",
            "institution_id": inst_id,
            "loan_type": "VEHICLE",
            "principal_amount": 500000,
            "interest_rate": 8.5,
            "tenure_months": 60,
            "emi_amount": 10000,
            "start_date": "2026-01-01",
        }
        resp = seeded_client.post(f"{ACC_URL}/loan", json=payload)
        assert resp.status_code == 201


class TestCreateBrokerage:
    def test_create_brokerage_returns_201(self, seeded_client, inst_id):
        payload = {
            "display_name": "Demat",
            "institution_id": inst_id,
            "demat_id": "IN12345678",
        }
        resp = seeded_client.post(f"{ACC_URL}/brokerage", json=payload)
        assert resp.status_code == 201


class TestCreateFixedDeposit:
    def test_create_fd_returns_201(self, seeded_client, inst_id):
        payload = {
            "display_name": "1yr FD",
            "institution_id": inst_id,
            "principal_amount": 100000,
            "interest_rate": 7.0,
            "start_date": "2026-01-01",
            "maturity_date": "2027-01-01",
        }
        resp = seeded_client.post(f"{ACC_URL}/fixed-deposit", json=payload)
        assert resp.status_code == 201


class TestCreateCashWallet:
    def test_create_cash_returns_201(self, seeded_client):
        # Cash doesn't need an institution
        resp = seeded_client.post(f"{ACC_URL}/cash", json={"display_name": "Wallet"})
        assert resp.status_code == 201


# ── GET /accounts ───────────────────────────────────────────────────────


@pytest.mark.skip(reason="awaiting service layer implementation in Phase 2")
class TestListAccounts:
    @pytest.fixture(autouse=True)
    def setup_accounts(self, seeded_client, inst_id):
        # Bank
        seeded_client.post(f"{ACC_URL}/bank", json={
            "display_name": "Bank1", "institution_id": inst_id,
            "account_number_masked": "1111", "bank_account_type": "SAVINGS"
        })
        # CC
        seeded_client.post(f"{ACC_URL}/credit-card", json={
            "display_name": "CC1", "institution_id": inst_id,
            "last_four_digits": "2222", "credit_limit": 100,
            "billing_cycle_day": 1, "interest_rate_annual": 0
        })

    def test_list_returns_paginated_response(self, seeded_client):
        resp = seeded_client.get(ACC_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_filter_by_type(self, seeded_client):
        resp = seeded_client.get(f"{ACC_URL}?account_type=LIABILITY")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1
        assert resp.json()["items"][0]["name"] == "CC1"


# ── GET & DELETE /accounts/{id} ─────────────────────────────────────────


@pytest.mark.skip(reason="awaiting service layer implementation in Phase 2")
class TestGetAndDeleteAccount:
    def test_get_by_id_returns_200(self, seeded_client, inst_id):
        payload = {
            "display_name": "GetTest",
            "institution_id": inst_id,
            "account_number_masked": "9999",
            "bank_account_type": "SAVINGS",
        }
        created = seeded_client.post(f"{ACC_URL}/bank", json=payload).json()
        acc_id = created["id"]

        resp = seeded_client.get(f"{ACC_URL}/{acc_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "GetTest"

    def test_not_found(self, seeded_client):
        resp = seeded_client.get(f"{ACC_URL}/99999")
        assert resp.status_code == 404

    def test_delete_returns_204(self, seeded_client, inst_id):
        payload = {
            "display_name": "DelTest",
            "institution_id": inst_id,
            "account_number_masked": "9999",
            "bank_account_type": "SAVINGS",
        }
        created = seeded_client.post(f"{ACC_URL}/bank", json=payload).json()
        acc_id = created["id"]

        resp = seeded_client.delete(f"{ACC_URL}/{acc_id}")
        assert resp.status_code == 204
