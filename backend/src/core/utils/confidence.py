"""Confidence scoring utilities for parser output.

Implements the weighted-signal formula from SM-C §4.1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

# ── Weights matching the spec (SM-C §4.1) ────────────────────────────────────
_WEIGHTS: dict[str, float] = {
    "balance_cross_check_passed": 0.40,
    "all_rows_have_valid_date": 0.20,
    "all_rows_have_amount": 0.20,
    "row_count_positive": 0.10,
    "no_row_parse_errors": 0.10,
}

CONFIDENCE_THRESHOLD = 0.75  # Minimum to consider extraction "successful"


@dataclass
class ConfidenceSignals:
    """Boolean input signals used to compute extraction confidence.

    ``balance_cross_check_passed`` may be ``None`` when the check cannot be
    run (e.g. no opening/closing balance in the source), in which case the
    signal contributes 0 to the score rather than penalising the parser.
    """

    balance_cross_check_passed: bool | None = None
    all_rows_have_valid_date: bool = False
    all_rows_have_amount: bool = False
    row_count_positive: bool = False
    no_row_parse_errors: bool = False


def compute_confidence(signals: ConfidenceSignals) -> float:
    """Return a float in [0.0, 1.0] from the weighted signal formula.

    When ``balance_cross_check_passed`` is ``None`` (check not applicable),
    its weight is redistributed equally among the remaining four signals.

    >>> compute_confidence(ConfidenceSignals(True, True, True, True, True))
    1.0
    >>> compute_confidence(ConfidenceSignals())
    0.0
    """
    bcc = signals.balance_cross_check_passed
    if bcc is None:
        # Balance check not applicable — distribute its weight to other signals
        other_weight = 1.0  # remaining four signals share the full score
        score = (
            _WEIGHTS["all_rows_have_valid_date"] * float(signals.all_rows_have_valid_date)
            + _WEIGHTS["all_rows_have_amount"] * float(signals.all_rows_have_amount)
            + _WEIGHTS["row_count_positive"] * float(signals.row_count_positive)
            + _WEIGHTS["no_row_parse_errors"] * float(signals.no_row_parse_errors)
        )
        # Scale to [0, 1] by dividing by the sum of the four active weights
        active_weight = 1.0 - _WEIGHTS["balance_cross_check_passed"]
        score = score / active_weight if active_weight else 0.0
    else:
        score = (
            _WEIGHTS["balance_cross_check_passed"] * float(bcc)
            + _WEIGHTS["all_rows_have_valid_date"] * float(signals.all_rows_have_valid_date)
            + _WEIGHTS["all_rows_have_amount"] * float(signals.all_rows_have_amount)
            + _WEIGHTS["row_count_positive"] * float(signals.row_count_positive)
            + _WEIGHTS["no_row_parse_errors"] * float(signals.no_row_parse_errors)
        )
    return round(score, 4)


def check_balance_cross_check(
    opening: Decimal | None,
    closing: Decimal | None,
    debits: list[Decimal],
    credits: list[Decimal],
    tolerance: Decimal = Decimal("1.00"),
) -> bool:
    """Verify: opening + Σcredits − Σdebits ≈ closing (within ±₹1 tolerance).

    Returns False if opening or closing is None (insufficient data to check).

    >>> from decimal import Decimal
    >>> check_balance_cross_check(Decimal("10000"), Decimal("9550"), [Decimal("450")], [])
    True
    >>> check_balance_cross_check(Decimal("10000"), Decimal("9000"), [Decimal("450")], [])
    False
    """
    if opening is None or closing is None:
        return False
    expected = opening + sum(credits, Decimal("0")) - sum(debits, Decimal("0"))
    return abs(expected - closing) <= tolerance


def signals_from_rows(
    rows_raw_dates: list[str],
    rows_have_amount: list[bool],
    rows_have_error: list[bool],
    opening: Decimal | None,
    closing: Decimal | None,
    debits: list[Decimal],
    credits: list[Decimal],
) -> ConfidenceSignals:
    """Build ConfidenceSignals from extracted row data.

    Convenience helper so each parser doesn't duplicate this logic.
    """
    total = len(rows_raw_dates)
    return ConfidenceSignals(
        balance_cross_check_passed=check_balance_cross_check(opening, closing, debits, credits),
        all_rows_have_valid_date=total > 0 and all(bool(d.strip()) for d in rows_raw_dates),
        all_rows_have_amount=total > 0 and all(rows_have_amount),
        row_count_positive=total > 0,
        no_row_parse_errors=total > 0 and not any(rows_have_error),
    )
