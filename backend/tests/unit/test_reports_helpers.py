"""Unit tests for the pure-Python helper functions in api/routers/reports.py.

These tests require no database, HTTP client, or FastAPI setup — they verify the
core computation logic independently of the routing layer.

Coverage:
    _signed_balance       — DEBIT-normal and CREDIT-normal account direction
    _month_offset         — calendar arithmetic, year-wrap on January
    _month_end            — last day of any month, including Feb in a leap year
    _strip_internal       — removes _bal from flat and nested trees
    _type_total           — sums signed balances across a list of accounts
    _build_tree           — recursive CoA tree construction with placeholder groups
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from api.routers.reports import (
    _build_tree,
    _month_end,
    _month_offset,
    _signed_balance,
    _strip_internal,
    _type_total,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers / mocks
# ─────────────────────────────────────────────────────────────────────────────

class _Acc:
    """Minimal Account stand-in for the tree-building helpers."""

    def __init__(
        self,
        id: int,
        code: str,
        name: str,
        account_type: str,
        normal_balance: str,
        parent_id: int | None = None,
        is_placeholder: bool = False,
        is_active: bool = True,
        display_order: int = 0,
    ):
        self.id            = id
        self.code          = code
        self.name          = name
        self.account_type  = account_type
        self.normal_balance = normal_balance
        self.parent_id     = parent_id
        self.is_placeholder = is_placeholder
        self.is_active     = is_active
        self.display_order = display_order


# ─────────────────────────────────────────────────────────────────────────────
# _signed_balance
# ─────────────────────────────────────────────────────────────────────────────

class TestSignedBalance:
    def test_debit_normal_positive_when_debits_exceed_credits(self):
        """Asset / Expense accounts: DR more than CR → positive balance."""
        assert _signed_balance(Decimal("1000"), Decimal("300"), "DEBIT") == Decimal("700")

    def test_debit_normal_zero_when_equal(self):
        assert _signed_balance(Decimal("500"), Decimal("500"), "DEBIT") == Decimal("0")

    def test_debit_normal_negative_when_credits_exceed_debits(self):
        """Unusual state (overdraft), but function should handle it."""
        assert _signed_balance(Decimal("100"), Decimal("500"), "DEBIT") == Decimal("-400")

    def test_credit_normal_positive_when_credits_exceed_debits(self):
        """Income / Liability accounts: CR more than DR → positive balance."""
        assert _signed_balance(Decimal("200"), Decimal("1500"), "CREDIT") == Decimal("1300")

    def test_credit_normal_zero_when_equal(self):
        assert _signed_balance(Decimal("750"), Decimal("750"), "CREDIT") == Decimal("0")

    def test_credit_normal_negative_when_debits_exceed_credits(self):
        assert _signed_balance(Decimal("900"), Decimal("100"), "CREDIT") == Decimal("-800")

    def test_all_zeros_returns_zero(self):
        for normal in ("DEBIT", "CREDIT"):
            assert _signed_balance(Decimal(0), Decimal(0), normal) == Decimal("0")


# ─────────────────────────────────────────────────────────────────────────────
# _month_offset
# ─────────────────────────────────────────────────────────────────────────────

class TestMonthOffset:
    def test_zero_offset_is_current_month(self):
        today = date(2026, 3, 15)
        year, month = _month_offset(today, 0)
        assert (year, month) == (2026, 3)

    def test_one_month_back(self):
        today = date(2026, 3, 15)
        assert _month_offset(today, 1) == (2026, 2)

    def test_wraps_to_previous_year_from_january(self):
        """Going 1 month back from January should yield December of prior year."""
        today = date(2026, 1, 10)
        assert _month_offset(today, 1) == (2025, 12)

    def test_wraps_multiple_months_back_across_year_boundary(self):
        today = date(2026, 3, 1)
        assert _month_offset(today, 15) == (2024, 12)

    def test_11_months_back_from_march(self):
        today = date(2026, 3, 21)
        assert _month_offset(today, 11) == (2025, 4)


# ─────────────────────────────────────────────────────────────────────────────
# _month_end
# ─────────────────────────────────────────────────────────────────────────────

class TestMonthEnd:
    def test_31_day_month(self):
        assert _month_end(2026, 1) == date(2026, 1, 31)

    def test_30_day_month(self):
        assert _month_end(2026, 4) == date(2026, 4, 30)

    def test_february_non_leap_year(self):
        assert _month_end(2025, 2) == date(2025, 2, 28)

    def test_february_leap_year(self):
        assert _month_end(2024, 2) == date(2024, 2, 29)

    def test_december(self):
        assert _month_end(2025, 12) == date(2025, 12, 31)


# ─────────────────────────────────────────────────────────────────────────────
# _strip_internal
# ─────────────────────────────────────────────────────────────────────────────

class TestStripInternal:
    def test_removes_bal_key_from_flat_list(self):
        nodes = [{"id": 1, "name": "A", "balance": "100", "_bal": Decimal("100"), "children": []}]
        result = _strip_internal(nodes)
        assert "_bal" not in result[0]
        assert result[0]["balance"] == "100"

    def test_recursive_removal(self):
        nodes = [
            {
                "id": 1, "name": "Parent", "balance": "500", "_bal": Decimal("500"),
                "children": [
                    {"id": 2, "name": "Child", "balance": "200", "_bal": Decimal("200"), "children": []},
                ],
            }
        ]
        _strip_internal(nodes)
        assert "_bal" not in nodes[0]
        assert "_bal" not in nodes[0]["children"][0]

    def test_empty_list_is_noop(self):
        assert _strip_internal([]) == []

    def test_returns_same_list_object(self):
        nodes = [{"id": 1, "balance": "0", "_bal": Decimal(0), "children": []}]
        result = _strip_internal(nodes)
        assert result is nodes


# ─────────────────────────────────────────────────────────────────────────────
# _type_total
# ─────────────────────────────────────────────────────────────────────────────

class TestTypeTotal:
    def _bank(self, id_=1):
        return _Acc(id_, f"11{id_:02d}", "Bank", "ASSET", "DEBIT")

    def _salary(self, id_=10):
        return _Acc(id_, "3101", "Salary", "INCOME", "CREDIT")

    def test_sums_assets_ignores_income(self):
        leafs = [self._bank(1), self._bank(2), self._salary(10)]
        sums  = {
            1:  (Decimal("10000"), Decimal("2000")),   # bank1 balance = 8000
            2:  (Decimal("5000"),  Decimal("1000")),   # bank2 balance = 4000
            10: (Decimal("0"),     Decimal("9000")),   # salary balance = 9000 (ignored)
        }
        total = _type_total(leafs, sums, "ASSET")
        assert total == Decimal("12000")

    def test_zero_sums_for_accounts_not_in_dict(self):
        leafs = [self._bank(1)]
        sums  = {}  # no activity
        assert _type_total(leafs, sums, "ASSET") == Decimal("0")

    def test_income_total_uses_credit_normal_balance(self):
        leafs = [self._salary(10)]
        sums  = {10: (Decimal("0"), Decimal("75000"))}
        assert _type_total(leafs, sums, "INCOME") == Decimal("75000")

    def test_empty_leafs_returns_zero(self):
        assert _type_total([], {}, "ASSET") == Decimal("0")


# ─────────────────────────────────────────────────────────────────────────────
# _build_tree
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildTree:
    def test_empty_accounts_returns_empty_list(self):
        assert _build_tree([], {}, None, "ASSET") == []

    def test_single_leaf_with_no_transactions(self):
        acc = _Acc(1, "1101", "HDFC Savings", "ASSET", "DEBIT", parent_id=None)
        result = _build_tree([acc], {}, None, "ASSET")
        assert len(result) == 1
        node = result[0]
        assert node["id"]      == 1
        assert node["code"]    == "1101"
        assert node["balance"] == "0"
        assert node["is_group"] is False
        assert node["_bal"]    == Decimal("0")

    def test_leaf_with_debit_activity(self):
        acc = _Acc(1, "1101", "HDFC", "ASSET", "DEBIT", parent_id=None)
        sums = {1: (Decimal("50000"), Decimal("10000"))}
        result = _build_tree([acc], sums, None, "ASSET")
        assert result[0]["balance"] == "40000"
        assert result[0]["_bal"]    == Decimal("40000")

    def test_placeholder_sums_children_balances(self):
        """Placeholder parent should carry sum of all children."""
        parent = _Acc(1, "1100", "Bank Accounts", "ASSET", "DEBIT", parent_id=None,
                      is_placeholder=True)
        child1 = _Acc(2, "1101", "HDFC", "ASSET", "DEBIT", parent_id=1)
        child2 = _Acc(3, "1102", "SBI",  "ASSET", "DEBIT", parent_id=1)
        sums   = {2: (Decimal("20000"), Decimal("5000")), 3: (Decimal("30000"), Decimal("0"))}
        result = _build_tree([parent, child1, child2], sums, None, "ASSET")
        assert len(result) == 1
        parent_node = result[0]
        assert parent_node["is_group"]  is True
        # parent balance = child1(15000) + child2(30000) = 45000
        assert parent_node["_bal"]      == Decimal("45000")
        assert len(parent_node["children"]) == 2

    def test_inactive_accounts_excluded(self):
        active   = _Acc(1, "1101", "Active",   "ASSET", "DEBIT")
        inactive = _Acc(2, "1102", "Inactive", "ASSET", "DEBIT", is_active=False)
        result = _build_tree([active, inactive], {}, None, "ASSET")
        ids = [n["id"] for n in result]
        assert 1 in ids
        assert 2 not in ids

    def test_different_account_type_excluded(self):
        asset = _Acc(1, "1101", "Bank",   "ASSET",     "DEBIT")
        liab  = _Acc(2, "2100", "CC",     "LIABILITY", "CREDIT")
        result = _build_tree([asset, liab], {}, None, "ASSET")
        assert len(result) == 1
        assert result[0]["id"] == 1

    def test_children_sorted_by_display_order(self):
        parent = _Acc(1, "1000", "Assets", "ASSET", "DEBIT", is_placeholder=True)
        b      = _Acc(3, "1102", "SBI",  "ASSET", "DEBIT", parent_id=1, display_order=2)
        a      = _Acc(2, "1101", "HDFC", "ASSET", "DEBIT", parent_id=1, display_order=1)
        result = _build_tree([parent, b, a], {}, None, "ASSET")
        children = result[0]["children"]
        assert children[0]["id"] == 2  # display_order=1 first
        assert children[1]["id"] == 3
