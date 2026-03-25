"""Tests for GenericCsvParser — parse_dataframe(), detect_column_mapping(), fingerprint_headers()."""

from __future__ import annotations

import io
import uuid
from decimal import Decimal

import pytest

from core.models.column_mapping import ColumnMapping
from core.models.enums import ExtractionMethod, SourceType, TxnTypeHint
from modules.parser.parsers.generic_csv import (
    GenericCsvParser,
    detect_column_mapping,
    fingerprint_headers,
)

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not PANDAS_AVAILABLE, reason="pandas not installed")


@pytest.fixture
def parser() -> GenericCsvParser:
    return GenericCsvParser()


@pytest.fixture
def batch_id_local() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def hdfc_csv_df() -> "pd.DataFrame":
    data = {
        "Date": ["01/01/2026", "02/01/2026", "05/01/2026"],
        "Narration": ["UPI/SWIGGY FOOD", "NEFT CR/SALARY", "ATM WITHDRAWAL"],
        "Chq./Ref.No.": ["147896325478", "NEFT2026", "ATM001"],
        "Value Dt": ["01/01/2026", "02/01/2026", "05/01/2026"],
        "Withdrawal Amt (Dr)": ["450.00", "", "5000.00"],
        "Deposit Amt (Cr)": ["", "50000.00", ""],
        "Closing Balance": ["19550.00", "69550.00", "64550.00"],
    }
    return pd.DataFrame(data)


@pytest.fixture
def hdfc_column_mapping() -> ColumnMapping:
    return ColumnMapping(
        mapping_id="",
        user_id="system",
        format_fingerprint="hdfc_csv_v1",
        mapping_label="HDFC Bank CSV",
        date_column="Date",
        narration_column="Narration",
        debit_column="Withdrawal Amt (Dr)",
        credit_column="Deposit Amt (Cr)",
        balance_column="Closing Balance",
        reference_column="Chq./Ref.No.",
        date_format="%d/%m/%Y",
    )


@pytest.fixture
def signed_csv_df() -> "pd.DataFrame":
    """CSV with a single signed 'Amount' column (positive=credit, negative=debit)."""
    data = {
        "Trans Date": ["01/01/2026", "02/01/2026"],
        "Details": ["Shopping", "Salary"],
        "Amount": ["-450.00", "50000.00"],
        "Balance": ["19550.00", "69550.00"],
    }
    return pd.DataFrame(data)


@pytest.fixture
def signed_column_mapping() -> ColumnMapping:
    return ColumnMapping(
        user_id="user1",
        format_fingerprint="signed_test",
        mapping_label="Signed Amount CSV",
        date_column="Trans Date",
        narration_column="Details",
        amount_column="Amount",
        balance_column="Balance",
    )


# ── detect_column_mapping ─────────────────────────────────────────────────────

class TestDetectColumnMapping:
    def test_detects_hdfc_csv_headers(self):
        headers = [
            "Date", "Narration", "Chq./Ref.No.", "Value Dt",
            "Withdrawal Amt (Dr)", "Deposit Amt (Cr)", "Closing Balance",
        ]
        mapping = detect_column_mapping(headers)
        assert mapping is not None
        assert "HDFC" in mapping.mapping_label.upper()
        assert mapping.date_column == "Date"
        assert mapping.debit_column == "Withdrawal Amt (Dr)"

    def test_detects_sbi_csv_headers(self):
        headers = ["Txn Date", "Description", "Ref No./Cheque No.", "Debit", "Credit", "Balance"]
        mapping = detect_column_mapping(headers)
        assert mapping is not None
        assert "SBI" in mapping.mapping_label.upper()

    def test_returns_none_for_unknown_headers(self):
        headers = ["Trans Date", "Details", "Debit", "Credit", "Bal"]
        mapping = detect_column_mapping(headers)
        assert mapping is None

    def test_case_insensitive_match(self):
        """Header matching should be case-insensitive."""
        headers = [
            "date", "narration", "chq./ref.no.", "value dt",
            "withdrawal amt (dr)", "deposit amt (cr)", "closing balance",
        ]
        mapping = detect_column_mapping(headers)
        assert mapping is not None


# ── fingerprint_headers ───────────────────────────────────────────────────────

class TestFingerprintHeaders:
    def test_same_headers_same_fingerprint(self):
        headers = ["Date", "Narration", "Debit", "Credit", "Balance"]
        fp1 = fingerprint_headers(headers)
        fp2 = fingerprint_headers(headers)
        assert fp1 == fp2

    def test_order_independent(self):
        h1 = ["Date", "Narration", "Debit"]
        h2 = ["Narration", "Debit", "Date"]
        assert fingerprint_headers(h1) == fingerprint_headers(h2)

    def test_different_headers_different_fingerprint(self):
        h1 = ["Date", "Narration", "Debit"]
        h2 = ["Date", "Description", "Amount"]
        assert fingerprint_headers(h1) != fingerprint_headers(h2)

    def test_whitespace_stripped(self):
        h1 = ["Date", "Narration"]
        h2 = ["  Date  ", " Narration "]
        assert fingerprint_headers(h1) == fingerprint_headers(h2)

    def test_returns_hex_string(self):
        fp = fingerprint_headers(["Date", "Narration"])
        assert len(fp) == 64  # SHA-256 hex = 64 chars
        assert all(c in "0123456789abcdef" for c in fp)


# ── parse_dataframe ───────────────────────────────────────────────────────────

class TestParseDataframe:
    def test_extracts_rows_from_hdfc_csv(self, batch_id_local, hdfc_csv_df, hdfc_column_mapping):
        rows, errors = GenericCsvParser.parse_dataframe(
            batch_id_local, hdfc_csv_df, hdfc_column_mapping
        )
        assert len(rows) == 3
        assert errors == []

    def test_first_row_is_debit(self, batch_id_local, hdfc_csv_df, hdfc_column_mapping):
        rows, _ = GenericCsvParser.parse_dataframe(batch_id_local, hdfc_csv_df, hdfc_column_mapping)
        row = rows[0]
        assert row.raw_debit == "450.00"
        assert row.raw_credit is None

    def test_second_row_is_credit(self, batch_id_local, hdfc_csv_df, hdfc_column_mapping):
        rows, _ = GenericCsvParser.parse_dataframe(batch_id_local, hdfc_csv_df, hdfc_column_mapping)
        row = rows[1]
        assert row.raw_credit == "50000.00"
        assert row.raw_debit is None

    def test_narration_is_populated(self, batch_id_local, hdfc_csv_df, hdfc_column_mapping):
        rows, _ = GenericCsvParser.parse_dataframe(batch_id_local, hdfc_csv_df, hdfc_column_mapping)
        assert rows[0].raw_narration == "UPI/SWIGGY FOOD"

    def test_balance_is_populated(self, batch_id_local, hdfc_csv_df, hdfc_column_mapping):
        rows, _ = GenericCsvParser.parse_dataframe(batch_id_local, hdfc_csv_df, hdfc_column_mapping)
        assert rows[0].raw_balance == "19550.00"

    def test_rows_tagged_with_batch_id(self, batch_id_local, hdfc_csv_df, hdfc_column_mapping):
        rows, _ = GenericCsvParser.parse_dataframe(batch_id_local, hdfc_csv_df, hdfc_column_mapping)
        assert all(r.batch_id == batch_id_local for r in rows)

    def test_rows_tagged_as_hdfc_bank_csv(self, batch_id_local, hdfc_csv_df, hdfc_column_mapping):
        """Rows parsed with HDFC mapping get source_type=HDFC_BANK_CSV (not GENERIC_CSV)."""
        rows, _ = GenericCsvParser.parse_dataframe(batch_id_local, hdfc_csv_df, hdfc_column_mapping)
        assert all(r.source_type == SourceType.HDFC_BANK_CSV for r in rows)

    def test_row_numbers_are_sequential(self, batch_id_local, hdfc_csv_df, hdfc_column_mapping):
        rows, _ = GenericCsvParser.parse_dataframe(batch_id_local, hdfc_csv_df, hdfc_column_mapping)
        for i, row in enumerate(rows, start=1):
            assert row.row_number == i

    def test_signed_amount_negative_becomes_debit(self, batch_id_local, signed_csv_df, signed_column_mapping):
        rows, errors = GenericCsvParser.parse_dataframe(
            batch_id_local, signed_csv_df, signed_column_mapping
        )
        shopping = rows[0]
        assert shopping.raw_debit is not None
        assert shopping.raw_credit is None

    def test_signed_amount_positive_becomes_credit(self, batch_id_local, signed_csv_df, signed_column_mapping):
        rows, errors = GenericCsvParser.parse_dataframe(
            batch_id_local, signed_csv_df, signed_column_mapping
        )
        salary = rows[1]
        assert salary.raw_credit is not None
        assert salary.raw_debit is None

    def test_missing_date_row_produces_error(self, batch_id_local, hdfc_column_mapping):
        df = pd.DataFrame({
            "Date": ["", "02/01/2026"],
            "Narration": ["Test A", "Test B"],
            "Withdrawal Amt (Dr)": ["100.00", ""],
            "Deposit Amt (Cr)": ["", "500.00"],
            "Closing Balance": ["900.00", "1400.00"],
        })
        rows, errors = GenericCsvParser.parse_dataframe(batch_id_local, df, hdfc_column_mapping)
        assert any("date" in e.lower() for e in errors)
        assert len(rows) == 1  # Only the valid row


# ── extract() integration ─────────────────────────────────────────────────────

class TestGenericCsvParserExtract:
    def test_extract_with_hdfc_headers_returns_high_confidence(self, parser, batch_id_local):
        csv_bytes = (
            b"Date,Narration,Chq./Ref.No.,Value Dt,Withdrawal Amt (Dr),Deposit Amt (Cr),Closing Balance\n"
            b"01/01/2026,UPI/SWIGGY,REF1,01/01/2026,450.00,,19550.00\n"
            b"02/01/2026,NEFT SALARY,NEFT1,02/01/2026,,50000.00,69550.00\n"
        )
        result = parser.extract(
            batch_id=batch_id_local,
            file_bytes=csv_bytes,
            method=ExtractionMethod.TABLE_EXTRACTION,
            filename="statement.csv",
        )
        assert result.confidence > 0.0
        assert len(result.rows) == 2

    def test_extract_without_known_headers_returns_zero_confidence(self, parser, batch_id_local):
        csv_bytes = b"Trans Date,Details,Amount\n01/01/2026,Test,100.00\n"
        result = parser.extract(
            batch_id=batch_id_local,
            file_bytes=csv_bytes,
            method=ExtractionMethod.TABLE_EXTRACTION,
            filename="unknown.csv",
        )
        assert result.confidence == 0.0
        assert len(result.rows) == 0  # Triggers Column Mapper UI


# ── ICICI / Axis / Kotak / IDFC header detection ──────────────────────────────

class TestDetectBankCsvHeaders:
    """detect_column_mapping() must recognise ICICI, Axis, Kotak and IDFC headers."""

    def test_detects_icici_csv_headers(self):
        headers = [
            "Transaction Date", "Transaction Remarks",
            "Withdrawal Amount (INR )", "Deposit Amount (INR )", "Balance (INR )",
        ]
        mapping = detect_column_mapping(headers)
        assert mapping is not None
        assert "ICICI" in mapping.mapping_label.upper()
        assert mapping.format_fingerprint == "icici_csv_v1"

    def test_detects_axis_csv_headers(self):
        headers = ["Tran Date", "PARTICULARS", "Chq No.", "Value Date", "Debit", "Credit", "Balance"]
        mapping = detect_column_mapping(headers)
        assert mapping is not None
        assert "AXIS" in mapping.mapping_label.upper()
        assert mapping.format_fingerprint == "axis_csv_v1"

    def test_detects_kotak_csv_headers(self):
        headers = ["Transaction Date", "Description", "Chq/Ref Number", "Debit", "Credit", "Balance"]
        mapping = detect_column_mapping(headers)
        assert mapping is not None
        assert "KOTAK" in mapping.mapping_label.upper()
        assert mapping.format_fingerprint == "kotak_csv_v1"

    def test_detects_idfc_csv_headers(self):
        headers = ["Transaction Date", "Transaction Details", "Reference No.", "Debit", "Credit", "Balance"]
        mapping = detect_column_mapping(headers)
        assert mapping is not None
        assert "IDFC" in mapping.mapping_label.upper()
        assert mapping.format_fingerprint == "idfc_csv_v1"

    def test_icici_source_type(self, batch_id_local):
        """Rows produced from an ICICI CSV must carry SourceType.ICICI_BANK_CSV."""
        df = pd.DataFrame({
            "Transaction Date": ["01/01/2026", "02/01/2026"],
            "Transaction Remarks": ["UPI SWIGGY", "NEFT SALARY"],
            "Withdrawal Amount (INR )": ["450.00", ""],
            "Deposit Amount (INR )": ["", "50000.00"],
            "Balance (INR )": ["19550.00", "69550.00"],
        })
        mapping = detect_column_mapping(list(df.columns))
        assert mapping is not None
        rows, _ = GenericCsvParser.parse_dataframe(batch_id_local, df, mapping)
        assert all(r.source_type == SourceType.ICICI_BANK_CSV for r in rows)

    def test_axis_source_type(self, batch_id_local):
        df = pd.DataFrame({
            "Tran Date": ["01-01-2026", "02-01-2026"],
            "PARTICULARS": ["UPI ZOMATO", "IMPS RENT"],
            "Chq No.": ["", ""],
            "Value Date": ["01-01-2026", "02-01-2026"],
            "Debit": ["350.00", "12000.00"],
            "Credit": ["", ""],
            "Balance": ["9650.00", "0.00"],
        })
        mapping = detect_column_mapping(list(df.columns))
        assert mapping is not None
        rows, _ = GenericCsvParser.parse_dataframe(batch_id_local, df, mapping)
        assert all(r.source_type == SourceType.AXIS_BANK_CSV for r in rows)

    def test_kotak_source_type(self, batch_id_local):
        df = pd.DataFrame({
            "Transaction Date": ["01-01-2026"],
            "Description": ["ATM WITHDRAWAL"],
            "Chq/Ref Number": ["ATM001"],
            "Debit": ["5000.00"],
            "Credit": [""],
            "Balance": ["15000.00"],
        })
        mapping = detect_column_mapping(list(df.columns))
        assert mapping is not None
        rows, _ = GenericCsvParser.parse_dataframe(batch_id_local, df, mapping)
        assert all(r.source_type == SourceType.KOTAK_BANK_CSV for r in rows)

    def test_idfc_source_type(self, batch_id_local):
        df = pd.DataFrame({
            "Transaction Date": ["03/01/2026"],
            "Transaction Details": ["NEFT CREDIT"],
            "Reference No.": ["NEFT001"],
            "Debit": [""],
            "Credit": ["25000.00"],
            "Balance": ["45000.00"],
        })
        mapping = detect_column_mapping(list(df.columns))
        assert mapping is not None
        rows, _ = GenericCsvParser.parse_dataframe(batch_id_local, df, mapping)
        assert all(r.source_type == SourceType.IDFC_BANK_CSV for r in rows)

    def test_extract_icici_csv_bytes(self, parser, batch_id_local):
        csv_bytes = (
            b"Transaction Date,Transaction Remarks,Withdrawal Amount (INR ),Deposit Amount (INR ),Balance (INR )\n"
            b"01/01/2026,UPI SWIGGY,450.00,,19550.00\n"
            b"02/01/2026,NEFT SALARY,,50000.00,69550.00\n"
        )
        result = parser.extract(
            batch_id=batch_id_local,
            file_bytes=csv_bytes,
            method=ExtractionMethod.TABLE_EXTRACTION,
            filename="icici_statement.csv",
        )
        assert len(result.rows) == 2
        assert result.rows[0].source_type == SourceType.ICICI_BANK_CSV
