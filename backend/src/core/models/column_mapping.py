"""ColumnMapping — stores user-confirmed column mappings for Generic CSV/XLS sources.

Persisted after the Column Mapper UI flow (SM-C §5) and reused when the same
file format is uploaded again (matched by format_fingerprint = hash of header row).
"""

from __future__ import annotations

import uuid
from datetime import datetime, UTC

from pydantic import BaseModel, Field


class ColumnMapping(BaseModel):
    """Saved column mapping for a Generic CSV / XLS format."""

    mapping_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str

    # ── Format identification ─────────────────────────────────────────────────
    format_fingerprint: str     # SHA-256 of the normalised header row string
    mapping_label: str          # User-assigned name e.g. "Yes Bank CSV Export"

    # ── Column assignments ────────────────────────────────────────────────────
    date_column: str
    narration_column: str
    debit_column: str | None = None
    credit_column: str | None = None
    amount_column: str | None = None     # Single signed amount column (alternative to debit/credit)
    balance_column: str | None = None
    reference_column: str | None = None

    # ── Parsing hints ─────────────────────────────────────────────────────────
    date_format: str = "%d/%m/%Y"        # strptime format string
    amount_locale: str = "IN"            # IN = Indian commas, EU = European dots

    # ── Layout ────────────────────────────────────────────────────────────────
    header_row_index: int = 0
    data_start_row: int = 1              # 0-indexed row where data begins

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    confirmed_at: datetime | None = None  # Null until user explicitly confirms


class ColumnPreview(BaseModel):
    """Response from GET /imports/{batch_id}/column-preview."""

    batch_id: str
    headers: list[str]
    preview_rows: list[list[str]]        # First 10 data rows as string lists
    ai_suggestions: dict[str, str]       # {"date": "Date", "narration": "Remarks", ...}
    format_fingerprint: str
    existing_mapping_id: str | None = None  # Populated if a saved mapping matches
