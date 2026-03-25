"""
API-level tests for the Chart of Accounts (COA) onboarding module.

Endpoint coverage:
    POST   /api/v1/onboarding/coa/initialize    → create default COA tree
    GET    /api/v1/onboarding/coa/tree          → retrieve full COA hierarchy
    GET    /api/v1/onboarding/coa/accounts/{id} → retrieve single COA node
    POST   /api/v1/onboarding/coa/categories    → create custom category
    PUT    /api/v1/onboarding/coa/accounts/{id}/rename → rename account
    DELETE /api/v1/onboarding/coa/accounts/{id} → deactivate/delete account
    GET    /api/v1/onboarding/coa/status        → completion flag 
"""
import pytest

COA_URL = "/api/v1/onboarding/coa"


# ── POST /coa/initialize ────────────────────────────────────────────────


class TestInitializeCOA:
    def test_initialize_returns_201(self, client):
        resp = client.post(f"{COA_URL}/initialize")
        assert resp.status_code == 201
        data = resp.json()
        assert len(data) > 0
        assert data[0]["code"] == "1000"  # Assets typically

    def test_initialize_twice_returns_409(self, client):
        client.post(f"{COA_URL}/initialize")
        resp = client.post(f"{COA_URL}/initialize")
        # Can't initialise if already initialised
        assert resp.status_code == 409


# ── GET /coa/tree ───────────────────────────────────────────────────────


class TestGetCOATree:
    def test_get_tree_returns_hierarchical_structure(self, client):
        client.post(f"{COA_URL}/initialize")
        resp = client.get(f"{COA_URL}/tree")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        # Check that it's actually a tree 
        assert "children" in data[0]

    def test_get_tree_before_init_returns_empty(self, client):
        resp = client.get(f"{COA_URL}/tree")
        assert resp.status_code == 200
        assert resp.json() == []


# ── GET /coa/accounts/{id} ──────────────────────────────────────────────


class TestGetCOAAccount:
    def test_get_account_returns_200(self, seeded_client):
        # 1000 is ASSETS
        resp = seeded_client.get(f"{COA_URL}/accounts/1")
        assert resp.status_code == 200
        assert resp.json()["id"] == 1

    def test_not_found(self, seeded_client):
        resp = seeded_client.get(f"{COA_URL}/accounts/99999")
        assert resp.status_code == 404


# ── POST /coa/categories ────────────────────────────────────────────────


class TestCreateCategory:
    def test_create_category_returns_201(self, seeded_client):
        payload = {
            "parent_id": 1,  # Assuming 1 is Assets
            "name": "Custom Assets"
        }
        resp = seeded_client.post(f"{COA_URL}/categories", json=payload)
        assert resp.status_code == 201
        
        # Verify it's in the tree
        tree_resp = seeded_client.get(f"{COA_URL}/tree")
        nodes = tree_resp.json()
        asset_node = next(n for n in nodes if n["id"] == 1)
        # We should find it in the children
        child_names = [c["name"] for c in asset_node["children"]]
        assert "Custom Assets" in child_names


# ── PUT /coa/accounts/{id}/rename ───────────────────────────────────────


class TestRenameAccount:
    def test_rename_custom_account_returns_200(self, seeded_client):
        # Create a custom category first to ensure it's not system-locked
        payload = {
            "parent_id": 1,
            "name": "To Rename"
        }
        created = seeded_client.post(f"{COA_URL}/categories", json=payload).json()
        cat_id = created["id"]

        resp = seeded_client.put(f"{COA_URL}/accounts/{cat_id}/rename", json={"new_name": "Renamed"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Renamed"

    def test_rename_system_account_returns_403(self, seeded_client):
        # Try to rename 'Assets' (ID: 1 usually)
        resp = seeded_client.put(f"{COA_URL}/accounts/1/rename", json={"new_name": "Hacked Assets"})
        assert resp.status_code == 403
        assert resp.json()["error_code"] == "SYSTEM_ACCOUNT"


# ── DELETE /coa/accounts/{id} ───────────────────────────────────────────


class TestDeleteCategory:
    def test_delete_custom_category_returns_204(self, seeded_client):
        payload = {
            "parent_id": 1,
            "name": "To Delete"
        }
        created = seeded_client.post(f"{COA_URL}/categories", json=payload).json()
        cat_id = created["id"]

        resp = seeded_client.delete(f"{COA_URL}/accounts/{cat_id}")
        # Note: Depending on implementation it might be 200 or 204.
        # Router should return 204 purely as per REST
        assert resp.status_code == 204

        # Verify not found or deactivated
        get_resp = seeded_client.get(f"{COA_URL}/accounts/{cat_id}")
        assert get_resp.json().get("is_active") is False

    def test_delete_system_account_returns_403(self, seeded_client):
        resp = seeded_client.delete(f"{COA_URL}/accounts/1")
        assert resp.status_code == 403


# ── GET /coa/status ─────────────────────────────────────────────────────


class TestCOAStatus:
    def test_status_not_ready_initially(self, client):
        resp = client.get(f"{COA_URL}/status")
        assert resp.status_code == 200
        assert resp.json()["ready"] is False

    def test_status_ready_after_init(self, client):
        client.post(f"{COA_URL}/initialize")
        resp = client.get(f"{COA_URL}/status")
        assert resp.status_code == 200
        assert resp.json()["ready"] is True
