"""Standard Chartered Bank PDF parser."""

from __future__ import annotations

import logging
import re
from decimal import Decimal, InvalidOperation

from core.models.enums import ExtractionMethod, SourceType, TxnTypeHint
from core.models.raw_parsed_row import ParseMetadata, RawParsedRow
from core.utils.confidence import ConfidenceSignals, check_balance_cross_check, compute_confidence
from modules.parser.base import BaseParser, ExtractionResult
from modules.parser.extraction.ocr import OCRExtractor
from modules.parser.extraction.table_extract import TableExtractor
from modules.parser.extraction.text_layer import TextLayerExtractor

logger = logging.getLogger(__name__)

_DATE_TOKEN = r"(?:\d{1,2}\s+[A-Za-z]{3}\s+\d{2}|\d{2}[/-]\d{2}[/-](?:\d{2}|\d{4}))"
_DATE_RE = re.compile(rf"\b({_DATE_TOKEN})\b")
_ROW_WITH_TWO_DATES_RE = re.compile(
    rf"^\s*({_DATE_TOKEN})\s+({_DATE_TOKEN})\s+(.+?)\s+([\d,]+\.\d{{2}})\s+([\d,]+\.\d{{2}})\s*$",
    re.I,
)
_ROW_WITH_ONE_DATE_RE = re.compile(
    rf"^\s*({_DATE_TOKEN})\s+(.+?)\s+([\d,]+\.\d{{2}})\s+([\d,]+\.\d{{2}})\s*$",
    re.I,
)
_ROW_WITHOUT_DATE_RE = re.compile(r"^\s*(.+?)\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s*$")
# Opening / carry-forward: "DD Mon YY  DD Mon YY  BALANCE FORWARD  12,345.67" (single amount = balance only)
_ROW_BALANCE_FORWARD_RE = re.compile(
    rf"^\s*({_DATE_TOKEN})\s+({_DATE_TOKEN})\s+BALANCE\s+FORWARD\s+([\d,]+\.\d{{2}})\s*$",
    re.I,
)
_CR_DR_SUFFIX_RE = re.compile(r"\s*([CcDd][Rr])\s*$")

_UPI_RE = re.compile(r"\bUPI\b", re.I)
_NEFT_RE = re.compile(r"\bNEFT\b", re.I)
_IMPS_RE = re.compile(r"\bIMPS\b", re.I)


def _clean_amount(raw: str | None) -> Decimal | None:
    if not raw:
        return None
    cleaned = _CR_DR_SUFFIX_RE.sub("", raw).replace(",", "").strip()
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _strip_crdr(raw: str | None) -> str | None:
    if not raw:
        return None
    out = _CR_DR_SUFFIX_RE.sub("", raw).strip()
    return out or None


def _infer_txn_type(narration: str) -> TxnTypeHint:
    if _UPI_RE.search(narration):
        return TxnTypeHint.UPI
    if _NEFT_RE.search(narration):
        return TxnTypeHint.NEFT
    if _IMPS_RE.search(narration):
        return TxnTypeHint.IMPS
    return TxnTypeHint.UNKNOWN


def _normalize_sc_date(raw: str) -> str:
    parts = raw.split()
    if len(parts) == 3:
        day = parts[0].zfill(2)
        mon = parts[1].title()
        yy = parts[2]
        month_map = {
            "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
            "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
            "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12",
        }
        mm = month_map.get(mon, "01")
        return f"{day}/{mm}/{yy}"
    return raw.replace("-", "/")


def _is_continuation_only(narration: str) -> bool:
    """True for fragments that belong in the previous row, not a new txn line."""
    up = narration.upper().strip()
    # A full Standard Chartered UPI line starts with UPI/… and has amounts on the same line
    # (handled before this check). Never treat UPI/… as a bare reference fragment.
    if up.startswith("UPI/"):
        return False
    # NACH / EMI lines: single token like "KISETSUSAINHEEIXHDLDLOKN" + amount + balance on the
    # same physical line — must be a new row, not a numeric reference merged into the prior UPI.
    if up.startswith("KISETS"):
        return False
    return (
        up.startswith("AT ")
        or up.endswith("/INR")
        or re.fullmatch(r"[A-Z0-9/\-]{8,}", up) is not None
    )


def _classify_amount(narration: str, amount: str) -> tuple[str | None, str | None]:
    up = narration.upper()
    credit_markers = ("CRADJ", "CREDIT", "DEPOSIT", "NEFT ", "INWARD", "REFUND")
    debit_markers = ("WITHDRAWAL", "PURCHASE", "UPI/", "CHARGES", "CGST", "SGST", "IMPS/P2A", "IMPS/")
    if any(k in up for k in credit_markers):
        return None, amount
    if any(k in up for k in debit_markers):
        return amount, None
    # Conservative fallback for this statement format: single amount rows are mostly debits.
    return amount, None


class StandardCharteredPdfParser(BaseParser):
    source_type = SourceType.STANDARD_CHARTERED_BANK
    version = "1.0"
    supported_formats = ["PDF"]

    def __init__(self) -> None:
        self._text_extractor = TextLayerExtractor()
        self._table_extractor = TableExtractor()
        self._ocr_extractor = OCRExtractor()

    def supported_methods(self) -> list[ExtractionMethod]:
        return [ExtractionMethod.TEXT_LAYER, ExtractionMethod.TABLE_EXTRACTION, ExtractionMethod.OCR]

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
            logger.warning("StandardCharteredPdfParser.extract(%s) failed: %s", method.value, exc, exc_info=True)
        return self._make_failed_result(batch_id, method, f"Method {method.value} failed.")

    def parse_text_content(
        self,
        batch_id: str,
        text: str,
        method: ExtractionMethod = ExtractionMethod.TEXT_LAYER,
    ) -> ExtractionResult:
        rows: list[RawParsedRow] = []
        errors: list[str] = []
        current_row: RawParsedRow | None = None
        current_date: str | None = None
        row_num = 0

        for raw_line in text.splitlines():
            line = " ".join(raw_line.split()).strip()
            if not line:
                continue

            low = line.lower()
            # Do not skip "balance forward" here — opening lines look like
            # "DD Mon YY DD Mon YY BALANCE FORWARD 12,345.67" and must be parsed
            # to set current_date for following no-date UPI rows.
            if any(
                s in low
                for s in (
                    "account statement",
                    "page ",
                    "value date description",
                    "bank deposits are covered",
                    "please register the nomination",
                    "report irregularities in your statement",
                    "reward points statement",
                )
            ):
                continue
            # Footer summary line: "TOTAL dr cr balance" — not a transaction
            if re.match(r"^\s*TOTAL\s+[\d,]", line, re.I):
                continue

            m_bf = _ROW_BALANCE_FORWARD_RE.match(line)
            if m_bf:
                # Sets the active statement date so following UPI/NACH lines (no date on line) parse.
                current_date = _normalize_sc_date(m_bf.group(1))
                current_row = None
                continue

            m = _ROW_WITH_TWO_DATES_RE.match(line) or _ROW_WITH_ONE_DATE_RE.match(line)
            if m:
                if len(m.groups()) == 5:
                    txn_date = m.group(1)
                    narration = m.group(3)
                    amount = m.group(4)
                    balance = m.group(5)
                else:
                    txn_date = m.group(1)
                    narration = m.group(2)
                    amount = m.group(3)
                    balance = m.group(4)
                current_date = _normalize_sc_date(txn_date)
                raw_debit, raw_credit = _classify_amount(narration, amount)
                row_num += 1
                current_row = RawParsedRow(
                    batch_id=batch_id,
                    source_type=SourceType.STANDARD_CHARTERED_BANK,
                    parser_version=self.version,
                    extraction_method=method,
                    raw_date=current_date,
                    raw_narration=narration.strip(),
                    raw_debit=raw_debit,
                    raw_credit=raw_credit,
                    raw_balance=_strip_crdr(balance),
                    raw_reference=None,
                    txn_type_hint=_infer_txn_type(narration),
                    row_confidence=0.9,
                    row_number=row_num,
                )
                rows.append(current_row)
                continue

            m2 = _ROW_WITHOUT_DATE_RE.match(line)
            if m2 and current_date:
                narration = m2.group(1).strip()
                amount = m2.group(2)
                balance = m2.group(3)
                # Ignore clear continuation fragments containing only location/time/id text.
                if _is_continuation_only(narration):
                    if current_row is not None:
                        current_row.raw_narration = f"{(current_row.raw_narration or '').strip()} {narration}".strip()
                    continue
                raw_debit, raw_credit = _classify_amount(narration, amount)
                row_num += 1
                current_row = RawParsedRow(
                    batch_id=batch_id,
                    source_type=SourceType.STANDARD_CHARTERED_BANK,
                    parser_version=self.version,
                    extraction_method=method,
                    raw_date=current_date,
                    raw_narration=narration,
                    raw_debit=raw_debit,
                    raw_credit=raw_credit,
                    raw_balance=_strip_crdr(balance),
                    raw_reference=None,
                    txn_type_hint=_infer_txn_type(narration),
                    row_confidence=0.88,
                    row_number=row_num,
                )
                rows.append(current_row)
                continue

            # Free-form continuation lines: append to prior narration.
            if current_row is not None and not low.startswith("ifsc:") and "mr " not in low:
                current_row.raw_narration = f"{(current_row.raw_narration or '').strip()} {line}".strip()

        if not rows:
            errors.append("No Standard Chartered transaction rows parsed from text.")
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
        for table in tables:
            if not table:
                continue
            header = [c.replace("\n", " ").strip().lower() for c in table[0]]
            try:
                date_col = next(i for i, h in enumerate(header) if "date" in h)
                narr_col = next(i for i, h in enumerate(header) if "description" in h or "narration" in h or "details" in h)
                dr_col = next((i for i, h in enumerate(header) if "debit" in h or "withdraw" in h), None)
                cr_col = next((i for i, h in enumerate(header) if "credit" in h or "deposit" in h), None)
                bal_col = next((i for i, h in enumerate(header) if "balance" in h), None)
                ref_col = next((i for i, h in enumerate(header) if "ref" in h or "chq" in h), None)
            except StopIteration:
                continue
            for row in table[1:]:
                if date_col >= len(row):
                    continue
                date_cell = row[date_col].strip()
                if not date_cell or not _DATE_RE.search(date_cell):
                    continue
                row_num += 1
                narration = " ".join((row[narr_col] if narr_col < len(row) else "").split())
                raw_debit = (row[dr_col].replace("\n", "").strip() or None) if dr_col is not None and dr_col < len(row) else None
                raw_credit = (row[cr_col].replace("\n", "").strip() or None) if cr_col is not None and cr_col < len(row) else None
                raw_balance = (row[bal_col].replace("\n", "").strip() or None) if bal_col is not None and bal_col < len(row) else None
                raw_ref = (row[ref_col].replace("\n", " ").strip() or None) if ref_col is not None and ref_col < len(row) else None
                rows.append(
                    RawParsedRow(
                        batch_id=batch_id,
                        source_type=SourceType.STANDARD_CHARTERED_BANK,
                        parser_version=self.version,
                        extraction_method=ExtractionMethod.TABLE_EXTRACTION,
                        raw_date=date_cell.replace("-", "/").split()[0],
                        raw_narration=narration,
                        raw_debit=_strip_crdr(raw_debit),
                        raw_credit=_strip_crdr(raw_credit),
                        raw_balance=_strip_crdr(raw_balance),
                        raw_reference=raw_ref,
                        txn_type_hint=_infer_txn_type(narration),
                        row_confidence=0.9,
                        row_number=row_num,
                    )
                )
        return rows
