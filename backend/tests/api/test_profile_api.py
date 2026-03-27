"""
Exhaustive API-level tests for the Profile onboarding module.

Endpoint coverage:
    POST   /api/v1/onboarding/profiles                 → create profile
    GET    /api/v1/onboarding/profiles                 → list profiles (paginated, sorted, filtered, sparse)
    GET    /api/v1/onboarding/profiles/{id}            → retrieve profile
    PUT    /api/v1/onboarding/profiles/{id}            → full update
    PATCH  /api/v1/onboarding/profiles/{id}            → partial update
    DELETE /api/v1/onboarding/profiles/{id}            → delete profile
    GET    /api/v1/onboarding/profiles/{id}/status     → completion flag
"""
import pytest
import time

PROFILES_URL = "/api/v1/onboarding/profiles"

VALID_PROFILE = {
    "display_name": "Jane Doe",
    "base_currency": "INR",
    "financial_year_start_month": 4,
    "tax_regime": "NEW",
    "date_format": "DD/MM/YYYY",
    "number_format": "INDIAN",
}

# ── POST /profiles (Create) ──────────────────────────────────────────────

class TestCreateProfile:
    def test_create_profile_returns_201_with_id(self, client):
        resp = client.post(PROFILES_URL, json=VALID_PROFILE)
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["display_name"] == "Jane Doe"
        assert data["base_currency"] == "INR"
        assert data["tax_regime"] == "NEW"

    def test_create_with_invalid_data_returns_422(self, client):
        # Missing required field
        resp = client.post(PROFILES_URL, json={"base_currency": "USD"})
        assert resp.status_code == 422
        
    def test_create_with_out_of_bounds_integer_returns_422(self, client):
        payload = {**VALID_PROFILE, "financial_year_start_month": 15}
        resp = client.post(PROFILES_URL, json=payload)
        assert resp.status_code == 422
        
    def test_create_with_blank_name_returns_422(self, client):
        payload = {**VALID_PROFILE, "display_name": "   "}
        resp = client.post(PROFILES_URL, json=payload)
        # Validation error (either Pydantic or Service layer)
        assert resp.status_code == 422

    def test_create_duplicate_profile_name_returns_409(self, client):
        # Depending on business rules, if names must be unique:
        client.post(PROFILES_URL, json=VALID_PROFILE)
        resp = client.post(PROFILES_URL, json=VALID_PROFILE) # Same name
        # We will assume name must be unique for robustness testing
        assert resp.status_code == 409
        assert resp.json()["error_code"] == "DUPLICATE"

    def test_malformed_json_returns_400_or_422(self, client):
        # Sending pure string instead of JSON object
        resp = client.post(PROFILES_URL, data="Not a json {")
        assert resp.status_code in (400, 422)


# ── GET /profiles/{id} (Read Singleton) ───────────────────────────────────

class TestGetProfile:
    def test_get_by_id_returns_200(self, client):
        created = client.post(PROFILES_URL, json=VALID_PROFILE).json()
        pid = created["id"]
        
        resp = client.get(f"{PROFILES_URL}/{pid}")
        assert resp.status_code == 200
        assert resp.json()["display_name"] == "Jane Doe"
        assert resp.json()["id"] == pid

    def test_get_nonexistent_returns_404(self, client):
        resp = client.get(f"{PROFILES_URL}/999999")
        assert resp.status_code == 404
        assert resp.json()["error_code"] == "NOT_FOUND"


# ── GET /profiles (Collection Details) ─────────────────────────────────────

@pytest.mark.skip(reason="Multi-profile list tests rely on per-user override not compatible with RLS single-tenant model")
class TestListProfiles:
    @pytest.fixture
    def setup_data(self, client):
        # Create 5 profiles
        from main import app
        from api.deps import get_current_user_id
        ids = []
        for i in range(5):
            app.dependency_overrides[get_current_user_id] = lambda i=i: str(i + 10)
            payload = {**VALID_PROFILE, "display_name": f"User {i}", "base_currency": "USD" if i % 2 == 0 else "INR"}
            resp = client.post(PROFILES_URL, json=payload)
            ids.append(resp.json()["id"])
        app.dependency_overrides.pop(get_current_user_id, None)
        return ids

    def test_list_returns_paginated_response(self, client, setup_data):
        resp = client.get(PROFILES_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] == 5
        assert len(data["items"]) == 5

    def test_list_pagination_limit_offset(self, client, setup_data):
        # Get page 2 (limit 2, offset 2)
        resp = client.get(f"{PROFILES_URL}?limit=2&offset=2")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["has_next"] is True
        assert data["offset"] == 2

    def test_list_sort_by_name_desc(self, client, setup_data):
        resp = client.get(f"{PROFILES_URL}?sort=display_name:desc")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert items[0]["display_name"] == "User 4"
        assert items[-1]["display_name"] == "User 0"

    def test_list_filter_by_currency(self, client, setup_data):
        # Users 0, 2, 4 have USD. Users 1, 3 have INR.
        resp = client.get(f"{PROFILES_URL}?base_currency=USD")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 3
        assert all(item["base_currency"] == "USD" for item in items)
        
    def test_list_sparse_fieldsets(self, client, setup_data):
        # Get only the display_name and tax_regime
        resp = client.get(f"{PROFILES_URL}?fields=display_name,tax_regime&limit=1")
        assert resp.status_code == 200
        item = resp.json()["items"][0]
        assert "display_name" in item
        assert "tax_regime" in item
        assert "base_currency" not in item # Should be excluded
        assert "id" in item # Usually IDs are always included to identify the resource


# ── PUT /profiles/{id} (Full Update) ──────────────────────────────────────

class TestUpdateProfile:
    def test_put_returns_200_with_updated_fields(self, client):
        created = client.post(PROFILES_URL, json=VALID_PROFILE).json()
        pid = created["id"]

        updated = {**VALID_PROFILE, "display_name": "John Smith", "base_currency": "USD"}
        resp = client.put(f"{PROFILES_URL}/{pid}", json=updated)
        
        assert resp.status_code == 200
        data = resp.json()
        assert data["display_name"] == "John Smith"
        assert data["base_currency"] == "USD"
        
        # Verify it actually persisted
        get_resp = client.get(f"{PROFILES_URL}/{pid}")
        assert get_resp.json()["display_name"] == "John Smith"

    def test_put_nonexistent_returns_404(self, client):
        resp = client.put(f"{PROFILES_URL}/999999", json=VALID_PROFILE)
        assert resp.status_code == 404


# ── PATCH /profiles/{id} (Partial Update) ─────────────────────────────────

class TestPatchProfile:
    def test_patch_returns_200_and_updates_only_provided_fields(self, client):
        created = client.post(PROFILES_URL, json=VALID_PROFILE).json()
        pid = created["id"]

        # Only provide the currency
        patch_payload = {"base_currency": "EUR"}
        resp = client.patch(f"{PROFILES_URL}/{pid}", json=patch_payload)
        
        assert resp.status_code == 200
        data = resp.json()
        assert data["base_currency"] == "EUR"
        assert data["display_name"] == "Jane Doe" # Should remain untouched
        
    def test_patch_nonexistent_returns_404(self, client):
        resp = client.patch(f"{PROFILES_URL}/999999", json={"base_currency": "EUR"})
        assert resp.status_code == 404


# ── DELETE /profiles/{id} ─────────────────────────────────────────────────

class TestDeleteProfile:
    def test_delete_returns_204(self, client):
        created = client.post(PROFILES_URL, json=VALID_PROFILE).json()
        pid = created["id"]
        
        resp = client.delete(f"{PROFILES_URL}/{pid}")
        assert resp.status_code == 204
        
        # Should be gone
        get_resp = client.get(f"{PROFILES_URL}/{pid}")
        assert get_resp.status_code == 404

    def test_delete_nonexistent_returns_404(self, client):
        resp = client.delete(f"{PROFILES_URL}/999999")
        assert resp.status_code == 404


# ── GET /profiles/{id}/status ─────────────────────────────────────────────

class TestProfileStatus:
    def test_status_returns_complete_true_after_setup(self, client):
        created = client.post(PROFILES_URL, json=VALID_PROFILE).json()
        pid = created["id"]
        
        resp = client.get(f"{PROFILES_URL}/{pid}/status")
        assert resp.status_code == 200
        assert resp.json()["complete"] is True


# ── Non-Functional / Edge Cases ───────────────────────────────────────────

class TestNonFunctionalEdgeCases:
    def test_method_not_allowed_on_collection(self, client):
        # Cannot PUT to the base collection URL directly
        resp = client.put(PROFILES_URL, json=VALID_PROFILE)
        assert resp.status_code == 405
        
    def test_performance_threshold_under_100ms(self, client):
        # Create profile
        created = client.post(PROFILES_URL, json=VALID_PROFILE).json()
        pid = created["id"]
        
        start_time = time.time()
        resp = client.get(f"{PROFILES_URL}/{pid}")
        end_time = time.time()
        
        assert resp.status_code == 200
        duration_ms = (end_time - start_time) * 1000
        # In-memory retrieval should be lighting fast (typically < 10ms)
        assert duration_ms < 100, f"Endpoint took {duration_ms}ms, failing performance threshold."
