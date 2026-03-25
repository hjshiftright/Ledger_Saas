"""
API-level tests for the Institution onboarding module.

Endpoint coverage:
    POST   /api/v1/onboarding/institutions               → create institution
    GET    /api/v1/onboarding/institutions/{id}          → retrieve institution
    GET    /api/v1/onboarding/institutions               → list (paginated, sorted, filtered)
    PUT    /api/v1/onboarding/institutions/{id}          → full update
    DELETE /api/v1/onboarding/institutions/{id}          → soft delete
"""
import pytest


INST_URL = "/api/v1/onboarding/institutions"

VALID_INST = {
    "name": "State Bank of India",
    "institution_type": "BANK",
    "website_url": "https://sbi.co.in",
}


# ── POST /institutions ──────────────────────────────────────────────────


class TestCreateInstitution:
    def test_create_returns_201_with_id(self, client):
        resp = client.post(INST_URL, json=VALID_INST)
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["name"] == VALID_INST["name"]
        assert data["institution_type"] == VALID_INST["institution_type"]

    def test_create_duplicate_returns_409(self, client):
        client.post(INST_URL, json=VALID_INST)
        resp = client.post(INST_URL, json=VALID_INST)
        assert resp.status_code == 409
        assert resp.json()["error_code"] == "DUPLICATE"

    def test_create_with_invalid_type_returns_422(self, client):
        payload = {**VALID_INST, "institution_type": "UNKNOWN_TYPE"}
        resp = client.post(INST_URL, json=payload)
        assert resp.status_code == 422


# ── GET /institutions/{id} ──────────────────────────────────────────────


class TestGetInstitution:
    def test_get_by_id_returns_200(self, client):
        created = client.post(INST_URL, json=VALID_INST).json()
        inst_id = created["id"]

        resp = client.get(f"{INST_URL}/{inst_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == inst_id
        assert resp.json()["name"] == VALID_INST["name"]

    def test_get_nonexistent_returns_404(self, client):
        resp = client.get(f"{INST_URL}/9999")
        assert resp.status_code == 404
        assert resp.json()["error_code"] == "NOT_FOUND"


# ── GET /institutions (List) ────────────────────────────────────────────


class TestListInstitutions:
    @pytest.fixture(autouse=True)
    def setup_data(self, client):
        client.post(INST_URL, json={"name": "Bank A", "institution_type": "BANK"})
        client.post(INST_URL, json={"name": "Broker B", "institution_type": "BROKERAGE"})
        client.post(INST_URL, json={"name": "Bank C", "institution_type": "BANK"})

    def test_list_returns_paginated_response(self, client):
        resp = client.get(INST_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3
        assert data["page"] == 1
        assert "offset" in data
        assert "has_next" in data

    def test_list_page_2(self, client):
        resp = client.get(f"{INST_URL}?page=2&size=2")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["page"] == 2
        assert data["offset"] == 2
        assert data["has_next"] is False
        assert data["has_previous"] is True

    def test_list_with_offset_and_limit_overrides_page(self, client):
        # We can pass offset=1, limit=1
        resp = client.get(f"{INST_URL}?offset=1&limit=1")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Broker B"  # 2nd item created
        assert data["offset"] == 1
        assert data["has_next"] is True

    def test_list_sort_by_name_asc(self, client):
        resp = client.get(f"{INST_URL}?sort_by=name&sort_desc=false")
        assert resp.status_code == 200
        names = [i["name"] for i in resp.json()["items"]]
        assert names == ["Bank A", "Bank C", "Broker B"]

    def test_list_sort_by_name_desc(self, client):
        resp = client.get(f"{INST_URL}?sort_by=name&sort_desc=true")
        assert resp.status_code == 200
        names = [i["name"] for i in resp.json()["items"]]
        assert names == ["Broker B", "Bank C", "Bank A"]

    def test_list_filter_by_type(self, client):
        resp = client.get(f"{INST_URL}?institution_type=BROKERAGE")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Broker B"

    def test_list_search_by_name(self, client):
        resp = client.get(f"{INST_URL}?search=bank")
        assert resp.status_code == 200
        assert resp.json()["total"] == 2


# ── PUT /institutions/{id} ──────────────────────────────────────────────


class TestUpdateInstitution:
    def test_put_returns_200_with_updated_fields(self, client):
        created = client.post(INST_URL, json=VALID_INST).json()
        inst_id = created["id"]

        updated_payload = {**VALID_INST, "name": "SBI Updated", "website_url": "https://new.com"}
        resp = client.put(f"{INST_URL}/{inst_id}", json=updated_payload)
        assert resp.status_code == 200
        assert resp.json()["name"] == "SBI Updated"
        assert resp.json()["website_url"] == "https://new.com"

        # Verify it persisted
        get_resp = client.get(f"{INST_URL}/{inst_id}")
        assert get_resp.json()["name"] == "SBI Updated"

    def test_put_nonexistent_returns_404(self, client):
        resp = client.put(f"{INST_URL}/9999", json=VALID_INST)
        assert resp.status_code == 404


# ── DELETE /institutions/{id} ───────────────────────────────────────────


@pytest.mark.skip(reason="awaiting service layer implementation in Phase 2")
class TestDeleteInstitution:
    def test_delete_returns_204(self, client):
        created = client.post(INST_URL, json=VALID_INST).json()
        inst_id = created["id"]

        resp = client.delete(f"{INST_URL}/{inst_id}")
        assert resp.status_code == 204

        # Verify it's gone
        get_resp = client.get(f"{INST_URL}/{inst_id}")
        assert get_resp.status_code == 404

    def test_delete_nonexistent_returns_404(self, client):
        resp = client.delete(f"{INST_URL}/9999")
        assert resp.status_code == 404
