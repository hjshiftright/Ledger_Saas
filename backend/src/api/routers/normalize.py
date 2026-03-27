"""SM-E Schema Normalization REST API."""
from __future__ import annotations
from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from api.deps import CurrentUserPayload
from api.routers.imports import _batches
from api.routers.parser import _parsed_rows
from core.models.enums import BatchStatus
from services.normalize_service import NormalizeService, NormalizedTransaction

router = APIRouter(prefix="/normalize", tags=["Schema Normalization (SM-E)"])
_svc = NormalizeService()
_normalized_rows: dict[str, list[NormalizedTransaction]] = {}


class NormalizeResponse(BaseModel):
    batch_id: str
    rows_normalized: int
    rows_skipped: int
    success_rate: float
    warnings: list[str]


class NormalizedRowOut(BaseModel):
    row_id: str
    batch_id: str
    txn_date: str | None
    raw_date: str
    amount: str
    is_debit: bool
    narration: str
    reference: str | None
    txn_type: str
    row_confidence: float
    extra_fields: dict[str, Any]


@router.post("/{batch_id}", response_model=NormalizeResponse, summary="Normalize raw parsed rows (SM-E)", operation_id="normalizeBatch")
async def normalize_batch(batch_id: str, auth: CurrentUserPayload) -> NormalizeResponse:
    batch = _batches.get(batch_id)
    if not batch or getattr(batch, "tenant_id", None) != auth.tenant_id:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND"})
    raw = _parsed_rows.get(batch_id, [])
    if not raw:
        raise HTTPException(status_code=422, detail={"error": "NO_PARSED_ROWS", "message": "Parse the batch first."})
    result = _svc.normalize_batch(batch_id, raw)
    _normalized_rows[batch_id] = result.rows
    batch.status = BatchStatus.NORMALIZING
    return NormalizeResponse(batch_id=batch_id, rows_normalized=result.rows_normalized,
                             rows_skipped=result.rows_skipped, success_rate=round(result.success_rate, 3),
                             warnings=result.warnings)


@router.get("/{batch_id}/rows", response_model=list[NormalizedRowOut], summary="Get normalized rows", operation_id="getNormalizedRows")
async def get_normalized_rows(batch_id: str, auth: CurrentUserPayload) -> list[NormalizedRowOut]:
    batch = _batches.get(batch_id)
    if not batch or getattr(batch, "tenant_id", None) != auth.tenant_id:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND"})
    return [
        NormalizedRowOut(row_id=r.row_id, batch_id=r.batch_id, txn_date=str(r.txn_date) if r.txn_date else None,
                         raw_date=r.raw_date, amount=str(r.amount), is_debit=r.is_debit,
                         narration=r.narration, reference=r.reference, txn_type=r.txn_type.value,
                         row_confidence=r.row_confidence, extra_fields=r.extra_fields)
        for r in _normalized_rows.get(batch_id, [])
    ]
