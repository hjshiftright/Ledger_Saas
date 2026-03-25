"""Tests for SM-A Account Registry — verifies BR-A-01 through BR-A-11."""

from __future__ import annotations

import pytest
from accounts.models import AccountSubType, AccountType
from accounts.service import AccountService, AccountServiceError
import accounts.service as _acct_svc_mod


@pytest.fixture()
def uid() -> str:
    return "user-test-001"


@pytest.fixture()
def svc(uid) -> AccountService:
    # Reset in-memory store for this user so tests are fully isolated
    _acct_svc_mod._store.pop(uid, None)
    return AccountService()



@pytest.fixture()
def asset_root(svc, uid) -> str:
    """Create a root asset account and return its ID."""
    acc = svc.create_account(uid, "Assets", AccountType.ASSET, AccountSubType.OTHER_ASSET)
    return acc.account_id


@pytest.fixture()
def bank_parent(svc, uid, asset_root) -> str:
    acc = svc.create_account(uid, "Bank Accounts", AccountType.ASSET, AccountSubType.BANK, parent_id=asset_root)
    return acc.account_id


# ── BR-A-01: valid type ───────────────────────────────────────────────────────

def test_br_a_01_valid_type_created(svc, uid):
    """BR-A-01: Account must have a valid AccountType."""
    acc = svc.create_account(uid, "Cash", AccountType.ASSET, AccountSubType.CASH)
    assert acc.account_type == AccountType.ASSET


# ── BR-A-02: parent validation ────────────────────────────────────────────────

def test_br_a_02_nonexistent_parent_raises(svc, uid):
    """BR-A-02: Parent must exist."""
    with pytest.raises(AccountServiceError, match="does not exist"):
        svc.create_account(uid, "Leaf", AccountType.ASSET, AccountSubType.CASH, parent_id="ghost-id")


def test_br_a_02_root_account_no_parent(svc, uid):
    """BR-A-02: Root accounts have parent_id=None."""
    acc = svc.create_account(uid, "Liabilities", AccountType.LIABILITY, AccountSubType.OTHER_LOAN)
    assert acc.parent_id is None
    assert acc.depth == 1


# ── BR-A-03: max depth 4 ──────────────────────────────────────────────────────

def test_br_a_03_max_depth_allow_4(svc, uid):
    """BR-A-03: Depth 4 should be allowed."""
    l1 = svc.create_account(uid, "L1", AccountType.ASSET, parent_id=None).account_id
    l2 = svc.create_account(uid, "L2", AccountType.ASSET, parent_id=l1).account_id
    l3 = svc.create_account(uid, "L3", AccountType.ASSET, parent_id=l2).account_id
    l4 = svc.create_account(uid, "L4", AccountType.ASSET, parent_id=l3)
    assert l4.depth == 4


def test_br_a_03_depth_5_raises(svc, uid):
    """BR-A-03: Depth > 4 must raise."""
    l1 = svc.create_account(uid, "L1", AccountType.ASSET, parent_id=None).account_id
    l2 = svc.create_account(uid, "L2", AccountType.ASSET, parent_id=l1).account_id
    l3 = svc.create_account(uid, "L3", AccountType.ASSET, parent_id=l2).account_id
    l4 = svc.create_account(uid, "L4", AccountType.ASSET, parent_id=l3).account_id
    with pytest.raises(AccountServiceError, match="depth"):
        svc.create_account(uid, "L5", AccountType.ASSET, parent_id=l4)


# ── BR-A-04: no cycles ────────────────────────────────────────────────────────

def test_br_a_04_self_parent_raises(svc, uid):
    """BR-A-04: Account cannot have itself as parent."""
    acc = svc.create_account(uid, "X", AccountType.ASSET)
    with pytest.raises(AccountServiceError, match="own parent"):
        svc.move_account(uid, acc.account_id, acc.account_id)


def test_br_a_04_ancestor_cycle_raises(svc, uid):
    """BR-A-04: Moving parent under its own descendant must fail."""
    parent = svc.create_account(uid, "Parent", AccountType.ASSET).account_id
    child  = svc.create_account(uid, "Child",  AccountType.ASSET, parent_id=parent).account_id
    with pytest.raises(AccountServiceError, match="descendants"):
        svc.move_account(uid, parent, child)


# ── BR-A-05: cannot delete with children ─────────────────────────────────────

def test_br_a_05_delete_with_children_raises(svc, uid, asset_root, bank_parent):
    """BR-A-05: Cannot delete an account that has children."""
    with pytest.raises(AccountServiceError, match="sub-accounts"):
        svc.delete_account(uid, asset_root)


def test_br_a_05_delete_leaf_succeeds(svc, uid, bank_parent):
    """BR-A-05: Deleting a leaf account succeeds."""
    leaf = svc.create_account(uid, "HDFC Savings", AccountType.ASSET,
                               AccountSubType.BANK, parent_id=bank_parent).account_id
    svc.delete_account(uid, leaf)
    with pytest.raises(AccountServiceError, match="not found"):
        svc.get(uid, leaf)


# ── BR-A-06: system accounts cannot be deleted ───────────────────────────────

def test_br_a_06_system_account_delete_raises(svc, uid):
    """BR-A-06: System accounts raise on delete."""
    acc = svc.create_account(uid, "System PPF", AccountType.ASSET,
                              AccountSubType.PPF_EPF, is_system=True)
    with pytest.raises(AccountServiceError, match="system account"):
        svc.delete_account(uid, acc.account_id)


# ── BR-A-07: unique name within parent ───────────────────────────────────────

def test_br_a_07_duplicate_name_under_same_parent_raises(svc, uid, bank_parent):
    """BR-A-07: Duplicate name under the same parent must raise."""
    svc.create_account(uid, "HDFC", AccountType.ASSET, parent_id=bank_parent)
    with pytest.raises(AccountServiceError, match="already exists"):
        svc.create_account(uid, "HDFC", AccountType.ASSET, parent_id=bank_parent)


def test_br_a_07_same_name_different_parent_ok(svc, uid, asset_root):
    """BR-A-07: Same name under different parents is allowed."""
    p1 = svc.create_account(uid, "P1", AccountType.ASSET, parent_id=asset_root).account_id
    p2 = svc.create_account(uid, "P2", AccountType.ASSET, parent_id=asset_root).account_id
    svc.create_account(uid, "Savings", AccountType.ASSET, parent_id=p1)
    svc.create_account(uid, "Savings", AccountType.ASSET, parent_id=p2)  # must not raise


# ── BR-A-08: normal balance follows type ─────────────────────────────────────

def test_br_a_08_asset_is_debit(svc, uid):
    from accounts.models import NormalBalance
    acc = svc.create_account(uid, "Cash", AccountType.ASSET)
    assert acc.normal_balance == NormalBalance.DEBIT


def test_br_a_08_income_is_credit(svc, uid):
    from accounts.models import NormalBalance
    acc = svc.create_account(uid, "Salary", AccountType.INCOME)
    assert acc.normal_balance == NormalBalance.CREDIT


def test_br_a_08_expense_is_debit(svc, uid):
    from accounts.models import NormalBalance
    acc = svc.create_account(uid, "Food", AccountType.EXPENSE)
    assert acc.normal_balance == NormalBalance.DEBIT


def test_br_a_08_liability_is_credit(svc, uid):
    from accounts.models import NormalBalance
    acc = svc.create_account(uid, "Credit Card", AccountType.LIABILITY)
    assert acc.normal_balance == NormalBalance.CREDIT


# ── BR-A-09: balance rollup ───────────────────────────────────────────────────

def test_br_a_09_balance_rollup(svc, uid, bank_parent):
    """BR-A-09: Parent balance rolls up from leaves."""
    from decimal import Decimal
    leaf1 = svc.create_account(uid, "HDFC", AccountType.ASSET, parent_id=bank_parent)
    leaf2 = svc.create_account(uid, "SBI",  AccountType.ASSET, parent_id=bank_parent)
    leaf1.balance = Decimal("10000")
    leaf2.balance = Decimal("5000")
    result = svc.compute_balance(uid, bank_parent)
    assert Decimal(result["balance"]) == Decimal("15000")


# ── BR-A-10: move preserves children ─────────────────────────────────────────

def test_br_a_10_move_with_children(svc, uid, asset_root):
    """BR-A-10: Moving a parent preserves all its children."""
    p1    = svc.create_account(uid, "P1",  AccountType.ASSET, parent_id=asset_root).account_id
    child = svc.create_account(uid, "Child", AccountType.ASSET, parent_id=p1).account_id
    p2    = svc.create_account(uid, "P2",  AccountType.ASSET, parent_id=asset_root).account_id

    svc.move_account(uid, p1, p2)

    moved_p1 = svc.get(uid, p1)
    moved_child = svc.get(uid, child)
    assert moved_p1.parent_id == p2
    assert moved_child.parent_id == p1


# ── BR-A-11: archive preserves history ───────────────────────────────────────

def test_br_a_11_archive_hides_from_active_list(svc, uid):
    """BR-A-11: Archived accounts are excluded from list by default."""
    acc = svc.create_account(uid, "Old Account", AccountType.ASSET)
    svc.archive_account(uid, acc.account_id)
    active = svc.list_accounts(uid, include_inactive=False)
    assert all(a.account_id != acc.account_id for a in active)


def test_br_a_11_archived_account_visible_when_requested(svc, uid):
    """BR-A-11: Archived accounts appear when include_inactive=True."""
    acc = svc.create_account(uid, "Old Account", AccountType.ASSET)
    svc.archive_account(uid, acc.account_id)
    all_accs = svc.list_accounts(uid, include_inactive=True)
    assert any(a.account_id == acc.account_id for a in all_accs)


def test_br_a_11_restore_reactivates(svc, uid):
    """BR-A-11: Restoring an archived account brings it back to active list."""
    acc = svc.create_account(uid, "Revived Account", AccountType.ASSET)
    svc.archive_account(uid, acc.account_id)
    svc.restore_account(uid, acc.account_id)
    active = svc.list_accounts(uid, include_inactive=False)
    assert any(a.account_id == acc.account_id for a in active)


# ── Provision defaults ────────────────────────────────────────────────────────

def test_provision_defaults_creates_accounts(svc, uid):
    """provision_defaults() should create a non-trivial CoA."""
    accounts = svc.provision_defaults(uid)
    assert len(accounts) >= 30  # PRD R1.3 specifies 20+ default accounts
    types_seen = {a.account_type for a in accounts}
    assert types_seen == {AccountType.ASSET, AccountType.LIABILITY,
                          AccountType.EQUITY, AccountType.INCOME, AccountType.EXPENSE}


def test_provision_defaults_all_system(svc, uid):
    """All provisioned defaults should be marked as system accounts."""
    accounts = svc.provision_defaults(uid)
    assert all(a.is_system for a in accounts)
