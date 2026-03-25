"""Tests for KotakPdfParser.parse_text_content() — pure function, no I/O."""

from __future__ import annotations

import uuid

import pytest

from core.models.enums import ExtractionMethod, SourceType, TxnTypeHint
from modules.parser.parsers.kotak_pdf import KotakPdfParser


@pytest.fixture
def parser() -> KotakPdfParser:
    return KotakPdfParser()


@pytest.fixture
def batch_id() -> str:
    return str(uuid.uuid4())


# ── Text fixtures ─────────────────────────────────────────────────────────────
# Kotak format: DD/MM/YYYY or DD-MM-YYYY  Description  Ref  [Debit]  [Credit]  Balance

KOTAK_SINGLE_DEBIT = """\
Kotak Mahindra Bank - Account Statement
Opening Balance : 25,000.00

01/01/2026 UPI-ZOMATO-ORDER 123456789 450.00  24,550.00

"""

KOTAK_SINGLE_CREDIT = """\
Kotak Mahindra Bank - Account Statement
Opening Balance : 5,000.00

05/02/2026 NEFT-SALARY NEFT2026  50,000.00 55,000.00

"""

KOTAK_MULTI_TXN = """\
Kotak Mahindra Bank Account Statement
Opening Balance : 30,000.00

01/01/2026 UPI-SWIGGY 9876543210 450.00  29,550.00
10/01/2026 NEFT-SALARY NEFT001  50,000.00 79,550.00
15/01/2026 ATM-WITHDRAWAL ATM001 5,000.00  74,550.00
20/01/2026 IMPS-TRANSFER IMPS001 2,000.00  72,550.00
25/01/2026 CHQ-PAYMENT 001001 10,000.00  62,550.00
30/01/2026 ECS-EMI ECS001 5,500.00  57,050.00

Closing Balance : 57,050.00
"""

KOTAK_DASH_DATE = """\
Kotak Bank Statement

01-01-2026 UPI-PAYTM PAYTM123 299.00  19,701.00

"""

KOTAK_EMPTY = "Kotak Mahindra Bank Statement\n\nNo transactions."


# ── Row extraction ────────────────────────────────────────────────────────────

class TestRowExtraction:
    def test_single_debit(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, KOTAK_SINGLE_DEBIT)
        assert len(result.rows) == 1
        assert result.rows[0].raw_debit is not None
        assert result.rows[0].raw_credit is None

    def test_single_credit(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, KOTAK_SINGLE_CREDIT)
        assert len(result.rows) == 1
        assert result.rows[0].raw_credit is not None or result.rows[0].raw_debit is not None

    def test_multiple_rows(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, KOTAK_MULTI_TXN)
        assert len(result.rows) == 6

    def test_empty_returns_zero_rows(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, KOTAK_EMPTY)
        assert len(result.rows) == 0

    def test_source_type_kotak(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, KOTAK_SINGLE_DEBIT)
        assert all(r.source_type == SourceType.KOTAK_BANK for r in result.rows)

    def test_batch_id_propagated(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, KOTAK_SINGLE_DEBIT)
        assert all(r.batch_id == batch_id for r in result.rows)

    def test_row_numbers_sequential(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, KOTAK_MULTI_TXN)
        for i, row in enumerate(result.rows, start=1):
            assert row.row_number == i

    def test_dash_date_format_accepted(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, KOTAK_DASH_DATE)
        assert len(result.rows) == 1


# ── Transaction type inference ────────────────────────────────────────────────

class TestTxnTypes:
    def test_upi_detected(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, KOTAK_SINGLE_DEBIT)
        assert result.rows[0].txn_type_hint == TxnTypeHint.UPI

    def test_neft_detected(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, KOTAK_SINGLE_CREDIT)
        assert result.rows[0].txn_type_hint == TxnTypeHint.NEFT

    def test_atm_detected(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, KOTAK_MULTI_TXN)
        assert any(r.txn_type_hint == TxnTypeHint.ATM_WITHDRAWAL for r in result.rows)

    def test_cheque_or_ecs_detected(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, KOTAK_MULTI_TXN)
        # Both CHQ and ECS should map to CHEQUE in TxnTypeHint
        special = [r for r in result.rows if r.txn_type_hint == TxnTypeHint.CHEQUE]
        assert len(special) >= 1


# ── Metadata ──────────────────────────────────────────────────────────────────

class TestMetadata:
    def test_confidence_positive(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, KOTAK_MULTI_TXN)
        assert result.confidence > 0.0

    def test_confidence_zero_for_empty(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, KOTAK_EMPTY)
        assert result.confidence <= 0.15
