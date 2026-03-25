"""OpenAI GPT-4o provider for SM-D LLM Processing Module.

Supports:
  - Text extraction (gpt-4o)
  - Vision extraction (gpt-4o multimodal via image_url)
  - Files API upload + extraction by file_id
"""

from __future__ import annotations

import base64
import json
import logging
import re
import uuid

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

MAX_PAGES_PER_CALL = 10  # Vision chunks


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT-4o provider adapter.

    Supports text and vision extraction, plus the OpenAI Files API for
    direct document upload (avoids base64 re-encoding large PDFs).
    """

    PROVIDER_NAME = "OPENAI"
    DEFAULT_TEXT_MODEL   = "gpt-4o"   # gpt-4.1 also available; override via Settings
    DEFAULT_VISION_MODEL = "gpt-4o"

    def __init__(
        self,
        api_key: str,
        text_model: str   = DEFAULT_TEXT_MODEL,
        vision_model: str = DEFAULT_VISION_MODEL,
        base_url: str | None = None,
    ) -> None:
        self._api_key     = api_key
        self._text_model  = text_model
        self._vision_model = vision_model
        self._base_url    = base_url

    # ── Text extraction ───────────────────────────────────────────────────────

    def extract_text(self, request: TextExtractionRequest) -> LLMResponse:
        try:
            from openai import OpenAI  # noqa: PLC0415

            is_categorize = str(request.source_type) == "CATEGORIZE"
            client = OpenAI(api_key=self._api_key, base_url=self._base_url)
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

            response = client.chat.completions.create(
                model=self._text_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0,
                max_tokens=4096,
            )

            raw_json = response.choices[0].message.content or ""
            rows     = self._parse_json_response(raw_json, request.batch_id, "TEXT")
            usage    = response.usage

            return LLMResponse(
                batch_id=request.batch_id,
                rows=rows,
                input_tokens=getattr(usage, "prompt_tokens", 0),
                output_tokens=getattr(usage, "completion_tokens", 0),
                model_used=self._text_model,
                provider_name=self.PROVIDER_NAME,
                overall_confidence=self._avg_confidence(rows),
                raw_response=raw_json,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("OpenAIProvider.extract_text failed: %s", exc, exc_info=True)
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
                logger.error("OpenAIProvider.extract_vision chunk %d failed: %s", chunk_idx, exc)
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
        from openai import OpenAI  # noqa: PLC0415

        client = OpenAI(api_key=self._api_key, base_url=self._base_url)

        image_parts = [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{base64.b64encode(png).decode()}",
                    "detail": "high",
                },
            }
            for png in pages
        ]
        text_content = (
            "Extract all transactions from the statement page(s). "
            "Return JSON: {\"transactions\": [{\"date\", \"narration\", \"debit_amount\", "
            "\"credit_amount\", \"balance\", \"reference\", \"page_number\", \"confidence\"}]}"
        )
        if request.existing_rows_context:
            text_content += f"\n\nContext:\n{request.existing_rows_context}"

        response = client.chat.completions.create(
            model=self._vision_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_VISION},
                {"role": "user",   "content": image_parts + [{"type": "text", "text": text_content}]},
            ],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=4096,
        )
        raw_json = response.choices[0].message.content or ""
        usage    = response.usage
        rows     = self._parse_json_response(raw_json, request.batch_id, "VISION", page_offset)
        return rows, getattr(usage, "prompt_tokens", 0), getattr(usage, "completion_tokens", 0), raw_json

    # ── Files API ─────────────────────────────────────────────────────────────

    def upload_file(self, request: FileExtractionRequest) -> UploadedFile:
        """Upload a document to the OpenAI Files API (purpose=assistants)."""
        try:
            import io as _io
            from openai import OpenAI  # noqa: PLC0415

            client = OpenAI(api_key=self._api_key, base_url=self._base_url)
            file_tuple = (_io.BytesIO(request.file_bytes), request.filename)
            response = client.files.create(file=file_tuple, purpose="assistants")
            return UploadedFile(
                file_id=response.id,
                provider_name=self.PROVIDER_NAME,
                filename=request.filename,
                mime_type=request.mime_type,
                size_bytes=len(request.file_bytes),
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("OpenAIProvider.upload_file failed: %s", exc)
            raise RuntimeError(f"OpenAI file upload failed: {exc}") from exc

    def extract_with_file(
        self,
        file_id: str,
        batch_id: str,
        source_type: str,
        extra_context: dict | None = None,
    ) -> LLMResponse:
        """Extract using a previously uploaded file via Assistants vector store."""
        try:
            from openai import OpenAI  # noqa: PLC0415

            client = OpenAI(api_key=self._api_key, base_url=self._base_url)
            user_prompt = (
                f"Source type: {source_type}\n\n"
                "Extract all transactions from the attached document. "
                "Return JSON: {\"transactions\": [{\"date\", \"narration\", \"debit_amount\", "
                "\"credit_amount\", \"balance\", \"reference\", \"confidence\"}]}"
            )
            if extra_context:
                user_prompt += f"\n\nContext: {extra_context}"

            response = client.chat.completions.create(
                model=self._text_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT_EXTRACTION},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_prompt},
                            {"type": "file", "file": {"file_id": file_id}},
                        ],
                    },
                ],
                response_format={"type": "json_object"},
                temperature=0,
                max_tokens=4096,
            )
            raw_json = response.choices[0].message.content or ""
            rows     = self._parse_json_response(raw_json, batch_id, "TEXT")
            usage    = response.usage
            return LLMResponse(
                batch_id=batch_id,
                rows=rows,
                input_tokens=getattr(usage, "prompt_tokens", 0),
                output_tokens=getattr(usage, "completion_tokens", 0),
                model_used=self._text_model,
                provider_name=self.PROVIDER_NAME,
                overall_confidence=self._avg_confidence(rows),
                raw_response=raw_json,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("OpenAIProvider.extract_with_file failed: %s", exc)
            return LLMResponse(batch_id=batch_id, rows=[], error=str(exc))

    def delete_file(self, file_id: str) -> bool:
        try:
            from openai import OpenAI  # noqa: PLC0415
            client = OpenAI(api_key=self._api_key, base_url=self._base_url)
            client.files.delete(file_id)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("OpenAIProvider.delete_file failed for %s: %s", file_id, exc)
            return False

    def test_connection(self) -> bool:
        try:
            from openai import OpenAI  # noqa: PLC0415
            client = OpenAI(api_key=self._api_key, base_url=self._base_url)
            response = client.chat.completions.create(
                model=self._text_model,
                messages=[{"role": "user", "content": "Say ok"}],
                max_tokens=5,
            )
            return bool(response.choices[0].message.content)
        except Exception as exc:  # noqa: BLE001
            logger.warning("OpenAIProvider.test_connection failed: %s", exc)
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
            logger.warning("OpenAIProvider: JSON parse failed: %s", exc)
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
                parser_version=f"openai/{path.lower()}",
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

