"""SM-H Confidence Scoring.

Computes an overall confidence score for each NormalizedTransaction
by combining signals from the parser, categorization, and data quality.

Output: ConfidenceBand (GREEN / YELLOW / RED) per transaction.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.models.enums import ConfidenceBand
from services.normalize_service import NormalizedTransaction

# Thresholds (spec SM-H)
_GREEN_THRESHOLD  = 0.85
_YELLOW_THRESHOLD = 0.60


@dataclass
class ScoredTransaction:
    row_id: str
    overall_confidence: float
    band: ConfidenceBand
    signals: dict[str, float]   # Individual signal scores for audit


@dataclass
class ConfidenceBatchResult:
    batch_id: str
    scored: list[ScoredTransaction] = field(default_factory=list)

    @property
    def green_count(self) -> int:
        return sum(1 for s in self.scored if s.band == ConfidenceBand.GREEN)

    @property
    def yellow_count(self) -> int:
        return sum(1 for s in self.scored if s.band == ConfidenceBand.YELLOW)

    @property
    def red_count(self) -> int:
        return sum(1 for s in self.scored if s.band == ConfidenceBand.RED)


class ConfidenceService:
    """SM-H: Score transactions and classify into GREEN/YELLOW/RED bands."""

    def score_batch(
        self,
        batch_id: str,
        rows: list[NormalizedTransaction],
    ) -> ConfidenceBatchResult:
        result = ConfidenceBatchResult(batch_id=batch_id)
        for row in rows:
            scored = self._score_row(row)
            row.extra_fields["overall_confidence"] = scored.overall_confidence
            row.extra_fields["confidence_band"]    = scored.band.value
            result.scored.append(scored)
        return result

    def _score_row(self, row: NormalizedTransaction) -> ScoredTransaction:
        signals: dict[str, float] = {}

        # Signal 1: Parser row confidence (weight 0.40)
        signals["parser"] = row.row_confidence

        # Signal 2: Date parsed successfully (0.20)
        signals["date_parsed"] = 1.0 if row.txn_date is not None else 0.0

        # Signal 3: Amount confidence (0.20) — full confidence if both debit and credit not ambiguous
        amount_conf = 1.0
        has_debit  = row.raw_debit  and row.raw_debit.strip()  not in ("", "0", "0.00")
        has_credit = row.raw_credit and row.raw_credit.strip() not in ("", "0", "0.00")
        if has_debit and has_credit:
            amount_conf = 0.5   # ambiguous — both populated
        elif not has_debit and not has_credit:
            amount_conf = 0.2   # missing
        signals["amount"] = amount_conf

        # Signal 4: Category confidence (0.20)
        category_conf = float(row.extra_fields.get("category_confidence", 0.30))
        signals["category"] = category_conf

        # Weighted sum
        overall = (
            signals["parser"]      * 0.40
            + signals["date_parsed"] * 0.20
            + signals["amount"]      * 0.20
            + signals["category"]    * 0.20
        )
        overall = max(0.0, min(1.0, overall))

        if overall >= _GREEN_THRESHOLD:
            band = ConfidenceBand.GREEN
        elif overall >= _YELLOW_THRESHOLD:
            band = ConfidenceBand.YELLOW
        else:
            band = ConfidenceBand.RED

        return ScoredTransaction(
            row_id=row.row_id,
            overall_confidence=round(overall, 4),
            band=band,
            signals=signals,
        )
