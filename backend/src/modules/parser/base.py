"""BaseParser abstract class and ExtractionChain fallback orchestrator."""

from __future__ import annotations

import abc
import logging
from typing import final

from core.models.enums import ExtractionMethod, ParseStatus, SourceType
from core.models.raw_parsed_row import ParseMetadata, ParseResult, RawParsedRow

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD: float = 0.75


class ExtractionResult:
    """Return type from a single extraction attempt.

    Attributes:
        rows: The extracted rows (may be empty).
        metadata: Aggregate metadata from the extraction attempt.
        method: Which method produced this result.
        confidence: Computed confidence score [0, 1].
        succeeded: True if confidence >= CONFIDENCE_THRESHOLD.
    """

    __slots__ = ("rows", "metadata", "method", "confidence", "succeeded")

    def __init__(
        self,
        rows: list[RawParsedRow],
        metadata: ParseMetadata,
        method: ExtractionMethod,
        confidence: float,
    ) -> None:
        self.rows = rows
        self.metadata = metadata
        self.method = method
        self.confidence = confidence
        self.succeeded = confidence >= CONFIDENCE_THRESHOLD


class BaseParser(abc.ABC):
    """Abstract base class that every source-specific parser must implement.

    Design rules:
    - `extract()` should NEVER raise — wrap errors and return low-confidence result.
    - `extract()` is pure in that it only reads from `file_bytes`; no DB calls.
    - The ExtractionChain calls `extract()` for each method in `supported_methods()`.

    Subclass checklist:
        class HdfcPdfParser(BaseParser):
            source_type = SourceType.HDFC_BANK
            version = "1.2"
            supported_formats = ["PDF"]

            def extract(self, batch_id, file_bytes, method) -> ExtractionResult:
                ...
    """

    source_type: SourceType          # Must be set on the subclass (not instance)
    version: str = "1.0"
    supported_formats: list[str] = ["PDF"]

    @abc.abstractmethod
    def extract(
        self,
        batch_id: str,
        file_bytes: bytes,
        method: ExtractionMethod,
    ) -> ExtractionResult:
        """Attempt extraction using the given method.

        Args:
            batch_id: Parent ImportBatch ID (for tagging rows).
            file_bytes: Decrypted document bytes.
            method: The extraction method to attempt.

        Returns:
            ExtractionResult — always. Never raises.
        """
        ...

    def supported_methods(self) -> list[ExtractionMethod]:
        """Return the ordered list of extraction methods this parser supports.

        Override in subclasses that only support a subset (e.g. CSV parsers
        only use TABLE_EXTRACTION, not TEXT_LAYER or OCR).
        """
        return [
            ExtractionMethod.TEXT_LAYER,
            ExtractionMethod.TABLE_EXTRACTION,
            ExtractionMethod.OCR,
        ]

    @final
    def parser_id(self) -> str:
        """Stable string identifier: '{source_type}-{version}'."""
        return f"{self.source_type.value.lower()}-{self.version}"

    def _make_failed_result(
        self,
        batch_id: str,
        method: ExtractionMethod,
        error: str,
    ) -> ExtractionResult:
        """Helper for parsers to return a zero-confidence failure result."""
        meta = ParseMetadata(
            extraction_method=method,
            parser_version=self.version,
            warnings=[error],
        )
        return ExtractionResult(rows=[], metadata=meta, method=method, confidence=0.0)
