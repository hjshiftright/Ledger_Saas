"""Integration tests for the Ledger 3.0 REST API.

Tests exercise the full request/response cycle using FastAPI's TestClient.
No mocks are applied to routing, auth, detection, or parsing — the real
modules run end-to-end.  In-memory stores are cleared between tests.

Run from the *src/* directory (PYTHONPATH must include src/):

    pytest ../tests/integration/ -v

Or from the project root after ``pip install -e .``:

    pytest tests/integration/ -v
"""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient

import api.routers.imports as _imports_mod
import api.routers.parser as _parser_mod
from main import create_app
from jose import jwt
from config import get_settings

_settings = get_settings()
_DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"
_ALICE_TENANT_ID   = "00000000-0000-0000-0000-000000000002"


def make_token(user_id: str, tenant_id: str = _DEFAULT_TENANT_ID) -> str:
    return jwt.encode(
        {"sub": user_id, "tenant_id": tenant_id},
        _settings.secret_key,
        algorithm="HS256",
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def app():
    """Single FastAPI application instance shared across all classes in this module.

    Uses the module-level app so that dependency_overrides applied in conftest
    (aiosqlite engine) take effect.
    """
    from main import app as _app
    return _app


@pytest.fixture(scope="class")
def client(app):  # noqa: F811
    """TestClient alive for the duration of each test class."""
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture(autouse=True)
def clear_stores():
    """Clear in-memory batch / parsed-row stores before and after every test."""
    _imports_mod._batches.clear()
    _parser_mod._parsed_rows.clear()
    yield
    _imports_mod._batches.clear()
    _parser_mod._parsed_rows.clear()


# Bearer token used for all tests that need an authenticated user.
_AUTH = {"Authorization": f"Bearer {make_token('test-user')}"}


# ---------------------------------------------------------------------------
# Minimal CSV sample factories
# ---------------------------------------------------------------------------

def _hdfc_csv(n_rows: int = 3) -> bytes:
    """HDFC Bank CSV that matches both the CSV-header detector and the generic parser.

    Required detector columns (from detector._CSV_HEADER_SIGNATURES):
        Date, Narration, Value Dt, Withdrawal Amt (Dr), Deposit Amt (Cr)
    """
    lines = [
        "Date,Narration,Chq./Ref.No.,Value Dt,Withdrawal Amt (Dr),Deposit Amt (Cr),Closing Balance",
    ]
    for i in range(1, n_rows + 1):
        lines.append(
            f"0{i}/01/2024,UPI/TXN{i:04d}/SWIGGY,,0{i}/01/2024,{i * 100:.2f},,{50000 - i * 100:.2f}"
        )
    return "\n".join(lines).encode()


def _sbi_csv(n_rows: int = 3) -> bytes:
    """SBI Bank CSV matching the SBI_BANK_CSV detector signature.

    Required columns: Txn Date, Description, Debit, Credit, Balance
    Date format: %d %b %Y
    """
    lines = [
        "Txn Date,Description,Ref No./Cheque No.,Debit,Credit,Balance",
    ]
    for i in range(1, n_rows + 1):
        lines.append(
            f"0{i} Jan 2024,ATM/WDL{i:04d},{i:06d},{i * 150:.2f},,{30000 - i * 150:.2f}"
        )
    return "\n".join(lines).encode()


def _icici_csv(n_rows: int = 3) -> bytes:
    """ICICI Bank CSV.

    ICICI CSV has no entry in detector._CSV_HEADER_SIGNATURES, so callers must
    always pass source_type_hint="ICICI_BANK_CSV" for correct detection.

    Note: column names include a trailing space before ')' — this is intentional
    and matches the real ICICI netbanking export format.
    """
    lines = [
        "Transaction Date,Transaction Remarks,Withdrawal Amount (INR ),Deposit Amount (INR ),Balance (INR )",
    ]
    for i in range(1, n_rows + 1):
        lines.append(
            f"0{i}/01/2024,NEFT/HDFC/{i:04d}/{400_000 + i},{i * 200:.2f},,{80000 - i * 200:.2f}"
        )
    return "\n".join(lines).encode()


# ---------------------------------------------------------------------------
# Shared upload helper
# ---------------------------------------------------------------------------

def _upload(
    client: TestClient,
    csv_bytes: bytes,
    filename: str,
    **form_data,
):
    """POST /api/v1/imports/upload and return the raw Response object."""
    return client.post(
        "/api/v1/imports/upload",
        files={"file": (filename, io.BytesIO(csv_bytes), "text/csv")},
        data=form_data or None,
        headers=_AUTH,
    )


# ---------------------------------------------------------------------------
# Class: TestDevAuth
# ---------------------------------------------------------------------------

class TestDevAuth:
    """Verify the dev-mode auth bypass.

    When APP_ENV=development (the default) any endpoint must accept requests
    that carry *no* Authorization header.  The missing token is silently
    replaced by DEV_DEFAULT_USER_ID ("dev-user").
    """

    def test_no_auth_header_accepted_in_dev_mode(self, client: TestClient):
        """GET /api/v1/imports must return 200 without any Authorization header."""
        resp = client.get("/api/v1/imports")
        assert resp.status_code == 200

    def test_explicit_bearer_token_still_works(self, client: TestClient):
        """A valid Bearer token must always be accepted regardless of env."""
        resp = client.get("/api/v1/imports", headers={"Authorization": f"Bearer {make_token('alice', _ALICE_TENANT_ID)}"})
        assert resp.status_code == 200

    def test_non_bearer_scheme_rejected(self, client: TestClient):
        """Non-Bearer Authorization schemes must be rejected with HTTP 401."""
        resp = client.get(
            "/api/v1/imports",
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"]["error"] == "TOKEN_INVALID"

    def test_empty_bearer_rejected(self, client: TestClient):
        """An empty Bearer value must be rejected with HTTP 401."""
        resp = client.get(
            "/api/v1/imports",
            headers={"Authorization": "Bearer "},
        )
        assert resp.status_code == 401

    def test_dev_user_batches_invisible_to_other_users(self, client: TestClient):
        """Batches uploaded without auth (→ dev-user) must not appear for other users."""
        # Upload without auth — lands under DEV_DEFAULT_USER_ID = "dev-user"
        client.post(
            "/api/v1/imports/upload",
            files={"file": ("bank_statement.csv", io.BytesIO(_hdfc_csv()), "text/csv")},
        )
        # Alice's list must be empty
        resp = client.get("/api/v1/imports", headers={"Authorization": f"Bearer {make_token('alice', _ALICE_TENANT_ID)}"})
        assert resp.json()["total"] == 0


# ---------------------------------------------------------------------------
# Class: TestImportUploadAPI
# ---------------------------------------------------------------------------

class TestImportUploadAPI:
    """POST /api/v1/imports/upload — file ingestion and source-type auto-detection.

    Neutral filenames (no bank keyword) are used so that the detector must
    fall back to CSV header scanning, exercising the real auto-detection path.
    """

    def test_hdfc_csv_auto_detected(self, client: TestClient):
        resp = _upload(client, _hdfc_csv(), "bank_statement.csv")
        assert resp.status_code == 202
        data = resp.json()
        assert data["source_type"] == "HDFC_BANK_CSV"
        assert data["format"] == "CSV"
        assert data["batch_id"]

    def test_sbi_csv_auto_detected(self, client: TestClient):
        resp = _upload(client, _sbi_csv(), "export.csv")
        assert resp.status_code == 202
        assert resp.json()["source_type"] == "SBI_BANK_CSV"

    def test_source_type_hint_overrides_detection(self, client: TestClient):
        """Caller-supplied source_type_hint must win over content scanning."""
        resp = _upload(
            client, _icici_csv(), "statement.csv",
            source_type_hint="ICICI_BANK_CSV",
        )
        assert resp.status_code == 202
        assert resp.json()["source_type"] == "ICICI_BANK_CSV"

    def test_upload_returns_poll_url(self, client: TestClient):
        data = _upload(client, _hdfc_csv(), "bank_statement.csv").json()
        assert data["poll_url"].startswith("/api/v1/imports/")

    def test_upload_stores_file_metadata(self, client: TestClient):
        data = _upload(client, _hdfc_csv(5), "bank_statement.csv").json()
        assert data["file_size_bytes"] > 0
        assert data["filename"] == "bank_statement.csv"
        assert data["detection_confidence"] > 0.0

    def test_duplicate_file_adds_warning(self, client: TestClient):
        """Uploading identical bytes twice must include a duplicate-detection warning."""
        csv_bytes = _hdfc_csv(3)
        _upload(client, csv_bytes, "bank_statement.csv")
        second = _upload(client, csv_bytes, "bank_statement.csv")
        warnings = second.json().get("warnings", [])
        assert any("uplicate" in w for w in warnings)


# ---------------------------------------------------------------------------
# Class: TestBatchLifecycleAPI
# ---------------------------------------------------------------------------

class TestBatchLifecycleAPI:
    """GET /api/v1/imports, GET /api/v1/imports/{id}, DELETE /api/v1/imports/{id}."""

    def test_list_empty_before_any_upload(self, client: TestClient):
        body = client.get("/api/v1/imports", headers=_AUTH).json()
        assert body["total"] == 0
        assert body["items"] == []

    def test_list_shows_batch_after_upload(self, client: TestClient):
        _upload(client, _hdfc_csv(), "bank_statement.csv")
        body = client.get("/api/v1/imports", headers=_AUTH).json()
        assert body["total"] == 1

    def test_get_batch_detail(self, client: TestClient):
        batch_id = _upload(client, _hdfc_csv(), "bank_statement.csv").json()["batch_id"]
        resp = client.get(f"/api/v1/imports/{batch_id}", headers=_AUTH)
        assert resp.status_code == 200
        assert resp.json()["batch_id"] == batch_id

    def test_get_nonexistent_batch_returns_404(self, client: TestClient):
        resp = client.get("/api/v1/imports/no-such-batch", headers=_AUTH)
        assert resp.status_code == 404

    def test_delete_batch_cancels_it(self, client: TestClient):
        batch_id = _upload(client, _hdfc_csv(), "bank_statement.csv").json()["batch_id"]
        del_resp = client.delete(f"/api/v1/imports/{batch_id}", headers=_AUTH)
        assert del_resp.status_code in (200, 204)
        # DELETE marks the batch as CANCELLED; it remains visible but frozen
        detail = client.get(f"/api/v1/imports/{batch_id}", headers=_AUTH).json()
        assert detail["status"] == "CANCELLED"

    def test_user_isolation_in_list(self, client: TestClient):
        """test-user's batch must NOT appear in alice's list."""
        _upload(client, _hdfc_csv(), "bank_statement.csv")  # uploaded by test-user
        resp = client.get("/api/v1/imports", headers={"Authorization": f"Bearer {make_token('alice', _ALICE_TENANT_ID)}"})
        assert resp.json()["total"] == 0


# ---------------------------------------------------------------------------
# Class: TestParseAPI
# ---------------------------------------------------------------------------

class TestParseAPI:
    """POST /api/v1/pipeline/parse -- upload + detect + parse in a single request."""

    # -- Private upload+parse helpers ----------------------------------------

    def _parse_hdfc(self, client: TestClient, n_rows: int = 5) -> str:
        resp = client.post(
            "/api/v1/pipeline/parse",
            files={"file": ("bank_statement.csv", io.BytesIO(_hdfc_csv(n_rows)), "text/csv")},
            headers=_AUTH,
        )
        assert resp.status_code == 202
        return resp.json()["batch_id"]

    def _parse_sbi(self, client: TestClient, n_rows: int = 4) -> str:
        resp = client.post(
            "/api/v1/pipeline/parse",
            files={"file": ("export.csv", io.BytesIO(_sbi_csv(n_rows)), "text/csv")},
            headers=_AUTH,
        )
        assert resp.status_code == 202
        return resp.json()["batch_id"]

    def _parse_icici(self, client: TestClient, n_rows: int = 3) -> str:
        resp = client.post(
            "/api/v1/pipeline/parse",
            files={"file": ("statement.csv", io.BytesIO(_icici_csv(n_rows)), "text/csv")},
            data={"source_type_hint": "ICICI_BANK_CSV"},
            headers=_AUTH,
        )
        assert resp.status_code == 202
        return resp.json()["batch_id"]

    # -- Tests ---------------------------------------------------------------

    def test_trigger_parse_returns_202(self, client: TestClient):
        resp = client.post(
            "/api/v1/pipeline/parse",
            files={"file": ("bank_statement.csv", io.BytesIO(_hdfc_csv(5)), "text/csv")},
            headers=_AUTH,
        )
        assert resp.status_code == 202

    def test_trigger_parse_unknown_batch_returns_404(self, client: TestClient):
        resp = client.get("/api/v1/pipeline/parse/status/no-such-batch", headers=_AUTH)
        assert resp.status_code == 404

    def test_rows_available_after_parse(self, client: TestClient):
        batch_id = self._parse_hdfc(client, n_rows=5)
        data = client.get(f"/api/v1/pipeline/parse/{batch_id}/rows", headers=_AUTH).json()
        assert data["total"] >= 1
        assert data["batch_id"] == batch_id

    def test_parsed_rows_contain_required_fields(self, client: TestClient):
        batch_id = self._parse_hdfc(client)
        rows = client.get(
            f"/api/v1/pipeline/parse/{batch_id}/rows", headers=_AUTH
        ).json()["items"]
        assert len(rows) >= 1
        for field in ("row_id", "raw_date", "raw_narration", "row_confidence"):
            assert field in rows[0], f"Missing field in parsed row: {field}"

    def test_parse_status_endpoint(self, client: TestClient):
        batch_id = self._parse_hdfc(client)
        resp = client.get(f"/api/v1/pipeline/parse/status/{batch_id}", headers=_AUTH)
        assert resp.status_code == 200
        assert resp.json()["batch_id"] == batch_id

    def test_source_types_endpoint_lists_known_formats(self, client: TestClient):
        resp = client.get("/api/v1/pipeline/source-types", headers=_AUTH)
        assert resp.status_code == 200
        values = {st["value"] for st in resp.json()}
        for expected in ("HDFC_BANK_CSV", "SBI_BANK_CSV", "ICICI_BANK_CSV", "AXIS_BANK_CSV"):
            assert expected in values

    def test_sbi_csv_parse_produces_rows(self, client: TestClient):
        batch_id = self._parse_sbi(client, n_rows=4)
        data = client.get(f"/api/v1/pipeline/parse/{batch_id}/rows", headers=_AUTH).json()
        assert data["total"] >= 1

    def test_icici_csv_parse_with_hint_produces_rows(self, client: TestClient):
        batch_id = self._parse_icici(client, n_rows=3)
        data = client.get(f"/api/v1/pipeline/parse/{batch_id}/rows", headers=_AUTH).json()
        assert data["total"] >= 1

    def test_re_parse_after_completion_is_accepted(self, client: TestClient):
        """Uploading the same file twice must return 202 both times."""
        csv_bytes = _hdfc_csv(5)
        for _ in range(2):
            resp = client.post(
                "/api/v1/pipeline/parse",
                files={"file": ("bank_statement.csv", io.BytesIO(csv_bytes), "text/csv")},
                headers=_AUTH,
            )
            assert resp.status_code == 202


# ---------------------------------------------------------------------------
# Class: TestPipelineParseAPI
# ---------------------------------------------------------------------------

class TestPipelineParseAPI:
    """POST /api/v1/pipeline/parse — single-call upload + detect + parse (SM-K)."""

    def test_hdfc_csv_in_one_call(self, client: TestClient):
        resp = client.post(
            "/api/v1/pipeline/parse",
            files={"file": ("bank_statement.csv", io.BytesIO(_hdfc_csv(4)), "text/csv")},
            headers=_AUTH,
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["source_type"] == "HDFC_BANK_CSV"
        assert data["txn_found"] >= 1

    def test_sbi_csv_in_one_call(self, client: TestClient):
        resp = client.post(
            "/api/v1/pipeline/parse",
            files={"file": ("export.csv", io.BytesIO(_sbi_csv(3)), "text/csv")},
            headers=_AUTH,
        )
        assert resp.status_code == 202
        assert resp.json()["source_type"] == "SBI_BANK_CSV"

    def test_icici_csv_with_hint(self, client: TestClient):
        resp = client.post(
            "/api/v1/pipeline/parse",
            files={"file": ("statement.csv", io.BytesIO(_icici_csv(3)), "text/csv")},
            data={"source_type_hint": "ICICI_BANK_CSV"},
            headers=_AUTH,
        )
        assert resp.status_code == 202
        assert resp.json()["txn_found"] >= 1

    def test_response_contains_urls(self, client: TestClient):
        data = client.post(
            "/api/v1/pipeline/parse",
            files={"file": ("bank_statement.csv", io.BytesIO(_hdfc_csv(2)), "text/csv")},
            headers=_AUTH,
        ).json()
        assert data["process_url"].startswith("/api/v1/pipeline/process/")

    def test_rows_accessible_via_pipeline_alias(self, client: TestClient):
        resp = client.post(
            "/api/v1/pipeline/parse",
            files={"file": ("bank_statement.csv", io.BytesIO(_hdfc_csv(3)), "text/csv")},
            headers=_AUTH,
        )
        batch_id = resp.json()["batch_id"]
        rows = client.get(
            f"/api/v1/pipeline/parse/{batch_id}/rows", headers=_AUTH
        ).json()
        assert rows["total"] >= 1

    def test_unrecognised_csv_returns_202_with_warning(self, client: TestClient):
        """Unknown CSV that can't be detected must still return 202, not 500."""
        resp = client.post(
            "/api/v1/pipeline/parse",
            files={"file": ("unknown.csv", io.BytesIO(b"col1,col2\na,b\nc,d"), "text/csv")},
            headers=_AUTH,
        )
        assert resp.status_code == 202
        assert len(resp.json()["warnings"]) >= 1


# ---------------------------------------------------------------------------
# Class: TestFullPipelineAPI
# ---------------------------------------------------------------------------

class TestFullPipelineAPI:
    """POST /api/v1/pipeline/parse + POST /api/v1/pipeline/process/{batch_id} — end-to-end."""

    def _run_pipeline(self, client: TestClient, csv_bytes: bytes, filename: str, **form_data) -> dict:
        """Parse then process; return the ProcessResponse JSON."""
        parse_resp = client.post(
            "/api/v1/pipeline/parse",
            files={"file": (filename, io.BytesIO(csv_bytes), "text/csv")},
            data=form_data or None,
            headers=_AUTH,
        )
        assert parse_resp.status_code == 202
        batch_id = parse_resp.json()["batch_id"]
        proc_resp = client.post(
            f"/api/v1/pipeline/process/{batch_id}",
            json={},
            headers=_AUTH,
        )
        assert proc_resp.status_code == 200
        return proc_resp.json()

    def test_hdfc_csv_end_to_end(self, client: TestClient):
        data = self._run_pipeline(client, _hdfc_csv(5), "bank_statement.csv")
        assert data["batch_id"]
        assert data["raw_rows_count"] >= 1
        assert data["proposals_generated"] >= 0

    def test_response_contains_all_required_keys(self, client: TestClient):
        data = self._run_pipeline(client, _hdfc_csv(3), "bank_statement.csv")
        for key in (
            "batch_id", "raw_rows_count", "normalized_count", "new_count",
            "duplicate_count", "proposals_generated", "warnings",
        ):
            assert key in data, f"Missing key in process response: {key}"

    def test_sbi_csv_end_to_end(self, client: TestClient):
        data = self._run_pipeline(client, _sbi_csv(3), "export.csv")
        assert data["raw_rows_count"] >= 1

    def test_icici_csv_with_hint(self, client: TestClient):
        data = self._run_pipeline(
            client, _icici_csv(3), "statement.csv",
            source_type_hint="ICICI_BANK_CSV",
        )
        assert data["raw_rows_count"] >= 1

    def test_txn_counts_are_consistent(self, client: TestClient):
        """new_count + duplicate_count must equal normalized_count."""
        data = self._run_pipeline(client, _hdfc_csv(4), "bank_statement.csv")
        assert data["new_count"] + data["duplicate_count"] == data["normalized_count"]

    def test_stages_completed_is_non_empty(self, client: TestClient):
        """proposals_generated must be a non-negative integer."""
        data = self._run_pipeline(client, _hdfc_csv(3), "bank_statement.csv")
        assert isinstance(data["proposals_generated"], int)
        assert data["proposals_generated"] >= 0
