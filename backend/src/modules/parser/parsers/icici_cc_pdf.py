"""ICICI Bank Credit Card PDF parser.

Parses ICICI Bank credit card e-statement PDFs (Amazon Pay ICICI, Sapphiro,
Coral, Rubyx, etc.).

Column layout (as extracted by pdfplumber — columns merged on one line):
    Date  SerNo.  Transaction Details  [Reward Points]  [Intl. Amt]  Amount (in`)

Amount column:
    - Purchases / charges : plain number  → raw_debit
    - Payments / credits  : number followed by "(Cr)" OR description contains
                            PAYMENT / CREDIT / REFUND / REVERSAL  → raw_credit

Multi-line format (PyMuPDF / test fixtures):
    Each field on a separate line starting with the date.
"""

from __future__ import annotations

import logging
import re
from decimal import Decimal, InvalidOperation

from core.models.enums import ExtractionMethod, SourceType, TxnTypeHint
from core.models.raw_parsed_row import ParseMetadata, RawParsedRow
from core.utils.confidence import ConfidenceSignals, compute_confidence
from modules.parser.base import BaseParser, ExtractionResult
from modules.parser.extraction.ocr import OCRExtractor
from modules.parser.extraction.text_layer import TextLayerExtractor

logger = logging.getLogger(__name__)

# ── Regexes ───────────────────────────────────────────────────────────────────

# pdfplumber single-line format:
#   DD/MM/YYYY  <SerNo 9+ digits>  <description + optional reward pts>  amount[(Cr)]
_TXN_INLINE_RE = re.compile(
    r"^(\d{2}/\d{2}/\d{4})\s+(\d{9,})\s+(.+?)\s+([\d,]+\.\d{2})\s*(\(Cr\))?\s*$",
    re.I,
)

# Multi-line block start: line begins with DD/MM/YYYY
_TXN_DATE_LINE_RE = re.compile(r"^(\d{2}/\d{2}/\d{4})\s*(.*)$")

# Amount-only line (multi-line format): "2,084.00" or "2,084.00 (Cr)"
_AMOUNT_ONLY_RE = re.compile(r"^([\d,]+\.\d{2})\s*(\(Cr\))?\s*$", re.I)

# Serial-number-only line (9+ digits with no spaces — identifies transaction rows)
_SERIAL_RE = re.compile(r"^\d{9,}$")

# Statement period: "Statement period : December 26, 2024 to February 25, 2026"
_PERIOD_MONTHNAME_RE = re.compile(
    r"Statement period\s*[:\-]\s*(\w+ \d+,?\s*\d{4})\s+to\s+(\w+ \d+,?\s*\d{4})", re.I
)
# Also handle DD/MM/YYYY - DD/MM/YYYY format
_PERIOD_DMY_RE = re.compile(
    r"Statement period\s*[:\-]\s*(\d{2}/\d{2}/\d{4})\s+to\s+(\d{2}/\d{2}/\d{4})", re.I
)

# Card number: masked form "4315XXXXXXXX8000" or similar
_CARD_RE = re.compile(r"\b(\d{4}[X*]{4,}\d{4,})\b", re.I)

# Credit-direction keywords in description
_CREDIT_KEYWORDS_RE = re.compile(
    r"\b(PAYMENT|CREDIT|REFUND|REVERSAL|CASHBACK|CASH\s*BACK|WAIVER|REWARD)\b",
    re.I,
)

# UPI / payment-type markers for TxnTypeHint
_UPI_RE  = re.compile(r"\bUPI[_\b/]?",          re.I)
_NEFT_RE = re.compile(r"\bNEFT\b",              re.I)
_IMPS_RE = re.compile(r"\bIMPS\b",              re.I)
_ATM_RE  = re.compile(r"\bATM\b",               re.I)
_CHQ_RE  = re.compile(r"\b(CHQ|CHEQUE|CLG|ECS)\b", re.I)

# Trailing noise in description: reward points `20` or intl amount `1,234.56`
# We strip trailing standalone small integers (reward pts) that crept into description
_TRAILING_REWARD_RE = re.compile(r"\s+\d{1,6}\s*$")


def _clean_amount(raw: str) -> Decimal | None:
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


def _is_credit_row(description: str, has_cr_suffix: bool) -> bool:
    """True when the transaction is a credit (payment / refund / reversal)."""
    if has_cr_suffix:
        return True
    return bool(_CREDIT_KEYWORDS_RE.search(description))


def _parse_english_date(date_str: str) -> str | None:
    """Convert 'December 26, 2024' or 'December 26 2024' → 'YYYY-MM-DD'."""
    _MONTHS = {
        "january": "01", "february": "02", "march": "03", "april": "04",
        "may": "05", "june": "06", "july": "07", "august": "08",
        "september": "09", "october": "10", "november": "11", "december": "12",
    }
    m = re.match(r"(\w+)\s+(\d+),?\s*(\d{4})", date_str.strip(), re.I)
    if not m:
        return None
    month = _MONTHS.get(m.group(1).lower())
    if not month:
        return None
    return f"{m.group(3)}-{month}-{int(m.group(2)):02d}"


def _dmy_to_iso(date_str: str) -> str | None:
    parts = date_str.split("/")
    if len(parts) == 3:
        return f"{parts[2]}-{parts[1]}-{parts[0]}"
    return None


class IciciCcPdfParser(BaseParser):
    """Parses ICICI Bank Credit Card PDF e-statements.

    Extraction order:
        1. TEXT_LAYER  — pdfplumber merges table columns onto single lines
        2. OCR         — fallback for scanned / printed copies

    Supports all ICICI CC variants: Amazon Pay, Sapphiro, Coral, Rubyx, etc.
    """

    source_type = SourceType.ICICI_BANK_CC
    version = "1.0"
    supported_formats = ["PDF"]

    def __init__(self) -> None:
        self._text_extractor = TextLayerExtractor()
        self._ocr_extractor = OCRExtractor()

    def supported_methods(self) -> list[ExtractionMethod]:
        return [ExtractionMethod.TEXT_LAYER, ExtractionMethod.OCR]

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

            if method == ExtractionMethod.OCR:
                combined = self._ocr_extractor.extract_combined(file_bytes)
                if not combined.strip():
                    return self._make_failed_result(batch_id, method, "OCR produced no text.")
                return self.parse_text_content(batch_id, combined, method)

            return self._make_failed_result(batch_id, method, f"Unsupported method: {method}")

        except Exception as exc:  # noqa: BLE001
            logger.warning("IciciCcPdfParser.extract failed: %s", exc, exc_info=True)
            return self._make_failed_result(batch_id, method, str(exc))

    # ── Core parsing ──────────────────────────────────────────────────────────

    def parse_text_content(
        self,
        batch_id: str,
        text: str,
        method: ExtractionMethod = ExtractionMethod.TEXT_LAYER,
    ) -> ExtractionResult:
        """Parse ICICI Bank CC e-statement text.

        Pure function — unit-testable without real PDF bytes.

        **Inline (pdfplumber)** — each transaction on one line:
            DD/MM/YYYY SerNo DESCRIPTION [reward_pts] amount[(Cr)]

        **Multi-line (PyMuPDF / test fixtures)**:
            DD/MM/YYYY [desc fragment]
            SerNo
            DESCRIPTION
            [reward_pts]
            amount[(Cr)]
        """
        rows: list[RawParsedRow] = []
        errors: list[str] = []

        # ── Statement-level metadata ───────────────────────────────────────
        card_match = _CARD_RE.search(text)
        account_hint = card_match.group(1) if card_match else None

        stmt_from = stmt_to = None
        m = _PERIOD_DMY_RE.search(text)
        if m:
            stmt_from = _dmy_to_iso(m.group(1))
            stmt_to = _dmy_to_iso(m.group(2))
        else:
            m = _PERIOD_MONTHNAME_RE.search(text)
            if m:
                stmt_from = _parse_english_date(m.group(1))
                stmt_to = _parse_english_date(m.group(2))

        # ── First pass: inline single-line format (pdfplumber) ────────────
        inline_rows: list[RawParsedRow] = []

        for line_num, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            m2 = _TXN_INLINE_RE.match(stripped)
            if not m2:
                continue

            raw_date = m2.group(1)
            serial   = m2.group(2)
            desc_raw = m2.group(3).strip()
            raw_amt  = m2.group(4)
            cr_flag  = bool(m2.group(5))

            # Strip trailing reward points number from description
            desc_clean = _TRAILING_REWARD_RE.sub("", desc_raw).strip()

            is_credit = _is_credit_row(desc_clean, cr_flag)
            raw_debit  = raw_amt if not is_credit else None
            raw_credit = raw_amt if is_credit     else None

            inline_rows.append(
                RawParsedRow(
                    batch_id=batch_id,
                    source_type=SourceType.ICICI_BANK_CC,
                    parser_version=self.version,
                    extraction_method=method,
                    raw_date=raw_date,
                    raw_narration=desc_clean,
                    raw_debit=raw_debit,
                    raw_credit=raw_credit,
                    raw_balance=None,       # CC statement — no per-row balance
                    raw_reference=serial,
                    txn_type_hint=_infer_txn_type(desc_clean),
                    row_number=line_num,
                    row_confidence=0.9,
                )
            )

        if inline_rows:
            rows = inline_rows
        else:
            # ── Second pass: multi-line block format (PyMuPDF / fixtures) ─
            lines = text.splitlines()
            i = 0
            block_num = 0
            while i < len(lines):
                stripped = lines[i].strip()
                # Look for a date line
                dm = _TXN_DATE_LINE_RE.match(stripped) if stripped else None
                if not dm:
                    i += 1
                    continue

                raw_date = dm.group(1)
                block_lines = [dm.group(2).strip()] if dm.group(2).strip() else []
                i += 1

                # Collect subsequent non-date lines into the block until next date or end
                while i < len(lines):
                    nxt = lines[i].strip()
                    if not nxt:
                        i += 1
                        continue
                    if _TXN_DATE_LINE_RE.match(nxt):
                        break
                    block_lines.append(nxt)
                    i += 1

                if not block_lines:
                    errors.append(f"Row near line {i}: date line with no content — skipped")
                    continue

                # Find serial number and amount from block_lines
                serial: str | None = None
                raw_amt: str | None = None
                cr_flag = False
                desc_parts: list[str] = []

                for bl in block_lines:
                    if _SERIAL_RE.match(bl) and serial is None:
                        serial = bl
                    elif _AMOUNT_ONLY_RE.match(bl):
                        am = _AMOUNT_ONLY_RE.match(bl)
                        if am:
                            raw_amt = am.group(1)
                            cr_flag = bool(am.group(2))
                    elif not bl.isdigit():   # skip standalone reward point numbers
                        desc_parts.append(bl)

                if raw_amt is None:
                    errors.append(f"Row {block_num} ({raw_date}): no amount — skipped")
                    continue

                desc_clean = " ".join(desc_parts).strip()
                desc_clean = _TRAILING_REWARD_RE.sub("", desc_clean).strip()

                is_credit = _is_credit_row(desc_clean, cr_flag)
                raw_debit  = raw_amt if not is_credit else None
                raw_credit = raw_amt if is_credit     else None

                block_num += 1
                rows.append(
                    RawParsedRow(
                        batch_id=batch_id,
                        source_type=SourceType.ICICI_BANK_CC,
                        parser_version=self.version,
                        extraction_method=method,
                        raw_date=raw_date,
                        raw_narration=desc_clean or raw_date,
                        raw_debit=raw_debit,
                        raw_credit=raw_credit,
                        raw_balance=None,
                        raw_reference=serial,
                        txn_type_hint=_infer_txn_type(desc_clean),
                        row_number=block_num,
                        row_confidence=0.9,
                    )
                )

        # ── Confidence ────────────────────────────────────────────────────
        all_have_date   = all(r.raw_date for r in rows)
        all_have_amount = all(r.raw_debit or r.raw_credit for r in rows)

        signals = ConfidenceSignals(
            balance_cross_check_passed=None,   # n/a for credit card statements
            all_rows_have_valid_date=all_have_date,
            all_rows_have_amount=all_have_amount,
            row_count_positive=len(rows) > 0,
            no_row_parse_errors=len(errors) == 0,
        )
        confidence = compute_confidence(signals)

        meta = ParseMetadata(
            statement_from=stmt_from,
            statement_to=stmt_to,
            account_hint=account_hint,
            total_rows_found=len(rows),
            rows_with_errors=len(errors),
            opening_balance=None,
            closing_balance=None,
            balance_cross_check_passed=None,
            overall_confidence=confidence,
            warnings=errors,
            extraction_method=method,
            parser_version=self.version,
        )
        return ExtractionResult(rows=rows, metadata=meta, method=method, confidence=confidence)
