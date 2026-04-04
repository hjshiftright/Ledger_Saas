"""Tests for SourceDetector — filename and content-based source detection."""

from __future__ import annotations

import pytest

from core.models.enums import FileFormat, SourceType
from modules.parser.detector import DetectionResult, SourceDetector

DETECTION_THRESHOLD = 0.70


@pytest.fixture
def detector() -> SourceDetector:
    return SourceDetector()


# ── Filename-based detection ──────────────────────────────────────────────────

class TestFilenameDetection:
    def test_hdfc_bank_pdf(self, detector: SourceDetector):
        result = detector.detect("HDFC_Bank_Statement_Jan2026.pdf", b"")
        assert result.source_type == SourceType.HDFC_BANK
        assert result.confidence >= DETECTION_THRESHOLD
        assert result.method == "filename"
        assert result.file_format == FileFormat.PDF

    def test_sbi_bank_pdf(self, detector: SourceDetector):
        result = detector.detect("SBI_Account_Statement.pdf", b"")
        assert result.source_type == SourceType.SBI_BANK
        assert result.confidence >= DETECTION_THRESHOLD

    def test_icici_pdf(self, detector: SourceDetector):
        result = detector.detect("icicibank_statement_202601.pdf", b"")
        assert result.source_type == SourceType.ICICI_BANK
        assert result.confidence >= DETECTION_THRESHOLD

    def test_axis_pdf(self, detector: SourceDetector):
        result = detector.detect("axis_stmt_jan26.pdf", b"")
        assert result.source_type == SourceType.AXIS_BANK
        assert result.confidence >= DETECTION_THRESHOLD

    def test_cams_cas(self, detector: SourceDetector):
        result = detector.detect("CAS_CAMS_Jan2026.pdf", b"")
        assert result.source_type == SourceType.CAS_CAMS
        assert result.confidence >= 0.85

    def test_kfintech_cas(self, detector: SourceDetector):
        result = detector.detect("kfintech_cas_statement.pdf", b"")
        assert result.source_type == SourceType.CAS_KFINTECH
        assert result.confidence >= DETECTION_THRESHOLD

    def test_zerodha_tradebook(self, detector: SourceDetector):
        result = detector.detect("zerodha_tradebook_2025.csv", b"")
        assert result.source_type == SourceType.ZERODHA_TRADEBOOK
        assert result.confidence >= 0.85

    def test_zerodha_holdings(self, detector: SourceDetector):
        result = detector.detect("zerodha_holding_summary.csv", b"")
        assert result.source_type == SourceType.ZERODHA_HOLDINGS
        assert result.confidence >= 0.85

    def test_capital_gains_csv(self, detector: SourceDetector):
        result = detector.detect("zerodha_capital_gains_2025.csv", b"")
        assert result.source_type == SourceType.ZERODHA_CAPITAL_GAINS
        assert result.confidence >= DETECTION_THRESHOLD

    def test_unknown_filename_returns_unknown(self, detector: SourceDetector):
        result = detector.detect("my_random_document.pdf", b"")
        assert result.source_type == SourceType.UNKNOWN
        assert result.confidence == 0.0

    def test_file_format_csv(self, detector: SourceDetector):
        result = detector.detect("zerodha_tradebook.csv", b"")
        assert result.file_format == FileFormat.CSV

    def test_file_format_xls(self, detector: SourceDetector):
        result = detector.detect("statement.xls", b"")
        assert result.file_format == FileFormat.XLS

    def test_file_format_xlsx(self, detector: SourceDetector):
        result = detector.detect("statement.xlsx", b"")
        assert result.file_format == FileFormat.XLSX


# ── Hint override ─────────────────────────────────────────────────────────────

class TestHintOverride:
    def test_hint_overrides_filename(self, detector: SourceDetector):
        """A caller-supplied hint always wins with confidence=1.0."""
        result = detector.detect(
            filename="random_file.pdf",
            file_bytes=b"",
            source_type_hint="SBI_BANK",
        )
        assert result.source_type == SourceType.SBI_BANK
        assert result.confidence == 1.0
        assert result.method == "hint"

    def test_hint_is_case_insensitive(self, detector: SourceDetector):
        result = detector.detect("x.pdf", b"", source_type_hint="hdfc_bank")
        assert result.source_type == SourceType.HDFC_BANK

    def test_invalid_hint_falls_through_to_unknown(self, detector: SourceDetector):
        """An unrecognised hint value results in UNKNOWN rather than crashing."""
        result = detector.detect("x.pdf", b"", source_type_hint="NOT_A_REAL_TYPE")
        assert result.source_type == SourceType.UNKNOWN


# ── Content-based detection ───────────────────────────────────────────────────

class TestPdfContentDetection:
    def test_hdfc_content_signature(self, detector: SourceDetector):
        """Embedded HDFC keywords should trigger content-based detection."""
        content = b"HDFC Bank Account Statement\nWithdrawal Amt (Dr) Deposit Amt (Cr) Closing Balance"
        result = detector.detect("unknown_file.pdf", content)
        assert result.source_type == SourceType.HDFC_BANK
        assert result.confidence >= DETECTION_THRESHOLD

    def test_sbi_not_boi_state_bank_contains_bank_of_india_substring(self, detector: SourceDetector):
        """SBI PDFs say 'State Bank of India' — must not classify as Bank of India (BOI)."""
        content = (
            b"%PDF-1.4\nSTATEMENT OF ACCOUNT\nState Bank of India\n"
            b"Debit Credit Balance\nTerms and conditions apply."
        )
        result = detector.detect("AccountStatement-FEB.pdf", content)
        assert result.source_type == SourceType.SBI_BANK
        assert result.confidence >= 0.90
        assert result.method == "content"

    def test_cams_content_signature(self, detector: SourceDetector):
        content = b"CAMS Consolidated Account Statement\nFolio No: 12345678"
        result = detector.detect("report.pdf", content)
        assert result.source_type == SourceType.CAS_CAMS
        assert result.confidence >= 0.90


class TestCsvHeaderDetection:
    def test_hdfc_csv_headers(self, detector: SourceDetector):
        headers_line = b"Date,Narration,Chq./Ref.No.,Value Dt,Withdrawal Amt (Dr),Deposit Amt (Cr),Closing Balance\n"
        result = detector.detect("statement.csv", headers_line)
        assert result.source_type == SourceType.HDFC_BANK_CSV
        assert result.confidence >= 0.90

    def test_sbi_csv_headers(self, detector: SourceDetector):
        headers_line = b"Txn Date,Description,Ref No./Cheque No.,Debit,Credit,Balance\n"
        result = detector.detect("sbi.csv", headers_line)
        assert result.source_type == SourceType.SBI_BANK_CSV
        assert result.confidence >= DETECTION_THRESHOLD
