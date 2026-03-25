"""SM-B Document Ingestion API — file upload, source detection, batch lifecycle.

Endpoints:
    POST   /api/v1/imports/upload          — upload a statement file
    GET    /api/v1/imports                 — list all batches for the current user
    GET    /api/v1/imports/{batch_id}      — get batch status + metadata
    DELETE /api/v1/imports/{batch_id}      — cancel / rollback a batch
    POST   /api/v1/imports/{batch_id}/reprocess — re-trigger parsing
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field

from api.deps import CurrentUser, SettingsDep
from core.models.enums import BatchStatus, FileFormat, SourceType
from core.models.import_batch import ImportBatch
from modules.parser.detector import SourceDetector

router = APIRouter(prefix="/imports", tags=["Document Ingestion (SM-B)"])

_detector = SourceDetector()

# ── In-memory batch store (replace with DB in production) ─────────────────────
_batches: dict[str, ImportBatch] = {}


# ── Response schemas ──────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    batch_id: str
    status: str
    source_type: str | None
    source_type_inferred: bool
    filename: str
    format: str
    file_size_bytes: int
    is_encrypted: bool
    detection_confidence: float
    warnings: list[str]
    poll_url: str


class BatchSummary(BaseModel):
    batch_id: str
    filename: str
    source_type: str | None
    status: str
    format: str
    file_size_bytes: int
    txn_found: int
    parse_confidence: float
    created_at: datetime


class BatchListResponse(BaseModel):
    items: list[BatchSummary]
    total: int
    page: int
    page_size: int


class BatchDetailResponse(BatchSummary):
    detection_confidence: float
    is_encrypted: bool
    statement_from: str | None
    statement_to: str | None
    txn_new: int
    txn_duplicate: int
    error_message: str | None
    updated_at: datetime


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ext_to_format(filename: str) -> FileFormat:
    ext = filename.rsplit(".", 1)[-1].upper() if "." in filename else ""
    return {"PDF": FileFormat.PDF, "CSV": FileFormat.CSV, "XLS": FileFormat.XLS, "XLSX": FileFormat.XLSX}.get(ext, FileFormat.CSV)


def _batch_to_detail(b: ImportBatch) -> BatchDetailResponse:
    return BatchDetailResponse(
        batch_id=b.batch_id,
        filename=b.filename,
        source_type=b.source_type.value if b.source_type else None,
        status=b.status.value,
        format=b.format.value,
        file_size_bytes=getattr(b, "file_size_bytes", 0),
        txn_found=b.txn_found,
        parse_confidence=b.parse_confidence,
        detection_confidence=getattr(b, "detection_confidence", 0.0),
        is_encrypted=getattr(b, "is_encrypted", False),
        statement_from=b.statement_from,
        statement_to=b.statement_to,
        txn_new=b.txn_new,
        txn_duplicate=b.txn_duplicate,
        error_message=b.error_message,
        created_at=b.created_at,
        updated_at=b.updated_at,
    )


# ── POST /imports/upload ──────────────────────────────────────────────────────

@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a financial statement for parsing",
    description=(
        "Accepts PDF, CSV, XLS, or XLSX statement files. "
        "Performs source detection and creates an ImportBatch record. "
        "Returns 202 Accepted — parsing runs asynchronously. "
        "Poll GET /imports/{batch_id} for status."
    ),
    operation_id="uploadImport",
)
async def upload_import(
    user_id: CurrentUser,
    settings: SettingsDep,
    file: Annotated[UploadFile, File(description="Statement file (PDF/CSV/XLS/XLSX). Max 50 MB.")],
    account_id: Annotated[str, Form(description="Account UUID this statement belongs to")] = "",
    password: Annotated[str, Form(description="PDF password (never stored; used only for decryption)")] = "",
    source_type_hint: Annotated[str, Form(description="Override source detection (e.g. HDFC_BANK)")] = "",
    use_llm: Annotated[bool, Form(description="Enable LLM fallback for low-confidence pages")] = False,
    statement_from: Annotated[str, Form(description="Override statement start date (ISO 8601)")] = "",
    statement_to: Annotated[str, Form(description="Override statement end date (ISO 8601)")] = "",
) -> UploadResponse:
    # Size check
    file_bytes = await file.read()
    if len(file_bytes) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={"error": "FILE_TOO_LARGE", "message": f"Max upload size is {settings.max_upload_size_mb} MB."},
        )

    filename   = file.filename or "upload"
    fmt        = _ext_to_format(filename)
    file_hash  = hashlib.sha256(file_bytes).hexdigest()
    warnings: list[str] = []

    # Duplicate detection (same content already uploaded by this user)
    for existing in _batches.values():
        if getattr(existing, "user_id", None) == user_id and getattr(existing, "file_hash", None) == file_hash:
            warnings.append(f"Duplicate file detected. Existing batch: {existing.batch_id}")
            break

    # Source detection
    detection = _detector.detect(
        filename=filename,
        file_bytes=file_bytes,
        source_type_hint=source_type_hint or None,
    )
    if detection.confidence < 0.70:
        warnings.append(
            "Could not confidently detect source type. "
            "Set source_type_hint to override (e.g. HDFC_BANK, ZERODHA_TRADEBOOK)."
        )

    # Create ImportBatch
    batch = ImportBatch(
        user_id=user_id,
        account_id=account_id or str(uuid.uuid4()),
        filename=filename,
        file_hash=file_hash,
        source_type=detection.source_type,
        format=fmt,
        status=BatchStatus.DETECTING,
    )
    # Attach extra fields not in model (stored as object attrs for the stub)
    object.__setattr__(batch, "file_size_bytes", len(file_bytes))
    object.__setattr__(batch, "detection_confidence", detection.confidence)
    object.__setattr__(batch, "is_encrypted", False)
    object.__setattr__(batch, "file_bytes_cache", file_bytes)

    _batches[batch.batch_id] = batch

    return UploadResponse(
        batch_id=batch.batch_id,
        status=batch.status.value,
        source_type=batch.source_type.value if batch.source_type else None,
        source_type_inferred=not bool(source_type_hint),
        filename=filename,
        format=fmt.value,
        file_size_bytes=len(file_bytes),
        is_encrypted=False,
        detection_confidence=detection.confidence,
        warnings=warnings,
        poll_url=f"/api/v1/imports/{batch.batch_id}",
    )


# ── GET /imports ──────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=BatchListResponse,
    summary="List all import batches for the current user",
    operation_id="listImports",
)
def list_imports(
    user_id: CurrentUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> BatchListResponse:
    user_batches = [b for b in _batches.values() if getattr(b, "user_id", None) == user_id]
    if status_filter:
        user_batches = [b for b in user_batches if b.status.value == status_filter.upper()]

    user_batches.sort(key=lambda b: b.created_at, reverse=True)
    total = len(user_batches)
    start = (page - 1) * page_size
    page_items = user_batches[start : start + page_size]

    return BatchListResponse(
        items=[
            BatchSummary(
                batch_id=b.batch_id,
                filename=b.filename,
                source_type=b.source_type.value if b.source_type else None,
                status=b.status.value,
                format=b.format.value,
                file_size_bytes=getattr(b, "file_size_bytes", 0),
                txn_found=b.txn_found,
                parse_confidence=b.parse_confidence,
                created_at=b.created_at,
            )
            for b in page_items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


# ── GET /imports/{batch_id} ───────────────────────────────────────────────────

@router.get(
    "/{batch_id}",
    response_model=BatchDetailResponse,
    summary="Get import batch status and metadata",
    operation_id="getImport",
)
def get_import(batch_id: str, user_id: CurrentUser) -> BatchDetailResponse:
    batch = _batches.get(batch_id)
    if not batch or getattr(batch, "user_id", None) != user_id:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "Batch not found."})
    return _batch_to_detail(batch)


# ── DELETE /imports/{batch_id} ────────────────────────────────────────────────

@router.delete(
    "/{batch_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel or rollback an import batch",
    operation_id="deleteImport",
)
def delete_import(batch_id: str, user_id: CurrentUser) -> None:
    batch = _batches.get(batch_id)
    if not batch or getattr(batch, "user_id", None) != user_id:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "Batch not found."})
    terminal_states = {BatchStatus.COMPLETED, BatchStatus.CANCELLED}
    if batch.status in terminal_states:
        raise HTTPException(
            status_code=409,
            detail={"error": "INVALID_STATE", "message": f"Cannot cancel a batch in state {batch.status.value}."},
        )
    batch.status = BatchStatus.CANCELLED
