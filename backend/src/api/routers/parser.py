"""SM-C Parser Engine API — trigger parsing, poll status, retrieve rows.

Endpoints:
    POST   /api/v1/parser/parse/{batch_id}                     — trigger parsing
    GET    /api/v1/parser/parse/{batch_id}/status              — poll parse status
    GET    /api/v1/parser/parse/{batch_id}/rows                — paginated raw rows
    POST   /api/v1/parser/column-preview/{batch_id}            — detect column mapping
    POST   /api/v1/parser/column-mapping                       — save a mapping
    GET    /api/v1/parser/column-mapping/{mapping_id}          — retrieve saved mapping
    GET    /api/v1/parser/source-types                         — list supported source types
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from api.deps import CurrentUser
from api.routers.imports import _batches
from core.models.column_mapping import ColumnMapping, ColumnPreview
from core.models.enums import BatchStatus, SourceType
from core.models.raw_parsed_row import RawParsedRow
from modules.parser.chain import ExtractionChain
from modules.parser.registry import ParserRegistry

# ── Batch error cache (error_message stored here since ImportBatch field added) ─
_batch_errors: dict[str, str] = {}

router = APIRouter(prefix="/parser", tags=["Parser Engine (SM-C)"])

# ── In-memory column mapping store (replace with DB) ──────────────────────────
_column_mappings: dict[str, ColumnMapping] = {}

# ── Parsed rows cache (batch_id → list[RawParsedRow]) ─────────────────────────
_parsed_rows: dict[str, list[RawParsedRow]] = {}


# ── Schemas ───────────────────────────────────────────────────────────────────

class ParseTriggerRequest(BaseModel):
    """Optional overrides when triggering a parse."""
    source_type: str | None = None
    password: str | None = None          # PDF decryption password (never stored)
    use_llm: bool = False
    llm_provider_id: str | None = None
    extra_context: str | None = None


class ParseTriggerResponse(BaseModel):
    batch_id: str
    status: str
    source_type: str | None
    message: str
    poll_url: str


class ParseStatusResponse(BaseModel):
    batch_id: str
    status: str
    source_type: str | None
    txn_found: int
    txn_new: int
    txn_duplicate: int
    parse_confidence: float
    error_message: str | None


class RawRowOut(BaseModel):
    row_id: str
    batch_id: str
    row_number: int | None
    page_number: int | None
    raw_date: str
    raw_narration: str
    raw_debit: str | None
    raw_credit: str | None
    raw_balance: str | None
    raw_reference: str | None
    txn_type_hint: str
    row_confidence: float
    extra_fields: dict[str, Any]


class RawRowsResponse(BaseModel):
    items: list[RawRowOut]
    total: int
    page: int
    page_size: int
    batch_id: str


class ColumnPreviewRequest(BaseModel):
    """Headers-only preview for generic CSV mapping."""
    column_names: list[str]
    sample_rows: list[list[str]] = []


class ColumnMappingRequest(BaseModel):
    batch_id: str
    source_type: str
    date_col: str
    description_col: str
    debit_col: str | None = None
    credit_col: str | None = None
    amount_col: str | None = None
    balance_col: str | None = None
    date_format: str = "%d/%m/%Y"


class ColumnMappingResponse(BaseModel):
    mapping_id: str
    batch_id: str
    source_type: str
    date_col: str
    description_col: str
    debit_col: str | None
    credit_col: str | None
    amount_col: str | None
    balance_col: str | None
    date_format: str


class SourceTypeInfo(BaseModel):
    value: str
    label: str
    format: str


# ── POST /parser/parse/{batch_id} ─────────────────────────────────────────────

@router.post(
    "/parse/{batch_id}",
    response_model=ParseTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger parsing for an uploaded batch",
    operation_id="triggerParse",
)
def trigger_parse(
    batch_id: str,
    user_id: CurrentUser,
    body: ParseTriggerRequest | None = None,
) -> ParseTriggerResponse:
    batch = _batches.get(batch_id)
    if not batch or getattr(batch, "user_id", None) != user_id:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "Batch not found."})

    runnable_states = {
        BatchStatus.DETECTING, BatchStatus.QUEUED,
        BatchStatus.PARSE_FAILED, BatchStatus.PARSE_COMPLETE,
    }
    if batch.status not in runnable_states:
        raise HTTPException(
            status_code=409,
            detail={"error": "INVALID_STATE", "message": f"Batch is in state {batch.status.value}; cannot re-parse."},
        )

    batch.status = BatchStatus.PARSING

    # Apply overrides
    if body and body.source_type:
        try:
            batch.source_type = SourceType(body.source_type.upper())
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail={"error": "INVALID_SOURCE_TYPE", "message": f"Unknown source type: {body.source_type}"},
            )

    if batch.source_type is None:
        batch.status = BatchStatus.FAILED
        batch.error_message = "source_type is unknown; set source_type in the request body to override."
        raise HTTPException(
            status_code=422,
            detail={"error": "UNKNOWN_SOURCE_TYPE", "message": batch.error_message},
        )

    # Run synchronous extraction (async workers can be bolted on later)
    file_bytes: bytes = getattr(batch, "file_bytes_cache", b"")

    # Decrypt password-protected PDF if a password was supplied
    if body and body.password:
        try:
            from core.utils.pdf_utils import is_pdf_encrypted, decrypt_pdf_bytes  # noqa: PLC0415
            if is_pdf_encrypted(file_bytes):
                file_bytes = decrypt_pdf_bytes(file_bytes, body.password)
        except ValueError as exc:
            if "WRONG_PASSWORD" in str(exc):
                raise HTTPException(
                    status_code=422,
                    detail={"error": "WRONG_PASSWORD", "message": "Incorrect PDF password."},
                )
            raise HTTPException(
                status_code=422,
                detail={"error": "DECRYPT_FAILED", "message": str(exc)},
            ) from exc

    # Resolve LLM provider for vision fallback (scanned / image-only PDFs)
    _parse_llm = None
    if body and body.use_llm:
        try:
            from commands._helpers import _get_db_session as _p_db, _resolve_llm_provider as _p_llm  # noqa: PLC0415
            _p_sess = _p_db()
            _parse_llm = _p_llm(_p_sess, user_id, body.llm_provider_id or None)
            _p_sess.close()
        except Exception:
            pass

    try:
        registry = ParserRegistry.default()
        parser = registry.get(batch.source_type)
        if parser is None:
            msg = f"No parser registered for source type: {batch.source_type.value}"
            batch.status = BatchStatus.PARSE_FAILED
            batch.error_message = msg
            raise HTTPException(status_code=422, detail={"error": "NO_PARSER", "message": msg})
        chain = ExtractionChain(parser, batch_id, file_bytes)
        result = chain.run(llm_provider=_parse_llm)
        _parsed_rows[batch_id] = result.rows
        batch.txn_found        = len(result.rows)
        batch.txn_new          = batch.txn_found
        batch.parse_confidence = result.metadata.overall_confidence
        batch.status           = BatchStatus.PARSE_COMPLETE
        batch.error_message    = None
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover
        batch.status        = BatchStatus.PARSE_FAILED
        batch.error_message = str(exc)
        raise HTTPException(status_code=500, detail={"error": "PARSE_FAILED", "message": str(exc)}) from exc

    return ParseTriggerResponse(
        batch_id=batch_id,
        status=batch.status.value,
        source_type=batch.source_type.value,
        message=f"Parsed {batch.txn_found} transactions.",
        poll_url=f"/api/v1/parser/parse/{batch_id}/status",
    )


# ── GET /parser/parse/{batch_id}/status ──────────────────────────────────────

@router.get(
    "/parse/{batch_id}/status",
    response_model=ParseStatusResponse,
    summary="Poll parse status for a batch",
    operation_id="getParseStatus",
)
def get_parse_status(batch_id: str, user_id: CurrentUser) -> ParseStatusResponse:
    batch = _batches.get(batch_id)
    if not batch or getattr(batch, "user_id", None) != user_id:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "Batch not found."})
    return ParseStatusResponse(
        batch_id=batch_id,
        status=batch.status.value,
        source_type=batch.source_type.value if batch.source_type else None,
        txn_found=batch.txn_found,
        txn_new=batch.txn_new,
        txn_duplicate=batch.txn_duplicate,
        parse_confidence=batch.parse_confidence,
        error_message=batch.error_message,
    )


# ── GET /parser/parse/{batch_id}/rows ─────────────────────────────────────────

@router.get(
    "/parse/{batch_id}/rows",
    response_model=RawRowsResponse,
    summary="Retrieve paginated raw parsed rows for a batch",
    operation_id="getParseRows",
)
def get_parse_rows(
    batch_id: str,
    user_id: CurrentUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
    min_confidence: Annotated[float, Query(ge=0.0, le=1.0)] = 0.0,
) -> RawRowsResponse:
    batch = _batches.get(batch_id)
    if not batch or getattr(batch, "user_id", None) != user_id:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "Batch not found."})

    rows = _parsed_rows.get(batch_id, [])
    if min_confidence > 0.0:
        rows = [r for r in rows if r.confidence >= min_confidence]

    total = len(rows)
    start = (page - 1) * page_size
    page_rows = rows[start : start + page_size]

    return RawRowsResponse(
        items=[
            RawRowOut(
                row_id=r.row_id,
                batch_id=r.batch_id,
                row_number=r.row_number,
                page_number=r.page_number,
                raw_date=r.raw_date,
                raw_narration=r.raw_narration,
                raw_debit=r.raw_debit,
                raw_credit=r.raw_credit,
                raw_balance=r.raw_balance,
                raw_reference=r.raw_reference,
                txn_type_hint=r.txn_type_hint.value,
                row_confidence=r.row_confidence,
                extra_fields=r.extra_fields,
            )
            for r in page_rows
        ],
        total=total,
        page=page,
        page_size=page_size,
        batch_id=batch_id,
    )


# ── POST /parser/column-preview/{batch_id} ────────────────────────────────────

@router.post(
    "/column-preview/{batch_id}",
    response_model=ColumnPreview,
    summary="Auto-detect column mapping for a generic CSV file",
    operation_id="getColumnPreview",
)
def get_column_preview(
    batch_id: str,
    user_id: CurrentUser,
    body: ColumnPreviewRequest,
) -> ColumnPreview:
    batch = _batches.get(batch_id)
    if not batch or getattr(batch, "user_id", None) != user_id:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "Batch not found."})

    # Attempt heuristic mapping from header names
    headers_lower = [h.lower().strip() for h in body.column_names]

    def _find(*candidates: str) -> str | None:
        for c in candidates:
            for i, h in enumerate(headers_lower):
                if c in h:
                    return body.column_names[i]
        return None

    return ColumnPreview(
        column_names=body.column_names,
        suggested_date_col=_find("date"),
        suggested_description_col=_find("narration", "description", "particulars", "remark"),
        suggested_debit_col=_find("debit", "withdrawal", "dr"),
        suggested_credit_col=_find("credit", "deposit", "cr"),
        suggested_amount_col=_find("amount"),
        suggested_balance_col=_find("balance"),
    )


# ── POST /parser/column-mapping ───────────────────────────────────────────────

@router.post(
    "/column-mapping",
    response_model=ColumnMappingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save a confirmed column mapping",
    operation_id="saveColumnMapping",
)
def save_column_mapping(body: ColumnMappingRequest, user_id: CurrentUser) -> ColumnMappingResponse:
    mapping_id = str(uuid.uuid4())
    mapping = ColumnMapping(
        mapping_id=mapping_id,
        batch_id=body.batch_id,
        source_type=body.source_type,
        date_col=body.date_col,
        description_col=body.description_col,
        debit_col=body.debit_col,
        credit_col=body.credit_col,
        amount_col=body.amount_col,
        balance_col=body.balance_col,
        date_format=body.date_format,
    )
    _column_mappings[mapping_id] = mapping
    return ColumnMappingResponse(**mapping.model_dump())


# ── GET /parser/column-mapping/{mapping_id} ───────────────────────────────────

@router.get(
    "/column-mapping/{mapping_id}",
    response_model=ColumnMappingResponse,
    summary="Retrieve a saved column mapping",
    operation_id="getColumnMapping",
)
def get_column_mapping(mapping_id: str, user_id: CurrentUser) -> ColumnMappingResponse:
    mapping = _column_mappings.get(mapping_id)
    if mapping is None:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "Column mapping not found."})
    return ColumnMappingResponse(**mapping.model_dump())


# ── GET /parser/source-types ──────────────────────────────────────────────────

@router.get(
    "/source-types",
    response_model=list[SourceTypeInfo],
    summary="List all supported source types and their expected file formats",
    operation_id="listSourceTypes",
)
def list_source_types() -> list[SourceTypeInfo]:
    from core.models.enums import PDF_SOURCE_TYPES, CSV_SOURCE_TYPES
    items: list[SourceTypeInfo] = []
    for s in SourceType:
        fmt = "PDF" if s in PDF_SOURCE_TYPES else "CSV/XLS"
        items.append(SourceTypeInfo(value=s.value, label=s.value.replace("_", " ").title(), format=fmt))
    return items
