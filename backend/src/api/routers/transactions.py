"""Committed transactions read API.

Endpoints:
    GET /api/v1/transactions          — paginated list with optional date filter
    GET /api/v1/transactions/count    — total non-void transaction count
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import desc, func, select

from api.deps import CurrentUser, DBSession
from db.models.accounts import Account
from db.models.transactions import Transaction, TransactionLine

router = APIRouter(prefix="/transactions", tags=["Transactions"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class TxnLineOut(BaseModel):
    id: int
    account_code: str
    account_name: str
    line_type: str
    amount: str
    description: str | None


class TxnOut(BaseModel):
    id: int
    transaction_date: str
    description: str
    transaction_type: str
    status: str
    is_void: bool
    reference_number: str | None
    lines: list[TxnLineOut]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/count", summary="Count committed (non-void) transactions")
def count_transactions(user: CurrentUser, session: DBSession) -> dict:
    n = session.scalar(
        select(func.count()).select_from(Transaction).where(Transaction.is_void == False)
    )
    return {"count": n or 0}


@router.get("", response_model=list[TxnOut], summary="List committed transactions")
def list_transactions(
    user: CurrentUser,
    session: DBSession,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
):
    stmt = (
        select(Transaction)
        .where(Transaction.is_void == False)
        .order_by(desc(Transaction.transaction_date))
        .limit(limit)
        .offset(offset)
    )
    if from_date:
        stmt = stmt.where(Transaction.transaction_date >= from_date)
    if to_date:
        stmt = stmt.where(Transaction.transaction_date <= to_date)

    txns = list(session.scalars(stmt).all())

    # Batch-load all referenced accounts to avoid N+1
    acc_ids = {ln.account_id for txn in txns for ln in txn.lines}
    accs: dict[int, Account] = (
        {a.id: a for a in session.scalars(select(Account).where(Account.id.in_(acc_ids))).all()}
        if acc_ids else {}
    )

    results = []
    for txn in txns:
        lines = [
            TxnLineOut(
                id=ln.id,
                account_code=accs[ln.account_id].code if ln.account_id in accs else "",
                account_name=accs[ln.account_id].name if ln.account_id in accs else "",
                line_type=ln.line_type,
                amount=str(ln.amount),
                description=ln.description,
            )
            for ln in txn.lines
        ]
        results.append(
            TxnOut(
                id=txn.id,
                transaction_date=str(txn.transaction_date),
                description=txn.description,
                transaction_type=txn.transaction_type,
                status=txn.status,
                is_void=txn.is_void,
                reference_number=txn.reference_number,
                lines=lines,
            )
        )
    return results
