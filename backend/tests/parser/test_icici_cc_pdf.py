"""Tests for IciciCcPdfParser — ICICI Bank Credit Card PDF parser.

All tests use ``parse_text_content()`` to avoid PDF I/O, keeping them fast
and deterministic.

Two extraction formats are tested:

**Inline (pdfplumber)** – pdfplumber merges table columns onto a single line:
    DD/MM/YYYY  <SerNo 9+digits>  <description [reward pts]>  amount[(Cr)]

**Multi-line (PyMuPDF / fixtures)** – each field on its own line:
    DD/MM/YYYY
    SerNo
    DESCRIPTION
    reward_pts           (optional standalone integer)
    amount[(Cr)]
"""

from __future__ import annotations

import pytest

from core.models.enums import ExtractionMethod, SourceType, TxnTypeHint
from modules.parser.parsers.icici_cc_pdf import IciciCcPdfParser

# ── Helpers ───────────────────────────────────────────────────────────────────

_HEADER_INLINE = """\
ICICI Bank Credit Card
CREDIT CARD STATEMENT
Statement period : December 26, 2024 to February 25, 2026
Card Number : 4315XXXXXXXX8000
Date SerNo. Transaction Details Reward Points Intl.# amount Amount (in`)
"""

_HEADER_MULTILINE = """\
ICICI Bank Credit Card
CREDIT CARD STATEMENT
Statement period : December 26, 2024 to February 25, 2026
Card Number : 4315XXXXXXXX8000
"""

# ── Fixture text ──────────────────────────────────────────────────────────────

MINIMAL_INLINE = (
    _HEADER_INLINE
    + "21/02/2026 12920627149 ZEPTO MARKETPLACE PRIV BANGALORE IN 20 2,084.00\n"
)

SINGLE_CREDIT_INLINE = (
    _HEADER_INLINE
    + "05/01/2026 98765432101 PAYMENT RECEIVED NEFT 100 1,00,000.00 (Cr)\n"
)

MULTI_TXN_INLINE = (
    _HEADER_INLINE
    + "21/02/2026 12920627149 ZEPTO MARKETPLACE PRIV BANGALORE IN 20 2,084.00\n"
    + "22/02/2026 23456789012 SWIGGY INSTAMART BANGALORE IN 10 499.00\n"
    + "23/02/2026 34567890123 AMAZON IN MARKETPLACE 15 1,299.00\n"
    + "28/02/2026 45678901234 PAYMENT RECEIVED NEFT 0 50,000.00 (Cr)\n"
)

MULTI_TXN_MULTILINE = (
    _HEADER_MULTILINE
    + "21/02/2026\n"
    + "12920627149\n"
    + "ZEPTO MARKETPLACE PRIV BANGALORE IN\n"
    + "20\n"
    + "2,084.00\n"
    + "22/02/2026\n"
    + "23456789012\n"
    + "SWIGGY INSTAMART BANGALORE IN\n"
    + "10\n"
    + "499.00\n"
    + "28/02/2026\n"
    + "45678901234\n"
    + "PAYMENT RECEIVED NEFT\n"
    + "0\n"
    + "50,000.00 (Cr)\n"
)

UPI_TXN_INLINE = (
    _HEADER_INLINE
    + "10/01/2026 11223344556 UPI ZOMATO BANGALORE IN 5 350.00\n"
)

NEFT_PAYMENT_INLINE = (
    _HEADER_INLINE
    + "15/01/2026 99887766554 PAYMENT RECEIVED NEFT 0 25,000.00 (Cr)\n"
)

REFUND_INLINE = (
    _HEADER_INLINE
    + "20/01/2026 66554433221 REFUND AMAZON IN MARKETPLACE 0 599.00 (Cr)\n"
)

REVERSAL_INLINE = (
    _HEADER_INLINE
    + "25/01/2026 77665544330 REVERSAL OF CHARGE AXIS BANK 0 100.00 (Cr)\n"
)

CASHBACK_INLINE = (
    _HEADER_INLINE
    + "26/01/2026 88776655441 CASHBACK CREDIT AMAZON PAY 0 150.00 (Cr)\n"
)


@pytest.fixture()
def parser() -> IciciCcPdfParser:
    return IciciCcPdfParser()


@pytest.fixture()
def batch_id() -> str:
    return "test-batch-icici-001"


# ── 1. Parser metadata ────────────────────────────────────────────────────────

class TestParserMeta:
    def test_source_type(self, parser):
        assert parser.source_type == SourceType.ICICI_BANK_CC

    def test_version_string(self, parser):
        assert parser.version == "1.0"

    def test_supported_methods_contains_text_layer(self, parser):
        assert ExtractionMethod.TEXT_LAYER in parser.supported_methods()

    def test_supported_methods_contains_ocr(self, parser):
        assert ExtractionMethod.OCR in parser.supported_methods()

    def test_supported_methods_excludes_table(self, parser):
        assert ExtractionMethod.TABLE_EXTRACTION not in parser.supported_methods()


# ── 2. Row count ──────────────────────────────────────────────────────────────

class TestRowCount:
    def test_minimal_inline_has_one_row(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MINIMAL_INLINE)
        assert len(result.rows) == 1

    def test_multi_txn_inline_has_four_rows(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MULTI_TXN_INLINE)
        assert len(result.rows) == 4

    def test_multi_txn_multiline_has_three_rows(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MULTI_TXN_MULTILINE)
        assert len(result.rows) == 3

    def test_empty_text_produces_no_rows(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, "")
        assert len(result.rows) == 0

    def test_header_only_produces_no_rows(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, _HEADER_INLINE)
        assert len(result.rows) == 0


# ── 3. Debit / credit direction ───────────────────────────────────────────────

class TestAmountDirection:
    def test_purchase_is_debit(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MINIMAL_INLINE)
        row = result.rows[0]
        assert row.raw_debit == "2,084.00"
        assert row.raw_credit is None

    def test_payment_cr_suffix_is_credit(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, SINGLE_CREDIT_INLINE)
        row = result.rows[0]
        assert row.raw_credit is not None
        assert row.raw_debit is None

    def test_refund_keyword_is_credit(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, REFUND_INLINE)
        row = result.rows[0]
        assert row.raw_credit is not None
        assert row.raw_debit is None

    def test_reversal_keyword_is_credit(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, REVERSAL_INLINE)
        row = result.rows[0]
        assert row.raw_credit is not None

    def test_cashback_keyword_is_credit(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, CASHBACK_INLINE)
        row = result.rows[0]
        assert row.raw_credit is not None

    def test_multi_mixed_direction(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MULTI_TXN_INLINE)
        debits  = [r for r in result.rows if r.raw_debit  is not None]
        credits = [r for r in result.rows if r.raw_credit is not None]
        assert len(debits)  == 3   # ZEPTO, SWIGGY, AMAZON
        assert len(credits) == 1   # PAYMENT RECEIVED

    def test_raw_balance_is_none(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MINIMAL_INLINE)
        assert result.rows[0].raw_balance is None


# ── 4. Source type tagging ────────────────────────────────────────────────────

class TestSourceTypeTagging:
    def test_all_rows_tagged_icici_cc(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MULTI_TXN_INLINE)
        for row in result.rows:
            assert row.source_type == SourceType.ICICI_BANK_CC

    def test_batch_id_propagated(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MINIMAL_INLINE)
        assert result.rows[0].batch_id == batch_id


# ── 5. Serial number as reference ────────────────────────────────────────────

class TestSerialReference:
    def test_serial_stored_as_reference(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MINIMAL_INLINE)
        assert result.rows[0].raw_reference == "12920627149"

    def test_each_row_has_different_serial(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MULTI_TXN_INLINE)
        refs = [r.raw_reference for r in result.rows]
        assert len(set(refs)) == 4   # all unique

    def test_multiline_serial_stored(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MULTI_TXN_MULTILINE)
        assert result.rows[0].raw_reference == "12920627149"


# ── 6. Date parsing ───────────────────────────────────────────────────────────

class TestDateParsing:
    def test_date_preserved_as_dmy(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MINIMAL_INLINE)
        assert result.rows[0].raw_date == "21/02/2026"

    def test_multi_txn_dates_ordered(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MULTI_TXN_INLINE)
        dates = [r.raw_date for r in result.rows]
        assert dates[0] == "21/02/2026"
        assert dates[-1] == "28/02/2026"


# ── 7. Statement metadata ─────────────────────────────────────────────────────

class TestMetadata:
    def test_card_number_captured(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MINIMAL_INLINE)
        meta = result.metadata
        assert meta.account_hint == "4315XXXXXXXX8000"

    def test_statement_period_english_months(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MINIMAL_INLINE)
        meta = result.metadata
        assert meta.statement_from == "2024-12-26"
        assert meta.statement_to   == "2026-02-25"

    def test_opening_balance_is_none(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MINIMAL_INLINE)
        assert result.metadata.opening_balance is None

    def test_closing_balance_is_none(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MINIMAL_INLINE)
        assert result.metadata.closing_balance is None

    def test_balance_cross_check_is_none(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MINIMAL_INLINE)
        assert result.metadata.balance_cross_check_passed is None

    def test_total_rows_found_matches(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MULTI_TXN_INLINE)
        assert result.metadata.total_rows_found == 4


# ── 8. TxnTypeHint inference ──────────────────────────────────────────────────

class TestTxnTypeHint:
    def test_upi_txn_hint(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, UPI_TXN_INLINE)
        assert result.rows[0].txn_type_hint == TxnTypeHint.UPI

    def test_neft_payment_hint(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, NEFT_PAYMENT_INLINE)
        assert result.rows[0].txn_type_hint == TxnTypeHint.NEFT

    def test_regular_purchase_unknown_hint(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MINIMAL_INLINE)
        assert result.rows[0].txn_type_hint == TxnTypeHint.UNKNOWN


# ── 9. Confidence ─────────────────────────────────────────────────────────────

class TestConfidence:
    def test_confidence_is_float(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MINIMAL_INLINE)
        assert isinstance(result.confidence, float)

    def test_confidence_above_threshold(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MULTI_TXN_INLINE)
        assert result.confidence >= 0.8

    def test_empty_text_lower_confidence(self, parser, batch_id):
        # Empty text → no rows (row_count_positive=False) → confidence < best score
        empty_result = parser.parse_text_content(batch_id, "")
        good_result  = parser.parse_text_content(batch_id, MINIMAL_INLINE)
        assert empty_result.confidence < good_result.confidence

    def test_confidence_reported_in_metadata(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MINIMAL_INLINE)
        assert result.metadata.overall_confidence == result.confidence


# ── 10. Narration / description ───────────────────────────────────────────────

class TestNarration:
    def test_description_extracted(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MINIMAL_INLINE)
        assert "ZEPTO" in result.rows[0].raw_narration

    def test_narration_does_not_include_serial(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MINIMAL_INLINE)
        assert "12920627149" not in result.rows[0].raw_narration

    def test_narration_does_not_include_date(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MINIMAL_INLINE)
        assert "21/02/2026" not in result.rows[0].raw_narration


# ── 11. Extraction method propagation ────────────────────────────────────────

class TestExtractionMethod:
    def test_default_method_is_text_layer(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MINIMAL_INLINE)
        assert result.method == ExtractionMethod.TEXT_LAYER

    def test_explicit_ocr_method_propagated(self, parser, batch_id):
        result = parser.parse_text_content(
            batch_id, MINIMAL_INLINE, ExtractionMethod.OCR
        )
        assert result.method == ExtractionMethod.OCR
        assert result.rows[0].extraction_method == ExtractionMethod.OCR


# ── 12. Detector integration ──────────────────────────────────────────────────

class TestDetection:
    def test_content_signature_icici_bank_credit_card(self):
        from modules.parser.detector import SourceDetector
        detector = SourceDetector()
        text = (
            b"ICICI Bank Credit Card\n"
            b"CREDIT CARD STATEMENT\n"
            b"SerNo. Transaction Details\n"
        )
        result = detector.detect("statement.pdf", text)
        assert result.source_type == SourceType.ICICI_BANK_CC

    def test_content_signature_with_statement_period(self):
        from modules.parser.detector import SourceDetector
        detector = SourceDetector()
        text = (
            b"ICICI Bank Credit Card\n"
            b"SerNo.\n"
            b"Statement period : December 26, 2024 to February 25, 2026\n"
        )
        result = detector.detect("statement.pdf", text)
        assert result.source_type == SourceType.ICICI_BANK_CC

    def test_filename_pattern_icic_cc(self):
        from modules.parser.detector import SourceDetector
        detector = SourceDetector()
        result = detector.detect("icic-cc.pdf", b"%PDF-1.4 stub")
        assert result.source_type == SourceType.ICICI_BANK_CC

    def test_filename_pattern_icici_credit(self):
        from modules.parser.detector import SourceDetector
        detector = SourceDetector()
        result = detector.detect("icici_credit_card_jan2026.pdf", b"%PDF-1.4 stub")
        assert result.source_type == SourceType.ICICI_BANK_CC

    def test_hint_overrides_detection(self):
        from modules.parser.detector import SourceDetector
        detector = SourceDetector()
        result = detector.detect(
            "random.pdf",
            b"%PDF-1.4 stub",
            source_type_hint=SourceType.ICICI_BANK_CC.value,
        )
        assert result.source_type == SourceType.ICICI_BANK_CC
        assert result.confidence == 1.0
