"""Goals CRUD API — all goals are scoped to the authenticated tenant via RLS.

Endpoints:
    GET    /api/v1/goals            — list tenant's goals with progress %
    POST   /api/v1/goals            — create a goal
    GET    /api/v1/goals/{id}       — get single goal
    PATCH  /api/v1/goals/{id}       — partial update (including current_amount)
    DELETE /api/v1/goals/{id}       — delete a goal
"""
from __future__ import annotations

import logging
import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.deps import CurrentUserPayload, TenantDBSession
from repositories.sqla_goal_repo import SqlAlchemyGoalRepository

router = APIRouter(prefix="/goals", tags=["Goals"])
logger = logging.getLogger(__name__)


# ── Schemas ───────────────────────────────────────────────────────────────────

class GoalCreate(BaseModel):
    name: str
    goal_type: str = "OTHERS"
    target_amount: Decimal
    current_amount: Decimal = Decimal(0)
    target_date: date | None = None
    currency_code: str = "INR"
    sip_amount: Decimal | None = None
    expected_return_rate: Decimal | None = None
    notes: str | None = None


class GoalUpdate(BaseModel):
    name: str | None = None
    goal_type: str | None = None
    target_amount: Decimal | None = None
    current_amount: Decimal | None = None
    target_date: date | None = None
    is_active: bool | None = None
    sip_amount: Decimal | None = None
    notes: str | None = None


class GoalOut(BaseModel):
    id: int
    name: str
    goal_type: str
    target_amount: str
    current_amount: str
    target_date: str | None
    currency_code: str
    is_active: bool
    notes: str | None
    progress_pct: float


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_out(g) -> GoalOut:
    target = float(g.target_amount) if g.target_amount else 0.0
    current = float(g.current_amount) if g.current_amount else 0.0
    pct = round(min(current / target * 100, 100.0), 1) if target > 0 else 0.0
    return GoalOut(
        id=g.id,
        name=g.name,
        goal_type=g.goal_type,
        target_amount=str(g.target_amount),
        current_amount=str(g.current_amount),
        target_date=str(g.target_date) if g.target_date else None,
        currency_code=g.currency_code,
        is_active=g.is_active,
        notes=g.notes,
        progress_pct=pct,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=list[GoalOut], summary="List tenant's goals")
async def list_goals(auth: CurrentUserPayload, session: TenantDBSession):
    repo = SqlAlchemyGoalRepository(session)
    return [_to_out(g) for g in await repo.list()]


@router.post("", response_model=GoalOut, status_code=201, summary="Create a goal")
async def create_goal(auth: CurrentUserPayload, session: TenantDBSession, body: GoalCreate):
    repo = SqlAlchemyGoalRepository(session)
    data = body.model_dump()
    data["tenant_id"] = uuid.UUID(auth.tenant_id)
    g = await repo.create(data)
    logger.info(
        "[DB PERSIST] Goal CREATED — tenant=%s user=%s id=%s name=%r type=%s target=%s",
        auth.tenant_id, auth.user_id, g.id, g.name, g.goal_type, g.target_amount,
    )
    return _to_out(g)


@router.get("/{goal_id}", response_model=GoalOut, summary="Get a single goal")
async def get_goal(auth: CurrentUserPayload, session: TenantDBSession, goal_id: int):
    repo = SqlAlchemyGoalRepository(session)
    g = await repo.get(goal_id)
    if not g:
        raise HTTPException(404, "Goal not found")
    return _to_out(g)


@router.patch("/{goal_id}", response_model=GoalOut, summary="Partially update a goal")
async def update_goal(auth: CurrentUserPayload, session: TenantDBSession, goal_id: int, body: GoalUpdate):
    repo = SqlAlchemyGoalRepository(session)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    g = await repo.update(goal_id, updates)
    if not g:
        raise HTTPException(404, "Goal not found")
    logger.info(
        "[DB PERSIST] Goal UPDATED — tenant=%s user=%s id=%s name=%r fields=%s",
        auth.tenant_id, auth.user_id, g.id, g.name, list(updates.keys()),
    )
    return _to_out(g)


@router.delete("/{goal_id}", status_code=204, summary="Delete a goal")
async def delete_goal(auth: CurrentUserPayload, session: TenantDBSession, goal_id: int):
    repo = SqlAlchemyGoalRepository(session)
    g = await repo.get(goal_id)
    if not g:
        raise HTTPException(404, "Goal not found")
    logger.info(
        "[DB PERSIST] Goal DELETED — tenant=%s user=%s id=%s name=%r",
        auth.tenant_id, auth.user_id, g.id, g.name,
    )
    await session.delete(g)
