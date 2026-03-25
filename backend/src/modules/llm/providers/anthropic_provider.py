"""Anthropic Claude provider for SM-D LLM Processing Module.

Supports:
  - Text extraction (claude-3-5-sonnet — tool_use for structured output)
  - Vision extraction (multimodal image messages)
  - Files API (beta — requires anthropic>=0.40 with files beta header)
"""

from __future__ import annotations

import base64
import json
import logging
import re

from core.models.enums import ExtractionMethod, SourceType
from core.models.raw_parsed_row import RawParsedRow
from modules.llm.base import (
    BaseLLMProvider,
    FileExtractionRequest,
    LLMResponse,
    TextExtractionRequest,
    UploadedFile,
    VisionExtractionRequest,
)
from modules.llm.models import SYSTEM_PROMPT_CATEGORIZE, SYSTEM_PROMPT_EXTRACTION, SYSTEM_PROMPT_VISION

logger = logging.getLogger(__name__)

MAX_PAGES_PER_CALL = 10


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider adapter."""

    PROVIDER_NAME = "ANTHROPIC"
    DEFAULT_TEXT_MODEL   = "claude-3-7-sonnet-20250219"  # Claude 3.7 Sonnet (Feb 2025)
    DEFAULT_VISION_MODEL = "claude-3-7-sonnet-20250219"

    def __init__(
        self,
        api_key: str,
        text_model: str   = DEFAULT_TEXT_MODEL,
        vision_model: str = DEFAULT_VISION_MODEL,
    ) -> None:
        self._api_key     = api_key
        self._text_model  = text_model
        self._vision_model = vision_model

    # ── Text extraction ───────────────────────────────────────────────────────

    def extract_text(self, request: TextExtractionRequest) -> LLMResponse:
        try:
            import anthropic  # noqa: PLC0415

            is_categorize = str(request.source_type) == "CATEGORIZE"
            client = anthropic.Anthropic(api_key=self._api_key)
            if is_categorize:
                system_prompt = SYSTEM_PROMPT_CATEGORIZE
                user_prompt = (
                    "Categorize each of the following bank transactions.\n"
                    "Return a JSON array assigning a category_code to each TXN_N entry.\n\n"
                    + request.partial_text
                )
            else:
                system_prompt = SYSTEM_PROMPT_EXTRACTION
                user_prompt = (
                    f"Source type: {request.source_type}\n"
                    f"Total pages: {request.page_count}\n\n"
                    "Extracted text:\n```\n"
                    f"{request.partial_text}\n```\n\n"
                    "Extract all transactions. Return JSON: "
                    "{\"transactions\": [{\"date\", \"narration\", \"debit_amount\", \"credit_amount\", \"balance\", \"reference\", \"confidence\"}]}"
                )

            response = client.messages.create(
                model=self._text_model,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                max_tokens=4096,
                temperature=0,
            )

            raw_json = response.content[0].text if response.content else ""
            rows     = self._parse_json_response(raw_json, request.batch_id, "TEXT")
            usage    = response.usage

            return LLMResponse(
                batch_id=request.batch_id,
                rows=rows,
                input_tokens=getattr(usage, "input_tokens", 0),
                output_tokens=getattr(usage, "output_tokens", 0),
                model_used=self._text_model,
                provider_name=self.PROVIDER_NAME,
                overall_confidence=self._avg_confidence(rows),
                raw_response=raw_json,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("AnthropicProvider.extract_text failed: %s", exc, exc_info=True)
            return LLMResponse(batch_id=request.batch_id, rows=[], error=str(exc))

    # ── Vision extraction ─────────────────────────────────────────────────────

    def extract_vision(self, request: VisionExtractionRequest) -> LLMResponse:
        chunks = [
            request.page_images[i : i + MAX_PAGES_PER_CALL]
            for i in range(0, len(request.page_images), MAX_PAGES_PER_CALL)
        ]
        all_rows: list[RawParsedRow] = []
        total_input = total_output = 0
        last_raw = ""

        for chunk_idx, chunk_pages in enumerate(chunks):
            try:
                rows, in_tok, out_tok, raw = self._vision_chunk(
                    request, chunk_pages, chunk_idx * MAX_PAGES_PER_CALL
                )
                all_rows.extend(rows)
                total_input  += in_tok
                total_output += out_tok
                last_raw = raw
            except Exception as exc:  # noqa: BLE001
                logger.error("AnthropicProvider chunk %d failed: %s", chunk_idx, exc)
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

    def _vision_chunk(
        self,
        request: VisionExtractionRequest,
        pages: list[bytes],
        page_offset: int,
    ) -> tuple[list[RawParsedRow], int, int, str]:
        import anthropic  # noqa: PLC0415

        client = anthropic.Anthropic(api_key=self._api_key)
        content: list = []

        for png in pages:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": base64.b64encode(png).decode(),
                },
            })

        text_prompt = (
            "Extract all transactions from the statement page(s). "
            "Return JSON: {\"transactions\": [{\"date\", \"narration\", \"debit_amount\", "
            "\"credit_amount\", \"balance\", \"reference\", \"page_number\", \"confidence\"}]}"
        )
        if request.existing_rows_context:
            text_prompt += f"\n\nContext:\n{request.existing_rows_context}"
        content.append({"type": "text", "text": text_prompt})

        response = client.messages.create(
            model=self._vision_model,
            system=SYSTEM_PROMPT_VISION,
            messages=[{"role": "user", "content": content}],
            max_tokens=16000,
            temperature=0,
        )
        raw_json = response.content[0].text if response.content else ""
        usage    = response.usage
        rows     = self._parse_json_response(raw_json, request.batch_id, "VISION", page_offset)
        return rows, getattr(usage, "input_tokens", 0), getattr(usage, "output_tokens", 0), raw_json

    # ── Files API (beta) ──────────────────────────────────────────────────────

    def upload_file(self, request: FileExtractionRequest) -> UploadedFile:
        """Upload to Anthropic Files API (requires beta header)."""
        try:
            import anthropic  # noqa: PLC0415
            import io as _io

            client = anthropic.Anthropic(
                api_key=self._api_key,
                default_headers={"anthropic-beta": "files-api-2025-04-14"},
            )
            file_tuple = (_io.BytesIO(request.file_bytes), request.filename)
            response = client.beta.files.upload(
                file=(request.filename, file_tuple, request.mime_type)
            )
            return UploadedFile(
                file_id=response.id,
                provider_name=self.PROVIDER_NAME,
                filename=request.filename,
                mime_type=request.mime_type,
                size_bytes=len(request.file_bytes),
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("AnthropicProvider.upload_file failed: %s", exc)
            raise RuntimeError(f"Anthropic file upload failed: {exc}") from exc

    def extract_with_file(
        self,
        file_id: str,
        batch_id: str,
        source_type: str,
        extra_context: dict | None = None,
    ) -> LLMResponse:
        """Extract using a previously uploaded file via Anthropic Files API."""
        try:
            import anthropic  # noqa: PLC0415

            client = anthropic.Anthropic(
                api_key=self._api_key,
                default_headers={"anthropic-beta": "files-api-2025-04-14"},
            )
            text_prompt = (
                f"Source type: {source_type}\n\n"
                "Extract all transactions from the attached document. "
                "Return JSON: {\"transactions\": [{\"date\", \"narration\", \"debit_amount\", "
                "\"credit_amount\", \"balance\", \"reference\", \"confidence\"}]}"
            )
            if extra_context:
                text_prompt += f"\n\nContext: {extra_context}"

            content = [
                {"type": "document", "source": {"type": "file", "file_id": file_id}},
                {"type": "text", "text": text_prompt},
            ]
            response = client.messages.create(
                model=self._text_model,
                system=SYSTEM_PROMPT_EXTRACTION,
                messages=[{"role": "user", "content": content}],
                max_tokens=16000,
                temperature=0,
            )
            raw_json = response.content[0].text if response.content else ""
            rows     = self._parse_json_response(raw_json, batch_id, "TEXT")
            usage    = response.usage
            return LLMResponse(
                batch_id=batch_id,
                rows=rows,
                input_tokens=getattr(usage, "input_tokens", 0),
                output_tokens=getattr(usage, "output_tokens", 0),
                model_used=self._text_model,
                provider_name=self.PROVIDER_NAME,
                overall_confidence=self._avg_confidence(rows),
                raw_response=raw_json,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("AnthropicProvider.extract_with_file failed: %s", exc)
            return LLMResponse(batch_id=batch_id, rows=[], error=str(exc))

    def delete_file(self, file_id: str) -> bool:
        try:
            import anthropic  # noqa: PLC0415
            client = anthropic.Anthropic(
                api_key=self._api_key,
                default_headers={"anthropic-beta": "files-api-2025-04-14"},
            )
            client.beta.files.delete(file_id)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("AnthropicProvider.delete_file failed for %s: %s", file_id, exc)
            return False

    def test_connection(self) -> bool:
        try:
            import anthropic  # noqa: PLC0415
            client = anthropic.Anthropic(api_key=self._api_key)
            response = client.messages.create(
                model=self._text_model,
                messages=[{"role": "user", "content": "Say ok"}],
                max_tokens=5,
            )
            return bool(response.content)
        except Exception as exc:  # noqa: BLE001
            logger.warning("AnthropicProvider.test_connection failed: %s", exc)
            return False

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _parse_json_response(
        raw_json: str, batch_id: str, path: str, page_offset: int = 0
    ) -> list[RawParsedRow]:
        cleaned = re.sub(r"```(?:json)?", "", raw_json).strip().rstrip("`").strip()
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.warning("AnthropicProvider: JSON parse failed: %s", exc)
            return []

        if not isinstance(data, list):
            data = data.get("transactions", data.get("rows", []))

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

            rows.append(RawParsedRow(
                batch_id=batch_id,
                source_type=SourceType.UNKNOWN,
                parser_version=f"claude/{path.lower()}",
                extraction_method=(
                    ExtractionMethod.LLM_TEXT if path == "TEXT" else ExtractionMethod.LLM_VISION
                ),
                raw_date=raw_date,
                raw_narration=str(item.get("narration", "")).strip(),
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
            ))
        return rows

    @staticmethod
    def _avg_confidence(rows: list[RawParsedRow]) -> float:
        if not rows:
            return 0.0
        return round(sum(r.row_confidence for r in rows) / len(rows), 4)



class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude 3.5 Sonnet provider adapter."""

    PROVIDER_NAME = "ANTHROPIC"
    DEFAULT_TEXT_MODEL = "claude-3-5-sonnet-20241022"
    DEFAULT_VISION_MODEL = "claude-3-5-sonnet-20241022"

    def __init__(
        self,
        api_key: str,
        text_model: str = DEFAULT_TEXT_MODEL,
        vision_model: str = DEFAULT_VISION_MODEL,
    ) -> None:
        self._api_key = api_key
        self._text_model = text_model
        self._vision_model = vision_model

    def extract_text(self, request: TextExtractionRequest) -> LLMResponse:
        logger.warning("AnthropicProvider.extract_text not yet implemented.")
        return LLMResponse(
            batch_id=request.batch_id,
            rows=[],
            model_used=self._text_model,
            provider_name=self.PROVIDER_NAME,
            error="Anthropic provider not yet implemented.",
        )

    def extract_vision(self, request: VisionExtractionRequest) -> LLMResponse:
        logger.warning("AnthropicProvider.extract_vision not yet implemented.")
        return LLMResponse(
            batch_id=request.batch_id,
            rows=[],
            model_used=self._vision_model,
            provider_name=self.PROVIDER_NAME,
            error="Anthropic provider not yet implemented.",
        )

    def test_connection(self) -> bool:
        return False
