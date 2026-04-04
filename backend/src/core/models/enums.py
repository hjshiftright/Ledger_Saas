"""Shared enumerations for the Ledger 3.0 Transaction Manager pipeline.

All modules (SM-A through SM-K) import from here.
Do NOT define enums inside individual modules.
"""

from enum import Enum


class SourceType(str, Enum):
    """Identifies the source institution / format of a statement file."""

    # ── Bank PDFs ──────────────────────────────────────────────────────────────
    HDFC_BANK = "HDFC_BANK"
    SBI_BANK = "SBI_BANK"
    ICICI_BANK = "ICICI_BANK"
    AXIS_BANK = "AXIS_BANK"
    KOTAK_BANK = "KOTAK_BANK"
    INDUSIND_BANK = "INDUSIND_BANK"
    IDFC_BANK = "IDFC_BANK"
    UNION_BANK = "UNION_BANK"
    BARODA_BANK = "BARODA_BANK"
    CANARA_BANK = "CANARA_BANK"
    STANDARD_CHARTERED_BANK = "STANDARD_CHARTERED_BANK"
    BOI_BANK = "BOI_BANK"  # Bank of India (PDF)
    YES_BANK_CC = "YES_BANK_CC"   # Yes Bank Credit Card e-statement
    ICICI_BANK_CC = "ICICI_BANK_CC" # ICICI Bank Credit Card e-statement
    HDFC_BANK_CC = "HDFC_BANK_CC"   # HDFC Bank Credit Card e-statement

    # ── Bank CSVs / XLS ──────────────────────────────────────────────────────
    HDFC_BANK_CSV = "HDFC_BANK_CSV"
    SBI_BANK_CSV = "SBI_BANK_CSV"
    ICICI_BANK_CSV = "ICICI_BANK_CSV"
    AXIS_BANK_CSV = "AXIS_BANK_CSV"
    KOTAK_BANK_CSV = "KOTAK_BANK_CSV"
    IDFC_BANK_CSV = "IDFC_BANK_CSV"
    UNION_BANK_CSV = "UNION_BANK_CSV"
    BARODA_BANK_CSV = "BARODA_BANK_CSV"
    CANARA_BANK_CSV = "CANARA_BANK_CSV"
    STANDARD_CHARTERED_BANK_CSV = "STANDARD_CHARTERED_BANK_CSV"
    BOI_BANK_CSV = "BOI_BANK_CSV"  # Bank of India (CSV/XLS/XLSX)

    # ── Mutual Fund CAS ────────────────────────────────────────────────────────
    CAS_CAMS = "CAS_CAMS"
    CAS_KFINTECH = "CAS_KFINTECH"
    CAS_MF_CENTRAL = "CAS_MF_CENTRAL"

    # ── Zerodha ────────────────────────────────────────────────────────────────
    ZERODHA_HOLDINGS = "ZERODHA_HOLDINGS"
    ZERODHA_TRADEBOOK = "ZERODHA_TRADEBOOK"
    ZERODHA_TAX_PNL = "ZERODHA_TAX_PNL"              # legacy / full-file detection
    ZERODHA_TAX_PNL_TRADEWISE = "ZERODHA_TAX_PNL_TRADEWISE"    # Tradewise Exits → capital gains
    ZERODHA_TAX_PNL_DIVIDENDS = "ZERODHA_TAX_PNL_DIVIDENDS"    # Equity Dividends → div income
    ZERODHA_TAX_PNL_CHARGES   = "ZERODHA_TAX_PNL_CHARGES"      # Other Debits/Credits → broker fees
    ZERODHA_OPEN_POSITIONS    = "ZERODHA_OPEN_POSITIONS"        # Open Positions → portfolio snapshot
    ZERODHA_CAPITAL_GAINS = "ZERODHA_CAPITAL_GAINS"

    # ── Generic / Unknown ──────────────────────────────────────────────────────
    GENERIC_CSV = "GENERIC_CSV"
    GENERIC_XLS = "GENERIC_XLS"
    UNKNOWN = "UNKNOWN"


class ExtractionMethod(str, Enum):
    """Method used to extract transaction data from a source document."""

    TEXT_LAYER = "TEXT_LAYER"
    TABLE_EXTRACTION = "TABLE_EXTRACTION"
    OCR = "OCR"
    LLM_TEXT = "LLM_TEXT"
    LLM_VISION = "LLM_VISION"


class TxnTypeHint(str, Enum):
    """Parser-assigned transaction type hint — refined by SM-E normalization."""

    # ── Mutual fund ────────────────────────────────────────────────────────────
    PURCHASE = "PURCHASE"
    REDEMPTION = "REDEMPTION"
    DIVIDEND_PAYOUT = "DIVIDEND_PAYOUT"
    DIVIDEND_REINVEST = "DIVIDEND_REINVEST"
    BONUS = "BONUS"
    SIP = "SIP"
    SWP = "SWP"
    STP_IN = "STP_IN"
    STP_OUT = "STP_OUT"
    SWITCH_IN = "SWITCH_IN"
    SWITCH_OUT = "SWITCH_OUT"

    # ── Bank ───────────────────────────────────────────────────────────────────
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"
    ATM_WITHDRAWAL = "ATM_WITHDRAWAL"
    NEFT = "NEFT"
    IMPS = "IMPS"
    UPI = "UPI"
    CHEQUE = "CHEQUE"
    INTEREST = "INTEREST"
    UNKNOWN = "UNKNOWN"


class BatchStatus(str, Enum):
    """ImportBatch lifecycle status — 13 states as per SM-B spec."""

    UPLOADING = "UPLOADING"
    DETECTING = "DETECTING"
    QUEUED = "QUEUED"
    PARSING = "PARSING"
    PARSE_COMPLETE = "PARSE_COMPLETE"
    PARSE_FAILED = "PARSE_FAILED"
    NORMALIZING = "NORMALIZING"
    DEDUPLICATING = "DEDUPLICATING"
    CATEGORIZING = "CATEGORIZING"
    SCORING = "SCORING"
    IN_REVIEW = "IN_REVIEW"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ParseStatus(str, Enum):
    """Result of a single parser run."""

    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"   # Rows extracted but below confidence threshold
    FAILED = "FAILED"


class DedupStatus(str, Enum):
    """Deduplication result per transaction row (SM-F)."""

    NEW = "NEW"
    DUPLICATE = "DUPLICATE"
    NEAR_DUPLICATE = "NEAR_DUPLICATE"
    TRANSFER_PAIR = "TRANSFER_PAIR"
    TRANSFER_PAIR_CANDIDATE = "TRANSFER_PAIR_CANDIDATE"


class ConfidenceBand(str, Enum):
    """Three-tier band for the Review Queue (SM-H thresholds)."""

    GREEN = "GREEN"    # overall_confidence >= 0.85  → bulk-approvable
    YELLOW = "YELLOW"  # 0.60 <= overall_confidence < 0.85
    RED = "RED"        # overall_confidence < 0.60   → must review individually


class FileFormat(str, Enum):
    """Supported upload file formats."""

    PDF = "PDF"
    CSV = "CSV"
    XLS = "XLS"
    XLSX = "XLSX"


class ReviewStatus(str, Enum):
    """PendingTransaction review state (SM-I)."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    EXCLUDED = "EXCLUDED"
    SKIPPED = "SKIPPED"


# ── Source-type groupings (used by detector and registry) ─────────────────────

PDF_SOURCE_TYPES: frozenset[SourceType] = frozenset(
    {
        SourceType.HDFC_BANK,
        SourceType.SBI_BANK,
        SourceType.ICICI_BANK,
        SourceType.AXIS_BANK,
        SourceType.KOTAK_BANK,
        SourceType.INDUSIND_BANK,
        SourceType.IDFC_BANK,
        SourceType.UNION_BANK,
        SourceType.BARODA_BANK,
        SourceType.CANARA_BANK,
        SourceType.STANDARD_CHARTERED_BANK,
        SourceType.BOI_BANK,
        SourceType.CAS_CAMS,
        SourceType.CAS_KFINTECH,
        SourceType.CAS_MF_CENTRAL,
    }
)

CSV_SOURCE_TYPES: frozenset[SourceType] = frozenset(
    {
        SourceType.HDFC_BANK_CSV,
        SourceType.SBI_BANK_CSV,
        SourceType.ICICI_BANK_CSV,
        SourceType.AXIS_BANK_CSV,
        SourceType.KOTAK_BANK_CSV,
        SourceType.IDFC_BANK_CSV,
        SourceType.UNION_BANK_CSV,
        SourceType.BARODA_BANK_CSV,
        SourceType.CANARA_BANK_CSV,
        SourceType.STANDARD_CHARTERED_BANK_CSV,
        SourceType.BOI_BANK_CSV,
        SourceType.ZERODHA_HOLDINGS,
        SourceType.ZERODHA_TRADEBOOK,
        SourceType.ZERODHA_TAX_PNL,
        SourceType.ZERODHA_TAX_PNL_TRADEWISE,
        SourceType.ZERODHA_TAX_PNL_DIVIDENDS,
        SourceType.ZERODHA_TAX_PNL_CHARGES,
        SourceType.ZERODHA_OPEN_POSITIONS,
        SourceType.ZERODHA_CAPITAL_GAINS,
        SourceType.GENERIC_CSV,
        SourceType.GENERIC_XLS,
    }
)

BANK_SOURCE_TYPES: frozenset[SourceType] = frozenset(
    {
        SourceType.HDFC_BANK,
        SourceType.SBI_BANK,
        SourceType.ICICI_BANK,
        SourceType.AXIS_BANK,
        SourceType.KOTAK_BANK,
        SourceType.INDUSIND_BANK,
        SourceType.IDFC_BANK,
        SourceType.UNION_BANK,
        SourceType.BARODA_BANK,
        SourceType.CANARA_BANK,
        SourceType.STANDARD_CHARTERED_BANK,
        SourceType.BOI_BANK,
        SourceType.HDFC_BANK_CSV,
        SourceType.SBI_BANK_CSV,
        SourceType.ICICI_BANK_CSV,
        SourceType.AXIS_BANK_CSV,
        SourceType.KOTAK_BANK_CSV,
        SourceType.IDFC_BANK_CSV,
        SourceType.UNION_BANK_CSV,
        SourceType.BARODA_BANK_CSV,
        SourceType.CANARA_BANK_CSV,
        SourceType.STANDARD_CHARTERED_BANK_CSV,
        SourceType.BOI_BANK_CSV,
    }
)

CAS_SOURCE_TYPES: frozenset[SourceType] = frozenset(
    {
        SourceType.CAS_CAMS,
        SourceType.CAS_KFINTECH,
        SourceType.CAS_MF_CENTRAL,
    }
)
