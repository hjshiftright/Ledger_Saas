"""SM-G Categorization Engine.

Applies a rule cascade to assign each NormalizedTransaction to an account
from the user's Chart of Accounts (or a default category code).

Cascade:
  1. Exact narration match from user's saved rules.
  2. Regex / keyword rules (built-in + user-defined).
  3. LLM suggestion (optional, called lazily when confidence < threshold).

User corrections are stored as exact-match rules so future imports
automatically apply the learned mapping (R2.4).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from services.normalize_service import NormalizedTransaction

# ── Category definitions ──────────────────────────────────────────────────────

@dataclass
class CategoryRule:
    pattern: str            # regex (case-insensitive)
    category_code: str      # CoA account code or label
    priority: int = 50      # Higher = checked first


# ── Source-type-aware category overrides ─────────────────────────────────────
# For structured statement types (Zerodha, MF CAS) the tx_type_hint already
# tells us exactly what the transaction is — no regex matching needed.
# These fire as Stage 0 in the cascade, before any regex rules.
# Key: SourceType value string → {TxnTypeHint value string → category_code}
# Special key "_all" acts as a catch-all for any txn_type not listed.

_SOURCE_TYPE_CATEGORIES: dict[str, dict[str, str]] = {
    # ── Zerodha Tradebook (equity buy/sell) ───────────────────────────────────
    # BUY  → PURCHASE hint  → money leaving bank to buy stock → INVESTMENT
    # SELL → REDEMPTION hint → proceeds coming in → INCOME_CAPITAL_GAINS
    "ZERODHA_TRADEBOOK": {
        "PURCHASE":  "INVESTMENT",
        "REDEMPTION": "INCOME_CAPITAL_GAINS",
        "_all":      "INVESTMENT",
    },
    # Holdings snapshot (no date-based trades, treated as investment positions)
    "ZERODHA_HOLDINGS": {
        "_all": "INVESTMENT",
    },
    # Tax P&L and Capital Gains reports — all rows represent realised gains
    "ZERODHA_TAX_PNL": {
        "_all": "INCOME_CAPITAL_GAINS",
    },
    "ZERODHA_CAPITAL_GAINS": {
        "_all": "INCOME_CAPITAL_GAINS",
    },
    # ── Mutual Fund CAS (CAMS / KFintech / MF Central) ───────────────────────
    # All purchase/SIP flows → INVESTMENT
    # Dividend payouts → INCOME_DIVIDEND
    # Redemptions/switches still touch the investment account (asset ↔ asset)
    "CAS_CAMS": {
        "PURCHASE":          "INVESTMENT",
        "SIP":               "INVESTMENT",
        "STP_IN":            "INVESTMENT",
        "STP_OUT":           "INVESTMENT",
        "SWP":               "INVESTMENT",
        "SWITCH_IN":         "INVESTMENT",
        "SWITCH_OUT":        "INVESTMENT",
        "REDEMPTION":        "INVESTMENT",
        "DIVIDEND_REINVEST": "INVESTMENT",
        "BONUS":             "INVESTMENT",
        "DIVIDEND_PAYOUT":   "INCOME_DIVIDEND",
        "_all":              "INVESTMENT",
    },
    "CAS_KFINTECH":   {
        "PURCHASE": "INVESTMENT", "SIP": "INVESTMENT", "REDEMPTION": "INVESTMENT",
        "DIVIDEND_PAYOUT": "INCOME_DIVIDEND", "DIVIDEND_REINVEST": "INVESTMENT",
        "_all": "INVESTMENT",
    },
    "CAS_MF_CENTRAL": {
        "PURCHASE": "INVESTMENT", "SIP": "INVESTMENT", "REDEMPTION": "INVESTMENT",
        "DIVIDEND_PAYOUT": "INCOME_DIVIDEND", "DIVIDEND_REINVEST": "INVESTMENT",
        "_all": "INVESTMENT",
    },
}


# Built-in keyword rules - ordered by specificity
_BUILTIN_RULES: list[CategoryRule] = [
    # Income — refunds and cashback checked before generic expense rules
    CategoryRule(r"refund|reversal|rfd\s|money.?back|cancelled.*amount|amt.*returned", "INCOME_REFUND",   92),
    CategoryRule(r"cashback|cash.?back|reward.*credit|loyalty.*credit",                "INCOME_CASHBACK", 91),
    # Credit card bill payment (from bank statement debit or CC statement credit)
    # Priority 84 — below EXPENSE_EMI (85) so "CREDITCARD/EMI PAYMENT" stays as EMI
    CategoryRule(r"cc.*pay|credit.?card.*pay|card.*bill|autopay.*card|bill.*clear|cc.*autopay", "CC_PAYMENT", 84),
    CategoryRule(r"salary|payroll|\bctc\b|pay.*slip", "INCOME_SALARY",         90),
    CategoryRule(r"interest.*credit|int\.?credit|savings.*int", "INCOME_INTEREST", 85),
    CategoryRule(r"dividend|div\s*pay", "INCOME_DIVIDEND",                 85),
    CategoryRule(r"capital.?gain|ltcg|stcg",  "INCOME_CAPITAL_GAINS",      80),
    # Transfers
    CategoryRule(r"upi|neft|rtgs|imps|transfer|trf", "TRANSFER",           10),
    CategoryRule(r"atm|cash.*wd|wd.*cash", "CASH_WITHDRAWAL",               70),
    # Expenses
    CategoryRule(r"swiggy|zomato|uber.?eat|food.*del|dining|restaurant|cafe|hotel.*food", "EXPENSE_FOOD", 80),
    CategoryRule(r"uber|ola|rapido|metro|irctc|train|flight|air.*india|indigo|spicejet", "EXPENSE_TRANSPORT", 80),
    CategoryRule(r"amazon|flipkart|myntra|meesho|nykaa|shop|shopping|store|mart", "EXPENSE_SHOPPING", 75),
    CategoryRule(r"apollo|medplus|pharmacy|hospital|clinic|doctor|health|medicover", "EXPENSE_HEALTHCARE", 80),
    CategoryRule(r"electricity|bescom|tata.*power|adani.*elec|bses|solar|gas.*bill|piped.?gas", "EXPENSE_UTILITIES", 80),
    CategoryRule(r"jio|airtel|vi\b|bsnl|broadband|internet|wifi|telecom", "EXPENSE_UTILITIES", 75),
    CategoryRule(r"rent|house.*rent|pg\b|accommodation", "EXPENSE_HOUSING", 80),
    CategoryRule(r"\bemi\b|home.*loan|car.*loan|vehicle.*loan|loan.*\bemi\b|mortgage", "EXPENSE_EMI", 85),
    CategoryRule(r"lic\b|insurance|premium|policy|term.?plan|health.*ins", "EXPENSE_INSURANCE", 80),
    CategoryRule(r"school|college|university|tuition|education|byju|coursera|udemy", "EXPENSE_EDUCATION", 80),
    CategoryRule(r"netflix|prime.*video|hotstar|spotify|youtube.*premium|subscription|ott", "EXPENSE_ENTERTAINMENT", 82),
    CategoryRule(r"zerodha|groww|angel|demat|mutual.fund|sip|elss|nps.*contribution", "INVESTMENT", 80),
    CategoryRule(r"ppf|epf|provident|nps|sukanya", "INVESTMENT",            82),
    CategoryRule(r"fd\b|fixed.?deposit|term.?dep", "INVESTMENT",            80),
]

def _get_user_rules(user_id: str, session) -> list["CategoryRule"]:
    """Load user rules from SQLite for the given user."""
    from sqlalchemy import select  # noqa: PLC0415
    from db.models.categories import UserCategoryRule  # noqa: PLC0415
    rows = session.execute(
        select(UserCategoryRule).where(UserCategoryRule.user_id == user_id)
    ).scalars().all()
    return [
        CategoryRule(
            pattern=r.pattern,
            category_code=r.category_code,
            priority=r.priority,
        )
        for r in rows
    ]


@dataclass
class CategoryResult:
    row_id: str
    category_code: str
    confidence: float
    method: str             # "exact" | "regex" | "llm" | "default"


@dataclass
class CategorizeBatchResult:
    batch_id: str
    results: list[CategoryResult] = field(default_factory=list)

    @property
    def mean_confidence(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.confidence for r in self.results) / len(self.results)

    @property
    def categories_found(self) -> list[str]:
        return sorted({r.category_code for r in self.results})


class CategorizeService:
    """SM-G: Assign categories to normalized transactions."""

    def categorize_batch(
        self,
        user_id: str,
        batch_id: str,
        rows: list[NormalizedTransaction],
        session=None,
    ) -> CategorizeBatchResult:
        result = CategorizeBatchResult(batch_id=batch_id)
        compiled = self._compile_rules(user_id, session)

        for row in rows:
            cat_result = self._categorize_row(row, compiled)
            row.extra_fields["category"] = cat_result.category_code
            row.extra_fields["category_confidence"] = cat_result.confidence
            row.extra_fields["category_method"] = cat_result.method
            result.results.append(cat_result)

        return result

    def learn_from_correction(
        self,
        user_id: str,
        narration_pattern: str,
        category_code: str,
        session=None,
    ) -> None:
        """Store a user correction as an exact-match rule (R2.4)."""
        from sqlalchemy import select, delete  # noqa: PLC0415
        from db.models.categories import UserCategoryRule  # noqa: PLC0415

        escaped = re.escape(narration_pattern.lower())
        # Remove existing rule for same pattern (case-insensitive)
        session.execute(
            delete(UserCategoryRule).where(
                UserCategoryRule.user_id == user_id,
                UserCategoryRule.pattern == escaped,
            )
        )
        session.add(UserCategoryRule(
            user_id=user_id,
            pattern=escaped,
            category_code=category_code,
            priority=100,
        ))
        session.flush()

    def _compile_rules(self, user_id: str, session=None) -> list[tuple[re.Pattern[str], str, float]]:
        """Return compiled (pattern, code, confidence) tuples sorted by priority desc."""
        all_rules = list(_BUILTIN_RULES)
        if session is not None:
            all_rules.extend(_get_user_rules(user_id, session))
        all_rules.sort(key=lambda r: -r.priority)
        return [
            (re.compile(r.pattern, re.IGNORECASE), r.category_code,
             min(0.99, 0.6 + r.priority / 250))
            for r in all_rules
        ]

    def _categorize_row(
        self,
        row: NormalizedTransaction,
        compiled: list[tuple[re.Pattern[str], str, float]],
    ) -> CategoryResult:
        # ── Stage 0: Source-type override (highest priority) ──────────────────
        # Structured statement formats (Zerodha, CAS) carry reliable txn_type_hint
        # values set by their parsers. Use those directly — no regex needed.
        source_type = row.source_type  # string like "ZERODHA_TRADEBOOK"
        if source_type in _SOURCE_TYPE_CATEGORIES:
            type_map   = _SOURCE_TYPE_CATEGORIES[source_type]
            txn_hint   = row.txn_type.value if row.txn_type else ""
            category   = type_map.get(txn_hint.upper(), type_map.get("_all"))
            if category:
                return CategoryResult(
                    row_id=row.row_id,
                    category_code=category,
                    confidence=0.95,
                    method="source_type",
                )

        text = (row.narration + " " + row.raw_narration).lower()

        for pattern, code, confidence in compiled:
            if pattern.search(text):
                # Semantic override: money ARRIVING (credit) that matches an expense
                # vendor is almost certainly a refund/reversal from that merchant.
                # Transfers are excluded — they stay as TRANSFER regardless of direction.
                if not row.is_debit and code.startswith("EXPENSE_"):
                    return CategoryResult(
                        row_id=row.row_id, category_code="INCOME_REFUND",
                        confidence=0.70, method="regex_refund_override",
                    )
                return CategoryResult(
                    row_id=row.row_id, category_code=code,
                    confidence=confidence, method="regex",
                )

        return CategoryResult(
            row_id=row.row_id,
            category_code="EXPENSE_OTHER" if row.is_debit else "INCOME_OTHER",
            confidence=0.30,
            method="default",
        )
