"""Tests for AxisPdfParser.parse_text_content() — pure function, no I/O."""

from __future__ import annotations

import uuid

import pytest

from core.models.enums import ExtractionMethod, SourceType, TxnTypeHint
from modules.parser.parsers.axis_pdf import AxisPdfParser


@pytest.fixture
def parser() -> AxisPdfParser:
    return AxisPdfParser()


@pytest.fixture
def batch_id() -> str:
    return str(uuid.uuid4())


# ── Text fixtures ─────────────────────────────────────────────────────────────
# Axis format: DD-MM-YYYY  Description  ChqNo  DD-MM-YYYY  [Debit]  [Credit]  Balance

AXIS_SINGLE_DEBIT = """\
Axis Bank Account Statement
Opening Balance : 15,000.00

01-01-2026 UPI/SWIGGY FOOD 987654 01-01-2026 450.00  14,550.00

"""

AXIS_SINGLE_CREDIT = """\
Axis Bank Account Statement
Opening Balance : 10,000.00

05-02-2026 NEFT CR/SALARY NEFT2026 05-02-2026  50,000.00 60,000.00

"""

AXIS_MULTI_TXN = """\
Axis Bank Account Statement
Opening Balance : 20,000.00

01-01-2026 UPI-SWIGGY FOOD 987654 01-01-2026 450.00  19,550.00
10-01-2026 NEFT CR-SALARY NEFT001 10-01-2026  50,000.00 69,550.00
15-01-2026 ATM WD BOM001 ATM001 15-01-2026 5,000.00  64,550.00
20-01-2026 IMPS PHONEPE IMPS001 20-01-2026 199.00  64,351.00
25-01-2026 CHQ CLEARED 001234 25-01-2026 10,000.00  54,351.00

Closing Balance : 54,351.00
"""

AXIS_SLASH_DATE = """\
Axis Bank Account Statement

01/01/2026 UPI/PAYTM TOPUP PAYTM123 01/01/2026 299.00  19,701.00

"""

AXIS_EMPTY = "Axis Bank Account Statement\n\nNo transactions found."


# ── Row extraction ────────────────────────────────────────────────────────────

class TestRowExtraction:
    def test_single_debit_row(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, AXIS_SINGLE_DEBIT)
        assert len(result.rows) == 1
        row = result.rows[0]
        assert row.raw_debit is not None
        assert row.raw_credit is None

    def test_single_credit_row(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, AXIS_SINGLE_CREDIT)
        assert len(result.rows) == 1
        row = result.rows[0]
        assert row.raw_credit is not None or row.raw_debit is not None

    def test_multiple_rows(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, AXIS_MULTI_TXN)
        assert len(result.rows) == 5

    def test_empty_returns_zero_rows(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, AXIS_EMPTY)
        assert len(result.rows) == 0

    def test_source_type_axis(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, AXIS_SINGLE_DEBIT)
        assert all(r.source_type == SourceType.AXIS_BANK for r in result.rows)

    def test_batch_id_propagated(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, AXIS_SINGLE_DEBIT)
        assert all(r.batch_id == batch_id for r in result.rows)

    def test_row_numbers_sequential(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, AXIS_MULTI_TXN)
        for i, row in enumerate(result.rows, start=1):
            assert row.row_number == i

    def test_slash_date_format_accepted(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, AXIS_SLASH_DATE)
        assert len(result.rows) == 1


# ── Transaction type inference ────────────────────────────────────────────────

class TestTxnTypeInference:
    def test_upi_detected(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, AXIS_SINGLE_DEBIT)
        assert result.rows[0].txn_type_hint == TxnTypeHint.UPI

    def test_neft_detected(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, AXIS_SINGLE_CREDIT)
        assert result.rows[0].txn_type_hint == TxnTypeHint.NEFT

    def test_atm_detected(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, AXIS_MULTI_TXN)
        atm_rows = [r for r in result.rows if r.txn_type_hint == TxnTypeHint.ATM_WITHDRAWAL]
        assert len(atm_rows) >= 1

    def test_cheque_detected(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, AXIS_MULTI_TXN)
        chq_rows = [r for r in result.rows if r.txn_type_hint == TxnTypeHint.CHEQUE]
        assert len(chq_rows) >= 1


# ── Metadata ──────────────────────────────────────────────────────────────────

class TestMetadata:
    def test_confidence_positive(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, AXIS_MULTI_TXN)
        assert result.confidence > 0.0

    def test_confidence_zero_for_empty(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, AXIS_EMPTY)
        assert result.confidence <= 0.15

    def test_total_rows_in_metadata(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, AXIS_MULTI_TXN)
        assert result.metadata.total_rows_found == 5
