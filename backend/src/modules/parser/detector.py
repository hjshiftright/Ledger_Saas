"""SourceDetector — infers SourceType from filename + file content fingerprint.

Returns a (SourceType, confidence) pair. Confidence < 0.70 means detection
is ambiguous and the caller should ask the user for source_type_hint.

Spec reference: SM-K §3.1 and SM-B source detection.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from core.models.enums import FileFormat, SourceType

logger = logging.getLogger(__name__)

DETECTION_THRESHOLD: float = 0.70


@dataclass
class DetectionResult:
    source_type: SourceType
    confidence: float
    method: str   # "filename" | "content" | "header_scan" | "hint"
    file_format: FileFormat


# ── PDF-flavour → CSV-flavour source type remap ─────────────────────────────
# When the file's actual format (determined by magic bytes) is XLS / XLSX / CSV
# but the filename pattern matched a PDF-only SourceType, remap to the CSV
# counterpart so GenericCsvParser is selected instead of the PDF parser.
_PDF_TO_CSV_REMAP: dict[SourceType, SourceType] = {
    SourceType.HDFC_BANK:   SourceType.HDFC_BANK_CSV,
    SourceType.SBI_BANK:    SourceType.SBI_BANK_CSV,
    SourceType.ICICI_BANK:  SourceType.ICICI_BANK_CSV,
    SourceType.AXIS_BANK:   SourceType.AXIS_BANK_CSV,
    SourceType.KOTAK_BANK:  SourceType.KOTAK_BANK_CSV,
    SourceType.IDFC_BANK:   SourceType.IDFC_BANK_CSV,
    SourceType.UNION_BANK:  SourceType.UNION_BANK_CSV,
}

# ── Filename keyword patterns ─────────────────────────────────────────────────
# Each entry: (regex_pattern, SourceType, base_confidence)
_FILENAME_PATTERNS: list[tuple[re.Pattern[str], SourceType, float]] = [
    # ── Bank patterns ─────────────────────────────────────────────────────────
    (re.compile(r"hdfc.*cc|hdfccc|hdfc.*credit.*card|hdfc.*creditcard", re.I), SourceType.HDFC_BANK_CC, 0.87),
    (re.compile(r"hdfc", re.I), SourceType.HDFC_BANK, 0.85),
    (re.compile(r"acct\s*statement", re.I), SourceType.HDFC_BANK, 0.80),
    (re.compile(r"sbi.*stmt|sbi.*acc|sbionline", re.I), SourceType.SBI_BANK, 0.85),
    (re.compile(r"accountstatement.*\d{8}_\d{6}", re.I), SourceType.SBI_BANK, 0.87),
    (re.compile(r"icici.*cc|icic-cc|icici.*credit", re.I), SourceType.ICICI_BANK_CC, 0.85),
    (re.compile(r"icici.*stmt|icici.*acc|icicibank|icici", re.I), SourceType.ICICI_BANK, 0.85),
    (re.compile(r"axis.*stmt|axis.*acc|axisbank", re.I), SourceType.AXIS_BANK, 0.80),
    (re.compile(r"kotak.*stmt|kotakbank", re.I), SourceType.KOTAK_BANK, 0.80),
    (re.compile(r"indusind|induslnd", re.I), SourceType.INDUSIND_BANK, 0.80),
    (re.compile(r"idfc.*first|idfcbank", re.I), SourceType.IDFC_BANK, 0.80),
    (re.compile(r"union.*bank|unionbank|ubi.*stmt|ubi.*acc|OpTransaction.*UX", re.I), SourceType.UNION_BANK, 0.85),
    (re.compile(r"yes.*cc|yes.*credit|yes-cc", re.I), SourceType.YES_BANK_CC, 0.85),
    # ── CAMS / KFintech / MF Central ─────────────────────────────────────────
    (re.compile(r"cas.*cams|cams.*cas|camsonline", re.I), SourceType.CAS_CAMS, 0.90),
    # CAMSonline transaction PDF: e.g. FEB2026_AA30408065_TXN.pdf
    (re.compile(r"[A-Z]{3}\d{4}_[A-Z0-9]+_TXN", re.I), SourceType.CAS_CAMS, 0.88),
    (re.compile(r"cas.*kfin|kfin.*cas|kfintech", re.I), SourceType.CAS_KFINTECH, 0.90),
    (re.compile(r"mf.?central|mfcentral", re.I), SourceType.CAS_MF_CENTRAL, 0.90),
    # ── Zerodha ───────────────────────────────────────────────────────────────
    (re.compile(r"zerodha.*tradebook", re.I), SourceType.ZERODHA_TRADEBOOK, 0.85),
    (re.compile(r"zerodha.*holding", re.I), SourceType.ZERODHA_HOLDINGS, 0.85),
    (re.compile(r"zerodha.*capital.*gain", re.I), SourceType.ZERODHA_CAPITAL_GAINS, 0.85),
    # Matches: zerodha*pnl, zerodha*p&l, taxpnl-* (Zerodha Tax P&L export)
    (re.compile(r"zerodha.*p.?&.?l|zerodha.*pnl|zerodha.*tax|^taxpnl", re.I), SourceType.ZERODHA_TAX_PNL, 0.90),
]

# ── PDF content keyword signatures ───────────────────────────────────────────
# Text to look for in the first ~4KB of extracted PDF text.
# Matching is case-insensitive (see _scan_pdf_content).
_PDF_CONTENT_SIGNATURES: list[tuple[list[str], SourceType, float]] = [
    # ── Bank PDF signatures ───────────────────────────────────────────────────
    (["HDFC Bank Credit Cards", "Credit Card No.", "Billing Period"], SourceType.HDFC_BANK_CC, 0.97),
    (["HDFC Bank Credit Cards", "TOTAL AMOUNT DUE", "Credit Card No."], SourceType.HDFC_BANK_CC, 0.95),
    (["HDFC Bank Credit Cards", "Minimum Amount Due", "Due Date"], SourceType.HDFC_BANK_CC, 0.93),
    (["HDFC Bank Credit Cards", "Billing Period"], SourceType.HDFC_BANK_CC, 0.90),
    (["HDFC Bank", "Withdrawal Amt", "Deposit Amt"], SourceType.HDFC_BANK, 0.92),
    (["HDFC Bank", "IFSC Code"], SourceType.HDFC_BANK, 0.82),
    (["Date", "Narration", "Chq./Ref.No.", "Value Dt", "Withdrawal Amt.", "Closing Balance"], SourceType.HDFC_BANK, 0.95),
    (["WithdrawalAmt.", "DepositAmt.", "ClosingBalance"], SourceType.HDFC_BANK, 0.93),
    (["Statementofaccount", "RTGS/NEFTIFSC"], SourceType.HDFC_BANK, 0.90),
    (["HDFCBANKLTD", "Statementofaccount"], SourceType.HDFC_BANK, 0.88),
    (["HDFCBANKLTD", "WithdrawalAmt."], SourceType.HDFC_BANK, 0.88),
    (["State Bank of India", "Debit", "Credit"], SourceType.SBI_BANK, 0.90),
    (["Txn Date", "Value Date", "Debit", "Credit", "Balance"], SourceType.SBI_BANK, 0.88),
    (["Txn Date", "Debit", "Credit", "Balance"], SourceType.SBI_BANK, 0.85),
    (["State Bank of India", "Balance"], SourceType.SBI_BANK, 0.82),
    (["ICICI Bank", "Withdrawal", "Deposit"], SourceType.ICICI_BANK, 0.90),
    (["ICICI BANK", "Withdrawal", "Deposit"], SourceType.ICICI_BANK, 0.88),
    (["ICICI BANK", "Transaction Remarks"], SourceType.ICICI_BANK, 0.85),
    (["Axis Bank", "DR", "CR"], SourceType.AXIS_BANK, 0.85),
    (["Kotak Mahindra Bank"], SourceType.KOTAK_BANK, 0.85),
    (["IndusInd Bank"], SourceType.INDUSIND_BANK, 0.85),
    (["IDFC FIRST Bank", "IDFC First Bank"], SourceType.IDFC_BANK, 0.85),
    (["Union Bank of India", "Withdrawals", "Deposits"], SourceType.UNION_BANK, 0.94),
    (["Union Bank of India", "Debit", "Credit"], SourceType.UNION_BANK, 0.92),
    (["Union Bank of India"], SourceType.UNION_BANK, 0.82),
    (["YES BANK", "Credit Card Statement", "Amount (Rs.)"], SourceType.YES_BANK_CC, 0.95),
    (["YES BANK", "Card Number", "Total Amount Due"], SourceType.YES_BANK_CC, 0.92),
    (["YES BANK", "Statement Period", "Minimum Amount Due"], SourceType.YES_BANK_CC, 0.90),
    (["ICICI Bank Credit Card", "CREDIT CARD STATEMENT"], SourceType.ICICI_BANK_CC, 0.95),
    (["ICICI Bank Credit Card", "SerNo."], SourceType.ICICI_BANK_CC, 0.92),
    (["CREDIT CARD STATEMENT", "SerNo.", "Statement period"], SourceType.ICICI_BANK_CC, 0.90),
    # ── CAMS / KFintech / MF Central ─────────────────────────────────────────
    # CAS (Consolidated Account Statement) — standard CAMS/KFintech CAS PDF
    (["CAMS", "Consolidated Account Statement", "Folio No"], SourceType.CAS_CAMS, 0.97),
    # CAMSonline transaction / account statement PDFs (not CAS)
    (["CAMS", "Statement of Account", "Folio"], SourceType.CAS_CAMS, 0.93),
    (["CAMS", "Account Statement", "Folio"], SourceType.CAS_CAMS, 0.92),
    (["Computer Age Management", "Folio"], SourceType.CAS_CAMS, 0.92),
    (["camsonline.com", "Folio"], SourceType.CAS_CAMS, 0.90),
    # Broader fallback: any PDF mentioning CAMS + transaction keywords
    (["CAMS", "Transaction", "Units"], SourceType.CAS_CAMS, 0.88),
    (["CAMS", "NAV", "Folio"], SourceType.CAS_CAMS, 0.88),
    (["KFin", "Consolidated Account Statement"], SourceType.CAS_KFINTECH, 0.95),
    (["KFin", "Statement of Account", "Folio"], SourceType.CAS_KFINTECH, 0.92),
    (["MF Central", "Consolidated Account Statement"], SourceType.CAS_MF_CENTRAL, 0.95),
]

# ── CSV / XLS header signatures ───────────────────────────────────────────────
# Set of column names that uniquely identify a CSV or XLS/XLSX file.
_CSV_HEADER_SIGNATURES: list[tuple[set[str], SourceType, float]] = [
    # ── Bank CSV/XLS signatures ───────────────────────────────────────────────
    ({"Date", "Narration", "Value Dt", "Withdrawal Amt (Dr)", "Deposit Amt (Cr)"}, SourceType.HDFC_BANK_CSV, 0.95),
    ({"Date", "Narration", "Value Dt", "Withdrawal Amt.", "Deposit Amt.", "Closing Balance"}, SourceType.HDFC_BANK_CSV, 0.95),
    ({"Txn Date", "Description", "Debit", "Credit", "Balance"}, SourceType.SBI_BANK_CSV, 0.90),
    ({"Date", "Details", "Ref No/Cheque No", "Debit", "Credit", "Balance"}, SourceType.SBI_BANK_CSV, 0.92),
    ({"Transaction Date", "Transaction Remarks", "Withdrawal Amount (INR )", "Deposit Amount (INR )", "Balance (INR )"}, SourceType.ICICI_BANK_CSV, 0.95),
    ({"Transaction Date", "Transaction Remarks", "Withdrawal Amount (INR)", "Deposit Amount (INR)", "Balance (INR)"}, SourceType.ICICI_BANK_CSV, 0.92),
    ({"Transaction Date", "Transaction Remarks", "Withdrawal Amount(INR)", "Deposit Amount(INR)", "Balance(INR)"}, SourceType.ICICI_BANK_CSV, 0.95),
    ({"Tran Date", "PARTICULARS", "Chq No.", "Debit", "Credit", "Balance"}, SourceType.AXIS_BANK_CSV, 0.92),
    ({"Transaction Date", "Description", "Chq/Ref Number", "Debit", "Credit", "Balance"}, SourceType.KOTAK_BANK_CSV, 0.92),
    ({"Transaction Date", "Transaction Details", "Reference No.", "Debit", "Credit", "Balance"}, SourceType.IDFC_BANK_CSV, 0.92),
    ({"Date", "Particulars", "Chq/Ref No.", "Debit", "Credit", "Balance"}, SourceType.UNION_BANK_CSV, 0.92),
    ({"Tran Date", "Particulars", "Reference No", "Debit", "Credit", "Balance"}, SourceType.UNION_BANK_CSV, 0.90),
    # Union Bank UX3 XLS: OpTransactionHistoryUX3_XLS format
    ({"Date", "Tran Id", "Remarks", "UTR Number", "Withdrawals", "Deposits", "Balance"}, SourceType.UNION_BANK_CSV, 0.95),
    # ── Zerodha — only Tax P&L ────────────────────────────────────────────────
    # Tax P&L XLSX — first sheet "Tradewise Exits" header row
    ({"Symbol", "ISIN", "Entry Date", "Exit Date", "Quantity", "Buy Value", "Sell Value"}, SourceType.ZERODHA_TAX_PNL, 0.95),
]


class SourceDetector:
    """Determines the SourceType of a document from its filename and/or content.

    Detection priority:
        1. `source_type_hint` (caller override) → confidence 1.0
        2. File content scan  (PDF text keywords OR spreadsheet/CSV column headers)
        3. Filename pattern matching (fallback when content scan is inconclusive)
        4. UNKNOWN at confidence 0.0
    """

    def detect(
        self,
        filename: str,
        file_bytes: bytes,
        source_type_hint: str | None = None,
    ) -> DetectionResult:
        """Run detection and return the best candidate.

        Args:
            filename: Original filename including extension.
            file_bytes: Raw file bytes (used for content scan).
            source_type_hint: Optional caller override (e.g. "HDFC_BANK").

        Returns:
            DetectionResult with source_type, confidence, method, file_format.
        """
        fmt = self._infer_format(filename, file_bytes)

        # 1. Caller-supplied hint wins unconditionally — but remap PDF-flavour
        #    types to CSV-parser variants when the actual file is a spreadsheet.
        if source_type_hint:
            st = self._parse_hint(source_type_hint)
            if fmt in (FileFormat.XLS, FileFormat.XLSX, FileFormat.CSV):
                st = _PDF_TO_CSV_REMAP.get(st, st)
            return DetectionResult(st, 1.0, "hint", fmt)

        # 2. Content scan — always the primary signal.
        #    For PDF: extract text and match keyword signatures.
        #    For CSV/XLS/XLSX: read the actual column headers via the spreadsheet
        #    engine so binary formats are handled correctly.
        content_result = self._detect_from_content(file_bytes, fmt)
        if content_result and content_result.confidence >= DETECTION_THRESHOLD:
            return content_result

        # 3. Filename pattern matching — fallback when content is ambiguous.
        filename_result = self._detect_from_filename(filename, fmt)
        if filename_result and filename_result.confidence >= DETECTION_THRESHOLD:
            return filename_result

        # Return best of what we have (may be below threshold)
        best = max(
            [r for r in (content_result, filename_result) if r is not None],
            key=lambda r: r.confidence,
            default=None,
        )
        return best or DetectionResult(SourceType.UNKNOWN, 0.0, "none", fmt)

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _infer_format(filename: str, file_bytes: bytes | None = None) -> FileFormat:
        # Magic bytes take precedence over the extension — handles mislabelled files
        # (e.g. an HDFC XLS netbanking export saved/renamed as .pdf).
        #   OLE2/CFBF container (XLS, DOC …): D0 CF 11 E0
        #   ZIP container (XLSX, DOCX …):      PK 03 04
        #   PDF (may have UTF-8 BOM prefix):   %PDF
        if file_bytes and len(file_bytes) >= 4:
            magic = file_bytes[:4]
            if magic == b"\xD0\xCF\x11\xE0":
                return FileFormat.XLS
            if magic[:2] == b"PK":
                return FileFormat.XLSX
            if file_bytes[:5].lstrip(b"\xef\xbb\xbf").startswith(b"%PDF"):
                return FileFormat.PDF
        ext = filename.rsplit(".", 1)[-1].upper()
        mapping = {"PDF": FileFormat.PDF, "CSV": FileFormat.CSV, "XLS": FileFormat.XLS, "XLSX": FileFormat.XLSX}
        return mapping.get(ext, FileFormat.CSV)

    @staticmethod
    def _parse_hint(hint: str) -> SourceType:
        try:
            return SourceType(hint.upper())
        except ValueError:
            logger.warning("Unknown source_type_hint '%s'; defaulting to UNKNOWN.", hint)
            return SourceType.UNKNOWN

    @staticmethod
    def _detect_from_filename(filename: str, fmt: FileFormat) -> DetectionResult | None:
        name = filename.lower()
        for pattern, source_type, confidence in _FILENAME_PATTERNS:
            if pattern.search(name):
                # If the actual file format is XLS / XLSX / CSV, remap the
                # PDF-flavour SourceType to its CSV-parser counterpart so
                # GenericCsvParser is dispatched instead of the PDF parser.
                if fmt in (FileFormat.XLS, FileFormat.XLSX, FileFormat.CSV):
                    source_type = _PDF_TO_CSV_REMAP.get(source_type, source_type)
                return DetectionResult(source_type, confidence, "filename", fmt)
        return None

    @staticmethod
    def _detect_from_content(file_bytes: bytes, fmt: FileFormat) -> DetectionResult | None:
        if fmt == FileFormat.PDF:
            return SourceDetector._scan_pdf_content(file_bytes, fmt)
        return SourceDetector._scan_csv_headers(file_bytes, fmt)

    @staticmethod
    def _scan_pdf_content(file_bytes: bytes, fmt: FileFormat) -> DetectionResult | None:
        """Check PDF text (and table cells) for known bank keyword signatures.

        Scans up to 5 pages so that multi-page preambles (cover page, summary,
        relationship page) don't prevent detection of keywords that appear in
        the transaction table header on later pages.

        If the text layer is sparse (< 200 chars — e.g. old SBI table-only PDFs
        where pdfplumber's extract_text() yields little), table cell content is
        appended to the sample so column-header keywords ("Txn Date", "Debit" …)
        can still be matched.
        """
        sample = ""
        try:
            from core.utils.pdf_utils import extract_text_per_page

            pages = extract_text_per_page(file_bytes, max_pages=5)
            sample = " ".join(pages)
        except Exception:  # noqa: BLE001
            # Not a valid PDF (e.g. in tests bytes are plain text) — decode directly
            sample = file_bytes.decode("utf-8", errors="ignore")

        # Supplement with table-cell text when the text layer is sparse.
        # Some SBI old-format PDFs are table-heavy; pdfplumber's extract_text()
        # may return very little while extract_tables() gives clean column headers.
        if len(sample.strip()) < 200:
            try:
                from core.utils.pdf_utils import extract_tables_per_page  # noqa: PLC0415
                for page_tables in extract_tables_per_page(file_bytes)[:3]:
                    for tbl in page_tables:
                        for row in tbl:
                            sample += " " + " ".join(c or "" for c in row)
            except Exception:  # noqa: BLE001
                pass

        if not sample.strip():
            return None

        best_confidence = 0.0
        best_type: SourceType | None = None
        # Case-insensitive matching so "STATE BANK OF INDIA" matches "State Bank of India", etc.
        sample_lower = sample.lower()
        for keywords, source_type, confidence in _PDF_CONTENT_SIGNATURES:
            # All keywords must be present (case-insensitive)
            if all(kw.lower() in sample_lower for kw in keywords):
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_type = source_type

        if best_type:
            return DetectionResult(best_type, best_confidence, "content", fmt)
        return None

    @staticmethod
    def _scan_csv_headers(file_bytes: bytes, fmt: FileFormat) -> DetectionResult | None:
        """Read column headers from CSV, XLS, or XLSX and match known signatures.

        For XLS/XLSX the raw bytes are binary — we must use the spreadsheet engine
        to extract headers rather than trying to decode them as text.
        For CSV we try UTF-8 then latin-1 line-based parsing.
        """
        headers = SourceDetector._extract_headers(file_bytes, fmt)
        if not headers:
            return None

        # Case-insensitive comparison so files with ALL-CAPS or all-lower headers
        # (e.g. SBI XLSX exported with different locale) still match.
        headers_lower = {h.lower() for h in headers}

        best_confidence = 0.0
        best_type: SourceType | None = None
        for required_cols, source_type, confidence in _CSV_HEADER_SIGNATURES:
            required_lower = {c.lower() for c in required_cols}
            overlap = len(required_lower & headers_lower) / len(required_lower)
            if overlap >= 0.80 and confidence > best_confidence:
                best_confidence = confidence * overlap
                best_type = source_type

        if best_type and best_confidence >= DETECTION_THRESHOLD:
            return DetectionResult(best_type, best_confidence, "header_scan", fmt)
        return None

    @staticmethod
    def _extract_headers(file_bytes: bytes, fmt: FileFormat) -> set[str]:
        """Return normalised column header names from the file.

        For XLS/XLSX: uses pandas/xlrd to read the workbook, skipping any
        preamble rows (e.g. HDFC netbanking exports have ~21 metadata rows
        before the real header).  Scans the first 30 rows to find a row that
        matches at least 3 known header keywords.
        For CSV: line-based text parse.
        """
        _HEADER_KEYWORDS = {
            "date", "narration", "description", "debit", "credit", "balance",
            "withdrawal", "deposit", "transaction", "amount", "particulars",
            "remarks", "reference", "cheque", "chq", "txn",
        }

        def _row_score(cells: list[str]) -> int:
            """Count how many cells contain at least one header keyword as a substring."""
            return sum(
                1 for c in cells
                if any(kw in c.lower() for kw in _HEADER_KEYWORDS)
            )

        if fmt in (FileFormat.XLS, FileFormat.XLSX):
            try:
                import io
                import pandas as pd
                engine = "xlrd" if fmt == FileFormat.XLS else None
                df_raw = pd.read_excel(
                    io.BytesIO(file_bytes), header=None, dtype=str, engine=engine
                )
                # Scan ALL rows and return the one with the HIGHEST keyword score.
                # Returning the *first* row with score≥2 can accidentally pick a
                # preamble row (e.g. "From Date:" + "To Date:" both score 1 each)
                # instead of the real header row which scores 4-6.
                best_score = 0
                best_cells: list[str] = []
                for _, row in df_raw.iterrows():
                    cells = [str(c).strip() for c in row if str(c).strip() not in ("", "nan")]
                    s = _row_score(cells)
                    if s > best_score:
                        best_score = s
                        best_cells = cells
                if best_score >= 2:
                    return {c.strip() for c in best_cells}
            except Exception:  # noqa: BLE001
                # xlrd failed — might be a text-based pseudo-XLS (SBI old format).
                # Try reading as tab-separated text with single-quoted cells.
                try:
                    for enc in ("utf-8", "latin-1"):
                        try:
                            text = file_bytes.decode(enc)
                            break
                        except UnicodeDecodeError:
                            continue
                    else:
                        return set()
                    for line in text.splitlines():
                        cells = [c.strip().strip("'") for c in line.split("\t")]
                        # Require a high score so preamble rows (low keyword density)
                        # are skipped and only the real transaction header is returned.
                        if _row_score(cells) >= 4:
                            return {c.strip() for c in cells if c.strip()}
                except Exception:  # noqa: BLE001
                    pass
            return set()

        # CSV — try UTF-8 then latin-1
        try:
            for enc in ("utf-8", "latin-1"):
                try:
                    text = file_bytes[:4096].decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                return set()
            for line in text.splitlines():
                line = line.strip()
                if line:
                    return {h.strip().strip('"') for h in line.split(",")}
        except Exception:  # noqa: BLE001
            pass
        return set()

    # ── Public metadata extraction ────────────────────────────────────────────

    @staticmethod
    def extract_metadata(file_bytes: bytes, fmt: FileFormat) -> dict[str, str | None]:
        """Extract bank metadata from a statement file.

        Parses IFSC codes, account numbers, holder names, statement date
        range, and branch from both spreadsheet preamble rows and PDF text.

        Returns a dict with keys: ifsc_code, account_number, account_holder,
        statement_from, statement_to, branch_name.  Values are ``None`` when
        the field could not be found.
        """
        meta: dict[str, str | None] = {
            "ifsc_code":       None,
            "account_number":  None,
            "account_holder":  None,
            "statement_from":  None,
            "statement_to":    None,
            "branch_name":     None,
        }
        if fmt == FileFormat.PDF:
            text = ""
            try:
                from core.utils.pdf_utils import extract_text_per_page  # noqa: PLC0415
                pages = extract_text_per_page(file_bytes)
                text = " ".join(pages[:3])
            except Exception:  # noqa: BLE001
                text = file_bytes.decode("utf-8", errors="ignore")
            meta.update(SourceDetector._parse_metadata_from_text(text))

        elif fmt in (FileFormat.XLS, FileFormat.XLSX):
            try:
                import io  # noqa: PLC0415
                import pandas as pd  # noqa: PLC0415
                engine = "xlrd" if fmt == FileFormat.XLS else None
                df_raw = pd.read_excel(
                    io.BytesIO(file_bytes), header=None, dtype=str, engine=engine
                )
                preamble_lines: list[str] = []
                for _, row in df_raw.head(40).iterrows():
                    cells = [str(c).strip() for c in row if str(c).strip() not in ("", "nan")]
                    if cells:
                        preamble_lines.append(" ".join(cells))
                meta.update(SourceDetector._parse_metadata_from_text("\n".join(preamble_lines)))
            except Exception:  # noqa: BLE001
                pass

        elif fmt == FileFormat.CSV:
            try:
                for enc in ("utf-8", "latin-1"):
                    try:
                        text = file_bytes[:8192].decode(enc)
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    text = ""
                meta.update(SourceDetector._parse_metadata_from_text(text))
            except Exception:  # noqa: BLE001
                pass

        return meta

    @staticmethod
    def _parse_metadata_from_text(text: str) -> dict[str, str | None]:
        """Extract structured bank metadata fields from plain text using heuristics."""
        found: dict[str, str | None] = {}

        # IFSC code — 4 uppercase letters, literal "0", 6 alphanumeric chars
        m = re.search(r"\b([A-Z]{4}0[A-Z0-9]{6})\b", text)
        if m:
            found["ifsc_code"] = m.group(1)

        # Account number — look for labelled pattern (8–20 digits, optionally masked with X/*)
        m = re.search(
            r"(?:A/?C\s*(?:No\.?|Number|Num)?|Account\s*(?:No\.?|Number|Num))\s*[:\-]?\s*([\dXx*]{6,20})",
            text, re.I,
        )
        if m:
            found["account_number"] = m.group(1).strip()

        # Account holder / customer name
        m = re.search(
            r"(?:Account\s*(?:Holder|Name)|Customer\s*Name|Name\s*:)\s*[:\-]?\s*([A-Za-z][A-Za-z\s\.]{2,50}?)(?=\s{2,}|\n|$)",
            text, re.I,
        )
        if m:
            name = m.group(1).strip()
            if len(name) >= 3:
                found["account_holder"] = name

        # Date range — patterns like "01/04/2025 To 30/04/2025" or labelled From/To fields
        _date_pat = r"(\d{2}[/\-]\d{2}[/\-]\d{2,4})"
        m = re.search(r"(?:From|Statement\s+From|Period\s+From)\s*[:\-]?\s*" + _date_pat, text, re.I)
        if m:
            found["statement_from"] = m.group(1)
        m = re.search(r"(?:\bTo\b|Statement\s+To|Period\s+To)\s*[:\-]?\s*" + _date_pat, text, re.I)
        if m:
            found["statement_to"] = m.group(1)

        # Branch name (commonly "Branch : Andheri West" style)
        m = re.search(
            r"Branch\s*(?:Name|Code)?\s*[:\-]?\s*([A-Za-z][A-Za-z\s\-\.]{2,40}?)(?=\s{2,}|\n|$)",
            text, re.I,
        )
        if m:
            branch = m.group(1).strip()
            if len(branch) >= 3:
                found["branch_name"] = branch

        return found
