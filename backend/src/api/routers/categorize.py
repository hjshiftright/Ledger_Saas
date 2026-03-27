"""SM-G Categorization Engine REST API."""
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from api.deps import CurrentUserPayload, TenantDBSession
from api.routers.imports import _batches
from api.routers.normalize import _normalized_rows
from services.categorize_service import CategorizeService

router = APIRouter(prefix="/categorize", tags=["Categorization Engine (SM-G)"])
_svc = CategorizeService()


class CategorizeResponse(BaseModel):
    batch_id: str
    txn_categorized: int
    mean_confidence: float
    categories_found: list[str]


class LearnCorrectionRequest(BaseModel):
    narration_pattern: str
    category_code: str


@router.post("/{batch_id}", response_model=CategorizeResponse, summary="Categorize transactions (SM-G)", operation_id="categorizeBatch")
async def categorize_batch(batch_id: str, auth: CurrentUserPayload, session: TenantDBSession) -> CategorizeResponse:
    batch = _batches.get(batch_id)
    if not batch or getattr(batch, "tenant_id", None) != auth.tenant_id:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND"})
    rows = _normalized_rows.get(batch_id, [])
    if not rows:
        raise HTTPException(status_code=422, detail={"error": "NO_NORMALIZED_ROWS"})
    result = await _svc.categorize_batch(batch_id=batch_id, rows=rows, session=session)
    return CategorizeResponse(batch_id=batch_id, txn_categorized=len(result.results),
                              mean_confidence=round(result.mean_confidence, 3),
                              categories_found=result.categories_found)


@router.post("/rules/learn", status_code=204, summary="Learn from user correction (R2.4)", operation_id="learnCorrectionRule")
async def learn_correction(body: LearnCorrectionRequest, auth: CurrentUserPayload, session: TenantDBSession) -> None:
    await _svc.learn_from_correction(body.narration_pattern, body.category_code, session)
