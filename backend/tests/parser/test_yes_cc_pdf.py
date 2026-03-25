"""Tests for YesCcPdfParser — Yes Bank Credit Card PDF parser.

All tests use `parse_text_content()` to avoid PDF I/O, making them fast and
deterministic.  The fixture strings mirror the actual text extracted from
the Yes Bank CC e-statement by PyMuPDF.

Row format (one transaction block):
    DD/MM/YYYY  <description> - Ref No: <ref>
    [merchant category]          ← optional
    amount.cc Dr|Cr
"""

from __future__ import annotations

import pytest

from core.models.enums import ExtractionMethod, SourceType, TxnTypeHint
from modules.parser.parsers.yes_cc_pdf import YesCcPdfParser


# ── Fixtures ──────────────────────────────────────────────────────────────────

MINIMAL_STATEMENT = """\
Statement for YES BANK Card Number 3561XXXXXXXX4581
Credit Card Statement
Statement Period:
15/02/2026 To 14/03/2026
Date
Transaction Details
Merchant Category
Amount (Rs.)
15/02/2026 PAYMENT RECEIVED BBPS - Ref No: 09999999980215001310189
98,939.61 Cr
17/02/2026 UPI_BMTC BUS KA57F3290 IND - Ref No: RT260480398000750000899
Transportation Services
24.00 Dr
17/02/2026 UPI_INFIBEAM AVENUES L D IND - Ref No: RT260490388001000000634
Retail Outlet Services
432.00 Dr
17/02/2026 UPI_INFIBEAM AVENUES L D IND - Ref No: RT260490388001000000636
Retail Outlet Services
432.00 Cr
"""

# A single transaction with no merchant category line (first page payment row)
PAYMENT_ROW = """\
Statement for YES BANK Card Number 3561XXXXXXXX4581
Credit Card Statement
Statement Period:
01/03/2026 To 31/03/2026
Date
Transaction Details
Merchant Category
Amount (Rs.)
01/03/2026 PAYMENT RECEIVED BBPS - Ref No: 09999999980301001234567
50,000.00 Cr
"""

# Merchant category merged onto the description line (wrapped PDF text)
MERGED_MERCHANT_ROW = """\
Statement for YES BANK Card Number 3561XXXXXXXX4581
Credit Card Statement
Statement Period:
01/03/2026 To 31/03/2026
Date
Transaction Details
Merchant Category
Amount (Rs.)
22/02/2026 UPI_SVASTYA ORGANIC FA MS IND - Ref No: RT260530372000600000652 Retail Outlet Services
2,499.00 Dr
"""


@pytest.fixture()
def parser() -> YesCcPdfParser:
    return YesCcPdfParser()


@pytest.fixture()
def batch_id() -> str:
    return "test-batch-yes-cc-001"


# ── Source type & version ─────────────────────────────────────────────────────

class TestParserMeta:
    def test_source_type(self, parser: YesCcPdfParser):
        assert parser.source_type == SourceType.YES_BANK_CC

    def test_version(self, parser: YesCcPdfParser):
        assert parser.version == "1.0"

    def test_supported_formats(self, parser: YesCcPdfParser):
        assert "PDF" in parser.supported_formats

    def test_supported_methods(self, parser: YesCcPdfParser):
        methods = parser.supported_methods()
        assert ExtractionMethod.TEXT_LAYER in methods
        assert ExtractionMethod.OCR in methods
        # CC parser does not use table extraction
        assert ExtractionMethod.TABLE_EXTRACTION not in methods


# ── Row count ─────────────────────────────────────────────────────────────────

class TestRowCount:
    def test_minimal_statement_rows(self, parser: YesCcPdfParser, batch_id: str):
        result = parser.parse_text_content(batch_id, MINIMAL_STATEMENT)
        assert len(result.rows) == 4

    def test_payment_only_row(self, parser: YesCcPdfParser, batch_id: str):
        result = parser.parse_text_content(batch_id, PAYMENT_ROW)
        assert len(result.rows) == 1

    def test_empty_text_yields_no_rows(self, parser: YesCcPdfParser, batch_id: str):
        result = parser.parse_text_content(batch_id, "\n\n\n")
        assert len(result.rows) == 0


# ── Debit / credit direction ──────────────────────────────────────────────────

class TestAmountDirection:
    def test_payment_is_credit(self, parser: YesCcPdfParser, batch_id: str):
        result = parser.parse_text_content(batch_id, PAYMENT_ROW)
        row = result.rows[0]
        assert row.raw_credit == "50,000.00"
        assert row.raw_debit is None

    def test_purchase_is_debit(self, parser: YesCcPdfParser, batch_id: str):
        result = parser.parse_text_content(batch_id, MINIMAL_STATEMENT)
        # Row index 1 is the BMTC bus UPI purchase (24.00 Dr)
        upi_row = next(r for r in result.rows if "BMTC" in r.raw_narration)
        assert upi_row.raw_debit == "24.00"
        assert upi_row.raw_credit is None

    def test_reversal_is_credit(self, parser: YesCcPdfParser, batch_id: str):
        result = parser.parse_text_content(batch_id, MINIMAL_STATEMENT)
        # INFIBEAM row with Cr suffix
        refund_row = next(
            r for r in result.rows
            if "INFIBEAM" in r.raw_narration and r.raw_credit is not None
        )
        assert refund_row.raw_credit == "432.00"
        assert refund_row.raw_debit is None

    def test_mixed_debits_and_credits(self, parser: YesCcPdfParser, batch_id: str):
        result = parser.parse_text_content(batch_id, MINIMAL_STATEMENT)
        debits  = [r for r in result.rows if r.raw_debit]
        credits = [r for r in result.rows if r.raw_credit]
        assert len(debits)  == 2   # BMTC + INFIBEAM Dr
        assert len(credits) == 2   # PAYMENT + INFIBEAM Cr


# ── Source type tagging ───────────────────────────────────────────────────────

class TestSourceTypeTagging:
    def test_all_rows_tagged_yes_bank_cc(self, parser: YesCcPdfParser, batch_id: str):
        result = parser.parse_text_content(batch_id, MINIMAL_STATEMENT)
        assert all(r.source_type == SourceType.YES_BANK_CC for r in result.rows)

    def test_extraction_method_tagged(self, parser: YesCcPdfParser, batch_id: str):
        result = parser.parse_text_content(
            batch_id, MINIMAL_STATEMENT, ExtractionMethod.TEXT_LAYER
        )
        assert all(r.extraction_method == ExtractionMethod.TEXT_LAYER for r in result.rows)


# ── Reference numbers ─────────────────────────────────────────────────────────

class TestReferenceExtraction:
    def test_ref_no_extracted(self, parser: YesCcPdfParser, batch_id: str):
        result = parser.parse_text_content(batch_id, PAYMENT_ROW)
        assert result.rows[0].raw_reference == "09999999980301001234567"

    def test_upi_ref_extracted(self, parser: YesCcPdfParser, batch_id: str):
        result = parser.parse_text_content(batch_id, MINIMAL_STATEMENT)
        upi_row = next(r for r in result.rows if "BMTC" in r.raw_narration)
        assert upi_row.raw_reference == "RT260480398000750000899"

    def test_ref_stripped_from_narration(self, parser: YesCcPdfParser, batch_id: str):
        result = parser.parse_text_content(batch_id, PAYMENT_ROW)
        narration = result.rows[0].raw_narration
        assert "Ref No" not in narration
        assert "09999999980301001234567" not in narration


# ── Dates ─────────────────────────────────────────────────────────────────────

class TestDateParsing:
    def test_raw_date_format(self, parser: YesCcPdfParser, batch_id: str):
        result = parser.parse_text_content(batch_id, MINIMAL_STATEMENT)
        # Raw dates should be in DD/MM/YYYY format as they appear in the PDF
        for row in result.rows:
            parts = row.raw_date.split("/")
            assert len(parts) == 3
            assert len(parts[2]) == 4  # 4-digit year

    def test_payment_date(self, parser: YesCcPdfParser, batch_id: str):
        result = parser.parse_text_content(batch_id, PAYMENT_ROW)
        assert result.rows[0].raw_date == "01/03/2026"


# ── Statement metadata ────────────────────────────────────────────────────────

class TestMetadata:
    def test_statement_period_from(self, parser: YesCcPdfParser, batch_id: str):
        result = parser.parse_text_content(batch_id, MINIMAL_STATEMENT)
        assert result.metadata.statement_from == "2026-02-15"

    def test_statement_period_to(self, parser: YesCcPdfParser, batch_id: str):
        result = parser.parse_text_content(batch_id, MINIMAL_STATEMENT)
        assert result.metadata.statement_to == "2026-03-14"

    def test_account_hint_is_card_number(self, parser: YesCcPdfParser, batch_id: str):
        result = parser.parse_text_content(batch_id, MINIMAL_STATEMENT)
        assert result.metadata.account_hint == "3561XXXXXXXX4581"

    def test_total_rows_found(self, parser: YesCcPdfParser, batch_id: str):
        result = parser.parse_text_content(batch_id, MINIMAL_STATEMENT)
        assert result.metadata.total_rows_found == 4

    def test_no_balance_for_cc_statement(self, parser: YesCcPdfParser, batch_id: str):
        result = parser.parse_text_content(batch_id, MINIMAL_STATEMENT)
        assert result.metadata.opening_balance is None
        assert result.metadata.closing_balance is None
        assert result.metadata.balance_cross_check_passed is None
        # All rows must also have no balance
        assert all(r.raw_balance is None for r in result.rows)


# ── TxnTypeHint inference ─────────────────────────────────────────────────────

class TestTxnTypeHint:
    def test_upi_txns_classified(self, parser: YesCcPdfParser, batch_id: str):
        result = parser.parse_text_content(batch_id, MINIMAL_STATEMENT)
        upi_rows = [r for r in result.rows if "BMTC" in r.raw_narration or "INFIBEAM" in r.raw_narration]
        assert all(r.txn_type_hint == TxnTypeHint.UPI for r in upi_rows)

    def test_non_upi_payment_unknown(self, parser: YesCcPdfParser, batch_id: str):
        result = parser.parse_text_content(batch_id, PAYMENT_ROW)
        # PAYMENT RECEIVED BBPS is not UPI/NEFT/IMPS → UNKNOWN
        assert result.rows[0].txn_type_hint == TxnTypeHint.UNKNOWN


# ── Confidence ────────────────────────────────────────────────────────────────

class TestConfidence:
    def test_confidence_above_threshold(self, parser: YesCcPdfParser, batch_id: str):
        result = parser.parse_text_content(batch_id, MINIMAL_STATEMENT)
        assert result.confidence >= 0.75

    def test_succeeded_flag_set(self, parser: YesCcPdfParser, batch_id: str):
        result = parser.parse_text_content(batch_id, MINIMAL_STATEMENT)
        assert result.succeeded is True


# ── Merged merchant category (PDF text wrap edge case) ───────────────────────

class TestMergedMerchantCategory:
    def test_merged_merchant_parsed(self, parser: YesCcPdfParser, batch_id: str):
        """When pdfplumber merges merchant cat onto the description line, still parses."""
        result = parser.parse_text_content(batch_id, MERGED_MERCHANT_ROW)
        assert len(result.rows) == 1
        row = result.rows[0]
        assert row.raw_debit == "2,499.00"
        assert row.raw_credit is None
        assert row.raw_date == "22/02/2026"


# ── Detector integration ──────────────────────────────────────────────────────

class TestDetection:
    def test_content_detection(self):
        from modules.parser.detector import SourceDetector

        det = SourceDetector()
        content = (
            b"Statement for YES BANK Card Number 3561XXXXXXXX4581\n"
            b"Credit Card Statement\n"
            b"Total Amount Due:\nRs. 60,126.89\n"
            b"Amount (Rs.)\n"
        )
        result = det.detect("statement.pdf", content)
        assert result.source_type == SourceType.YES_BANK_CC
        assert result.confidence >= 0.70

    def test_filename_detection(self):
        from modules.parser.detector import SourceDetector

        det = SourceDetector()
        result = det.detect("yes-cc.pdf", b"%PDF-1.4 stub")
        assert result.source_type == SourceType.YES_BANK_CC
        assert result.confidence >= 0.70
