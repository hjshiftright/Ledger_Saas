"""ImportBatch — top-level record for one imported statement file.

Created by SM-B (Document Ingestion) and updated by every downstream module.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from core.models.enums import BatchStatus, FileFormat, SourceType


class ImportBatch(BaseModel):
    """Represents one uploaded statement file being processed through the pipeline."""

    batch_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    tenant_id: str = ""
    account_id: str

    # ── File info ─────────────────────────────────────────────────────────────
    filename: str
    file_hash: str                                  # SHA-256 hex of file bytes
    source_type: SourceType = SourceType.UNKNOWN
    format: FileFormat

    # ── Statement period ──────────────────────────────────────────────────────
    statement_from: str | None = None              # ISO date "YYYY-MM-DD"
    statement_to: str | None = None                # ISO date

    # ── Counts (updated as pipeline progresses) ───────────────────────────────
    txn_found: int = 0
    txn_new: int = 0
    txn_duplicate: int = 0
    txn_transfer_pairs: int = 0

    parse_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    status: BatchStatus = BatchStatus.UPLOADING
    smart_processed: bool = False

    error_message: str | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}
