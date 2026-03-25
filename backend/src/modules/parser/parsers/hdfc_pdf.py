"""HDFC Bank PDF parser.

Parses digitally-generated HDFC Bank account statement PDFs.

HDFC statement format (text layer):
    Date | Narration | Chq/Ref No. | Value Dt | Withdrawal Amt (Dr) | Deposit Amt (Cr) | Closing Balance

Design:
    - `extract()` dispatches to the right sub-method based on ExtractionMethod.
    - `parse_text_content()` is a *pure function* (no I/O) so it can be unit-tested
      directly with fixture strings without needing real PDF bytes.
"""

from __future__ import annotations

import logging
import re
from decimal import Decimal, InvalidOperation

from core.models.enums import ExtractionMethod, SourceType, TxnTypeHint
from core.models.raw_parsed_row import ParseMetadata, RawParsedRow
from core.utils.confidence import (
    ConfidenceSignals,
    compute_confidence,
    check_balance_cross_check,
)
from modules.parser.base import BaseParser, ExtractionResult
from modules.parser.extraction.text_layer import TextLayerExtractor
from modules.parser.extraction.table_extract import TableExtractor
from modules.parser.extraction.ocr import OCRExtractor

logger = logging.getLogger(__name__)

# ── HDFC-specific text parsing patterns ───────────────────────────────────────

# Date: DD/MM/YYYY or DD/MM/YY
_DATE_RE = re.compile(r"\b(\d{2}/\d{2}/(?:\d{4}|\d{2}))\b")

# Amount: 1,23,456.78  or  456.78  (Indian lakh format)
_AMOUNT_RE = re.compile(r"[\d,]+\.\d{2}")

# Opening/Closing balance line (HDFC includes them as special rows)
_OPENING_BALANCE_RE = re.compile(
    r"Opening\s+Balance\s+([\d,]+\.\d{2})", re.I
)
_CLOSING_BALANCE_RE = re.compile(
    r"Closing\s+Balance\s+([\d,]+\.\d{2})", re.I
)

# Transaction row: Date ... Value_Date ... [Withdrawal] ... [Deposit] ... Balance
# The key insight is two dates at positions[0] and [1], then optional amounts
_TXN_ROW_RE = re.compile(
    r"""
    ^\s*(\d{2}/\d{2}/(?:\d{4}|\d{2}))   # Group 1: Transaction date
    \s+
    (.+?)                   # Group 2: Narration (non-greedy)
    \s+
    (\S*)                   # Group 3: Chq / Ref No (may be empty string)
    \s+
    (\d{2}/\d{2}/(?:\d{4}|\d{2}))    # Group 4: Value date
    \s+
    ([\d,]+\.\d{2})?        # Group 5: Withdrawal (optional)
    \s*
    ([\d,]+\.\d{2})?        # Group 6: Deposit (optional)
    \s+
    ([\d,]+\.\d{2})         # Group 7: Closing balance (required)
    \s*$
    """,
    re.VERBOSE | re.MULTILINE,
)

# UPI / NEFT / IMPS / Cheque narration hints
_UPI_RE = re.compile(r"\bUPI\b", re.I)
_NEFT_RE = re.compile(r"\bNEFT\b", re.I)
_IMPS_RE = re.compile(r"\bIMPS\b", re.I)
_ATM_RE = re.compile(r"\bATM\b", re.I)
_CHQ_RE = re.compile(r"\b(CHQ|CHEQUE|CLG)\b", re.I)


def _clean_amount(raw: str) -> Decimal | None:
    """Convert '1,23,456.78' → Decimal('123456.78')."""
    try:
        return Decimal(raw.replace(",", ""))
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
    if _CHQ_RE.search(narration):
        return TxnTypeHint.CHEQUE
    return TxnTypeHint.UNKNOWN


class HdfcPdfParser(BaseParser):
    """Parses HDFC Bank PDF account statements.

    Extraction order (as per SM-C §4):
        1. TEXT_LAYER  — fastest, works on digitally generated PDFs
        2. TABLE_EXTRACTION — Camelot / pdfplumber stream mode
        3. OCR — slowest, for printed/scanned statements
    """

    source_type = SourceType.HDFC_BANK
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
        """Dispatch to the appropriate extraction sub-method."""
        try:
            if method == ExtractionMethod.TEXT_LAYER:
                return self._extract_text_layer(batch_id, file_bytes)
            if method == ExtractionMethod.TABLE_EXTRACTION:
                return self._extract_table(batch_id, file_bytes)
            if method == ExtractionMethod.OCR:
                return self._extract_ocr(batch_id, file_bytes)
        except Exception as exc:  # noqa: BLE001
            logger.warning("HdfcPdfParser.extract(%s) failed: %s", method.value, exc, exc_info=True)
        return self._make_failed_result(batch_id, method, f"Extraction method {method.value} failed.")

    # ── Sub-extraction methods ────────────────────────────────────────────────

    def _extract_text_layer(self, batch_id: str, file_bytes: bytes) -> ExtractionResult:
        pages = self._text_extractor.extract_pages(file_bytes)
        combined = "\n".join(pages)
        if not combined.strip():
            return self._make_failed_result(batch_id, ExtractionMethod.TEXT_LAYER, "No text in PDF.")
        return self.parse_text_content(batch_id, combined, ExtractionMethod.TEXT_LAYER)

    def _extract_table(self, batch_id: str, file_bytes: bytes) -> ExtractionResult:
        tables = self._table_extractor.extract_tables(file_bytes, method="auto")
        if not tables:
            return self._make_failed_result(batch_id, ExtractionMethod.TABLE_EXTRACTION, "No tables found.")
        rows, opening, closing = self._rows_from_tables(batch_id, tables)
        return self._build_result(batch_id, rows, opening, closing, ExtractionMethod.TABLE_EXTRACTION)

    def _extract_ocr(self, batch_id: str, file_bytes: bytes) -> ExtractionResult:
        combined = self._ocr_extractor.extract_combined(file_bytes)
        if not combined.strip():
            return self._make_failed_result(batch_id, ExtractionMethod.OCR, "OCR produced no text.")
        return self.parse_text_content(batch_id, combined, ExtractionMethod.OCR)

    # ── Core parsing logic (pure — testable without file I/O) ─────────────────

    def parse_text_content(
        self,
        batch_id: str,
        text: str,
        method: ExtractionMethod = ExtractionMethod.TEXT_LAYER,
    ) -> ExtractionResult:
        """Parse extracted text into RawParsedRow objects.

        This is the primary unit-testable function — pass any string and
        it will attempt to extract HDFC transaction rows from it.

        Args:
            batch_id: Parent batch identifier.
            text: Full multi-page text content from the PDF.
            method: Which extraction method produced this text.

        Returns:
            ExtractionResult with rows and computed confidence.
        """
        rows: list[RawParsedRow] = []
        errors: list[str] = []
        opening: Decimal | None = None
        closing: Decimal | None = None
        debits: list[Decimal] = []
        credits: list[Decimal] = []

        # Extract opening/closing balance
        m_open = _OPENING_BALANCE_RE.search(text)
        if m_open:
            opening = _clean_amount(m_open.group(1))

        m_close = _CLOSING_BALANCE_RE.search(text)
        if m_close:
            closing = _clean_amount(m_close.group(1))

        # Extract transaction rows
        for row_num, match in enumerate(_TXN_ROW_RE.finditer(text), start=1):
            txn_date = match.group(1)
            # Expand DD/MM/YY to DD/MM/YYYY
            if len(txn_date) == 8:
                parts = txn_date.split("/")
                txn_date = f"{parts[0]}/{parts[1]}/20{parts[2]}"
                
            narration = match.group(2).strip()
            ref_no = match.group(3).strip()
            value_date = match.group(4)
            raw_debit = match.group(5)      # May be None
            raw_credit = match.group(6)     # May be None
            raw_balance = match.group(7)

            # HDFC text layer: when only one amount is captured, the regex assigns it
            # to Group 5 (withdrawal) regardless of direction.  Re-classify as a
            # credit when the narration contains the HDFC credit indicator " CR".
            # Examples: "NEFT CR/SALARY/...", "SALARY CR/...", "INTEREST CR/..."
            if raw_debit and not raw_credit and re.search(r"\bCR\b", narration, re.I):
                raw_credit = raw_debit
                raw_debit = None

            has_amount = bool(raw_debit or raw_credit)
            if not has_amount:
                errors.append(f"Row {row_num}: no debit or credit amount")
            else:
                if raw_debit:
                    d = _clean_amount(raw_debit)
                    if d:
                        debits.append(d)
                if raw_credit:
                    c = _clean_amount(raw_credit)
                    if c:
                        credits.append(c)

            rows.append(
                RawParsedRow(
                    batch_id=batch_id,
                    source_type=SourceType.HDFC_BANK,
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

        return self._build_result(batch_id, rows, opening, closing, method, errors)

    def _build_result(
        self,
        batch_id: str,
        rows: list[RawParsedRow],
        opening: Decimal | None,
        closing: Decimal | None,
        method: ExtractionMethod,
        errors: list[str] | None = None,
    ) -> ExtractionResult:
        errors = errors or []
        signals = ConfidenceSignals(
            balance_cross_check_passed=check_balance_cross_check(
                opening,
                closing,
                [_clean_amount(r.raw_debit) for r in rows if r.raw_debit and _clean_amount(r.raw_debit)],
                [_clean_amount(r.raw_credit) for r in rows if r.raw_credit and _clean_amount(r.raw_credit)],
            ),
            all_rows_have_valid_date=bool(rows) and all(bool(r.raw_date.strip()) for r in rows),
            all_rows_have_amount=bool(rows) and all(r.raw_debit or r.raw_credit for r in rows),
            row_count_positive=len(rows) > 0,
            no_row_parse_errors=len(errors) == 0,
        )
        confidence = compute_confidence(signals)

        # Determine statement period
        dates = [r.raw_date for r in rows if r.raw_date]
        meta = ParseMetadata(
            statement_from=dates[0] if dates else None,
            statement_to=dates[-1] if dates else None,
            total_rows_found=len(rows),
            rows_with_errors=len(errors),
            opening_balance=opening,
            closing_balance=closing,
            balance_cross_check_passed=signals.balance_cross_check_passed,
            overall_confidence=confidence,
            warnings=errors,
            extraction_method=method,
            parser_version=self.version,
        )
        return ExtractionResult(rows=rows, metadata=meta, method=method, confidence=confidence)

    @staticmethod
    def _rows_from_tables(
        batch_id: str,
        tables: list[list[list[str]]],
    ) -> tuple[list[RawParsedRow], Decimal | None, Decimal | None]:
        """Convert pdfplumber / Camelot table output into RawParsedRow objects."""
        rows: list[RawParsedRow] = []
        opening: Decimal | None = None
        closing: Decimal | None = None

        for table in tables:
            if not table:
                continue
            # Find header row
            header = [c.strip().lower() for c in table[0]]
            try:
                date_col = next(i for i, h in enumerate(header) if "date" in h and "value" not in h)
                narr_col = next(i for i, h in enumerate(header) if "narr" in h or "desc" in h or "details" in h)
                dr_col = next((i for i, h in enumerate(header) if "withdraw" in h or "dr" in h or "debit" in h), None)
                cr_col = next((i for i, h in enumerate(header) if "deposit" in h or "cr" in h or "credit" in h), None)
                bal_col = next((i for i, h in enumerate(header) if "balance" in h or "bal" in h), None)
            except StopIteration:
                continue  # Unrecognized table layout — skip

            for row_num, row in enumerate(table[1:], start=1):
                max_col = max([c for c in [date_col, narr_col, dr_col, cr_col, bal_col] if c is not None])
                if len(row) <= max_col:
                    continue
                raw_date = row[date_col].strip() if date_col < len(row) else ""
                if not _DATE_RE.match(raw_date):
                    continue  # Skip non-transaction rows (headers / totals)
                raw_narr = row[narr_col].strip() if narr_col < len(row) else ""
                raw_dr = row[dr_col].strip() if dr_col is not None and dr_col < len(row) else None
                raw_cr = row[cr_col].strip() if cr_col is not None and cr_col < len(row) else None
                raw_bal = row[bal_col].strip() if bal_col is not None and bal_col < len(row) else None

                rows.append(
                    RawParsedRow(
                        batch_id=batch_id,
                        source_type=SourceType.HDFC_BANK,
                        parser_version="1.2",
                        extraction_method=ExtractionMethod.TABLE_EXTRACTION,
                        raw_date=raw_date,
                        raw_narration=raw_narr,
                        raw_debit=raw_dr or None,
                        raw_credit=raw_cr or None,
                        raw_balance=raw_bal or None,
                        txn_type_hint=_infer_txn_type(raw_narr),
                        row_number=row_num,
                    )
                )

        return rows, opening, closing
