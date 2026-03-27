"""Budgets CRUD API — all budgets are scoped to the authenticated tenant via RLS.

Endpoints:
    GET    /api/v1/budgets              — list tenant's budgets (active_only=true by default)
    POST   /api/v1/budgets              — create a budget with line items
    GET    /api/v1/budgets/{id}         — get a single budget with items
    DELETE /api/v1/budgets/{id}         — deactivate (soft-delete) a budget
"""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from api.deps import CurrentUserPayload, TenantDBSession
from db.models.accounts import Account
from db.models.budgets import Budget, BudgetItem

router = APIRouter(prefix="/budgets", tags=["Budgets"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class BudgetItemCreate(BaseModel):
    account_code: str
    planned_amount: Decimal
    notes: str | None = None


class BudgetCreate(BaseModel):
    name: str
    period_type: str = "MONTHLY"
    start_date: date
    end_date: date | None = None
    items: list[BudgetItemCreate] = []


class BudgetItemOut(BaseModel):
    id: int
    account_id: int
    account_code: str
    account_name: str
    planned_amount: str
    notes: str | None


class BudgetOut(BaseModel):
    id: int
    name: str
    period_type: str
    start_date: str
    end_date: str | None
    is_active: bool
    items: list[BudgetItemOut]


async def _item_out(bi: BudgetItem, acc: Account | None) -> BudgetItemOut:
    return BudgetItemOut(
        id=bi.id,
        account_id=bi.account_id,
        account_code=acc.code if acc else "",
        account_name=acc.name if acc else "",
        planned_amount=str(bi.planned_amount),
        notes=bi.notes,
    )


async def _budget_out(b: Budget, session) -> BudgetOut:
    acc_ids = {bi.account_id for bi in b.items}
    accs: dict[int, Account] = {}
    if acc_ids:
        result = await session.execute(select(Account).where(Account.id.in_(acc_ids)))
        accs = {a.id: a for a in result.scalars().all()}
    return BudgetOut(
        id=b.id,
        name=b.name,
        period_type=b.period_type,
        start_date=str(b.start_date),
        end_date=str(b.end_date) if b.end_date else None,
        is_active=b.is_active,
        items=[await _item_out(bi, accs.get(bi.account_id)) for bi in b.items],
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=list[BudgetOut], summary="List tenant's budgets")
async def list_budgets(auth: CurrentUserPayload, session: TenantDBSession, active_only: bool = True):
    stmt = select(Budget)
    if active_only:
        stmt = stmt.where(Budget.is_active == True)  # noqa: E712
    result = await session.execute(stmt)
    budgets = result.scalars().all()
    return [await _budget_out(b, session) for b in budgets]


@router.post("", response_model=BudgetOut, status_code=201, summary="Create a budget")
async def create_budget(auth: CurrentUserPayload, session: TenantDBSession, body: BudgetCreate):
    tenant_id = uuid.UUID(auth.tenant_id)
    budget = Budget(
        tenant_id=tenant_id,
        name=body.name,
        period_type=body.period_type,
        start_date=body.start_date,
        end_date=body.end_date,
    )
    session.add(budget)
    await session.flush()

    for item_in in body.items:
        acc = await session.scalar(select(Account).where(Account.code == item_in.account_code))
        if not acc:
            raise HTTPException(400, detail=f"Account code '{item_in.account_code}' not found")
        session.add(BudgetItem(
            tenant_id=tenant_id,
            budget_id=budget.id,
            account_id=acc.id,
            planned_amount=item_in.planned_amount,
            notes=item_in.notes,
        ))
    await session.flush()
    return await _budget_out(budget, session)


@router.get("/{budget_id}", response_model=BudgetOut, summary="Get a budget")
async def get_budget(auth: CurrentUserPayload, session: TenantDBSession, budget_id: int):
    b = await session.scalar(select(Budget).where(Budget.id == budget_id))
    if not b:
        raise HTTPException(404, "Budget not found")
    return await _budget_out(b, session)


@router.delete("/{budget_id}", status_code=204, summary="Deactivate (soft-delete) a budget")
async def delete_budget(auth: CurrentUserPayload, session: TenantDBSession, budget_id: int):
    b = await session.scalar(select(Budget).where(Budget.id == budget_id))
    if not b:
        raise HTTPException(404, "Budget not found")
    b.is_active = False
