"""Goals CRUD API — all goals are scoped to the authenticated user.

Endpoints:
    GET    /api/v1/goals            — list this user's goals with progress %
    POST   /api/v1/goals            — create a goal
    GET    /api/v1/goals/{id}       — get single goal
    PATCH  /api/v1/goals/{id}       — partial update (including current_amount)
    DELETE /api/v1/goals/{id}       — delete a goal
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.deps import CurrentUser, DBSession
from repositories.sqla_goal_repo import SqlAlchemyGoalRepository

router = APIRouter(prefix="/goals", tags=["Goals"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class GoalCreate(BaseModel):
    name: str
    goal_type: str = "OTHERS"
    target_amount: Decimal
    current_amount: Decimal = Decimal(0)
    target_date: date | None = None
    start_date: date
    priority: str = "MEDIUM"
    icon: str | None = None
    color: str | None = None
    notes: str | None = None


class GoalUpdate(BaseModel):
    name: str | None = None
    goal_type: str | None = None
    target_amount: Decimal | None = None
    current_amount: Decimal | None = None
    target_date: date | None = None
    priority: str | None = None
    status: str | None = None
    icon: str | None = None
    color: str | None = None
    notes: str | None = None


class GoalOut(BaseModel):
    id: int
    name: str
    goal_type: str
    target_amount: str
    current_amount: str
    target_date: str | None
    start_date: str
    priority: str
    status: str
    icon: str | None
    color: str | None
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
        start_date=str(g.start_date),
        priority=g.priority,
        status=g.status,
        icon=g.icon,
        color=g.color,
        notes=g.notes,
        progress_pct=pct,
    )


def _parse_user_id(user: str) -> int:
    try:
        return int(user)
    except (ValueError, TypeError):
        return 0


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=list[GoalOut], summary="List this user's goals")
def list_goals(user: CurrentUser, session: DBSession):
    uid = _parse_user_id(user)
    repo = SqlAlchemyGoalRepository(session)
    return [_to_out(g) for g in repo.list(user_id=uid)]


@router.post("", response_model=GoalOut, status_code=201, summary="Create a goal")
def create_goal(user: CurrentUser, session: DBSession, body: GoalCreate):
    uid = _parse_user_id(user)
    repo = SqlAlchemyGoalRepository(session)
    data = body.model_dump()
    data["user_id"] = uid
    g = repo.create(data)
    return _to_out(g)


@router.get("/{goal_id}", response_model=GoalOut, summary="Get a single goal")
def get_goal(user: CurrentUser, session: DBSession, goal_id: int):
    uid = _parse_user_id(user)
    repo = SqlAlchemyGoalRepository(session)
    g = repo.get(goal_id, user_id=uid)
    if not g:
        raise HTTPException(404, "Goal not found")
    return _to_out(g)


@router.patch("/{goal_id}", response_model=GoalOut, summary="Partially update a goal")
def update_goal(user: CurrentUser, session: DBSession, goal_id: int, body: GoalUpdate):
    uid = _parse_user_id(user)
    repo = SqlAlchemyGoalRepository(session)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    g = repo.update(goal_id, updates, user_id=uid)
    if not g:
        raise HTTPException(404, "Goal not found")
    return _to_out(g)


@router.delete("/{goal_id}", status_code=204, summary="Delete a goal")
def delete_goal(user: CurrentUser, session: DBSession, goal_id: int):
    uid = _parse_user_id(user)
    repo = SqlAlchemyGoalRepository(session)
    g = repo.get(goal_id, user_id=uid)
    if not g:
        raise HTTPException(404, "Goal not found")
    session.delete(g)
