"""Yes Bank Credit Card PDF parser.

Parses Yes Bank credit card e-statement PDFs.

Statement columns: Date | Transaction Details | Merchant Category | Amount (Rs.)

Amount format:
    1,234.56 Dr   — debit (purchase / cash advance)
    1,234.56 Cr   — credit (payment received / reversal)

Note: This is a credit card statement, so there is no per-row closing balance.
The parser sets raw_balance = None for all rows.
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

# A transaction block starts with DD/MM/YYYY followed by description text
_TXN_DATE_LINE_RE = re.compile(r"^(\d{2}/\d{2}/\d{4})\s+(.+)$")

# Inline / single-line format (pdfplumber merges table columns onto one line):
#   DD/MM/YYYY <description + merchant cat> amount.cc Dr|Cr
_TXN_INLINE_RE = re.compile(
    r"^(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([\d,]+\.\d{2})\s+(Dr|Cr)\s*$",
    re.I,
)

# Amount line on its own (multi-line / PyMuPDF format): "24.00 Dr" / "98,939.61 Cr"
_AMOUNT_LINE_RE = re.compile(r"^([\d,]+\.\d{2})\s+(Dr|Cr)\s*$", re.I)

# Reference number: "- Ref No: RT260480398000750000899" or "- Ref No: 0999..."
_REF_RE = re.compile(r"-\s*Ref\s*No[:\.]?\s*(\S+)", re.I)

# Statement period: "15/02/2026 To 14/03/2026"
_PERIOD_RE = re.compile(r"(\d{2}/\d{2}/\d{4})\s+To\s+(\d{2}/\d{2}/\d{4})", re.I)

# Card / account number: "YES BANK Card Number 3561XXXXXXXX4581"
_CARD_RE = re.compile(r"Card\s+Number\s+(\S+)", re.I)

# Lines to discard — column headers, reward-point section labels, footers
_SKIP_LINE_FRAGMENTS: frozenset[str] = frozenset({
    "date",
    "transaction details",
    "merchant category",
    "amount (rs.)",
    "opening reward points",
    "point earned",
    "bonus points",
    "points redeemed",
    "closing reward points",
    "page",
    "credit card statement",
    "important information",
    "yes bank klick",
    "yes touch phonebanking",
    "sms",
    "email us",
    "cin :",
})

# UPI / payment-type markers
_UPI_RE  = re.compile(r"\bUPI[_\b]",          re.I)
_NEFT_RE = re.compile(r"\bNEFT\b",            re.I)
_IMPS_RE = re.compile(r"\bIMPS\b",            re.I)
_ATM_RE  = re.compile(r"\bATM\b",             re.I)
_CHQ_RE  = re.compile(r"\b(CHQ|CHEQUE|CLG|ECS)\b", re.I)


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


def _is_skip_line(line: str) -> bool:
    """Return True if the line is a header / footer / boilerplate to ignore."""
    lower = line.strip().lower()
    for fragment in _SKIP_LINE_FRAGMENTS:
        if lower.startswith(fragment):
            return True
    return False


def _dmy_to_iso(date_str: str) -> str | None:
    """Convert 'DD/MM/YYYY' → 'YYYY-MM-DD'."""
    parts = date_str.split("/")
    if len(parts) == 3:
        return f"{parts[2]}-{parts[1]}-{parts[0]}"
    return None


class YesCcPdfParser(BaseParser):
    """Parses Yes Bank Credit Card PDF e-statements.

    Extraction order (as per SM-C §4):
        1. TEXT_LAYER  — fastest, handles digitally generated e-statements
        2. OCR         — fallback for scanned/printed copies
    """

    source_type = SourceType.YES_BANK_CC
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
        """Dispatch to the correct extraction sub-method."""
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
            logger.warning("YesCcPdfParser.extract failed: %s", exc, exc_info=True)
            return self._make_failed_result(batch_id, method, str(exc))

    # ── Core parsing ──────────────────────────────────────────────────────────

    def parse_text_content(
        self,
        batch_id: str,
        text: str,
        method: ExtractionMethod = ExtractionMethod.TEXT_LAYER,
    ) -> ExtractionResult:
        """Parse Yes Bank CC e-statement text.

        Pure function — unit-testable without real PDF bytes.

        Handles two layout variants produced by different extractors:

        **Inline / single-line** (pdfplumber column merge — used in production):
            DD/MM/YYYY <description> - Ref No: <ref> [Merchant Category] amount.cc Dr|Cr

        **Multi-line** (PyMuPDF / test fixtures):
            DD/MM/YYYY <description> - Ref No: <ref>
            [<merchant category>]
            amount.cc Dr|Cr
        """
        rows: list[RawParsedRow] = []
        errors: list[str] = []

        # ── Statement-level metadata ───────────────────────────────────────
        card_match = _CARD_RE.search(text)
        account_hint = card_match.group(1) if card_match else None

        period_match = _PERIOD_RE.search(text)
        stmt_from = stmt_to = None
        if period_match:
            stmt_from = _dmy_to_iso(period_match.group(1))
            stmt_to = _dmy_to_iso(period_match.group(2))

        # ── First pass: try inline (single-line) format ───────────────────
        # pdfplumber merges all table columns onto one line, so:
        #   "17/02/2026 UPI_BMTC ... Ref No: RT2604... Transportation Services 24.00 Dr"
        inline_rows: list[RawParsedRow] = []
        inline_errors: list[str] = []

        lines = text.splitlines()
        for line_num, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            m = _TXN_INLINE_RE.match(stripped)
            if not m:
                continue
            raw_date = m.group(1)
            narration_raw = m.group(2).strip()
            raw_amount = m.group(3)
            direction = m.group(4).upper()

            ref_match = _REF_RE.search(narration_raw)
            ref_no = ref_match.group(1) if ref_match else None
            narration = _REF_RE.sub("", narration_raw).strip().rstrip("- ").strip()

            raw_debit  = raw_amount if direction == "DR" else None
            raw_credit = raw_amount if direction == "CR" else None

            inline_rows.append(
                RawParsedRow(
                    batch_id=batch_id,
                    source_type=SourceType.YES_BANK_CC,
                    parser_version=self.version,
                    extraction_method=method,
                    raw_date=raw_date,
                    raw_narration=narration,
                    raw_debit=raw_debit,
                    raw_credit=raw_credit,
                    raw_balance=None,
                    raw_reference=ref_no,
                    txn_type_hint=_infer_txn_type(narration),
                    row_number=line_num,
                    row_confidence=0.9,
                )
            )

        if inline_rows:
            rows = inline_rows
            errors = inline_errors
        else:
            # ── Second pass: multi-line block format ───────────────────────
            # Each block starts at a line with DD/MM/YYYY and ends before the next.
            blocks: list[list[str]] = []
            current: list[str] = []

            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue
                if _TXN_DATE_LINE_RE.match(stripped):
                    if current:
                        blocks.append(current)
                    current = [stripped]
                elif current:
                    current.append(stripped)

            if current:
                blocks.append(current)

            for block_num, block in enumerate(blocks, start=1):
                if not block:
                    continue

                first_match = _TXN_DATE_LINE_RE.match(block[0])
                if not first_match:
                    continue

                raw_date = first_match.group(1)
                first_desc = first_match.group(2).strip()

                # Find the amount line scanning from the end
                amount_idx: int | None = None
                for i in range(len(block) - 1, 0, -1):
                    if _AMOUNT_LINE_RE.match(block[i]):
                        amount_idx = i
                        break

                if amount_idx is None:
                    errors.append(f"Block {block_num} ({raw_date}): no amount line — skipped")
                    continue

                amount_match = _AMOUNT_LINE_RE.match(block[amount_idx])
                raw_amount = amount_match.group(1)
                direction = amount_match.group(2).upper()

                middle_lines = [
                    block[i]
                    for i in range(1, amount_idx)
                    if not _is_skip_line(block[i])
                ]

                narration_raw = " ".join([first_desc] + middle_lines).strip()
                ref_match = _REF_RE.search(narration_raw)
                ref_no = ref_match.group(1) if ref_match else None
                narration = _REF_RE.sub("", narration_raw).strip().rstrip("- ").strip()

                raw_debit  = raw_amount if direction == "DR" else None
                raw_credit = raw_amount if direction == "CR" else None

                rows.append(
                    RawParsedRow(
                        batch_id=batch_id,
                        source_type=SourceType.YES_BANK_CC,
                        parser_version=self.version,
                        extraction_method=method,
                        raw_date=raw_date,
                        raw_narration=narration,
                        raw_debit=raw_debit,
                        raw_credit=raw_credit,
                        raw_balance=None,
                        raw_reference=ref_no,
                        txn_type_hint=_infer_txn_type(narration),
                        row_number=block_num,
                        row_confidence=0.9,
                    )
                )

        # ── Compute confidence ────────────────────────────────────────────
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
