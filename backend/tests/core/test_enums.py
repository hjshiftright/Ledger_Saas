"""Tests for core/models/enums.py"""

from core.models.enums import (
    BANK_SOURCE_TYPES,
    CAS_SOURCE_TYPES,
    CSV_SOURCE_TYPES,
    PDF_SOURCE_TYPES,
    BatchStatus,
    ConfidenceBand,
    DedupStatus,
    ExtractionMethod,
    FileFormat,
    ParseStatus,
    ReviewStatus,
    SourceType,
    TxnTypeHint,
)


class TestSourceType:
    def test_all_bank_pdfs_in_registry(self):
        """All bank PDF source types should be in the PDF_SOURCE_TYPES set."""
        bank_pdfs = {
            SourceType.HDFC_BANK,
            SourceType.SBI_BANK,
            SourceType.ICICI_BANK,
            SourceType.AXIS_BANK,
            SourceType.KOTAK_BANK,
            SourceType.INDUSIND_BANK,
            SourceType.IDFC_BANK,
        }
        assert bank_pdfs.issubset(PDF_SOURCE_TYPES)

    def test_cas_types_in_pdf_set(self):
        assert CAS_SOURCE_TYPES.issubset(PDF_SOURCE_TYPES)

    def test_zerodha_types_in_csv_set(self):
        zerodha = {
            SourceType.ZERODHA_HOLDINGS,
            SourceType.ZERODHA_TRADEBOOK,
            SourceType.ZERODHA_TAX_PNL,
            SourceType.ZERODHA_CAPITAL_GAINS,
        }
        assert zerodha.issubset(CSV_SOURCE_TYPES)

    def test_source_type_is_string_enum(self):
        assert SourceType.HDFC_BANK == "HDFC_BANK"
        assert SourceType.UNKNOWN.value == "UNKNOWN"

    def test_source_type_roundtrip(self):
        """Can reconstruct from value string."""
        assert SourceType("HDFC_BANK") == SourceType.HDFC_BANK

    def test_pdf_and_csv_sets_are_disjoint(self):
        """A source should not be in both PDF and CSV sets (except generics)."""
        overlap = PDF_SOURCE_TYPES & CSV_SOURCE_TYPES
        assert len(overlap) == 0, f"Unexpected overlap: {overlap}"

    def test_bank_source_types_span_both_formats(self):
        """BANK_SOURCE_TYPES includes both PDF and CSV banks."""
        assert SourceType.HDFC_BANK in BANK_SOURCE_TYPES      # PDF
        assert SourceType.HDFC_BANK_CSV in BANK_SOURCE_TYPES  # CSV


class TestExtractionMethod:
    def test_all_methods_present(self):
        methods = {m.value for m in ExtractionMethod}
        assert "TEXT_LAYER" in methods
        assert "TABLE_EXTRACTION" in methods
        assert "OCR" in methods
        assert "LLM_TEXT" in methods
        assert "LLM_VISION" in methods

    def test_is_string_enum(self):
        assert ExtractionMethod.TEXT_LAYER == "TEXT_LAYER"


class TestTxnTypeHint:
    def test_bank_types_present(self):
        hints = {h.value for h in TxnTypeHint}
        for expected in ("UPI", "NEFT", "IMPS", "ATM_WITHDRAWAL", "CHEQUE", "INTEREST"):
            assert expected in hints

    def test_mf_types_present(self):
        hints = {h.value for h in TxnTypeHint}
        for expected in ("PURCHASE", "REDEMPTION", "SIP", "DIVIDEND_PAYOUT", "DIVIDEND_REINVEST"):
            assert expected in hints


class TestBatchStatus:
    def test_thirteen_states(self):
        """Spec requires exactly 13 states."""
        assert len(list(BatchStatus)) == 13

    def test_terminal_states(self):
        assert BatchStatus.COMPLETED in list(BatchStatus)
        assert BatchStatus.CANCELLED in list(BatchStatus)


class TestConfidenceBand:
    def test_three_bands(self):
        assert len(list(ConfidenceBand)) == 3

    def test_band_values(self):
        assert ConfidenceBand.GREEN == "GREEN"
        assert ConfidenceBand.YELLOW == "YELLOW"
        assert ConfidenceBand.RED == "RED"


class TestFileFormat:
    def test_pdf_and_csv_present(self):
        assert FileFormat.PDF in list(FileFormat)
        assert FileFormat.CSV in list(FileFormat)
        assert FileFormat.XLS in list(FileFormat)
        assert FileFormat.XLSX in list(FileFormat)
