"""Generic CSV / XLS parser.

Handles:
  - Known CSV formats (HDFC CSV, SBI CSV) via column header detection.
  - Unknown formats via ColumnMapping (user assigns semantic columns).

Uses pandas for all CSV/XLS reading.

Design:
    `parse_dataframe()` is the core, pure function — accepts a pandas DataFrame
    and a ColumnMapping, returns RawParsedRow[]. Tests can call this directly.
"""

from __future__ import annotations

import hashlib
import io
import logging
import re
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING

from core.models.enums import ExtractionMethod, SourceType, TxnTypeHint
from core.models.raw_parsed_row import ParseMetadata, RawParsedRow
from core.models.column_mapping import ColumnMapping
from core.utils.confidence import ConfidenceSignals, compute_confidence
from modules.parser.base import BaseParser, ExtractionResult

if TYPE_CHECKING:
    import pandas as pd

logger = logging.getLogger(__name__)

# ── Known CSV column header sets ─────────────────────────────────────────────

# Mapping: frozenset of header keywords → ColumnMapping stub (no mapping_id needed)
_KNOWN_HEADER_MAPPINGS: dict[frozenset[str], ColumnMapping] = {
    # HDFC Bank XLS (downloaded from netbanking — has ~21-row preamble before data header)
    frozenset({"date", "narration", "withdrawal amt.", "deposit amt.", "closing balance"}): ColumnMapping(
        mapping_id="",
        user_id="system",
        format_fingerprint="hdfc_xls_v1",
        mapping_label="HDFC Bank XLS",
        date_column="Date",
        narration_column="Narration",
        debit_column="Withdrawal Amt.",
        credit_column="Deposit Amt.",
        balance_column="Closing Balance",
        reference_column="Chq./Ref.No.",
        date_format="%d/%m/%y",
    ),
    # HDFC Bank CSV
    frozenset({"date", "narration", "withdrawal amt (dr)", "deposit amt (cr)", "closing balance"}): ColumnMapping(
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
    ),
    # SBI Bank CSV / old-format XLSX
    frozenset({"txn date", "description", "debit", "credit", "balance"}): ColumnMapping(
        mapping_id="",
        user_id="system",
        format_fingerprint="sbi_csv_v1",
        mapping_label="SBI Bank CSV",
        date_column="Txn Date",
        narration_column="Description",
        debit_column="Debit",
        credit_column="Credit",
        balance_column="Balance",
        reference_column="Ref No./Cheque No.",
        date_format="%d %b %Y",
    ),
    # SBI Bank XLSX (new format — Date/Details/Ref No/Cheque No headers, DD/MM/YYYY dates,
    # amounts stored as numbers)
    frozenset({"date", "details", "debit", "credit", "balance"}): ColumnMapping(
        mapping_id="",
        user_id="system",
        format_fingerprint="sbi_xlsx_v1",
        mapping_label="SBI Bank XLSX new format",
        date_column="Date",
        narration_column="Details",
        debit_column="Debit",
        credit_column="Credit",
        balance_column="Balance",
        reference_column="Ref No/Cheque No",
        date_format="%d/%m/%Y",
    ),
    # ICICI Bank CSV (netbanking / iMobile export)
    frozenset({"transaction date", "transaction remarks", "withdrawal amount (inr )", "deposit amount (inr )", "balance (inr )"}): ColumnMapping(
        mapping_id="",
        user_id="system",
        format_fingerprint="icici_csv_v1",
        mapping_label="ICICI Bank CSV",
        date_column="Transaction Date",
        narration_column="Transaction Remarks",
        debit_column="Withdrawal Amount (INR )",
        credit_column="Deposit Amount (INR )",
        balance_column="Balance (INR )",
        date_format="%d/%m/%Y",
    ),
    # ICICI Bank XLS (iMobile/netbanking detailed download — no space before paren)
    frozenset({"transaction date", "transaction remarks", "withdrawal amount(inr)", "deposit amount(inr)", "balance(inr)"}): ColumnMapping(
        mapping_id="",
        user_id="system",
        format_fingerprint="icici_xls_v1",
        mapping_label="ICICI Bank XLS",
        date_column="Transaction Date",
        narration_column="Transaction Remarks",
        debit_column="Withdrawal Amount(INR)",
        credit_column="Deposit Amount(INR)",
        balance_column="Balance(INR)",
        reference_column="Cheque Number",
        date_format="%d/%m/%Y",
    ),
    # Axis Bank CSV
    frozenset({"tran date", "particulars", "chq no.", "debit", "credit", "balance"}): ColumnMapping(
        mapping_id="",
        user_id="system",
        format_fingerprint="axis_csv_v1",
        mapping_label="Axis Bank CSV",
        date_column="Tran Date",
        narration_column="PARTICULARS",
        debit_column="Debit",
        credit_column="Credit",
        balance_column="Balance",
        reference_column="Chq No.",
        date_format="%d-%m-%Y",
    ),
    # Kotak Mahindra Bank CSV
    frozenset({"transaction date", "description", "chq/ref number", "debit", "credit", "balance"}): ColumnMapping(
        mapping_id="",
        user_id="system",
        format_fingerprint="kotak_csv_v1",
        mapping_label="Kotak Bank CSV",
        date_column="Transaction Date",
        narration_column="Description",
        debit_column="Debit",
        credit_column="Credit",
        balance_column="Balance",
        reference_column="Chq/Ref Number",
        date_format="%d-%m-%Y",
    ),
    # IDFC First Bank CSV
    frozenset({"transaction date", "transaction details", "reference no.", "debit", "credit", "balance"}): ColumnMapping(
        mapping_id="",
        user_id="system",
        format_fingerprint="idfc_csv_v1",
        mapping_label="IDFC First Bank CSV",
        date_column="Transaction Date",
        narration_column="Transaction Details",
        debit_column="Debit",
        credit_column="Credit",
        balance_column="Balance",
        reference_column="Reference No.",
        date_format="%d/%m/%Y",
    ),
    # Union Bank of India CSV (netbanking export)
    frozenset({"date", "particulars", "chq/ref no.", "debit", "credit", "balance"}): ColumnMapping(
        mapping_id="",
        user_id="system",
        format_fingerprint="union_csv_v1",
        mapping_label="Union Bank of India CSV",
        date_column="Date",
        narration_column="Particulars",
        debit_column="Debit",
        credit_column="Credit",
        balance_column="Balance",
        reference_column="Chq/Ref No.",
        date_format="%d/%m/%Y",
    ),
    # Union Bank of India CSV (alternate column labels seen in some exports)
    frozenset({"tran date", "particulars", "reference no", "debit", "credit", "balance"}): ColumnMapping(
        mapping_id="",
        user_id="system",
        format_fingerprint="union_csv_v2",
        mapping_label="Union Bank of India CSV",
        date_column="Tran Date",
        narration_column="Particulars",
        debit_column="Debit",
        credit_column="Credit",
        balance_column="Balance",
        reference_column="Reference No",
        date_format="%d/%m/%Y",
    ),
    # Union Bank of India XLS — OpTransactionHistoryUX3 format (online banking download)
    # Header row: Date | Tran Id | Remarks | (blank) | UTR Number | Instr. Id | Withdrawals | Deposits | Balance
    frozenset({"date", "tran id", "remarks", "withdrawals", "deposits", "balance"}): ColumnMapping(
        mapping_id="",
        user_id="system",
        format_fingerprint="union_xls_v1",
        mapping_label="Union Bank of India XLS (UX3)",
        date_column="Date",
        narration_column="Remarks",
        debit_column="Withdrawals",
        credit_column="Deposits",
        balance_column="Balance",
        reference_column="Tran Id",
        date_format="%d-%m-%Y",
    ),
}

# Map format_fingerprint → SourceType for auto-detection
_FINGERPRINT_TO_SOURCE_TYPE: dict[str, SourceType] = {
    "hdfc_xls_v1":  SourceType.HDFC_BANK_CSV,
    "hdfc_csv_v1":  SourceType.HDFC_BANK_CSV,
    "sbi_csv_v1":   SourceType.SBI_BANK_CSV,
    "sbi_xlsx_v1":  SourceType.SBI_BANK_CSV,
    "icici_csv_v1": SourceType.ICICI_BANK_CSV,
    "icici_xls_v1": SourceType.ICICI_BANK_CSV,
    "axis_csv_v1":  SourceType.AXIS_BANK_CSV,
    "kotak_csv_v1": SourceType.KOTAK_BANK_CSV,
    "idfc_csv_v1":  SourceType.IDFC_BANK_CSV,
    "union_csv_v1": SourceType.UNION_BANK_CSV,
    "union_csv_v2": SourceType.UNION_BANK_CSV,
    "union_xls_v1": SourceType.UNION_BANK_CSV,
}

_UPI_RE = re.compile(r"\bUPI\b", re.I)
_NEFT_RE = re.compile(r"\bNEFT\b", re.I)
_IMPS_RE = re.compile(r"\bIMPS\b", re.I)


def _infer_txn_type(narration: str) -> TxnTypeHint:
    if _UPI_RE.search(narration):
        return TxnTypeHint.UPI
    if _NEFT_RE.search(narration):
        return TxnTypeHint.NEFT
    if _IMPS_RE.search(narration):
        return TxnTypeHint.IMPS
    return TxnTypeHint.UNKNOWN


def fingerprint_headers(headers: list[str]) -> str:
    """SHA-256 of the sorted, lowercased, stripped header list."""
    key = "|".join(sorted(h.strip().lower() for h in headers))
    return hashlib.sha256(key.encode()).hexdigest()


def detect_column_mapping(headers: list[str]) -> ColumnMapping | None:
    """Return a known ColumnMapping if headers match a known format."""
    lower_headers = {h.strip().lower() for h in headers}
    for signature, mapping in _KNOWN_HEADER_MAPPINGS.items():
        if signature.issubset(lower_headers):
            return mapping
    return None


def _normalise_xls_cell(value: object) -> str:
    """Convert a pandas cell value read from XLS without dtype=str back to string.

    When pandas reads XLS with header=None (no dtype=str), float cells arrive as
    Python floats (e.g. 700.0, 41018.36).  Whole-number floats are kept without
    the trailing '.0' so downstream Decimal parsing is clean.
    """
    if value is None:
        return ""
    s = str(value).strip()
    # Drop nan produced by pandas for empty cells
    if s.lower() == "nan":
        return ""
    # Whole-number float: "700.0" → "700"
    if s.endswith(".0") and s[:-2].lstrip("-").isdigit():
        return s[:-2]
    return s


class GenericCsvParser(BaseParser):
    """Parses CSV and XLS/XLSX files using a ColumnMapping.

    If no column mapping is provided and the headers are not recognized,
    an ExtractionResult with confidence=0.0 is returned and the caller
    should trigger the Column Mapper UI flow.
    """

    source_type = SourceType.GENERIC_CSV
    version = "1.0"
    supported_formats = ["CSV", "XLS", "XLSX"]

    def supported_methods(self) -> list[ExtractionMethod]:
        # CSV only uses TABLE_EXTRACTION (direct pandas read — no text/OCR)
        return [ExtractionMethod.TABLE_EXTRACTION]

    def extract(
        self,
        batch_id: str,
        file_bytes: bytes,
        method: ExtractionMethod,
        column_mapping: ColumnMapping | None = None,
        filename: str = "file.csv",
    ) -> ExtractionResult:
        """Parse a CSV/XLS file.

        Args:
            batch_id: Parent batch ID.
            file_bytes: Raw CSV / XLS bytes.
            method: Should be TABLE_EXTRACTION for CSV files.
            column_mapping: Optional user-confirmed or auto-detected mapping.
            filename: Filename hint to choose between CSV and XLS reading.
        """
        try:
            import pandas  # noqa: PLC0415  (lazy import)
        except ImportError:
            return self._make_failed_result(
                batch_id, method, "pandas is required for CSV/XLS parsing."
            )

        try:
            df = self._read_file(file_bytes, filename)
        except Exception as exc:  # noqa: BLE001
            return self._make_failed_result(batch_id, method, f"Failed to read file: {exc}")

        # Auto-detect column mapping if not provided
        if column_mapping is None:
            column_mapping = detect_column_mapping(list(df.columns))

        if column_mapping is None:
            return ExtractionResult(
                rows=[],
                metadata=ParseMetadata(
                    warnings=["Column mapping required — headers not recognized."],
                    extraction_method=method,
                    parser_version=self.version,
                ),
                method=method,
                confidence=0.0,  # Triggers Column Mapper UI
            )

        rows, errors = self.parse_dataframe(batch_id, df, column_mapping)
        return self._build_result(batch_id, rows, errors, method)

    # ── Core parsing logic (pure — testable without file I/O) ─────────────────

    @staticmethod
    def parse_dataframe(
        batch_id: str,
        df: "pd.DataFrame",
        mapping: ColumnMapping,
    ) -> tuple[list[RawParsedRow], list[str]]:
        """Convert a pandas DataFrame + ColumnMapping into RawParsedRow objects.

        This is the primary unit-testable function.
        Returns (rows, errors).
        """
        rows: list[RawParsedRow] = []
        errors: list[str] = []

        for row_num, (_, row) in enumerate(df.iterrows(), start=1):
            raw_date = str(row.get(mapping.date_column, "")).strip()
            raw_narr = str(row.get(mapping.narration_column, "")).strip()
            # Collapse embedded newlines (e.g. from multi-line XLSX cells) to spaces
            raw_narr = " ".join(raw_narr.split())

            if not raw_date or raw_date.lower() in ("nan", ""):
                errors.append(f"Row {row_num}: missing date")
                continue

            raw_debit: str | None = None
            raw_credit: str | None = None

            _ZERO_VALS = {"0", "0.0", "0.00"}

            if mapping.debit_column and mapping.debit_column in row.index:
                val = str(row[mapping.debit_column]).strip()
                raw_debit = val if val and val.lower() not in ("nan", *_ZERO_VALS) else None

            if mapping.credit_column and mapping.credit_column in row.index:
                val = str(row[mapping.credit_column]).strip()
                raw_credit = val if val and val.lower() not in ("nan", *_ZERO_VALS) else None

            if mapping.amount_column and mapping.amount_column in row.index:
                val = str(row[mapping.amount_column]).strip()
                if val and val.lower() != "nan":
                    # Negative = debit, positive = credit
                    try:
                        amount = Decimal(val.replace(",", ""))
                        if amount < 0:
                            raw_debit = str(abs(amount))
                        else:
                            raw_credit = val
                    except InvalidOperation:
                        errors.append(f"Row {row_num}: cannot parse amount '{val}'")

            raw_balance: str | None = None
            if mapping.balance_column and mapping.balance_column in row.index:
                val = str(row[mapping.balance_column]).strip()
                raw_balance = val if val and val.lower() != "nan" else None

            raw_ref: str | None = None
            if mapping.reference_column and mapping.reference_column in row.index:
                val = str(row[mapping.reference_column]).strip()
                raw_ref = val if val and val.lower() != "nan" else None

            has_amount = bool(raw_debit or raw_credit)
            if not has_amount:
                errors.append(f"Row {row_num}: no debit or credit amount")

            detected_source_type = _FINGERPRINT_TO_SOURCE_TYPE.get(
                mapping.format_fingerprint or "", SourceType.GENERIC_CSV
            )
            rows.append(
                RawParsedRow(
                    batch_id=batch_id,
                    source_type=detected_source_type,
                    parser_version="1.0",
                    extraction_method=ExtractionMethod.TABLE_EXTRACTION,
                    raw_date=raw_date,
                    raw_narration=raw_narr,
                    raw_debit=raw_debit,
                    raw_credit=raw_credit,
                    raw_balance=raw_balance,
                    raw_reference=raw_ref,
                    txn_type_hint=_infer_txn_type(raw_narr),
                    row_confidence=0.9 if has_amount else 0.5,
                    row_number=row_num,
                )
            )

        return rows, errors

    # ── Private ───────────────────────────────────────────────────────────────

    @staticmethod
    def _read_file(file_bytes: bytes, filename: str) -> "pd.DataFrame":
        import pandas as pd

        # Detect file type by magic bytes first, then fall back to extension.
        # This ensures correct handling when callers omit or default the filename.
        # OLE2/CFBF container (real XLS, DOC, …): D0 CF 11 E0
        # ZIP container (XLSX, DOCX, …):          PK 03 04
        magic = file_bytes[:4]
        if magic == b"\xD0\xCF\x11\xE0":
            ext = "xls"
        elif magic == b"PK\x03\x04":
            ext = "xlsx"
        else:
            ext = filename.rsplit(".", 1)[-1].lower()

        if ext in ("xls", "xlsx"):
            # SBI old-format "XLS" is actually a tab-separated text file with a .xls
            # extension and ' single-quoted cell values — detect by magic-byte absence.
            if magic not in (b"\xD0\xCF\x11\xE0", b"PK\x03\x04"):
                result = GenericCsvParser._read_sbi_pseudo_xls(file_bytes)
                if result is not None:
                    return result
            return GenericCsvParser._read_xls(file_bytes, ext)

        # CSV (or unknown extension, e.g. when ExtractionChain passes no filename and
        # the parser defaults to "file.csv"). Before reading as comma-separated CSV,
        # check whether the content actually looks like a pseudo-XLS (SBI old format:
        # tab-separated text with single-quoted cells). Magic bytes for OLE2/ZIP/PDF
        # are absent from such files, so they always reach this branch.
        if (
            magic not in (b"\xD0\xCF\x11\xE0", b"PK\x03\x04")
            and not file_bytes[:5].lstrip(b"\xef\xbb\xbf").startswith(b"%PDF")
        ):
            pseudo = GenericCsvParser._read_sbi_pseudo_xls(file_bytes)
            if pseudo is not None:
                return pseudo

        # True CSV — try UTF-8 first, then latin-1
        try:
            return pd.read_csv(io.BytesIO(file_bytes), dtype=str)
        except UnicodeDecodeError:
            return pd.read_csv(io.BytesIO(file_bytes), dtype=str, encoding="latin-1")

    @staticmethod
    def _read_sbi_pseudo_xls(file_bytes: bytes) -> "pd.DataFrame | None":
        """Handle SBI old-format XLS exports: tab-separated text with 'quoted' cells.

        SBI netbanking exports an XLS with .xls extension that is actually a
        tab-delimited text file.  Each cell value is surrounded by single-quote
        characters (e.g. 'Txn Date'\\t'2 Apr 2023'\\t...).  This function:
          1. Decodes the bytes (UTF-8 then latin-1 fallback)
          2. Finds the header row containing 'Txn Date' (first occurrence)
          3. Returns a DataFrame with quotes stripped and proper column names.

        Returns None if the file does not look like a SBI pseudo-XLS.
        """
        import pandas as pd

        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = file_bytes.decode("latin-1")

        lines = text.splitlines()
        header_idx: int | None = None
        for i, line in enumerate(lines):
            # Strip enclosing quotes from each tab-delimited cell for the check
            cells = [c.strip().strip("'") for c in line.split("\t")]
            if any(c.lower() == "txn date" for c in cells):
                header_idx = i
                break

        if header_idx is None:
            return None

        # Build header list (strip quotes + extra whitespace)
        raw_headers = [c.strip().strip("'").strip() for c in lines[header_idx].split("\t")]
        # Remove empty trailing headers
        while raw_headers and not raw_headers[-1]:
            raw_headers.pop()

        records: list[dict[str, str]] = []
        for line in lines[header_idx + 1:]:
            parts = [c.strip().strip("'").strip() for c in line.split("\t")]
            if not any(parts):
                continue
            # Pad or trim to header width
            parts = (parts + [""] * len(raw_headers))[: len(raw_headers)]
            row = dict(zip(raw_headers, parts))
            # Keep only rows that have a non-empty Txn Date column
            date_val = row.get("Txn Date", "").strip()
            if not date_val:
                continue
            records.append(row)

        if not records:
            return None

        return pd.DataFrame(records, columns=raw_headers)

    # Keywords used to identify a real transaction header row in XLS preambles
    _XLS_HEADER_KEYWORDS: frozenset[str] = frozenset({
        # ICICI netbanking XLS
        "transaction date", "transaction remarks",
        "withdrawal amount(inr)", "deposit amount(inr)", "balance(inr)",
        "withdrawal amount (inr )", "deposit amount (inr )", "balance (inr )",
        "withdrawal amount (inr)", "deposit amount (inr)", "balance (inr)",
        # SBI netbanking XLS / XLSX (old format)
        "txn date", "value date", "description", "debit", "credit", "balance",
        "ref no./cheque no.",
        # SBI netbanking XLSX (new format — Date/Details headers)
        "date", "details", "ref no/cheque no",
        # Union Bank UX3 XLS (online banking download)
        "tran id", "remarks", "utr number", "instr. id", "withdrawals", "deposits",
    })

    @staticmethod
    def _read_xls(file_bytes: bytes, ext: str) -> "pd.DataFrame":
        """Read XLS/XLSX, auto-detecting preamble rows for HDFC and ICICI exports.

        HDFC netbanking XLS: ~21 metadata rows before header (Date | Narration | …).
        ICICI netbanking XLS: ~11 metadata rows before header (S No. | Value Date | Transaction Date | …).
        This method finds the real header row by two heuristics:
          1. HDFC pattern: first cell == "Date" and second == "Narration"
          2. Generic pattern: row contains ≥ 2 known transaction-column keyword matches
        For ICICI, any serial-number column ("S No.") and "Value Date" duplicate are kept
        but the ColumnMapping simply ignores them (they are not in the mapping).
        """
        import pandas as pd

        # First pass: raw read without header to locate the real header row
        engine = "xlrd" if ext == "xls" else None
        df_raw = pd.read_excel(
            io.BytesIO(file_bytes), header=None, dtype=str, engine=engine
        )

        header_row_idx: int | None = None
        hdfc_style = False
        # Scan all rows (no fixed limit) so variable-length preambles (nominee details,
        # account info, etc.) don't push the real header row past the search window.
        for idx, row in df_raw.iterrows():
            cells_raw = [str(c).strip() for c in row]
            cells_low = [c.lower() for c in cells_raw]

            # HDFC pattern: "Date" | "Narration" as first two non-empty cells
            if cells_raw[0] == "Date" and len(cells_raw) > 1 and cells_raw[1] == "Narration":
                header_row_idx = int(idx)
                hdfc_style = True
                break

            # Generic preamble pattern: ≥ 2 cells match known transaction header keywords
            keyword_hits = sum(
                1 for c in cells_low
                if c in GenericCsvParser._XLS_HEADER_KEYWORDS
            )
            if keyword_hits >= 2:
                header_row_idx = int(idx)
                break

        if header_row_idx is None:
            # No preamble detected — standard read
            return pd.read_excel(io.BytesIO(file_bytes), dtype=str, engine=engine)

        # Build DataFrame: header row → column names (deduplicate blank/nan entries)
        raw_cols = [str(v).strip() for v in df_raw.iloc[header_row_idx]]
        seen: dict[str, int] = {}
        columns: list[str] = []
        for i, c in enumerate(raw_cols):
            if not c or c.lower() == "nan":
                c = f"_col{i}"
            if c in seen:
                seen[c] += 1
                c = f"{c}_{seen[c]}"
            else:
                seen[c] = 0
            columns.append(c)

        if hdfc_style:
            # HDFC has a "***" separator row right after the header
            data_start = header_row_idx + 2
        else:
            # ICICI and others: data starts immediately after the header row
            data_start = header_row_idx + 1

        df = df_raw.iloc[data_start:].copy()
        df.columns = columns
        df = df.reset_index(drop=True)

        # Identify the date column (first column whose name contains "date" case-insensitive)
        date_col = next(
            (c for c in df.columns if "date" in c.lower() and "value" not in c.lower()),
            columns[0],  # fallback to first column
        )

        # Drop trailing footer / empty rows — keep only rows with a recognisable date value.
        # Accepted formats: DD/MM/YY(YY), DD-MM-YYYY, D Mon YYYY (SBI), DD Mon YYYY, etc.
        if date_col in df.columns:
            date_mask = df[date_col].str.strip().str.match(
                # Match DD/MM/YYYY, DD-MM-YYYY, or with optional time HH:MM:SS
                r"^\d{1,2}[/\-.\s]\w{2,4}[/\-.\s]\d{2,4}(\s+\d{1,2}:\d{2}(:\d{2})?)?\s*$",
                na=False,
                case=False,
            )
            df = df[date_mask].reset_index(drop=True)
            # Strip time portion from datetime values (e.g., "02-04-2025 01:34:00" → "02-04-2025")
            df[date_col] = df[date_col].str.strip().str.replace(
                r"\s+\d{1,2}:\d{2}(:\d{2})?\s*$", "", regex=True
            ).str.strip()

        # Normalise float cells (e.g. "700.0" → "700")
        for col in df.columns:
            df[col] = df[col].apply(_normalise_xls_cell)

        return df

    def _build_result(
        self,
        batch_id: str,
        rows: list[RawParsedRow],
        errors: list[str],
        method: ExtractionMethod,
    ) -> ExtractionResult:
        signals = ConfidenceSignals(
            balance_cross_check_passed=None,  # Deferred to SM-E normalisation
            all_rows_have_valid_date=bool(rows) and all(bool(r.raw_date.strip()) for r in rows),
            all_rows_have_amount=bool(rows) and all(r.raw_debit or r.raw_credit for r in rows),
            row_count_positive=len(rows) > 0,
            no_row_parse_errors=len(errors) == 0,
        )
        confidence = compute_confidence(signals)
        dates = [r.raw_date for r in rows if r.raw_date]
        meta = ParseMetadata(
            statement_from=dates[0] if dates else None,
            statement_to=dates[-1] if dates else None,
            total_rows_found=len(rows),
            rows_with_errors=len(errors),
            overall_confidence=confidence,
            warnings=errors,
            extraction_method=method,
            parser_version=self.version,
        )
        return ExtractionResult(rows=rows, metadata=meta, method=method, confidence=confidence)
