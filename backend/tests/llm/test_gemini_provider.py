"""Unit tests for GeminiProvider — all external API calls are mocked.

The implementation uses the new google-genai SDK (google.genai.Client),
so we patch sys.modules['google.genai'] and sys.modules['google.genai.types']
to intercept the lazy imports inside each provider method.
"""

from __future__ import annotations

import json
import math
import sys
from contextlib import contextmanager
from types import ModuleType
from unittest.mock import MagicMock

import pytest

from modules.llm.base import (
    FileExtractionRequest,
    LLMResponse,
    TextExtractionRequest,
    UploadedFile,
    VisionExtractionRequest,
)
from modules.llm.providers.gemini import GeminiProvider, MAX_PAGES_PER_CALL


# ── Fixtures & helpers ────────────────────────────────────────────────────────

@pytest.fixture()
def provider():
    return GeminiProvider(
        api_key="test-key",
        text_model="gemini-1.5-pro",
        vision_model="gemini-1.5-pro",
    )


@contextmanager
def mock_genai():
    """Inject MagicMocks for google.genai and google.genai.types so the lazy
    ``from google import genai`` / ``from google.genai import types`` imports
    inside the provider pick up our fakes instead of calling the real API.
    """
    fake_genai = MagicMock()
    fake_types = MagicMock()

    # google.genai.types.Part.from_bytes must return a mock part
    fake_types.Part.from_bytes.return_value = MagicMock()

    # Ensure the google package namespace exists
    if "google" not in sys.modules:
        sys.modules["google"] = ModuleType("google")

    originals = {
        "google.genai": sys.modules.get("google.genai"),
        "google.genai.types": sys.modules.get("google.genai.types"),
    }
    sys.modules["google.genai"] = fake_genai
    sys.modules["google.genai.types"] = fake_types

    # Make `from google import genai` resolve to our fake
    sys.modules["google"].genai = fake_genai  # type: ignore[attr-defined]

    try:
        yield fake_genai, fake_types
    finally:
        for key, val in originals.items():
            if val is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = val


def _make_client_mock(fake_genai: MagicMock, response_text: str) -> MagicMock:
    """Wire fake_genai.Client() so client.models.generate_content() returns
    a mock response with .text and .usage_metadata set."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = response_text
    mock_response.usage_metadata.prompt_token_count = 10
    mock_response.usage_metadata.candidates_token_count = 20
    mock_client.models.generate_content.return_value = mock_response
    fake_genai.Client.return_value = mock_client
    return mock_client


_SAMPLE_JSON = json.dumps({
    "transactions": [
        {
            "date": "01/03/2024",
            "narration": "SWIGGY ORDER",
            "debit_amount": "450.00",
            "credit_amount": "",
            "balance": "9550.00",
        }
    ]
})

_FENCED_JSON = f"```json\n{_SAMPLE_JSON}\n```"


# ── extract_text ──────────────────────────────────────────────────────────────

def test_extract_text_returns_rows(provider):
    with mock_genai() as (genai, _types):
        mock_client = _make_client_mock(genai, _SAMPLE_JSON)

        req = TextExtractionRequest(batch_id="b1", source_type="HDFC_BANK", partial_text="some text")
        resp = provider.extract_text(req)

    assert isinstance(resp, LLMResponse)
    assert len(resp.rows) == 1
    assert resp.rows[0].raw_date == "01/03/2024"
    assert resp.error is None


def test_extract_text_strips_json_fence(provider):
    """extract_text must handle ```json ... ``` wrapped responses."""
    with mock_genai() as (genai, _types):
        _make_client_mock(genai, _FENCED_JSON)

        req = TextExtractionRequest(batch_id="b1", source_type="HDFC_BANK", partial_text="text")
        resp = provider.extract_text(req)

    assert len(resp.rows) == 1


def test_extract_text_invalid_json_returns_error_or_empty(provider):
    with mock_genai() as (genai, _types):
        _make_client_mock(genai, "not json at all")

        req = TextExtractionRequest(batch_id="b1", source_type="HDFC_BANK", partial_text="text")
        resp = provider.extract_text(req)

    assert resp.error is not None or len(resp.rows) == 0


# ── extract_vision ────────────────────────────────────────────────────────────

def test_extract_vision_chunks_10_pages(provider):
    """extract_vision must split pages into chunks of MAX_PAGES_PER_CALL."""
    n_pages = 25
    expected_calls = math.ceil(n_pages / MAX_PAGES_PER_CALL)

    with mock_genai() as (genai, _types):
        mock_client = _make_client_mock(genai, _SAMPLE_JSON)

        pages = [b"\x89PNG\r\n" + b"x" * 100] * n_pages
        req = VisionExtractionRequest(batch_id="b2", source_type="HDFC_BANK", page_images=pages)
        provider.extract_vision(req)

    assert mock_client.models.generate_content.call_count == expected_calls


def test_extract_vision_single_page(provider):
    with mock_genai() as (genai, _types):
        mock_client = _make_client_mock(genai, _SAMPLE_JSON)

        req = VisionExtractionRequest(batch_id="b3", source_type="HDFC_BANK", page_images=[b"PNG"])
        provider.extract_vision(req)

    assert mock_client.models.generate_content.call_count == 1


# ── upload_file / delete_file ─────────────────────────────────────────────────

def test_upload_file_returns_uploaded_file(provider):
    with mock_genai() as (genai, _types):
        mock_client = MagicMock()
        mock_uploaded = MagicMock()
        mock_uploaded.name = "files/abc123"
        mock_client.files.upload.return_value = mock_uploaded
        genai.Client.return_value = mock_client

        req = FileExtractionRequest(
            batch_id="b4", source_type="HDFC_BANK",
            file_bytes=b"%PDF", filename="stmt.pdf",
        )
        result = provider.upload_file(req)

    assert isinstance(result, UploadedFile)
    assert result.file_id == "files/abc123"


def test_delete_file_returns_true(provider):
    with mock_genai() as (genai, _types):
        mock_client = MagicMock()
        mock_client.files.delete.return_value = None
        genai.Client.return_value = mock_client
        assert provider.delete_file("files/abc123") is True


def test_delete_file_returns_false_on_error(provider):
    with mock_genai() as (genai, _types):
        mock_client = MagicMock()
        mock_client.files.delete.side_effect = Exception("Not found")
        genai.Client.return_value = mock_client
        assert provider.delete_file("files/missing") is False


# ── test_connection ───────────────────────────────────────────────────────────

def test_test_connection_succeeds(provider):
    with mock_genai() as (genai, _types):
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = MagicMock(text="ok")
        genai.Client.return_value = mock_client
        assert provider.test_connection() is True


def test_test_connection_raises_on_failure(provider):
    with mock_genai() as (genai, _types):
        genai.Client.side_effect = Exception("Invalid API key")
        # test_connection catches exceptions and returns False (never raises)
        result = provider.test_connection()
        assert result is False
