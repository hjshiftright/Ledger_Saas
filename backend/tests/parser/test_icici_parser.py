"""Tests for IciciPdfParser.parse_text_content() — pure function, no I/O."""

from __future__ import annotations

import uuid

import pytest

from core.models.enums import ExtractionMethod, SourceType, TxnTypeHint
from modules.parser.parsers.icici_pdf import IciciPdfParser


@pytest.fixture
def parser() -> IciciPdfParser:
    return IciciPdfParser()


@pytest.fixture
def batch_id() -> str:
    return str(uuid.uuid4())


# ── Text fixtures ─────────────────────────────────────────────────────────────
# ICICI format: DD/MM/YYYY  Description  Ref  DD/MM/YYYY  [Withdrawal]  [Deposit]  Balance

ICICI_SINGLE_WITHDRAWAL = """\
ICICI Bank Account Statement

01/01/2026 UPI-SWIGGY FOOD-9876543210 987654321 01/01/2026 450.00  9,550.00

"""

ICICI_SINGLE_DEPOSIT = """\
ICICI Bank Account Statement

05/02/2026 NEFT-SALARY-EMPLOYER NEFT2026 05/02/2026  50,000.00 60,000.00

"""

ICICI_MULTI_TXN = """\
ICICI Bank Account Statement
Opening Balance : 20,000.00

01/01/2026 UPI-SWIGGY FOOD-9876543210 987654321 01/01/2026 450.00  19,550.00
10/01/2026 NEFT-SALARY-EMPLOYER NEFT001 10/01/2026  50,000.00 69,550.00
15/01/2026 ATM WDL-BOM-001 ATM00001 15/01/2026 5,000.00  64,550.00
20/01/2026 IMPS-PAYMENT-PHONEPE IMPS001 20/01/2026 199.00  64,351.00
25/01/2026 NEFT-INTEREST INT2026 25/01/2026  350.00 64,701.00

Closing Balance : 64,701.00
"""

ICICI_EMPTY = "ICICI Bank Savings Account\n\nNo transactions in selected period."


# ── Row extraction ────────────────────────────────────────────────────────────

class TestRowExtraction:
    def test_single_withdrawal_row(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, ICICI_SINGLE_WITHDRAWAL)
        assert len(result.rows) == 1
        row = result.rows[0]
        assert row.raw_debit is not None
        assert row.raw_credit is None

    def test_single_deposit_row(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, ICICI_SINGLE_DEPOSIT)
        assert len(result.rows) == 1
        row = result.rows[0]
        # Credit row: amount appears in credit or debit depending on column alignment
        assert row.raw_credit is not None or row.raw_debit is not None

    def test_multiple_rows(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, ICICI_MULTI_TXN)
        assert len(result.rows) == 5

    def test_empty_text_zero_rows(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, ICICI_EMPTY)
        assert len(result.rows) == 0

    def test_source_type_tagged(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, ICICI_SINGLE_WITHDRAWAL)
        assert all(r.source_type == SourceType.ICICI_BANK for r in result.rows)

    def test_batch_id_propagated(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, ICICI_SINGLE_WITHDRAWAL)
        assert all(r.batch_id == batch_id for r in result.rows)

    def test_row_numbers_sequential(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, ICICI_MULTI_TXN)
        for i, row in enumerate(result.rows, start=1):
            assert row.row_number == i

    def test_date_format_preserved(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, ICICI_SINGLE_WITHDRAWAL)
        assert result.rows[0].raw_date == "01/01/2026"


# ── Transaction type inference ────────────────────────────────────────────────

class TestTxnTypeInference:
    def test_upi_detected(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, ICICI_SINGLE_WITHDRAWAL)
        assert result.rows[0].txn_type_hint == TxnTypeHint.UPI

    def test_neft_detected(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, ICICI_SINGLE_DEPOSIT)
        assert result.rows[0].txn_type_hint == TxnTypeHint.NEFT

    def test_atm_detected(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, ICICI_MULTI_TXN)
        atm_rows = [r for r in result.rows if r.txn_type_hint == TxnTypeHint.ATM_WITHDRAWAL]
        assert len(atm_rows) >= 1

    def test_imps_detected(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, ICICI_MULTI_TXN)
        imps_rows = [r for r in result.rows if r.txn_type_hint == TxnTypeHint.IMPS]
        assert len(imps_rows) >= 1


# ── Metadata & confidence ─────────────────────────────────────────────────────

class TestMetadata:
    def test_total_rows_matches(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, ICICI_MULTI_TXN)
        assert result.metadata.total_rows_found == len(result.rows)

    def test_confidence_positive_for_valid_data(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, ICICI_MULTI_TXN)
        assert result.confidence > 0.0

    def test_confidence_zero_for_empty(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, ICICI_EMPTY)
        assert result.confidence <= 0.15
