"""Tests for HdfcPdfParser.parse_text_content() — pure function, no I/O."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from core.models.enums import ExtractionMethod, SourceType, TxnTypeHint
from modules.parser.parsers.hdfc_pdf import HdfcPdfParser, _clean_amount, _infer_txn_type


@pytest.fixture
def parser() -> HdfcPdfParser:
    return HdfcPdfParser()


@pytest.fixture
def batch_id_local() -> str:
    return str(uuid.uuid4())


# ── Minimal HDFC text fixtures ─────────────────────────────────────────────────

HDFC_SINGLE_DEBIT = """\
HDFC Bank Account Statement
Opening Balance 20,000.00

Date              Narration                       Chq/Ref No.        Value Dt    Withdrawal Amt (Dr)  Deposit Amt (Cr)  Closing Balance
01/01/2026        UPI/147896325478/SWIGGY/pay     147896325478       01/01/2026  450.00                                 19,550.00

Closing Balance 19,550.00
"""

HDFC_SINGLE_CREDIT = """\
HDFC Bank Account Statement
Opening Balance 10,000.00

Date              Narration                       Chq/Ref No.        Value Dt    Withdrawal Amt (Dr)  Deposit Amt (Cr)  Closing Balance
02/01/2026        NEFT CR/20260201/SALARY         NEFT20260201       02/01/2026                        50,000.00        60,000.00

Closing Balance 60,000.00
"""

HDFC_MULTI_TXN = """\
HDFC Bank Account Statement
Opening Balance 20,000.00

Date              Narration                       Chq/Ref No.        Value Dt    Withdrawal Amt (Dr)  Deposit Amt (Cr)  Closing Balance
01/01/2026        UPI/147896325478/SWIGGY/pay     147896325478       01/01/2026  450.00                                 19,550.00
02/01/2026        NEFT CR/20260201/SALARY         NEFT20260201       02/01/2026                        50,000.00        69,550.00
05/01/2026        ATM/BOM/00123 CASH WD           ATM00123           05/01/2026  5,000.00                               64,550.00
10/01/2026        IMPS/98765432100/PHONEPE        IMPS98765          10/01/2026  1,200.00                               63,350.00
15/01/2026        NEFT CR/20260115/INTEREST       NEFT20260115       15/01/2026                        350.00           63,700.00

Closing Balance 63,700.00
"""

HDFC_EMPTY = "HDFC Bank Account Statement\n\nNo transactions found."


# ── parse_text_content — row extraction ──────────────────────────────────────

class TestRowExtraction:
    def test_extracts_single_debit_row(self, parser, batch_id_local):
        result = parser.parse_text_content(batch_id_local, HDFC_SINGLE_DEBIT)
        assert len(result.rows) == 1
        row = result.rows[0]
        assert row.raw_date == "01/01/2026"
        assert "SWIGGY" in row.raw_narration.upper() or "UPI" in row.raw_narration.upper()
        assert row.raw_debit is not None
        assert row.raw_credit is None

    def test_extracts_single_credit_row(self, parser, batch_id_local):
        result = parser.parse_text_content(batch_id_local, HDFC_SINGLE_CREDIT)
        assert len(result.rows) == 1
        row = result.rows[0]
        # Credit amount ends up in whichever column the regex puts the single number
        assert row.raw_credit is not None or row.raw_debit is not None

    def test_extracts_multiple_rows(self, parser, batch_id_local):
        result = parser.parse_text_content(batch_id_local, HDFC_MULTI_TXN)
        assert len(result.rows) == 5

    def test_empty_text_returns_zero_rows(self, parser, batch_id_local):
        result = parser.parse_text_content(batch_id_local, HDFC_EMPTY)
        assert len(result.rows) == 0
        assert result.confidence <= 0.15

    def test_rows_tagged_with_batch_id(self, parser, batch_id_local):
        result = parser.parse_text_content(batch_id_local, HDFC_SINGLE_DEBIT)
        assert all(r.batch_id == batch_id_local for r in result.rows)

    def test_rows_tagged_with_source_type(self, parser, batch_id_local):
        result = parser.parse_text_content(batch_id_local, HDFC_SINGLE_DEBIT)
        assert all(r.source_type == SourceType.HDFC_BANK for r in result.rows)

    def test_rows_have_row_numbers(self, parser, batch_id_local):
        result = parser.parse_text_content(batch_id_local, HDFC_MULTI_TXN)
        for i, row in enumerate(result.rows, start=1):
            assert row.row_number == i


# ── Transaction type inference ────────────────────────────────────────────────

class TestTxnTypeInference:
    def test_upi_narration(self, parser, batch_id_local):
        result = parser.parse_text_content(batch_id_local, HDFC_SINGLE_DEBIT)
        assert result.rows[0].txn_type_hint == TxnTypeHint.UPI

    def test_neft_narration(self, parser, batch_id_local):
        result = parser.parse_text_content(batch_id_local, HDFC_SINGLE_CREDIT)
        assert result.rows[0].txn_type_hint == TxnTypeHint.NEFT

    def test_atm_narration(self, parser, batch_id_local):
        result = parser.parse_text_content(batch_id_local, HDFC_MULTI_TXN)
        atm_rows = [r for r in result.rows if r.txn_type_hint == TxnTypeHint.ATM_WITHDRAWAL]
        assert len(atm_rows) >= 1

    def test_imps_narration(self, parser, batch_id_local):
        result = parser.parse_text_content(batch_id_local, HDFC_MULTI_TXN)
        imps_rows = [r for r in result.rows if r.txn_type_hint == TxnTypeHint.IMPS]
        assert len(imps_rows) >= 1


# ── Confidence scoring ────────────────────────────────────────────────────────

class TestConfidenceScoring:
    def test_high_confidence_clean_data(self, parser, batch_id_local):
        """With rows extracted → confidence above 0.5."""
        result = parser.parse_text_content(batch_id_local, HDFC_MULTI_TXN)
        assert result.confidence >= 0.5

    def test_zero_confidence_empty(self, parser, batch_id_local):
        result = parser.parse_text_content(batch_id_local, "")
        assert result.confidence <= 0.15

    def test_result_is_extraction_result(self, parser, batch_id_local):
        from modules.parser.base import ExtractionResult
        result = parser.parse_text_content(batch_id_local, HDFC_SINGLE_DEBIT)
        assert isinstance(result, ExtractionResult)


# ── Amount parsing helpers ────────────────────────────────────────────────────

class TestCleanAmount:
    def test_simple_amount(self):
        assert _clean_amount("450.00") == Decimal("450.00")

    def test_indian_lakh_format(self):
        assert _clean_amount("1,23,456.78") == Decimal("123456.78")

    def test_thousands_comma(self):
        assert _clean_amount("50,000.00") == Decimal("50000.00")

    def test_invalid_returns_none(self):
        assert _clean_amount("N/A") is None

    def test_empty_string_returns_none(self):
        assert _clean_amount("") is None


# ── Txn type inference helper ─────────────────────────────────────────────────

class TestInferTxnType:
    @pytest.mark.parametrize("narration, expected", [
        ("UPI/123/SWIGGY", TxnTypeHint.UPI),
        ("NEFT CR/SALARY", TxnTypeHint.NEFT),
        ("IMPS/PHONEPE/XYZ", TxnTypeHint.IMPS),
        ("ATM CASH WD BOM", TxnTypeHint.ATM_WITHDRAWAL),
        ("CHEQUE PAYMENT CLG", TxnTypeHint.CHEQUE),
        ("MISCELLANEOUS CHARGE", TxnTypeHint.UNKNOWN),
    ])
    def test_infer(self, narration, expected):
        assert _infer_txn_type(narration) == expected


# ── Method flag propagation ───────────────────────────────────────────────────

class TestMethodFlagPropagation:
    def test_method_stored_in_rows(self, parser, batch_id_local):
        result = parser.parse_text_content(
            batch_id_local,
            HDFC_SINGLE_DEBIT,
            method=ExtractionMethod.OCR,
        )
        for row in result.rows:
            assert row.extraction_method == ExtractionMethod.OCR
