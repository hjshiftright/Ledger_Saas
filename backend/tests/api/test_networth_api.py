"""
API-level tests for the Net Worth onboarding module.

Endpoint coverage:
    GET /api/v1/onboarding/networth    → compute current net worth snapshot
"""
import pytest
from datetime import date

NW_URL = "/api/v1/onboarding/networth"


class TestNetWorthAPI:
    def test_get_net_worth_returns_200(self, seeded_client):
        # We need an opening balance to have non-zero net worth but even 0 net worth is valid 
        # as long as the endpoint works.
        
        # In a real scenario we'd query params like ?as_of_date=2024-01-01
        # Let's test the endpoint without explicit date (defaults to today)
        resp = seeded_client.get(NW_URL)
        assert resp.status_code == 200
        
        data = resp.json()
        assert "total_assets" in data
        assert "total_liabilities" in data
        assert "net_worth" in data
        assert "as_of_date" in data
        assert "breakdown" in data

    def test_get_net_worth_with_date_returns_200(self, seeded_client):
        # Test Date query parameter
        test_date = date.today().isoformat()
        resp = seeded_client.get(f"{NW_URL}?as_of_date={test_date}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["as_of_date"] == test_date
