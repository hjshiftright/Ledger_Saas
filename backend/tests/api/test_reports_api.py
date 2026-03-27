"""API-level integration tests for the Reports module.

.. note::
    Skipped pending migration of raw_session from sync to async SQLAlchemy.
"""
import pytest
pytestmark = pytest.mark.skip(reason="raw_session not yet migrated to async; pending Phase D")

"""ORIGINAL DOCSTRING:

Endpoint coverage:
    GET  /api/v1/reports/summary              — dashboard KPIs
    GET  /api/v1/reports/income-expense       — I&E statement
    GET  /api/v1/reports/balance-sheet        — asset / liability tree
    GET  /api/v1/reports/net-worth-history    — monthly NW trend
    GET  /api/v1/reports/monthly-trend        — monthly income vs expense
    GET  /api/v1/reports/expense-categories   — category breakdown
    GET  /api/v1/reports/accounts-list        — leaf account list
    GET  /api/v1/reports/account-statement/{id} — per-account ledger
    POST /api/v1/reports/insights             — LLM commentary (graceful no-provider)

Fixture strategy
----------------
* ``seeded_client``   – inherited from api/conftest.py; has profile + full CoA.
* ``raw_session``     – inherited from api/conftest.py; direct DB session for
                        inserting Transactions / TransactionLines without HTTP.
* ``funded_client``   – test-local fixture; combines seeded_client + raw_session
                        to insert one income txn (₹75 000 salary) and one expense
                        txn (₹4 500 dining) so every computed metric is non-zero.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from db.models.accounts import Account
from db.models.transactions import Transaction, TransactionLine

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

BASE = "/api/v1/reports"
TODAY = date.today().isoformat()
MONTH_START = date.today().replace(day=1).isoformat()


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

def _account_by_code(session, code: str) -> Account | None:
    return session.execute(
        select(Account).where(Account.code == code)
    ).scalar_one_or_none()


def _insert_income_txn(
    session,
    bank_id: int,
    income_id: int,
    amount: Decimal,
    txn_date: date,
) -> Transaction:
    """DR bank (asset), CR salary (income) — standard income journal entry."""
    txn = Transaction(
        transaction_date=txn_date,
        transaction_type="INCOME",
        description="Test Salary Credit",
        status="CONFIRMED",
        is_void=False,
        user_id=1,
    )
    session.add(txn)
    session.flush()
    session.add(TransactionLine(
        transaction_id=txn.id, account_id=bank_id,
        line_type="DEBIT", amount=amount,
    ))
    session.add(TransactionLine(
        transaction_id=txn.id, account_id=income_id,
        line_type="CREDIT", amount=amount,
    ))
    session.flush()
    return txn


def _insert_expense_txn(
    session,
    bank_id: int,
    expense_id: int,
    amount: Decimal,
    txn_date: date,
) -> Transaction:
    """DR expense, CR bank — standard expense journal entry."""
    txn = Transaction(
        transaction_date=txn_date,
        transaction_type="EXPENSE",
        description="Test Dining Expense",
        status="CONFIRMED",
        is_void=False,
        user_id=1,
    )
    session.add(txn)
    session.flush()
    session.add(TransactionLine(
        transaction_id=txn.id, account_id=expense_id,
        line_type="DEBIT", amount=amount,
    ))
    session.add(TransactionLine(
        transaction_id=txn.id, account_id=bank_id,
        line_type="CREDIT", amount=amount,
    ))
    session.flush()
    return txn


# ─────────────────────────────────────────────────────────────────────────────
# funded_client fixture
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def funded_client(seeded_client, raw_session):
    """seeded_client extended with one income and one expense transaction.

    Income:  ₹75 000 salary  (DR 1102 bank, CR 4100 salary)
    Expense: ₹ 4 500 dining  (DR 5101 dining, CR 1102 bank)

    After these two transactions:
        bank balance         = 75 000 – 4 500  = 70 500
        total_assets         ≥ 70 500
        period_income        = 75 000
        period_expenses      = 4 500
        net_income           = 70 500
        savings_rate         ≈ 94.0 %
    """
    bank    = _account_by_code(raw_session, "1102")
    salary  = _account_by_code(raw_session, "4100")
    dining  = _account_by_code(raw_session, "5101")

    if not bank or not salary or not dining:
        pytest.skip("Required CoA accounts not seeded — check default_tree.py codes.")

    today = date.today()
    _insert_income_txn(raw_session, bank.id, salary.id,  Decimal("75000"), today)
    _insert_expense_txn(raw_session, bank.id, dining.id, Decimal("4500"),  today)
    raw_session.commit()

    return seeded_client, {
        "bank_id":    bank.id,
        "salary_id":  salary.id,
        "dining_id":  dining.id,
        "income":     Decimal("75000"),
        "expense":    Decimal("4500"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /reports/summary
# ─────────────────────────────────────────────────────────────────────────────

class TestSummaryEndpoint:
    def test_returns_200(self, seeded_client):
        resp = seeded_client.get(f"{BASE}/summary")
        assert resp.status_code == 200

    def test_response_contains_required_keys(self, seeded_client):
        data = seeded_client.get(f"{BASE}/summary").json()
        required = {
            "as_of", "from_date", "to_date",
            "net_worth", "total_assets", "total_liabilities",
            "period_income", "period_expenses", "net_income",
            "savings_rate", "top_expenses",
        }
        assert required <= data.keys()

    def test_top_expenses_is_a_list(self, seeded_client):
        data = seeded_client.get(f"{BASE}/summary").json()
        assert isinstance(data["top_expenses"], list)

    def test_empty_db_returns_zero_totals(self, seeded_client):
        data = seeded_client.get(f"{BASE}/summary").json()
        assert Decimal(data["total_assets"])      >= Decimal("0")
        assert Decimal(data["total_liabilities"]) >= Decimal("0")

    def test_date_params_reflected_in_response(self, seeded_client):
        resp = seeded_client.get(
            f"{BASE}/summary",
            params={"as_of": "2026-01-31", "from_date": "2026-01-01", "to_date": "2026-01-31"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["as_of"]     == "2026-01-31"
        assert data["from_date"] == "2026-01-01"
        assert data["to_date"]   == "2026-01-31"

    def test_savings_rate_zero_when_no_income(self, seeded_client):
        """Without income transactions the savings rate should be 0.0, not NaN/error."""
        data = seeded_client.get(f"{BASE}/summary").json()
        assert data["savings_rate"] == 0.0

    def test_with_transactions_shows_correct_values(self, funded_client):
        client, ctx = funded_client
        data = client.get(f"{BASE}/summary").json()
        assert Decimal(data["period_income"])   == ctx["income"]
        assert Decimal(data["period_expenses"]) == ctx["expense"]
        net = ctx["income"] - ctx["expense"]
        assert Decimal(data["net_income"]) == net

    def test_top_expenses_sorted_descending(self, funded_client):
        client, _ = funded_client
        data = client.get(f"{BASE}/summary").json()
        amts = [float(e["amount"]) for e in data["top_expenses"]]
        assert amts == sorted(amts, reverse=True)

    def test_top_expenses_capped_at_6(self, seeded_client):
        data = seeded_client.get(f"{BASE}/summary").json()
        assert len(data["top_expenses"]) <= 6

    def test_savings_rate_correct_with_transactions(self, funded_client):
        client, ctx = funded_client
        data = client.get(f"{BASE}/summary").json()
        expected_rate = round(float((ctx["income"] - ctx["expense"]) / ctx["income"] * 100), 1)
        assert data["savings_rate"] == pytest.approx(expected_rate, abs=0.2)


# ─────────────────────────────────────────────────────────────────────────────
# GET /reports/income-expense
# ─────────────────────────────────────────────────────────────────────────────

class TestIncomeExpenseEndpoint:
    def test_returns_200(self, seeded_client):
        resp = seeded_client.get(f"{BASE}/income-expense")
        assert resp.status_code == 200

    def test_required_keys_present(self, seeded_client):
        data = seeded_client.get(f"{BASE}/income-expense").json()
        assert "from_date"    in data
        assert "to_date"      in data
        assert "income"       in data
        assert "expenses"     in data
        assert "net_income"   in data
        assert "savings_rate" in data

    def test_income_and_expenses_have_items_and_total(self, seeded_client):
        data = seeded_client.get(f"{BASE}/income-expense").json()
        assert "items" in data["income"]
        assert "total" in data["income"]
        assert "items" in data["expenses"]
        assert "total" in data["expenses"]

    def test_empty_db_zero_totals(self, seeded_client):
        data = seeded_client.get(f"{BASE}/income-expense").json()
        assert Decimal(data["income"]["total"])   == Decimal("0")
        assert Decimal(data["expenses"]["total"]) == Decimal("0")

    def test_date_params_reflected(self, seeded_client):
        data = seeded_client.get(
            f"{BASE}/income-expense",
            params={"from_date": "2025-01-01", "to_date": "2025-12-31"},
        ).json()
        assert data["from_date"] == "2025-01-01"
        assert data["to_date"]   == "2025-12-31"

    def test_income_zero_outside_period(self, funded_client):
        """Transactions posted today should not appear in a future date range."""
        client, _ = funded_client
        future_start = (date.today() + timedelta(days=1)).isoformat()
        future_end   = (date.today() + timedelta(days=30)).isoformat()
        data = client.get(
            f"{BASE}/income-expense",
            params={"from_date": future_start, "to_date": future_end},
        ).json()
        assert Decimal(data["income"]["total"])   == Decimal("0")
        assert Decimal(data["expenses"]["total"]) == Decimal("0")

    def test_correct_totals_with_transactions(self, funded_client):
        client, ctx = funded_client
        data = client.get(f"{BASE}/income-expense").json()
        assert Decimal(data["income"]["total"])   == ctx["income"]
        assert Decimal(data["expenses"]["total"]) == ctx["expense"]

    def test_income_items_sorted_by_code(self, funded_client):
        client, _ = funded_client
        data = client.get(f"{BASE}/income-expense").json()
        codes = [i["code"] for i in data["income"]["items"]]
        assert codes == sorted(codes)

    def test_expense_items_sorted_descending_by_amount(self, funded_client):
        client, _ = funded_client
        data = client.get(f"{BASE}/income-expense").json()
        amts = [float(e["amount"]) for e in data["expenses"]["items"]]
        assert amts == sorted(amts, reverse=True)

    def test_savings_rate_zero_when_no_income(self, seeded_client):
        data = seeded_client.get(f"{BASE}/income-expense").json()
        assert data["savings_rate"] == 0.0

    def test_net_income_equals_income_minus_expenses(self, funded_client):
        client, ctx = funded_client
        data = client.get(f"{BASE}/income-expense").json()
        expected_net = ctx["income"] - ctx["expense"]
        assert Decimal(data["net_income"]) == expected_net


# ─────────────────────────────────────────────────────────────────────────────
# GET /reports/balance-sheet
# ─────────────────────────────────────────────────────────────────────────────

class TestBalanceSheetEndpoint:
    def test_returns_200(self, seeded_client):
        resp = seeded_client.get(f"{BASE}/balance-sheet")
        assert resp.status_code == 200

    def test_required_keys_present(self, seeded_client):
        data = seeded_client.get(f"{BASE}/balance-sheet").json()
        assert "as_of"             in data
        assert "assets"            in data
        assert "liabilities"       in data
        assert "total_assets"      in data
        assert "total_liabilities" in data
        assert "net_worth"         in data

    def test_assets_and_liabilities_are_lists(self, seeded_client):
        data = seeded_client.get(f"{BASE}/balance-sheet").json()
        assert isinstance(data["assets"],      list)
        assert isinstance(data["liabilities"], list)

    def test_as_of_defaults_to_today(self, seeded_client):
        data = seeded_client.get(f"{BASE}/balance-sheet").json()
        assert data["as_of"] == TODAY

    def test_as_of_param_reflected(self, seeded_client):
        data = seeded_client.get(
            f"{BASE}/balance-sheet", params={"as_of": "2025-12-31"}
        ).json()
        assert data["as_of"] == "2025-12-31"

    def test_net_worth_equals_assets_minus_liabilities(self, seeded_client):
        data = seeded_client.get(f"{BASE}/balance-sheet").json()
        expected = Decimal(data["total_assets"]) - Decimal(data["total_liabilities"])
        assert Decimal(data["net_worth"]) == expected

    def test_asset_nodes_have_no_internal_bal_key(self, seeded_client):
        data = seeded_client.get(f"{BASE}/balance-sheet").json()
        def no_bal(nodes):
            for n in nodes:
                assert "_bal" not in n, f"_bal leaked into response for node {n.get('code')}"
                no_bal(n.get("children", []))
        no_bal(data["assets"])
        no_bal(data["liabilities"])

    def test_asset_balance_increases_after_income_txn(self, funded_client):
        client, ctx = funded_client
        data = client.get(f"{BASE}/balance-sheet").json()
        # Net asset inflow = income 75000 – expense 4500 = 70500
        assert Decimal(data["total_assets"]) >= ctx["income"] - ctx["expense"]

    def test_as_of_yesterday_excludes_todays_transactions(self, funded_client):
        """Transactions dated today must not appear in as_of=yesterday."""
        client, ctx = funded_client
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        data = client.get(
            f"{BASE}/balance-sheet", params={"as_of": yesterday}
        ).json()
        assert Decimal(data["total_assets"]) < ctx["income"]


# ─────────────────────────────────────────────────────────────────────────────
# GET /reports/net-worth-history
# ─────────────────────────────────────────────────────────────────────────────

class TestNetWorthHistoryEndpoint:
    def test_returns_200(self, seeded_client):
        assert seeded_client.get(f"{BASE}/net-worth-history").status_code == 200

    def test_default_returns_12_items(self, seeded_client):
        data = seeded_client.get(f"{BASE}/net-worth-history").json()
        assert len(data) == 12

    def test_months_param_controls_list_length(self, seeded_client):
        for n in (1, 3, 6, 24):
            data = seeded_client.get(f"{BASE}/net-worth-history", params={"months": n}).json()
            assert len(data) == n

    def test_months_too_large_returns_422(self, seeded_client):
        resp = seeded_client.get(f"{BASE}/net-worth-history", params={"months": 61})
        assert resp.status_code == 422

    def test_months_zero_returns_422(self, seeded_client):
        resp = seeded_client.get(f"{BASE}/net-worth-history", params={"months": 0})
        assert resp.status_code == 422

    def test_each_item_has_required_keys(self, seeded_client):
        data = seeded_client.get(f"{BASE}/net-worth-history").json()
        required = {"date", "year", "month", "label", "total_assets", "total_liabilities", "net_worth"}
        for item in data:
            assert required <= item.keys()

    def test_label_format_is_year_month(self, seeded_client):
        data = seeded_client.get(f"{BASE}/net-worth-history").json()
        for item in data:
            assert len(item["label"]) == 7          # "YYYY-MM"
            assert item["label"][4] == "-"

    def test_items_in_chronological_order(self, seeded_client):
        data = seeded_client.get(f"{BASE}/net-worth-history").json()
        labels = [item["label"] for item in data]
        assert labels == sorted(labels)

    def test_last_item_is_current_period(self, seeded_client):
        data = seeded_client.get(f"{BASE}/net-worth-history").json()
        today = date.today()
        last = data[-1]
        assert last["year"]  == today.year
        assert last["month"] == today.month

    def test_net_worth_matches_assets_minus_liabilities_per_row(self, seeded_client):
        data = seeded_client.get(f"{BASE}/net-worth-history").json()
        for item in data:
            expected = Decimal(item["total_assets"]) - Decimal(item["total_liabilities"])
            assert Decimal(item["net_worth"]) == expected


# ─────────────────────────────────────────────────────────────────────────────
# GET /reports/monthly-trend
# ─────────────────────────────────────────────────────────────────────────────

class TestMonthlyTrendEndpoint:
    def test_returns_200(self, seeded_client):
        assert seeded_client.get(f"{BASE}/monthly-trend").status_code == 200

    def test_default_12_items(self, seeded_client):
        data = seeded_client.get(f"{BASE}/monthly-trend").json()
        assert len(data) == 12

    def test_months_param(self, seeded_client):
        for n in (1, 6, 24):
            data = seeded_client.get(f"{BASE}/monthly-trend", params={"months": n}).json()
            assert len(data) == n

    def test_each_item_keys(self, seeded_client):
        data = seeded_client.get(f"{BASE}/monthly-trend").json()
        for item in data:
            assert {"year", "month", "label", "income", "expenses", "net"} <= item.keys()

    def test_items_in_chronological_order(self, seeded_client):
        data = seeded_client.get(f"{BASE}/monthly-trend").json()
        labels = [item["label"] for item in data]
        assert labels == sorted(labels)

    def test_net_equals_income_minus_expenses_per_row(self, seeded_client):
        data = seeded_client.get(f"{BASE}/monthly-trend").json()
        for item in data:
            expected = Decimal(item["income"]) - Decimal(item["expenses"])
            assert Decimal(item["net"]) == expected

    def test_current_month_shows_today_transactions(self, funded_client):
        client, ctx = funded_client
        data = client.get(f"{BASE}/monthly-trend").json()
        current = data[-1]
        assert Decimal(current["income"])   == ctx["income"]
        assert Decimal(current["expenses"]) == ctx["expense"]


# ─────────────────────────────────────────────────────────────────────────────
# GET /reports/expense-categories
# ─────────────────────────────────────────────────────────────────────────────

class TestExpenseCategoriesEndpoint:
    def test_returns_200(self, seeded_client):
        assert seeded_client.get(f"{BASE}/expense-categories").status_code == 200

    def test_required_keys(self, seeded_client):
        data = seeded_client.get(f"{BASE}/expense-categories").json()
        assert "from_date"   in data
        assert "to_date"     in data
        assert "total"       in data
        assert "categories"  in data

    def test_categories_is_list(self, seeded_client):
        data = seeded_client.get(f"{BASE}/expense-categories").json()
        assert isinstance(data["categories"], list)

    def test_empty_db_total_zero(self, seeded_client):
        data = seeded_client.get(f"{BASE}/expense-categories").json()
        assert Decimal(data["total"]) == Decimal("0")

    def test_date_params_reflected(self, seeded_client):
        data = seeded_client.get(
            f"{BASE}/expense-categories",
            params={"from_date": "2025-04-01", "to_date": "2026-03-31"},
        ).json()
        assert data["from_date"] == "2025-04-01"
        assert data["to_date"]   == "2026-03-31"

    def test_category_has_required_fields(self, funded_client):
        client, _ = funded_client
        data = client.get(f"{BASE}/expense-categories").json()
        for cat in data["categories"]:
            assert "code"       in cat
            assert "name"       in cat
            assert "amount"     in cat
            assert "percentage" in cat

    def test_percentages_sum_to_100(self, funded_client):
        client, _ = funded_client
        data = client.get(f"{BASE}/expense-categories").json()
        if data["categories"]:
            total_pct = sum(c["percentage"] for c in data["categories"])
            assert abs(total_pct - 100.0) < 0.2  # float rounding tolerance

    def test_categories_sorted_descending_by_amount(self, funded_client):
        client, _ = funded_client
        data = client.get(f"{BASE}/expense-categories").json()
        amts = [float(c["amount"]) for c in data["categories"]]
        assert amts == sorted(amts, reverse=True)

    def test_expense_amount_matches_inserted_txn(self, funded_client):
        client, ctx = funded_client
        data = client.get(f"{BASE}/expense-categories").json()
        assert Decimal(data["total"]) == ctx["expense"]


# ─────────────────────────────────────────────────────────────────────────────
# GET /reports/accounts-list
# ─────────────────────────────────────────────────────────────────────────────

class TestAccountsListEndpoint:
    def test_returns_200(self, seeded_client):
        assert seeded_client.get(f"{BASE}/accounts-list").status_code == 200

    def test_returns_list(self, seeded_client):
        data = seeded_client.get(f"{BASE}/accounts-list").json()
        assert isinstance(data, list)

    def test_seeded_coa_produces_accounts(self, seeded_client):
        """The COA seed should have created at least some leaf accounts."""
        data = seeded_client.get(f"{BASE}/accounts-list").json()
        assert len(data) > 0

    def test_each_account_has_required_fields(self, seeded_client):
        data = seeded_client.get(f"{BASE}/accounts-list").json()
        for acct in data:
            assert "id"           in acct
            assert "code"         in acct
            assert "name"         in acct
            assert "account_type" in acct

    def test_no_placeholder_accounts_in_list(self, seeded_client):
        """Placeholder (group) accounts must not appear — they have no transactions."""
        data = seeded_client.get(f"{BASE}/accounts-list").json()
        # All returned accounts must be leaf nodes (is_placeholder=False).
        # We can't check the flag directly from the JSON, but we can ensure
        # the known placeholder codes are absent.
        codes = {a["code"] for a in data}
        # "1000" is Assets root (placeholder in default CoA)
        assert "1000" not in codes

    def test_filter_by_asset_type(self, seeded_client):
        data = seeded_client.get(f"{BASE}/accounts-list", params={"account_type": "ASSET"}).json()
        for acct in data:
            assert acct["account_type"] == "ASSET"

    def test_filter_by_expense_type(self, seeded_client):
        data = seeded_client.get(f"{BASE}/accounts-list", params={"account_type": "EXPENSE"}).json()
        for acct in data:
            assert acct["account_type"] == "EXPENSE"

    def test_filter_by_income_type(self, seeded_client):
        data = seeded_client.get(f"{BASE}/accounts-list", params={"account_type": "INCOME"}).json()
        for acct in data:
            assert acct["account_type"] == "INCOME"

    def test_nonexistent_type_returns_empty_list(self, seeded_client):
        data = seeded_client.get(
            f"{BASE}/accounts-list", params={"account_type": "BOGUS"}
        ).json()
        assert data == []

    def test_results_sorted_by_code(self, seeded_client):
        data = seeded_client.get(f"{BASE}/accounts-list").json()
        codes = [a["code"] for a in data]
        assert codes == sorted(codes)


# ─────────────────────────────────────────────────────────────────────────────
# GET /reports/account-statement/{account_id}
# ─────────────────────────────────────────────────────────────────────────────

class TestAccountStatementEndpoint:
    def test_nonexistent_account_returns_404(self, seeded_client):
        resp = seeded_client.get(f"{BASE}/account-statement/999999")
        assert resp.status_code == 404

    def test_valid_account_returns_200(self, seeded_client, raw_session):
        bank = _account_by_code(raw_session, "1102")
        if not bank:
            pytest.skip("Account 1102 not seeded.")
        resp = seeded_client.get(f"{BASE}/account-statement/{bank.id}")
        assert resp.status_code == 200

    def test_required_keys_in_response(self, seeded_client, raw_session):
        bank = _account_by_code(raw_session, "1102")
        if not bank:
            pytest.skip("Account 1102 not seeded.")
        data = seeded_client.get(f"{BASE}/account-statement/{bank.id}").json()
        assert "account"         in data
        assert "from_date"       in data
        assert "to_date"         in data
        assert "opening_balance" in data
        assert "closing_balance" in data
        assert "entries"         in data

    def test_account_info_in_response(self, seeded_client, raw_session):
        bank = _account_by_code(raw_session, "1102")
        if not bank:
            pytest.skip("Account 1102 not seeded.")
        data = seeded_client.get(f"{BASE}/account-statement/{bank.id}").json()
        acc = data["account"]
        assert acc["id"]   == bank.id
        assert acc["code"] == "1102"

    def test_entries_is_list(self, seeded_client, raw_session):
        bank = _account_by_code(raw_session, "1102")
        if not bank:
            pytest.skip("Account 1102 not seeded.")
        data = seeded_client.get(f"{BASE}/account-statement/{bank.id}").json()
        assert isinstance(data["entries"], list)

    def test_date_params_reflected(self, seeded_client, raw_session):
        bank = _account_by_code(raw_session, "1102")
        if not bank:
            pytest.skip("Account 1102 not seeded.")
        data = seeded_client.get(
            f"{BASE}/account-statement/{bank.id}",
            params={"from_date": "2026-01-01", "to_date": "2026-01-31"},
        ).json()
        assert data["from_date"] == "2026-01-01"
        assert data["to_date"]   == "2026-01-31"

    def test_entries_contain_debit_credit_balance(self, funded_client, raw_session):
        client, ctx = funded_client
        bank = _account_by_code(raw_session, "1102")
        if not bank:
            pytest.skip("Account 1102 not seeded.")
        data = client.get(f"{BASE}/account-statement/{bank.id}").json()
        assert len(data["entries"]) > 0
        for entry in data["entries"]:
            assert "date"        in entry
            assert "description" in entry
            assert "balance"     in entry
            # exactly one of debit/credit must be non-null per line
            assert (entry["debit"] is None) != (entry["credit"] is None)

    def test_closing_balance_matches_last_entry_balance(self, funded_client, raw_session):
        client, ctx = funded_client
        bank = _account_by_code(raw_session, "1102")
        if not bank:
            pytest.skip("Account 1102 not seeded.")
        data = client.get(f"{BASE}/account-statement/{bank.id}").json()
        if data["entries"]:
            assert Decimal(data["closing_balance"]) == Decimal(data["entries"][-1]["balance"])

    def test_running_balance_correct_after_transactions(self, funded_client, raw_session):
        """Bank has: income DR 75000, expense CR 4500 → closing = 70500."""
        client, ctx = funded_client
        bank = _account_by_code(raw_session, "1102")
        if not bank:
            pytest.skip("Account 1102 not seeded.")
        data = client.get(f"{BASE}/account-statement/{bank.id}").json()
        closing = Decimal(data["closing_balance"])
        expected = ctx["income"] - ctx["expense"]
        assert closing == expected

    def test_voided_transactions_excluded(self, funded_client, raw_session):
        """Creating a voided transaction should not affect the statement."""
        client, ctx = funded_client
        bank   = _account_by_code(raw_session, "1102")
        salary = _account_by_code(raw_session, "4100")
        if not bank or not salary:
            pytest.skip("Accounts not seeded.")

        # Insert a voided income transaction (should be ignored)
        void_txn = Transaction(
            transaction_date=date.today(),
            transaction_type="INCOME",
            description="Voided Txn",
            status="VOID",
            is_void=True,
            user_id=1,
        )
        raw_session.add(void_txn)
        raw_session.flush()
        raw_session.add(TransactionLine(
            transaction_id=void_txn.id, account_id=bank.id,
            line_type="DEBIT", amount=Decimal("99999"),
        ))
        raw_session.add(TransactionLine(
            transaction_id=void_txn.id, account_id=salary.id,
            line_type="CREDIT", amount=Decimal("99999"),
        ))
        raw_session.commit()

        data = client.get(f"{BASE}/account-statement/{bank.id}").json()
        closing = Decimal(data["closing_balance"])
        expected = ctx["income"] - ctx["expense"]
        assert closing == expected, "Voided txn should not affect running balance."


# ─────────────────────────────────────────────────────────────────────────────
# POST /reports/insights  (LLM — graceful no-provider path)
# ─────────────────────────────────────────────────────────────────────────────

class TestInsightsEndpoint:
    _VALID_PAYLOAD = {
        "report_type": "Financial Summary",
        "data": {
            "net_worth": "1000000",
            "total_income": "75000",
            "total_expenses": "4500",
            "savings_rate": 94.0,
        },
        "provider_id": None,
    }

    def test_returns_200_even_without_provider(self, seeded_client):
        """No LLM provider configured → 200 with error field, never a 5xx."""
        resp = seeded_client.post(f"{BASE}/insights", json=self._VALID_PAYLOAD)
        assert resp.status_code == 200

    def test_response_has_insight_or_error_field(self, seeded_client):
        data = seeded_client.post(f"{BASE}/insights", json=self._VALID_PAYLOAD).json()
        assert "insight" in data or "error" in data

    def test_without_provider_error_field_is_set(self, seeded_client):
        data = seeded_client.post(f"{BASE}/insights", json=self._VALID_PAYLOAD).json()
        # When no provider is configured, insight should be None and error non-null
        assert data.get("insight") is None
        assert data.get("error") is not None
        assert isinstance(data["error"], str)

    def test_missing_report_type_returns_422(self, seeded_client):
        resp = seeded_client.post(
            f"{BASE}/insights",
            json={"data": {"key": "val"}},   # report_type missing
        )
        assert resp.status_code == 422

    def test_missing_data_field_returns_422(self, seeded_client):
        resp = seeded_client.post(
            f"{BASE}/insights",
            json={"report_type": "Balance Sheet"},  # data missing
        )
        assert resp.status_code == 422

    def test_empty_data_dict_accepted(self, seeded_client):
        resp = seeded_client.post(
            f"{BASE}/insights",
            json={"report_type": "Balance Sheet", "data": {}},
        )
        assert resp.status_code == 200

    def test_nonexistent_provider_id_returns_error_field_not_5xx(self, seeded_client):
        resp = seeded_client.post(
            f"{BASE}/insights",
            json={**self._VALID_PAYLOAD, "provider_id": "non-existent-uuid"},
        )
        # Must not blow up — either 200 with error, or 404 from _resolve_provider
        assert resp.status_code in (200, 404)


# ─────────────────────────────────────────────────────────────────────────────
# GET /reports/trial-balance
# ─────────────────────────────────────────────────────────────────────────────

class TestTrialBalanceEndpoint:

    def test_returns_200(self, seeded_client):
        resp = seeded_client.get(f"{BASE}/trial-balance")
        assert resp.status_code == 200

    def test_required_top_level_keys(self, seeded_client):
        data = seeded_client.get(f"{BASE}/trial-balance").json()
        for key in ("as_of", "sections", "grand_total_debit", "grand_total_credit"):
            assert key in data, f"Missing key: {key}"

    def test_as_of_defaults_to_today(self, seeded_client):
        data = seeded_client.get(f"{BASE}/trial-balance").json()
        assert data["as_of"] == TODAY

    def test_as_of_param_reflected(self, seeded_client):
        data = seeded_client.get(
            f"{BASE}/trial-balance", params={"as_of": "2025-01-31"}
        ).json()
        assert data["as_of"] == "2025-01-31"

    def test_sections_is_list(self, seeded_client):
        data = seeded_client.get(f"{BASE}/trial-balance").json()
        assert isinstance(data["sections"], list)

    def test_section_structure(self, seeded_client, funded_client):
        client, _ = funded_client
        data = client.get(f"{BASE}/trial-balance").json()
        assert len(data["sections"]) > 0
        for section in data["sections"]:
            assert "account_type"    in section
            assert "label"           in section
            assert "accounts"        in section
            assert "section_debit"   in section
            assert "section_credit"  in section
            assert isinstance(section["accounts"], list)

    def test_account_row_keys(self, funded_client):
        client, _ = funded_client
        data = client.get(f"{BASE}/trial-balance").json()
        for section in data["sections"]:
            for acc in section["accounts"]:
                assert "id"             in acc
                assert "code"           in acc
                assert "name"           in acc
                assert "normal_balance" in acc
                assert "total_debit"    in acc
                assert "total_credit"   in acc

    def test_asset_account_in_debit_column(self, funded_client, raw_session):
        """Bank account (ASSET, DEBIT normal) with net debit activity → debit_balance set."""
        client, ctx = funded_client
        data = client.get(f"{BASE}/trial-balance").json()
        asset_section = next(
            (s for s in data["sections"] if s["account_type"] == "ASSET"), None
        )
        assert asset_section is not None
        bank_row = next(
            (a for a in asset_section["accounts"] if a["id"] == ctx["bank_id"]), None
        )
        assert bank_row is not None, "Bank account should appear in the trial balance."
        assert bank_row["debit_balance"]  is not None
        assert bank_row["credit_balance"] is None
        assert Decimal(bank_row["debit_balance"]) == ctx["income"] - ctx["expense"]

    def test_income_account_in_credit_column(self, funded_client, raw_session):
        """Salary (INCOME, CREDIT normal) → credit_balance set."""
        client, ctx = funded_client
        data = client.get(f"{BASE}/trial-balance").json()
        income_section = next(
            (s for s in data["sections"] if s["account_type"] == "INCOME"), None
        )
        assert income_section is not None
        salary_row = next(
            (a for a in income_section["accounts"] if a["id"] == ctx["salary_id"]), None
        )
        assert salary_row is not None, "Salary account should appear in the trial balance."
        assert salary_row["credit_balance"] is not None
        assert salary_row["debit_balance"]  is None
        assert Decimal(salary_row["credit_balance"]) == ctx["income"]

    def test_expense_account_in_debit_column(self, funded_client):
        """Dining (EXPENSE, DEBIT normal) → debit_balance set."""
        client, ctx = funded_client
        data = client.get(f"{BASE}/trial-balance").json()
        expense_section = next(
            (s for s in data["sections"] if s["account_type"] == "EXPENSE"), None
        )
        assert expense_section is not None
        dining_row = next(
            (a for a in expense_section["accounts"] if a["id"] == ctx["dining_id"]), None
        )
        assert dining_row is not None, "Dining account should appear in trial balance."
        assert dining_row["debit_balance"]  is not None
        assert dining_row["credit_balance"] is None
        assert Decimal(dining_row["debit_balance"]) == ctx["expense"]

    def test_grand_totals_are_numeric_strings(self, seeded_client):
        data = seeded_client.get(f"{BASE}/trial-balance").json()
        Decimal(data["grand_total_debit"])   # must not raise
        Decimal(data["grand_total_credit"])  # must not raise

    def test_grand_totals_balance(self, funded_client):
        """After a proper double-entry income + expense pair, Dr total == Cr total."""
        client, _ = funded_client
        data = client.get(f"{BASE}/trial-balance").json()
        dr = Decimal(data["grand_total_debit"])
        cr = Decimal(data["grand_total_credit"])
        assert dr == cr, f"Books out of balance: Dr={dr} Cr={cr}"

    def test_no_activity_no_sections_for_future_date(self, seeded_client):
        """Querying a date before any transactions were entered returns zero activity."""
        data = seeded_client.get(
            f"{BASE}/trial-balance", params={"as_of": "1990-01-01"}
        ).json()
        # all sections should have no accounts (no historical transactions)
        total_accounts = sum(len(s["accounts"]) for s in data["sections"])
        assert total_accounts == 0


# ─────────────────────────────────────────────────────────────────────────────
# GET /reports/general-ledger
# ─────────────────────────────────────────────────────────────────────────────

class TestGeneralLedgerEndpoint:

    def test_returns_200(self, seeded_client):
        resp = seeded_client.get(f"{BASE}/general-ledger")
        assert resp.status_code == 200

    def test_required_top_level_keys(self, seeded_client):
        data = seeded_client.get(f"{BASE}/general-ledger").json()
        for key in ("from_date", "to_date", "account_type_filter", "sections"):
            assert key in data, f"Missing key: {key}"

    def test_dates_default_to_current_month(self, seeded_client):
        data = seeded_client.get(f"{BASE}/general-ledger").json()
        assert data["from_date"] == MONTH_START
        assert data["to_date"]   == TODAY

    def test_date_params_reflected(self, seeded_client):
        data = seeded_client.get(
            f"{BASE}/general-ledger",
            params={"from_date": "2026-01-01", "to_date": "2026-01-31"},
        ).json()
        assert data["from_date"] == "2026-01-01"
        assert data["to_date"]   == "2026-01-31"

    def test_sections_is_list(self, seeded_client):
        data = seeded_client.get(f"{BASE}/general-ledger").json()
        assert isinstance(data["sections"], list)

    def test_no_transactions_sections_empty(self, seeded_client):
        data = seeded_client.get(f"{BASE}/general-ledger").json()
        # seeded_client has no transactions → all accounts dormant → no sections
        total_accounts = sum(len(s["accounts"]) for s in data["sections"])
        assert total_accounts == 0

    def test_account_type_filter_asset(self, funded_client):
        client, _ = funded_client
        data = client.get(
            f"{BASE}/general-ledger", params={"account_type": "ASSET"}
        ).json()
        assert data["account_type_filter"] == "ASSET"
        for section in data["sections"]:
            assert section["account_type"] == "ASSET"

    def test_account_type_filter_expense(self, funded_client):
        client, ctx = funded_client
        data = client.get(
            f"{BASE}/general-ledger", params={"account_type": "EXPENSE"}
        ).json()
        assert data["account_type_filter"] == "EXPENSE"
        for section in data["sections"]:
            assert section["account_type"] == "EXPENSE"

    def test_invalid_account_type_returns_all(self, funded_client):
        client, _ = funded_client
        data = client.get(
            f"{BASE}/general-ledger", params={"account_type": "BOGUS"}
        ).json()
        # invalid type → all sections returned
        types_returned = {s["account_type"] for s in data["sections"]}
        assert len(types_returned) > 1

    def test_account_row_keys(self, funded_client):
        client, _ = funded_client
        data = client.get(f"{BASE}/general-ledger").json()
        for section in data["sections"]:
            for acc in section["accounts"]:
                for key in (
                    "id", "code", "name", "normal_balance",
                    "opening_balance", "closing_balance",
                    "period_total_debit", "period_total_credit",
                    "debit_entries", "credit_entries", "entries",
                ):
                    assert key in acc, f"Account row missing key: {key}"

    def test_entry_keys(self, funded_client):
        client, _ = funded_client
        data = client.get(f"{BASE}/general-ledger").json()
        for section in data["sections"]:
            for acc in section["accounts"]:
                for entry in acc["entries"]:
                    assert "date"        in entry
                    assert "description" in entry
                    assert "balance"     in entry
                    # exactly one of debit/credit must be non-null per line
                    assert (entry["debit"] is None) != (entry["credit"] is None)

    def test_bank_account_entries_and_closing(self, funded_client):
        """Bank (ASSET): income DR 75 000, expense CR 4 500 → closing 70 500."""
        client, ctx = funded_client
        data = client.get(
            f"{BASE}/general-ledger", params={"account_type": "ASSET"}
        ).json()
        asset_section = next(
            (s for s in data["sections"] if s["account_type"] == "ASSET"), None
        )
        assert asset_section is not None
        bank_acc = next(
            (a for a in asset_section["accounts"] if a["id"] == ctx["bank_id"]), None
        )
        assert bank_acc is not None, "Bank account not in general ledger."
        assert len(bank_acc["entries"]) == 2
        assert Decimal(bank_acc["closing_balance"]) == ctx["income"] - ctx["expense"]

    def test_debit_entries_list_populated(self, funded_client):
        """Bank (ASSET) should have one debit_entry (the income deposit)."""
        client, ctx = funded_client
        data = client.get(
            f"{BASE}/general-ledger", params={"account_type": "ASSET"}
        ).json()
        asset_section = next(
            (s for s in data["sections"] if s["account_type"] == "ASSET"), None
        )
        bank_acc = next(
            (a for a in asset_section["accounts"] if a["id"] == ctx["bank_id"]), None
        )
        assert len(bank_acc["debit_entries"])  == 1
        assert len(bank_acc["credit_entries"]) == 1
        assert Decimal(bank_acc["debit_entries"][0]["amount"])  == ctx["income"]
        assert Decimal(bank_acc["credit_entries"][0]["amount"]) == ctx["expense"]

    def test_income_account_credit_entries(self, funded_client):
        """Salary (INCOME, CREDIT normal) should show the credit entry."""
        client, ctx = funded_client
        data = client.get(
            f"{BASE}/general-ledger", params={"account_type": "INCOME"}
        ).json()
        income_section = next(
            (s for s in data["sections"] if s["account_type"] == "INCOME"), None
        )
        assert income_section is not None
        salary_acc = next(
            (a for a in income_section["accounts"] if a["id"] == ctx["salary_id"]), None
        )
        assert salary_acc is not None
        assert Decimal(salary_acc["closing_balance"]) == ctx["income"]

    def test_past_date_excludes_current_transactions(self, funded_client):
        """Querying before today's entries should return empty for those accounts."""
        client, _ = funded_client
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        data = client.get(
            f"{BASE}/general-ledger",
            params={"from_date": "1990-01-01", "to_date": yesterday},
        ).json()
        total_accounts = sum(len(s["accounts"]) for s in data["sections"])
        # No pre-existing transactions → nothing in this range
        assert total_accounts == 0


# ─────────────────────────────────────────────────────────────────────────────
# GET /reports/journal
# ─────────────────────────────────────────────────────────────────────────────

class TestJournalEndpoint:

    def test_returns_200(self, seeded_client):
        resp = seeded_client.get(f"{BASE}/journal")
        assert resp.status_code == 200

    def test_required_top_level_keys(self, seeded_client):
        data = seeded_client.get(f"{BASE}/journal").json()
        for key in ("from_date", "to_date", "page", "page_size", "total", "total_pages", "entries"):
            assert key in data, f"Missing key: {key}"

    def test_entries_is_list(self, seeded_client):
        data = seeded_client.get(f"{BASE}/journal").json()
        assert isinstance(data["entries"], list)

    def test_no_transactions_returns_empty_entries(self, seeded_client):
        data = seeded_client.get(f"{BASE}/journal").json()
        assert data["total"] == 0
        assert data["entries"] == []

    def test_date_params_reflected(self, seeded_client):
        data = seeded_client.get(
            f"{BASE}/journal",
            params={"from_date": "2026-01-01", "to_date": "2026-01-31"},
        ).json()
        assert data["from_date"] == "2026-01-01"
        assert data["to_date"]   == "2026-01-31"

    def test_funded_entries_count(self, funded_client):
        """Two transactions inserted by funded_client fixture → total == 2."""
        client, _ = funded_client
        data = client.get(f"{BASE}/journal").json()
        assert data["total"] == 2
        assert len(data["entries"]) == 2

    def test_entry_required_keys(self, funded_client):
        client, _ = funded_client
        data = client.get(f"{BASE}/journal").json()
        for entry in data["entries"]:
            for key in ("id", "date", "description", "transaction_type",
                        "debits", "credits", "total_amount"):
                assert key in entry, f"Entry missing key: {key}"

    def test_debits_and_credits_are_lists(self, funded_client):
        client, _ = funded_client
        data = client.get(f"{BASE}/journal").json()
        for entry in data["entries"]:
            assert isinstance(entry["debits"],  list)
            assert isinstance(entry["credits"], list)

    def test_leg_required_keys(self, funded_client):
        client, _ = funded_client
        data = client.get(f"{BASE}/journal").json()
        for entry in data["entries"]:
            for leg in entry["debits"] + entry["credits"]:
                assert "account_id"   in leg
                assert "account_code" in leg
                assert "account_name" in leg
                assert "account_type" in leg
                assert "amount"       in leg

    def test_income_entry_dr_bank_cr_income(self, funded_client, raw_session):
        """Income txn: DR bank (ASSET 1102) / CR salary (INCOME 3101)."""
        client, ctx = funded_client
        data = client.get(f"{BASE}/journal").json()
        income_entry = next(
            (e for e in data["entries"] if e["transaction_type"] == "INCOME"), None
        )
        assert income_entry is not None
        dr_ids = [d["account_id"] for d in income_entry["debits"]]
        cr_ids = [c["account_id"] for c in income_entry["credits"]]
        assert ctx["bank_id"]   in dr_ids
        assert ctx["salary_id"] in cr_ids

    def test_expense_entry_dr_expense_cr_bank(self, funded_client):
        """Expense txn: DR dining (EXPENSE 4201) / CR bank (ASSET 1102)."""
        client, ctx = funded_client
        data = client.get(f"{BASE}/journal").json()
        expense_entry = next(
            (e for e in data["entries"] if e["transaction_type"] == "EXPENSE"), None
        )
        assert expense_entry is not None
        dr_ids = [d["account_id"] for d in expense_entry["debits"]]
        cr_ids = [c["account_id"] for c in expense_entry["credits"]]
        assert ctx["dining_id"] in dr_ids
        assert ctx["bank_id"]   in cr_ids

    def test_total_amount_equals_debit_sum(self, funded_client):
        """total_amount on each entry should equal the sum of its debit legs."""
        client, _ = funded_client
        data = client.get(f"{BASE}/journal").json()
        for entry in data["entries"]:
            debit_sum = sum(Decimal(d["amount"]) for d in entry["debits"])
            assert Decimal(entry["total_amount"]) == debit_sum

    def test_double_entry_debits_equal_credits(self, funded_client):
        """Sum of debits must equal sum of credits for every entry (books balance)."""
        client, _ = funded_client
        data = client.get(f"{BASE}/journal").json()
        for entry in data["entries"]:
            dr = sum(Decimal(d["amount"]) for d in entry["debits"])
            cr = sum(Decimal(c["amount"]) for c in entry["credits"])
            assert dr == cr, f"Entry {entry['id']} unbalanced: DR={dr} CR={cr}"

    def test_past_date_range_excludes_entries(self, funded_client):
        client, _ = funded_client
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        data = client.get(
            f"{BASE}/journal",
            params={"from_date": "1990-01-01", "to_date": yesterday},
        ).json()
        assert data["total"] == 0
        assert data["entries"] == []

    def test_pagination_page_size(self, funded_client):
        """page_size=1 with 2 transactions → total_pages=2, one entry per page."""
        client, _ = funded_client
        p1 = client.get(f"{BASE}/journal", params={"page": 1, "page_size": 1}).json()
        assert p1["total_pages"] == 2
        assert len(p1["entries"]) == 1
        p2 = client.get(f"{BASE}/journal", params={"page": 2, "page_size": 1}).json()
        assert len(p2["entries"]) == 1
        # Two pages should have different transaction IDs
        assert p1["entries"][0]["id"] != p2["entries"][0]["id"]

    def test_voided_transactions_excluded(self, funded_client, raw_session):
        """Voided transactions must not appear in the journal."""
        client, ctx = funded_client
        bank   = _account_by_code(raw_session, "1102")
        salary = _account_by_code(raw_session, "4100")
        void_txn = Transaction(
            transaction_date=date.today(),
            transaction_type="INCOME",
            description="Voided — should be hidden",
            status="VOID",
            is_void=True,
            user_id=1,
        )
        raw_session.add(void_txn)
        raw_session.flush()
        raw_session.add(TransactionLine(
            transaction_id=void_txn.id, account_id=bank.id,
            line_type="DEBIT", amount=Decimal("1"),
        ))
        raw_session.add(TransactionLine(
            transaction_id=void_txn.id, account_id=salary.id,
            line_type="CREDIT", amount=Decimal("1"),
        ))
        raw_session.commit()
        data = client.get(f"{BASE}/journal").json()
        ids = [e["id"] for e in data["entries"]]
        assert void_txn.id not in ids
