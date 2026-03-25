"""Tests for HdfcCcPdfParser — HDFC Bank Credit Card PDF parser.

All tests use ``parse_text_content()`` to avoid PDF I/O, keeping them fast
and deterministic.

The fixture strings mirror the text extracted by pdfplumber from the real
HDFC CC statement (Mar2026_Billedstatements_6424_24-03-26_09-17.pdf).

Transaction format (pdfplumber inline):
    DD/MM/YYYY| HH:MM  DESCRIPTION  [+ ]C  amount  PI
    "+" before the currency glyph → credit (payment/refund)
"""

from __future__ import annotations

import pytest

from core.models.enums import ExtractionMethod, SourceType, TxnTypeHint
from modules.parser.parsers.hdfc_cc_pdf import HdfcCcPdfParser


# ── Fixture text ──────────────────────────────────────────────────────────────

_HEADER = """\
DUPLICATE Millennia Credit Card Statement
HSN Code: 997113 HDFC Bank Credit Cards GSTIN: 33AAACH2702H2Z6
DANTURTI PARVATHI RAJASEKHAR Credit Card No. 434155XXXXXX6424
Statement Date 22 Mar, 2026
Billing Period 23 Feb, 2026 - 22 Mar, 2026
PAYMENTS/CREDITS PURCHASES/DEBIT
PREVIOUS STATEMENT DUES FINANCE CHARGES TOTAL AMOUNT DUE
DATE & TIME TRANSACTION DESCRIPTION AMOUNT PI
"""

MINIMAL_STATEMENT = (
    _HEADER
    + "23/02/2026| 20:56 AMAZON PAY INDIA PRIVATE WWW.AMAZON C 1,004.00 l\n"
)

PAYMENT_CREDIT = (
    _HEADER
    + "23/02/2026| 20:56 BPPY CC PAYMENT BD016054BAKAAAGVYCP (Ref# ST260560083000010263758) + C 15,336.00 l\n"
)

MULTI_TXN = (
    _HEADER
    + "23/02/2026| 20:56 AMAZON PAY INDIA PRIVATE WWW.AMAZON C 1,004.00 l\n"
    + "23/02/2026| 20:56 BPPY CC PAYMENT BD016054BAKAAAGVYCP (Ref# ST260560083000010263758) + C 15,336.00 l\n"
    + "26/02/2026| 05:40 EMI SpayBBPS 6276930434 Banga 60561643 C 2,538.00 l\n"
    + "27/02/2026| 10:35 ASSPLBangalore C 1,204.00 l\n"
    + "12/03/2026| 10:03 ASSPLBangalore C 284.00 l\n"
    + "12/03/2026| 10:05 ASSPLBangalore C 284.00 l\n"
    + "12/03/2026| 00:00 ASSPLBangalore + C 284.00 l\n"
    + "14/03/2026| 19:24 CORNER HOUSE ICE CREAMSBANGALORE C 221.00 l\n"
    + "17/03/2026| 13:44 AMAZONINGURGAON C 1,626.07 l\n"
)

UPI_TXN = (
    _HEADER
    + "10/01/2026| 14:30 UPI_SWIGGY FOOD ORDER BANGALORE C 350.00 l\n"
)

NEFT_TXN = (
    _HEADER
    + "15/01/2026| 09:00 NEFT PAYMENT RECEIVED + C 25,000.00 l\n"
)

EMI_TXN = (
    _HEADER
    + "26/02/2026| 05:40 EMI SpayBBPS 6276930434 C 2,538.00 l\n"
)

REFUND_TXN = (
    _HEADER
    + "20/01/2026| 11:22 AMAZON REFUND RETURN (Ref# TXN12345ABCDE) + C 599.00 l\n"
)

NO_REF_TXN = (
    _HEADER
    + "14/03/2026| 19:24 CORNER HOUSE ICE CREAMSBANGALORE C 221.00 l\n"
)

# Page break: same format continues on next "page"
PAGE2_TXN = (
    _HEADER
    + "12/03/2026| 00:00 ASSPLBangalore + C 284.00 l\n"
    + "Offers on your card\n"
    + "Domestic Transactions\n"
    + "DATE & TIME TRANSACTION DESCRIPTION AMOUNT PI\n"
    + "14/03/2026| 19:24 CORNER HOUSE ICE CREAMSBANGALORE C 221.00 l\n"
)


@pytest.fixture()
def parser() -> HdfcCcPdfParser:
    return HdfcCcPdfParser()


@pytest.fixture()
def batch_id() -> str:
    return "test-batch-hdfccc-001"


# ── 1. Parser metadata ────────────────────────────────────────────────────────

class TestParserMeta:
    def test_source_type(self, parser):
        assert parser.source_type == SourceType.HDFC_BANK_CC

    def test_version_string(self, parser):
        assert parser.version == "1.0"

    def test_supported_methods_text_layer(self, parser):
        assert ExtractionMethod.TEXT_LAYER in parser.supported_methods()

    def test_supported_methods_ocr(self, parser):
        assert ExtractionMethod.OCR in parser.supported_methods()

    def test_supported_methods_no_table(self, parser):
        assert ExtractionMethod.TABLE_EXTRACTION not in parser.supported_methods()


# ── 2. Row count ──────────────────────────────────────────────────────────────

class TestRowCount:
    def test_minimal_one_row(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MINIMAL_STATEMENT)
        assert len(result.rows) == 1

    def test_multi_txn_nine_rows(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MULTI_TXN)
        assert len(result.rows) == 9

    def test_page2_skips_header_lines(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, PAGE2_TXN)
        assert len(result.rows) == 2

    def test_empty_text_no_rows(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, "")
        assert len(result.rows) == 0

    def test_header_only_no_rows(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, _HEADER)
        assert len(result.rows) == 0


# ── 3. Debit / credit direction ───────────────────────────────────────────────

class TestAmountDirection:
    def test_purchase_is_debit(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MINIMAL_STATEMENT)
        row = result.rows[0]
        assert row.raw_debit == "1,004.00"
        assert row.raw_credit is None

    def test_payment_plus_prefix_is_credit(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, PAYMENT_CREDIT)
        row = result.rows[0]
        assert row.raw_credit == "15,336.00"
        assert row.raw_debit is None

    def test_refund_plus_prefix_is_credit(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, REFUND_TXN)
        row = result.rows[0]
        assert row.raw_credit is not None
        assert row.raw_debit is None

    def test_multi_mixed_direction(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MULTI_TXN)
        debits  = [r for r in result.rows if r.raw_debit  is not None]
        credits = [r for r in result.rows if r.raw_credit is not None]
        assert len(debits)  == 7
        assert len(credits) == 2

    def test_raw_balance_is_none(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MINIMAL_STATEMENT)
        assert result.rows[0].raw_balance is None


# ── 4. Source type tagging ────────────────────────────────────────────────────

class TestSourceTypeTagging:
    def test_all_rows_tagged_hdfc_cc(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MULTI_TXN)
        for row in result.rows:
            assert row.source_type == SourceType.HDFC_BANK_CC

    def test_batch_id_propagated(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MINIMAL_STATEMENT)
        assert result.rows[0].batch_id == batch_id


# ── 5. Reference extraction ───────────────────────────────────────────────────

class TestReferenceExtraction:
    def test_ref_extracted_from_description(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, PAYMENT_CREDIT)
        assert result.rows[0].raw_reference == "ST260560083000010263758"

    def test_ref_stripped_from_narration(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, PAYMENT_CREDIT)
        assert "Ref#" not in result.rows[0].raw_narration

    def test_no_ref_gives_none(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, NO_REF_TXN)
        assert result.rows[0].raw_reference is None

    def test_refund_ref_extracted(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, REFUND_TXN)
        assert result.rows[0].raw_reference == "TXN12345ABCDE"


# ── 6. Date parsing ───────────────────────────────────────────────────────────

class TestDateParsing:
    def test_date_preserved_as_dmy(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MINIMAL_STATEMENT)
        assert result.rows[0].raw_date == "23/02/2026"

    def test_date_does_not_include_time(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MINIMAL_STATEMENT)
        assert "|" not in result.rows[0].raw_date
        assert "20:56" not in result.rows[0].raw_date


# ── 7. Statement metadata ─────────────────────────────────────────────────────

class TestMetadata:
    def test_card_number_captured(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MINIMAL_STATEMENT)
        assert result.metadata.account_hint == "434155XXXXXX6424"

    def test_statement_from_date(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MINIMAL_STATEMENT)
        assert result.metadata.statement_from == "2026-02-23"

    def test_statement_to_date(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MINIMAL_STATEMENT)
        assert result.metadata.statement_to == "2026-03-22"

    def test_opening_balance_is_none(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MINIMAL_STATEMENT)
        assert result.metadata.opening_balance is None

    def test_closing_balance_is_none(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MINIMAL_STATEMENT)
        assert result.metadata.closing_balance is None

    def test_balance_cross_check_is_none(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MINIMAL_STATEMENT)
        assert result.metadata.balance_cross_check_passed is None

    def test_total_rows_matches(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MULTI_TXN)
        assert result.metadata.total_rows_found == 9


# ── 8. TxnTypeHint inference ──────────────────────────────────────────────────

class TestTxnTypeHint:
    def test_upi_hint(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, UPI_TXN)
        assert result.rows[0].txn_type_hint == TxnTypeHint.UPI

    def test_neft_hint(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, NEFT_TXN)
        assert result.rows[0].txn_type_hint == TxnTypeHint.NEFT

    def test_emi_falls_back_to_unknown(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, EMI_TXN)
        assert result.rows[0].txn_type_hint == TxnTypeHint.UNKNOWN

    def test_regular_purchase_unknown(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, NO_REF_TXN)
        assert result.rows[0].txn_type_hint == TxnTypeHint.UNKNOWN


# ── 9. Confidence ─────────────────────────────────────────────────────────────

class TestConfidence:
    def test_confidence_is_float(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MINIMAL_STATEMENT)
        assert isinstance(result.confidence, float)

    def test_confidence_high_for_valid_statement(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MULTI_TXN)
        assert result.confidence >= 0.8

    def test_confidence_in_metadata(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MINIMAL_STATEMENT)
        assert result.metadata.overall_confidence == result.confidence

    def test_empty_lower_confidence_than_real(self, parser, batch_id):
        empty  = parser.parse_text_content(batch_id, "")
        real   = parser.parse_text_content(batch_id, MULTI_TXN)
        assert empty.confidence < real.confidence


# ── 10. Narration / description ───────────────────────────────────────────────

class TestNarration:
    def test_description_captured(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MINIMAL_STATEMENT)
        assert "AMAZON PAY" in result.rows[0].raw_narration

    def test_description_excludes_date(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MINIMAL_STATEMENT)
        assert "23/02/2026" not in result.rows[0].raw_narration

    def test_description_excludes_amount(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MINIMAL_STATEMENT)
        assert "1,004.00" not in result.rows[0].raw_narration


# ── 11. Extraction method propagation ────────────────────────────────────────

class TestExtractionMethod:
    def test_default_method_text_layer(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, MINIMAL_STATEMENT)
        assert result.method == ExtractionMethod.TEXT_LAYER

    def test_ocr_method_propagated(self, parser, batch_id):
        result = parser.parse_text_content(
            batch_id, MINIMAL_STATEMENT, ExtractionMethod.OCR
        )
        assert result.method == ExtractionMethod.OCR
        assert result.rows[0].extraction_method == ExtractionMethod.OCR


# ── 12. Detector integration ──────────────────────────────────────────────────

class TestDetection:
    def test_content_sig_hdfc_cc_billing_period(self):
        from modules.parser.detector import SourceDetector
        det = SourceDetector()
        content = (
            b"HDFC Bank Credit Cards GSTIN: 33AAACH2702H2Z6\n"
            b"Credit Card No. 434155XXXXXX6424\n"
            b"Billing Period 23 Feb, 2026 - 22 Mar, 2026\n"
        )
        result = det.detect("statement.pdf", content)
        assert result.source_type == SourceType.HDFC_BANK_CC

    def test_content_sig_total_amount_due(self):
        from modules.parser.detector import SourceDetector
        det = SourceDetector()
        content = (
            b"HDFC Bank Credit Cards\n"
            b"TOTAL AMOUNT DUE\n"
            b"Credit Card No. 434155XXXXXX6424\n"
        )
        result = det.detect("statement.pdf", content)
        assert result.source_type == SourceType.HDFC_BANK_CC

    def test_filename_hdfccc(self):
        from modules.parser.detector import SourceDetector
        det = SourceDetector()
        result = det.detect("hdfccc.pdf", b"%PDF-1.4 stub")
        assert result.source_type == SourceType.HDFC_BANK_CC

    def test_filename_hdfc_credit_card(self):
        from modules.parser.detector import SourceDetector
        det = SourceDetector()
        result = det.detect("hdfc_credit_card_mar2026.pdf", b"%PDF-1.4 stub")
        assert result.source_type == SourceType.HDFC_BANK_CC

    def test_generic_hdfc_stmt_still_hdfc_bank(self):
        """Plain HDFC savings account filename should NOT map to CC."""
        from modules.parser.detector import SourceDetector
        det = SourceDetector()
        result = det.detect("hdfc-stmt-jan2026.pdf", b"%PDF-1.4 stub")
        assert result.source_type == SourceType.HDFC_BANK

    def test_hint_overrides(self):
        from modules.parser.detector import SourceDetector
        det = SourceDetector()
        result = det.detect(
            "random.pdf",
            b"%PDF-1.4 stub",
            source_type_hint=SourceType.HDFC_BANK_CC.value,
        )
        assert result.source_type == SourceType.HDFC_BANK_CC
        assert result.confidence == 1.0


# ── 13. Real-sample smoke test ────────────────────────────────────────────────

class TestRealSample:
    """Smoke test against the real unencrypted PDF."""

    SAMPLE_PATH = "src/samples/Mar2026_Billedstatements_6424_24-03-26_09-17.pdf"

    def test_real_pdf_row_count(self, parser, batch_id):
        import os
        if not os.path.exists(self.SAMPLE_PATH):
            pytest.skip("Real PDF sample not available")

        with open(self.SAMPLE_PATH, "rb") as f:
            file_bytes = f.read()

        from modules.parser.extraction.text_layer import TextLayerExtractor
        pages = TextLayerExtractor().extract_pages(file_bytes)
        combined = "\n".join(pages)
        result = parser.parse_text_content(batch_id, combined)

        assert len(result.rows) >= 9
        assert result.confidence >= 0.8

    def test_real_pdf_card_hint(self, parser, batch_id):
        import os
        if not os.path.exists(self.SAMPLE_PATH):
            pytest.skip("Real PDF sample not available")

        with open(self.SAMPLE_PATH, "rb") as f:
            file_bytes = f.read()

        from modules.parser.extraction.text_layer import TextLayerExtractor
        pages = TextLayerExtractor().extract_pages(file_bytes)
        combined = "\n".join(pages)
        result = parser.parse_text_content(batch_id, combined)

        assert result.metadata.account_hint == "434155XXXXXX6424"
