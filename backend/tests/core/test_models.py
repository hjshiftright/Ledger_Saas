"""Tests for core/models/ — RawParsedRow, ParseMetadata, ImportBatch, ColumnMapping,
Transaction, PendingTransaction."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

import pytest

from core.models.column_mapping import ColumnMapping, ColumnPreview
from core.models.enums import BatchStatus, ExtractionMethod, FileFormat, ParseStatus, ReviewStatus, SourceType, TxnTypeHint
from core.models.import_batch import ImportBatch
from core.models.raw_parsed_row import ParseMetadata, ParseResult, RawParsedRow
from core.models.transaction import JournalLine, Transaction
from core.models.pending_transaction import PendingTransaction


class TestRawParsedRow:
    def test_auto_row_id(self, batch_id):
        row = RawParsedRow(
            batch_id=batch_id,
            source_type=SourceType.HDFC_BANK,
            parser_version="1.0",
            extraction_method=ExtractionMethod.TEXT_LAYER,
            raw_date="01/01/2026",
            raw_narration="Test",
            row_confidence=0.9,
        )
        assert uuid.UUID(row.row_id)  # Valid UUID

    def test_optional_fields_default_none(self, batch_id):
        row = RawParsedRow(
            batch_id=batch_id,
            source_type=SourceType.HDFC_BANK,
            parser_version="1.0",
            extraction_method=ExtractionMethod.TEXT_LAYER,
            raw_date="01/01/2026",
            raw_narration="Test",
            row_confidence=0.9,
        )
        assert row.raw_debit is None
        assert row.raw_credit is None
        assert row.folio_id is None
        assert row.fund_isin is None

    def test_txn_type_default_unknown(self, batch_id):
        row = RawParsedRow(
            batch_id=batch_id,
            source_type=SourceType.HDFC_BANK,
            parser_version="1.0",
            extraction_method=ExtractionMethod.TEXT_LAYER,
            raw_date="01/01/2026",
            raw_narration="Test",
            row_confidence=0.9,
        )
        assert row.txn_type_hint == TxnTypeHint.UNKNOWN

    def test_extra_fields_default_empty_dict(self, batch_id):
        row = RawParsedRow(
            batch_id=batch_id,
            source_type=SourceType.HDFC_BANK,
            parser_version="1.0",
            extraction_method=ExtractionMethod.TEXT_LAYER,
            raw_date="01/01/2026",
            raw_narration="Test",
            row_confidence=0.9,
        )
        assert row.extra_fields == {}

    def test_confidence_bounds(self, batch_id):
        with pytest.raises(Exception):  # Pydantic validation error
            RawParsedRow(
                batch_id=batch_id,
                source_type=SourceType.HDFC_BANK,
                parser_version="1.0",
                extraction_method=ExtractionMethod.TEXT_LAYER,
                raw_date="01/01/2026",
                raw_narration="Test",
                row_confidence=1.5,  # Out of [0,1]
            )

    def test_mutable(self, sample_raw_row):
        """RawParsedRow must be mutable (frozen=False) for confidence updates."""
        sample_raw_row.row_confidence = 0.5
        assert sample_raw_row.row_confidence == 0.5


class TestParseMetadata:
    def test_defaults(self):
        meta = ParseMetadata()
        assert meta.total_rows_found == 0
        assert meta.overall_confidence == 0.0
        assert meta.warnings == []

    def test_with_balances(self):
        meta = ParseMetadata(
            opening_balance=Decimal("10000.00"),
            closing_balance=Decimal("9550.00"),
            balance_cross_check_passed=True,
        )
        assert meta.opening_balance == Decimal("10000.00")
        assert meta.balance_cross_check_passed is True


class TestParseResult:
    def test_succeeded_property(self, batch_id):
        result = ParseResult(batch_id=batch_id, status=ParseStatus.SUCCESS)
        assert result.succeeded is True

    def test_partial_not_succeeded(self, batch_id):
        result = ParseResult(batch_id=batch_id, status=ParseStatus.PARTIAL)
        assert result.succeeded is False

    def test_failed_property(self, batch_id):
        result = ParseResult(batch_id=batch_id, status=ParseStatus.FAILED)
        assert result.succeeded is False

    def test_row_count_property(self, batch_id, sample_rows):
        result = ParseResult(batch_id=batch_id, status=ParseStatus.SUCCESS, rows=sample_rows)
        assert result.row_count == 3

    def test_empty_rows_default(self, batch_id):
        result = ParseResult(batch_id=batch_id, status=ParseStatus.PARTIAL)
        assert result.rows == []


class TestImportBatch:
    def test_auto_batch_id(self, user_id, account_id):
        batch = ImportBatch(
            user_id=user_id,
            account_id=account_id,
            filename="test.pdf",
            file_hash="abc",
            format=FileFormat.PDF,
        )
        assert uuid.UUID(batch.batch_id)

    def test_default_status(self, user_id, account_id):
        batch = ImportBatch(
            user_id=user_id,
            account_id=account_id,
            filename="test.pdf",
            file_hash="abc",
            format=FileFormat.PDF,
        )
        assert batch.status == BatchStatus.UPLOADING

    def test_default_counts_zero(self, user_id, account_id):
        batch = ImportBatch(
            user_id=user_id,
            account_id=account_id,
            filename="test.pdf",
            file_hash="abc",
            format=FileFormat.PDF,
        )
        assert batch.txn_found == 0
        assert batch.txn_new == 0
        assert batch.parse_confidence == 0.0


# ── Transaction persistence model ─────────────────────────────────────────────

class TestTransaction:
    def _make_txn(self, **kwargs) -> Transaction:
        defaults = dict(
            user_id="u1",
            account_id="1102",
            batch_id="b1",
            txn_date=date(2026, 1, 15),
            narration="UPI SWIGGY",
            amount=Decimal("-450.00"),
            is_debit=True,
            category_code="EXPENSE_FOOD",
            confidence=0.88,
            source_type=SourceType.HDFC_BANK_CSV,
            original_proposal_id="prop-001",
        )
        defaults.update(kwargs)
        return Transaction(**defaults)

    def test_auto_txn_id(self):
        txn = self._make_txn()
        assert uuid.UUID(txn.txn_id)  # Valid UUID4

    def test_default_created_at_is_set(self):
        txn = self._make_txn()
        assert isinstance(txn.created_at, datetime)

    def test_is_balanced_true_when_entries_balance(self):
        txn = self._make_txn()
        txn.journal_lines = [
            JournalLine("5100", "5100", "Food", debit=Decimal("450")),
            JournalLine("1102", "1102", "HDFC Bank", credit=Decimal("450")),
        ]
        assert txn.is_balanced is True

    def test_is_balanced_false_when_entries_unequal(self):
        txn = self._make_txn()
        txn.journal_lines = [
            JournalLine("5100", "5100", "Food", debit=Decimal("450")),
            JournalLine("1102", "1102", "HDFC Bank", credit=Decimal("400")),
        ]
        assert txn.is_balanced is False

    def test_is_balanced_true_when_no_lines(self):
        txn = self._make_txn()
        assert txn.is_balanced is True  # Empty set is trivially balanced

    def test_extra_fields_default_empty(self):
        txn = self._make_txn()
        assert txn.extra_fields == {}

    def test_approved_fields_default_none(self):
        txn = self._make_txn()
        assert txn.approved_at is None
        assert txn.approved_by is None


# ── PendingTransaction model ──────────────────────────────────────────────────

class TestPendingTransaction:
    def _make_pending(self, **kwargs) -> PendingTransaction:
        defaults = dict(
            user_id="u1",
            batch_id="b1",
            confidence_band="YELLOW",
        )
        defaults.update(kwargs)
        return PendingTransaction(**defaults)

    def test_auto_pending_id(self):
        pending = self._make_pending()
        assert uuid.UUID(pending.pending_id)

    def test_default_status_is_pending(self):
        pending = self._make_pending()
        assert pending.review_status == ReviewStatus.PENDING

    def test_is_actionable_when_pending(self):
        pending = self._make_pending()
        assert pending.is_actionable is True

    def test_is_not_actionable_after_approved(self):
        pending = self._make_pending()
        pending.review_status = ReviewStatus.APPROVED
        assert pending.is_actionable is False

    def test_effective_category_returns_revised_first(self):
        pending = self._make_pending()
        pending.llm_suggested_category = "EXPENSE_FOOD"
        pending.revised_category = "EXPENSE_SHOPPING"
        assert pending.effective_category == "EXPENSE_SHOPPING"

    def test_effective_category_falls_back_to_llm(self):
        pending = self._make_pending()
        pending.llm_suggested_category = "EXPENSE_FOOD"
        assert pending.effective_category == "EXPENSE_FOOD"

    def test_effective_category_none_when_no_proposal(self):
        pending = self._make_pending()
        assert pending.effective_category is None

    def test_created_at_is_set(self):
        pending = self._make_pending()
        assert isinstance(pending.created_at, datetime)

    def test_reviewed_at_default_none(self):
        pending = self._make_pending()
        assert pending.reviewed_at is None


class TestColumnMapping:
    def test_auto_mapping_id(self, user_id):
        mapping = ColumnMapping(
            user_id=user_id,
            format_fingerprint="fp123",
            mapping_label="Test",
            date_column="Date",
            narration_column="Narration",
        )
        assert mapping.mapping_id  # Not empty

    def test_optional_columns_default_none(self, user_id):
        mapping = ColumnMapping(
            user_id=user_id,
            format_fingerprint="fp123",
            mapping_label="Test",
            date_column="Date",
            narration_column="Narration",
        )
        assert mapping.debit_column is None
        assert mapping.credit_column is None
        assert mapping.amount_column is None

    def test_default_date_format(self, user_id):
        mapping = ColumnMapping(
            user_id=user_id,
            format_fingerprint="fp123",
            mapping_label="Test",
            date_column="Date",
            narration_column="Narration",
        )
        assert mapping.date_format == "%d/%m/%Y"
        assert mapping.amount_locale == "IN"
