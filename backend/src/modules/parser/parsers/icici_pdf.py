"""ICICI Bank PDF parser.

ICICI Bank account statement format:
    Date | Transaction Details | Chq/Ref No. | Value Date | Withdrawal (Dr) | Deposit (Cr) | Balance

Parsing strategy (in priority order):
    1. TABLE_EXTRACTION  — read cells by column index (most reliable)
    2. TEXT_LAYER        — regex over the embedded text
    3. OCR               — last resort (requires Tesseract)

ICICI also exports CSV/XLS — those are handled by GenericCsvParser + ColumnMapping.
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

# ── Text-layer regex ──────────────────────────────────────────────────────────
# Matches transaction rows in the embedded-text layer.  Two sub-formats:
#   Full : Date  Narration  Ref  ValueDate  [Debit]  [Credit]  Balance
#   Short: Date  Narration  [Debit]  [Credit]  Balance  (no ref/value-date)

# Full format (value-date present)
_TXN_ROW_RE = re.compile(
    r"""
    ^(\d{2}[/-]\d{2}[/-]\d{4})  # Txn date  (DD/MM/YYYY or DD-MM-YYYY)
    [ \t]+
    (.+?)                         # Description (non-greedy, single line)
    [ \t]+
    (\S*)                         # Ref/chq  (may be empty)
    [ \t]+
    (\d{2}[/-]\d{2}[/-]\d{4})   # Value date (same line)
    [ \t]+
    ([\d,]+\.\d{2})?              # Withdrawal Dr
    [ \t]*
    ([\d,]+\.\d{2})?              # Deposit Cr
    [ \t]+
    ([\d,]+\.\d{2})               # Balance
    """,
    re.VERBOSE | re.MULTILINE,
)

# Short format (no value-date / ref)
_TXN_ROW_SHORT_RE = re.compile(
    r"""
    ^(\d{2}[/-]\d{2}[/-]\d{4})  # Txn date
    [ \t]+
    (.+?)                         # Description (single line)
    [ \t]+
    ([\d,]+\.\d{2})?              # Withdrawal Dr
    [ \t]*
    ([\d,]+\.\d{2})?              # Deposit Cr
    [ \t]+
    ([\d,]+\.\d{2})               # Balance
    """,
    re.VERBOSE | re.MULTILINE,
)

# Date pattern used as a row anchor for token-based fallback
_DATE_RE = re.compile(r"^\d{2}[/\-.]\d{2}[/\-.]\d{4}$")
_AMOUNT_RE = re.compile(r"^[\d,]+\.\d{2}$")

# ── ICICI OpTransactionHistory PDF column x-boundaries ───────────────────────
# Format: S No. | Transaction Date | Cheque Number | Transaction Remarks
#             | Withdrawal Amount (INR) | Deposit Amount (INR) | Balance (INR)
# Column bounds (x0 thresholds in PDF points, A4 landscape word positions):
_OPT_COL_BOUNDS: list[float] = [19.0, 49.0, 119.0, 189.0, 390.0, 456.0, 522.0, 576.0]
# Col indices:                      0      1      2       3        4         5        6
# 0=sno 1=date 2=cheque 3=remarks 4=withdrawal 5=deposit 6=balance
_OPT_DATE_RE = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")

# Header column keywords — used to locate column indices in table extraction
_DATE_COLS     = {"date", "txn date", "transaction date", "value date"}
_NARR_COLS     = {"transaction details", "particulars", "description", "narration", "remarks"}
_DR_COLS       = {"withdrawal", "withdrawal (dr)", "debit", "dr", "withdrawal amt"}
_CR_COLS       = {"deposit", "deposit (cr)", "credit", "cr", "deposit amt"}
_BAL_COLS      = {"balance", "closing balance", "available balance"}
_REF_COLS      = {"ref", "chq", "reference", "chq/ref no.", "chq no."}

_UPI_RE   = re.compile(r"\bUPI\b",   re.I)
_NEFT_RE  = re.compile(r"\bNEFT\b",  re.I)
_IMPS_RE  = re.compile(r"\bIMPS\b",  re.I)
_ATM_RE   = re.compile(r"\bATM\b",   re.I)
_CHQ_RE   = re.compile(r"\b(CHQ|CHEQUE|CLG|ECS)\b", re.I)


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


class IciciPdfParser(BaseParser):
    """Parses ICICI Bank PDF account statements.

    Priority: TABLE_EXTRACTION (cell-indexed) → TEXT_LAYER (regex) → OCR.
    parse_text_content() and parse_table_rows() are the pure, unit-testable entry points.
    """

    source_type = SourceType.ICICI_BANK
    version = "1.0"
    supported_formats = ["PDF"]

    def __init__(self) -> None:
        self._text_extractor  = TextLayerExtractor()
        self._table_extractor = TableExtractor()
        self._ocr_extractor   = OCRExtractor()

    def supported_methods(self) -> list[ExtractionMethod]:
        # TABLE_EXTRACTION first — cell-indexed parsing is more reliable than text regex
        return [ExtractionMethod.TABLE_EXTRACTION, ExtractionMethod.TEXT_LAYER, ExtractionMethod.OCR]

    def extract(self, batch_id: str, file_bytes: bytes, method: ExtractionMethod) -> ExtractionResult:
        try:
            if method == ExtractionMethod.TABLE_EXTRACTION:
                # 1. Try word-coordinate table parser (handles ICICI OpTransactionHistory format)
                result = self.parse_word_table_pdf(batch_id, file_bytes, method)
                if result.rows:
                    return result

                # 2. Try pdfplumber/camelot table extraction
                tables = self._table_extractor.extract_tables(file_bytes, method="auto")
                if tables:
                    result = self.parse_table_rows(batch_id, tables, method)
                    if result.rows:
                        return result
                # Fall through to text if tables gave nothing

            if method == ExtractionMethod.TEXT_LAYER:
                pages = self._text_extractor.extract_pages(file_bytes)
                text  = "\n".join(pages)
                if not text.strip():
                    return self._make_failed_result(batch_id, method, "No text in PDF.")
                return self.parse_text_content(batch_id, text, method)

            if method == ExtractionMethod.OCR:
                text = self._ocr_extractor.extract_combined(file_bytes)
                if not text.strip():
                    return self._make_failed_result(batch_id, method, "OCR produced no text.")
                return self.parse_text_content(batch_id, text, method)

        except Exception as exc:  # noqa: BLE001
            logger.warning("IciciPdfParser.extract(%s) failed: %s", method.value, exc)
        return self._make_failed_result(batch_id, method, f"{method.value} failed.")

    # ── Word-coordinate table parser (ICICI OpTransactionHistory PDF) ─────────

    def parse_word_table_pdf(
        self,
        batch_id: str,
        file_bytes: bytes,
        method: ExtractionMethod = ExtractionMethod.TABLE_EXTRACTION,
    ) -> ExtractionResult:
        """Parse ICICI 'Statement of Transactions' PDFs using word x-positions.

        The OpTransactionHistory PDF renders a 7-column table using shaded cell
        backgrounds (not drawn borders), so pdfplumber's table extractor only
        picks up the header row.  This method instead uses extract_words() and
        groups each word into a column band based on its x0 co-ordinate.

        Column layout (A4 portrait, points):
            0: S No.            x ∈ [19, 49)
            1: Transaction Date x ∈ [49, 119)
            2: Cheque Number    x ∈ [119, 189)
            3: Transaction Rem. x ∈ [189, 390)
            4: Withdrawal (INR) x ∈ [390, 456)
            5: Deposit (INR)    x ∈ [456, 522)
            6: Balance (INR)    x ∈ [522, 576)

        Each transaction block is anchored by a row whose col-0 cell contains
        a pure integer (the serial number).  Narration text (col-3) may span
        several PDF text lines within the block.
        """
        try:
            import io as _io
            import pdfplumber
        except ImportError:
            return self._make_failed_result(batch_id, method, "pdfplumber not available.")

        def _col(x: float) -> int:
            for i in range(len(_OPT_COL_BOUNDS) - 1):
                if _OPT_COL_BOUNDS[i] <= x < _OPT_COL_BOUNDS[i + 1]:
                    return i
            return -1

        rows: list[RawParsedRow] = []
        errors: list[str] = []

        try:
            with pdfplumber.open(_io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    words = page.extract_words(keep_blank_chars=False)
                    if not words:
                        continue

                    # Map each word to (y_bucket, col_index)
                    from collections import defaultdict
                    by_row: dict[int, dict[int, list[str]]] = defaultdict(lambda: defaultdict(list))
                    for w in words:
                        c = _col(w["x0"])
                        if c >= 0:
                            by_row[round(w["top"])][c].append(w["text"])

                    sorted_ys = sorted(by_row.keys())

                    # Anchors: rows where col-0 contains a plain integer (serial no.)
                    anchors: list[tuple[int, int]] = []
                    for y in sorted_ys:
                        words_c0 = by_row[y][0]
                        if words_c0 and words_c0[0].isdigit():
                            anchors.append((y, int(words_c0[0])))

                    for i, (anchor_y, _sno) in enumerate(anchors):
                        next_y = anchors[i + 1][0] if i + 1 < len(anchors) else sorted_ys[-1] + 1
                        block_ys = [y for y in sorted_ys if anchor_y <= y < next_y]

                        raw_date    = " ".join(by_row[anchor_y][1])
                        raw_cheque  = " ".join(by_row[anchor_y][2]) or None
                        raw_wdraw   = " ".join(by_row[anchor_y][4]) or None
                        raw_dep     = " ".join(by_row[anchor_y][5]) or None
                        raw_bal     = " ".join(by_row[anchor_y][6]) or None

                        # Treat "0.00" as null (ICICI uses it as placeholder)
                        _ZERO = {"0", "0.0", "0.00"}
                        if raw_wdraw in _ZERO:
                            raw_wdraw = None
                        if raw_dep in _ZERO:
                            raw_dep = None

                        if not raw_date or not _OPT_DATE_RE.match(raw_date):
                            continue

                        # Normalise date from DD.MM.YYYY → DD/MM/YYYY
                        raw_date = raw_date.replace(".", "/")

                        # Narration = all col-3 text across the block
                        narr_parts: list[str] = []
                        for y in block_ys:
                            if by_row[y][3]:
                                narr_parts.append(" ".join(by_row[y][3]))
                        narration = " ".join(narr_parts).strip() or "—"

                        has_amount = bool(raw_wdraw or raw_dep)
                        row_num = len(rows) + 1
                        rows.append(RawParsedRow(
                            batch_id=batch_id,
                            source_type=SourceType.ICICI_BANK,
                            parser_version=self.version,
                            extraction_method=method,
                            raw_date=raw_date,
                            raw_narration=narration,
                            raw_reference=raw_cheque,
                            raw_debit=raw_wdraw,
                            raw_credit=raw_dep,
                            raw_balance=raw_bal,
                            txn_type_hint=_infer_txn_type(narration),
                            row_confidence=0.92 if has_amount else 0.5,
                            row_number=row_num,
                        ))
        except Exception as exc:  # noqa: BLE001
            logger.warning("IciciPdfParser.parse_word_table_pdf failed: %s", exc)
            return self._make_failed_result(batch_id, method, f"Word-table parse failed: {exc}")

        return self._make_result(batch_id, rows, errors, None, None, method)

    # ── Table-cell parser (primary path) ──────────────────────────────────────

    def parse_table_rows(
        self,
        batch_id: str,
        tables: list[list[list[str]]],
        method: ExtractionMethod = ExtractionMethod.TABLE_EXTRACTION,
    ) -> ExtractionResult:
        """Parse transaction rows directly from table cells (no text conversion)."""
        rows: list[RawParsedRow] = []
        errors: list[str] = []
        opening: Decimal | None = None
        closing: Decimal | None = None

        for table in tables:
            if not table:
                continue

            # Find header row and map column indices
            col_map = self._find_columns(table)
            if not col_map:
                # No recognisable header — try the text fallback on stringified table
                text_fallback = self._tables_to_text([table])
                fb = self.parse_text_content(batch_id, text_fallback, method)
                if fb.rows:
                    rows.extend(fb.rows)
                continue

            date_i = col_map.get("date", -1)
            narr_i = col_map.get("narr", -1)
            dr_i   = col_map.get("dr",   -1)
            cr_i   = col_map.get("cr",   -1)
            bal_i  = col_map.get("bal",  -1)
            ref_i  = col_map.get("ref",  -1)

            header_row = col_map["_header_row"]
            row_num = 0
            for raw_row in table[header_row + 1:]:
                if not raw_row:
                    continue
                cells = [c.strip() if c else "" for c in raw_row]

                def _cell(i: int) -> str:
                    return cells[i] if 0 <= i < len(cells) else ""

                raw_date = _cell(date_i)
                if not raw_date or not _DATE_RE.match(raw_date.split()[0]):
                    # Try to detect opening/closing balance rows
                    row_text = " ".join(cells)
                    if m := _OPENING_RE.search(row_text):
                        opening = _clean_amount(m.group(1))
                    if m := _CLOSING_RE.search(row_text):
                        closing = _clean_amount(m.group(1))
                    continue

                raw_debit  = _cell(dr_i)  or None
                raw_credit = _cell(cr_i)  or None
                raw_bal    = _cell(bal_i) or None
                raw_ref    = _cell(ref_i) or None
                narration  = _cell(narr_i)

                has_amount = bool(raw_debit or raw_credit)
                if not has_amount:
                    errors.append(f"Row {row_num + 1}: no debit or credit amount")

                rows.append(RawParsedRow(
                    batch_id=batch_id,
                    source_type=SourceType.ICICI_BANK,
                    parser_version=self.version,
                    extraction_method=method,
                    raw_date=raw_date,
                    raw_narration=narration,
                    raw_reference=raw_ref,
                    raw_debit=raw_debit,
                    raw_credit=raw_credit,
                    raw_balance=raw_bal,
                    txn_type_hint=_infer_txn_type(narration),
                    row_confidence=0.92 if has_amount else 0.5,
                    row_number=row_num + 1,
                ))
                row_num += 1

        return self._make_result(batch_id, rows, errors, opening, closing, method)

    # ── Text-layer / OCR parser ────────────────────────────────────────────────

    # ── Pure function — unit-testable ─────────────────────────────────────────

    def parse_text_content(
        self,
        batch_id: str,
        text: str,
        method: ExtractionMethod = ExtractionMethod.TEXT_LAYER,
    ) -> ExtractionResult:
        """Parse rows from embedded text or OCR output using regex + token fallback."""
        rows: list[RawParsedRow] = []
        errors: list[str] = []
        opening = _clean_amount(m.group(1)) if (m := _OPENING_RE.search(text)) else None
        closing = _clean_amount(m.group(1)) if (m := _CLOSING_RE.search(text)) else None

        # Try full regex (with value-date)
        for row_num, match in enumerate(_TXN_ROW_RE.finditer(text), start=1):
            raw_debit  = match.group(5) or None
            raw_credit = match.group(6) or None
            has_amount = bool(raw_debit or raw_credit)
            if not has_amount:
                errors.append(f"Row {row_num}: no debit or credit amount")
            rows.append(RawParsedRow(
                batch_id=batch_id,
                source_type=SourceType.ICICI_BANK,
                parser_version=self.version,
                extraction_method=method,
                raw_date=match.group(1),
                raw_narration=match.group(2).strip(),
                raw_reference=match.group(3).strip() or None,
                raw_debit=raw_debit,
                raw_credit=raw_credit,
                raw_balance=match.group(7),
                txn_type_hint=_infer_txn_type(match.group(2)),
                row_confidence=0.88 if has_amount else 0.5,
                row_number=row_num,
            ))

        # Try short regex (no value-date / ref) if full matched nothing
        if not rows:
            for row_num, match in enumerate(_TXN_ROW_SHORT_RE.finditer(text), start=1):
                raw_debit  = match.group(3) or None
                raw_credit = match.group(4) or None
                has_amount = bool(raw_debit or raw_credit)
                if not has_amount:
                    errors.append(f"Row {row_num}: no debit or credit amount")
                rows.append(RawParsedRow(
                    batch_id=batch_id,
                    source_type=SourceType.ICICI_BANK,
                    parser_version=self.version,
                    extraction_method=method,
                    raw_date=match.group(1),
                    raw_narration=match.group(2).strip(),
                    raw_debit=raw_debit,
                    raw_credit=raw_credit,
                    raw_balance=match.group(5),
                    txn_type_hint=_infer_txn_type(match.group(2)),
                    row_confidence=0.80 if has_amount else 0.5,
                    row_number=row_num,
                ))

        # Token-based fallback: always run; use it if it finds more amount-bearing rows
        # (handles multi-line transactions where narration is on the preceding line)
        token_rows, token_errors = self._token_parse(batch_id, text, method)
        regex_amount_count = sum(1 for r in rows if r.raw_debit or r.raw_credit)
        token_amount_count = sum(1 for r in token_rows if r.raw_debit or r.raw_credit)
        if token_amount_count > regex_amount_count:
            rows, errors = token_rows, token_errors

        return self._make_result(batch_id, rows, errors, opening, closing, method)

    # ── Token-based fallback ──────────────────────────────────────────────────

    def _token_parse(
        self,
        batch_id: str,
        text: str,
        method: ExtractionMethod,
    ) -> tuple[list[RawParsedRow], list[str]]:
        """Multi-line-aware scanner for ICICI text-layer PDFs.

        ICICI statements spread each transaction over 2-3 lines:
            MODE/NEFT/narration-part-1              ← pre-narration (no date)
            DD-MM-YYYY  [inline-narr]  AMT  BAL     ← key line (date + amounts)
            ref-continuation                        ← post-ref (first line only)

        Direction (DR/CR) is determined by comparing balance to the previous row:
            balance decreased → withdrawal / DR
            balance increased → deposit   / CR
        """
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

        # ── Pass 1: tag key lines ─────────────────────────────────────────────
        key: list[tuple[int, str, list[str], list[str]]] = []
        for i, line in enumerate(lines):
            tokens = line.split()
            if not tokens or not _DATE_RE.match(tokens[0]):
                continue
            amounts: list[str] = []
            rest = tokens[1:]
            while rest and _AMOUNT_RE.match(rest[-1].replace(",", "")):
                amounts.insert(0, rest.pop())
            if amounts:
                key.append((i, tokens[0], amounts, rest))

        # ── Pass 2: build rows ────────────────────────────────────────────────
        rows: list[RawParsedRow] = []
        errors: list[str] = []
        prev_balance: Decimal | None = None

        for seq, (line_idx, raw_date, amounts, inline_tokens) in enumerate(key):
            prev_key_idx = key[seq - 1][0] if seq > 0 else -1
            next_key_idx = key[seq + 1][0] if seq + 1 < len(key) else len(lines)

            # Narration = last non-key line BEFORE this key + inline + first non-key line AFTER
            pre_lines  = lines[prev_key_idx + 1 : line_idx]
            post_lines = lines[line_idx + 1 : next_key_idx]
            pre_narr   = pre_lines[-1].strip() if pre_lines else ""
            inline     = " ".join(inline_tokens).strip()
            post_narr  = post_lines[0].strip() if post_lines else ""
            parts      = [p for p in (pre_narr, inline, post_narr) if p]
            narration  = " | ".join(parts) if parts else "—"

            raw_balance = amounts[-1]
            curr_balance = _clean_amount(raw_balance)

            raw_debit: str | None = None
            raw_credit: str | None = None

            if len(amounts) >= 2:
                txn_amount = amounts[-2]
                if prev_balance is not None and curr_balance is not None:
                    if curr_balance < prev_balance:
                        raw_debit  = txn_amount   # balance fell → withdrawal
                    elif curr_balance > prev_balance:
                        raw_credit = txn_amount   # balance rose → deposit
                    else:
                        raw_debit  = txn_amount   # unchanged → treat as debit
                else:
                    raw_debit = txn_amount          # no prev to compare → fallback

            if curr_balance is not None:
                prev_balance = curr_balance

            # Skip opening-balance marker lines (no transaction amount)
            if not raw_debit and not raw_credit:
                continue

            row_num = len(rows) + 1
            rows.append(RawParsedRow(
                batch_id=batch_id,
                source_type=SourceType.ICICI_BANK,
                parser_version=self.version,
                extraction_method=method,
                raw_date=raw_date,
                raw_narration=narration,
                raw_debit=raw_debit,
                raw_credit=raw_credit,
                raw_balance=raw_balance,
                txn_type_hint=_infer_txn_type(narration),
                row_confidence=0.72,
                row_number=row_num,
            ))
        return rows, errors

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _find_columns(table: list[list[str]]) -> dict | None:
        """Scan the first few rows to find the header and build a column-index map."""
        for row_idx, row in enumerate(table[:6]):
            low = [str(c).strip().lower() if c else "" for c in row]
            date_i = next((i for i, h in enumerate(low) if h in _DATE_COLS), -1)
            narr_i = next((i for i, h in enumerate(low) if h in _NARR_COLS), -1)
            bal_i  = next((i for i, h in enumerate(low) if h in _BAL_COLS),  -1)
            if date_i >= 0 and narr_i >= 0 and bal_i >= 0:
                dr_i  = next((i for i, h in enumerate(low) if h in _DR_COLS),  -1)
                cr_i  = next((i for i, h in enumerate(low) if h in _CR_COLS),  -1)
                ref_i = next((i for i, h in enumerate(low) if h in _REF_COLS), -1)
                return {
                    "date": date_i, "narr": narr_i, "dr": dr_i,
                    "cr": cr_i, "bal": bal_i, "ref": ref_i,
                    "_header_row": row_idx,
                }
        return None

    def _make_result(
        self,
        batch_id: str,
        rows: list[RawParsedRow],
        errors: list[str],
        opening: Decimal | None,
        closing: Decimal | None,
        method: ExtractionMethod,
    ) -> ExtractionResult:
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

    @staticmethod
    def _tables_to_text(tables: list[list[list[str]]]) -> str:
        """Convert table data to space-separated text (last-resort text fallback)."""
        lines: list[str] = []
        for table in tables:
            for row in table:
                lines.append("  ".join(cell.strip() for cell in row if cell))
        return "\n".join(lines)
