"""Import pipeline REST API.

User-facing endpoints (3 groups):

  Upload + parse:
    POST   /api/v1/pipeline/parse                    — upload file, detect source, parse (\u00b1LLM extraction)
    GET    /api/v1/pipeline/parse/status/{batch_id}  — poll parse status
    GET    /api/v1/pipeline/parse/{batch_id}/rows    — paginated raw rows

  Smart-process (normalize \u2192 dedup \u2192 categorize \u2192 score \u2192 propose):
    POST   /api/v1/pipeline/process/{batch_id}       — run full AI pipeline; use_llm=true for LLM assist

  Review + commit (handled by proposals router):
    GET    /api/v1/proposals/{batch_id}
    POST   /api/v1/proposals/{batch_id}/approve
    POST   /api/v1/proposals/{batch_id}/commit
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel

from api.deps import CurrentUser, DBSession, SettingsDep
from api.routers.imports import _batches
from api.routers.parser import _parsed_rows
from api.routers.proposals import _proposals
from services.smart_service import SmartProcessor, SmartProcessingOptions

router = APIRouter(prefix="/pipeline", tags=["Import Pipeline"])

logger = logging.getLogger(__name__)


# ── Schemas ───────────────────────────────────────────────────────────────────

class ParseResponse(BaseModel):
    batch_id: str
    status: str
    source_type: str | None
    source_type_confidence: float
    txn_found: int
    parse_confidence: float
    warnings: list[str]
    llm_used_for_parse: bool = False   # True when LLM extraction was triggered during parse
    process_url: str   # next step: POST this URL to run smart-processing
    bank_account_code: str        # CoA code the source maps to, e.g. "1102"
    bank_account_name: str        # Human label, e.g. "Savings Account"
    bank_account_class: str       # "ASSET" | "LIABILITY" etc.


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
    raw_date: str | None
    raw_narration: str | None
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


class ProcessResponse(BaseModel):
    batch_id: str
    raw_rows_count: int
    normalized_count: int
    new_count: int
    duplicate_count: int
    llm_enhanced_count: int
    green_count: int
    yellow_count: int
    red_count: int
    proposals_generated: int
    use_llm: bool
    warnings: list[str]
    proposals_url: str   # next step: GET this URL to review proposals


class DetectResponse(BaseModel):
    """Result of the lightweight pre-upload detection call."""
    source_type: str | None            # e.g. "HDFC_BANK_CSV"
    source_type_label: str | None      # e.g. "HDFC Bank (CSV/XLS)"
    file_format: str                   # e.g. "XLSX"
    confidence: float
    method: str                        # "header_scan" | "content" | "filename" | "hint" | "none"
    is_encrypted: bool
    needs_password: bool
    password_hint: str | None = None   # e.g. "Your PAN is the password for CAS statements"
    metadata: dict[str, str | None]    # ifsc_code, account_number, account_holder, …
    missing_fields: list[str]          # fields user may want to supply
    warnings: list[str]
    bank_account_code: str             # CoA account code the source maps to, e.g. "1102"
    bank_account_name: str             # Human label, e.g. "Savings Account"
    bank_account_class: str            # "ASSET" | "LIABILITY" etc.


# ── POST /pipeline/detect ─────────────────────────────────────────────────────

@router.post(
    "/detect",
    response_model=DetectResponse,
    summary="Detect source type + extract metadata without parsing",
    description=(
        "Upload a file and get back the detected bank/source type, file format, "
        "confidence score, any extractable metadata (IFSC code, account number, "
        "statement period), and a list of fields the user may want to supply manually. "
        "Call this before /pipeline/parse so the UI can show confirmation and "
        "collect any missing details upfront."
    ),
    operation_id="pipelineDetect",
)
async def pipeline_detect(
    user_id: CurrentUser,
    settings: SettingsDep,
    session: DBSession,
    file: Annotated[UploadFile, File(description="Statement file (PDF/CSV/XLS/XLSX)")],
    source_type_hint: Annotated[str, Form()] = "",
    password: Annotated[str, Form(description="PDF password — only needed to read encrypted files")] = "",
) -> DetectResponse:
    from modules.parser.detector import SourceDetector  # noqa: PLC0415

    file_bytes = await file.read()
    if len(file_bytes) > settings.max_upload_size_bytes:
        raise HTTPException(status_code=413, detail={"error": "FILE_TOO_LARGE"})

    filename = file.filename or "upload"
    warnings: list[str] = []

    # ── password hint helper (filename-based, pre-decryption) ─────────────────
    import re as _re  # noqa: PLC0415
    _CAS_PATTERNS = _re.compile(
        r"cas.*cams|cams.*cas|camsonline|cas.*kfin|kfin.*cas|kfintech|mf.?central|\bcas\b"
        r"|[A-Z]{3}\d{4}_[A-Z0-9]+_TXN",  # CAMSonline TXN: e.g. FEB2026_AA30408065_TXN.pdf
        _re.I,
    )
    _pwd_hint: str | None = (
        "For CAMS / KFintech CAS statements your 10-character PAN is the password (e.g. ABCDE1234F)."
        if _CAS_PATTERNS.search(filename)
        else None
    )

    # Check for encrypted PDF (magic bytes — not extension)
    _is_real_pdf = file_bytes[:5].lstrip(b"\xef\xbb\xbf").startswith(b"%PDF")
    is_encrypted = False
    needs_password = False
    if _is_real_pdf:
        try:
            from core.utils.pdf_utils import is_pdf_encrypted, decrypt_pdf_bytes  # noqa: PLC0415
            if is_pdf_encrypted(file_bytes):
                is_encrypted = True
                if not password:
                    needs_password = True
                    # Return early — caller must supply password before we can detect
                    return DetectResponse(
                        source_type=None,
                        source_type_label=None,
                        file_format="PDF",
                        confidence=0.0,
                        method="none",
                        is_encrypted=True,
                        needs_password=True,
                        password_hint=_pwd_hint,
                        metadata={},
                        missing_fields=["password"],
                        warnings=["File is password-protected. Provide password to continue."],
                        bank_account_code="1102",
                        bank_account_name="Savings Account",
                        bank_account_class="ASSET",
                    )
                try:
                    file_bytes = decrypt_pdf_bytes(file_bytes, password)
                    is_encrypted = False   # decrypted successfully
                except ValueError as exc:
                    if "WRONG_PASSWORD" in str(exc):
                        raise HTTPException(
                            status_code=422,
                            detail={"error": "WRONG_PASSWORD", "message": "Incorrect PDF password."},
                        )
                    raise HTTPException(
                        status_code=422,
                        detail={"error": "PDF_ERROR", "message": str(exc)},
                    )
        except HTTPException:
            raise
        except Exception:  # noqa: BLE001
            pass

    # Check for OLE2-encrypted spreadsheet (password-protected XLS/XLSX).
    # Encrypted XLSX files produced by Excel/SBI use an OLE2 container wrapper
    # (magic D0 CF 11 E0) even though the underlying file is XLSX format.
    elif file_bytes[:4] == b"\xD0\xCF\x11\xE0":
        try:
            import io as _io  # noqa: PLC0415
            import msoffcrypto  # noqa: PLC0415
            office_file = msoffcrypto.OfficeFile(_io.BytesIO(file_bytes))
            if office_file.is_encrypted():
                is_encrypted = True
                if not password:
                    needs_password = True
                    return DetectResponse(
                        source_type=None,
                        source_type_label=None,
                        file_format="XLSX",
                        confidence=0.0,
                        method="none",
                        is_encrypted=True,
                        needs_password=True,
                        password_hint=_pwd_hint,
                        metadata={},
                        missing_fields=["password"],
                        warnings=["File is password-protected. Provide password to continue."],
                        bank_account_code="1102",
                        bank_account_name="Savings Account",
                        bank_account_class="ASSET",
                    )
                try:
                    office_file.load_key(password=password)
                    _dec_buf = _io.BytesIO()
                    office_file.decrypt(_dec_buf)
                    file_bytes = _dec_buf.getvalue()
                    is_encrypted = False
                except Exception as exc:  # noqa: BLE001
                    raise HTTPException(
                        status_code=422,
                        detail={"error": "WRONG_PASSWORD", "message": f"Could not decrypt file: {exc}"},
                    ) from exc
        except HTTPException:
            raise
        except Exception:  # noqa: BLE001
            pass

    # Run detection
    detector = SourceDetector()
    detection = detector.detect(
        filename=filename,
        file_bytes=file_bytes,
        source_type_hint=source_type_hint or None,
    )
    if detection.confidence < 0.70:
        warnings.append(
            "Low confidence detection — source type could not be determined reliably from file content. "
            "Use the override selector to set the correct bank."
        )

    # Extract metadata (IFSC, account number, dates, …)
    metadata = detector.extract_metadata(file_bytes, detection.file_format)

    # Determine which fields are still missing that the user might want to provide
    missing_fields: list[str] = []
    if not metadata.get("account_number"):
        missing_fields.append("account_number")
    if not metadata.get("ifsc_code"):
        missing_fields.append("ifsc_code")

    # Reuse the module-level labels dict (includes all banks + Zerodha Tax P&L)
    _source_labels = _ACTIVE_SOURCE_LABELS
    st_value = detection.source_type.value if detection.source_type else "UNKNOWN"
    source_label = _source_labels.get(st_value)

    from core.models.source_map import get_source_account  # noqa: PLC0415
    _src_acct = get_source_account(detection.source_type)

    b_code = _src_acct.account_code
    b_name = _src_acct.account_name
    b_class = _src_acct.account_class

    account_num = metadata.get("account_number")
    if account_num:
        from db.models.accounts import BankAccount
        from sqlalchemy import select
        from sqlalchemy.orm import joinedload
        
        bank_accounts = session.scalars(
            select(BankAccount)
            .where(BankAccount.is_active == True)
            .options(joinedload(BankAccount.account))
        ).all()
        
        for ba in bank_accounts:
            if ba.account_number_masked:
                digits = "".join(c for c in ba.account_number_masked if c.isdigit())
                if digits and account_num.endswith(digits):
                    acc = ba.account
                    if acc:
                        b_code = acc.code
                        b_name = acc.name
                        b_class = acc.account_type
                        break

    return DetectResponse(
        source_type=st_value if st_value != "UNKNOWN" else None,
        source_type_label=source_label,
        file_format=detection.file_format.value,
        confidence=detection.confidence,
        method=detection.method,
        is_encrypted=is_encrypted,
        needs_password=needs_password,
        metadata=metadata,
        missing_fields=missing_fields,
        warnings=warnings,
        bank_account_code=b_code,
        bank_account_name=b_name,
        bank_account_class=b_class,
    )


# ── POST /pipeline/parse ──────────────────────────────────────────────────────

@router.post(
    "/parse",
    response_model=ParseResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload + detect + parse in a single request",
    description=(
        "Combines SM-B upload and SM-C parse into one call. "
        "Returns 202 on initial acceptance; poll /pipeline/parse/status/{batch_id} "
        "until status is COMPLETED or FAILED."
    ),
    operation_id="pipelineParse",
)
async def pipeline_parse(
    user_id: CurrentUser,
    settings: SettingsDep,
    session: DBSession,
    file: Annotated[UploadFile, File(description="Statement file (PDF/CSV/XLS/XLSX)")],
    account_id: Annotated[str, Form()] = "",
    source_type_hint: Annotated[str, Form()] = "",
    use_llm: Annotated[bool, Form()] = False,
    llm_provider_id: Annotated[str, Form()] = "",
    extra_context: Annotated[str, Form()] = "",
    password: Annotated[str, Form(description="PDF password (never stored)")] = "",
) -> ParseResponse:
    import hashlib
    from core.models.enums import BatchStatus, SourceType
    from core.models.import_batch import ImportBatch
    from modules.parser.chain import ExtractionChain
    from modules.parser.detector import SourceDetector
    from modules.parser.registry import ParserRegistry
    from api.routers.imports import _batches, _ext_to_format
    from api.routers.parser import _parsed_rows

    file_bytes = await file.read()
    if len(file_bytes) > settings.max_upload_size_bytes:
        raise HTTPException(status_code=413, detail={"error": "FILE_TOO_LARGE"})

    filename = file.filename or "upload"

    # Detect and handle password-protected PDFs.
    # Only attempt this when the bytes really are a PDF (magic bytes %PDF),
    # not for XLS/XLSX files that may carry a .pdf extension.
    _is_real_pdf = file_bytes[:5].lstrip(b"\xef\xbb\xbf").startswith(b"%PDF")
    if _is_real_pdf:
        from core.utils.pdf_utils import is_pdf_encrypted, decrypt_pdf_bytes
        try:
            if is_pdf_encrypted(file_bytes):
                if not password:
                    # Tell the frontend to ask for the password — don't attempt to parse.
                    raise HTTPException(
                        status_code=422,
                        detail={"error": "PDF_ENCRYPTED", "message": "This PDF is password-protected. Please provide the password."},
                    )
                file_bytes = decrypt_pdf_bytes(file_bytes, password)
        except HTTPException:
            raise
        except ValueError as exc:
            if "WRONG_PASSWORD" in str(exc):
                raise HTTPException(
                    status_code=422,
                    detail={"error": "WRONG_PASSWORD", "message": "Incorrect PDF password."},
                )
            raise HTTPException(status_code=422, detail={"error": "PDF_ERROR", "message": str(exc)})

    # Detect and handle OLE2-encrypted spreadsheets (password-protected XLSX/XLS).
    elif file_bytes[:4] == b"\xD0\xCF\x11\xE0":
        try:
            import io as _io  # noqa: PLC0415
            import msoffcrypto  # noqa: PLC0415
            office_file = msoffcrypto.OfficeFile(_io.BytesIO(file_bytes))
            if office_file.is_encrypted():
                if not password:
                    raise HTTPException(
                        status_code=422,
                        detail={"error": "XLSX_ENCRYPTED", "message": "This spreadsheet is password-protected. Please provide the password."},
                    )
                office_file.load_key(password=password)
                _dec_buf = _io.BytesIO()
                office_file.decrypt(_dec_buf)
                file_bytes = _dec_buf.getvalue()
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=422,
                detail={"error": "WRONG_PASSWORD", "message": f"Could not decrypt file: {exc}"},
            ) from exc
    fmt = _ext_to_format(filename)
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    warnings: list[str] = []

    detector = SourceDetector()
    detection = detector.detect(
        filename=filename,
        file_bytes=file_bytes,
        source_type_hint=source_type_hint or None,
    )
    if detection.confidence < 0.70:
        warnings.append("Low source detection confidence. Consider setting source_type_hint.")

    batch = ImportBatch(
        user_id=user_id,
        account_id=account_id or str(uuid.uuid4()),
        filename=filename,
        file_hash=file_hash,
        source_type=detection.source_type,
        format=fmt,
        status=BatchStatus.PARSING,
    )
    object.__setattr__(batch, "file_size_bytes", len(file_bytes))
    object.__setattr__(batch, "detection_confidence", detection.confidence)
    _batches[batch.batch_id] = batch

    # Resolve LLM provider for parse-time extraction fallback (zero-row PDFs, scanned docs)
    _parse_llm_provider = None
    if use_llm and llm_provider_id:
        try:
            from api.routers.llm import _resolve_provider  # noqa: PLC0415
            _, _parse_llm_provider = _resolve_provider(user_id, llm_provider_id, settings, session)
            logger.info("parse: LLM provider resolved for extraction fallback (provider_id=%s)", llm_provider_id)
        except Exception as _llm_exc:
            warnings.append(f"LLM provider unavailable for parse: {_llm_exc}")

    try:
        registry = ParserRegistry.default()
        parser = registry.get(batch.source_type)
        if parser is None:
            batch.status = BatchStatus.PARSE_FAILED
            batch.error_message = f"No parser for {batch.source_type.value}"
            warnings.append(batch.error_message)
        else:
            chain = ExtractionChain(parser, batch.batch_id, file_bytes, filename=filename)
            result = chain.run(llm_provider=_parse_llm_provider)
            _parsed_rows[batch.batch_id] = result.rows
            batch.txn_found        = len(result.rows)
            batch.txn_new          = batch.txn_found
            batch.parse_confidence = result.metadata.overall_confidence
            batch.status           = BatchStatus.PARSE_COMPLETE
    except Exception as exc:  # pragma: no cover
        batch.status        = BatchStatus.PARSE_FAILED
        batch.error_message = str(exc)
        warnings.append(f"Parse failed: {exc}")

    from core.models.source_map import get_source_account  # noqa: PLC0415
    _src_acct = get_source_account(batch.source_type)

    return ParseResponse(
        batch_id=batch.batch_id,
        status=batch.status.value,
        source_type=batch.source_type.value if batch.source_type else None,
        source_type_confidence=detection.confidence,
        txn_found=batch.txn_found,
        parse_confidence=batch.parse_confidence,
        warnings=warnings,
        llm_used_for_parse=_parse_llm_provider is not None,
        process_url=f"/api/v1/pipeline/process/{batch.batch_id}",
        bank_account_code=_src_acct.account_code,
        bank_account_name=_src_acct.account_name,
        bank_account_class=_src_acct.account_class,
    )


# ── GET /pipeline/parse/status/{batch_id} ────────────────────────────────────

@router.get(
    "/parse/status/{batch_id}",
    response_model=ParseStatusResponse,
    summary="Poll pipeline parse status",
    operation_id="pipelineParseStatus",
)
def pipeline_parse_status(batch_id: str, user_id: CurrentUser) -> ParseStatusResponse:
    batch = _batches.get(batch_id)
    if not batch or getattr(batch, "user_id", None) != user_id:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND"})

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


# ── GET /pipeline/parse/{batch_id}/rows ───────────────────────────────────────

@router.get(
    "/parse/{batch_id}/rows",
    response_model=RawRowsResponse,
    summary="Retrieve paginated raw rows (pipeline alias)",
    operation_id="pipelineRows",
)
def pipeline_rows(
    batch_id: str,
    user_id: CurrentUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> RawRowsResponse:
    batch = _batches.get(batch_id)
    if not batch or getattr(batch, "user_id", None) != user_id:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND"})

    rows = _parsed_rows.get(batch_id, [])
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


# ── POST /pipeline/process/{batch_id} ─────────────────────────────────────────

class ProcessRequest(BaseModel):
    use_llm: bool = False
    provider_id: str | None = None
    llm_for_red_band_only: bool = True
    bank_account_id: str = "1102"
    account_id: str = ""  # override batch.account_id when set


@router.post(
    "/process/{batch_id}",
    response_model=ProcessResponse,
    summary="Normalize → dedup → categorize → score → propose",
    description=(
        "Runs the full smart-processing pipeline on the parsed rows of a batch. "
        "Set use_llm=true to enable LLM-assisted categorisation (requires a configured provider). "
        "Stores the resulting proposals for review via GET /api/v1/proposals/{batch_id}."
    ),
    operation_id="pipelineProcess",
)
def pipeline_process(
    batch_id: str,
    body: ProcessRequest,
    user_id: CurrentUser,
    session: DBSession,
    settings: SettingsDep,
) -> ProcessResponse:
    from core.models.enums import BatchStatus

    batch = _batches.get(batch_id)
    if not batch or getattr(batch, "user_id", None) != user_id:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND"})
    if batch.status not in (BatchStatus.PARSE_COMPLETE, BatchStatus.COMPLETED):
        raise HTTPException(
            status_code=409,
            detail={"error": "NOT_PARSED", "message": "Batch must be in PARSE_COMPLETE state."},
        )

    raw = _parsed_rows.get(batch_id, [])

    # Resolve optional LLM provider
    llm_provider = None
    if body.use_llm and body.provider_id:
        from api.routers.llm import _resolve_provider
        try:
            _name, llm_provider = _resolve_provider(user_id, body.provider_id, settings, session)
            logger.info("LLM provider resolved: %s (provider_id=%s)", _name, body.provider_id)
        except HTTPException:
            raise
    else:
        logger.info(
            "LLM skipped at router: use_llm=%s, provider_id=%s",
            body.use_llm, body.provider_id,
        )

    # Fetch committed hashes for this account to drive dedup
    from repositories.sqla_account_repo import AccountRepository
    effective_account_id = body.account_id or getattr(batch, "account_id", "")
    db_hashes: set[str] = set()
    acc_repo = AccountRepository(session)
    acc = acc_repo.find_by_code(effective_account_id)
    if acc is None:
        try:
            acc = acc_repo.get(int(effective_account_id))
        except (ValueError, TypeError):
            pass
    if acc:
        from repositories.sqla_transaction_repo import TransactionRepository
        db_hashes = TransactionRepository(session).get_committed_hashes_for_account(acc.id)

    opts = SmartProcessingOptions(
        use_llm=body.use_llm,
        llm_provider=llm_provider,
        llm_for_red_band_only=body.llm_for_red_band_only,
        bank_account_id=body.bank_account_id,
        db_hashes=db_hashes,
        session=session,
    )

    result = SmartProcessor().process_batch(user_id, batch_id, raw, opts)

    # Store proposals for the review step
    _proposals[batch_id] = result.proposals.proposals

    # Update batch counters
    batch.txn_new       = result.new_count
    batch.txn_duplicate = result.duplicate_count
    batch.status        = BatchStatus.COMPLETED

    return ProcessResponse(
        batch_id=batch_id,
        raw_rows_count=len(raw),
        normalized_count=result.normalized_count,
        new_count=result.new_count,
        duplicate_count=result.duplicate_count,
        llm_enhanced_count=result.llm_enhanced_count,
        green_count=result.green_count,
        yellow_count=result.yellow_count,
        red_count=result.red_count,
        proposals_generated=len(_proposals[batch_id]),
        use_llm=body.use_llm,
        warnings=result.warnings,
        proposals_url=f"/api/v1/proposals/{batch_id}",
    )


# ── GET /pipeline/source-types ────────────────────────────────────────────────

class SourceTypeInfo(BaseModel):
    value: str
    label: str
    format: str


_ACTIVE_SOURCE_TYPES = {
    # Zerodha — only Tax P&L
    "ZERODHA_TAX_PNL",
    # CAMS / KFintech / MF Central
    "CAS_CAMS",
    "CAS_KFINTECH",
    "CAS_MF_CENTRAL",
    # Banks
    "HDFC_BANK",
    "HDFC_BANK_CSV",
    "HDFC_BANK_CC",
    "SBI_BANK",
    "SBI_BANK_CSV",
    "ICICI_BANK",
    "ICICI_BANK_CSV",
    "ICICI_BANK_CC",
    "AXIS_BANK",
    "AXIS_BANK_CSV",
    "KOTAK_BANK",
    "KOTAK_BANK_CSV",
    "IDFC_BANK",
    "IDFC_BANK_CSV",
    "UNION_BANK",
    "UNION_BANK_CSV",
    "INDUSIND_BANK",
    "YES_BANK_CC",
}

_ACTIVE_SOURCE_LABELS = {
    "ZERODHA_TAX_PNL":  "Zerodha Tax P&L",
    "CAS_CAMS":         "CAMS (Mutual Funds)",
    "CAS_KFINTECH":     "KFintech (Mutual Funds)",
    "CAS_MF_CENTRAL":   "MF Central (Mutual Funds)",
    "HDFC_BANK":        "HDFC Bank (PDF)",
    "HDFC_BANK_CSV":    "HDFC Bank (CSV/XLS)",
    "HDFC_BANK_CC":     "HDFC Bank Credit Card (PDF)",
    "SBI_BANK":         "State Bank of India (PDF)",
    "SBI_BANK_CSV":     "State Bank of India (CSV)",
    "ICICI_BANK":       "ICICI Bank (PDF)",
    "ICICI_BANK_CSV":   "ICICI Bank (CSV/XLS)",
    "ICICI_BANK_CC":    "ICICI Bank Credit Card (PDF)",
    "AXIS_BANK":        "Axis Bank (PDF)",
    "AXIS_BANK_CSV":    "Axis Bank (CSV/XLS)",
    "KOTAK_BANK":       "Kotak Mahindra Bank (PDF)",
    "KOTAK_BANK_CSV":   "Kotak Mahindra Bank (CSV/XLS)",
    "IDFC_BANK":        "IDFC First Bank (PDF)",
    "IDFC_BANK_CSV":    "IDFC First Bank (CSV/XLS)",
    "UNION_BANK":       "Union Bank (PDF)",
    "UNION_BANK_CSV":   "Union Bank (CSV/XLS)",
    "INDUSIND_BANK":    "IndusInd Bank (PDF)",
    "YES_BANK_CC":      "YES Bank Credit Card (PDF)",
}


@router.get(
    "/source-types",
    response_model=list[SourceTypeInfo],
    summary="List all supported source types and their expected file formats",
    operation_id="pipelineListSourceTypes",
)
def pipeline_source_types() -> list[SourceTypeInfo]:
    from core.models.enums import SourceType, PDF_SOURCE_TYPES  # noqa: F401
    items: list[SourceTypeInfo] = []
    for s in SourceType:
        if s.value not in _ACTIVE_SOURCE_TYPES:
            continue
        fmt = "PDF" if s in PDF_SOURCE_TYPES else "CSV/XLS"
        label = _ACTIVE_SOURCE_LABELS.get(s.value, s.value.replace("_", " ").title())
        items.append(SourceTypeInfo(value=s.value, label=label, format=fmt))
    return items
