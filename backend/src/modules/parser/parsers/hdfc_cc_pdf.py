"""HDFC Bank Credit Card PDF parser.

Supports all HDFC CC variants: Millennia, Regalia, MoneyBack, RuPay, etc.

Column layout (pdfplumber, columns merged onto single lines):
    DD/MM/YYYY| HH:MM  <Description>  [+ ]C  amount  [PI]

Amount notation:
    "C 1,004.00"     → debit  (purchase / charge)
    "+ C 15,336.00"  → credit (payment / refund / reversal)

The "C" character is the rupee symbol ₹ as rendered by the PDF's embedded font.

The PI (Purchase Indicator / Insights) column is a single glyph at the end of
each line — it is ignored.

Metadata extracted:
    Billing Period  : "23 Feb, 2026 - 22 Mar, 2026"
    Credit Card No. : "434155XXXXXX6424"
"""

from __future__ import annotations

import logging
import re

from core.models.enums import ExtractionMethod, SourceType, TxnTypeHint
from core.models.raw_parsed_row import ParseMetadata, RawParsedRow
from core.utils.confidence import ConfidenceSignals, compute_confidence
from modules.parser.base import BaseParser, ExtractionResult
from modules.parser.extraction.ocr import OCRExtractor
from modules.parser.extraction.text_layer import TextLayerExtractor

logger = logging.getLogger(__name__)

# ── Regexes ───────────────────────────────────────────────────────────────────

# Primary: pdfplumber / text-layer inline format
#   DD/MM/YYYY| HH:MM  DESCRIPTION  [+ ]C  amount  [anything]
_TXN_INLINE_RE = re.compile(
    r"^(\d{2}/\d{2}/\d{4})\|\s*\d{2}:\d{2}\s+"   # date | time
    r"(.+?)\s+"                                     # description (lazy)
    r"(\+\s*)?"                                     # optional '+' → credit
    r"[C₹]\s*"                                      # currency glyph
    r"([\d,]+\.\d{2})"                              # amount
    r"(?:\s+\S+)?\s*$",                             # optional PI glyph + EOL
)

# Reference number embedded in description: "(Ref# ST260560083000010263758)"
_REF_RE = re.compile(r"\(Ref#\s*(\S+?)\)", re.I)

# Billing period: "Billing Period 23 Feb, 2026 - 22 Mar, 2026"
# or "Statement Date 22 Mar, 2026"  /  "23 Feb, 2026 - 22 Mar, 2026"
_PERIOD_RE = re.compile(
    r"Billing Period\s+"
    r"(\d{1,2}\s+\w+,?\s*\d{4})"
    r"\s*[-–]\s*"
    r"(\d{1,2}\s+\w+,?\s*\d{4})",
    re.I,
)

# Card number: "Credit Card No. 434155XXXXXX6424" — prefix may be 4–6 digits
_CARD_RE = re.compile(r"Credit Card No\.?\s+(\d{4,}[X*]+\d{4,})", re.I)

# Header line to skip
_HEADER_LINE_RE = re.compile(
    r"^DATE\s*&\s*TIME\s+TRANSACTION|^Offers on your card|^Domestic Trans|"
    r"^International Trans|^Benefits on your|^Important Inform|^Rewards Program",
    re.I,
)

# TxnTypeHint detection from description
_UPI_RE  = re.compile(r"\bUPI[/_]?",  re.I)
_NEFT_RE = re.compile(r"\bNEFT\b",   re.I)
_IMPS_RE = re.compile(r"\bIMPS\b",   re.I)
_ATM_RE  = re.compile(r"\bATM\b",    re.I)
_CHQ_RE  = re.compile(r"\b(CHQ|CHEQUE|CLG|ECS)\b", re.I)

_MONTHS = {
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "may": "05", "jun": "06", "jul": "07", "aug": "08",
    "sep": "09", "oct": "10", "nov": "11", "dec": "12",
}


def _parse_billing_date(s: str) -> str | None:
    """Convert '23 Feb, 2026' → '2026-02-23'."""
    m = re.match(r"(\d{1,2})\s+(\w+),?\s*(\d{4})", s.strip(), re.I)
    if not m:
        return None
    month = _MONTHS.get(m.group(2).lower()[:3])
    if not month:
        return None
    return f"{m.group(3)}-{month}-{int(m.group(1)):02d}"


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


class HdfcCcPdfParser(BaseParser):
    """Parses HDFC Bank Credit Card PDF e-statements.

    Extraction order:
        1. TEXT_LAYER  — works for digitally-generated PDFs
        2. OCR         — fallback for printed / scanned copies

    Handles all HDFC CC variants: Millennia, Regalia, MoneyBack, Diners, etc.
    """

    source_type = SourceType.HDFC_BANK_CC
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
            logger.warning("HdfcCcPdfParser.extract failed: %s", exc, exc_info=True)
            return self._make_failed_result(batch_id, method, str(exc))

    # ── Core parsing ──────────────────────────────────────────────────────────

    def parse_text_content(
        self,
        batch_id: str,
        text: str,
        method: ExtractionMethod = ExtractionMethod.TEXT_LAYER,
    ) -> ExtractionResult:
        """Parse HDFC Bank CC e-statement text.

        Pure function — unit-testable without real PDF bytes.

        Each transaction line (pdfplumber inline format):
            DD/MM/YYYY| HH:MM  DESCRIPTION  [+ ]C amount  [PI]
        """
        rows: list[RawParsedRow] = []
        errors: list[str] = []

        # ── Statement metadata ────────────────────────────────────────────────
        card_match = _CARD_RE.search(text)
        account_hint = card_match.group(1) if card_match else None

        stmt_from = stmt_to = None
        pm = _PERIOD_RE.search(text)
        if pm:
            stmt_from = _parse_billing_date(pm.group(1))
            stmt_to   = _parse_billing_date(pm.group(2))

        # ── Transaction parsing ───────────────────────────────────────────────
        for line_num, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            if _HEADER_LINE_RE.match(stripped):
                continue

            m = _TXN_INLINE_RE.match(stripped)
            if not m:
                continue

            raw_date   = m.group(1)
            desc_raw   = m.group(2).strip()
            is_credit  = m.group(3) is not None   # '+' present
            raw_amt    = m.group(4)

            # Extract reference from description, then strip it
            ref_m = _REF_RE.search(desc_raw)
            raw_reference = ref_m.group(1) if ref_m else None
            desc_clean = _REF_RE.sub("", desc_raw).strip(" -")

            raw_debit  = raw_amt if not is_credit else None
            raw_credit = raw_amt if is_credit     else None

            rows.append(
                RawParsedRow(
                    batch_id=batch_id,
                    source_type=SourceType.HDFC_BANK_CC,
                    parser_version=self.version,
                    extraction_method=method,
                    raw_date=raw_date,
                    raw_narration=desc_clean,
                    raw_debit=raw_debit,
                    raw_credit=raw_credit,
                    raw_balance=None,          # CC statement — no per-row balance
                    raw_reference=raw_reference,
                    txn_type_hint=_infer_txn_type(desc_clean),
                    row_number=line_num,
                    row_confidence=0.9,
                )
            )

        # ── Confidence ────────────────────────────────────────────────────────
        all_have_date   = all(r.raw_date for r in rows)
        all_have_amount = all(r.raw_debit or r.raw_credit for r in rows)

        signals = ConfidenceSignals(
            balance_cross_check_passed=None,
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
