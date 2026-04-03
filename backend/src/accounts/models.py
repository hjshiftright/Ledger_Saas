"""SM-A Account Registry — data models.

Defines the Chart of Accounts (CoA) hierarchy and related types.

Business Rules (BR-A-01 through BR-A-11):
    BR-A-01  Every account must have a valid AccountType.
    BR-A-02  Root accounts have no parent; child type must equal parent type or be a sub-type.
    BR-A-03  Account hierarchy max depth is 4 levels.
    BR-A-04  An account cannot be its own ancestor (no cycles).
    BR-A-05  Cannot delete an account that has child accounts.
    BR-A-06  Cannot delete system-provisioned accounts (is_system=True).
    BR-A-07  Account name must be unique within the same parent.
    BR-A-08  Normal balance is inferred from AccountType
             (ASSET/EXPENSE → DEBIT; LIABILITY/EQUITY/INCOME → CREDIT).
    BR-A-09  Balance rolls up from leaf → root through the parent chain.
    BR-A-10  Moving an account preserves all its children.
    BR-A-11  Archiving an account hides it from UI but preserves all history.
"""

from __future__ import annotations

import uuid
from datetime import datetime, UTC
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


# ── Enums ─────────────────────────────────────────────────────────────────────

class AccountType(str, Enum):
    """Top-level account classification (double-entry accounting)."""

    ASSET      = "ASSET"
    LIABILITY  = "LIABILITY"
    EQUITY     = "EQUITY"
    INCOME     = "INCOME"
    EXPENSE    = "EXPENSE"


class AccountSubType(str, Enum):
    """Second-level sub-classification within an AccountType."""

    # ASSET sub-types
    CASH          = "CASH"
    BANK          = "BANK"
    INVESTMENT    = "INVESTMENT"
    FIXED_DEPOSIT = "FIXED_DEPOSIT"
    REAL_ESTATE   = "REAL_ESTATE"
    GOLD          = "GOLD"
    PPF_EPF       = "PPF_EPF"
    RECEIVABLE    = "RECEIVABLE"
    OTHER_ASSET   = "OTHER_ASSET"

    # LIABILITY sub-types
    CREDIT_CARD   = "CREDIT_CARD"
    HOME_LOAN     = "HOME_LOAN"
    VEHICLE_LOAN  = "VEHICLE_LOAN"
    PERSONAL_LOAN = "PERSONAL_LOAN"
    OTHER_LOAN    = "OTHER_LOAN"

    # EQUITY sub-types
    OPENING_BALANCE = "OPENING_BALANCE"
    RETAINED        = "RETAINED"

    # INCOME sub-types
    SALARY    = "SALARY"
    INTEREST  = "INTEREST"
    DIVIDEND  = "DIVIDEND"
    CAPITAL_GAINS = "CAPITAL_GAINS"
    RENTAL    = "RENTAL"
    OTHER_INCOME = "OTHER_INCOME"

    # EXPENSE sub-types
    FOOD          = "FOOD"
    TRANSPORT     = "TRANSPORT"
    HOUSING       = "HOUSING"
    HEALTHCARE    = "HEALTHCARE"
    EDUCATION     = "EDUCATION"
    ENTERTAINMENT = "ENTERTAINMENT"
    SHOPPING      = "SHOPPING"
    UTILITIES     = "UTILITIES"
    INSURANCE     = "INSURANCE"
    TAXES         = "TAXES"
    OTHER_EXPENSE = "OTHER_EXPENSE"

    # Generic
    GENERIC = "GENERIC"


class NormalBalance(str, Enum):
    """Whether increases are recorded as DEBIT or CREDIT (per double-entry rules)."""

    DEBIT  = "DEBIT"   # ASSET, EXPENSE
    CREDIT = "CREDIT"  # LIABILITY, EQUITY, INCOME


# BR-A-08: Normal balance inferred from type
_NORMAL_BALANCE_MAP: dict[AccountType, NormalBalance] = {
    AccountType.ASSET:     NormalBalance.DEBIT,
    AccountType.EXPENSE:   NormalBalance.DEBIT,
    AccountType.LIABILITY: NormalBalance.CREDIT,
    AccountType.EQUITY:    NormalBalance.CREDIT,
    AccountType.INCOME:    NormalBalance.CREDIT,
}


def normal_balance_for(account_type: AccountType) -> NormalBalance:
    """Return the normal balance for an account type (BR-A-08)."""
    return _NORMAL_BALANCE_MAP[account_type]


# ── Core Account model ────────────────────────────────────────────────────────

class Account(BaseModel):
    """One node in the Chart of Accounts tree.

    Leaf accounts (is_leaf=True) actually hold transactions.
    Parent accounts aggregate their children's balances.
    """

    account_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str

    # ── Identity ──────────────────────────────────────────────────────────────
    name: str = Field(..., min_length=1, max_length=120)
    code: str | None = None           # Optional short code, e.g. "1010"
    description: str = ""

    # ── Hierarchy ─────────────────────────────────────────────────────────────
    parent_id: str | None = None      # None means root account
    depth: int = Field(default=1, ge=1, le=4)   # BR-A-03: max depth 4

    # ── Classification ────────────────────────────────────────────────────────
    account_type: AccountType
    sub_type: AccountSubType = AccountSubType.GENERIC
    normal_balance: NormalBalance = NormalBalance.DEBIT  # computed in validator

    # ── State ─────────────────────────────────────────────────────────────────
    is_system: bool = False           # BR-A-06: system accounts cannot be deleted
    is_leaf: bool = True              # False if it has children
    is_active: bool = True            # BR-A-11: archived = is_active=False
    currency: str = "INR"

    # ── Balance (computed, not persisted) ─────────────────────────────────────
    balance: Decimal = Field(default=Decimal("0"))
    balance_book: Decimal = Field(default=Decimal("0"))        # cost basis
    balance_market: Decimal = Field(default=Decimal("0"))      # market value

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = {"frozen": False}

    @model_validator(mode="after")
    def _set_normal_balance(self) -> "Account":
        self.normal_balance = normal_balance_for(self.account_type)
        return self


class AccountTree(BaseModel):
    """Flat list of accounts with helpers for tree traversal."""

    accounts: list[Account] = Field(default_factory=list)

    def get(self, account_id: str) -> Account | None:
        for a in self.accounts:
            if a.account_id == account_id:
                return a
        return None

    def children(self, parent_id: str) -> list[Account]:
        return [a for a in self.accounts if a.parent_id == parent_id]

    def roots(self) -> list[Account]:
        return [a for a in self.accounts if a.parent_id is None]

    def ancestors(self, account_id: str) -> list[Account]:
        """Return ancestors from immediate parent → root."""
        result: list[Account] = []
        account = self.get(account_id)
        while account and account.parent_id:
            parent = self.get(account.parent_id)
            if parent:
                result.append(parent)
            account = parent
        return result

    def depth_of(self, account_id: str) -> int:
        return len(self.ancestors(account_id)) + 1

    def subtree_ids(self, account_id: str) -> set[str]:
        """Return all descendant account IDs (inclusive)."""
        result: set[str] = {account_id}
        queue = list(self.children(account_id))
        while queue:
            node = queue.pop()
            result.add(node.account_id)
            queue.extend(self.children(node.account_id))
        return result
