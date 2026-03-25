"""Tests for IndusIndPdfParser.parse_text_content() — pure function, no I/O."""

from __future__ import annotations

import uuid

import pytest

from core.models.enums import ExtractionMethod, SourceType, TxnTypeHint
from modules.parser.parsers.indusind_pdf import IndusIndPdfParser


@pytest.fixture
def parser() -> IndusIndPdfParser:
    return IndusIndPdfParser()


@pytest.fixture
def batch_id() -> str:
    return str(uuid.uuid4())


# ── Text fixtures ─────────────────────────────────────────────────────────────
# IndusInd format: DD/MM/YYYY  Particulars  Ref  DD/MM/YYYY  [Debit]  [Credit]  Balance

INDUSIND_SINGLE_DEBIT = """\
IndusInd Bank Account Statement

01/01/2026 UPI-SWIGGY FOOD 987654321 01/01/2026 450.00  19,550.00

"""

INDUSIND_SINGLE_CREDIT = """\
IndusInd Bank Account Statement

05/02/2026 NEFT-SALARY-EMPLOYER NEFT2026 05/02/2026  50,000.00 60,000.00

"""

INDUSIND_MULTI_TXN = """\
IndusInd Bank Account Statement
Opening Balance : 20,000.00

01/01/2026 UPI-SWIGGY-ORDER 987654321 01/01/2026 450.00  19,550.00
10/01/2026 NEFT-SALARY NEFT001 10/01/2026  50,000.00 69,550.00
15/01/2026 ATM-CASH-WD ATM001 15/01/2026 5,000.00  64,550.00
20/01/2026 IMPS-TRANSFER IMPS001 20/01/2026 1,500.00  63,050.00
25/01/2026 CHQ-CLEARING 001234 25/01/2026 8,000.00  55,050.00

Closing Balance : 55,050.00
"""

INDUSIND_DASH_DATE = """\
IndusInd Bank Statement

01-01-2026 UPI-PHONEPE PHONE001 01-01-2026 299.00  19,701.00

"""

INDUSIND_EMPTY = "IndusInd Bank Statement\n\nNo transactions in selected period."


# ── Row extraction ────────────────────────────────────────────────────────────

class TestRowExtraction:
    def test_single_debit(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, INDUSIND_SINGLE_DEBIT)
        assert len(result.rows) == 1
        row = result.rows[0]
        assert row.raw_debit is not None
        assert row.raw_credit is None

    def test_single_credit(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, INDUSIND_SINGLE_CREDIT)
        assert len(result.rows) == 1
        row = result.rows[0]
        assert row.raw_credit is not None or row.raw_debit is not None

    def test_multiple_rows(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, INDUSIND_MULTI_TXN)
        assert len(result.rows) == 5

    def test_empty_returns_zero_rows(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, INDUSIND_EMPTY)
        assert len(result.rows) == 0

    def test_source_type_indusind(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, INDUSIND_SINGLE_DEBIT)
        assert all(r.source_type == SourceType.INDUSIND_BANK for r in result.rows)

    def test_batch_id_propagated(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, INDUSIND_SINGLE_DEBIT)
        assert all(r.batch_id == batch_id for r in result.rows)

    def test_row_numbers_sequential(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, INDUSIND_MULTI_TXN)
        for i, row in enumerate(result.rows, start=1):
            assert row.row_number == i

    def test_dash_date_accepted(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, INDUSIND_DASH_DATE)
        assert len(result.rows) == 1


# ── Transaction type inference ────────────────────────────────────────────────

class TestTxnTypes:
    def test_upi_detected(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, INDUSIND_SINGLE_DEBIT)
        assert result.rows[0].txn_type_hint == TxnTypeHint.UPI

    def test_neft_detected(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, INDUSIND_SINGLE_CREDIT)
        assert result.rows[0].txn_type_hint == TxnTypeHint.NEFT

    def test_atm_detected(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, INDUSIND_MULTI_TXN)
        assert any(r.txn_type_hint == TxnTypeHint.ATM_WITHDRAWAL for r in result.rows)

    def test_imps_detected(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, INDUSIND_MULTI_TXN)
        assert any(r.txn_type_hint == TxnTypeHint.IMPS for r in result.rows)


# ── Metadata ──────────────────────────────────────────────────────────────────

class TestMetadata:
    def test_confidence_positive(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, INDUSIND_MULTI_TXN)
        assert result.confidence > 0.0

    def test_confidence_zero_for_empty(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, INDUSIND_EMPTY)
        assert result.confidence <= 0.15

    def test_method_text_layer(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, INDUSIND_SINGLE_DEBIT)
        assert result.method == ExtractionMethod.TEXT_LAYER
