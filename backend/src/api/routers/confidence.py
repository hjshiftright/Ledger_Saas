"""SM-H Confidence Scoring REST API."""
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from api.deps import CurrentUser
from api.routers.imports import _batches
from api.routers.normalize import _normalized_rows
from services.confidence_service import ConfidenceService

router = APIRouter(prefix="/confidence", tags=["Confidence Scoring (SM-H)"])
_svc = ConfidenceService()


class ConfidenceScoreResponse(BaseModel):
    batch_id: str
    total: int
    green: int
    yellow: int
    red: int
    mean_confidence: float


@router.post("/{batch_id}", response_model=ConfidenceScoreResponse, summary="Score transaction confidence (SM-H)", operation_id="scoreBatch")
def score_batch(batch_id: str, user_id: CurrentUser) -> ConfidenceScoreResponse:
    batch = _batches.get(batch_id)
    if not batch or getattr(batch, "user_id", None) != user_id:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND"})
    rows = _normalized_rows.get(batch_id, [])
    if not rows:
        raise HTTPException(status_code=422, detail={"error": "NO_NORMALIZED_ROWS"})
    result = _svc.score_batch(batch_id=batch_id, rows=rows)
    mean_conf = sum(s.overall_confidence for s in result.scored) / len(result.scored) if result.scored else 0.0
    return ConfidenceScoreResponse(
        batch_id=batch_id, total=len(result.scored),
        green=result.green_count, yellow=result.yellow_count, red=result.red_count,
        mean_confidence=round(mean_conf, 4),
    )
