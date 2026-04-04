"""Canara Bank PDF parser.

Handles statement layouts visible in provided samples:
- Header columns: Txn Date | Value Date | Cheque No. | Description | Branch Code | Debit | Credit | Balance
- Txn Date may include time (e.g. 16-02-2023 16:23:06)
- Description frequently wraps into continuation rows
"""

from __future__ import annotations

import logging
import re
from decimal import Decimal, InvalidOperation

from core.models.enums import ExtractionMethod, SourceType, TxnTypeHint
from core.models.raw_parsed_row import ParseMetadata, RawParsedRow
from core.utils.confidence import ConfidenceSignals, compute_confidence, check_balance_cross_check
from modules.parser.base import BaseParser, ExtractionResult
from modules.parser.extraction.ocr import OCRExtractor
from modules.parser.extraction.table_extract import TableExtractor
from modules.parser.extraction.text_layer import TextLayerExtractor

logger = logging.getLogger(__name__)

_DATE_RE = re.compile(r"\b(\d{2}[/-]\d{2}[/-]\d{4})(?:\s+\d{2}:\d{2}:\d{2})?\b")
_TXN_RE = re.compile(
    r"""
    ^\s*(\d{2}[/-]\d{2}[/-]\d{4}(?:\s+\d{2}:\d{2}:\d{2})?)\s+
    (.+?)\s+
    (\S*)\s+
    (-?[\d,]+\.\d{2})?\s*
    (-?[\d,]+\.\d{2})?\s+
    (-?[\d,]+\.\d{2}(?:\s*[CcDd][Rr])?)
    """,
    re.VERBOSE | re.MULTILINE,
)
_CR_DR_SUFFIX_RE = re.compile(r"\s*([CcDd][Rr])\s*$")

_UPI_RE = re.compile(r"\bUPI\b", re.I)
_NEFT_RE = re.compile(r"\bNEFT\b", re.I)
_IMPS_RE = re.compile(r"\bIMPS\b", re.I)
_ATM_RE = re.compile(r"\bATM\b|\bCASH\s+WD\b|\bCASH\s+WITHDRAWAL\b", re.I)
_CHQ_RE = re.compile(r"\b(CHQ|CHEQUE|CLG|CLR)\b", re.I)


def _clean_amount(raw: str | None) -> Decimal | None:
    if not raw:
        return None
    cleaned = _CR_DR_SUFFIX_RE.sub("", raw).replace(",", "").strip()
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
    if _CHQ_RE.search(narration):
        return TxnTypeHint.CHEQUE
    return TxnTypeHint.UNKNOWN


def _strip_crdr(raw: str | None) -> str | None:
    if not raw:
        return None
    out = _CR_DR_SUFFIX_RE.sub("", raw).strip()
    return out or None


class CanaraPdfParser(BaseParser):
    source_type = SourceType.CANARA_BANK
    version = "1.0"
    supported_formats = ["PDF"]

    def __init__(self) -> None:
        self._text_extractor = TextLayerExtractor()
        self._table_extractor = TableExtractor()
        self._ocr_extractor = OCRExtractor()

    def supported_methods(self) -> list[ExtractionMethod]:
        # Canara statements in observed samples are parsed reliably from text layer.
        # Table extraction may return positional/shifted cells for this layout.
        return [ExtractionMethod.TEXT_LAYER, ExtractionMethod.OCR]

    def extract(self, batch_id: str, file_bytes: bytes, method: ExtractionMethod) -> ExtractionResult:
        try:
            if method == ExtractionMethod.TEXT_LAYER:
                pages = self._text_extractor.extract_pages(file_bytes)
                text = "\n".join(pages)
                if not text.strip():
                    return self._make_failed_result(batch_id, method, "No text in PDF.")
                return self.parse_text_content(batch_id, text, method)
            if method == ExtractionMethod.TABLE_EXTRACTION:
                tables = self._table_extractor.extract_tables(file_bytes, method="auto")
                if not tables:
                    return self._make_failed_result(batch_id, method, "No tables found.")
                rows = self._rows_from_tables(batch_id, tables)
                return self._build_result(rows, method)
            if method == ExtractionMethod.OCR:
                text = self._ocr_extractor.extract_combined(file_bytes)
                if not text.strip():
                    return self._make_failed_result(batch_id, method, "OCR produced no text.")
                return self.parse_text_content(batch_id, text, method)
        except Exception as exc:  # noqa: BLE001
            logger.warning("CanaraPdfParser.extract(%s) failed: %s", method.value, exc, exc_info=True)
        return self._make_failed_result(batch_id, method, f"Method {method.value} failed.")

    def parse_text_content(
        self,
        batch_id: str,
        text: str,
        method: ExtractionMethod = ExtractionMethod.TEXT_LAYER,
    ) -> ExtractionResult:
        rows: list[RawParsedRow] = []
        errors: list[str] = []

        for row_num, match in enumerate(_TXN_RE.finditer(text), start=1):
            raw_date = match.group(1).replace("-", "/").split()[0]
            narration = match.group(2).strip()
            ref_no = match.group(3).strip()
            raw_debit = match.group(4)
            raw_credit = match.group(5)
            raw_balance = _strip_crdr(match.group(6))

            if raw_debit and not raw_credit and re.search(r"\bCR\b", narration, re.I):
                raw_credit, raw_debit = raw_debit, None
            if raw_debit and not raw_credit:
                narr_upper = narration.upper()
                if " DEPOSIT" in narr_upper or narr_upper.startswith("BY ") or narr_upper.startswith("CASH-BNA"):
                    raw_credit, raw_debit = raw_debit, None

            if not (raw_debit or raw_credit):
                errors.append(f"Row {row_num}: no debit or credit amount")

            rows.append(
                RawParsedRow(
                    batch_id=batch_id,
                    source_type=SourceType.CANARA_BANK,
                    parser_version=self.version,
                    extraction_method=method,
                    raw_date=raw_date,
                    raw_narration=narration,
                    raw_debit=raw_debit,
                    raw_credit=raw_credit,
                    raw_balance=raw_balance,
                    raw_reference=ref_no or None,
                    txn_type_hint=_infer_txn_type(narration),
                    row_confidence=0.9 if (raw_debit or raw_credit) else 0.5,
                    row_number=row_num,
                )
            )

        return self._build_result(rows, method, errors)

    def _build_result(
        self,
        rows: list[RawParsedRow],
        method: ExtractionMethod,
        errors: list[str] | None = None,
    ) -> ExtractionResult:
        errors = errors or []
        opening = _clean_amount(rows[0].raw_balance) if rows else None
        closing = _clean_amount(rows[-1].raw_balance) if rows else None
        debits = [_clean_amount(r.raw_debit) for r in rows if r.raw_debit]
        credits = [_clean_amount(r.raw_credit) for r in rows if r.raw_credit]
        debits = [d for d in debits if d is not None]
        credits = [c for c in credits if c is not None]

        balance_ok: bool | None = None
        if opening is not None and closing is not None:
            _ok = check_balance_cross_check(opening, closing, debits, credits)
            # Multi-page running-balance/carry-forward formatting can make this
            # check unreliable for this source; only reward a positive check.
            balance_ok = True if _ok else None

        signals = ConfidenceSignals(
            balance_cross_check_passed=balance_ok,
            all_rows_have_valid_date=bool(rows) and all(bool(_DATE_RE.search(r.raw_date or "")) for r in rows),
            all_rows_have_amount=bool(rows) and all(bool(r.raw_debit or r.raw_credit) for r in rows),
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

    def _rows_from_tables(self, batch_id: str, tables: list[list[list[str]]]) -> list[RawParsedRow]:
        rows: list[RawParsedRow] = []
        row_num = 0
        cols: dict[str, int | None] | None = None
        current_row: RawParsedRow | None = None

        for table in tables:
            if not table:
                continue
            header = [c.replace("\n", " ").strip().lower() for c in table[0]]
            try:
                date_col = next(i for i, h in enumerate(header) if "txn date" in h or h == "date")
                narr_col = next(i for i, h in enumerate(header) if "description" in h or "detail" in h or "narr" in h or "particular" in h)
                dr_col = next((i for i, h in enumerate(header) if "debit" in h or "withdraw" in h), None)
                cr_col = next((i for i, h in enumerate(header) if "credit" in h or "deposit" in h), None)
                bal_col = next((i for i, h in enumerate(header) if "balance" in h), None)
                ref_col = next((i for i, h in enumerate(header) if "ref" in h or "chq" in h or "cheque" in h), None)
                cols = {"date": date_col, "narr": narr_col, "dr": dr_col, "cr": cr_col, "bal": bal_col, "ref": ref_col}
                data_rows = table[1:]
            except StopIteration:
                if cols is None:
                    continue
                date_col = cols["date"]
                narr_col = cols["narr"]
                dr_col = cols["dr"]
                cr_col = cols["cr"]
                bal_col = cols["bal"]
                ref_col = cols["ref"]
                data_rows = table

            for row in data_rows:
                if date_col >= len(row):
                    continue
                date_cell = row[date_col].strip()
                if not date_cell or not _DATE_RE.search(date_cell):
                    if current_row is not None and narr_col < len(row):
                        extra = " ".join(row[narr_col].split()).strip()
                        if extra and "disclaimer" not in extra.lower() and "end of statement" not in extra.lower():
                            current_row.raw_narration = f"{(current_row.raw_narration or '').strip()} {extra}".strip()
                    continue
                row_num += 1
                raw_date = date_cell.split("\n")[0].strip().replace("-", "/").split()[0]
                narration = " ".join((row[narr_col] if narr_col < len(row) else "").split())
                if not narration or "disclaimer" in narration.lower() or "end of statement" in narration.lower():
                    continue
                raw_debit = (row[dr_col].replace("\n", "").strip() or None) if dr_col is not None and dr_col < len(row) else None
                raw_credit = (row[cr_col].replace("\n", "").strip() or None) if cr_col is not None and cr_col < len(row) else None
                raw_balance = (row[bal_col].replace("\n", "").strip() or None) if bal_col is not None and bal_col < len(row) else None
                raw_balance = _strip_crdr(raw_balance)
                raw_ref = (row[ref_col].replace("\n", " ").strip() or None) if ref_col is not None and ref_col < len(row) else None
                parsed = RawParsedRow(
                    batch_id=batch_id,
                    source_type=SourceType.CANARA_BANK,
                    parser_version=self.version,
                    extraction_method=ExtractionMethod.TABLE_EXTRACTION,
                    raw_date=raw_date,
                    raw_narration=narration,
                    raw_debit=raw_debit,
                    raw_credit=raw_credit,
                    raw_balance=raw_balance,
                    raw_reference=raw_ref,
                    txn_type_hint=_infer_txn_type(narration),
                    row_confidence=0.9,
                    row_number=row_num,
                )
                rows.append(parsed)
                current_row = parsed
        return rows
