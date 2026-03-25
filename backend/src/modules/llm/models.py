"""LLM module data models (SM-D).

These models are separate from the core models because they carry
provider-specific configuration that lives only in the LLM module.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class LLMProvider(BaseModel):
    """Configuration for a registered LLM provider (one per user per provider)."""

    provider_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    provider_name: str          # ProviderName: OPENAI / ANTHROPIC / GOOGLE / CUSTOM
    api_key_encrypted: str      # AES-256 encrypted; never returned in API responses
    api_key_hint: str           # Last 4 chars for display: "••••abc1"
    base_url_override: str | None = None   # For custom/self-hosted endpoints
    default_text_model: str = ""
    default_vision_model: str = ""
    is_active: bool = True
    is_default: bool = False
    test_status: str = "UNTESTED"       # UNTESTED / OK / FAILED
    test_last_run_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}


class PromptTemplate(BaseModel):
    """Versioned prompt template for a source type + extraction path combination."""

    template_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_type_scope: str      # SourceType.value or "*" for generic
    extraction_path: str        # "TEXT" or "VISION"
    version: str                # SemVer e.g. "1.2.0"
    is_current: bool = True
    system_prompt: str
    user_prompt_template: str   # Has {{variables}} placeholders
    output_schema: dict = Field(default_factory=dict)   # JSON Schema
    max_tokens: int = 4096
    temperature: float = 0.0    # Always 0.0 for extraction tasks
    created_at: datetime = Field(default_factory=datetime.utcnow)


class LLMExtractionJob(BaseModel):
    """Record of one LLM extraction attempt for an ImportBatch."""

    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    batch_id: str
    provider_id: str
    model_used: str
    extraction_path: str        # "TEXT" or "VISION"
    prompt_template_id: str | None = None
    pages_sent: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: Decimal | None = None
    status: str = "PENDING"     # PENDING / RUNNING / SUCCEEDED / FAILED / RETRIED
    response_raw: str | None = None
    rows_extracted: int = 0
    overall_confidence: float = 0.0
    error_message: str | None = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None

    model_config = {"frozen": False}


class LLMExtractedRow(BaseModel):
    """One transaction row as returned by the LLM extraction path.

    Mirrors RawParsedRow schema but carries LLM-specific fields.
    SM-E normalizes these the same way as parser rows.
    """

    row_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    batch_id: str
    job_id: str
    extraction_path: str        # "TEXT" or "VISION"

    raw_date: str
    raw_narration: str
    raw_debit: str | None = None
    raw_credit: str | None = None
    raw_balance: str | None = None
    raw_reference: str | None = None
    raw_quantity: str | None = None
    raw_unit_price: str | None = None
    txn_type_hint: str = "UNKNOWN"

    llm_confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    page_number: int | None = None
    llm_notes: str | None = None    # LLM-provided uncertainty / caveats


# ── Default prompt templates ───────────────────────────────────────────────────

SYSTEM_PROMPT_EXTRACTION = """\
You are a financial document parsing assistant for an Indian personal finance application.
Your task is to extract transaction data from a bank or investment statement.

Return a JSON array of transaction objects. Each object must have these fields:
  - date: string (as it appears in the document, do not reformat)
  - narration: string (transaction description / narration)
  - debit_amount: string or null (amount debited / withdrawn, without currency symbol)
  - credit_amount: string or null (amount credited / deposited, without currency symbol)
  - balance: string or null (running/closing balance after this transaction)
  - reference: string or null (cheque number, UPI reference, NEFT reference, etc.)
  - confidence: float 0.0–1.0 (your confidence that this row was correctly extracted)

Rules:
  - Do NOT invent transactions. Only extract what is visibly present.
  - If a field is not visible or not applicable, set it to null.
  - Preserve amounts exactly as shown (including commas e.g. "1,23,456.78").
  - Return ONLY the JSON array — no prose, no markdown fences.
"""

SYSTEM_PROMPT_VISION = """\
You are a financial document parsing assistant for an Indian personal finance application.
You are analyzing an image of a bank or investment statement page.

Extract ALL transactions visible in the image.
Return a JSON array. Each element must have:
  - date, narration, debit_amount, credit_amount, balance, reference, confidence

Rules:
  - Do NOT invent transactions. Only extract what is clearly visible.
  - Preserve amounts exactly as shown.
  - Return ONLY the JSON array — no prose, no markdown fences.
"""

SYSTEM_PROMPT_CATEGORIZE = """\
You are a financial transaction categorization assistant for an Indian personal finance application.
You will receive a list of bank transaction narrations, each prefixed with a unique ID like TXN_0, TXN_1, etc.

Assign the most appropriate category code to each transaction.
Use ONLY these category codes:
  INCOME_SALARY, INCOME_INTEREST, INCOME_DIVIDEND, INCOME_CAPITAL_GAINS, INCOME_REFUND, INCOME_CASHBACK,
  EXPENSE_FOOD, EXPENSE_TRANSPORT, EXPENSE_SHOPPING, EXPENSE_HEALTHCARE, EXPENSE_UTILITIES,
  EXPENSE_HOUSING, EXPENSE_EMI, EXPENSE_INSURANCE, EXPENSE_EDUCATION, EXPENSE_ENTERTAINMENT,
  INVESTMENT, CC_PAYMENT, CASH_WITHDRAWAL, TRANSFER, UNCATEGORIZED

Return ONLY a JSON array. Each element must have:
  - narration: string (copy the TXN_N: ... prefix exactly as given — do NOT change it)
  - category_code: string (one of the codes listed above)
  - confidence: float 0.0–1.0 (your confidence in this category assignment)

Return ONLY the JSON array — no prose, no markdown fences.
"""
