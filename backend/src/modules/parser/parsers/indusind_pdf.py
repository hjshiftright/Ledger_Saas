"""IndusInd Bank PDF parser.

IndusInd Bank statement format:
    Date | Particulars | Chq/Ref No. | Value Date | Debit | Credit | Balance
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

_OPENING_RE = re.compile(r"Opening\s+Balance\s*[:\-]?\s*([\d,]+\.\d{2})", re.I)
_CLOSING_RE = re.compile(r"Closing\s+Balance\s*[:\-]?\s*([\d,]+\.\d{2})", re.I)

_TXN_ROW_RE = re.compile(
    r"""
    ^(\d{2}[-/]\d{2}[-/]\d{4})   # Date
    \s+
    (.+?)                          # Particulars
    \s+
    (\S*)                          # Chq/Ref
    \s+
    (\d{2}[-/]\d{2}[-/]\d{4})    # Value date
    \s+
    ([\d,]+\.\d{2})?               # Debit
    \s*
    ([\d,]+\.\d{2})?               # Credit
    \s+
    ([\d,]+\.\d{2})                # Balance
    """,
    re.VERBOSE | re.MULTILINE,
)

_UPI_RE  = re.compile(r"\bUPI\b",  re.I)
_NEFT_RE = re.compile(r"\bNEFT\b", re.I)
_IMPS_RE = re.compile(r"\bIMPS\b", re.I)
_ATM_RE  = re.compile(r"\bATM\b",  re.I)
_CHQ_RE  = re.compile(r"\b(CHQ|CHEQUE|CLG|ECS)\b", re.I)


def _clean_amount(raw: str | None) -> Decimal | None:
    if not raw:
        return None
    try:
        return Decimal(raw.replace(",", ""))
    except InvalidOperation:
        return None


def _infer_txn_type(narration: str) -> TxnTypeHint:
    if _UPI_RE.search(narration):  return TxnTypeHint.UPI
    if _NEFT_RE.search(narration): return TxnTypeHint.NEFT
    if _IMPS_RE.search(narration): return TxnTypeHint.IMPS
    if _ATM_RE.search(narration):  return TxnTypeHint.ATM_WITHDRAWAL
    if _CHQ_RE.search(narration):  return TxnTypeHint.CHEQUE
    return TxnTypeHint.UNKNOWN


class IndusIndPdfParser(BaseParser):
    """Parses IndusInd Bank PDF account statements."""

    source_type = SourceType.INDUSIND_BANK
    version = "1.0"
    supported_formats = ["PDF"]

    def __init__(self) -> None:
        self._text_extractor  = TextLayerExtractor()
        self._table_extractor = TableExtractor()
        self._ocr_extractor   = OCRExtractor()

    def supported_methods(self) -> list[ExtractionMethod]:
        return [ExtractionMethod.TEXT_LAYER, ExtractionMethod.TABLE_EXTRACTION, ExtractionMethod.OCR]

    def extract(self, batch_id: str, file_bytes: bytes, method: ExtractionMethod) -> ExtractionResult:
        try:
            if method == ExtractionMethod.TEXT_LAYER:
                text = "\n".join(self._text_extractor.extract_pages(file_bytes))
                if not text.strip():
                    return self._make_failed_result(batch_id, method, "No text in PDF.")
                return self.parse_text_content(batch_id, text, method)

            if method == ExtractionMethod.TABLE_EXTRACTION:
                tables = self._table_extractor.extract_tables(file_bytes, method="auto")
                if not tables:
                    return self._make_failed_result(batch_id, method, "No tables found.")
                text = "\n".join("  ".join(c.strip() for c in row) for tbl in tables for row in tbl)
                return self.parse_text_content(batch_id, text, method)

            if method == ExtractionMethod.OCR:
                text = self._ocr_extractor.extract_combined(file_bytes)
                if not text.strip():
                    return self._make_failed_result(batch_id, method, "OCR produced no text.")
                return self.parse_text_content(batch_id, text, method)

        except Exception as exc:  # noqa: BLE001
            logger.warning("IndusIndPdfParser.extract(%s) failed: %s", method.value, exc)
        return self._make_failed_result(batch_id, method, f"Extraction method {method.value} failed.")

    def parse_text_content(
        self,
        batch_id: str,
        text: str,
        method: ExtractionMethod = ExtractionMethod.TEXT_LAYER,
    ) -> ExtractionResult:
        rows: list[RawParsedRow] = []
        errors: list[str] = []
        opening = _clean_amount(m.group(1)) if (m := _OPENING_RE.search(text)) else None
        closing = _clean_amount(m.group(1)) if (m := _CLOSING_RE.search(text)) else None

        for row_num, match in enumerate(_TXN_ROW_RE.finditer(text), start=1):
            raw_debit  = match.group(5)
            raw_credit = match.group(6)
            has_amount = bool(raw_debit or raw_credit)
            if not has_amount:
                errors.append(f"Row {row_num}: no debit or credit amount")

            rows.append(RawParsedRow(
                batch_id=batch_id,
                source_type=SourceType.INDUSIND_BANK,
                parser_version=self.version,
                extraction_method=method,
                raw_date=match.group(1),
                raw_narration=match.group(2).strip(),
                raw_reference=match.group(3).strip() or None,
                raw_debit=raw_debit,
                raw_credit=raw_credit,
                raw_balance=match.group(7),
                txn_type_hint=_infer_txn_type(match.group(2)),
                row_confidence=0.9 if has_amount else 0.5,
                row_number=row_num,
            ))

        debits  = [d for r in rows if r.raw_debit  and (d := _clean_amount(r.raw_debit))]
        credits = [c for r in rows if r.raw_credit and (c := _clean_amount(r.raw_credit))]
        signals = ConfidenceSignals(
            balance_cross_check_passed=check_balance_cross_check(opening, closing, debits, credits),
            all_rows_have_valid_date=bool(rows) and all(bool(r.raw_date.strip()) for r in rows),
            all_rows_have_amount=bool(rows) and all(r.raw_debit or r.raw_credit for r in rows),
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
            opening_balance=opening,
            closing_balance=closing,
            balance_cross_check_passed=signals.balance_cross_check_passed,
            overall_confidence=confidence,
            warnings=errors,
            extraction_method=method,
            parser_version=self.version,
        )
        return ExtractionResult(rows=rows, metadata=meta, method=method, confidence=confidence)
