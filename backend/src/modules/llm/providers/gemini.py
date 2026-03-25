"""Google Gemini LLM provider (primary provider for SM-D).

Uses the `google-genai` SDK (google.genai — the new stable package).
The deprecated `google.generativeai` package has been removed.

Spec reference: SM-D §3.1 — Provider Capability Matrix.
"""

from __future__ import annotations

import json
import logging
import re

from core.models.enums import ExtractionMethod, SourceType
from core.models.raw_parsed_row import RawParsedRow
from modules.llm.base import (
    BaseLLMProvider,
    LLMResponse,
    TextExtractionRequest,
    VisionExtractionRequest,
)
from modules.llm.models import SYSTEM_PROMPT_EXTRACTION, SYSTEM_PROMPT_VISION

logger = logging.getLogger(__name__)

# Gemini model identifiers — update as new versions release
GEMINI_TEXT_MODEL   = "gemini-3-flash-preview"   # fast, low-cost, natively multimodal
GEMINI_VISION_MODEL = "gemini-3-flash-preview"   # same model handles text + vision

# Max pages per vision call — keep small so each chunk fits within token limits
MAX_PAGES_PER_CALL = 3


class GeminiProvider(BaseLLMProvider):
    """Google Gemini provider adapter.

    API key is injected at construction time — never stored as a class attribute.
    The genai SDK is configured lazily on first use.

    Usage:
        provider = GeminiProvider(api_key="AIza...", text_model="gemini-1.5-pro")
        response = provider.extract_text(request)
    """

    PROVIDER_NAME = "GOOGLE"

    def __init__(
        self,
        api_key: str,
        text_model: str = GEMINI_TEXT_MODEL,
        vision_model: str = GEMINI_VISION_MODEL,
    ) -> None:
        self._api_key = api_key
        self._text_model = text_model
        self._vision_model = vision_model

    # ── Public interface ──────────────────────────────────────────────────────

    def extract_text(self, request: TextExtractionRequest) -> LLMResponse:
        """Send partial text to Gemini and extract structured transaction rows.

        When ``request.source_type == "CATEGORIZE"`` the method switches to the
        categorization system prompt and a categorization-specific user message so
        the LLM returns category codes instead of raw transaction fields.
        """
        try:
            from google import genai  # noqa: PLC0415
            from google.genai import types  # noqa: PLC0415
            from modules.llm.models import SYSTEM_PROMPT_CATEGORIZE  # noqa: PLC0415

            is_categorize = str(request.source_type) == "CATEGORIZE"
            client = genai.Client(api_key=self._api_key)
            system_prompt = SYSTEM_PROMPT_CATEGORIZE if is_categorize else SYSTEM_PROMPT_EXTRACTION
            user_prompt = (
                self._build_categorize_user_prompt(request)
                if is_categorize
                else self._build_text_user_prompt(request)
            )

            response = client.models.generate_content(
                model=self._text_model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.0,
                    response_mime_type="application/json",
                    max_output_tokens=32000,
                ),
            )

            raw_json = response.text
            rows, is_truncated = self._parse_json_response(raw_json, request.batch_id, "TEXT")
            usage = response.usage_metadata

            return LLMResponse(
                batch_id=request.batch_id,
                rows=rows,
                input_tokens=getattr(usage, "prompt_token_count", 0),
                output_tokens=getattr(usage, "candidates_token_count", 0),
                model_used=self._text_model,
                provider_name=self.PROVIDER_NAME,
                overall_confidence=self._avg_confidence(rows),
                raw_response=raw_json,
                is_truncated=is_truncated,
            )

        except Exception as exc:  # noqa: BLE001
            logger.error("GeminiProvider.extract_text failed: %s", exc, exc_info=True)
            return LLMResponse(
                batch_id=request.batch_id,
                rows=[],
                model_used=self._text_model,
                provider_name=self.PROVIDER_NAME,
                error=str(exc),
            )

    def extract_vision(self, request: VisionExtractionRequest) -> LLMResponse:
        """Send page images to Gemini Vision and extract structured transaction rows.

        Pages are sent in chunks of MAX_PAGES_PER_CALL to stay within token limits.
        """
        all_rows: list[RawParsedRow] = []
        total_input = 0
        total_output = 0
        last_raw = ""

        chunks = [
            request.page_images[i : i + MAX_PAGES_PER_CALL]
            for i in range(0, len(request.page_images), MAX_PAGES_PER_CALL)
        ]

        for chunk_idx, chunk_pages in enumerate(chunks):
            try:
                rows, in_tok, out_tok, raw = self._vision_chunk(
                    request, chunk_pages, chunk_idx * MAX_PAGES_PER_CALL
                )
                all_rows.extend(rows)
                total_input += in_tok
                total_output += out_tok
                last_raw = raw
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "GeminiProvider.extract_vision chunk %d failed: %s", chunk_idx, exc
                )
                return LLMResponse(
                    batch_id=request.batch_id,
                    rows=all_rows,
                    input_tokens=total_input,
                    output_tokens=total_output,
                    model_used=self._vision_model,
                    provider_name=self.PROVIDER_NAME,
                    error=str(exc),
                )

        return LLMResponse(
            batch_id=request.batch_id,
            rows=all_rows,
            input_tokens=total_input,
            output_tokens=total_output,
            model_used=self._vision_model,
            provider_name=self.PROVIDER_NAME,
            overall_confidence=self._avg_confidence(all_rows),
            raw_response=last_raw,
        )

    def test_connection(self) -> bool:
        """Send a minimal prompt to verify the API key and model are accessible."""
        try:
            from google import genai  # noqa: PLC0415

            client = genai.Client(api_key=self._api_key)
            response = client.models.generate_content(
                model=self._text_model,
                contents="Reply with the word ok only.",
            )
            return bool(response.text)
        except Exception as exc:  # noqa: BLE001
            logger.warning("GeminiProvider.test_connection failed: %s", exc)
            return False

    # ── Private helpers ───────────────────────────────────────────────────────

    def _vision_chunk(
        self,
        request: VisionExtractionRequest,
        pages: list[bytes],
        page_offset: int,
    ) -> tuple[list[RawParsedRow], int, int, str]:
        from google import genai  # noqa: PLC0415
        from google.genai import types  # noqa: PLC0415

        client = genai.Client(api_key=self._api_key)

        # Build content: [image_part, image_part, ..., text_prompt]
        content_parts: list = []
        for png_bytes in pages:
            content_parts.append(
                types.Part.from_bytes(data=png_bytes, mime_type="image/png")
            )

        user_text = _build_vision_user_prompt(request.source_type, request.existing_rows_context)
        content_parts.append(user_text)

        response = client.models.generate_content(
            model=self._vision_model,
            contents=content_parts,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT_VISION,
                temperature=0.0,
                response_mime_type="application/json",
                max_output_tokens=32000,
            ),
        )
        raw_json = response.text
        usage = response.usage_metadata
        rows, _trunc = self._parse_json_response(raw_json, request.batch_id, "VISION", page_offset)
        return (
            rows,
            getattr(usage, "prompt_token_count", 0),
            getattr(usage, "candidates_token_count", 0),
            raw_json,
        )

    @staticmethod
    def _build_text_user_prompt(request: TextExtractionRequest) -> str:
        lines = [
            f"Source type: {request.source_type}",
            f"Total pages: {request.page_count}",
            "",
            "Extracted text:",
            "```",
            request.partial_text,
            "```",
            "",
            "Extract all transactions from the text above.",
        ]
        return "\n".join(lines)

    @staticmethod
    def _build_categorize_user_prompt(request: TextExtractionRequest) -> str:
        lines = [
            "Categorize each of the following bank transactions.",
            "Return a compact JSON array — one object per line — with ONLY these three fields:",
            '  {"id": "TXN_N", "category_code": "<CODE>", "confidence": <0.0-1.0>}',
            "Do NOT echo the narration back. Use only the TXN_N identifier.",
            "",
            request.partial_text,
        ]
        return "\n".join(lines)

    @staticmethod
    def _parse_json_response(
        raw_json: str,
        batch_id: str,
        path: str,
        page_offset: int = 0,
    ) -> tuple[list[RawParsedRow], bool]:
        """Parse the LLM JSON response into RawParsedRow objects.

        Returns (rows, is_truncated) where is_truncated is True when the raw JSON
        was cut off and partial recovery was used.
        """
        is_truncated = False
        # Strip markdown fences if model added them despite mime_type hint
        cleaned = re.sub(r"```(?:json)?", "", raw_json).strip().rstrip("`").strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.warning("GeminiProvider: JSON parse failed: %s — attempting partial recovery", exc)
            # Recover complete objects from a truncated JSON array by finding the last
            # closing brace that ends a complete object (indicated by trailing "}," or "}").
            last_close = cleaned.rfind("},")
            if last_close == -1:
                last_close = cleaned.rfind("}")
            if last_close > 0:
                partial = cleaned[: last_close + 1].lstrip()
                if not partial.startswith("["):
                    partial = "[" + partial
                partial = partial + "]"
                try:
                    data = json.loads(partial)
                    is_truncated = True
                    logger.info(
                        "GeminiProvider: partial recovery succeeded — %d item(s) recovered",
                        len(data) if isinstance(data, list) else 1,
                    )
                except json.JSONDecodeError:
                    logger.warning("GeminiProvider: partial recovery also failed, returning []")
                    return [], True
            else:
                return [], True

        if not isinstance(data, list):
            # Unwrap any common envelope keys the model might use
            for key in ("transactions", "rows", "data", "entries", "records", "items", "result"):
                if key in data and isinstance(data[key], list):
                    data = data[key]
                    break
            else:
                data = [data]  # single-object response

        if len(data) < 3:
            logger.debug(
                "GeminiProvider: only %d row(s) parsed from response (path=%s).\nRaw: %s",
                len(data), path, raw_json[:1000],
            )

        rows: list[RawParsedRow] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            raw_date = str(item.get("date", "")).strip()
            # Categorization responses have no date — accept them if category_code is present
            if not raw_date and not item.get("category_code"):
                continue

            page_num = item.get("page_number")
            if page_num is not None:
                page_num = int(page_num) + page_offset

            rows.append(
                RawParsedRow(
                    batch_id=batch_id,
                    source_type=SourceType.UNKNOWN,
                    parser_version="gemini-1.5-pro",
                    extraction_method=(
                        ExtractionMethod.LLM_TEXT if path == "TEXT" else ExtractionMethod.LLM_VISION
                    ),
                    raw_date=raw_date,
                    raw_narration=(
                        str(item.get("narration") or item.get("id", "")).strip()
                    ),
                    raw_debit=str(item["debit_amount"]).strip() if item.get("debit_amount") else None,
                    raw_credit=str(item["credit_amount"]).strip() if item.get("credit_amount") else None,
                    raw_balance=str(item["balance"]).strip() if item.get("balance") else None,
                    raw_reference=str(item["reference"]).strip() if item.get("reference") else None,
                    row_confidence=float(item.get("confidence", 0.8)),
                    page_number=page_num,
                    extra_fields=(
                        {"category_code": str(item["category_code"]).strip()}
                        if item.get("category_code")
                        else {}
                    ),
                )
            )

        return rows, is_truncated

    @staticmethod
    def _avg_confidence(rows: list[RawParsedRow]) -> float:
        if not rows:
            return 0.0
        return round(sum(r.row_confidence for r in rows) / len(rows), 4)

    # ── Files API ─────────────────────────────────────────────────────────────

    def upload_file(self, request: "FileExtractionRequest") -> "UploadedFile":
        """Upload a document to the Gemini Files API.

        Gemini supports arbitrary MIME types including application/pdf.
        Uploaded files persist for 48 hours and can be referenced by URI.
        """
        from modules.llm.base import UploadedFile  # noqa: PLC0415
        try:
            from google import genai  # noqa: PLC0415
            import io as _io

            client = genai.Client(api_key=self._api_key)
            uploaded = client.files.upload(
                file=_io.BytesIO(request.file_bytes),
                config={"mime_type": request.mime_type, "display_name": request.filename},
            )
            return UploadedFile(
                file_id=uploaded.name,
                provider_name=self.PROVIDER_NAME,
                filename=request.filename,
                mime_type=request.mime_type,
                size_bytes=len(request.file_bytes),
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("GeminiProvider.upload_file failed: %s", exc)
            raise RuntimeError(f"Gemini file upload failed: {exc}") from exc

    def extract_with_file(
        self,
        file_id: str,
        batch_id: str,
        source_type: str,
        extra_context: dict | None = None,
    ) -> "LLMResponse":
        """Extract transactions from a previously uploaded file via the Files API."""
        from modules.llm.base import LLMResponse  # noqa: PLC0415
        try:
            from google import genai  # noqa: PLC0415
            from google.genai import types  # noqa: PLC0415

            client = genai.Client(api_key=self._api_key)
            file_ref = client.files.get(name=file_id)
            user_prompt = (
                f"Source type: {source_type}\n\n"
                "Extract all transactions from the attached document. "
                "Return JSON with the schema: "
                "{\"transactions\": [{\"date\", \"narration\", \"debit_amount\", \"credit_amount\", \"balance\", \"reference\", \"confidence\"}]}"
            )
            if extra_context:
                user_prompt += f"\n\nAdditional context: {extra_context}"

            response = client.models.generate_content(
                model=self._vision_model,
                contents=[file_ref, user_prompt],
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT_EXTRACTION,
                    temperature=0.0,
                    response_mime_type="application/json",
                    max_output_tokens=32000,
                ),
            )
            raw_json = response.text
            rows, is_truncated = self._parse_json_response(raw_json, batch_id, "TEXT")
            usage    = response.usage_metadata

            return LLMResponse(
                batch_id=batch_id,
                rows=rows,
                input_tokens=getattr(usage, "prompt_token_count", 0),
                output_tokens=getattr(usage, "candidates_token_count", 0),
                model_used=self._vision_model,
                provider_name=self.PROVIDER_NAME,
                overall_confidence=self._avg_confidence(rows),
                raw_response=raw_json,
                is_truncated=is_truncated,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("GeminiProvider.extract_with_file failed: %s", exc)
            return LLMResponse(batch_id=batch_id, rows=[], error=str(exc))

    def delete_file(self, file_id: str) -> bool:
        """Delete an uploaded file from the Gemini Files API."""
        try:
            from google import genai  # noqa: PLC0415
            client = genai.Client(api_key=self._api_key)
            client.files.delete(name=file_id)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("GeminiProvider.delete_file failed for %s: %s", file_id, exc)
            return False


# ── Module-level helpers ──────────────────────────────────────────────────────

_SOURCE_TYPE_HINTS: dict[str, str] = {
    "HDFC_BANK": (
        "This is an HDFC Bank account statement (India). "
        "Standard columns: Date | Narration | Chq./Ref.No. | Value Dt | "
        "Withdrawal Amt. (= debit_amount) | Deposit Amt. (= credit_amount) | Closing Balance (= balance). "
        "Dates are typically DD/MM/YY or DD-MM-YYYY. "
        "Map 'Chq./Ref.No.' → reference. "
        "Opening/Closing balance summary lines are NOT transactions — skip them."
    ),
    "HDFC_BANK_CSV": (
        "This is an HDFC Bank account statement (India). "
        "Columns: Date | Narration | Chq./Ref.No. | Value Dt | "
        "Withdrawal Amt. (= debit_amount) | Deposit Amt. (= credit_amount) | Closing Balance. "
        "Opening/Closing balance summary lines are NOT transactions — skip them."
    ),
    "ICICI_BANK": (
        "This is an ICICI Bank account statement (India). "
        "Columns typically: S.No. | Transaction Date | Value Date | Description | "
        "Debit (= debit_amount) | Credit (= credit_amount) | Balance."
    ),
    "SBI_BANK": (
        "This is an SBI Bank account statement (India). "
        "Columns typically: Txn Date | Value Date | Description | Ref No. | "
        "Debit (= debit_amount) | Credit (= credit_amount) | Balance."
    ),
}


def _build_vision_user_prompt(source_type: str, existing_rows_context: str | None = None) -> str:
    """Build the per-chunk vision user prompt, enriched with source-type column hints."""
    hint = _SOURCE_TYPE_HINTS.get(str(source_type), "")
    lines = ["Extract ALL transactions visible in the statement page(s) above."]
    if hint:
        lines.append(f"\nStatement format: {hint}")
    lines.append(
        "\nReturn a JSON array where every element has exactly these keys: "
        "date, narration, debit_amount, credit_amount, balance, reference, confidence. "
        'Use empty string "" for any field not present. '
        "Do NOT include header rows, opening balance lines, or summary lines."
    )
    if existing_rows_context:
        lines.append(f"\nContext (previously parsed rows for reference):\n{existing_rows_context}")
    return "\n".join(lines)
