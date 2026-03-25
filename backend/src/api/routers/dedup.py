"""SM-F Deduplication Engine REST API."""
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from api.deps import CurrentUser, DBSession
from api.routers.imports import _batches
from api.routers.normalize import _normalized_rows
from repositories.sqla_account_repo import AccountRepository
from repositories.sqla_transaction_repo import TransactionRepository
from services.dedup_service import DedupService

router = APIRouter(prefix="/dedup", tags=["Deduplication (SM-F)"])
_svc = DedupService()


class DedupResponse(BaseModel):
    batch_id: str
    txn_new: int
    txn_duplicate: int
    txn_transfer_pairs: int
    duplicate_row_ids: list[str]
    transfer_pairs: list[list[str]]


@router.post(
    "/{batch_id}",
    response_model=DedupResponse,
    summary="Deduplicate normalized rows (SM-F)",
    operation_id="dedupBatch",
)
def dedup_batch(
    batch_id: str,
    user_id: CurrentUser,
    session: DBSession,
    account_id: str = "",
) -> DedupResponse:
    batch = _batches.get(batch_id)
    if not batch or getattr(batch, "user_id", None) != user_id:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND"})
    rows = _normalized_rows.get(batch_id, [])
    if not rows:
        raise HTTPException(status_code=422, detail={"error": "NO_NORMALIZED_ROWS", "message": "Normalize the batch first."})

    effective_account_id = account_id or getattr(batch, "account_id", batch_id)

    # Pull committed hashes from the DB for this account (safety-net for stale JSON store)
    db_hashes: set[str] = set()
    acc_repo = AccountRepository(session)
    acc = acc_repo.find_by_code(effective_account_id)
    if acc is None:
        # account_id may be an integer string or UUID; try integer lookup
        try:
            acc = acc_repo.get(int(effective_account_id))
        except (ValueError, TypeError):
            pass
    if acc:
        db_hashes = TransactionRepository(session).get_committed_hashes_for_account(acc.id)

    result = _svc.dedup_batch(
        user_id=user_id,
        batch_id=batch_id,
        account_id=effective_account_id,
        rows=rows,
        db_hashes=db_hashes,
    )
    batch.txn_new       = result.txn_new
    batch.txn_duplicate = result.txn_duplicate
    return DedupResponse(
        batch_id=batch_id,
        txn_new=result.txn_new,
        txn_duplicate=result.txn_duplicate,
        txn_transfer_pairs=len(result.transfer_pairs),
        duplicate_row_ids=result.duplicates,
        transfer_pairs=[[a, b] for a, b in result.transfer_pairs],
    )
