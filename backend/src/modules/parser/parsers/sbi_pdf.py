"""SBI Bank PDF parser.

Parses State Bank of India account statement PDFs.

SBI statement format (old and new):
    Txn Date | Value Date | Description | Ref No./Cheque No. | Debit | Credit | Balance

Two format variants are handled by the same parser:
  - Old format (no password): pdfplumber table extraction gives clean 7-column rows.
  - New format (password-protected, decrypted before reaching this parser):
    same column structure, potentially with a different preamble before the table.

The primary extraction strategy is TABLE_EXTRACTION (pdfplumber), which gives
the cleanest results because cells may contain embedded newlines.  TEXT_LAYER
and OCR are retained as fallbacks.

Table cells may contain embedded \\n characters (e.g. "13 May\\n2025" for dates
or multi-line descriptions).  These are normalised in _rows_from_tables().
"""

from __future__ import annotations

import logging
import re
from decimal import Decimal, InvalidOperation

from core.models.enums import ExtractionMethod, SourceType, TxnTypeHint
from core.models.raw_parsed_row import ParseMetadata, RawParsedRow
from core.utils.confidence import ConfidenceSignals, compute_confidence, check_balance_cross_check
from modules.parser.base import BaseParser, ExtractionResult
from modules.parser.extraction.text_layer import TextLayerExtractor
from modules.parser.extraction.table_extract import TableExtractor
from modules.parser.extraction.ocr import OCRExtractor

logger = logging.getLogger(__name__)

_DATE_RE = re.compile(r"\b(\d{1,2}\s+\w{3}\s+\d{4}|\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4})\b")
_AMOUNT_RE = re.compile(r"[\d,]+\.\d{2}")

# SBI transaction row pattern (text-layer fallback).
# This matches the *anchor* line that starts a transaction in the text stream.
# Format: D Mon YYYY  D Mon YYYY  Description           Ref   [Debit]  [Credit]  Balance
# The regex is intentionally loose — downstream debit/credit logic resolves ambiguity.
_TXN_ROW_RE = re.compile(
    r"""
    ^(\d{1,2}\s+\w{3}\s+\d{4}|\d{2}/\d{2}/\d{4})   # Txn Date
    \s+
    (\d{1,2}\s+\w{3}\s+\d{4}|\d{2}/\d{2}/\d{4})     # Value Date
    \s+
    (.+?)                                              # Description
    \s+
    (\S*)                                              # Ref / Cheque (may be empty)
    \s+
    ([\d,]+\.\d{2})?                                   # Debit (optional)
    \s*
    ([\d,]+\.\d{2})?                                   # Credit (optional)
    \s+
    ([\d,]+\.\d{2})                                    # Balance (required)
    """,
    re.VERBOSE | re.MULTILINE,
)

# Transaction-type inference regexes
_UPI_RE = re.compile(r"\bUPI\b|\bPHONEPE\b|\bGPAY\b|\bPAYTM\b", re.I)
_NEFT_RE = re.compile(r"\bNEFT\b", re.I)
_IMPS_RE = re.compile(r"\bIMPS\b", re.I)
_ATM_RE = re.compile(r"\bATM\b|\bCASH WD\b", re.I)


def _clean_amount(raw: str | None) -> Decimal | None:
    if not raw:
        return None
    cleaned = raw.replace(",", "").strip()
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _infer_txn_type(narration: str) -> TxnTypeHint:
    if _UPI_RE.search(narration):
        return TxnTypeHint.UPI
    if _NEFT_RE.search(narration):
        return TxnTypeHint.NEFT
    if _IMPS_RE.search(narration):
        return TxnTypeHint.IMPS
    if _ATM_RE.search(narration):
        return TxnTypeHint.ATM_WITHDRAWAL
    return TxnTypeHint.UNKNOWN


def _normalise_cell(value: str | None) -> str:
    """Normalise a pdfplumber table cell: replace embedded newlines with spaces."""
    if not value:
        return ""
    return " ".join(value.split())


class SbiPdfParser(BaseParser):
    """Parses SBI Bank PDF account statements (old and new format)."""

    source_type = SourceType.SBI_BANK
    version = "1.2"
    supported_formats = ["PDF"]

    def __init__(self) -> None:
        self._text_extractor = TextLayerExtractor()
        self._table_extractor = TableExtractor()
        self._ocr_extractor = OCRExtractor()

    def supported_methods(self) -> list[ExtractionMethod]:
        return [
            ExtractionMethod.TEXT_LAYER,
            ExtractionMethod.TABLE_EXTRACTION,
            ExtractionMethod.OCR,
        ]

    def extract(
        self,
        batch_id: str,
        file_bytes: bytes,
        method: ExtractionMethod,
    ) -> ExtractionResult:
        try:
            if method == ExtractionMethod.TEXT_LAYER:
                pages = self._text_extractor.extract_pages(file_bytes)
                combined = "\n".join(pages)
                if not combined.strip():
                    return self._make_failed_result(batch_id, method, "No text in PDF.")
                return self.parse_text_content(batch_id, combined, method)

            if method == ExtractionMethod.TABLE_EXTRACTION:
                tables = self._table_extractor.extract_tables(file_bytes)
                if not tables:
                    return self._make_failed_result(batch_id, method, "No tables found.")
                rows = self._rows_from_tables(batch_id, tables)
                return self._build_result(batch_id, rows, method)

            if method == ExtractionMethod.OCR:
                combined = self._ocr_extractor.extract_combined(file_bytes)
                if not combined.strip():
                    return self._make_failed_result(batch_id, method, "OCR produced no text.")
                return self.parse_text_content(batch_id, combined, method)

        except Exception as exc:  # noqa: BLE001
            logger.warning("SbiPdfParser.extract(%s) failed: %s", method.value, exc, exc_info=True)

        return self._make_failed_result(batch_id, method, f"Method {method.value} failed.")

    def parse_text_content(
        self,
        batch_id: str,
        text: str,
        method: ExtractionMethod = ExtractionMethod.TEXT_LAYER,
    ) -> ExtractionResult:
        """Parse SBI statement text. Pure function — unit-testable without PDF bytes."""
        rows: list[RawParsedRow] = []
        errors: list[str] = []

        for row_num, match in enumerate(_TXN_ROW_RE.finditer(text), start=1):
            txn_date = match.group(1).strip()
            narration = match.group(3).strip()
            ref_no = match.group(4).strip()
            raw_debit = match.group(5)
            raw_credit = match.group(6)
            raw_balance = match.group(7)

            has_amount = bool(raw_debit or raw_credit)
            if not has_amount:
                errors.append(f"Row {row_num}: no debit or credit amount")

            rows.append(
                RawParsedRow(
                    batch_id=batch_id,
                    source_type=SourceType.SBI_BANK,
                    parser_version=self.version,
                    extraction_method=method,
                    raw_date=txn_date,
                    raw_narration=narration,
                    raw_debit=raw_debit,
                    raw_credit=raw_credit,
                    raw_balance=raw_balance,
                    raw_reference=ref_no or None,
                    txn_type_hint=_infer_txn_type(narration),
                    row_confidence=0.9 if has_amount else 0.5,
                    row_number=row_num,
                )
            )

        return self._build_result(batch_id, rows, method, errors)

    def _build_result(
        self,
        batch_id: str,
        rows: list[RawParsedRow],
        method: ExtractionMethod,
        errors: list[str] | None = None,
    ) -> ExtractionResult:
        errors = errors or []

        # Attempt balance cross-check using consecutive running balances
        balance_ok: bool | None = None
        if rows and any(r.raw_balance for r in rows):
            try:
                balance_ok = check_balance_cross_check(
                    [(r.raw_debit, r.raw_credit, r.raw_balance) for r in rows]
                )
            except Exception:  # noqa: BLE001
                balance_ok = None

        signals = ConfidenceSignals(
            balance_cross_check_passed=bool(balance_ok),
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

    @staticmethod
    def _rows_from_tables(batch_id: str, tables: list[list[list[str]]]) -> list[RawParsedRow]:
        """Convert pdfplumber tables to RawParsedRow list.

        Each page of an SBI PDF produces one table.  The first row of each table
        is the column header (repeated on every page and therefore skipped).
        Cells may contain embedded \\n characters — these are normalised to spaces.
        """
        rows: list[RawParsedRow] = []
        row_num = 0

        for table in tables:
            if not table:
                continue

            # Normalise header column names (embedded \\n → space, strip, lowercase)
            header = [_normalise_cell(c).lower() for c in table[0]]

            # SBI new-format PDFs: pdfplumber may not parse column headers properly —
            # the header row comes through as ['', '', '', '', '', '', 'balance'] because
            # the PDF visual header uses a merged/rotated cell.  Detect this "positional"
            # table: ≥7 columns, at most 1 non-empty header, and that header is "balance".
            # Apply the known SBI 7-column layout (Date|ValDate|Narr|Ref|Debit|Credit|Bal).
            non_empty = [h for h in header if h]
            is_positional = (
                len(header) >= 7
                and len(non_empty) <= 1
                and any("balance" in h for h in non_empty)
            )

            if is_positional:
                date_col = 0
                narr_col = 2
                ref_col  = 3
                dr_col   = 4
                cr_col   = 5
                bal_col  = len(header) - 1  # last column is always balance
            else:
                # Named-column lookup (old format or any future format with proper headers)
                try:
                    date_col = next(
                        i for i, h in enumerate(header)
                        if ("txn" in h and "date" in h) or h == "date"
                    )
                    narr_col = next(
                        i for i, h in enumerate(header)
                        if "desc" in h or "narr" in h or "detail" in h
                    )
                except StopIteration:
                    continue  # not a transaction table

                dr_col = next(
                    (i for i, h in enumerate(header) if h in ("debit", "dr") or ("debit" in h and "credit" not in h)),
                    None,
                )
                cr_col = next(
                    (i for i, h in enumerate(header) if h in ("credit", "cr") or ("credit" in h and "debit" not in h)),
                    None,
                )
                bal_col = next(
                    (i for i, h in enumerate(header) if "balance" in h),
                    None,
                )
                ref_col = next(
                    (i for i, h in enumerate(header) if "ref" in h or "cheque" in h or "chq" in h),
                    None,
                )

            for row in table[1:]:
                if len(row) <= date_col:
                    continue
                raw_date = _normalise_cell(row[date_col])
                if not raw_date or not _DATE_RE.search(raw_date):
                    continue  # skip header repeat rows and empty rows

                row_num += 1
                raw_narr = _normalise_cell(row[narr_col]) if narr_col < len(row) else ""
                raw_debit = _normalise_cell(row[dr_col]) if dr_col is not None and dr_col < len(row) else ""
                raw_credit = _normalise_cell(row[cr_col]) if cr_col is not None and cr_col < len(row) else ""
                # New SBI format uses "-" as a placeholder for absent debit/credit — treat as empty
                raw_debit  = None if raw_debit  in ("", "-") else raw_debit
                raw_credit = None if raw_credit in ("", "-") else raw_credit
                raw_balance = _normalise_cell(row[bal_col]) if bal_col is not None and bal_col < len(row) else ""
                raw_ref = _normalise_cell(row[ref_col]) if ref_col is not None and ref_col < len(row) else ""

                rows.append(
                    RawParsedRow(
                        batch_id=batch_id,
                        source_type=SourceType.SBI_BANK,
                        parser_version="1.2",
                        extraction_method=ExtractionMethod.TABLE_EXTRACTION,
                        raw_date=raw_date,
                        raw_narration=raw_narr,
                        raw_debit=raw_debit,
                        raw_credit=raw_credit,
                        raw_balance=raw_balance or None,
                        raw_reference=raw_ref or None,
                        txn_type_hint=_infer_txn_type(raw_narr),
                        row_confidence=0.95 if (raw_debit or raw_credit) else 0.5,
                        row_number=row_num,
                    )
                )

        return rows

