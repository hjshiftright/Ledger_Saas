"""RawParsedRow, ParseMetadata, and ParseResult.

These are the canonical outputs of SM-C (Parser Engine) and SM-D (LLM Module).
Both modules produce the same schema so SM-E (Normalization) has a single input contract.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from core.models.enums import ExtractionMethod, ParseStatus, SourceType, TxnTypeHint


class RawParsedRow(BaseModel):
    """One extracted transaction row — pre-normalization.

    Produced by SM-C or SM-D; consumed by SM-E.
    All monetary fields remain as raw strings until SM-E normalizes them.
    """

    row_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    batch_id: str
    source_type: SourceType
    parser_version: str
    extraction_method: ExtractionMethod

    # ── Raw string fields (un-parsed) ─────────────────────────────────────────
    raw_date: str
    raw_narration: str
    raw_debit: str | None = None
    raw_credit: str | None = None
    raw_balance: str | None = None
    raw_reference: str | None = None
    raw_quantity: str | None = None    # Investment rows: units / shares
    raw_unit_price: str | None = None  # Investment rows: NAV or price per unit

    txn_type_hint: TxnTypeHint = TxnTypeHint.UNKNOWN
    row_confidence: float = Field(ge=0.0, le=1.0, default=0.0)

    # ── Positional ────────────────────────────────────────────────────────────
    page_number: int | None = None
    row_number: int | None = None

    # ── Investment / CAS specific ─────────────────────────────────────────────
    folio_id: str | None = None
    fund_isin: str | None = None

    extra_fields: dict[str, Any] = Field(default_factory=dict)

    model_config = {"frozen": False}


class ParseMetadata(BaseModel):
    """Summary metadata produced alongside RawParsedRow[] by a parser run."""

    statement_from: str | None = None          # ISO date string "YYYY-MM-DD"
    statement_to: str | None = None            # ISO date string
    account_hint: str | None = None            # Account number fragment / folio
    total_rows_found: int = 0
    rows_with_errors: int = 0
    opening_balance: Decimal | None = None
    closing_balance: Decimal | None = None
    balance_cross_check_passed: bool | None = None
    overall_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)
    extraction_method: ExtractionMethod = ExtractionMethod.TEXT_LAYER
    parser_version: str = "unknown"


class ParseResult(BaseModel):
    """Complete result of parsing one ImportBatch document."""

    batch_id: str
    status: ParseStatus
    rows: list[RawParsedRow] = Field(default_factory=list)
    metadata: ParseMetadata = Field(default_factory=ParseMetadata)
    error_message: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.status == ParseStatus.SUCCESS

    @property
    def row_count(self) -> int:
        return len(self.rows)
