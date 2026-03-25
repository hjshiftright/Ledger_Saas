"""Tests for UnionBankPdfParser.parse_text_content() and Union Bank CSV detection.

Pure-function tests — no PDF file I/O required.
"""

from __future__ import annotations

import uuid

import pytest

from core.models.enums import ExtractionMethod, SourceType, TxnTypeHint
from modules.parser.parsers.union_pdf import UnionBankPdfParser


@pytest.fixture
def parser() -> UnionBankPdfParser:
    return UnionBankPdfParser()


@pytest.fixture
def batch_id() -> str:
    return str(uuid.uuid4())


# ── Text fixtures ─────────────────────────────────────────────────────────────
# Union Bank format: Date  Particulars  Chq/Ref  [Debit]  [Credit]  Balance

UNION_SINGLE_DEBIT = """\
Union Bank of India
Account Statement

01/01/2026    UPI/123456789/SWIGGY FOOD       123456789  450.00           49,550.00

"""

UNION_SINGLE_CREDIT = """\
Union Bank of India
Account Statement

02/01/2026    NEFT CR/SALARY CREDIT           NEFT001               50,000.00  99,550.00

"""

UNION_MULTI_TXN = """\
Union Bank of India
Account Statement

Opening Balance 1,00,000.00

01/01/2026    UPI/123456789/SWIGGY FOOD       123456789  450.00            99,550.00
02/01/2026    NEFT CR/SALARY CREDIT           NEFT001               50,000.00  1,49,550.00
05/01/2026    ATM CASH WITHDRAWAL/MUM/001     ATM00123   5,000.00          1,44,550.00
08/01/2026    IMPS/9876/PHONEPE RECHARGE      IMPS9876   299.00            1,44,251.00

Closing Balance 1,44,251.00
"""

UNION_DASHES_DATE = """\
Union Bank of India

15-03-2026    NEFT CR/EMPLOYER SALARY         NEFT999               40,000.00  2,00,000.00

"""

UNION_EMPTY = "Union Bank of India\n\nNo transactions in the selected period."


# ── Parser metadata ────────────────────────────────────────────────────────────

class TestParserMetadata:
    def test_source_type(self, parser):
        assert parser.source_type == SourceType.UNION_BANK

    def test_supported_methods(self, parser):
        methods = parser.supported_methods()
        assert ExtractionMethod.TEXT_LAYER in methods
        assert ExtractionMethod.TABLE_EXTRACTION in methods
        assert ExtractionMethod.OCR in methods


# ── Row extraction ─────────────────────────────────────────────────────────────

class TestRowExtraction:
    def test_single_debit_row(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, UNION_SINGLE_DEBIT)
        assert len(result.rows) == 1
        row = result.rows[0]
        assert row.raw_debit is not None
        assert row.raw_credit is None
        assert row.raw_balance == "49,550.00"

    def test_single_credit_row(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, UNION_SINGLE_CREDIT)
        assert len(result.rows) == 1
        row = result.rows[0]
        assert row.raw_credit is not None
        assert row.raw_debit is None

    def test_multiple_rows(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, UNION_MULTI_TXN)
        assert len(result.rows) == 4

    def test_empty_text_returns_no_rows(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, UNION_EMPTY)
        assert len(result.rows) == 0

    def test_dash_date_normalised_to_slash(self, parser, batch_id):
        """DD-MM-YYYY dates are normalised to DD/MM/YYYY."""
        result = parser.parse_text_content(batch_id, UNION_DASHES_DATE)
        assert len(result.rows) == 1
        assert result.rows[0].raw_date == "15/03/2026"


# ── Source type tagging ────────────────────────────────────────────────────────

class TestSourceTypeTagging:
    def test_rows_tagged_union_bank(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, UNION_MULTI_TXN)
        for row in result.rows:
            assert row.source_type == SourceType.UNION_BANK

    def test_batch_id_propagated(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, UNION_MULTI_TXN)
        for row in result.rows:
            assert row.batch_id == batch_id


# ── Transaction type inference ─────────────────────────────────────────────────

class TestTxnTypeInference:
    def test_upi_detected(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, UNION_SINGLE_DEBIT)
        assert result.rows[0].txn_type_hint == TxnTypeHint.UPI

    def test_neft_detected(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, UNION_SINGLE_CREDIT)
        assert result.rows[0].txn_type_hint == TxnTypeHint.NEFT

    def test_atm_detected(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, UNION_MULTI_TXN)
        atm_row = next(r for r in result.rows if "ATM" in (r.raw_narration or ""))
        assert atm_row.txn_type_hint == TxnTypeHint.ATM_WITHDRAWAL

    def test_imps_detected(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, UNION_MULTI_TXN)
        imps_row = next(r for r in result.rows if "IMPS" in (r.raw_narration or ""))
        assert imps_row.txn_type_hint == TxnTypeHint.IMPS


# ── Confidence ─────────────────────────────────────────────────────────────────

class TestConfidence:
    def test_valid_rows_have_high_row_confidence(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, UNION_MULTI_TXN)
        for row in result.rows:
            assert row.row_confidence >= 0.85

    def test_overall_confidence_positive(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, UNION_MULTI_TXN)
        assert result.confidence > 0.0

    def test_empty_text_zero_confidence(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, UNION_EMPTY)
        assert result.confidence < 0.2   # near-zero — no rows extracted


# ── CSV detection ──────────────────────────────────────────────────────────────

class TestUnionCsvDetection:
    def test_detect_column_mapping_v1(self):
        from modules.parser.parsers.generic_csv import detect_column_mapping
        headers = ["Date", "Particulars", "Chq/Ref No.", "Debit", "Credit", "Balance"]
        mapping = detect_column_mapping(headers)
        assert mapping is not None
        assert mapping.format_fingerprint == "union_csv_v1"
        assert mapping.narration_column == "Particulars"

    def test_detect_column_mapping_v2(self):
        from modules.parser.parsers.generic_csv import detect_column_mapping
        headers = ["Tran Date", "Particulars", "Reference No", "Debit", "Credit", "Balance"]
        mapping = detect_column_mapping(headers)
        assert mapping is not None
        assert mapping.format_fingerprint == "union_csv_v2"

    def test_fingerprint_to_source_type_v1(self):
        from modules.parser.parsers.generic_csv import _FINGERPRINT_TO_SOURCE_TYPE
        assert _FINGERPRINT_TO_SOURCE_TYPE["union_csv_v1"] == SourceType.UNION_BANK_CSV

    def test_fingerprint_to_source_type_v2(self):
        from modules.parser.parsers.generic_csv import _FINGERPRINT_TO_SOURCE_TYPE
        assert _FINGERPRINT_TO_SOURCE_TYPE["union_csv_v2"] == SourceType.UNION_BANK_CSV


# ── Detector integration ───────────────────────────────────────────────────────

class TestDetector:
    def test_filename_union_bank_pdf(self):
        from modules.parser.detector import SourceDetector
        det = SourceDetector()
        result = det.detect(filename="union_bank_stmt_jan2026.pdf", file_bytes=b"%PDF-1.4")
        assert result.source_type == SourceType.UNION_BANK
        assert result.confidence >= 0.70

    def test_csv_header_scan_detects_union(self):
        from modules.parser.detector import SourceDetector
        csv_bytes = b"Date,Particulars,Chq/Ref No.,Debit,Credit,Balance\n01/01/2026,UPI/123,123,450.00,,49550.00"
        det = SourceDetector()
        result = det.detect(filename="statement.csv", file_bytes=csv_bytes)
        assert result.source_type == SourceType.UNION_BANK_CSV
        assert result.confidence >= 0.90

    def test_registry_has_union_bank(self):
        from modules.parser.registry import ParserRegistry
        registry = ParserRegistry.default()
        assert registry.has(SourceType.UNION_BANK)
        assert registry.has(SourceType.UNION_BANK_CSV)
