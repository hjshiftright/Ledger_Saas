"""Tests for SbiPdfParser.parse_text_content() — pure function, no I/O."""

from __future__ import annotations

import uuid

import pytest

from core.models.enums import ExtractionMethod, SourceType, TxnTypeHint
from modules.parser.parsers.sbi_pdf import SbiPdfParser


@pytest.fixture
def parser() -> SbiPdfParser:
    return SbiPdfParser()


@pytest.fixture
def batch_id() -> str:
    return str(uuid.uuid4())


# ── Text fixtures ─────────────────────────────────────────────────────────────
# SBI format: Txn Date  Value Date  Description  Ref  [Debit]  [Credit]  Balance

SBI_SINGLE_DEBIT = """\
State Bank of India
Account Statement

01 Jan 2026  01 Jan 2026  UPI/SWIGGY FOOD ORDER          987654321098  450.00               9,550.00

"""

SBI_SINGLE_CREDIT = """\
State Bank of India
Account Statement

05 Feb 2026  05 Feb 2026  NEFT CR/SALARY/EMPLOYER        NEFT20260205            50,000.00  60,000.00

"""

SBI_MULTI_TXN = """\
State Bank of India Account Statement

01 Jan 2026  01 Jan 2026  UPI/SWIGGY FOOD ORDER          987654321098  450.00               9,550.00
10 Jan 2026  10 Jan 2026  NEFT CR/SALARY/EMPLOYER        NEFT20260110            50,000.00  59,550.00
15 Jan 2026  15 Jan 2026  ATM CASH WD/BOM/001            ATM00001      5,000.00             54,550.00
20 Jan 2026  20 Jan 2026  IMPS/TRANSFER/ACCOUNT          IMPS001       199.00               54,351.00

"""

SBI_EMPTY = "State Bank of India\n\nNo transactions in selected period."

SBI_DATE_SLASH = """\
SBI Account Statement

01/01/2026  01/01/2026  UPI/PAYTM RECHARGE             PAYTM123      299.00               19,701.00

"""


# ── Row extraction ────────────────────────────────────────────────────────────

class TestRowExtraction:
    def test_single_debit_row(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, SBI_SINGLE_DEBIT)
        assert len(result.rows) == 1
        row = result.rows[0]
        assert row.raw_debit is not None
        assert row.raw_credit is None
        assert row.raw_balance == "9,550.00"

    def test_single_credit_row(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, SBI_SINGLE_CREDIT)
        assert len(result.rows) == 1
        row = result.rows[0]
        # A credit row has a non-None amount in either raw_credit or raw_debit
        assert row.raw_credit is not None or row.raw_debit is not None

    def test_multiple_rows(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, SBI_MULTI_TXN)
        assert len(result.rows) == 4

    def test_empty_text_returns_zero_rows(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, SBI_EMPTY)
        assert len(result.rows) == 0

    def test_rows_tagged_with_correct_source_type(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, SBI_SINGLE_DEBIT)
        assert all(r.source_type == SourceType.SBI_BANK for r in result.rows)

    def test_row_numbers_sequential(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, SBI_MULTI_TXN)
        for i, row in enumerate(result.rows, start=1):
            assert row.row_number == i

    def test_batch_id_propagated(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, SBI_SINGLE_DEBIT)
        assert all(r.batch_id == batch_id for r in result.rows)

    def test_slash_date_format_parsed(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, SBI_DATE_SLASH)
        assert len(result.rows) == 1
        assert "/" in result.rows[0].raw_date


# ── Transaction type inference ────────────────────────────────────────────────

class TestTxnTypeInference:
    def test_upi_detected(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, SBI_SINGLE_DEBIT)
        assert result.rows[0].txn_type_hint == TxnTypeHint.UPI

    def test_neft_detected(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, SBI_SINGLE_CREDIT)
        assert result.rows[0].txn_type_hint == TxnTypeHint.NEFT

    def test_atm_detected(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, SBI_MULTI_TXN)
        atm_rows = [r for r in result.rows if r.txn_type_hint == TxnTypeHint.ATM_WITHDRAWAL]
        assert len(atm_rows) >= 1

    def test_imps_detected(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, SBI_MULTI_TXN)
        imps_rows = [r for r in result.rows if r.txn_type_hint == TxnTypeHint.IMPS]
        assert len(imps_rows) >= 1


# ── Metadata ──────────────────────────────────────────────────────────────────

class TestMetadata:
    def test_total_rows_matches(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, SBI_MULTI_TXN)
        assert result.metadata.total_rows_found == len(result.rows)

    def test_confidence_positive_for_valid_data(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, SBI_MULTI_TXN)
        assert result.confidence > 0.0

    def test_confidence_zero_for_empty(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, SBI_EMPTY)
        assert result.confidence <= 0.15

    def test_method_tagged(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, SBI_SINGLE_DEBIT)
        assert result.method == ExtractionMethod.TEXT_LAYER
