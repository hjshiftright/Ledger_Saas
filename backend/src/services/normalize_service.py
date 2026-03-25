"""SM-E Schema Normalization — converts RawParsedRow → NormalizedTransaction.

Handles:
- Date parsing (multiple Indian date formats)
- Amount resolution (debit/credit → signed decimal)
- Narration cleaning
- Reference number extraction
- TxnType inference
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from core.models.enums import TxnTypeHint
from core.models.raw_parsed_row import RawParsedRow

# ── Date format candidates ────────────────────────────────────────────────────
_DATE_FORMATS = [
    "%d/%m/%Y", "%d-%m-%Y", "%d %m %Y",
    "%Y-%m-%d", "%Y/%m/%d",
    "%d/%m/%y", "%d-%m-%y",
    "%d %b %Y", "%d-%b-%Y", "%d/%b/%Y",
    "%d %B %Y", "%d-%B-%Y",
]

# ── Narration cleaner ─────────────────────────────────────────────────────────
_NOISE_RE = re.compile(
    r"\b(UPI|NEFT|RTGS|IMPS|ATM|WDL|POS|CHQ|CMS|ECS|ACH|NACH|DEBIT|CREDIT|TXN|REF|BY|TO|FROM)\b",
    re.IGNORECASE,
)
_MULTI_SPACE_RE = re.compile(r"\s{2,}")


@dataclass
class NormalizedTransaction:
    """Output of SM-E normalization — one canonical transaction record."""

    row_id: str
    batch_id: str
    source_type: str

    # ── Date ──────────────────────────────────────────────────────────────────
    txn_date: date | None
    raw_date: str

    # ── Amount ────────────────────────────────────────────────────────────────
    amount: Decimal                         # Positive = credit to bank, negative = debit
    is_debit: bool
    raw_debit: str | None
    raw_credit: str | None
    raw_balance: str | None
    closing_balance: Decimal | None

    # ── Description ───────────────────────────────────────────────────────────
    narration: str                          # Cleaned narration
    raw_narration: str
    reference: str | None

    # ── Type ─────────────────────────────────────────────────────────────────
    txn_type: TxnTypeHint

    # ── Confidence ───────────────────────────────────────────────────────────
    row_confidence: float

    # ── Pass-through ─────────────────────────────────────────────────────────
    extra_fields: dict[str, Any] = field(default_factory=dict)
    parse_warnings: list[str] = field(default_factory=list)


@dataclass
class NormalizationResult:
    batch_id: str
    rows: list[NormalizedTransaction]
    rows_normalized: int = 0
    rows_skipped: int = 0
    warnings: list[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        total = self.rows_normalized + self.rows_skipped
        return self.rows_normalized / total if total else 0.0


# ── Public service ────────────────────────────────────────────────────────────

class NormalizeService:
    """SM-E: Converts a list of RawParsedRow into NormalizedTransaction records."""

    def normalize_batch(self, batch_id: str, raw_rows: list[RawParsedRow]) -> NormalizationResult:
        result = NormalizationResult(batch_id=batch_id, rows=[])
        for row in raw_rows:
            norm, warnings = self._normalize_row(row)
            if norm:
                norm.parse_warnings = warnings
                result.rows.append(norm)
                result.rows_normalized += 1
            else:
                result.rows_skipped += 1
                result.warnings.extend(warnings)
        return result

    def _normalize_row(self, row: RawParsedRow) -> tuple[NormalizedTransaction | None, list[str]]:
        warnings: list[str] = []

        # Date
        txn_date = _parse_date(row.raw_date)
        if txn_date is None:
            warnings.append(f"Could not parse date: '{row.raw_date}' (row {row.row_number})")

        # Amount
        amount, is_debit, amt_warnings = _resolve_amount(row.raw_debit, row.raw_credit)
        warnings.extend(amt_warnings)
        if amount is None:
            warnings.append(f"Could not resolve amount for row {row.row_number}")
            return None, warnings

        # Balance
        closing_balance = _parse_decimal(row.raw_balance) if row.raw_balance else None

        # Narration
        narration = _clean_narration(row.raw_narration)

        return NormalizedTransaction(
            row_id=row.row_id,
            batch_id=row.batch_id,
            source_type=row.source_type.value,
            txn_date=txn_date,
            raw_date=row.raw_date,
            amount=amount,
            is_debit=is_debit,
            raw_debit=row.raw_debit,
            raw_credit=row.raw_credit,
            raw_balance=row.raw_balance,
            closing_balance=closing_balance,
            narration=narration,
            raw_narration=row.raw_narration,
            reference=row.raw_reference,
            txn_type=row.txn_type_hint,
            row_confidence=row.row_confidence,
            extra_fields=dict(row.extra_fields),
        ), warnings


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_date(raw: str) -> date | None:
    raw = raw.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            pass
    return None


def _parse_decimal(raw: str | None) -> Decimal | None:
    if not raw:
        return None
    cleaned = re.sub(r"[,\s₹$]", "", raw.strip())
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _resolve_amount(
    raw_debit: str | None,
    raw_credit: str | None,
) -> tuple[Decimal | None, bool, list[str]]:
    """Returns (amount, is_debit, warnings). Amount is always positive."""
    warnings: list[str] = []
    debit  = _parse_decimal(raw_debit)
    credit = _parse_decimal(raw_credit)

    if debit and debit > 0:
        return debit, True, warnings
    if credit and credit > 0:
        return credit, False, warnings
    if debit is not None and credit is not None:
        warnings.append("Both debit and credit are zero or None.")
    return None, True, warnings


def _clean_narration(narration: str) -> str:
    cleaned = _NOISE_RE.sub(" ", narration)
    cleaned = _MULTI_SPACE_RE.sub(" ", cleaned).strip()
    return cleaned or narration.strip()
