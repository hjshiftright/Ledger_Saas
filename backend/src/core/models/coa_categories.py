"""Single source of truth: category code → Chart of Accounts mapping.

These codes MUST match the accounts provisioned by
``POST /api/v1/accounts/provision-defaults`` in api/routers/accounts.py.

CoA structure provisioned by that endpoint:
  1xxx  Assets     (1101 Cash in Hand, 1102 Savings Account, 1201 Mutual Funds …)
  2xxx  Liabilities (2100 Credit Cards, 2999 Transfer Clearing …)
  3xxx  Equity     (3100 Opening Balances)
  4xxx  Income     (4100 Salary, 4200 Interest, 4300 Dividend, 4400 Capital Gains,
                    4500 Rental, 4900 Other)
  5xxx  Expenses   (5100 Groceries, 5200 Transport, 5300 Housing/Rent,
                    5400 Utilities, 5500 Healthcare, 5600 Education,
                    5700 Shopping, 5800 Entertainment, 5900 Insurance,
                    5999 Miscellaneous)

Import this dict in any module that needs to resolve a category string to a
CoA code — never hard-code the codes in multiple places.
"""
from __future__ import annotations

# (account_code, account_name) keyed by category string emitted by CategorizeService
CATEGORY_TO_ACCOUNT: dict[str, tuple[str, str]] = {
    # ── Income (4xxx) ──────────────────────────────────────────────────────────
    "INCOME_SALARY":        ("4100", "Salary / Wages"),
    "INCOME_INTEREST":      ("4200", "Interest Income"),
    "INCOME_DIVIDEND":      ("4300", "Dividend Income"),
    "INCOME_CAPITAL_GAINS": ("4400", "Capital Gains"),
    "INCOME_REFUND":        ("4900", "Other Income"),   # no dedicated refund leaf
    "INCOME_CASHBACK":      ("4900", "Other Income"),   # no dedicated cashback leaf
    "INCOME_OTHER":         ("4900", "Other Income"),
    # ── Expenses (5xxx) ────────────────────────────────────────────────────────
    "EXPENSE_FOOD":         ("5100", "Groceries"),
    "EXPENSE_TRANSPORT":    ("5200", "Transportation"),
    "EXPENSE_HOUSING":      ("5300", "Housing / Rent"),
    "EXPENSE_EMI":          ("5300", "Housing / Rent"),  # loan EMI → same bucket for now
    "EXPENSE_UTILITIES":    ("5400", "Utilities"),
    "EXPENSE_HEALTHCARE":   ("5500", "Healthcare"),
    "EXPENSE_EDUCATION":    ("5600", "Education"),
    "EXPENSE_SHOPPING":     ("5700", "Shopping"),
    "EXPENSE_ENTERTAINMENT":("5800", "Entertainment"),
    "EXPENSE_INSURANCE":    ("5900", "Insurance Premium"),
    "EXPENSE_OTHER":        ("5999", "Miscellaneous"),
    # ── Asset movements ────────────────────────────────────────────────────────
    "CASH_WITHDRAWAL":      ("1101", "Cash in Hand"),
    "INVESTMENT":           ("1201", "Mutual Funds"),
    # ── Clearing ───────────────────────────────────────────────────────────────
    "TRANSFER":             ("2999", "Transfer Clearing"),
    "CC_PAYMENT":           ("2999", "Transfer Clearing"),
}

# Fallback when category is missing or unrecognised
DEFAULT_COUNTERPART: tuple[str, str] = ("5999", "Miscellaneous")
