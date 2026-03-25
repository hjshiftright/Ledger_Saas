"""SM-D LLM Processing API — provider management, extraction jobs.

Endpoints:
    GET    /api/v1/llm/providers                         — list configured providers
    POST   /api/v1/llm/providers                         — register a new provider
    GET    /api/v1/llm/providers/{provider_id}           — get provider detail
    DELETE /api/v1/llm/providers/{provider_id}           — remove provider
    POST   /api/v1/llm/providers/{provider_id}/test      — test provider connectivity
    POST   /api/v1/llm/extract/text                      — text extraction for a batch
    POST   /api/v1/llm/extract/vision                    — vision extraction for a batch
    POST   /api/v1/llm/extract/file                      — upload file + extract via Files API
    GET    /api/v1/llm/jobs/{batch_id}                   — list LLM jobs for a batch

NOTE: Provider records and job records are stored in plain in-memory dataclasses.
The canonical LLM domain models (src/modules/llm/models.py) are DB-persistence models
with different field contracts; we use lightweight dataclasses here for the stub store.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.deps import CurrentUser, DBSession, SettingsDep
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
    method: str                 # text | vision | file
    rows_extracted: int
    confidence: float
    tokens_used: int
    processing_ms: float
    created_at: datetime = field(default_factory=datetime.utcnow)


# Keyed by batch_id → [_StoredJob]
_jobs: dict[str, list[_StoredJob]] = {}


# ── Schemas ───────────────────────────────────────────────────────────────────

class ProviderRegisterRequest(BaseModel):
    provider_name: str = Field(..., description="gemini | openai | anthropic")
    api_key: str = Field(..., description="API key (never returned in responses)")
    display_name: str = ""
    text_model: str = ""
    vision_model: str = ""
    is_default: bool = False


class ProviderResponse(BaseModel):
    provider_id: str
    provider_name: str
    display_name: str
    text_model: str
    vision_model: str
    is_active: bool
    is_default: bool
    created_at: datetime


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


# ── DB helpers ────────────────────────────────────────────────────────────────

def _get_provider_or_404(session: Session, user_id: str, provider_id: str):
    from db.models.system import LlmProvider  # noqa: PLC0415
    from sqlalchemy import select  # noqa: PLC0415
    row = session.execute(
        select(LlmProvider).where(
            LlmProvider.provider_id == provider_id,
            LlmProvider.user_id == user_id,
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "Provider not found."})
    return row


def _resolve_provider(user_id: str, provider_id: str | None, settings, session: Session):
    """Return (display_name, provider_instance) for the given provider_id or env default."""
    from modules.llm.providers.gemini import GeminiProvider  # noqa: PLC0415
    from modules.llm.providers.openai_provider import OpenAIProvider  # noqa: PLC0415
    from modules.llm.providers.anthropic_provider import AnthropicProvider  # noqa: PLC0415
    from db.models.system import LlmProvider  # noqa: PLC0415
    from sqlalchemy import select  # noqa: PLC0415

    stored = None
    if provider_id:
        stored = session.execute(
            select(LlmProvider).where(
                LlmProvider.provider_id == provider_id,
                LlmProvider.user_id == user_id,
            )
        ).scalar_one_or_none()
        if stored is None:
            raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "Provider not found."})

    name     = stored.provider_name if stored else settings.default_llm_provider.lower()
    api_key  = stored.api_key if stored else {
        "gemini": settings.gemini_api_key, "openai": settings.openai_api_key,
        "anthropic": settings.anthropic_api_key,
    }.get(name, "")
    text_m   = stored.text_model if stored else {
        "gemini": settings.gemini_text_model, "openai": settings.openai_text_model,
        "anthropic": settings.anthropic_text_model,
    }.get(name, "")
    vision_m = stored.vision_model if stored else {
        "gemini": settings.gemini_vision_model, "openai": settings.openai_vision_model,
        "anthropic": settings.anthropic_vision_model,
    }.get(name, "")

    factories = {
        "gemini":    lambda: GeminiProvider(api_key=api_key, text_model=text_m, vision_model=vision_m),
        "openai":    lambda: OpenAIProvider(api_key=api_key, text_model=text_m, vision_model=vision_m),
        "anthropic": lambda: AnthropicProvider(api_key=api_key, text_model=text_m, vision_model=vision_m),
    }
    factory = factories.get(name)
    if factory is None:
        raise HTTPException(status_code=422, detail={"error": "UNKNOWN_PROVIDER", "message": f"'{name}' is not supported."})
    return name, factory()


def _to_response(p) -> ProviderResponse:
    return ProviderResponse(
        provider_id=p.provider_id, provider_name=p.provider_name,
        display_name=p.display_name, text_model=p.text_model,
        vision_model=p.vision_model, is_active=p.is_active,
        is_default=p.is_default, created_at=p.created_at,
    )


# ── GET /llm/providers ────────────────────────────────────────────────────────

@router.get(
    "/providers",
    response_model=list[ProviderResponse],
    summary="List registered LLM providers for the current user",
    operation_id="listLLMProviders",
)
def list_providers(user_id: CurrentUser, session: DBSession) -> list[ProviderResponse]:
    from db.models.system import LlmProvider  # noqa: PLC0415
    from sqlalchemy import select  # noqa: PLC0415
    rows = session.execute(
        select(LlmProvider).where(LlmProvider.user_id == user_id)
    ).scalars().all()
    return [_to_response(p) for p in rows]


# ── POST /llm/providers ───────────────────────────────────────────────────────

@router.post(
    "/providers",
    response_model=ProviderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new LLM provider",
    operation_id="registerLLMProvider",
)
def register_provider(body: ProviderRegisterRequest, user_id: CurrentUser, session: DBSession, settings: SettingsDep) -> ProviderResponse:
    from db.models.system import LlmProvider  # noqa: PLC0415
    from sqlalchemy import select, update  # noqa: PLC0415

    SUPPORTED = {"gemini", "openai", "anthropic"}
    name_lower = body.provider_name.lower()
    if name_lower not in SUPPORTED:
        raise HTTPException(status_code=422, detail={"error": "UNSUPPORTED_PROVIDER", "message": f"Supported: {sorted(SUPPORTED)}"})

    is_first = session.execute(
        select(LlmProvider).where(LlmProvider.user_id == user_id)
    ).first() is None

    if body.is_default or is_first:
        session.execute(
            update(LlmProvider)
            .where(LlmProvider.user_id == user_id)
            .values(is_default=False)
        )

    text_model   = body.text_model   or getattr(settings, f"{name_lower}_text_model",   "")
    vision_model = body.vision_model or getattr(settings, f"{name_lower}_vision_model", "")

    row = LlmProvider(
        provider_id=str(uuid.uuid4()),
        user_id=user_id,
        provider_name=name_lower,
        api_key=body.api_key,
        display_name=body.display_name or body.provider_name,
        text_model=text_model,
        vision_model=vision_model,
        is_default=body.is_default or is_first,
    )
    session.add(row)
    session.flush()
    return _to_response(row)


# ── GET /llm/providers/{provider_id} ─────────────────────────────────────────

@router.get(
    "/providers/{provider_id}",
    response_model=ProviderResponse,
    summary="Get LLM provider detail",
    operation_id="getLLMProvider",
)
def get_provider(provider_id: str, user_id: CurrentUser, session: DBSession) -> ProviderResponse:
    return _to_response(_get_provider_or_404(session, user_id, provider_id))


# ── PATCH /llm/providers/{provider_id} ───────────────────────────────────────

class ProviderUpdateRequest(BaseModel):
    display_name: str | None = None
    api_key: str | None = None          # omit to keep existing key
    text_model: str | None = None
    vision_model: str | None = None
    is_default: bool | None = None


@router.patch(
    "/providers/{provider_id}",
    response_model=ProviderResponse,
    summary="Update display name, API key or models for an existing provider",
    operation_id="updateLLMProvider",
)
def update_provider(provider_id: str, body: ProviderUpdateRequest, user_id: CurrentUser, session: DBSession) -> ProviderResponse:
    from sqlalchemy import update as sa_update  # noqa: PLC0415
    from db.models.system import LlmProvider  # noqa: PLC0415

    p = _get_provider_or_404(session, user_id, provider_id)
    if body.display_name is not None:
        p.display_name = body.display_name
    if body.api_key is not None and body.api_key.strip():
        p.api_key = body.api_key.strip()
    if body.text_model is not None:
        p.text_model = body.text_model
    if body.vision_model is not None:
        p.vision_model = body.vision_model
    if body.is_default is True:
        session.execute(
            sa_update(LlmProvider)
            .where(LlmProvider.user_id == user_id)
            .values(is_default=False)
        )
        p.is_default = True
    session.flush()
    return _to_response(p)


# ── DELETE /llm/providers/{provider_id} ───────────────────────────────────────

@router.delete(
    "/providers/{provider_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a registered LLM provider",
    operation_id="deleteLLMProvider",
)
def delete_provider(provider_id: str, user_id: CurrentUser, session: DBSession) -> None:
    p = _get_provider_or_404(session, user_id, provider_id)
    session.delete(p)


# ── POST /llm/providers/{provider_id}/test ────────────────────────────────────

@router.post(
    "/providers/{provider_id}/test",
    response_model=TestConnectionResponse,
    summary="Test connectivity and API key validity",
    operation_id="testLLMProvider",
)
def test_provider(provider_id: str, user_id: CurrentUser, session: DBSession, settings: SettingsDep) -> TestConnectionResponse:
    import time
    name, instance = _resolve_provider(user_id, provider_id, settings, session)
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
def extract_text_endpoint(body: TextExtractionAPIRequest, user_id: CurrentUser, session: DBSession, settings: SettingsDep) -> ExtractionResponse:
    import time
    from core.models.enums import SourceType

    name, provider = _resolve_provider(user_id, body.provider_id, settings, session)
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
def extract_vision_endpoint(body: VisionExtractionAPIRequest, user_id: CurrentUser, session: DBSession, settings: SettingsDep) -> ExtractionResponse:
    import base64, time
    from core.models.enums import SourceType

    name, provider = _resolve_provider(user_id, body.provider_id, settings, session)
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
    description=(
        "Uploads the PDF/CSV directly to the LLM provider's Files API, then sends only "
        "the file handle in the extraction prompt — avoids base64 re-encoding for large files."
    ),
    operation_id="extractFile",
)
async def extract_file_endpoint(
    user_id: CurrentUser,
    session: DBSession,
    settings: SettingsDep,
    file: Annotated[UploadFile, File()],
    batch_id: Annotated[str, Form()],
    source_type: Annotated[str, Form()] = "GENERIC_CSV",
    extra_context: Annotated[str, Form()] = "",
    provider_id: Annotated[str, Form()] = "",
) -> ExtractionResponse:
    import time
    from core.models.enums import SourceType

    name, provider = _resolve_provider(user_id, provider_id or None, settings, session)
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
    except Exception:  # pragma: no cover
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
def list_jobs(batch_id: str, user_id: CurrentUser) -> list[JobSummary]:
    return [
        JobSummary(
            job_id=j.job_id, batch_id=j.batch_id, provider_name=j.provider_name,
            model_used=j.model_used, method=j.method, rows_extracted=j.rows_extracted,
            confidence=j.confidence, created_at=j.created_at,
        )
        for j in _jobs.get(batch_id, [])
    ]
