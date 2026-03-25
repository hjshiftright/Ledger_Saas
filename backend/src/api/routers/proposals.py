"""SM-I Transaction Proposal REST API."""
from __future__ import annotations
from decimal import Decimal
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from api.deps import CurrentUser, DBSession
from api.routers.imports import _batches
from api.routers.normalize import _normalized_rows
from services.proposal_service import ProposalService, ProposedJournalEntry
from services.approval_service import ApprovalService

router = APIRouter(prefix="/proposals", tags=["Transaction Proposals (SM-I)"])
_svc = ProposalService()
_proposals: dict[str, list[ProposedJournalEntry]] = {}


class JournalLineOut(BaseModel):
    account_code: str
    account_name: str
    debit: str
    credit: str


class ProposalOut(BaseModel):
    proposal_id: str
    batch_id: str
    row_id: str
    txn_date: str | None
    narration: str
    reference: str | None
    lines: list[JournalLineOut]
    overall_confidence: float
    confidence_band: str
    status: str
    is_balanced: bool


class BulkApproveRequest(BaseModel):
    proposal_ids: list[str]


class CommitResponse(BaseModel):
    orm_batch_id: int
    committed: int
    skipped: int
    already_posted: int
    transaction_ids: list[int]


def _to_out(p: ProposedJournalEntry) -> ProposalOut:
    return ProposalOut(
        proposal_id=p.proposal_id, batch_id=p.batch_id, row_id=p.row_id,
        txn_date=str(p.txn_date) if p.txn_date else None, narration=p.narration,
        reference=p.reference,
        lines=[JournalLineOut(account_code=l.account_code, account_name=l.account_name,
                              debit=str(l.debit), credit=str(l.credit)) for l in p.lines],
        overall_confidence=p.overall_confidence, confidence_band=p.confidence_band,
        status=p.status, is_balanced=p.is_balanced,
    )


@router.post("/{batch_id}/generate", response_model=list[ProposalOut], summary="Generate journal entry proposals (SM-I)", operation_id="generateProposals")
def generate_proposals(batch_id: str, user_id: CurrentUser, bank_account_id: str = Query(default="1102")) -> list[ProposalOut]:
    batch = _batches.get(batch_id)
    if not batch or getattr(batch, "user_id", None) != user_id:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND"})
    rows = _normalized_rows.get(batch_id, [])
    if not rows:
        raise HTTPException(status_code=422, detail={"error": "NO_NORMALIZED_ROWS"})
    result = _svc.propose_batch(batch_id=batch_id, bank_account_id=bank_account_id, rows=rows)
    _proposals[batch_id] = result.proposals
    return [_to_out(p) for p in result.proposals]


@router.get("/{batch_id}", response_model=list[ProposalOut], summary="Get proposals for a batch", operation_id="getProposals")
def get_proposals(batch_id: str, user_id: CurrentUser, status_filter: str | None = None) -> list[ProposalOut]:
    batch = _batches.get(batch_id)
    if not batch or getattr(batch, "user_id", None) != user_id:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND"})
    proposals = _proposals.get(batch_id, [])
    if status_filter:
        proposals = [p for p in proposals if p.status == status_filter.upper()]
    return [_to_out(p) for p in proposals]


@router.post(
    "/{batch_id}/approve",
    status_code=200,
    summary="Mark proposals as approved (in-memory; call /commit to persist to DB)",
    operation_id="bulkApproveProposals",
)
def bulk_approve(batch_id: str, body: BulkApproveRequest, user_id: CurrentUser) -> dict:
    """Mark selected proposals CONFIRMED in the in-memory store.

    This is a lightweight, reversible step. The proposals are NOT yet written
    to the database.  Call POST /{batch_id}/commit to persist them to SQLite.
    """
    batch = _batches.get(batch_id)
    if not batch or getattr(batch, "user_id", None) != user_id:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND"})
    proposal_map = {p.proposal_id: p for p in _proposals.get(batch_id, [])}
    approved = 0
    for pid in body.proposal_ids:
        if pid in proposal_map:
            proposal_map[pid].status = "CONFIRMED"
            approved += 1
    return {"approved": approved, "not_found": len(body.proposal_ids) - approved}


class UpdateLineRequest(BaseModel):
    line_index: int
    account_code: str
    account_name: str


@router.patch(
    "/{batch_id}/{proposal_id}",
    response_model=ProposalOut,
    status_code=200,
    summary="Update a journal line's account assignment in a proposal",
    operation_id="updateProposalLine",
)
def update_proposal_line(
    batch_id: str,
    proposal_id: str,
    body: UpdateLineRequest,
    user_id: CurrentUser,
) -> ProposalOut:
    """Reassign one journal line's account (in-memory only; takes effect on /commit)."""
    batch = _batches.get(batch_id)
    if not batch or getattr(batch, "user_id", None) != user_id:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND"})
    proposals = _proposals.get(batch_id, [])
    p = next((x for x in proposals if x.proposal_id == proposal_id), None)
    if not p:
        raise HTTPException(status_code=404, detail={"error": "PROPOSAL_NOT_FOUND"})
    if not (0 <= body.line_index < len(p.lines)):
        raise HTTPException(status_code=422, detail={"error": "INVALID_LINE_INDEX"})
    line = p.lines[body.line_index]
    line.account_id = body.account_code
    line.account_code = body.account_code
    line.account_name = body.account_name
    return _to_out(p)


@router.post(
    "/{batch_id}/commit",
    response_model=CommitResponse,
    status_code=200,
    summary="Persist CONFIRMED proposals to the SQLite database",
    operation_id="commitProposals",
)
def commit_proposals(batch_id: str, user_id: CurrentUser, session: DBSession) -> CommitResponse:
    """Write all CONFIRMED proposals for this batch to the database.

    For each CONFIRMED proposal:
    - Resolves account codes to integer Account.id values.
    - Creates Transaction + TransactionLine + ReconciliationRecord rows.
    - Marks the ORM ImportBatch as COMPLETED.

    Re-entrant: proposals whose txn_hash is already in the DB are skipped
    (already_posted count), so calling this endpoint multiple times is safe.
    """
    batch = _batches.get(batch_id)
    if not batch or getattr(batch, "user_id", None) != user_id:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND"})

    proposals = _proposals.get(batch_id, [])
    confirmed = [p for p in proposals if p.status == "CONFIRMED"]
    if not confirmed:
        raise HTTPException(
            status_code=422,
            detail={"error": "NO_CONFIRMED_PROPOSALS", "message": "Approve at least one proposal before committing."},
        )

    svc = ApprovalService(session)
    result = svc.commit_proposals(confirmed, batch)
    return CommitResponse(**result)
