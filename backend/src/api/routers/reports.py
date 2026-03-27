"""Reports API — financial summaries, statements, and LLM insights.

Endpoints:
    GET  /api/v1/reports/summary              — dashboard KPIs (net worth, cash flow, savings rate)
    GET  /api/v1/reports/income-expense       — income & expense statement for a period
    GET  /api/v1/reports/balance-sheet        — asset / liability snapshot tree
    GET  /api/v1/reports/net-worth-history    — monthly net worth trend (last N months)
    GET  /api/v1/reports/monthly-trend        — monthly income vs expense bars
    GET  /api/v1/reports/expense-categories   — category-wise expense breakdown
    GET  /api/v1/reports/accounts-list        — flat list of leaf accounts (for statement selector)
    GET  /api/v1/reports/account-statement/{id} — per-account txn ledger with running balance
    POST /api/v1/reports/insights             — LLM narrative commentary on report data
"""
from __future__ import annotations

import json
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import CurrentUserPayload, TenantDBSession, SettingsDep
from db.models.accounts import Account
from db.models.transactions import Transaction, TransactionLine

router = APIRouter(prefix="/reports", tags=["Reports"])


# ─────────────────────────────────────────────────────────────────────────────
# Low-level SQL helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _debit_credit_sums(
    session: AsyncSession,
    account_ids: list[int],
    from_date: date | None,
    to_date: date,
) -> dict[int, tuple[Decimal, Decimal]]:
    """Return {account_id: (total_debit, total_credit)} for non-void transactions.

    When *from_date* is None the query is cumulative (balance-sheet style).
    When *from_date* is provided the query covers only that period (I&E style).
    """
    if not account_ids:
        return {}

    stmt = (
        select(
            TransactionLine.account_id,
            func.coalesce(
                func.sum(
                    case(
                        (TransactionLine.line_type == "DEBIT", TransactionLine.amount),
                        else_=0,
                    )
                ),
                0,
            ).label("d"),
            func.coalesce(
                func.sum(
                    case(
                        (TransactionLine.line_type == "CREDIT", TransactionLine.amount),
                        else_=0,
                    )
                ),
                0,
            ).label("c"),
        )
        .join(Transaction, Transaction.id == TransactionLine.transaction_id)
        .where(TransactionLine.account_id.in_(account_ids))
        .where(Transaction.transaction_date <= to_date)
        .where(Transaction.is_void == False)  # noqa: E712
        .group_by(TransactionLine.account_id)
    )
    if from_date is not None:
        stmt = stmt.where(Transaction.transaction_date >= from_date)
        # Exclude opening-balance adjustments from I&E / cash-flow queries —
        # they are balance-sheet initialisers, not real income or expense activity.
        stmt = stmt.where(Transaction.transaction_type != "OPENING_BALANCE")

    result = await session.execute(stmt)
    rows = result.all()
    return {r.account_id: (Decimal(str(r.d)), Decimal(str(r.c))) for r in rows}


def _signed_balance(d: Decimal, c: Decimal, normal_balance: str) -> Decimal:
    """Convert raw debit/credit to a signed balance where positive = has value."""
    return (d - c) if normal_balance == "DEBIT" else (c - d)


async def _load_accounts(session: AsyncSession, account_types: list[str]) -> list[Account]:
    result = await session.execute(
        select(Account)
        .where(Account.account_type.in_(account_types))
        .where(Account.is_active == True)  # noqa: E712
    )
    return list(result.scalars().all())


def _type_total(
    leafs: list[Account],
    sums: dict[int, tuple[Decimal, Decimal]],
    account_type: str,
) -> Decimal:
    return sum(
        _signed_balance(*sums.get(a.id, (Decimal(0), Decimal(0))), a.normal_balance)
        for a in leafs
        if a.account_type == account_type
    )


async def _period_items(
    session: AsyncSession,
    accounts: list[Account],
    account_types: list[str],
    from_date: date,
    to_date: date,
) -> list[dict[str, Any]]:
    """Return a list of {account_id, code, name, account_type, amount} for the period."""
    leafs = [a for a in accounts if a.account_type in account_types and not a.is_placeholder]
    if not leafs:
        return []
    sums = await _debit_credit_sums(session, [a.id for a in leafs], from_date, to_date)
    result = []
    for acc in leafs:
        d, c = sums.get(acc.id, (Decimal(0), Decimal(0)))
        amount = _signed_balance(d, c, acc.normal_balance)
        if amount != Decimal(0):
            result.append({
                "account_id": acc.id,
                "code": acc.code,
                "name": acc.name,
                "account_type": acc.account_type,
                "amount": amount,
            })
    return result


def _build_tree(
    all_accs: list[Account],
    sums: dict[int, tuple[Decimal, Decimal]],
    parent_id: int | None,
    account_type: str,
) -> list[dict[str, Any]]:
    """Recursively build a balance-sheet style tree.

    Each node gets a ``_bal`` key (Decimal) used for parent aggregation;
    callers should strip it with ``_strip_internal`` before sending to clients.
    """
    children = sorted(
        [a for a in all_accs if a.parent_id == parent_id and a.account_type == account_type and a.is_active],
        key=lambda a: a.display_order,
    )
    nodes = []
    for child in children:
        subtree = _build_tree(all_accs, sums, child.id, account_type)
        if child.is_placeholder:
            subtotal: Decimal = sum((n["_bal"] for n in subtree), Decimal(0))
            nodes.append({
                "id": child.id, "code": child.code, "name": child.name,
                "balance": str(subtotal), "_bal": subtotal,
                "is_group": True, "children": subtree,
            })
        else:
            d, c = sums.get(child.id, (Decimal(0), Decimal(0)))
            bal = _signed_balance(d, c, child.normal_balance)
            # A non-placeholder can still have children (uncommon but valid in CoA)
            if subtree:
                bal += sum((n["_bal"] for n in subtree), Decimal(0))
            nodes.append({
                "id": child.id, "code": child.code, "name": child.name,
                "balance": str(bal), "_bal": bal,
                "is_group": bool(subtree), "children": subtree,
            })
    return nodes


def _strip_internal(nodes: list[dict]) -> list[dict]:
    """Remove ``_bal`` helper keys before serialising."""
    for n in nodes:
        n.pop("_bal", None)
        _strip_internal(n.get("children", []))
    return nodes


def _month_offset(today: date, months_back: int) -> tuple[int, int]:
    year, month = today.year, today.month - months_back
    while month <= 0:
        month += 12
        year -= 1
    return year, month


def _month_end(year: int, month: int) -> date:
    return date(year, month, monthrange(year, month)[1])


# ─────────────────────────────────────────────────────────────────────────────
# GET /reports/summary
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/summary", summary="Dashboard KPIs — net worth, cash flow, top expenses")
async def reports_summary(
    auth: CurrentUserPayload,
    session: TenantDBSession,
    as_of: date | None     = Query(default=None, description="Balance-sheet date (default today)"),
    from_date: date | None = Query(default=None, description="Period start (default 1st of this month)"),
    to_date: date | None   = Query(default=None, description="Period end (default today)"),
):
    today = date.today()
    as_of     = as_of     or today
    to_date   = to_date   or today
    from_date = from_date or date(today.year, today.month, 1)

    all_accs = await _load_accounts(session, ["ASSET", "LIABILITY", "INCOME", "EXPENSE"])
    bs_leafs = [a for a in all_accs if a.account_type in ("ASSET", "LIABILITY") and not a.is_placeholder]
    bs_sums  = await _debit_credit_sums(session, [a.id for a in bs_leafs], None, as_of)

    total_assets      = _type_total(bs_leafs, bs_sums, "ASSET")
    total_liabilities = _type_total(bs_leafs, bs_sums, "LIABILITY")
    net_worth         = total_assets - total_liabilities

    income_items  = await _period_items(session, all_accs, ["INCOME"],  from_date, to_date)
    expense_items = await _period_items(session, all_accs, ["EXPENSE"], from_date, to_date)
    period_income   = sum(i["amount"] for i in income_items)
    period_expenses = sum(e["amount"] for e in expense_items)
    net_income      = period_income - period_expenses
    savings_rate    = round(float(net_income / period_income * 100), 1) if period_income > 0 else 0.0

    top_expenses = sorted(expense_items, key=lambda x: x["amount"], reverse=True)[:6]

    return {
        "as_of":            as_of.isoformat(),
        "from_date":        from_date.isoformat(),
        "to_date":          to_date.isoformat(),
        "net_worth":        str(net_worth),
        "total_assets":     str(total_assets),
        "total_liabilities": str(total_liabilities),
        "period_income":    str(period_income),
        "period_expenses":  str(period_expenses),
        "net_income":       str(net_income),
        "savings_rate":     savings_rate,
        "top_expenses": [
            {"code": e["code"], "name": e["name"], "amount": str(e["amount"])}
            for e in top_expenses
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /reports/income-expense
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/income-expense", summary="Income & Expense statement for a period")
async def income_expense(
    auth: CurrentUserPayload,
    session: TenantDBSession,
    from_date: date | None = Query(default=None),
    to_date: date | None   = Query(default=None),
):
    today     = date.today()
    to_date   = to_date   or today
    from_date = from_date or date(today.year, today.month, 1)

    all_accs      = await _load_accounts(session, ["INCOME", "EXPENSE"])
    income_items  = await _period_items(session, all_accs, ["INCOME"],  from_date, to_date)
    expense_items = await _period_items(session, all_accs, ["EXPENSE"], from_date, to_date)

    total_income   = sum(i["amount"] for i in income_items)
    total_expenses = sum(e["amount"] for e in expense_items)
    net_income     = total_income - total_expenses
    savings_rate   = round(float(net_income / total_income * 100), 1) if total_income > 0 else 0.0

    return {
        "from_date": from_date.isoformat(),
        "to_date":   to_date.isoformat(),
        "income": {
            "items": sorted(
                [{"code": i["code"], "name": i["name"], "amount": str(i["amount"])} for i in income_items],
                key=lambda x: x["code"],
            ),
            "total": str(total_income),
        },
        "expenses": {
            "items": sorted(
                [{"code": e["code"], "name": e["name"], "amount": str(e["amount"])} for e in expense_items],
                key=lambda x: -float(x["amount"]),
            ),
            "total": str(total_expenses),
        },
        "net_income":   str(net_income),
        "savings_rate": savings_rate,
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /reports/balance-sheet
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/balance-sheet", summary="Asset & Liability snapshot as a tree")
async def balance_sheet(
    auth: CurrentUserPayload,
    session: TenantDBSession,
    as_of: date | None = Query(default=None),
):
    today = date.today()
    as_of = as_of or today

    all_accs = await _load_accounts(session, ["ASSET", "LIABILITY"])
    leafs    = [a for a in all_accs if not a.is_placeholder]
    sums     = await _debit_credit_sums(session, [a.id for a in leafs], None, as_of)

    asset_tree     = _strip_internal(_build_tree(all_accs, sums, None, "ASSET"))
    liability_tree = _strip_internal(_build_tree(all_accs, sums, None, "LIABILITY"))

    total_assets      = _type_total(leafs, sums, "ASSET")
    total_liabilities = _type_total(leafs, sums, "LIABILITY")

    return {
        "as_of":             as_of.isoformat(),
        "assets":            asset_tree,
        "liabilities":       liability_tree,
        "total_assets":      str(total_assets),
        "total_liabilities": str(total_liabilities),
        "net_worth":         str(total_assets - total_liabilities),
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /reports/net-worth-history
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/net-worth-history", summary="Monthly net worth over the last N months")
async def net_worth_history(
    auth: CurrentUserPayload,
    session: TenantDBSession,
    months: int = Query(default=12, ge=1, le=60),
):
    today    = date.today()
    all_accs = await _load_accounts(session, ["ASSET", "LIABILITY"])
    leafs    = [a for a in all_accs if not a.is_placeholder]
    leaf_ids = [a.id for a in leafs]

    result = []
    for i in range(months - 1, -1, -1):
        year, month = _month_offset(today, i)
        snap_date   = today if i == 0 else _month_end(year, month)
        sums        = await _debit_credit_sums(session, leaf_ids, None, snap_date)
        assets      = _type_total(leafs, sums, "ASSET")
        liabilities = _type_total(leafs, sums, "LIABILITY")
        result.append({
            "date":              snap_date.isoformat(),
            "year":              year,
            "month":             month,
            "label":             f"{year}-{month:02d}",
            "total_assets":      str(assets),
            "total_liabilities": str(liabilities),
            "net_worth":         str(assets - liabilities),
        })
    return result


# ─────────────────────────────────────────────────────────────────────────────
# GET /reports/monthly-trend
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/monthly-trend", summary="Monthly income vs expense bars")
async def monthly_trend(
    auth: CurrentUserPayload,
    session: TenantDBSession,
    months: int = Query(default=12, ge=1, le=60),
):
    today    = date.today()
    all_accs = await _load_accounts(session, ["INCOME", "EXPENSE"])

    result = []
    for i in range(months - 1, -1, -1):
        year, month = _month_offset(today, i)
        from_date   = date(year, month, 1)
        to_date     = today if i == 0 else _month_end(year, month)

        income_items  = await _period_items(session, all_accs, ["INCOME"],  from_date, to_date)
        expense_items = await _period_items(session, all_accs, ["EXPENSE"], from_date, to_date)
        income   = sum(i["amount"] for i in income_items)
        expenses = sum(e["amount"] for e in expense_items)
        result.append({
            "year":     year,
            "month":    month,
            "label":    f"{year}-{month:02d}",
            "income":   str(income),
            "expenses": str(expenses),
            "net":      str(income - expenses),
        })
    return result


# ─────────────────────────────────────────────────────────────────────────────
# GET /reports/expense-categories
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/expense-categories", summary="Category-wise expense breakdown with percentages")
async def expense_categories(
    auth: CurrentUserPayload,
    session: TenantDBSession,
    from_date: date | None = Query(default=None),
    to_date: date | None   = Query(default=None),
):
    today     = date.today()
    to_date   = to_date   or today
    from_date = from_date or date(today.year, today.month, 1)

    expense_accs = await _load_accounts(session, ["EXPENSE"])
    items        = await _period_items(session, expense_accs, ["EXPENSE"], from_date, to_date)
    total        = sum(i["amount"] for i in items)
    sorted_items = sorted(items, key=lambda x: x["amount"], reverse=True)

    return {
        "from_date": from_date.isoformat(),
        "to_date":   to_date.isoformat(),
        "total":     str(total),
        "categories": [
            {
                "code":       e["code"],
                "name":       e["name"],
                "amount":     str(e["amount"]),
                "percentage": round(float(e["amount"] / total * 100), 1) if total > 0 else 0.0,
            }
            for e in sorted_items
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /reports/accounts-list
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/accounts-list", summary="Flat list of active leaf accounts")
async def accounts_list(
    auth: CurrentUserPayload,
    session: TenantDBSession,
    account_type: str | None = Query(default=None, description="Filter by ASSET|LIABILITY|INCOME|EXPENSE"),
):
    stmt = (
        select(Account)
        .where(Account.is_active == True)  # noqa: E712
        .where(Account.is_placeholder == False)  # noqa: E712
        .order_by(Account.code)
    )
    if account_type:
        stmt = stmt.where(Account.account_type == account_type.upper())
    accounts = (await session.execute(stmt)).scalars().all()
    return [
        {"id": a.id, "code": a.code, "name": a.name, "account_type": a.account_type}
        for a in accounts
    ]


# ─────────────────────────────────────────────────────────────────────────────
# GET /reports/account-statement/{account_id}
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/account-statement/{account_id}", summary="Per-account transaction ledger with running balance")
async def account_statement(
    account_id: int,
    auth: CurrentUserPayload,
    session: TenantDBSession,
    from_date: date | None = Query(default=None),
    to_date: date | None   = Query(default=None),
):
    today     = date.today()
    to_date   = to_date   or today
    from_date = from_date or date(today.year, today.month, 1)

    account = await session.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "Account not found."})

    # Opening balance = all activity strictly before from_date
    open_sums = await _debit_credit_sums(session, [account_id], None, from_date - timedelta(days=1))
    d0, c0    = open_sums.get(account_id, (Decimal(0), Decimal(0)))
    opening   = _signed_balance(d0, c0, account.normal_balance)

    # Transactions within the period
    stmt = (
        select(Transaction, TransactionLine)
        .join(TransactionLine, TransactionLine.transaction_id == Transaction.id)
        .where(TransactionLine.account_id == account_id)
        .where(Transaction.transaction_date >= from_date)
        .where(Transaction.transaction_date <= to_date)
        .where(Transaction.is_void == False)  # noqa: E712
        .order_by(Transaction.transaction_date, Transaction.id)
    )
    result = await session.execute(stmt)
    rows = result.all()

    entries: list[dict] = []
    running = opening
    for txn, line in rows:
        if account.normal_balance == "DEBIT":
            movement = line.amount if line.line_type == "DEBIT" else -line.amount
        else:
            movement = line.amount if line.line_type == "CREDIT" else -line.amount
        running += movement
        entries.append({
            "transaction_id": txn.id,
            "date":           txn.transaction_date.isoformat(),
            "description":    txn.description,
            "debit":          str(line.amount) if line.line_type == "DEBIT"  else None,
            "credit":         str(line.amount) if line.line_type == "CREDIT" else None,
            "balance":        str(running),
        })

    return {
        "account": {
            "id":           account.id,
            "code":         account.code,
            "name":         account.name,
            "account_type": account.account_type,
        },
        "from_date":       from_date.isoformat(),
        "to_date":         to_date.isoformat(),
        "opening_balance": str(opening),
        "closing_balance": str(running),
        "entries":         entries,
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /reports/trial-balance
# ─────────────────────────────────────────────────────────────────────────────

_SECTION_ORDER  = ["ASSET", "LIABILITY", "INCOME", "EXPENSE"]
_SECTION_LABELS = {"ASSET": "Assets", "LIABILITY": "Liabilities",
                   "INCOME": "Income", "EXPENSE": "Expenses"}


@router.get("/trial-balance", summary="Trial Balance — all accounts with Dr/Cr columns")
async def trial_balance(
    auth: CurrentUserPayload,
    session: TenantDBSession,
    as_of: date | None = Query(default=None, description="Snapshot date (default today)"),
):
    """Classic two-column Trial Balance.

    Every account's net balance is placed in either the Debit or Credit column
    according to its normal balance.  Grand-total debit == grand-total credit
    when the books are balanced.
    """
    today = date.today()
    as_of = as_of or today

    all_accs = await _load_accounts(session, _SECTION_ORDER)
    leafs    = [a for a in all_accs if not a.is_placeholder]
    sums     = await _debit_credit_sums(session, [a.id for a in leafs], None, as_of)

    grand_dr = Decimal("0")
    grand_cr = Decimal("0")
    sections: list[dict[str, Any]] = []

    for actype in _SECTION_ORDER:
        type_accs = [a for a in leafs if a.account_type == actype]
        rows: list[dict[str, Any]] = []

        for acc in sorted(type_accs, key=lambda a: a.code):
            d, c = sums.get(acc.id, (Decimal("0"), Decimal("0")))
            if d == Decimal("0") and c == Decimal("0"):
                continue  # omit zero-activity accounts
            net = _signed_balance(d, c, acc.normal_balance)
            # Positive net → natural column; negative net → opposite (contra) column
            if net >= Decimal("0"):
                dr_bal = str(net)          if acc.normal_balance == "DEBIT"   else None
                cr_bal = str(net)          if acc.normal_balance == "CREDIT"  else None
            else:
                abs_net = abs(net)
                dr_bal  = str(abs_net)     if acc.normal_balance == "CREDIT"  else None
                cr_bal  = str(abs_net)     if acc.normal_balance == "DEBIT"   else None

            grand_dr += Decimal(dr_bal) if dr_bal else Decimal("0")
            grand_cr += Decimal(cr_bal) if cr_bal else Decimal("0")
            rows.append({
                "id":             acc.id,
                "code":           acc.code,
                "name":           acc.name,
                "account_type":   acc.account_type,
                "normal_balance": acc.normal_balance,
                "total_debit":    str(d),
                "total_credit":   str(c),
                "debit_balance":  dr_bal,
                "credit_balance": cr_bal,
            })

        sec_dr = str(sum((Decimal(r["debit_balance"])  for r in rows if r["debit_balance"]),  Decimal("0")))
        sec_cr = str(sum((Decimal(r["credit_balance"]) for r in rows if r["credit_balance"]), Decimal("0")))
        sections.append({
            "account_type":   actype,
            "label":          _SECTION_LABELS[actype],
            "accounts":       rows,
            "section_debit":  sec_dr,
            "section_credit": sec_cr,
        })

    return {
        "as_of":              as_of.isoformat(),
        "sections":           sections,
        "grand_total_debit":  str(grand_dr),
        "grand_total_credit": str(grand_cr),
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /reports/general-ledger
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/general-ledger", summary="General Ledger — per-account T-account entries grouped by category")
async def general_ledger(
    auth: CurrentUserPayload,
    session: TenantDBSession,
    from_date: date | None   = Query(default=None),
    to_date: date | None     = Query(default=None),
    account_type: str | None = Query(default=None, description="ASSET|LIABILITY|INCOME|EXPENSE (default: all)"),
):
    """Ledger-book view: for each account in the requested category, returns
    the opening balance, individual transactions with Dr/Cr columns and a
    running balance, and the period totals.

    Both a *linear* entries list (Date | Narration | Dr | Cr | Balance) and
    split *debit_entries* / *credit_entries* lists (for T-account rendering)
    are included in the response so the UI can choose its presentation style.
    """
    today     = date.today()
    to_date   = to_date   or today
    from_date = from_date or date(today.year, today.month, 1)

    types_to_load = (
        [account_type.upper()]
        if account_type and account_type.upper() in _SECTION_ORDER
        else _SECTION_ORDER
    )

    all_accs = await _load_accounts(session, types_to_load)
    leafs    = [a for a in all_accs if not a.is_placeholder]

    sections: list[dict[str, Any]] = []

    for actype in _SECTION_ORDER:
        if actype not in types_to_load:
            continue

        type_accs = sorted(
            [a for a in leafs if a.account_type == actype], key=lambda a: a.code
        )
        account_rows: list[dict[str, Any]] = []

        for acc in type_accs:
            # Opening balance = all activity strictly before from_date
            open_sums = await _debit_credit_sums(
                session, [acc.id], None, from_date - timedelta(days=1)
            )
            d0, c0  = open_sums.get(acc.id, (Decimal("0"), Decimal("0")))
            opening = _signed_balance(d0, c0, acc.normal_balance)

            # Fetch period transactions
            _txn_r = await session.execute(
                select(Transaction, TransactionLine)
                .join(TransactionLine, TransactionLine.transaction_id == Transaction.id)
                .where(TransactionLine.account_id == acc.id)
                .where(Transaction.transaction_date >= from_date)
                .where(Transaction.transaction_date <= to_date)
                .where(Transaction.is_void == False)  # noqa: E712
                .order_by(Transaction.transaction_date, Transaction.id)
            )
            txn_rows = _txn_r.all()

            if not txn_rows and opening == Decimal("0"):
                continue  # skip dormant zero-balance accounts

            entries:         list[dict] = []
            debit_entries:   list[dict] = []   # left column of T-account
            credit_entries:  list[dict] = []   # right column of T-account
            running   = opening
            period_dr = Decimal("0")
            period_cr = Decimal("0")

            for txn, line in txn_rows:
                if acc.normal_balance == "DEBIT":
                    movement = line.amount if line.line_type == "DEBIT" else -line.amount
                else:
                    movement = line.amount if line.line_type == "CREDIT" else -line.amount
                running += movement

                entries.append({
                    "date":        txn.transaction_date.isoformat(),
                    "description": txn.description,
                    "debit":       str(line.amount) if line.line_type == "DEBIT"  else None,
                    "credit":      str(line.amount) if line.line_type == "CREDIT" else None,
                    "balance":     str(running),
                })
                if line.line_type == "DEBIT":
                    period_dr += line.amount
                    debit_entries.append({
                        "date":        txn.transaction_date.isoformat(),
                        "description": txn.description,
                        "amount":      str(line.amount),
                    })
                else:
                    period_cr += line.amount
                    credit_entries.append({
                        "date":        txn.transaction_date.isoformat(),
                        "description": txn.description,
                        "amount":      str(line.amount),
                    })

            account_rows.append({
                "id":                  acc.id,
                "code":                acc.code,
                "name":                acc.name,
                "account_type":        acc.account_type,
                "normal_balance":      acc.normal_balance,
                "opening_balance":     str(opening),
                "closing_balance":     str(running),
                "period_total_debit":  str(period_dr),
                "period_total_credit": str(period_cr),
                "debit_entries":       debit_entries,
                "credit_entries":      credit_entries,
                "entries":             entries,
            })

        if account_rows:
            sections.append({
                "account_type": actype,
                "label":        _SECTION_LABELS[actype],
                "accounts":     account_rows,
            })

    return {
        "from_date":           from_date.isoformat(),
        "to_date":             to_date.isoformat(),
        "account_type_filter": account_type.upper() if account_type else "ALL",
        "sections":            sections,
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /reports/dashboard/net-asset-value
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/dashboard/net-asset-value", summary="Net Asset Value dashboard — history, distribution, insights")
async def dashboard_nav(
    auth: CurrentUserPayload,
    session: TenantDBSession,
    months: int = Query(default=12, ge=3, le=60),
):
    today    = date.today()
    all_accs = await _load_accounts(session, ["ASSET", "LIABILITY"])
    leafs    = [a for a in all_accs if not a.is_placeholder]
    leaf_ids = [a.id for a in leafs]

    # Monthly history
    history = []
    for i in range(months - 1, -1, -1):
        year, month = _month_offset(today, i)
        snap  = today if i == 0 else _month_end(year, month)
        sums  = await _debit_credit_sums(session, leaf_ids, None, snap)
        assets = _type_total(leafs, sums, "ASSET")
        liabs  = _type_total(leafs, sums, "LIABILITY")
        history.append({
            "label":             f"{year}-{month:02d}",
            "total_assets":      float(assets),
            "total_liabilities": float(liabs),
            "net_worth":         float(assets - liabs),
        })

    # Current snapshot
    now_sums   = await _debit_credit_sums(session, leaf_ids, None, today)
    now_assets = _type_total(leafs, now_sums, "ASSET")
    now_liabs  = _type_total(leafs, now_sums, "LIABILITY")
    now_nw     = now_assets - now_liabs

    # Asset distribution
    asset_dist = []
    for acc in leafs:
        if acc.account_type != "ASSET":
            continue
        d, c = now_sums.get(acc.id, (Decimal(0), Decimal(0)))
        bal  = _signed_balance(d, c, acc.normal_balance)
        if bal > 0:
            asset_dist.append({
                "name":    acc.name,
                "code":    acc.code,
                "value":   float(bal),
                "percent": round(float(bal / now_assets * 100), 1) if now_assets > 0 else 0.0,
            })
    asset_dist.sort(key=lambda x: -x["value"])

    # Liability breakdown
    liab_dist = []
    for acc in leafs:
        if acc.account_type != "LIABILITY":
            continue
        d, c = now_sums.get(acc.id, (Decimal(0), Decimal(0)))
        bal  = _signed_balance(d, c, acc.normal_balance)
        if bal > 0:
            liab_dist.append({
                "name":    acc.name,
                "code":    acc.code,
                "value":   float(bal),
                "percent": round(float(bal / now_liabs * 100), 1) if now_liabs > 0 else 0.0,
            })
    liab_dist.sort(key=lambda x: -x["value"])

    # Growth velocity (mom)
    prev_nw       = Decimal(str(history[-2]["net_worth"])) if len(history) >= 2 else Decimal(0)
    nw_change     = now_nw - prev_nw
    nw_change_pct = round(float(nw_change / prev_nw * 100), 1) if prev_nw > 0 else 0.0

    # Liquid vs illiquid (11xx prefix = cash/bank)
    liquid_assets = float(sum(
        _signed_balance(*now_sums.get(a.id, (Decimal(0), Decimal(0))), a.normal_balance)
        for a in leafs
        if a.account_type == "ASSET" and a.code.startswith("11")
    ))
    illiquid_assets = float(now_assets) - liquid_assets

    return {
        "as_of":          today.isoformat(),
        "net_worth":      float(now_nw),
        "total_assets":   float(now_assets),
        "total_liabilities": float(now_liabs),
        "nw_change":      float(nw_change),
        "nw_change_pct":  nw_change_pct,
        "history":        history,
        "asset_distribution":   asset_dist,
        "liability_distribution": liab_dist,
        "liquidity": {
            "liquid":   round(liquid_assets, 2),
            "illiquid": round(illiquid_assets, 2),
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /reports/dashboard/cash-flow
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/dashboard/cash-flow", summary="Cash flow dashboard — patterns, insights, suggestions")
async def dashboard_cash_flow(
    auth: CurrentUserPayload,
    session: TenantDBSession,
    months: int = Query(default=12, ge=3, le=60),
):
    today    = date.today()
    all_accs = await _load_accounts(session, ["INCOME", "EXPENSE"])

    monthly = []
    for i in range(months - 1, -1, -1):
        year, month = _month_offset(today, i)
        fd = date(year, month, 1)
        td = today if i == 0 else _month_end(year, month)
        inc = float(sum(x["amount"] for x in await _period_items(session, all_accs, ["INCOME"],  fd, td)))
        exp = float(sum(x["amount"] for x in await _period_items(session, all_accs, ["EXPENSE"], fd, td)))
        monthly.append({
            "label":        f"{year}-{month:02d}",
            "income":       inc,
            "expenses":     exp,
            "net":          inc - exp,
            "savings_rate": round((inc - exp) / inc * 100, 1) if inc > 0 else 0.0,
        })

    cur_fd = date(today.year, today.month, 1)
    cur_inc = await _period_items(session, all_accs, ["INCOME"],  cur_fd, today)
    cur_exp = await _period_items(session, all_accs, ["EXPENSE"], cur_fd, today)

    nz = [m for m in monthly if m["income"] > 0]
    return {
        "as_of":   today.isoformat(),
        "months":  months,
        "monthly": monthly,
        "avg_monthly_income":   round(sum(m["income"]   for m in nz) / len(nz), 2) if nz else 0,
        "avg_monthly_expenses": round(sum(m["expenses"] for m in nz) / len(nz), 2) if nz else 0,
        "current_month": {
            "income":   round(float(sum(x["amount"] for x in cur_inc)), 2),
            "expenses": round(float(sum(x["amount"] for x in cur_exp)), 2),
            "income_sources":  sorted(
                [{"name": x["name"], "amount": float(x["amount"])} for x in cur_inc],
                key=lambda x: -x["amount"],
            )[:8],
            "expense_categories": sorted(
                [{"name": x["name"], "amount": float(x["amount"])} for x in cur_exp],
                key=lambda x: -x["amount"],
            )[:10],
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /reports/dashboard/diversification
# ─────────────────────────────────────────────────────────────────────────────

_ASSET_CLASSES = {
    "11": "Cash & Bank", "12": "Fixed Deposits", "13": "Equities",
    "14": "Mutual Funds", "15": "Provident Funds", "16": "Real Estate",
    "17": "Gold & Commodities", "18": "Foreign Assets",
}

@router.get("/dashboard/diversification", summary="Asset diversification dashboard")
async def dashboard_diversification(
    auth: CurrentUserPayload,
    session: TenantDBSession,
):
    today    = date.today()
    all_accs = await _load_accounts(session, ["ASSET"])
    leafs    = [a for a in all_accs if not a.is_placeholder]
    sums     = await _debit_credit_sums(session, [a.id for a in leafs], None, today)

    class_totals: dict[str, float] = {}
    for acc in leafs:
        d, c = sums.get(acc.id, (Decimal(0), Decimal(0)))
        bal  = float(_signed_balance(d, c, acc.normal_balance))
        if bal <= 0:
            continue
        prefix   = acc.code[:2] if len(acc.code) >= 2 else "19"
        cls_name = _ASSET_CLASSES.get(prefix, "Other Assets")
        class_totals[cls_name] = class_totals.get(cls_name, 0) + bal

    total = sum(class_totals.values())
    distribution = sorted(
        [{"asset_class": k, "value": round(v, 2),
          "percent": round(v / total * 100, 1) if total > 0 else 0.0}
         for k, v in class_totals.items()],
        key=lambda x: -x["value"],
    )

    top = distribution[0] if distribution else None
    return {
        "as_of":        today.isoformat(),
        "total_assets": round(total, 2),
        "distribution": distribution,
        "concentration_warning": (
            f"Over 60% of your wealth is in {top['asset_class']}. "
            "Consider spreading across more asset classes."
            if top and top["percent"] > 60 else None
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /reports/dashboard/spending-analysis
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/dashboard/spending-analysis", summary="Spending analysis — category trends and month-on-month delta")
async def dashboard_spending(
    auth: CurrentUserPayload,
    session: TenantDBSession,
    months: int = Query(default=6, ge=2, le=24),
):
    today    = date.today()
    all_accs = await _load_accounts(session, ["EXPENSE"])
    labels: list[str] = []

    # Build monthly per-category amounts
    category_monthly: dict[str, list[float]] = {}
    for i in range(months - 1, -1, -1):
        year, month = _month_offset(today, i)
        fd    = date(year, month, 1)
        td    = today if i == 0 else _month_end(year, month)
        label = f"{year}-{month:02d}"
        labels.append(label)
        items = await _period_items(session, all_accs, ["EXPENSE"], fd, td)
        seen  = set()
        for item in items:
            nm = item["name"]
            seen.add(nm)
            if nm not in category_monthly:
                category_monthly[nm] = [0.0] * (len(labels) - 1)
            category_monthly[nm].append(float(item["amount"]))
        for nm in category_monthly:
            if nm not in seen:
                category_monthly[nm].append(0.0)

    cur_fd = date(today.year, today.month, 1)
    py, pm = _month_offset(today, 1)
    prev_fd, prev_td = date(py, pm, 1), _month_end(py, pm)
    cur_map  = {x["name"]: float(x["amount"]) for x in await _period_items(session, all_accs, ["EXPENSE"], cur_fd, today)}
    prev_map = {x["name"]: float(x["amount"]) for x in await _period_items(session, all_accs, ["EXPENSE"], prev_fd, prev_td)}

    delta = sorted(
        [{"category": cat,
          "current":  cur_map.get(cat, 0),
          "previous": prev_map.get(cat, 0),
          "change_pct": round(((cur_map.get(cat, 0) - prev_map.get(cat, 0)) / prev_map[cat] * 100), 1)
                        if prev_map.get(cat, 0) > 0 else 0.0}
         for cat in sorted(set(cur_map) | set(prev_map))],
        key=lambda x: -abs(x["current"]),
    )[:10]

    return {
        "months":  months,
        "labels":  labels,
        "category_trends": sorted(
            [{"category": k, "monthly_amounts": v}
             for k, v in category_monthly.items()],
            key=lambda x: -sum(x["monthly_amounts"]),
        )[:10],
        "month_delta":   delta,
        "total_current_month":  round(sum(cur_map.values()),  2),
        "total_previous_month": round(sum(prev_map.values()), 2),
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /reports/dashboard/tax-optimization
# ─────────────────────────────────────────────────────────────────────────────

_TAX_SAVING_CODES = {
    "80C":  ["1201", "1203", "1204", "5900"],  # ELSS, FD, PPF/EPF/NPS, Insurance Premium
    "80D":  ["5500", "5900"],                   # Healthcare, Insurance Premium
    "Sec 24": ["2200"],                          # Home Loan
}
_SECTION_LIMITS = {"80C": 150000, "80D": 50000, "Sec 24": 200000}

@router.get("/dashboard/tax-optimization", summary="Tax optimization — FY utilization and savings potential")
async def dashboard_tax(
    auth: CurrentUserPayload,
    session: TenantDBSession,
):
    today    = date.today()
    fy_start = date(today.year if today.month >= 4 else today.year - 1, 4, 1)
    all_accs = await _load_accounts(session, ["EXPENSE", "ASSET"])
    fy_items = await _period_items(session, all_accs, ["EXPENSE", "ASSET"], fy_start, today)
    expense_map = {x["code"]: float(x["amount"]) for x in fy_items}

    income_accs   = await _load_accounts(session, ["INCOME"])
    inc_items     = await _period_items(session, income_accs, ["INCOME"], fy_start, today)
    annual_income = float(sum(x["amount"] for x in inc_items))

    sections = []
    total_used = total_limit = 0.0
    for section, codes in _TAX_SAVING_CODES.items():
        used  = sum(expense_map.get(c, 0) for c in codes)
        limit = _SECTION_LIMITS[section]
        remaining = max(0.0, limit - used)
        total_used  += min(used, limit)
        total_limit += limit
        sections.append({
            "section":   section,
            "used":      round(min(used, limit), 2),
            "limit":     limit,
            "remaining": round(remaining, 2),
            "percent":   round(min(used / limit * 100, 100), 1) if limit > 0 else 0.0,
        })

    return {
        "fy_start":             fy_start.isoformat(),
        "fy_end":               today.isoformat(),
        "annual_income_so_far": round(annual_income, 2),
        "sections":             sections,
        "total_used":           round(total_used,  2),
        "total_limit":          round(total_limit, 2),
        "overall_pct":          round(total_used / total_limit * 100, 1) if total_limit > 0 else 0.0,
        "potential_tax_saving": round(total_used * 0.30, 2),
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /reports/dashboard/life-insights
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/dashboard/life-insights", summary="Life insights — runway, FIRE clock, wealth velocity, lifestyle creep, lazy money, passive orchard")
async def dashboard_life_insights(
    auth: CurrentUserPayload,
    session: TenantDBSession,
    months: int = Query(default=12, ge=6, le=36),
):
    today = date.today()

    # ── Load all account groups ───────────────────────────────────────────
    asset_accs   = await _load_accounts(session, ["ASSET"])
    liab_accs    = await _load_accounts(session, ["LIABILITY"])
    income_accs  = await _load_accounts(session, ["INCOME"])
    expense_accs = await _load_accounts(session, ["EXPENSE"])

    asset_leafs = [a for a in asset_accs  if not a.is_placeholder]
    liab_leafs  = [a for a in liab_accs   if not a.is_placeholder]
    bs_ids      = [a.id for a in asset_leafs + liab_leafs]
    bs_sums     = await _debit_credit_sums(session, bs_ids, None, today)

    total_assets = _type_total(asset_leafs + liab_leafs, bs_sums, "ASSET")
    total_liabs  = _type_total(asset_leafs + liab_leafs, bs_sums, "LIABILITY")
    nw_now       = float(total_assets - total_liabs)

    liquid_assets = float(sum(
        _signed_balance(*bs_sums.get(a.id, (Decimal(0), Decimal(0))), a.normal_balance)
        for a in asset_leafs if a.code.startswith("11")
    ))

    # ── Monthly income / expense (last N months) ──────────────────────────
    monthly_data: list[dict] = []
    for i in range(months - 1, -1, -1):
        year, month = _month_offset(today, i)
        fd  = date(year, month, 1)
        td  = today if i == 0 else _month_end(year, month)
        inc = float(sum(x["amount"] for x in await _period_items(session, income_accs,  ["INCOME"],  fd, td)))
        exp = float(sum(x["amount"] for x in await _period_items(session, expense_accs, ["EXPENSE"], fd, td)))
        monthly_data.append({"label": f"{year}-{month:02d}", "income": round(inc, 2), "expenses": round(exp, 2)})

    nz_exp = [m for m in monthly_data if m["expenses"] > 0]
    nz_inc = [m for m in monthly_data if m["income"]   > 0]
    avg_exp = sum(m["expenses"] for m in nz_exp) / len(nz_exp) if nz_exp else 0.0
    avg_inc = sum(m["income"]   for m in nz_inc) / len(nz_inc) if nz_inc else 0.0

    # ── SURVIVAL RUNWAY ───────────────────────────────────────────────────
    runway = round(liquid_assets / avg_exp, 1) if avg_exp > 0 else 0.0

    # ── WEALTH VELOCITY ───────────────────────────────────────────────────
    snap_months = min(11, months - 1)
    y12, m12  = _month_offset(today, snap_months)
    old_sums  = await _debit_credit_sums(session, bs_ids, None, _month_end(y12, m12))
    nw_12m_ago    = float(_type_total(asset_leafs + liab_leafs, old_sums, "ASSET")
                         - _type_total(asset_leafs + liab_leafs, old_sums, "LIABILITY"))
    nw_growth_12m = nw_now - nw_12m_ago
    income_12m    = sum(m["income"] for m in monthly_data)
    paise_per_rupee = round(nw_growth_12m / income_12m * 100, 1) if income_12m > 0 else 0.0

    # ── LAZY MONEY ───────────────────────────────────────────────────────
    safety_buffer   = avg_exp * 3
    lazy_amount     = max(0.0, liquid_assets - safety_buffer)
    annual_inf_loss = round(lazy_amount * 0.06, 2)

    # ── FIRE CLOCK ───────────────────────────────────────────────────────
    annual_expenses = avg_exp * 12
    fire_number     = annual_expenses * 25
    avg_surplus     = avg_inc - avg_exp
    progress_pct    = round(min(100.0, max(0.0, nw_now) / fire_number * 100), 1) if fire_number > 0 else 0.0

    if avg_surplus > 0 and nw_now < fire_number:
        months_to_fire = int((fire_number - max(nw_now, 0.0)) / avg_surplus)
        fy, fm = today.year, today.month + months_to_fire
        while fm > 12:
            fm -= 12
            fy += 1
        fire_date = f"{fy}-{fm:02d}"
    elif nw_now >= fire_number > 0:
        months_to_fire = 0
        fire_date      = today.isoformat()[:7]
    else:
        months_to_fire = None
        fire_date      = None

    # ── LIFESTYLE CREEP ───────────────────────────────────────────────────
    half = len(monthly_data) // 2
    first_inc  = sum(m["income"]   for m in monthly_data[:half]) / half if half > 0 else 0.0
    second_inc = sum(m["income"]   for m in monthly_data[half:]) / half if half > 0 else 0.0
    first_exp  = sum(m["expenses"] for m in monthly_data[:half]) / half if half > 0 else 0.0
    second_exp = sum(m["expenses"] for m in monthly_data[half:]) / half if half > 0 else 0.0
    inc_growth = round((second_inc - first_inc) / first_inc  * 100, 1) if first_inc  > 0 else 0.0
    exp_growth = round((second_exp - first_exp) / first_exp  * 100, 1) if first_exp  > 0 else 0.0

    # ── GUILT-FREE SPEND ─────────────────────────────────────────────────
    cur_fd  = date(today.year, today.month, 1)
    cur_inc = float(sum(x["amount"] for x in await _period_items(session, income_accs,  ["INCOME"],  cur_fd, today)))
    cur_exp = float(sum(x["amount"] for x in await _period_items(session, expense_accs, ["EXPENSE"], cur_fd, today)))
    fun_budget = max(0.0, avg_inc - avg_exp * 0.70)

    # ── PASSIVE ORCHARD ───────────────────────────────────────────────────
    inv_accs  = [a for a in income_accs if not a.is_placeholder and a.code.startswith("32")]
    fy_start  = date(today.year if today.month >= 4 else today.year - 1, 4, 1)
    fy_months = max(1, (today.year - fy_start.year) * 12 + today.month - fy_start.month + 1)
    inv_total = float(sum(x["amount"] for x in (
        await _period_items(session, inv_accs, ["INCOME"], fy_start, today) if inv_accs else []
    )))
    monthly_inv = round(inv_total / fy_months, 2)
    coverage    = round(monthly_inv / avg_exp * 100, 1) if avg_exp > 0 else 0.0

    # ── INFLATION GHOST ───────────────────────────────────────────────────
    r = 0.06
    in5  = round(avg_exp * (1 + r) ** 5,  2)
    in10 = round(avg_exp * (1 + r) ** 10, 2)
    in20 = round(avg_exp * (1 + r) ** 20, 2)

    # ── DEBT SNOWBALL ─────────────────────────────────────────────────────
    DEBT_RATES = {"21": 0.36, "22": 0.09, "23": 0.12, "24": 0.18}
    debts: list[dict] = []
    for acc in liab_leafs:
        d, c = bs_sums.get(acc.id, (Decimal(0), Decimal(0)))
        bal  = float(_signed_balance(d, c, acc.normal_balance))
        if bal > 0:
            rate = DEBT_RATES.get(acc.code[:2], 0.12)
            debts.append({
                "name":        acc.name,
                "balance":     round(bal, 2),
                "annual_rate": round(rate * 100, 1),
                "monthly_int": round(bal * rate / 12, 2),
            })
    debts.sort(key=lambda x: -x["annual_rate"])

    return {
        "as_of":   today.isoformat(),
        "monthly": monthly_data,
        "survival_runway": {
            "liquid_assets":        round(liquid_assets, 2),
            "avg_monthly_expenses": round(avg_exp, 2),
            "months":               runway,
            "status":               "safe" if runway >= 6 else "warning" if runway >= 3 else "critical",
        },
        "wealth_velocity": {
            "income_12m":      round(income_12m, 2),
            "nw_growth_12m":   round(nw_growth_12m, 2),
            "paise_per_rupee": paise_per_rupee,
        },
        "lazy_money": {
            "liquid_assets":         round(liquid_assets, 2),
            "safety_buffer":         round(safety_buffer, 2),
            "lazy_amount":           round(lazy_amount, 2),
            "annual_inflation_loss": annual_inf_loss,
        },
        "fire_clock": {
            "annual_expenses":   round(annual_expenses, 2),
            "fire_number":       round(fire_number, 2),
            "current_net_worth": round(nw_now, 2),
            "monthly_savings":   round(avg_surplus, 2),
            "months_to_fire":    months_to_fire,
            "fire_date":         fire_date,
            "progress_pct":      progress_pct,
        },
        "lifestyle_creep": {
            "income_growth_pct":  inc_growth,
            "expense_growth_pct": exp_growth,
            "creep_detected":     bool(exp_growth > inc_growth + 5),
        },
        "guilt_free_spend": {
            "avg_monthly_income":   round(avg_inc, 2),
            "estimated_fixed":      round(avg_exp * 0.70, 2),
            "fun_budget":           round(fun_budget, 2),
            "current_month_income": round(cur_inc, 2),
            "current_month_spent":  round(cur_exp, 2),
        },
        "passive_orchard": {
            "monthly_investment_income": monthly_inv,
            "avg_monthly_expenses":      round(avg_exp, 2),
            "coverage_pct":              coverage,
        },
        "inflation_ghost": {
            "current_monthly":    round(avg_exp, 2),
            "in_5_years":         in5,
            "in_10_years":        in10,
            "in_20_years":        in20,
            "inflation_rate_pct": 6.0,
        },
        "debt_snowball": {
            "debts":             debts,
            "total_debt":        round(float(total_liabs), 2),
            "monthly_int_total": round(sum(d["monthly_int"] for d in debts), 2),
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /reports/journal
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/journal", summary="Journal / Day Book — all transactions as double-entry lines")
async def journal(
    auth: CurrentUserPayload,
    session: TenantDBSession,
    from_date: date | None = Query(default=None, description="Period start (default: first of current month)"),
    to_date:   date | None = Query(default=None, description="Period end (default: today)"),
    page:      int         = Query(default=1, ge=1, description="Page number (1-based)"),
    page_size: int         = Query(default=50, ge=1, le=200, description="Entries per page"),
):
    """Day Book / Journal — every transaction in the period shown as full double-entry.

    Each entry lists all DEBIT legs (left) and CREDIT legs (right) so the
    accounting equation can be visually verified at a glance.
    """
    from collections import defaultdict  # noqa: PLC0415

    today = date.today()
    fd = from_date or today.replace(day=1)
    td = to_date   or today

    base_filter = [
        Transaction.transaction_date >= fd,
        Transaction.transaction_date <= td,
        Transaction.is_void == False,  # noqa: E712
    ]

    total = await session.scalar(
        select(func.count(Transaction.id)).where(*base_filter)
    ) or 0

    txns_result = await session.execute(
        select(Transaction)
        .where(*base_filter)
        .order_by(Transaction.transaction_date, Transaction.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    txns = txns_result.scalars().all()

    txn_ids = [t.id for t in txns]
    lines_rows: list = []
    if txn_ids:
        lines_result = await session.execute(
            select(TransactionLine, Account)
            .join(Account, TransactionLine.account_id == Account.id)
            .where(TransactionLine.transaction_id.in_(txn_ids))
            .order_by(
                TransactionLine.transaction_id,
                TransactionLine.display_order,
                TransactionLine.id,
            )
        )
        lines_rows = lines_result.all()

    lines_map: dict = defaultdict(lambda: {"debits": [], "credits": []})
    for line, acc in lines_rows:
        leg = {
            "account_id":   acc.id,
            "account_code": acc.code,
            "account_name": acc.name,
            "account_type": acc.account_type,
            "amount":       str(line.amount),
            "note":         line.description,
        }
        bucket = "debits" if line.line_type == "DEBIT" else "credits"
        lines_map[line.transaction_id][bucket].append(leg)

    entries = []
    for txn in txns:
        legs      = lines_map[txn.id]
        total_dr  = sum(Decimal(d["amount"]) for d in legs["debits"])
        entries.append({
            "id":               txn.id,
            "date":             txn.transaction_date.isoformat(),
            "description":      txn.description,
            "transaction_type": txn.transaction_type,
            "reference_number": txn.reference_number,
            "debits":           legs["debits"],
            "credits":          legs["credits"],
            "total_amount":     str(total_dr),
        })

    return {
        "from_date":   fd.isoformat(),
        "to_date":     td.isoformat(),
        "page":        page,
        "page_size":   page_size,
        "total":       total,
        "total_pages": -(-total // page_size) if total else 0,
        "entries":     entries,
    }


# ─────────────────────────────────────────────────────────────────────────────
# POST /reports/insights  (LLM — optional)
# ─────────────────────────────────────────────────────────────────────────────

class InsightsRequest(BaseModel):
    report_type: str
    data: dict[str, Any]
    provider_id: str | None = None


@router.post("/insights", summary="Generate LLM narrative commentary on a report")
async def get_insights(
    body: InsightsRequest,
    auth: CurrentUserPayload,
    session: TenantDBSession,
    settings: SettingsDep,
):
    try:
        from api.routers.llm import _resolve_provider  # noqa: PLC0415
        from db.models.system import LlmProvider  # noqa: PLC0415

        pid = body.provider_id
        # When no provider_id specified, auto-detect: prefer is_default, fall back to any active
        if pid is None:
            _prov_result = await session.execute(
                select(LlmProvider)
                .where(LlmProvider.is_active == True)  # noqa: E712
                .order_by(LlmProvider.is_default.desc())
                .limit(1)
            )
            db_prov = _prov_result.scalar_one_or_none()
            if db_prov:
                pid = db_prov.provider_id

        provider_name, provider = _resolve_provider(user_id, pid, settings, session)
    except HTTPException:
        return {"insight": None, "error": "No LLM provider configured. Add one in Settings → LLM Providers."}

    prompt = (
        f"You are a personal finance advisor. Analyze this {body.report_type} report "
        "and provide 3-5 sentences of concise, actionable financial insights.\n\n"
        f"Report data:\n{json.dumps(body.data, indent=2, default=str)}\n\n"
        "Focus on key trends, areas of concern, and one concrete recommendation. "
        "Be specific. Write plain prose (no bullet points or headers)."
    )

    try:
        if provider_name == "gemini":
            from google import genai  # noqa: PLC0415
            from google.genai import types  # noqa: PLC0415
            client = genai.Client(api_key=provider._api_key)
            resp = client.models.generate_content(
                model=provider._text_model,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.3, max_output_tokens=512),
            )
            return {"insight": resp.text, "provider": provider_name}

        elif provider_name == "openai":
            from openai import OpenAI  # noqa: PLC0415
            client = OpenAI(api_key=provider._api_key)
            resp = client.chat.completions.create(
                model=provider._text_model or "gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=512,
                temperature=0.3,
            )
            return {"insight": resp.choices[0].message.content, "provider": provider_name}

        elif provider_name == "anthropic":
            import anthropic  # noqa: PLC0415
            client = anthropic.Anthropic(api_key=provider._api_key)
            resp = client.messages.create(
                model=provider._text_model or "claude-3-haiku-20240307",
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
            )
            return {"insight": resp.content[0].text, "provider": provider_name}

        else:
            return {"insight": None, "error": f"Unsupported provider: {provider_name}"}

    except Exception as exc:  # noqa: BLE001
        return {"insight": None, "error": str(exc)}
