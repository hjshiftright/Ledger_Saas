"""Budgets CRUD API — all budgets are scoped to the authenticated user.

Endpoints:
    GET    /api/v1/budgets              — list this user's budgets (active_only=true by default)
    POST   /api/v1/budgets              — create a budget with line items
    GET    /api/v1/budgets/{id}         — get a single budget with items
    DELETE /api/v1/budgets/{id}         — deactivate (soft-delete) a budget
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from api.deps import CurrentUser, DBSession
from db.models.accounts import Account
from db.models.budgets import Budget, BudgetItem

router = APIRouter(prefix="/budgets", tags=["Budgets"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_user_id(user: str) -> int:
    try:
        return int(user)
    except (ValueError, TypeError):
        return 0


# ── Schemas ───────────────────────────────────────────────────────────────────

class BudgetItemCreate(BaseModel):
    account_code: str
    budgeted_amount: Decimal
    alert_threshold_pct: Decimal = Decimal(80)
    rollover_unused: bool = False
    notes: str | None = None


class BudgetCreate(BaseModel):
    name: str
    period_type: str = "MONTHLY"
    start_date: date
    end_date: date
    is_recurring: bool = False
    items: list[BudgetItemCreate] = []


class BudgetItemOut(BaseModel):
    id: int
    account_id: int
    account_code: str
    account_name: str
    budgeted_amount: str
    spent_amount: str
    alert_threshold_pct: str | None
    rollover_unused: bool
    notes: str | None


class BudgetOut(BaseModel):
    id: int
    name: str
    period_type: str
    start_date: str
    end_date: str
    total_budgeted: str
    total_spent: str
    is_active: bool
    is_recurring: bool
    items: list[BudgetItemOut]


def _item_out(bi: BudgetItem, acc: Account | None) -> BudgetItemOut:
    return BudgetItemOut(
        id=bi.id,
        account_id=bi.account_id,
        account_code=acc.code if acc else "",
        account_name=acc.name if acc else "",
        budgeted_amount=str(bi.budgeted_amount),
        spent_amount=str(bi.spent_amount),
        alert_threshold_pct=str(bi.alert_threshold_pct) if bi.alert_threshold_pct is not None else None,
        rollover_unused=bi.rollover_unused,
        notes=bi.notes,
    )


def _budget_out(b: Budget, session) -> BudgetOut:
    acc_ids = {bi.account_id for bi in b.items}
    accs: dict[int, Account] = (
        {a.id: a for a in session.scalars(select(Account).where(Account.id.in_(acc_ids))).all()}
        if acc_ids else {}
    )
    return BudgetOut(
        id=b.id,
        name=b.name,
        period_type=b.period_type,
        start_date=str(b.start_date),
        end_date=str(b.end_date),
        total_budgeted=str(b.total_budgeted),
        total_spent=str(b.total_spent),
        is_active=b.is_active,
        is_recurring=b.is_recurring,
        items=[_item_out(bi, accs.get(bi.account_id)) for bi in b.items],
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=list[BudgetOut], summary="List this user's budgets")
def list_budgets(user: CurrentUser, session: DBSession, active_only: bool = True):
    uid = _parse_user_id(user)
    stmt = select(Budget).where(Budget.user_id == uid)
    if active_only:
        stmt = stmt.where(Budget.is_active == True)
    budgets = list(session.scalars(stmt).all())
    return [_budget_out(b, session) for b in budgets]


@router.post("", response_model=BudgetOut, status_code=201, summary="Create a budget")
def create_budget(user: CurrentUser, session: DBSession, body: BudgetCreate):
    uid = _parse_user_id(user)
    total_budgeted = sum((item.budgeted_amount for item in body.items), Decimal(0))
    budget = Budget(
        user_id=uid,
        name=body.name,
        period_type=body.period_type,
        start_date=body.start_date,
        end_date=body.end_date,
        is_recurring=body.is_recurring,
        total_budgeted=total_budgeted,
        total_spent=Decimal(0),
    )
    session.add(budget)
    session.flush()

    for item_in in body.items:
        acc = session.scalar(select(Account).where(Account.code == item_in.account_code))
        if not acc:
            raise HTTPException(400, detail=f"Account code '{item_in.account_code}' not found")
        session.add(BudgetItem(
            budget_id=budget.id,
            account_id=acc.id,
            budgeted_amount=item_in.budgeted_amount,
            spent_amount=Decimal(0),
            rollover_amount=Decimal(0),
            alert_threshold_pct=item_in.alert_threshold_pct,
            rollover_unused=item_in.rollover_unused,
            notes=item_in.notes,
        ))
    session.flush()
    return _budget_out(budget, session)


@router.get("/{budget_id}", response_model=BudgetOut, summary="Get a budget")
def get_budget(user: CurrentUser, session: DBSession, budget_id: int):
    uid = _parse_user_id(user)
    b = session.scalar(select(Budget).where(Budget.id == budget_id, Budget.user_id == uid))
    if not b:
        raise HTTPException(404, "Budget not found")
    return _budget_out(b, session)


@router.delete("/{budget_id}", status_code=204, summary="Deactivate (soft-delete) a budget")
def delete_budget(user: CurrentUser, session: DBSession, budget_id: int):
    uid = _parse_user_id(user)
    b = session.scalar(select(Budget).where(Budget.id == budget_id, Budget.user_id == uid))
    if not b:
        raise HTTPException(404, "Budget not found")
    b.is_active = False
