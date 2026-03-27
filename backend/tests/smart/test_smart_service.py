"""Tests for SmartProcessor._enhance_with_llm() — LLM categorisation logic."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock

import pytest

from core.models.enums import ConfidenceBand, ExtractionMethod, SourceType, TxnTypeHint
from core.models.raw_parsed_row import RawParsedRow
from modules.llm.base import LLMResponse
from services.normalize_service import NormalizedTransaction
from services.smart_service import SmartProcessor, SmartProcessingOptions


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_norm_row(
    batch_id: str,
    narration: str = "UPI SWIGGY FOOD",
    category: str = "EXPENSE_OTHER",
    category_confidence: float = 0.30,
    is_debit: bool = True,
) -> NormalizedTransaction:
    return NormalizedTransaction(
        row_id=str(uuid.uuid4()),
        batch_id=batch_id,
        source_type=SourceType.HDFC_BANK_CSV.value,
        txn_date=date(2026, 1, 15),
        raw_date="15/01/2026",
        amount=Decimal("-450.00") if is_debit else Decimal("50000.00"),
        is_debit=is_debit,
        raw_debit="450.00" if is_debit else None,
        raw_credit=None if is_debit else "50000.00",
        raw_balance="19550.00",
        closing_balance=Decimal("19550.00"),
        narration=narration,
        raw_narration=narration,
        reference=None,
        txn_type=TxnTypeHint.UPI,
        row_confidence=0.85,
        extra_fields={
            "category": category,
            "category_confidence": category_confidence,
            "confidence_band": ConfidenceBand.RED.value,
        },
    )


def _make_llm_row(
    batch_id: str,
    narration_prefix: str,
    suggested_category: str,
    confidence: float = 0.90,
) -> RawParsedRow:
    """Simulate an LLM-returned RawParsedRow carrying a suggested category."""
    return RawParsedRow(
        batch_id=batch_id,
        source_type=SourceType.GENERIC_CSV,
        parser_version="llm:test-model",
        extraction_method=ExtractionMethod.LLM_TEXT,
        raw_date="15/01/2026",
        raw_narration=narration_prefix,
        row_confidence=confidence,
        extra_fields={"category_code": suggested_category},
    )


def _make_llm_provider(llm_rows: list[RawParsedRow], overall_confidence: float = 0.85):
    provider = MagicMock()
    response = LLMResponse(
        batch_id="",
        rows=llm_rows,
        overall_confidence=overall_confidence,
        model_used="test-model",
        provider_name="TEST",
    )
    provider.extract_text.return_value = response
    return provider


# ── _enhance_with_llm unit tests ──────────────────────────────────────────────

class TestEnhanceWithLLM:
    """Direct unit tests for SmartProcessor._enhance_with_llm()."""

    @pytest.fixture
    def processor(self) -> SmartProcessor:
        return SmartProcessor()

    def test_returns_all_rows(self, processor, batch_id, user_id):
        rows = [_make_norm_row(batch_id) for _ in range(3)]
        provider = _make_llm_provider([])
        enhanced = processor._enhance_with_llm(user_id, batch_id, rows, provider)
        assert len(enhanced) == 3

    def test_sets_llm_enhanced_flag(self, processor, batch_id, user_id):
        rows = [_make_norm_row(batch_id)]
        provider = _make_llm_provider([])
        enhanced = processor._enhance_with_llm(user_id, batch_id, rows, provider)
        assert enhanced[0].extra_fields["llm_enhanced"] is True

    def test_sets_category_method(self, processor, batch_id, user_id):
        rows = [_make_norm_row(batch_id)]
        provider = _make_llm_provider([])
        enhanced = processor._enhance_with_llm(user_id, batch_id, rows, provider)
        assert enhanced[0].extra_fields["category_method"] == "llm"

    def test_confidence_increased(self, processor, batch_id, user_id):
        rows = [_make_norm_row(batch_id, category_confidence=0.30)]
        provider = _make_llm_provider([])
        enhanced = processor._enhance_with_llm(user_id, batch_id, rows, provider)
        new_conf = enhanced[0].extra_fields["category_confidence"]
        assert new_conf > 0.30

    def test_confidence_capped_at_095(self, processor, batch_id, user_id):
        rows = [_make_norm_row(batch_id, category_confidence=0.90)]
        provider = _make_llm_provider([])
        enhanced = processor._enhance_with_llm(user_id, batch_id, rows, provider)
        assert enhanced[0].extra_fields["category_confidence"] <= 0.95

    def test_llm_suggested_category_applied(self, processor, batch_id, user_id):
        """When the LLM suggests a category for a specific TXN index, it must be applied."""
        rows = [_make_norm_row(batch_id, narration="UPI SWIGGY FOOD")]
        llm_row = _make_llm_row(batch_id, "TXN_0: UPI SWIGGY FOOD", "EXPENSE_FOOD")
        provider = _make_llm_provider([llm_row])

        enhanced = processor._enhance_with_llm(user_id, batch_id, rows, provider)

        assert enhanced[0].extra_fields["category"] == "EXPENSE_FOOD"
        assert enhanced[0].extra_fields["llm_suggested_category"] == "EXPENSE_FOOD"

    def test_llm_suggested_category_multi_row(self, processor, batch_id, user_id):
        """LLM categories must be matched to the correct row by TXN index."""
        rows = [
            _make_norm_row(batch_id, narration="SWIGGY FOOD"),
            _make_norm_row(batch_id, narration="NEFT SALARY", is_debit=False),
        ]
        llm_rows = [
            _make_llm_row(batch_id, "TXN_0: SWIGGY FOOD", "EXPENSE_FOOD"),
            _make_llm_row(batch_id, "TXN_1: NEFT SALARY", "INCOME_SALARY"),
        ]
        provider = _make_llm_provider(llm_rows)
        enhanced = processor._enhance_with_llm(user_id, batch_id, rows, provider)

        assert enhanced[0].extra_fields["category"] == "EXPENSE_FOOD"
        assert enhanced[1].extra_fields["category"] == "INCOME_SALARY"

    def test_uses_conf_bump_when_no_matching_llm_row(self, processor, batch_id, user_id):
        """Rows with no LLM match still get the +0.15 confidence bump."""
        rows = [_make_norm_row(batch_id, category_confidence=0.20)]
        # LLM returns a row for index 99 (no match for index 0)
        llm_row = _make_llm_row(batch_id, "TXN_99: SOMETHING", "EXPENSE_OTHER")
        provider = _make_llm_provider([llm_row])

        enhanced = processor._enhance_with_llm(user_id, batch_id, rows, provider)
        new_conf = enhanced[0].extra_fields["category_confidence"]
        assert new_conf == pytest.approx(0.35, abs=0.01)

    def test_graceful_degradation_on_llm_error(self, processor, batch_id, user_id):
        """If provider.extract_text raises, rows still get the confidence bump."""
        rows = [_make_norm_row(batch_id, category_confidence=0.20)]
        provider = MagicMock()
        provider.extract_text.side_effect = RuntimeError("LLM API error")

        enhanced = processor._enhance_with_llm(user_id, batch_id, rows, provider)

        assert len(enhanced) == 1
        assert enhanced[0].extra_fields["llm_enhanced"] is True
        assert enhanced[0].extra_fields["category_method"] == "llm_fallback"
        assert enhanced[0].extra_fields["category_confidence"] > 0.20

    def test_extract_text_called_with_narrations(self, processor, batch_id, user_id):
        """provider.extract_text must be called exactly once with narration context."""
        rows = [
            _make_norm_row(batch_id, narration="SWIGGY UPI"),
            _make_norm_row(batch_id, narration="AMAZON SHOPPING"),
        ]
        provider = _make_llm_provider([])
        processor._enhance_with_llm(user_id, batch_id, rows, provider)

        provider.extract_text.assert_called_once()
        call_arg = provider.extract_text.call_args[0][0]
        assert "TXN_0: SWIGGY UPI" in call_arg.partial_text
        assert "TXN_1: AMAZON SHOPPING" in call_arg.partial_text


# ── SmartProcessingOptions ────────────────────────────────────────────────────

class TestSmartProcessingOptions:
    def test_default_use_llm_false(self):
        opts = SmartProcessingOptions()
        assert opts.use_llm is False

    def test_default_llm_provider_none(self):
        opts = SmartProcessingOptions()
        assert opts.llm_provider is None

    def test_llm_provider_accepted(self):
        mock_provider = MagicMock()
        opts = SmartProcessingOptions(use_llm=True, llm_provider=mock_provider)
        assert opts.llm_provider is mock_provider


# ── process_batch integration (smoke) ─────────────────────────────────────────

class TestSmartProcessorBatch:
    """Smoke tests for the full process_batch pipeline with and without LLM."""

    @pytest.fixture
    def processor(self) -> SmartProcessor:
        return SmartProcessor()

    def _make_raw_rows(self, batch_id: str, n: int = 3) -> list[RawParsedRow]:
        rows = []
        for i in range(n):
            rows.append(RawParsedRow(
                batch_id=batch_id,
                source_type=SourceType.HDFC_BANK_CSV,
                parser_version="1.0",
                extraction_method=ExtractionMethod.TABLE_EXTRACTION,
                raw_date="15/01/2026",
                raw_narration=f"UPI SWIGGY TXN {i}",
                raw_debit="100.00",
                row_confidence=0.85,
                row_number=i + 1,
            ))
        return rows

    async def test_process_batch_returns_result(self, processor, batch_id, user_id):
        raw_rows = self._make_raw_rows(batch_id)
        result = await processor.process_batch(user_id, batch_id, raw_rows)
        assert result.batch_id == batch_id
        assert result.raw_rows_count == 3

    async def test_process_batch_without_llm_no_enhancement(self, processor, batch_id, user_id):
        raw_rows = self._make_raw_rows(batch_id)
        opts = SmartProcessingOptions(use_llm=False)
        result = await processor.process_batch(user_id, batch_id, raw_rows, options=opts)
        assert result.llm_enhanced_count == 0

    async def test_process_batch_llm_skipped_when_provider_none(self, processor, batch_id, user_id):
        """use_llm=True but no provider → LLM enhancement must be skipped."""
        raw_rows = self._make_raw_rows(batch_id)
        opts = SmartProcessingOptions(use_llm=True, llm_provider=None)
        result = await processor.process_batch(user_id, batch_id, raw_rows, options=opts)
        assert result.llm_enhanced_count == 0
