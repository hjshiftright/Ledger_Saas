"""Union Bank of India PDF parser.

Parses digitally-generated Union Bank of India account statement PDFs.

Union Bank statement format (text layer):
    Date | Particulars | Chq/Ref No. | Debit | Credit | Balance

Date formats seen in the wild:
    DD/MM/YYYY  (most common)
    DD-MM-YYYY  (older statements)

Design:
    - `extract()` dispatches to the right sub-method based on ExtractionMethod.
    - `parse_text_content()` is a *pure function* (no I/O) so it can be
      unit-tested directly with fixture strings without needing real PDF bytes.
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

# ── Union Bank-specific text parsing patterns ─────────────────────────────────

# Date: DD/MM/YYYY  or  DD-MM-YYYY
_DATE_RE = re.compile(r"\b(\d{2}[/-]\d{2}[/-]\d{4})\b")

# Amount: 1,23,456.78  or  456.78  (Indian lakh / no-comma formats)
_AMOUNT_RE = re.compile(r"[\d,]+\.\d{2}")

# Opening / Closing balance marker lines (text layer)
_OPENING_BALANCE_RE = re.compile(
    r"Opening\s+Balance[:\s]+([\d,]+\.\d{2})", re.I
)
_CLOSING_BALANCE_RE = re.compile(
    r"Closing\s+Balance[:\s]+([\d,]+\.\d{2})", re.I
)

# Summary row cell patterns (table extraction — monthly statement)
_OPENING_CELL_RE = re.compile(r"[Oo]pening\s+[Bb]alance", re.I)
_CLOSING_CELL_RE = re.compile(r"[Cc]losing\s+[Bb]alance", re.I)
# Strip trailing Cr/Dr marker from a balance string
_CR_DR_SUFFIX_RE = re.compile(r"\s+[CcDd][Rr]\s*$")

# Transaction row:
#   DD/MM/YYYY  Particulars  [Chq/Ref]  [Debit]  [Credit]  Balance
#
# Union Bank PDFs have 5 columns after the date:
#   Particulars | Chq-Ref | Debit | Credit | Balance
# The Chq/Ref field may be blank.  Debit and Credit are mutually exclusive
# per row (one is always blank).
_TXN_ROW_RE = re.compile(
    r"""
    ^(\d{2}[/-]\d{2}[/-]\d{4})   # Group 1: Date  DD/MM/YYYY or DD-MM-YYYY
    \s+
    (.+?)                          # Group 2: Particulars (non-greedy)
    \s+
    (\S*)                          # Group 3: Cheque / Ref No. (may be blank)
    \s+
    ([\d,]+\.\d{2})?               # Group 4: Debit (optional)
    \s*
    ([\d,]+\.\d{2})?               # Group 5: Credit (optional)
    \s+
    ([\d,]+\.\d{2})                # Group 6: Balance (required)
    """,
    re.VERBOSE | re.MULTILINE,
)

_UPI_RE  = re.compile(r"\bUPI\b", re.I)
_NEFT_RE = re.compile(r"\bNEFT\b", re.I)
_IMPS_RE = re.compile(r"\bIMPS\b", re.I)
_ATM_RE  = re.compile(r"\bATM\b|\bCASH\s+WD\b|\bCASH\s+WITHDRAWAL\b", re.I)
_CHQ_RE  = re.compile(r"\b(CHQ|CHEQUE|CLG|CLR)\b", re.I)


def _clean_amount(raw: str | None) -> Decimal | None:
    """Convert '1,23,456.78'  →  Decimal('123456.78')."""
    if not raw:
        return None
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


class UnionBankPdfParser(BaseParser):
    """Parses Union Bank of India PDF account statements.

    Extraction order (as per SM-C §4):
        1. TEXT_LAYER       — fastest, works on digitally generated PDFs
        2. TABLE_EXTRACTION — pdfplumber stream mode
        3. OCR              — slowest, for printed/scanned statements
    """

    source_type = SourceType.UNION_BANK
    version = "1.0"
    supported_formats = ["PDF"]

    def __init__(self) -> None:
        self._text_extractor  = TextLayerExtractor()
        self._table_extractor = TableExtractor()
        self._ocr_extractor   = OCRExtractor()

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
            logger.warning(
                "UnionBankPdfParser.extract(%s) failed: %s", method.value, exc, exc_info=True
            )
        return self._make_failed_result(
            batch_id, method, f"Extraction method {method.value} failed."
        )

    # ── Sub-extraction methods ────────────────────────────────────────────────

    def _extract_text_layer(self, batch_id: str, file_bytes: bytes) -> ExtractionResult:
        pages    = self._text_extractor.extract_pages(file_bytes)
        combined = "\n".join(pages)
        if not combined.strip():
            return self._make_failed_result(
                batch_id, ExtractionMethod.TEXT_LAYER, "No text in PDF."
            )
        return self.parse_text_content(batch_id, combined, ExtractionMethod.TEXT_LAYER)

    def _extract_table(self, batch_id: str, file_bytes: bytes) -> ExtractionResult:
        tables = self._table_extractor.extract_tables(file_bytes, method="auto")
        if not tables:
            return self._make_failed_result(
                batch_id, ExtractionMethod.TABLE_EXTRACTION, "No tables found."
            )
        rows, opening, closing = self._rows_from_tables(batch_id, tables)
        return self._build_result(batch_id, rows, opening, closing, ExtractionMethod.TABLE_EXTRACTION)

    def _extract_ocr(self, batch_id: str, file_bytes: bytes) -> ExtractionResult:
        combined = self._ocr_extractor.extract_combined(file_bytes)
        if not combined.strip():
            return self._make_failed_result(
                batch_id, ExtractionMethod.OCR, "OCR produced no text."
            )
        return self.parse_text_content(batch_id, combined, ExtractionMethod.OCR)

    # ── Core parsing logic (pure — testable without file I/O) ─────────────────

    def parse_text_content(
        self,
        batch_id: str,
        text: str,
        method: ExtractionMethod = ExtractionMethod.TEXT_LAYER,
    ) -> ExtractionResult:
        """Parse extracted text into RawParsedRow objects.

        Pure function — pass any string and it will attempt to extract
        Union Bank transaction rows from it.

        Args:
            batch_id: Parent batch identifier.
            text:     Full multi-page text content from the PDF.
            method:   Which extraction method produced this text.

        Returns:
            ExtractionResult with rows and computed confidence.
        """
        rows: list[RawParsedRow] = []
        errors: list[str] = []
        opening: Decimal | None = None
        closing: Decimal | None = None
        debits:  list[Decimal] = []
        credits: list[Decimal] = []

        m_open = _OPENING_BALANCE_RE.search(text)
        if m_open:
            opening = _clean_amount(m_open.group(1))

        m_close = _CLOSING_BALANCE_RE.search(text)
        if m_close:
            closing = _clean_amount(m_close.group(1))

        for row_num, match in enumerate(_TXN_ROW_RE.finditer(text), start=1):
            txn_date   = match.group(1).replace("-", "/")   # normalise to DD/MM/YYYY
            narration  = match.group(2).strip()
            ref_no     = match.group(3).strip()
            raw_debit  = match.group(4)   # may be None
            raw_credit = match.group(5)   # may be None
            raw_balance = match.group(6)

            # When only one amount is captured it lands in group 4 (debit slot).
            # Reclassify as credit when the narration contains a credit indicator
            # such as NEFT CR, SALARY CR, INTEREST CR, etc.
            if raw_debit and not raw_credit and re.search(r"\bCR\b", narration, re.I):
                raw_credit = raw_debit
                raw_debit  = None

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
                    source_type=SourceType.UNION_BANK,
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

    # ── Result builder ────────────────────────────────────────────────────────

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
        debits  = [d for r in rows if r.raw_debit  for d in [_clean_amount(r.raw_debit)]  if d]
        credits = [c for r in rows if r.raw_credit for c in [_clean_amount(r.raw_credit)] if c]
        # Use None (not False) when opening/closing are absent — avoids penalising the
        # confidence weight for the balance check when the statement doesn't report them.
        balance_ok: bool | None = (
            check_balance_cross_check(opening, closing, debits, credits)
            if (opening and closing) else None
        )
        signals = ConfidenceSignals(
            balance_cross_check_passed=balance_ok,
            all_rows_have_valid_date=bool(rows) and all(
                bool(_DATE_RE.search(r.raw_date or "")) for r in rows
            ),
            all_rows_have_amount=bool(rows) and all(
                bool(r.raw_debit or r.raw_credit) for r in rows
            ),
            row_count_positive=len(rows) > 0,
            no_row_parse_errors=len(errors) == 0,
        )
        confidence = compute_confidence(signals)
        dates = [r.raw_date for r in rows if r.raw_date]
        meta  = ParseMetadata(
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

    # ── Table extraction helper ───────────────────────────────────────────────

    def _rows_from_tables(
        self,
        batch_id: str,
        tables: list[list[list[str]]],
    ) -> tuple[list[RawParsedRow], Decimal | None, Decimal | None]:
        rows: list[RawParsedRow] = []
        opening: Decimal | None = None
        closing: Decimal | None = None

        # Retain column indices once detected so continuation pages (no header row) work
        last_cols: dict[str, int | None] | None = None

        for table in tables:
            if not table:
                continue

            # ── Detect column indices from header row ──────────────────────────
            first_row = table[0]
            header = [c.replace("\n", " ").strip().lower() for c in first_row]
            try:
                date_col = next(i for i, h in enumerate(header) if "date" in h)
                narr_col = next(
                    i for i, h in enumerate(header)
                    if "remark" in h or "particular" in h or "description" in h
                    or "narr" in h or "detail" in h
                )
                dr_col = next(
                    (i for i, h in enumerate(header)
                     if "withdrawal" in h or ("debit" in h and "credit" not in h) or h == "dr"),
                    None,
                )
                cr_col = next(
                    (i for i, h in enumerate(header)
                     if "deposit" in h or ("credit" in h and "debit" not in h) or h == "cr"),
                    None,
                )
                bal_col = next((i for i, h in enumerate(header) if "balance" in h), None)
                ref_col = next(
                    (i for i, h in enumerate(header)
                     if "tran id" in h or "chq" in h or "ref" in h or "cheque" in h),
                    None,
                )
                last_cols = {
                    "date": date_col, "narr": narr_col, "dr": dr_col,
                    "cr": cr_col, "bal": bal_col, "ref": ref_col,
                }
                data_rows = table[1:]  # skip header row
            except StopIteration:
                # No header row — continuation page; reuse last known column layout
                if last_cols is None:
                    continue
                date_col = last_cols["date"]
                narr_col = last_cols["narr"]
                dr_col   = last_cols["dr"]
                cr_col   = last_cols["cr"]
                bal_col  = last_cols["bal"]
                ref_col  = last_cols["ref"]
                data_rows = table  # entire table is data

            # ── Parse data rows ────────────────────────────────────────────────
            for row_num, row in enumerate(data_rows, start=len(rows) + 1):
                raw_date_cell = row[date_col].strip() if date_col < len(row) else ""
                if not raw_date_cell or not _DATE_RE.search(raw_date_cell):
                    # Check if this is a Summary row carrying opening/closing balance
                    for ci, cell in enumerate(row):
                        if _OPENING_CELL_RE.search(cell) and ci + 1 < len(row):
                            val = _CR_DR_SUFFIX_RE.sub("", row[ci + 1]).strip()
                            if opening is None:
                                opening = _clean_amount(val)
                        if _CLOSING_CELL_RE.search(cell) and ci + 1 < len(row):
                            val = _CR_DR_SUFFIX_RE.sub("", row[ci + 1]).strip()
                            if closing is None:
                                closing = _clean_amount(val)
                    continue
                # UX3 PDF cells pack date + time as "DD-MM-YYYY\nHH:MM:SS" — keep date only
                raw_date = raw_date_cell.split("\n")[0].strip().replace("-", "/")

                narration = " ".join(
                    (row[narr_col] if narr_col < len(row) else "").split()
                )

                raw_debit = (
                    row[dr_col].replace("\n", "").strip() or None
                    if dr_col is not None and dr_col < len(row) else None
                )
                raw_credit = (
                    row[cr_col].replace("\n", "").strip() or None
                    if cr_col is not None and cr_col < len(row) else None
                )

                raw_balance_cell = (
                    row[bal_col].replace("\n", "").strip()
                    if bal_col is not None and bal_col < len(row) else ""
                )
                # Strip trailing "Cr"/"Dr" marker (monthly statements append it)
                raw_balance_cell = _CR_DR_SUFFIX_RE.sub("", raw_balance_cell).strip()

                rows.append(
                    RawParsedRow(
                        batch_id=batch_id,
                        source_type=SourceType.UNION_BANK,
                        parser_version=self.version,
                        extraction_method=ExtractionMethod.TABLE_EXTRACTION,
                        raw_date=raw_date,
                        raw_narration=narration,
                        raw_debit=raw_debit,
                        raw_credit=raw_credit,
                        raw_balance=raw_balance_cell or None,
                        raw_reference=(
                            row[ref_col].replace("\n", " ").strip() or None
                            if ref_col is not None and ref_col < len(row) else None
                        ),
                        txn_type_hint=_infer_txn_type(narration),
                        row_confidence=0.9,
                        row_number=row_num,
                    )
                )

        return rows, opening, closing
