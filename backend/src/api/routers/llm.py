"""SM-D LLM Processing API — provider management, extraction jobs.

Endpoints:
    GET    /api/v1/llm/providers                         — list configured providers
    POST   /api/v1/llm/providers                         — register a new provider
    GET    /api/v1/llm/providers/{provider_id}           — get provider detail
    PATCH  /api/v1/llm/providers/{provider_id}           — update provider
    DELETE /api/v1/llm/providers/{provider_id}           — remove provider
    POST   /api/v1/llm/providers/{provider_id}/test      — test provider connectivity
    POST   /api/v1/llm/extract/text                      — text extraction for a batch
    POST   /api/v1/llm/extract/vision                    — vision extraction for a batch
    POST   /api/v1/llm/extract/file                      — upload file + extract via Files API
    GET    /api/v1/llm/jobs/{batch_id}                   — list LLM jobs for a batch
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import CurrentUserPayload, TenantDBSession, SettingsDep
from db.models.system import LlmProvider
from modules.llm.base import (
    FileExtractionRequest,
    TextExtractionRequest,
    VisionExtractionRequest,
)

router = APIRouter(prefix="/llm", tags=["LLM Processing (SM-D)"])


# ── In-memory job records (ephemeral — not worth persisting) ──────────────────

@dataclass
class _StoredJob:
    job_id: str
    batch_id: str
    provider_name: str
    model_used: str
    method: str
    rows_extracted: int
    confidence: float
    tokens_used: int
    processing_ms: float
    created_at: datetime = field(default_factory=datetime.utcnow)


_jobs: dict[str, list[_StoredJob]] = {}


# ── Schemas ───────────────────────────────────────────────────────────────────

class ProviderRegisterRequest(BaseModel):
    provider_name: str = Field(..., description="gemini | openai | anthropic")
    api_key: str = Field(..., description="API key (never returned in responses)")
    display_name: str = ""
    is_default: bool = False


class ProviderResponse(BaseModel):
    provider_id: str
    provider_name: str
    display_name: str
    is_default: bool


class TestConnectionResponse(BaseModel):
    ok: bool
    provider_id: str
    latency_ms: float | None
    error: str | None


class TextExtractionAPIRequest(BaseModel):
    batch_id: str
    provider_id: str | None = None
    page_text: str = Field(..., description="Plain text to extract transactions from")
    source_type: str = "GENERIC_CSV"
    extra_context: str = ""


class VisionExtractionAPIRequest(BaseModel):
    batch_id: str
    provider_id: str | None = None
    page_images_b64: list[str] = Field(..., description="Base64-encoded PNG images, one per page")
    source_type: str = "GENERIC_CSV"
    extra_context: str = ""


class ExtractionResponse(BaseModel):
    job_id: str
    batch_id: str
    provider_name: str
    model_used: str
    method: str
    rows_extracted: int
    confidence: float
    tokens_used: int
    processing_ms: float
    raw_response: str = ""


class JobSummary(BaseModel):
    job_id: str
    batch_id: str
    provider_name: str
    model_used: str
    method: str
    rows_extracted: int
    confidence: float
    created_at: datetime


class ProviderUpdateRequest(BaseModel):
    display_name: str | None = None
    api_key: str | None = None
    is_default: bool | None = None


# ── DB helpers ────────────────────────────────────────────────────────────────

async def _get_provider_or_404(session: AsyncSession, provider_id: str) -> LlmProvider:
    row = await session.scalar(
        select(LlmProvider).where(LlmProvider.provider_id == provider_id)
    )
    if row is None:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "Provider not found."})
    return row


async def _resolve_provider(provider_id: str | None, settings, session: AsyncSession):
    """Return (display_name, provider_instance) for the given provider_id or env default."""
    from modules.llm.providers.gemini import GeminiProvider  # noqa: PLC0415

    stored = None
    if provider_id:
        stored = await session.scalar(
            select(LlmProvider).where(LlmProvider.provider_id == provider_id)
        )
        if stored is None:
            raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "Provider not found."})

    if stored is None:
        # Auto-detect: prefer is_default
        stored = await session.scalar(
            select(LlmProvider)
            .where(LlmProvider.is_default == True)  # noqa: E712
            .limit(1)
        )
    if stored is None:
        stored = await session.scalar(select(LlmProvider).limit(1))

    name    = stored.provider_name if stored else settings.default_llm_provider.lower()
    api_key = stored.api_key if stored else {
        "gemini": settings.gemini_api_key,
    }.get(name, "")

    if name == "gemini":
        return name, GeminiProvider(api_key=api_key)
    raise HTTPException(status_code=422, detail={"error": "UNKNOWN_PROVIDER", "message": f"'{name}' is not supported."})


def _to_response(p: LlmProvider) -> ProviderResponse:
    return ProviderResponse(
        provider_id=p.provider_id,
        provider_name=p.provider_name,
        display_name=p.display_name,
        is_default=p.is_default,
    )


# ── GET /llm/providers ────────────────────────────────────────────────────────

@router.get(
    "/providers",
    response_model=list[ProviderResponse],
    summary="List registered LLM providers for the current tenant",
    operation_id="listLLMProviders",
)
async def list_providers(auth: CurrentUserPayload, session: TenantDBSession) -> list[ProviderResponse]:
    result = await session.scalars(select(LlmProvider))
    return [_to_response(p) for p in result.all()]


# ── POST /llm/providers ───────────────────────────────────────────────────────

@router.post(
    "/providers",
    response_model=ProviderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new LLM provider",
    operation_id="registerLLMProvider",
)
async def register_provider(body: ProviderRegisterRequest, auth: CurrentUserPayload, session: TenantDBSession) -> ProviderResponse:
    import uuid as _uuid
    SUPPORTED = {"gemini", "openai", "anthropic"}
    name_lower = body.provider_name.lower()
    if name_lower not in SUPPORTED:
        raise HTTPException(status_code=422, detail={"error": "UNSUPPORTED_PROVIDER", "message": f"Supported: {sorted(SUPPORTED)}"})

    is_first = await session.scalar(select(LlmProvider).limit(1)) is None

    if body.is_default or is_first:
        await session.execute(sa_update(LlmProvider).values(is_default=False))

    row = LlmProvider(
        tenant_id=uuid.UUID(auth.tenant_id),
        provider_id=str(_uuid.uuid4()),
        provider_name=name_lower,
        api_key=body.api_key,
        display_name=body.display_name or body.provider_name,
        is_default=body.is_default or is_first,
    )
    session.add(row)
    await session.flush()
    return _to_response(row)


# ── GET /llm/providers/{provider_id} ─────────────────────────────────────────

@router.get(
    "/providers/{provider_id}",
    response_model=ProviderResponse,
    summary="Get LLM provider detail",
    operation_id="getLLMProvider",
)
async def get_provider(provider_id: str, auth: CurrentUserPayload, session: TenantDBSession) -> ProviderResponse:
    return _to_response(await _get_provider_or_404(session, provider_id))


# ── PATCH /llm/providers/{provider_id} ───────────────────────────────────────

@router.patch(
    "/providers/{provider_id}",
    response_model=ProviderResponse,
    summary="Update display name, API key for an existing provider",
    operation_id="updateLLMProvider",
)
async def update_provider(provider_id: str, body: ProviderUpdateRequest, auth: CurrentUserPayload, session: TenantDBSession) -> ProviderResponse:
    p = await _get_provider_or_404(session, provider_id)
    if body.display_name is not None:
        p.display_name = body.display_name
    if body.api_key is not None and body.api_key.strip():
        p.api_key = body.api_key.strip()
    if body.is_default is True:
        await session.execute(sa_update(LlmProvider).values(is_default=False))
        p.is_default = True
    await session.flush()
    return _to_response(p)


# ── DELETE /llm/providers/{provider_id} ───────────────────────────────────────

@router.delete(
    "/providers/{provider_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a registered LLM provider",
    operation_id="deleteLLMProvider",
)
async def delete_provider(provider_id: str, auth: CurrentUserPayload, session: TenantDBSession) -> None:
    p = await _get_provider_or_404(session, provider_id)
    await session.delete(p)


# ── POST /llm/providers/{provider_id}/test ────────────────────────────────────

@router.post(
    "/providers/{provider_id}/test",
    response_model=TestConnectionResponse,
    summary="Test connectivity and API key validity",
    operation_id="testLLMProvider",
)
async def test_provider(provider_id: str, auth: CurrentUserPayload, session: TenantDBSession, settings: SettingsDep) -> TestConnectionResponse:
    import time
    name, instance = await _resolve_provider(provider_id, settings, session)
    t0 = time.perf_counter()
    try:
        instance.test_connection()
        return TestConnectionResponse(ok=True, provider_id=provider_id,
                                      latency_ms=round((time.perf_counter() - t0) * 1000, 1), error=None)
    except Exception as exc:
        return TestConnectionResponse(ok=False, provider_id=provider_id, latency_ms=None, error=str(exc))


# ── POST /llm/extract/text ────────────────────────────────────────────────────

@router.post(
    "/extract/text",
    response_model=ExtractionResponse,
    summary="Extract transactions from plain-text content using LLM",
    operation_id="extractText",
)
async def extract_text_endpoint(body: TextExtractionAPIRequest, auth: CurrentUserPayload, session: TenantDBSession, settings: SettingsDep) -> ExtractionResponse:
    import time
    from core.models.enums import SourceType  # noqa: PLC0415

    name, provider = await _resolve_provider(body.provider_id, settings, session)
    try:
        source_type = SourceType(body.source_type.upper())
    except ValueError:
        raise HTTPException(status_code=422, detail={"error": "INVALID_SOURCE_TYPE"})

    req = TextExtractionRequest(
        batch_id=body.batch_id,
        source_type=source_type.value,
        partial_text=body.page_text,
        extra_context={"extra": body.extra_context} if body.extra_context else {},
    )
    t0 = time.perf_counter()
    llm_resp = provider.extract_text(req)
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)

    job = _StoredJob(
        job_id=str(uuid.uuid4()), batch_id=body.batch_id, provider_name=name,
        model_used=llm_resp.model_used, method="text",
        rows_extracted=len(llm_resp.rows), confidence=llm_resp.overall_confidence,
        tokens_used=llm_resp.input_tokens + llm_resp.output_tokens, processing_ms=elapsed_ms,
    )
    _jobs.setdefault(body.batch_id, []).append(job)
    return ExtractionResponse(
        job_id=job.job_id, batch_id=body.batch_id, provider_name=name,
        model_used=llm_resp.model_used, method="text",
        rows_extracted=len(llm_resp.rows), confidence=llm_resp.overall_confidence,
        tokens_used=job.tokens_used, processing_ms=elapsed_ms,
        raw_response=llm_resp.raw_response,
    )


# ── POST /llm/extract/vision ──────────────────────────────────────────────────

@router.post(
    "/extract/vision",
    response_model=ExtractionResponse,
    summary="Extract transactions from page images using LLM vision",
    operation_id="extractVision",
)
async def extract_vision_endpoint(body: VisionExtractionAPIRequest, auth: CurrentUserPayload, session: TenantDBSession, settings: SettingsDep) -> ExtractionResponse:
    import base64, time  # noqa: E401
    from core.models.enums import SourceType  # noqa: PLC0415

    name, provider = await _resolve_provider(body.provider_id, settings, session)
    try:
        source_type = SourceType(body.source_type.upper())
    except ValueError:
        raise HTTPException(status_code=422, detail={"error": "INVALID_SOURCE_TYPE"})

    req = VisionExtractionRequest(
        batch_id=body.batch_id,
        source_type=source_type.value,
        page_images=[base64.b64decode(b64) for b64 in body.page_images_b64],
        extra_context={"extra": body.extra_context} if body.extra_context else {},
    )
    t0 = time.perf_counter()
    llm_resp = provider.extract_vision(req)
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)

    job = _StoredJob(
        job_id=str(uuid.uuid4()), batch_id=body.batch_id, provider_name=name,
        model_used=llm_resp.model_used, method="vision",
        rows_extracted=len(llm_resp.rows), confidence=llm_resp.overall_confidence,
        tokens_used=llm_resp.input_tokens + llm_resp.output_tokens, processing_ms=elapsed_ms,
    )
    _jobs.setdefault(body.batch_id, []).append(job)
    return ExtractionResponse(
        job_id=job.job_id, batch_id=body.batch_id, provider_name=name,
        model_used=llm_resp.model_used, method="vision",
        rows_extracted=len(llm_resp.rows), confidence=llm_resp.overall_confidence,
        tokens_used=job.tokens_used, processing_ms=elapsed_ms,
    )


# ── POST /llm/extract/file ────────────────────────────────────────────────────

@router.post(
    "/extract/file",
    response_model=ExtractionResponse,
    summary="Upload file to LLM Files API and extract transactions",
    operation_id="extractFile",
)
async def extract_file_endpoint(
    auth: CurrentUserPayload,
    session: TenantDBSession,
    settings: SettingsDep,
    file: Annotated[UploadFile, File()],
    batch_id: Annotated[str, Form()],
    source_type: Annotated[str, Form()] = "GENERIC_CSV",
    extra_context: Annotated[str, Form()] = "",
    provider_id: Annotated[str, Form()] = "",
) -> ExtractionResponse:
    import time
    from core.models.enums import SourceType  # noqa: PLC0415

    name, provider = await _resolve_provider(provider_id or None, settings, session)
    try:
        st = SourceType(source_type.upper())
    except ValueError:
        raise HTTPException(status_code=422, detail={"error": "INVALID_SOURCE_TYPE"})

    file_bytes = await file.read()
    req = FileExtractionRequest(
        batch_id=batch_id, source_type=st.value, file_bytes=file_bytes,
        filename=file.filename or "upload", mime_type=file.content_type or "application/pdf",
        extra_context={"extra": extra_context} if extra_context else {},
    )

    t0 = time.perf_counter()
    uploaded = provider.upload_file(req)
    llm_resp  = provider.extract_with_file(
        file_id=uploaded.file_id, batch_id=batch_id, source_type=st.value,
        extra_context={"extra": extra_context} if extra_context else {},
    )
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)

    try:
        provider.delete_file(uploaded.file_id)
    except Exception:
        pass

    job = _StoredJob(
        job_id=str(uuid.uuid4()), batch_id=batch_id, provider_name=name,
        model_used=llm_resp.model_used, method="file",
        rows_extracted=len(llm_resp.rows), confidence=llm_resp.overall_confidence,
        tokens_used=llm_resp.input_tokens + llm_resp.output_tokens, processing_ms=elapsed_ms,
    )
    _jobs.setdefault(batch_id, []).append(job)
    return ExtractionResponse(
        job_id=job.job_id, batch_id=batch_id, provider_name=name,
        model_used=llm_resp.model_used, method="file",
        rows_extracted=len(llm_resp.rows), confidence=llm_resp.overall_confidence,
        tokens_used=job.tokens_used, processing_ms=elapsed_ms,
    )


# ── GET /llm/jobs/{batch_id} ──────────────────────────────────────────────────

@router.get(
    "/jobs/{batch_id}",
    response_model=list[JobSummary],
    summary="List LLM extraction jobs for a batch",
    operation_id="listLLMJobs",
)
async def list_jobs(batch_id: str, auth: CurrentUserPayload) -> list[JobSummary]:
    return [
        JobSummary(
            job_id=j.job_id, batch_id=j.batch_id, provider_name=j.provider_name,
            model_used=j.model_used, method=j.method, rows_extracted=j.rows_extracted,
            confidence=j.confidence, created_at=j.created_at,
        )
        for j in _jobs.get(batch_id, [])
    ]
