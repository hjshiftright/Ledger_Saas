"""Tests for ExtractionChain — fallback orchestration logic."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.models.enums import ExtractionMethod, ParseStatus, SourceType
from core.models.raw_parsed_row import ParseMetadata, RawParsedRow
from modules.parser.base import BaseParser, ExtractionResult
from modules.parser.chain import ExtractionChain

CONFIDENCE_THRESHOLD = 0.75


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_row(batch_id: str, row_num: int = 1) -> RawParsedRow:
    return RawParsedRow(
        batch_id=batch_id,
        source_type=SourceType.HDFC_BANK,
        parser_version="1.0",
        extraction_method=ExtractionMethod.TEXT_LAYER,
        raw_date="01/01/2026",
        raw_narration=f"Test transaction {row_num}",
        raw_debit="100.00",
        row_confidence=0.9,
        row_number=row_num,
    )


def _make_result(batch_id: str, confidence: float, method: ExtractionMethod, n_rows: int = 3) -> ExtractionResult:
    rows = [_make_row(batch_id, i) for i in range(1, n_rows + 1)]
    meta = ParseMetadata(total_rows_found=n_rows, overall_confidence=confidence)
    return ExtractionResult(rows=rows, metadata=meta, method=method, confidence=confidence)


def _make_empty_result(method: ExtractionMethod) -> ExtractionResult:
    return ExtractionResult(rows=[], metadata=ParseMetadata(), method=method, confidence=0.0)


class _StubParser(BaseParser):
    """Parser that returns pre-configured results per method."""

    source_type = SourceType.HDFC_BANK
    version = "0.1"

    def __init__(self, results_map: dict[ExtractionMethod, ExtractionResult], methods: list[ExtractionMethod] | None = None) -> None:
        self._map = results_map
        self._methods = methods or [ExtractionMethod.TEXT_LAYER, ExtractionMethod.TABLE_EXTRACTION, ExtractionMethod.OCR]

    def supported_methods(self) -> list[ExtractionMethod]:
        return self._methods

    def extract(self, batch_id, file_bytes, method) -> ExtractionResult:
        return self._map.get(method, _make_empty_result(method))


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestExtractionChainSuccess:
    def test_stops_at_first_success(self, batch_id):
        """Chain stops on the first method that meets the threshold."""
        text_result = _make_result(batch_id, 0.90, ExtractionMethod.TEXT_LAYER)
        table_result = _make_result(batch_id, 0.85, ExtractionMethod.TABLE_EXTRACTION)

        parser = _StubParser({
            ExtractionMethod.TEXT_LAYER: text_result,
            ExtractionMethod.TABLE_EXTRACTION: table_result,
        })

        chain = ExtractionChain(parser, batch_id, b"mock")
        result = chain.run()

        assert result.status == ParseStatus.SUCCESS
        assert result.rows == text_result.rows  # Text layer rows (first attempted)
        assert result.row_count == 3

    def test_succeeds_on_second_method(self, batch_id):
        """If text layer fails threshold, chain tries table extraction."""
        text_result = _make_result(batch_id, 0.30, ExtractionMethod.TEXT_LAYER)  # Below threshold
        table_result = _make_result(batch_id, 0.88, ExtractionMethod.TABLE_EXTRACTION)

        parser = _StubParser({
            ExtractionMethod.TEXT_LAYER: text_result,
            ExtractionMethod.TABLE_EXTRACTION: table_result,
        })

        chain = ExtractionChain(parser, batch_id, b"mock")
        result = chain.run()

        assert result.status == ParseStatus.SUCCESS
        assert result.rows == table_result.rows

    def test_succeeds_on_third_method_ocr(self, batch_id):
        """Chain reaches OCR if both text and table fail."""
        ocr_result = _make_result(batch_id, 0.80, ExtractionMethod.OCR)

        parser = _StubParser({
            ExtractionMethod.TEXT_LAYER: _make_empty_result(ExtractionMethod.TEXT_LAYER),
            ExtractionMethod.TABLE_EXTRACTION: _make_empty_result(ExtractionMethod.TABLE_EXTRACTION),
            ExtractionMethod.OCR: ocr_result,
        })

        chain = ExtractionChain(parser, batch_id, b"mock")
        result = chain.run()

        assert result.status == ParseStatus.SUCCESS

    def test_result_has_rows(self, batch_id):
        text_result = _make_result(batch_id, 0.90, ExtractionMethod.TEXT_LAYER, n_rows=5)

        parser = _StubParser({ExtractionMethod.TEXT_LAYER: text_result})
        chain = ExtractionChain(parser, batch_id, b"mock")
        result = chain.run()

        assert result.row_count == 5


class TestExtractionChainPartial:
    def test_returns_partial_when_below_threshold(self, batch_id):
        """All methods below threshold → PARTIAL (rows exist but low confidence)."""
        parser = _StubParser({
            ExtractionMethod.TEXT_LAYER: _make_result(batch_id, 0.40, ExtractionMethod.TEXT_LAYER),
            ExtractionMethod.TABLE_EXTRACTION: _make_result(batch_id, 0.50, ExtractionMethod.TABLE_EXTRACTION),
            ExtractionMethod.OCR: _make_result(batch_id, 0.45, ExtractionMethod.OCR),
        })

        chain = ExtractionChain(parser, batch_id, b"mock")
        result = chain.run()

        assert result.status == ParseStatus.PARTIAL
        assert result.row_count > 0  # Best result rows are kept

    def test_returns_best_rows_when_partial(self, batch_id):
        """The best (highest confidence) result's rows are returned in PARTIAL state."""
        low_result = _make_result(batch_id, 0.30, ExtractionMethod.TEXT_LAYER, n_rows=2)
        medium_result = _make_result(batch_id, 0.55, ExtractionMethod.TABLE_EXTRACTION, n_rows=5)
        bad_result = _make_result(batch_id, 0.20, ExtractionMethod.OCR, n_rows=1)

        parser = _StubParser({
            ExtractionMethod.TEXT_LAYER: low_result,
            ExtractionMethod.TABLE_EXTRACTION: medium_result,
            ExtractionMethod.OCR: bad_result,
        })

        chain = ExtractionChain(parser, batch_id, b"mock")
        result = chain.run()

        assert result.status == ParseStatus.PARTIAL
        assert result.row_count == 5  # Best (TABLE_EXTRACTION) rows

    def test_equal_confidence_prefers_more_rows(self, batch_id):
        """When two methods score the same (e.g. 0.6), keep the one with more rows."""
        text_result = _make_result(batch_id, 0.60, ExtractionMethod.TEXT_LAYER, n_rows=2)
        table_result = _make_result(batch_id, 0.60, ExtractionMethod.TABLE_EXTRACTION, n_rows=8)

        parser = _StubParser(
            {
                ExtractionMethod.TEXT_LAYER: text_result,
                ExtractionMethod.TABLE_EXTRACTION: table_result,
            },
            methods=[ExtractionMethod.TEXT_LAYER, ExtractionMethod.TABLE_EXTRACTION],
        )

        chain = ExtractionChain(parser, batch_id, b"mock")
        result = chain.run()

        assert result.status == ParseStatus.PARTIAL
        assert result.row_count == 8


class TestExtractionChainFailure:
    def test_returns_failed_when_no_rows_at_all(self, batch_id):
        """All methods produce zero rows → FAILED."""
        parser = _StubParser({
            ExtractionMethod.TEXT_LAYER: _make_empty_result(ExtractionMethod.TEXT_LAYER),
            ExtractionMethod.TABLE_EXTRACTION: _make_empty_result(ExtractionMethod.TABLE_EXTRACTION),
            ExtractionMethod.OCR: _make_empty_result(ExtractionMethod.OCR),
        })

        chain = ExtractionChain(parser, batch_id, b"mock")
        result = chain.run()

        assert result.status == ParseStatus.FAILED
        assert result.row_count == 0

    def test_exception_in_parser_is_handled(self, batch_id):
        """If a parser method raises, the chain continues to the next method."""

        class _ExplodingParser(BaseParser):
            source_type = SourceType.HDFC_BANK
            version = "0.1"
            _call_count = 0

            def supported_methods(self):
                return [ExtractionMethod.TEXT_LAYER, ExtractionMethod.TABLE_EXTRACTION]

            def extract(self, batch_id, file_bytes, method) -> ExtractionResult:
                if method == ExtractionMethod.TEXT_LAYER:
                    raise RuntimeError("Simulated extraction error")
                return _make_result(batch_id, 0.85, ExtractionMethod.TABLE_EXTRACTION)

        parser = _ExplodingParser()
        chain = ExtractionChain(parser, batch_id, b"mock")
        result = chain.run()

        assert result.status == ParseStatus.SUCCESS


class TestExtractionChainSingleMethod:
    def test_csv_parser_single_method(self, batch_id):
        """CSV parsers only declare TABLE_EXTRACTION — chain respects that."""
        table_result = _make_result(batch_id, 0.85, ExtractionMethod.TABLE_EXTRACTION)

        parser = _StubParser(
            {ExtractionMethod.TABLE_EXTRACTION: table_result},
            methods=[ExtractionMethod.TABLE_EXTRACTION],
        )

        chain = ExtractionChain(parser, batch_id, b"mock")
        result = chain.run()

        assert result.status == ParseStatus.SUCCESS


# ── LLM fallback ──────────────────────────────────────────────────────────────

class TestExtractionChainLLMFallback:
    """Tests for the LLM fallback path in ExtractionChain.run(llm_provider=...)."""

    def _make_llm_response(self, batch_id: str, rows: list, confidence: float = 0.85):
        from modules.llm.base import LLMResponse
        return LLMResponse(
            batch_id=batch_id,
            rows=rows,
            overall_confidence=confidence,
            model_used="test-model",
            provider_name="TEST",
        )

    def test_llm_not_called_when_traditional_succeeds(self, batch_id):
        """If a traditional method succeeds, LLM must not be called."""
        text_result = _make_result(batch_id, 0.90, ExtractionMethod.TEXT_LAYER)
        parser = _StubParser({ExtractionMethod.TEXT_LAYER: text_result})
        provider = MagicMock()

        with patch("modules.parser.chain.ExtractionChain._try_llm_fallback") as mock_llm:
            chain = ExtractionChain(parser, batch_id, b"mock")
            chain.run(llm_provider=provider)
            mock_llm.assert_not_called()

    def test_llm_called_when_all_methods_fail(self, batch_id):
        """When every method returns zero rows, LLM fallback must be attempted."""
        parser = _StubParser({
            ExtractionMethod.TEXT_LAYER: _make_empty_result(ExtractionMethod.TEXT_LAYER),
            ExtractionMethod.TABLE_EXTRACTION: _make_empty_result(ExtractionMethod.TABLE_EXTRACTION),
            ExtractionMethod.OCR: _make_empty_result(ExtractionMethod.OCR),
        })
        provider = MagicMock()

        with patch("modules.parser.chain.ExtractionChain._try_llm_fallback", return_value=None) as mock_llm:
            chain = ExtractionChain(parser, batch_id, b"mock")
            chain.run(llm_provider=provider)
            mock_llm.assert_called_once_with(provider)

    def test_llm_called_when_below_threshold(self, batch_id):
        """When best traditional result is below threshold, LLM fallback is attempted."""
        parser = _StubParser({
            ExtractionMethod.TEXT_LAYER: _make_result(batch_id, 0.40, ExtractionMethod.TEXT_LAYER),
            ExtractionMethod.TABLE_EXTRACTION: _make_result(batch_id, 0.50, ExtractionMethod.TABLE_EXTRACTION),
            ExtractionMethod.OCR: _make_result(batch_id, 0.45, ExtractionMethod.OCR),
        })
        provider = MagicMock()

        with patch("modules.parser.chain.ExtractionChain._try_llm_fallback", return_value=None) as mock_llm:
            chain = ExtractionChain(parser, batch_id, b"mock")
            chain.run(llm_provider=provider)
            mock_llm.assert_called_once()

    def test_llm_result_used_when_better(self, batch_id):
        """LLM result supersedes a low-confidence traditional result."""
        low_result = _make_result(batch_id, 0.30, ExtractionMethod.TEXT_LAYER)
        parser = _StubParser({ExtractionMethod.TEXT_LAYER: low_result})

        llm_rows = [_make_row(batch_id, i) for i in range(1, 6)]
        llm_response = self._make_llm_response(batch_id, llm_rows, confidence=0.88)

        provider = MagicMock()
        provider.extract_text.return_value = llm_response

        with patch("core.utils.pdf_utils.extract_text_per_page", return_value=["page text"]):
            with patch("core.utils.pdf_utils.render_all_pages_to_png", return_value=[]):
                chain = ExtractionChain(parser, batch_id, b"%PDF-mock")
                result = chain.run(llm_provider=provider)

        assert result.row_count == 5
        assert result.status == ParseStatus.SUCCESS

    def test_llm_vision_tried_when_text_empty(self, batch_id):
        """If LLM text extraction returns no rows, vision path must be tried."""
        from modules.llm.base import LLMResponse

        empty_resp = LLMResponse(batch_id=batch_id, rows=[], overall_confidence=0.0, model_used="m", provider_name="T")
        vision_rows = [_make_row(batch_id)]
        vision_resp = self._make_llm_response(batch_id, vision_rows, confidence=0.80)

        provider = MagicMock()
        provider.extract_text.return_value = empty_resp
        provider.extract_vision.return_value = vision_resp

        parser = _StubParser(
            {ExtractionMethod.TEXT_LAYER: _make_empty_result(ExtractionMethod.TEXT_LAYER)},
            methods=[ExtractionMethod.TEXT_LAYER],
        )

        with patch("core.utils.pdf_utils.extract_text_per_page", return_value=["text"]):
            with patch("core.utils.pdf_utils.render_all_pages_to_png", return_value=[b"img"]):
                chain = ExtractionChain(parser, batch_id, b"%PDF-mock")
                result = chain.run(llm_provider=provider)

        provider.extract_vision.assert_called_once()
        assert result.row_count == 1

    def test_no_provider_never_calls_llm(self, batch_id):
        """When llm_provider=None, the LLM path is never entered."""
        parser = _StubParser(
            {ExtractionMethod.TEXT_LAYER: _make_empty_result(ExtractionMethod.TEXT_LAYER)},
            methods=[ExtractionMethod.TEXT_LAYER],
        )

        with patch("modules.parser.chain.ExtractionChain._try_llm_fallback") as mock_llm:
            chain = ExtractionChain(parser, batch_id, b"mock")
            chain.run(llm_provider=None)
            mock_llm.assert_not_called()
