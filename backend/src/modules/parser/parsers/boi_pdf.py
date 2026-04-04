"""Bank of India PDF parser.

Handles real BOI account-statement PDFs where the text layer lists one field per line:
  Sl No → Txn Date → Description → … → Withdrawal/Deposit amount → Balance

Also falls back to a generic single-line regex when that layout is not present.
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
_BOI_STMT_DATE = re.compile(r"^(\d{2}-\d{2}-\d{4})$")
_BOI_STMT_AMOUNT = re.compile(r"^([\d,]+\.\d{2}|\d+\.\d{2})$")
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


def _parse_money_cell(s: str) -> Decimal | None:
    s = s.replace(",", "").strip()
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def _boi_pdf_header_noise(line: str) -> bool:
    low = line.lower().strip()
    if low in frozenset({
        "sl no", "txn date", "description", "cheque no", "withdrawal", "deposits", "balance",
        "(in rs.)",
    }):
        return True
    if low.startswith("withdrawal") and "rs" in low:
        return True
    if low.startswith("deposits") and "rs" in low:
        return True
    if low.startswith("balance") and "rs" in low:
        return True
    return False


def _boi_classify_txn(narration: str, txn_amount: str) -> tuple[str | None, str | None]:
    """When balance delta is unavailable, infer debit vs credit from narration."""
    u = narration.upper()
    credit_hints = (
        "SALARY", "NEFT", "REFUND", "MSBTE", "CREDIT", "INT:", "INT :",
        "REV MERV", "BIT SALARY", " UPI ", "/CR/", " DEP ", " DEPOSIT",
    )
    debit_hints = (
        "CWDR", "MEDR", "NACH/", "LOAN", "BDIPG", "SMSCharges", "SMS CHARGES",
        "CHARGES", "ATM", "POS",
    )
    if any(h in u for h in credit_hints):
        return None, txn_amount
    if any(h in u for h in debit_hints):
        return txn_amount, None
    return txn_amount, None


def _finalize_boi_amount_rows(
    segments: list[tuple[str, str, str, str]],
) -> list[tuple[str, str, str | None, str | None, str]]:
    """Turn (date, narration, txn_amount, balance) segments into rows with debit/credit split."""
    parsed: list[tuple[str, str, str | None, str | None, str]] = []
    prev_bal: Decimal | None = None
    for raw_date, narration, txn_s, bal_s in segments:
        txn_d = _parse_money_cell(txn_s)
        new_bal = _parse_money_cell(bal_s)
        if txn_d is None or new_bal is None:
            continue

        raw_debit: str | None = None
        raw_credit: str | None = None

        if prev_bal is not None:
            delta = new_bal - prev_bal
            if abs(delta) < Decimal("0.0001"):
                prev_bal = new_bal
                continue
            if abs(abs(delta) - txn_d) <= Decimal("0.05"):
                if delta > 0:
                    raw_credit = txn_s
                else:
                    raw_debit = txn_s
            else:
                raw_debit, raw_credit = _boi_classify_txn(narration, txn_s)
        else:
            raw_debit, raw_credit = _boi_classify_txn(narration, txn_s)

        if not raw_debit and not raw_credit:
            raw_debit, raw_credit = _boi_classify_txn(narration, txn_s)

        prev_bal = new_bal
        parsed.append((raw_date, narration, raw_debit, raw_credit, bal_s))

    return parsed


def _collect_boi_stacked_segments(text: str) -> list[tuple[str, str, str, str]]:
    """PyMuPDF-style text: one field per line (date, narration, amounts on separate lines)."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    i = 0
    while i < len(lines):
        if _BOI_STMT_DATE.match(lines[i]):
            break
        i += 1

    segments: list[tuple[str, str, str, str]] = []

    while i < len(lines):
        if _boi_pdf_header_noise(lines[i]):
            i += 1
            continue

        if i + 1 < len(lines) and re.match(r"^\d+$", lines[i]) and _BOI_STMT_DATE.match(lines[i + 1]):
            i += 1

        dm = _BOI_STMT_DATE.match(lines[i])
        if not dm:
            i += 1
            continue

        raw_date = dm.group(1).replace("-", "/")
        i += 1

        narr_parts: list[str] = []
        while i < len(lines):
            if _BOI_STMT_DATE.match(lines[i]):
                break
            if i + 1 < len(lines) and re.match(r"^\d+$", lines[i]) and _BOI_STMT_DATE.match(lines[i + 1]):
                break
            if _BOI_STMT_AMOUNT.match(lines[i]):
                break
            if _boi_pdf_header_noise(lines[i]):
                break
            narr_parts.append(lines[i])
            i += 1

        narration = " ".join(narr_parts).strip()
        amounts: list[str] = []
        while i < len(lines) and _BOI_STMT_AMOUNT.match(lines[i]):
            amounts.append(lines[i])
            i += 1

        if len(amounts) < 2:
            continue

        txn_s, bal_s = amounts[-2], amounts[-1]
        segments.append((raw_date, narration, txn_s, bal_s))

    return segments


def _collect_boi_flat_line_segments(text: str) -> list[tuple[str, str, str, str]]:
    """pdfplumber-style text: one row per line — [optional SlNo] Date Narration TxnAmt Balance."""
    segments: list[tuple[str, str, str, str]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        low = line.lower()
        if "txn date" in low and "description" in low:
            continue
        # Support both older BOI rows with serial-number prefix and newer rows
        # without serial number:
        #   "12 27-06-2017 MEDR/... 10.00 9.08"
        #   "27-06-2017 MEDR/... 10.00 9.08"
        m = re.match(r"^(?:\d+\s+)?(\d{2}-\d{2}-\d{4})\s+(.+)$", line)
        if not m:
            continue
        rest = m.group(2).strip()
        parts = rest.split()
        if len(parts) < 3:
            continue
        bal_s, txn_s = parts[-1], parts[-2]
        if not _BOI_STMT_AMOUNT.match(txn_s) or not _BOI_STMT_AMOUNT.match(bal_s):
            continue
        narration = " ".join(parts[:-2])
        raw_date = m.group(1).replace("-", "/")
        segments.append((raw_date, narration, txn_s, bal_s))
    return segments


def parse_boi_statement_stacked_text(text: str) -> list[tuple[str, str, str | None, str | None, str]]:
    """Parse BOI PDF text where each transaction is stacked on separate lines (PyMuPDF).

    Returns tuples: (raw_date, narration, raw_debit, raw_credit, raw_balance).
    """
    return _finalize_boi_amount_rows(_collect_boi_stacked_segments(text))


def parse_boi_pdf_text_auto(text: str) -> list[tuple[str, str, str | None, str | None, str]]:
    """Try stacked (PyMuPDF) layout, then single-line (pdfplumber) layout."""
    segs = _collect_boi_stacked_segments(text)
    rows = _finalize_boi_amount_rows(segs) if segs else []
    if rows:
        return rows
    segs2 = _collect_boi_flat_line_segments(text)
    return _finalize_boi_amount_rows(segs2) if segs2 else []


class BoiPdfParser(BaseParser):
    source_type = SourceType.BOI_BANK
    version = "1.0"
    supported_formats = ["PDF"]

    def __init__(self) -> None:
        self._text_extractor = TextLayerExtractor()
        self._table_extractor = TableExtractor()
        self._ocr_extractor = OCRExtractor()

    def supported_methods(self) -> list[ExtractionMethod]:
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
            logger.warning("BoiPdfParser.extract(%s) failed: %s", method.value, exc, exc_info=True)
        return self._make_failed_result(batch_id, method, f"Method {method.value} failed.")

    def parse_text_content(
        self,
        batch_id: str,
        text: str,
        method: ExtractionMethod = ExtractionMethod.TEXT_LAYER,
    ) -> ExtractionResult:
        stacked = parse_boi_pdf_text_auto(text)
        rows: list[RawParsedRow] = []
        errors: list[str] = []

        if stacked:
            for row_num, (raw_date, narration, raw_debit, raw_credit, raw_balance) in enumerate(stacked, start=1):
                if not (raw_debit or raw_credit):
                    errors.append(f"Row {row_num}: no debit or credit amount")
                rows.append(
                    RawParsedRow(
                        batch_id=batch_id,
                        source_type=SourceType.BOI_BANK,
                        parser_version=self.version,
                        extraction_method=method,
                        raw_date=raw_date,
                        raw_narration=narration,
                        raw_debit=raw_debit,
                        raw_credit=raw_credit,
                        raw_balance=_strip_crdr(raw_balance),
                        raw_reference=None,
                        txn_type_hint=_infer_txn_type(narration),
                        row_confidence=0.9 if (raw_debit or raw_credit) else 0.5,
                        row_number=row_num,
                    )
                )
            return self._build_result(rows, method, errors)

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
                if (
                    " DEPOSIT" in narr_upper
                    or " SALARY" in narr_upper
                    or narr_upper.startswith("BY ")
                    or narr_upper.startswith("CR ")
                ):
                    raw_credit, raw_debit = raw_debit, None

            if not (raw_debit or raw_credit):
                errors.append(f"Row {row_num}: no debit or credit amount")

            rows.append(
                RawParsedRow(
                    batch_id=batch_id,
                    source_type=SourceType.BOI_BANK,
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

        def _date_col_idx(header: list[str]) -> int:
            for i, h in enumerate(header):
                if "txn date" in h or "value date" in h or h == "date":
                    return i
            raise StopIteration

        for table in tables:
            if not table:
                continue
            header = [c.replace("\n", " ").strip().lower() for c in table[0]]
            try:
                date_col = _date_col_idx(header)
                narr_col = next(
                    i
                    for i, h in enumerate(header)
                    if "description" in h or "detail" in h or "narr" in h or "particular" in h or "remarks" in h
                )
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
                    source_type=SourceType.BOI_BANK,
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
