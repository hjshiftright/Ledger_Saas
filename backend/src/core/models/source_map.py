"""source_map.py — SourceType → source account metadata.

Whenever a file is imported or parsed, the SourceType (which parser handled it)
tells us unambiguously what *kind* of account is the source for all journal entries.

Usage
-----
    from core.models.source_map import get_source_account
    info = get_source_account(SourceType.HDFC_BANK_CSV)
    # info.account_code  → "1102"
    # info.account_name  → "Savings Account"
    # info.account_class → "ASSET"

Override
--------
    # Force credit-card interpretation regardless of SourceType
    info = get_source_account(SourceType.HDFC_BANK_CSV, account_type_override="CREDIT_CARD")
"""
from __future__ import annotations

from dataclasses import dataclass

from core.models.enums import SourceType


@dataclass(frozen=True)
class SourceAccountInfo:
    """Metadata for the *source* account in a double-entry journal entry."""
    account_code: str       # CoA code, e.g. "1102"
    account_name: str       # Display name, e.g. "Savings Account"
    account_class: str      # "ASSET" | "LIABILITY" | "EQUITY" | "INCOME" | "EXPENSE"
    is_debit_normal: bool   # True = DR increases (Asset, Expense); False = CR increases


# ---------------------------------------------------------------------------
# Override map — used when the caller explicitly specifies an account type
# e.g. --account-type CREDIT_CARD on the CLI
# ---------------------------------------------------------------------------
_OVERRIDE_MAP: dict[str, SourceAccountInfo] = {
    "CREDIT_CARD": SourceAccountInfo("2100", "Credit Card",       "LIABILITY", False),
    "CC":          SourceAccountInfo("2100", "Credit Card",       "LIABILITY", False),
    "BANK":        SourceAccountInfo("1102", "Savings Account",   "ASSET",     True),
    "SAVINGS":     SourceAccountInfo("1102", "Savings Account",   "ASSET",     True),
    "INVESTMENT":  SourceAccountInfo("1200", "Investments",       "ASSET",     True),
    "EQUITY_PORT": SourceAccountInfo("1201", "Equity Portfolio",  "ASSET",     True),
    "LOAN":        SourceAccountInfo("2200", "Loan Payable",      "LIABILITY", False),
}

# ---------------------------------------------------------------------------
# Primary map — keyed by SourceType
# ---------------------------------------------------------------------------
_SOURCE_TYPE_MAP: dict[SourceType, SourceAccountInfo] = {
    # ── Bank PDFs → Savings Account (Asset) ─────────────────────────────────
    SourceType.HDFC_BANK:     SourceAccountInfo("1102", "Savings Account",  "ASSET", True),
    SourceType.SBI_BANK:      SourceAccountInfo("1102", "Savings Account",  "ASSET", True),
    SourceType.ICICI_BANK:    SourceAccountInfo("1102", "Savings Account",  "ASSET", True),
    SourceType.AXIS_BANK:     SourceAccountInfo("1102", "Savings Account",  "ASSET", True),
    SourceType.KOTAK_BANK:    SourceAccountInfo("1102", "Savings Account",  "ASSET", True),
    SourceType.INDUSIND_BANK: SourceAccountInfo("1102", "Savings Account",  "ASSET", True),
    SourceType.IDFC_BANK:     SourceAccountInfo("1102", "Savings Account",  "ASSET", True),
    SourceType.UNION_BANK:    SourceAccountInfo("1102", "Savings Account",  "ASSET", True),
    SourceType.BARODA_BANK:   SourceAccountInfo("1102", "Savings Account",  "ASSET", True),
    SourceType.CANARA_BANK:   SourceAccountInfo("1102", "Savings Account",  "ASSET", True),
    SourceType.STANDARD_CHARTERED_BANK: SourceAccountInfo("1102", "Savings Account",  "ASSET", True),
    SourceType.BOI_BANK:      SourceAccountInfo("1102", "Savings Account",  "ASSET", True),

    # ── Credit Card PDFs → Credit Card (Liability) ─────────────────────────
    SourceType.YES_BANK_CC:   SourceAccountInfo("2100", "Credit Card",      "LIABILITY", False),
    SourceType.ICICI_BANK_CC:  SourceAccountInfo("2100", "Credit Card",      "LIABILITY", False),
    SourceType.HDFC_BANK_CC:   SourceAccountInfo("2100", "Credit Card",      "LIABILITY", False),

    # ── Bank CSVs → Savings Account (Asset) ─────────────────────────────────
    SourceType.HDFC_BANK_CSV:  SourceAccountInfo("1102", "Savings Account", "ASSET", True),
    SourceType.SBI_BANK_CSV:   SourceAccountInfo("1102", "Savings Account", "ASSET", True),
    SourceType.ICICI_BANK_CSV: SourceAccountInfo("1102", "Savings Account", "ASSET", True),
    SourceType.AXIS_BANK_CSV:  SourceAccountInfo("1102", "Savings Account", "ASSET", True),
    SourceType.KOTAK_BANK_CSV: SourceAccountInfo("1102", "Savings Account", "ASSET", True),
    SourceType.IDFC_BANK_CSV:  SourceAccountInfo("1102", "Savings Account", "ASSET", True),
    SourceType.UNION_BANK_CSV: SourceAccountInfo("1102", "Savings Account", "ASSET", True),
    SourceType.BARODA_BANK_CSV: SourceAccountInfo("1102", "Savings Account", "ASSET", True),
    SourceType.CANARA_BANK_CSV: SourceAccountInfo("1102", "Savings Account", "ASSET", True),
    SourceType.STANDARD_CHARTERED_BANK_CSV: SourceAccountInfo("1102", "Savings Account", "ASSET", True),
    SourceType.BOI_BANK_CSV: SourceAccountInfo("1102", "Savings Account", "ASSET", True),

    # ── Mutual Fund CAS → Investments (Asset) ───────────────────────────────
    SourceType.CAS_CAMS:       SourceAccountInfo("1200", "Investments",     "ASSET", True),
    SourceType.CAS_KFINTECH:   SourceAccountInfo("1200", "Investments",     "ASSET", True),
    SourceType.CAS_MF_CENTRAL: SourceAccountInfo("1200", "Investments",     "ASSET", True),

    # ── Zerodha ──────────────────────────────────────────────────────────────
    # Holdings & Tradebook: the portfolio itself is the source/destination asset
    SourceType.ZERODHA_HOLDINGS:     SourceAccountInfo("1220", "Equity Holdings",         "ASSET", True),
    SourceType.ZERODHA_TRADEBOOK:    SourceAccountInfo("1220", "Equity Holdings",         "ASSET", True),
    # Tax PnL sub-types — each sheet has a different source account context
    SourceType.ZERODHA_TAX_PNL:           SourceAccountInfo("1220", "Equity Holdings",          "ASSET",   True),
    SourceType.ZERODHA_TAX_PNL_TRADEWISE: SourceAccountInfo("1220", "Equity Holdings",          "ASSET",   True),
    SourceType.ZERODHA_TAX_PNL_DIVIDENDS: SourceAccountInfo("1230", "Zerodha Trading Account",  "ASSET",   True),
    SourceType.ZERODHA_TAX_PNL_CHARGES:   SourceAccountInfo("1230", "Zerodha Trading Account",  "ASSET",   True),
    SourceType.ZERODHA_OPEN_POSITIONS:    SourceAccountInfo("1220", "Equity Holdings",          "ASSET",   True),
    SourceType.ZERODHA_CAPITAL_GAINS:     SourceAccountInfo("1220", "Equity Holdings",          "ASSET",   True),

    # ── Generic / Unknown → default Savings Account ─────────────────────────
    SourceType.GENERIC_CSV: SourceAccountInfo("1102", "Savings Account",   "ASSET", True),
    SourceType.GENERIC_XLS: SourceAccountInfo("1102", "Savings Account",   "ASSET", True),
    SourceType.UNKNOWN:     SourceAccountInfo("1102", "Savings Account",   "ASSET", True),
}

#: Fallback used when both the override and the source-type lookup are unavailable
_DEFAULT = SourceAccountInfo("1102", "Savings Account", "ASSET", True)


def get_source_account(
    source_type: SourceType | str | None = None,
    account_type_override: str | None = None,
) -> SourceAccountInfo:
    """Return the ``SourceAccountInfo`` for a given source type.

    Priority
    --------
    1. ``account_type_override`` (e.g. "CREDIT_CARD") — always wins.
    2. ``source_type`` lookup in ``_SOURCE_TYPE_MAP``.
    3. ``_DEFAULT`` fallback (1102 Savings Account).

    Parameters
    ----------
    source_type:
        The SourceType enum value (or its string value) detected during parsing.
    account_type_override:
        A caller-supplied string (case-insensitive key from ``_OVERRIDE_MAP``).
        Typically comes from ``--account-type`` CLI flag.
    """
    if account_type_override:
        key = account_type_override.upper().replace("-", "_").replace(" ", "_")
        info = _OVERRIDE_MAP.get(key)
        if info is not None:
            return info

    if source_type is not None:
        # Accept both enum and string
        if not isinstance(source_type, SourceType):
            try:
                source_type = SourceType(source_type)
            except ValueError:
                return _DEFAULT
        return _SOURCE_TYPE_MAP.get(source_type, _DEFAULT)

    return _DEFAULT
