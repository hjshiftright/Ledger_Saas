"""SM-A Account Registry — business logic and tree operations.

AccountService enforces all business rules (BR-A-01 through BR-A-11).
It uses an in-memory store; swap _store with a DB session in production.
"""

from __future__ import annotations
from datetime import datetime, timezone
from accounts.models import (
    Account,
    AccountSubType,
    AccountTree,
    AccountType,
    NormalBalance,
    normal_balance_for,
)

# ── In-memory store (replace with DB in production) ───────────────────────────
# Keyed by user_id → {account_id: Account}
_store: dict[str, dict[str, Account]] = {}


class AccountServiceError(Exception):
    """Raised when a business-rule violation is detected."""


class AccountService:
    """CRUD + tree operations for Chart of Accounts."""

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _user_accounts(self, user_id: str) -> dict[str, Account]:
        return _store.setdefault(user_id, {})

    def _get_tree(self, user_id: str) -> AccountTree:
        return AccountTree(accounts=list(self._user_accounts(user_id).values()))

    # ── Queries ───────────────────────────────────────────────────────────────

    def get(self, user_id: str, account_id: str) -> Account:
        acc = self._user_accounts(user_id).get(account_id)
        if acc is None:
            raise AccountServiceError(f"Account {account_id} not found.")
        return acc

    def list_accounts(
        self,
        user_id: str,
        account_type: AccountType | None = None,
        include_inactive: bool = False,
    ) -> list[Account]:
        accs = list(self._user_accounts(user_id).values())
        if not include_inactive:
            accs = [a for a in accs if a.is_active]
        if account_type:
            accs = [a for a in accs if a.account_type == account_type]
        return sorted(accs, key=lambda a: (a.depth, a.name))

    def get_tree(self, user_id: str) -> AccountTree:
        return AccountTree(accounts=self.list_accounts(user_id))

    def get_children(self, user_id: str, account_id: str) -> list[Account]:
        return self._get_tree(user_id).children(account_id)

    # ── Create ────────────────────────────────────────────────────────────────

    def create_account(
        self,
        user_id: str,
        name: str,
        account_type: AccountType,
        sub_type: AccountSubType = AccountSubType.GENERIC,
        parent_id: str | None = None,
        code: str | None = None,
        description: str = "",
        currency: str = "INR",
        is_system: bool = False,
    ) -> Account:
        tree = self._get_tree(user_id)

        # BR-A-01: type must be valid (enforced by AccountType enum)

        # BR-A-02 / BR-A-04: validate parent
        depth = 1
        if parent_id:
            parent = self._user_accounts(user_id).get(parent_id)
            if parent is None:
                raise AccountServiceError(f"Parent account {parent_id} does not exist.")
            depth = parent.depth + 1
            # BR-A-03: max depth 4
            if depth > 4:
                raise AccountServiceError(
                    f"Maximum account hierarchy depth is 4. "
                    f"Parent '{parent.name}' is already at depth {parent.depth}."
                )

        # BR-A-07: unique name within same parent
        siblings = tree.children(parent_id) if parent_id else tree.roots()
        if any(s.name.lower() == name.lower() for s in siblings):
            raise AccountServiceError(
                f"An account named '{name}' already exists under the same parent."
            )

        account = Account(
            user_id=user_id,
            name=name,
            account_type=account_type,
            sub_type=sub_type,
            parent_id=parent_id,
            depth=depth,
            code=code,
            description=description,
            currency=currency,
            is_system=is_system,
        )
        self._user_accounts(user_id)[account.account_id] = account

        # Mark parent as non-leaf (it now has a child)
        if parent_id and parent_id in self._user_accounts(user_id):
            self._user_accounts(user_id)[parent_id].is_leaf = False

        return account

    # ── Update ────────────────────────────────────────────────────────────────

    def update_account(
        self,
        user_id: str,
        account_id: str,
        name: str | None = None,
        description: str | None = None,
        code: str | None = None,
        sub_type: AccountSubType | None = None,
    ) -> Account:
        acc = self.get(user_id, account_id)
        tree = self._get_tree(user_id)

        if name and name != acc.name:
            # BR-A-07: unique name within same parent
            siblings = tree.children(acc.parent_id) if acc.parent_id else tree.roots()
            if any(s.name.lower() == name.lower() and s.account_id != account_id for s in siblings):
                raise AccountServiceError(
                    f"An account named '{name}' already exists under the same parent."
                )
            acc.name = name

        if description is not None:
            acc.description = description
        if code is not None:
            acc.code = code
        if sub_type is not None:
            acc.sub_type = sub_type

        from datetime import datetime
        acc.updated_at = datetime.now(timezone.utc)
        return acc

    # ── Move ──────────────────────────────────────────────────────────────────

    def move_account(self, user_id: str, account_id: str, new_parent_id: str | None) -> Account:
        """Move an account to a different parent (BR-A-10: children move with it)."""
        acc = self.get(user_id, account_id)
        tree = self._get_tree(user_id)

        # BR-A-04: prevent cycles
        if new_parent_id:
            if new_parent_id == account_id:
                raise AccountServiceError("An account cannot be its own parent.")
            descendants = tree.subtree_ids(account_id)
            if new_parent_id in descendants:
                raise AccountServiceError("Cannot move an account to one of its own descendants.")

        # BR-A-03: depth check
        if new_parent_id:
            new_parent = self.get(user_id, new_parent_id)
            new_depth = new_parent.depth + 1
            if new_depth > 4:
                raise AccountServiceError(
                    f"Moving here would put '{acc.name}' at depth {new_depth}, exceeding max depth 4."
                )
        else:
            new_depth = 1

        # BR-A-07: unique name at new parent
        new_siblings = tree.children(new_parent_id) if new_parent_id else tree.roots()
        if any(s.name.lower() == acc.name.lower() and s.account_id != account_id for s in new_siblings):
            raise AccountServiceError(
                f"An account named '{acc.name}' already exists at the target location."
            )

        old_parent_id = acc.parent_id
        acc.parent_id = new_parent_id
        acc.depth     = new_depth
        self._fix_depths(user_id, account_id)

        # Update old parent's is_leaf status
        if old_parent_id and not tree.children(old_parent_id):
            old_parent = self._user_accounts(user_id).get(old_parent_id)
            if old_parent:
                old_parent.is_leaf = True

        # Update new parent's is_leaf status
        if new_parent_id and new_parent_id in self._user_accounts(user_id):
            self._user_accounts(user_id)[new_parent_id].is_leaf = False

        from datetime import datetime
        acc.updated_at = datetime.now(timezone.utc)
        return acc

    def _fix_depths(self, user_id: str, root_id: str) -> None:
        """Recursively recompute depths after a move (BR-A-10)."""
        store = self._user_accounts(user_id)
        root  = store.get(root_id)
        if root is None:
            return
        for child in AccountTree(accounts=list(store.values())).children(root_id):
            child.depth = root.depth + 1
            self._fix_depths(user_id, child.account_id)

    # ── Delete / Archive ──────────────────────────────────────────────────────

    def delete_account(self, user_id: str, account_id: str) -> None:
        """Hard-delete an account (BR-A-05, BR-A-06)."""
        acc = self.get(user_id, account_id)

        # BR-A-06: system accounts cannot be deleted
        if acc.is_system:
            raise AccountServiceError(
                f"Account '{acc.name}' is a system account and cannot be deleted."
            )

        # BR-A-05: cannot delete if it has children
        tree = self._get_tree(user_id)
        if tree.children(account_id):
            raise AccountServiceError(
                f"Account '{acc.name}' has sub-accounts. Delete or move them first."
            )

        # Update parent's is_leaf
        if acc.parent_id and acc.parent_id in self._user_accounts(user_id):
            siblings_after = [
                s for s in tree.children(acc.parent_id)
                if s.account_id != account_id
            ]
            if not siblings_after:
                self._user_accounts(user_id)[acc.parent_id].is_leaf = True

        del self._user_accounts(user_id)[account_id]

    def archive_account(self, user_id: str, account_id: str) -> Account:
        """Soft-delete (archive) an account — preserves history (BR-A-11)."""
        acc = self.get(user_id, account_id)
        if acc.is_system:
            raise AccountServiceError(f"Cannot archive system account '{acc.name}'.")
        acc.is_active = False
        from datetime import datetime
        acc.updated_at = datetime.now(timezone.utc)
        return acc

    def restore_account(self, user_id: str, account_id: str) -> Account:
        """Restore an archived account."""
        acc = self.get(user_id, account_id)
        acc.is_active = True
        from datetime import datetime, timezone
        acc.updated_at = datetime.now(timezone.utc)
        return acc

    # ── Balance rollup (BR-A-09) ──────────────────────────────────────────────

    def compute_balance(self, user_id: str, account_id: str) -> dict:
        """Recursively sum balances for an account and all its descendants."""
        tree   = self._get_tree(user_id)
        subtree = tree.subtree_ids(account_id)
        total  = sum(
            self._user_accounts(user_id)[aid].balance
            for aid in subtree
            if aid in self._user_accounts(user_id)
        )
        return {"account_id": account_id, "balance": total}

    # ── Default CoA provisioning ──────────────────────────────────────────────

    def provision_defaults(self, user_id: str) -> list[Account]:
        """Create the standard Indian household Chart of Accounts (R1.3)."""
        created: list[Account] = []

        def add(name, atype, sub, parent_id=None, code=None, is_system=True):
            a = self.create_account(
                user_id=user_id, name=name, account_type=atype,
                sub_type=sub, parent_id=parent_id, code=code, is_system=is_system,
            )
            created.append(a)
            return a.account_id

        # ── Assets ────────────────────────────────────────────────────────────
        assets = add("Assets", AccountType.ASSET, AccountSubType.OTHER_ASSET, code="1000")
        cash     = add("Cash & Bank",   AccountType.ASSET, AccountSubType.BANK,         assets, "1100")
        add("Cash in Hand",          AccountType.ASSET, AccountSubType.CASH,         cash,   "1101")
        add("Savings Account",       AccountType.ASSET, AccountSubType.BANK,         cash,   "1102")
        invest   = add("Investments",  AccountType.ASSET, AccountSubType.INVESTMENT,    assets, "1200")
        add("Mutual Funds",          AccountType.ASSET, AccountSubType.INVESTMENT,    invest, "1201")
        add("Stocks / Equities",     AccountType.ASSET, AccountSubType.INVESTMENT,    invest, "1202")
        add("Fixed Deposits",        AccountType.ASSET, AccountSubType.FIXED_DEPOSIT, invest, "1203")
        add("PPF / EPF / NPS",       AccountType.ASSET, AccountSubType.PPF_EPF,       invest, "1204")
        add("Gold",                  AccountType.ASSET, AccountSubType.GOLD,          assets, "1300")
        add("Real Estate",           AccountType.ASSET, AccountSubType.REAL_ESTATE,   assets, "1400")

        # ── Liabilities ───────────────────────────────────────────────────────
        liabs = add("Liabilities", AccountType.LIABILITY, AccountSubType.OTHER_LOAN, code="2000")
        add("Credit Cards",  AccountType.LIABILITY, AccountSubType.CREDIT_CARD,   liabs, "2100")
        add("Home Loan",     AccountType.LIABILITY, AccountSubType.HOME_LOAN,      liabs, "2200")
        add("Vehicle Loan",  AccountType.LIABILITY, AccountSubType.VEHICLE_LOAN,   liabs, "2300")
        add("Personal Loan", AccountType.LIABILITY, AccountSubType.PERSONAL_LOAN,  liabs, "2400")
        add("Transfer Clearing", AccountType.LIABILITY, AccountSubType.OTHER_LOAN,  liabs, "2999")

        # ── Equity ────────────────────────────────────────────────────────────
        equity = add("Equity", AccountType.EQUITY, AccountSubType.RETAINED, code="3000")
        add("Opening Balances", AccountType.EQUITY, AccountSubType.OPENING_BALANCE, equity, "3100")

        # ── Income ────────────────────────────────────────────────────────────
        income = add("Income", AccountType.INCOME, AccountSubType.OTHER_INCOME, code="4000")
        add("Salary / Wages",    AccountType.INCOME, AccountSubType.SALARY,        income, "4100")
        add("Interest Income",   AccountType.INCOME, AccountSubType.INTEREST,      income, "4200")
        add("Dividend Income",   AccountType.INCOME, AccountSubType.DIVIDEND,      income, "4300")
        add("Capital Gains",     AccountType.INCOME, AccountSubType.CAPITAL_GAINS, income, "4400")
        add("Rental Income",     AccountType.INCOME, AccountSubType.RENTAL,        income, "4500")
        add("Refunds Received",  AccountType.INCOME, AccountSubType.OTHER_INCOME,  income, "4600")
        add("Cashback Income",   AccountType.INCOME, AccountSubType.OTHER_INCOME,  income, "4700")
        add("Other Income",      AccountType.INCOME, AccountSubType.OTHER_INCOME,  income, "4900")

        # ── Expenses ──────────────────────────────────────────────────────────
        exp = add("Expenses", AccountType.EXPENSE, AccountSubType.OTHER_EXPENSE, code="5000")
        add("Groceries",         AccountType.EXPENSE, AccountSubType.FOOD,          exp, "5100")
        add("Dining Out",        AccountType.EXPENSE, AccountSubType.FOOD,          exp, "5101")
        add("Transportation",    AccountType.EXPENSE, AccountSubType.TRANSPORT,     exp, "5200")
        add("Housing / Rent",    AccountType.EXPENSE, AccountSubType.HOUSING,       exp, "5300")
        add("Utilities",         AccountType.EXPENSE, AccountSubType.UTILITIES,     exp, "5400")
        add("Mobile & Internet", AccountType.EXPENSE, AccountSubType.UTILITIES,     exp, "5401")
        add("Healthcare",        AccountType.EXPENSE, AccountSubType.HEALTHCARE,    exp, "5500")
        add("Education",         AccountType.EXPENSE, AccountSubType.EDUCATION,     exp, "5600")
        add("Shopping",          AccountType.EXPENSE, AccountSubType.SHOPPING,      exp, "5700")
        add("Entertainment",     AccountType.EXPENSE, AccountSubType.ENTERTAINMENT, exp, "5800")
        add("Insurance Premium", AccountType.EXPENSE, AccountSubType.INSURANCE,     exp, "5900")
        add("Taxes Paid",        AccountType.EXPENSE, AccountSubType.TAXES,         exp, "5950")
        add("Miscellaneous",     AccountType.EXPENSE, AccountSubType.OTHER_EXPENSE, exp, "5999")

        return created
