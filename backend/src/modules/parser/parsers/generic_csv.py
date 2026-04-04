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


def _norm_header_key(raw: str) -> str:
    """Normalize header labels for robust CSV/XLS/XLSX matching."""
    return " ".join(str(raw).replace("\n", " ").split()).strip().lower()

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
    # Bank of Baroda CSV (typical netbanking export)
    frozenset({"txn date", "narration", "debit", "credit", "balance"}): ColumnMapping(
        mapping_id="",
        user_id="system",
        format_fingerprint="baroda_csv_v1",
        mapping_label="Bank of Baroda CSV",
        date_column="Txn Date",
        narration_column="Narration",
        debit_column="Debit",
        credit_column="Credit",
        balance_column="Balance",
        reference_column="Cheque No",
        date_format="%d/%m/%Y",
    ),
    # Bank of Baroda XLS/CSV (statement-style: Value Date / Post Date / Details / Chq.No.)
    frozenset({"value date", "post date", "details", "chq.no.", "debit", "credit", "balance"}): ColumnMapping(
        mapping_id="",
        user_id="system",
        format_fingerprint="baroda_csv_v2",
        mapping_label="Bank of Baroda Statement XLS/CSV",
        date_column="Value Date",
        narration_column="Details",
        debit_column="Debit",
        credit_column="Credit",
        balance_column="Balance",
        reference_column="Chq.No.",
        date_format="%d/%m/%y",
    ),
    # Canara Bank CSV (typical netbanking export)
    frozenset({"transaction date", "description", "cheque no.", "debit", "credit", "balance"}): ColumnMapping(
        mapping_id="",
        user_id="system",
        format_fingerprint="canara_csv_v1",
        mapping_label="Canara Bank CSV",
        date_column="Transaction Date",
        narration_column="Description",
        debit_column="Debit",
        credit_column="Credit",
        balance_column="Balance",
        reference_column="Cheque No.",
        date_format="%d/%m/%Y",
    ),
    # Canara statement export (Txn Date + Value Date + Branch Code)
    frozenset({"txn date", "value date", "cheque no.", "description", "branch code", "debit", "credit", "balance"}): ColumnMapping(
        mapping_id="",
        user_id="system",
        format_fingerprint="canara_csv_v2",
        mapping_label="Canara Statement XLS/CSV",
        date_column="Txn Date",
        narration_column="Description",
        debit_column="Debit",
        credit_column="Credit",
        balance_column="Balance",
        reference_column="Cheque No.",
        date_format="%d-%m-%Y %H:%M:%S",
    ),
    # Canara variant where branch column is "Branch" (second header row has "Code")
    frozenset({"txn date", "value date", "cheque no.", "description", "branch", "debit", "credit", "balance"}): ColumnMapping(
        mapping_id="",
        user_id="system",
        format_fingerprint="canara_csv_v3",
        mapping_label="Canara Statement CSV (Branch column)",
        date_column="Txn Date",
        narration_column="Description",
        debit_column="Debit",
        credit_column="Credit",
        balance_column="Balance",
        reference_column="Cheque No.",
        date_format="%d-%m-%Y %H:%M:%S",
    ),
    # Standard Chartered Bank CSV
    frozenset({"date", "description", "cheque", "deposit", "withdrawal", "balance"}): ColumnMapping(
        mapping_id="",
        user_id="system",
        format_fingerprint="standard_chartered_csv_v0",
        mapping_label="Standard Chartered Bank statement CSV",
        date_column="Date",
        narration_column="Description",
        debit_column="Withdrawal",
        credit_column="Deposit",
        balance_column="Balance",
        reference_column="Cheque",
        date_format="%d %b %y",
    ),
    # Standard Chartered Bank CSV
    frozenset({"date", "description", "cheque number", "debit", "credit", "balance"}): ColumnMapping(
        mapping_id="",
        user_id="system",
        format_fingerprint="standard_chartered_csv_v1",
        mapping_label="Standard Chartered Bank CSV",
        date_column="Date",
        narration_column="Description",
        debit_column="Debit",
        credit_column="Credit",
        balance_column="Balance",
        reference_column="Cheque Number",
        date_format="%d/%m/%Y",
    ),
    # Standard Chartered variant
    frozenset({"transaction date", "narration", "reference", "withdrawal", "deposit", "balance"}): ColumnMapping(
        mapping_id="",
        user_id="system",
        format_fingerprint="standard_chartered_csv_v2",
        mapping_label="Standard Chartered Bank CSV",
        date_column="Transaction Date",
        narration_column="Narration",
        debit_column="Withdrawal",
        credit_column="Deposit",
        balance_column="Balance",
        reference_column="Reference",
        date_format="%d/%m/%Y",
    ),
    # Bank of India — netbanking / statement CSV & XLSX (common layouts)
    frozenset({"value date", "transaction date", "particulars", "debit", "credit", "balance"}): ColumnMapping(
        mapping_id="",
        user_id="system",
        format_fingerprint="boi_csv_v1",
        mapping_label="Bank of India CSV/XLS",
        date_column="Value Date",
        narration_column="Particulars",
        debit_column="Debit",
        credit_column="Credit",
        balance_column="Balance",
        reference_column=None,
        date_format="%d/%m/%Y",
    ),
    frozenset({"transaction date", "particulars", "cheque no.", "debit", "credit", "balance"}): ColumnMapping(
        mapping_id="",
        user_id="system",
        format_fingerprint="boi_csv_v2",
        mapping_label="Bank of India CSV/XLS",
        date_column="Transaction Date",
        narration_column="Particulars",
        debit_column="Debit",
        credit_column="Credit",
        balance_column="Balance",
        reference_column="Cheque No.",
        date_format="%d/%m/%Y",
    ),
    frozenset({"date", "remarks", "debit", "credit", "balance"}): ColumnMapping(
        mapping_id="",
        user_id="system",
        format_fingerprint="boi_csv_v3",
        mapping_label="Bank of India CSV/XLS",
        date_column="Date",
        narration_column="Remarks",
        debit_column="Debit",
        credit_column="Credit",
        balance_column="Balance",
        reference_column=None,
        date_format="%d/%m/%Y",
    ),
    # Bank of India — branch / netbanking statement (observed BOI.csv / BOI.xlsx)
    frozenset({
        "txn date",
        "description",
        "cheque no",
        "withdrawal (in rs.)",
        "deposits (in rs.)",
        "balance (in rs.)",
    }): ColumnMapping(
        mapping_id="",
        user_id="system",
        format_fingerprint="boi_csv_v4",
        mapping_label="Bank of India Statement CSV/XLS",
        date_column="Txn Date",
        narration_column="Description",
        debit_column="Withdrawal (in Rs.)",
        credit_column="Deposits (in Rs.)",
        balance_column="Balance (in Rs.)",
        reference_column="Cheque No",
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
    "baroda_csv_v1": SourceType.BARODA_BANK_CSV,
    "baroda_csv_v2": SourceType.BARODA_BANK_CSV,
    "canara_csv_v1": SourceType.CANARA_BANK_CSV,
    "canara_csv_v2": SourceType.CANARA_BANK_CSV,
    "canara_csv_v3": SourceType.CANARA_BANK_CSV,
    "standard_chartered_csv_v0": SourceType.STANDARD_CHARTERED_BANK_CSV,
    "standard_chartered_csv_v1": SourceType.STANDARD_CHARTERED_BANK_CSV,
    "standard_chartered_csv_v2": SourceType.STANDARD_CHARTERED_BANK_CSV,
    "boi_csv_v1": SourceType.BOI_BANK_CSV,
    "boi_csv_v2": SourceType.BOI_BANK_CSV,
    "boi_csv_v3": SourceType.BOI_BANK_CSV,
    "boi_csv_v4": SourceType.BOI_BANK_CSV,
}

_UPI_RE = re.compile(r"\bUPI\b", re.I)
_NEFT_RE = re.compile(r"\bNEFT\b", re.I)
_IMPS_RE = re.compile(r"\bIMPS\b", re.I)
_GENERIC_DATE_RE = re.compile(
    r"^\s*(\d{2}[/-]\d{2}[/-]\d{2,4}(\s+\d{2}:\d{2}:\d{2})?|\d{1,2}\s+[A-Za-z]{3}\s+\d{2,4}|\d{4}[-/]\d{2}[-/]\d{2}(\s+\d{2}:\d{2}(:\d{2})?(\.\d{1,6})?)?)\s*$"
)
_CR_DR_SUFFIX_RE = re.compile(r"\s*([CcDd][Rr])\s*$")
# Bank of Baroda statement-style Excel: narration cell ends with "txn_amt  balance_amtCr"
_BARODA_DETAILS_EMBEDDED_RE = re.compile(
    r"\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s*[Cc][Rr]\s*$",
    re.I,
)


def _baroda_embedded_amounts_from_details(details: str) -> tuple[str | None, str | None, str | None]:
    """If Details ends with two amounts (txn + running balance Cr), return (debit, credit, balance).

    Used when Debit/Credit cells are empty but amounts appear inside the Details column
    (common in merged-cell / statement PDF→Excel conversions).
    """
    s = details.strip()
    m = _BARODA_DETAILS_EMBEDDED_RE.search(s)
    if not m:
        return None, None, None
    amt, bal = m.group(1), m.group(2)
    prefix = s[: m.start()].strip()
    pu = prefix.upper()
    if pu.startswith("BY ") or " BY " in f" {pu} ":
        return None, amt, bal
    if pu.startswith("TO ") or " TO " in f" {pu} ":
        return amt, None, bal
    return None, amt, bal


def _baroda_strip_embedded_trailer(details: str) -> str:
    """Remove trailing txn + balance amounts from Details for cleaner narration."""
    s = details.strip()
    m = _BARODA_DETAILS_EMBEDDED_RE.search(s)
    if not m:
        return " ".join(s.split())
    return " ".join(s[: m.start()].split())


def _expand_baroda_v2_dataframe(df: "pd.DataFrame", mapping: ColumnMapping) -> "pd.DataFrame":
    """Split Baroda statement rows where Value Date / Balance contain newline-separated pairs.

    Some XLSX exports merge two transactions into one row (two dates, two balances,
    one debit and one credit amount in Debit/Credit columns).
    """
    import pandas as pd  # noqa: PLC0415

    if (mapping.format_fingerprint or "") != "baroda_csv_v2":
        return df
    date_col = mapping.date_column
    if not date_col or date_col not in df.columns:
        return df
    dr_col = mapping.debit_column
    cr_col = mapping.credit_column
    bal_col = mapping.balance_column
    narr_col = mapping.narration_column
    post_col = "Post Date" if "Post Date" in df.columns else None

    out_rows: list["pd.Series"] = []
    for _, row in df.iterrows():
        vd = str(row.get(date_col, "")).strip()
        if "\n" not in vd and "\r" not in vd:
            out_rows.append(row)
            continue
        vparts: list[str] = []
        for line in re.split(r"[\n\r]+", vd):
            line = line.strip()
            if line and _GENERIC_DATE_RE.match(line):
                vparts.append(line)
        if len(vparts) < 2:
            out_rows.append(row)
            continue

        post_parts: list[str] = []
        if post_col and post_col in row.index:
            ps = str(row.get(post_col, "")).strip()
            if ps and ps.lower() != "nan":
                for line in re.split(r"[\n\r]+", ps):
                    line = line.strip()
                    if line and _GENERIC_DATE_RE.match(line):
                        post_parts.append(line)

        bal_parts: list[str] = []
        if bal_col and bal_col in row.index:
            bs = str(row[bal_col]).strip()
            if bs and bs.lower() != "nan" and ("\n" in bs or "\r" in bs):
                bal_parts = [x.strip() for x in re.split(r"[\n\r]+", bs) if x.strip()]

        dr_s = str(row[dr_col]).strip() if dr_col and dr_col in row.index else ""
        cr_s = str(row[cr_col]).strip() if cr_col and cr_col in row.index else ""
        narr_s = str(row[narr_col]).strip() if narr_col and narr_col in row.index else ""
        narr_parts = [x.strip() for x in re.split(r"[\n\r]+", narr_s) if x.strip()] if narr_s else []

        n = len(vparts)
        if n != 2:
            out_rows.append(row)
            continue
        if "\n" in dr_s or "\r" in dr_s or "\n" in cr_s or "\r" in cr_s:
            out_rows.append(row)
            continue
        if not dr_s or dr_s.lower() == "nan" or not cr_s or cr_s.lower() == "nan":
            out_rows.append(row)
            continue
        if bal_parts and len(bal_parts) not in (0, 2):
            out_rows.append(row)
            continue

        for i in range(2):
            nr = row.copy()
            nr[date_col] = vparts[i]
            if post_col and post_col in nr.index:
                if post_parts and i < len(post_parts):
                    nr[post_col] = post_parts[i]
                elif post_parts and len(post_parts) == 1:
                    nr[post_col] = post_parts[0]
            if bal_col and bal_col in nr.index:
                if bal_parts and i < len(bal_parts):
                    nr[bal_col] = bal_parts[i]
                elif not bal_parts:
                    nr[bal_col] = ""
            if dr_col and dr_col in nr.index:
                nr[dr_col] = dr_s if i == 0 else ""
            if cr_col and cr_col in nr.index:
                nr[cr_col] = cr_s if i == 1 else ""
            if narr_col and narr_col in nr.index:
                if narr_parts and i < len(narr_parts):
                    nr[narr_col] = narr_parts[i]
                elif narr_parts:
                    nr[narr_col] = narr_parts[-1]
            out_rows.append(nr)

    if not out_rows:
        return df
    return pd.DataFrame(out_rows).reset_index(drop=True)


def _infer_txn_type(narration: str) -> TxnTypeHint:
    if _UPI_RE.search(narration):
        return TxnTypeHint.UPI
    if _NEFT_RE.search(narration):
        return TxnTypeHint.NEFT
    if _IMPS_RE.search(narration):
        return TxnTypeHint.IMPS
    return TxnTypeHint.UNKNOWN


def _clean_balance_text(raw: str | None) -> str | None:
    if not raw:
        return None
    out = _CR_DR_SUFFIX_RE.sub("", raw).strip()
    return out or None


def _is_numeric_amount(raw: str | None) -> bool:
    if not raw:
        return False
    cleaned = raw.replace(",", "").strip()
    if cleaned.startswith(("+", "-")):
        cleaned = cleaned[1:]
    if not cleaned:
        return False
    try:
        Decimal(cleaned)
        return True
    except InvalidOperation:
        return False


def fingerprint_headers(headers: list[str]) -> str:
    """SHA-256 of the sorted, lowercased, stripped header list."""
    key = "|".join(sorted(h.strip().lower() for h in headers))
    return hashlib.sha256(key.encode()).hexdigest()


def detect_column_mapping(headers: list[str]) -> ColumnMapping | None:
    """Return a known ColumnMapping if headers match a known format."""
    lower_headers = {_norm_header_key(h) for h in headers}
    best: ColumnMapping | None = None
    best_size = -1
    for signature, mapping in _KNOWN_HEADER_MAPPINGS.items():
        norm_signature = {_norm_header_key(s) for s in signature}
        if norm_signature.issubset(lower_headers):
            if len(signature) > best_size:
                best = mapping
                best_size = len(signature)
    return best


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
        last_valid_date: str | None = None

        df = _expand_baroda_v2_dataframe(df.copy(), mapping)

        for row_num, (_, row) in enumerate(df.iterrows(), start=1):
            raw_date = str(row.get(mapping.date_column, "")).strip()
            raw_narr = str(row.get(mapping.narration_column, "")).strip()
            # Collapse embedded newlines (e.g. from multi-line XLSX cells) to spaces
            raw_narr = " ".join(raw_narr.split())
            narr_low = raw_narr.lower()

            if any(m in narr_low for m in ("brought forward", "carried forward", "page summary", "end of statement", "page no.")):
                continue
            if any(m in narr_low for m in ("total ", "bonus", "redeemed", "points", "adjustment", "opening", "closing balance")):
                continue

            if not raw_date or raw_date.lower() in ("nan", "") or not _GENERIC_DATE_RE.match(raw_date):
                # Standard Chartered statement CSV: some rows omit Date/Value Date
                # but still carry a valid transaction amount + balance.
                if (
                    (mapping.format_fingerprint or "").startswith("standard_chartered_csv_")
                    and last_valid_date
                ):
                    tmp_debit = None
                    tmp_credit = None
                    if mapping.debit_column and mapping.debit_column in row.index:
                        val = str(row[mapping.debit_column]).strip()
                        cleaned = _clean_balance_text(val)
                        tmp_debit_val = (
                            cleaned if cleaned and cleaned.lower() not in ("nan", "0", "0.0", "0.00") else None
                        )
                        tmp_debit = tmp_debit_val if _is_numeric_amount(tmp_debit_val) else None
                    if mapping.credit_column and mapping.credit_column in row.index:
                        val = str(row[mapping.credit_column]).strip()
                        cleaned = _clean_balance_text(val)
                        tmp_credit_val = (
                            cleaned if cleaned and cleaned.lower() not in ("nan", "0", "0.0", "0.00") else None
                        )
                        tmp_credit = tmp_credit_val if _is_numeric_amount(tmp_credit_val) else None
                    if tmp_debit or tmp_credit:
                        raw_date = last_valid_date
                    else:
                        # Continuation row: append narration to previous transaction row.
                        if rows and raw_narr and raw_narr.lower() not in ("code", "page no.", "page"):
                            rows[-1].raw_narration = f"{(rows[-1].raw_narration or '').strip()} {raw_narr}".strip()
                            continue
                        errors.append(f"Row {row_num}: missing date")
                        continue
                else:
                    # Continuation row: append narration to previous transaction row.
                    if rows and raw_narr and raw_narr.lower() not in ("code", "page no.", "page"):
                        rows[-1].raw_narration = f"{(rows[-1].raw_narration or '').strip()} {raw_narr}".strip()
                        continue
                    errors.append(f"Row {row_num}: missing date")
                    continue

            raw_debit: str | None = None
            raw_credit: str | None = None

            _ZERO_VALS = {"0", "0.0", "0.00"}

            if mapping.debit_column and mapping.debit_column in row.index:
                val = str(row[mapping.debit_column]).strip()
                cleaned = _clean_balance_text(val)
                raw_debit = (
                    cleaned if cleaned and cleaned.lower() not in ("nan", *_ZERO_VALS) else None
                )
                if raw_debit and not _is_numeric_amount(raw_debit):
                    raw_debit = None

            if mapping.credit_column and mapping.credit_column in row.index:
                val = str(row[mapping.credit_column]).strip()
                cleaned = _clean_balance_text(val)
                raw_credit = (
                    cleaned if cleaned and cleaned.lower() not in ("nan", *_ZERO_VALS) else None
                )
                if raw_credit and not _is_numeric_amount(raw_credit):
                    raw_credit = None

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
                raw_balance = _clean_balance_text(val) if val and val.lower() != "nan" else None

            raw_ref: str | None = None
            if mapping.reference_column and mapping.reference_column in row.index:
                val = str(row[mapping.reference_column]).strip()
                raw_ref = val if val and val.lower() != "nan" else None

            # Baroda statement CSV quirk: for some rows, the transaction amount
            # is shifted into "Chq.No." while "Debit"/"Credit" contains a running
            # balance (with Cr/Dr suffix) and the "Balance" cell is empty.
            # When we detect this, prefer the "Chq.No." numeric value.
            if (
                (mapping.format_fingerprint or "") in {"baroda_csv_v2", "baroda_csv_v1"}
                and raw_ref
                and raw_balance is None
                and (raw_debit or raw_credit)
            ):
                narr_upper = raw_narr.upper()
                # Heuristic: transaction amount in Chq.No is usually an integer-like value.
                ref_clean = raw_ref.replace(",", "").strip()
                if "." not in ref_clean:
                    try:
                        cand_num = Decimal(ref_clean)
                    except InvalidOperation:
                        cand_num = None
                    if cand_num is not None and cand_num != 0:
                        if narr_upper.startswith("TO") or " TO " in narr_upper:
                            raw_debit = raw_ref
                            raw_credit = None
                        elif narr_upper.startswith("BY") or " BY " in narr_upper:
                            raw_credit = raw_ref
                            raw_debit = None

            # ── Baroda statement CSV quirk ─────────────────────────────────────
            # In some exports, when the narration is "TO ..." or "BY ...",
            # the actual amount is placed under "Chq.No." while Debit/Credit are empty.
            # Recover amount from Chq.No. so we don't drop otherwise-valid transactions.
            if (
                not raw_debit
                and not raw_credit
                and (mapping.format_fingerprint or "") in {"baroda_csv_v2", "baroda_csv_v1"}
                and raw_ref
            ):
                narr_upper = raw_narr.upper()
                # Candidate must be numeric (can include commas).
                cand_clean = raw_ref.replace(",", "").strip()
                try:
                    cand_num = Decimal(cand_clean)
                except InvalidOperation:
                    cand_num = None
                if cand_num is not None and cand_num != 0:
                    used_as_amount = False
                    if narr_upper.startswith("TO " ) or narr_upper.startswith("TO"):
                        raw_debit = raw_ref
                        used_as_amount = True
                    elif narr_upper.startswith("BY ") or narr_upper.startswith("BY"):
                        raw_credit = raw_ref
                        used_as_amount = True
                    elif " INT " in f" {narr_upper} ":
                        # "INT ON SB" style is a credit for bank accounts.
                        raw_credit = raw_ref
                        used_as_amount = True

                    if used_as_amount:
                        raw_ref = None

            # Baroda statement XLSX / merged-cell exports: amounts only at end of Details text.
            if (
                not raw_debit
                and not raw_credit
                and (mapping.format_fingerprint or "") in {"baroda_csv_v2", "baroda_csv_v1"}
                and raw_narr
            ):
                ed, ec, eb = _baroda_embedded_amounts_from_details(raw_narr)
                if ed:
                    raw_debit = ed
                if ec:
                    raw_credit = ec
                if eb and not raw_balance:
                    raw_balance = eb
                if ed or ec:
                    raw_narr = _baroda_strip_embedded_trailer(raw_narr)

            has_amount = bool(raw_debit or raw_credit)
            if not has_amount:
                continue

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
            last_valid_date = raw_date

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

        # True CSV with optional preamble/footer/repeated headers.
        return GenericCsvParser._read_csv_with_preamble(file_bytes)

    @staticmethod
    def _read_csv_with_preamble(file_bytes: bytes) -> "pd.DataFrame":
        """Read CSV and auto-detect the transaction header row after preamble."""
        import pandas as pd

        for enc in ("utf-8", "latin-1"):
            try:
                df_raw = pd.read_csv(
                    io.BytesIO(file_bytes),
                    header=None,
                    dtype=str,
                    encoding=enc,
                    on_bad_lines="skip",
                    engine="python",
                )
                break
            except UnicodeDecodeError:
                continue
        else:
            return pd.read_csv(io.BytesIO(file_bytes), dtype=str)

        header_row_idx: int | None = None
        for idx, row in df_raw.iterrows():
            cells = [str(c).strip() for c in row if str(c).strip() not in ("", "nan")]
            cells_low = [c.lower() for c in cells]
            keyword_hits = sum(1 for c in cells_low if c in GenericCsvParser._XLS_HEADER_KEYWORDS)
            if keyword_hits >= 3 and any("date" in c for c in cells_low):
                header_row_idx = int(idx)
                break
            # Bank of Baroda two-line header:
            # row N: Value | Post | Details | Chq.No. | Debit | Credit | Balance
            # row N+1: Date  | Date
            if {"value", "post", "details", "debit", "credit", "balance"}.issubset(set(cells_low)):
                if idx + 1 < len(df_raw):
                    next_cells = [
                        str(c).strip().lower()
                        for c in df_raw.iloc[idx + 1].tolist()
                        if str(c).strip() not in ("", "nan")
                    ]
                    if "date" in next_cells:
                        header_row_idx = int(idx)
                        break

        if header_row_idx is None:
            for enc in ("utf-8", "latin-1"):
                try:
                    return pd.read_csv(io.BytesIO(file_bytes), dtype=str, encoding=enc)
                except UnicodeDecodeError:
                    continue
            return pd.read_csv(io.BytesIO(file_bytes), dtype=str)

        raw_cols = [str(v).strip() for v in df_raw.iloc[header_row_idx]]
        data_start = header_row_idx + 1
        # Merge Baroda two-line date header into Value Date / Post Date.
        if (
            header_row_idx + 1 < len(df_raw)
            and len(raw_cols) >= 2
            and raw_cols[0].strip().lower() == "value"
            and raw_cols[1].strip().lower() == "post"
        ):
            next_row = [str(v).strip() for v in df_raw.iloc[header_row_idx + 1]]
            if len(next_row) >= 2 and next_row[0].strip().lower() == "date" and next_row[1].strip().lower() == "date":
                raw_cols[0] = "Value Date"
                raw_cols[1] = "Post Date"
                data_start = header_row_idx + 2
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

        df = df_raw.iloc[data_start:].copy()
        df.columns = columns
        df = df.reset_index(drop=True)

        narr_col = next(
            (c for c in df.columns if any(k in c.lower() for k in ("description", "details", "narration", "particular"))),
            None,
        )
        if narr_col and narr_col in df.columns:
            narr_series = df[narr_col].astype(str).str.strip().str.lower()
            stop_mask = narr_series.apply(
                lambda s: any(m in str(s) for m in GenericCsvParser._CSV_STOP_MARKERS)
            )
            if stop_mask.any():
                # Multi-page exports include "Page Summary"/footer between pages.
                # Truncating at the first occurrence would drop later transactions.
                # Instead, drop stop-markers only when the date cell is empty.
                date_col = next((c for c in df.columns if "date" in c.lower()), None)
                if date_col:
                    date_empty = (
                        df[date_col].fillna("").astype(str).str.strip().isin(("", "nan"))
                    )
                    df = df[~(stop_mask & date_empty)]

        # Remove repeated header-like rows that appear at page boundaries.
        if "Txn Date" in df.columns:
            mask = df["Txn Date"].astype(str).str.strip().str.lower().isin({"txn date", "value", "date", "nan", ""})
            df = df[~mask]
        if "Value Date" in df.columns:
            mask = df["Value Date"].astype(str).str.strip().str.lower().isin({"value date", "date", "nan"})
            df = df[~mask]

        for col in df.columns:
            df[col] = df[col].apply(_normalise_xls_cell)
        return df.reset_index(drop=True)

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
        # Baroda / Canara / Bank of India statement-style CSV exports
        "post date", "chq.no.", "cheque no.", "branch code", "particulars",
        # Standard Chartered variants
        "cheque number", "withdrawal", "deposit", "reference no.",
        # Bank of India account statement CSV (branch export)
        "sl no", "cheque no", "withdrawal (in rs.)", "deposits (in rs.)", "balance (in rs.)",
    })

    _CSV_STOP_MARKERS: tuple[str, ...] = (
        "page summary",
        "disclaimer",
        "end of statement",
        "this is system generated statement",
        "in case your account is operated",
        "toll free no",
    )

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
        raw_cols = [str(v).replace("\n", " ").strip() for v in df_raw.iloc[header_row_idx]]
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

        data_start = header_row_idx + 1
        # Bank of Baroda statement-style Excel may carry split header:
        # row N: Value | Post | Details | Chq.No. | Debit | Credit | Balance
        # row N+1: Date  | Date
        if (
            header_row_idx + 1 < len(df_raw)
            and len(raw_cols) >= 2
            and raw_cols[0].strip().lower() == "value"
            and raw_cols[1].strip().lower() == "post"
        ):
            next_row = [str(v).replace("\n", " ").strip() for v in df_raw.iloc[header_row_idx + 1]]
            if len(next_row) >= 2 and next_row[0].strip().lower() == "date" and next_row[1].strip().lower() == "date":
                raw_cols[0] = "Value Date"
                raw_cols[1] = "Post Date"
                # rebuild columns because raw_cols changed
                seen = {}
                columns = []
                for i, c in enumerate(raw_cols):
                    if not c or c.lower() == "nan":
                        c = f"_col{i}"
                    if c in seen:
                        seen[c] += 1
                        c = f"{c}_{seen[c]}"
                    else:
                        seen[c] = 0
                    columns.append(c)
                data_start = header_row_idx + 2

        if hdfc_style:
            # HDFC has a "***" separator row right after the header
            data_start = max(data_start, header_row_idx + 2)

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
            series = df[date_col].astype(str).str.strip()
            # Multi-line cells (e.g. Baroda XLSX with two Value Dates in one merged cell):
            # validate using the first line only so the row is not dropped before expansion.
            first_line = series.apply(
                lambda s: (re.split(r"[\n\r]+", str(s).strip())[0].strip() if str(s).strip() else "")
            )
            date_mask = (
                # DD/MM/YYYY, DD-MM-YYYY, 1 Apr 2024, with optional time
                first_line.str.match(
                    r"^\d{1,2}[/\-.\s]\w{2,4}[/\-.\s]\d{2,4}(\s+\d{1,2}:\d{2}(:\d{2})?(\.\d{1,6})?)?\s*$",
                    na=False,
                    case=False,
                )
                |
                # ISO style date/datetime commonly produced by pandas XLSX reads
                first_line.str.match(
                    r"^\d{4}[-/]\d{2}[-/]\d{2}(?:\s+\d{2}:\d{2}(?::\d{2})?(?:\.\d{1,6})?)?\s*$",
                    na=False,
                    case=False,
                )
            )
            df = df[date_mask].reset_index(drop=True)
            # Strip time portion from datetime values for all date-like columns
            # e.g. "2019-06-16 00:00:00.000000" -> "2019-06-16"
            for col in [c for c in df.columns if "date" in c.lower()]:
                df[col] = (
                    df[col]
                    .astype(str)
                    .str.strip()
                    .str.replace(r"\s+\d{1,2}:\d{2}(:\d{2})?(\.\d{1,6})?\s*$", "", regex=True)
                    .str.strip()
                )

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
