"""Tests for IdfcPdfParser.parse_text_content() — pure function, no I/O."""

from __future__ import annotations

import uuid

import pytest

from core.models.enums import ExtractionMethod, SourceType, TxnTypeHint
from modules.parser.parsers.idfc_pdf import IdfcPdfParser


@pytest.fixture
def parser() -> IdfcPdfParser:
    return IdfcPdfParser()


@pytest.fixture
def batch_id() -> str:
    return str(uuid.uuid4())


# ── Text fixtures ─────────────────────────────────────────────────────────────
# IDFC format: DD/MM/YYYY  Description  Reference  [Debit]  [Credit]  Balance

IDFC_SINGLE_DEBIT = """\
IDFC FIRST Bank Account Statement

01/01/2026 UPI-SWIGGY FOOD REF987654 450.00  19,550.00

"""

IDFC_SINGLE_CREDIT = """\
IDFC FIRST Bank Account Statement

05/02/2026 NEFT CR SALARY NEFT2026  50,000.00 60,000.00

"""

IDFC_MULTI_TXN = """\
IDFC FIRST Bank Account Statement
Opening Balance : 20,000.00

01/01/2026 UPI-SWIGGY ORDER REF987 450.00  19,550.00
10/01/2026 NEFT-SALARY NEFT001  50,000.00 69,550.00
15/01/2026 ATM CASH WD ATM0001 5,000.00  64,550.00
20/01/2026 IMPS PHONEPE IMPS001 1,200.00  63,350.00
25/01/2026 ECS-INSURANCE ECS0001 3,000.00  60,350.00

Closing Balance : 60,350.00
"""

IDFC_DASH_DATE = """\
IDFC FIRST Bank Statement

01-01-2026 UPI-PAYTM RECHARGE PAYTM1 299.00  19,701.00

"""

IDFC_EMPTY = "IDFC FIRST Bank Account Statement\n\nNo transactions."


# ── Row extraction ────────────────────────────────────────────────────────────

class TestRowExtraction:
    def test_single_debit(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, IDFC_SINGLE_DEBIT)
        assert len(result.rows) == 1
        row = result.rows[0]
        assert row.raw_debit is not None
        assert row.raw_credit is None

    def test_single_credit(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, IDFC_SINGLE_CREDIT)
        assert len(result.rows) == 1
        row = result.rows[0]
        assert row.raw_credit is not None or row.raw_debit is not None

    def test_multiple_rows(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, IDFC_MULTI_TXN)
        assert len(result.rows) == 5

    def test_empty_returns_zero_rows(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, IDFC_EMPTY)
        assert len(result.rows) == 0

    def test_source_type_idfc(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, IDFC_SINGLE_DEBIT)
        assert all(r.source_type == SourceType.IDFC_BANK for r in result.rows)

    def test_batch_id_propagated(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, IDFC_SINGLE_DEBIT)
        assert all(r.batch_id == batch_id for r in result.rows)

    def test_row_numbers_sequential(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, IDFC_MULTI_TXN)
        for i, row in enumerate(result.rows, start=1):
            assert row.row_number == i

    def test_dash_date_accepted(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, IDFC_DASH_DATE)
        assert len(result.rows) == 1


# ── Transaction type inference ────────────────────────────────────────────────

class TestTxnTypes:
    def test_upi_detected(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, IDFC_SINGLE_DEBIT)
        assert result.rows[0].txn_type_hint == TxnTypeHint.UPI

    def test_neft_detected(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, IDFC_SINGLE_CREDIT)
        assert result.rows[0].txn_type_hint == TxnTypeHint.NEFT

    def test_atm_detected(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, IDFC_MULTI_TXN)
        assert any(r.txn_type_hint == TxnTypeHint.ATM_WITHDRAWAL for r in result.rows)

    def test_imps_detected(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, IDFC_MULTI_TXN)
        assert any(r.txn_type_hint == TxnTypeHint.IMPS for r in result.rows)


# ── Metadata ──────────────────────────────────────────────────────────────────

class TestMetadata:
    def test_confidence_positive(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, IDFC_MULTI_TXN)
        assert result.confidence > 0.0

    def test_confidence_zero_for_empty(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, IDFC_EMPTY)
        assert result.confidence <= 0.15

    def test_method_text_layer(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, IDFC_SINGLE_DEBIT)
        assert result.method == ExtractionMethod.TEXT_LAYER
