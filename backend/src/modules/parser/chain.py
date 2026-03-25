"""ExtractionChain — orchestrates the layered extraction fallback strategy.

Calls a parser's supported methods in order, stopping at the first that
reaches CONFIDENCE_THRESHOLD. Returns the best available result if all methods fail.
As a last resort, an optional LLM provider is called with the raw text and/or
page images (LLM_TEXT → LLM_VISION cascade).

Usage:
    chain = ExtractionChain(parser, batch_id, file_bytes)
    result = chain.run()                          # no LLM fallback
    result = chain.run(llm_provider=my_provider)  # LLM called when all else fails
"""

from __future__ import annotations

import inspect
import logging
from typing import TYPE_CHECKING

from core.models.enums import ExtractionMethod, ParseStatus
from core.models.raw_parsed_row import ParseMetadata, ParseResult
from modules.parser.base import BaseParser, ExtractionResult

if TYPE_CHECKING:
    from modules.llm.base import BaseLLMProvider, LLMResponse

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD: float = 0.75


class ExtractionChain:
    """Runs all supported extraction methods in priority order.

    Stops early on the first method that returns confidence >= CONFIDENCE_THRESHOLD.
    Falls back to the best result seen if none meet the threshold.
    If an llm_provider is supplied and all traditional methods fail (or produce
    only a low-confidence partial result), the chain attempts LLM extraction
    using the raw text and then page images as a final fallback.
    """

    def __init__(
        self,
        parser: BaseParser,
        batch_id: str,
        file_bytes: bytes,
        filename: str = "",
    ) -> None:
        self._parser = parser
        self._batch_id = batch_id
        self._file_bytes = file_bytes
        self._filename = filename
        # Pre-compute whether the parser's extract() accepts a filename kwarg
        # (only GenericCsvParser does) so we only inspect once per chain.
        try:
            sig = inspect.signature(self._parser.extract)
            self._pass_filename = "filename" in sig.parameters
        except (ValueError, TypeError):
            self._pass_filename = False

    def run(self, llm_provider: "BaseLLMProvider | None" = None) -> ParseResult:
        """Execute the fallback chain and return the best available ParseResult."""
        methods = self._parser.supported_methods()
        best: ExtractionResult | None = None

        for method in methods:
            logger.info(
                "ExtractionChain: %s trying method %s for batch %s",
                self._parser.parser_id(),
                method.value,
                self._batch_id,
            )
            try:
                extra_kwargs: dict = {}
                if self._pass_filename and self._filename:
                    extra_kwargs["filename"] = self._filename
                result = self._parser.extract(
                    batch_id=self._batch_id,
                    file_bytes=self._file_bytes,
                    method=method,
                    **extra_kwargs,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Parser %s method %s raised unexpectedly: %s",
                    self._parser.parser_id(),
                    method.value,
                    exc,
                    exc_info=True,
                )
                continue

            # Keep track of the best result so far
            if best is None or result.confidence > best.confidence:
                best = result

            if result.succeeded:
                logger.info(
                    "ExtractionChain: %s succeeded via %s for batch %s (confidence=%.3f)",
                    self._parser.parser_id(),
                    method.value,
                    self._batch_id,
                    result.confidence,
                )
                return self._to_parse_result(result, ParseStatus.SUCCESS)

        # ── LLM fallback (when all traditional methods fail or fall short) ────
        if llm_provider is not None and (
            best is None or not best.rows or best.confidence < CONFIDENCE_THRESHOLD
        ):
            logger.info(
                "ExtractionChain: attempting LLM fallback for batch %s "
                "(traditional best confidence=%.3f)",
                self._batch_id,
                best.confidence if best else 0.0,
            )
            llm_result = self._try_llm_fallback(llm_provider)
            if llm_result is not None and llm_result.confidence > (
                best.confidence if best else 0.0
            ):
                best = llm_result

        # No method met the threshold
        if best and best.rows:
            status = (
                ParseStatus.SUCCESS
                if best.confidence >= CONFIDENCE_THRESHOLD
                else ParseStatus.PARTIAL
            )
            if status == ParseStatus.PARTIAL:
                logger.warning(
                    "ExtractionChain: all methods failed threshold for batch %s; "
                    "returning partial result (best_method=%s, confidence=%.3f)",
                    self._batch_id,
                    best.method.value,
                    best.confidence,
                )
            return self._to_parse_result(best, status)

        logger.error(
            "ExtractionChain: complete failure for batch %s — no rows extracted.",
            self._batch_id,
        )
        return ParseResult(
            batch_id=self._batch_id,
            status=ParseStatus.FAILED,
            rows=[],
            metadata=ParseMetadata(),
            error_message="All extraction methods failed to produce usable output.",
        )

    # ── LLM helpers ───────────────────────────────────────────────────────────

    def _try_llm_fallback(self, provider: "BaseLLMProvider") -> ExtractionResult | None:
        """Try LLM_TEXT then LLM_VISION and return the first successful result."""
        from modules.llm.base import TextExtractionRequest, VisionExtractionRequest
        from core.utils.pdf_utils import extract_text_per_page, render_all_pages_to_png

        # LLM text/vision fallback is PDF-specific — skip for CSV/XLS/other binary files.
        # PDF magic bytes are %PDF (0x25 0x50 0x44 0x46).
        if not self._file_bytes[:5].lstrip(b"\xef\xbb\xbf").startswith(b"%PDF"):
            logger.info(
                "ExtractionChain: skipping LLM fallback for batch %s — file is not a PDF",
                self._batch_id,
            )
            return None

        source_type_value = self._parser.source_type.value

        # Step 1: LLM text extraction
        try:
            pages = extract_text_per_page(self._file_bytes)
            combined_text = "\n".join(pages)
            if combined_text.strip():
                req = TextExtractionRequest(
                    batch_id=self._batch_id,
                    source_type=source_type_value,
                    partial_text=combined_text,
                    page_count=len(pages),
                )
                response = provider.extract_text(req)
                # Accept LLM_TEXT only when it produced a complete (non-truncated)
                # response with enough rows to be credible.
                # A truncated or sparse result falls through to LLM_VISION which
                # reads the actual page images and captures all transactions.
                if response.succeeded and not response.is_truncated and len(response.rows) >= 3:
                    logger.info(
                        "ExtractionChain: LLM_TEXT fallback succeeded for batch %s (%d rows)",
                        self._batch_id,
                        len(response.rows),
                    )
                    return self._llm_response_to_result(response, ExtractionMethod.LLM_TEXT)
                if response.rows or response.is_truncated:
                    logger.info(
                        "ExtractionChain: LLM_TEXT produced %d row(s) (truncated=%s) for batch %s "
                        "— falling through to LLM_VISION for complete coverage",
                        len(response.rows),
                        response.is_truncated,
                        self._batch_id,
                    )
        except Exception as exc:  # noqa: BLE001
            logger.warning("ExtractionChain: LLM_TEXT fallback error for batch %s: %s", self._batch_id, exc)

        # Step 2: LLM vision extraction
        try:
            page_images = render_all_pages_to_png(self._file_bytes, dpi=250)
            if page_images:
                req = VisionExtractionRequest(
                    batch_id=self._batch_id,
                    source_type=source_type_value,
                    page_images=page_images,
                )
                response = provider.extract_vision(req)
                if response.succeeded:
                    logger.info(
                        "ExtractionChain: LLM_VISION fallback succeeded for batch %s (%d rows)",
                        self._batch_id,
                        len(response.rows),
                    )
                    return self._llm_response_to_result(response, ExtractionMethod.LLM_VISION)
        except Exception as exc:  # noqa: BLE001
            logger.warning("ExtractionChain: LLM_VISION fallback error for batch %s: %s", self._batch_id, exc)

        logger.warning("ExtractionChain: LLM fallback produced no rows for batch %s", self._batch_id)
        return None

    @staticmethod
    def _llm_response_to_result(
        response: "LLMResponse", method: ExtractionMethod
    ) -> ExtractionResult:
        meta = ParseMetadata(
            total_rows_found=len(response.rows),
            overall_confidence=response.overall_confidence,
            extraction_method=method,
            parser_version=f"llm:{response.model_used}",
        )
        return ExtractionResult(
            rows=response.rows,
            metadata=meta,
            method=method,
            confidence=response.overall_confidence,
        )

    def _to_parse_result(self, result: ExtractionResult, status: ParseStatus) -> ParseResult:
        return ParseResult(
            batch_id=self._batch_id,
            status=status,
            rows=result.rows,
            metadata=result.metadata,
        )
