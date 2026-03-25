"""BaseLLMProvider — abstract interface that all LLM provider adapters implement.

Concrete providers: GeminiProvider, OpenAIProvider, AnthropicProvider.

Design:
    - All providers implement `extract_text()`, `extract_vision()`, and `upload_file()`.
    - `upload_file()` uploads a document to the provider's Files API and returns a file_id
      that can be referenced in subsequent extraction calls (avoids re-encoding large PDFs
      as base64 on every call).
    - `extract_with_file()` sends an extraction request that references a previously uploaded file.
    - Both methods return `LLMResponse` which carries RawParsedRow[].
    - No global state — providers are instantiated with their API key and model names.
    - Tests mock at this boundary (no real API calls in unit tests).
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field

from core.models.raw_parsed_row import RawParsedRow


# ── Request / response contracts ─────────────────────────────────────────────

@dataclass
class TextExtractionRequest:
    """Input for the text extraction path (SM-D §3 text path)."""

    batch_id: str
    source_type: str                # SourceType.value string
    partial_text: str               # Text already extracted by SM-C (may be partial)
    page_count: int = 1
    extra_context: dict = field(default_factory=dict)


@dataclass
class VisionExtractionRequest:
    """Input for the vision extraction path (SM-D §3 vision path)."""

    batch_id: str
    source_type: str                # SourceType.value string
    page_images: list[bytes]        # PNG bytes per page
    existing_rows_context: str = ""  # Draft rows as plain text (for Smart Mode enrichment)
    account_hint_list: list[dict] = field(default_factory=list)
    extra_context: dict = field(default_factory=dict)


@dataclass
class FileExtractionRequest:
    """Input for the file-handle extraction path (SM-D Files API path).

    Use this when you want to upload the raw document bytes directly to the
    provider's Files API rather than sending base64-encoded page images.
    Supported by: OpenAI (Files API), Anthropic (Files API beta), Google (Gemini Files API).
    """

    batch_id: str
    source_type: str
    file_bytes: bytes               # Raw document bytes (PDF, CSV, …)
    filename: str                   # Original filename including extension
    mime_type: str = "application/pdf"
    extra_context: dict = field(default_factory=dict)


@dataclass
class UploadedFile:
    """Metadata about a file uploaded to a provider's Files API."""

    file_id: str                    # Provider-assigned file ID
    provider_name: str
    filename: str
    mime_type: str
    size_bytes: int = 0
    expires_at: str | None = None   # ISO timestamp or None if permanent


@dataclass
class LLMResponse:
    """Output from any LLM extraction call."""

    batch_id: str
    rows: list[RawParsedRow]        # Normalized to RawParsedRow schema
    input_tokens: int = 0
    output_tokens: int = 0
    model_used: str = ""
    provider_name: str = ""
    overall_confidence: float = 0.0
    raw_response: str = ""          # Raw LLM JSON string (for debugging / audit)
    error: str | None = None
    is_truncated: bool = False       # True when the response was cut off mid-JSON

    @property
    def succeeded(self) -> bool:
        return self.error is None and len(self.rows) > 0


# ── Abstract base ─────────────────────────────────────────────────────────────

class BaseLLMProvider(abc.ABC):
    """Abstract base class for LLM provider adapters.

    Subclass checklist:
        class GeminiProvider(BaseLLMProvider):
            PROVIDER_NAME = "GOOGLE"

            def extract_text(self, request) -> LLMResponse: ...
            def extract_vision(self, request) -> LLMResponse: ...
            def upload_file(self, request) -> UploadedFile: ...
            def extract_with_file(self, file_id, batch_id, source_type) -> LLMResponse: ...
            def delete_file(self, file_id) -> bool: ...
            def test_connection(self) -> bool: ...
    """

    PROVIDER_NAME: str = "UNKNOWN"

    @abc.abstractmethod
    def extract_text(self, request: TextExtractionRequest) -> LLMResponse:
        """Extract transactions from partial text using an LLM completion."""
        ...

    @abc.abstractmethod
    def extract_vision(self, request: VisionExtractionRequest) -> LLMResponse:
        """Extract transactions from page images using a vision-capable LLM."""
        ...

    @abc.abstractmethod
    def upload_file(self, request: FileExtractionRequest) -> UploadedFile:
        """Upload a document to the provider's Files API.

        Returns an UploadedFile with a provider-assigned file_id.
        The file_id can then be passed to extract_with_file() to avoid
        re-uploading the same document for multiple extraction attempts.

        Raises RuntimeError if the provider does not support file uploads.
        """
        ...

    @abc.abstractmethod
    def extract_with_file(
        self,
        file_id: str,
        batch_id: str,
        source_type: str,
        extra_context: dict | None = None,
    ) -> LLMResponse:
        """Extract transactions from a previously uploaded file.

        Args:
            file_id: Provider-assigned file ID from upload_file().
            batch_id: Parent ImportBatch ID.
            source_type: SourceType.value string for prompt selection.
            extra_context: Optional additional context for the prompt.
        """
        ...

    @abc.abstractmethod
    def delete_file(self, file_id: str) -> bool:
        """Delete an uploaded file from the provider's Files API.

        Returns True if deleted successfully, False if not found or unsupported.
        Implementations should not raise — return False on any error.
        """
        ...

    @abc.abstractmethod
    def test_connection(self) -> bool:
        """Test the API key and model availability.

        Returns True if a minimal API call succeeds.
        """
        ...

    def provider_name(self) -> str:
        return self.PROVIDER_NAME

