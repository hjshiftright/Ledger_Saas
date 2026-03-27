"""SM-J Smart AI Processing — full AI-powered pipeline.

Combines SM-C parsing, SM-D LLM extraction, SM-E normalization,
SM-F dedup, SM-G categorization, SM-H confidence, and SM-I proposals
in a single orchestrated pipeline call.

For low-confidence rows (band = RED), optionally uses LLM to re-extract
or suggest a better categorization.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from core.models.enums import ConfidenceBand
from core.models.raw_parsed_row import RawParsedRow
from services.categorize_service import CategorizeService
from services.confidence_service import ConfidenceService
from services.dedup_service import DedupService
from services.normalize_service import NormalizeService, NormalizedTransaction
from services.proposal_service import ProposalBatchResult, ProposalService

if TYPE_CHECKING:
    from modules.llm.base import BaseLLMProvider

logger = logging.getLogger(__name__)


@dataclass
class SmartProcessingOptions:
    use_llm: bool = False
    llm_provider: "BaseLLMProvider | None" = None  # Resolved provider instance
    llm_provider_id: str | None = None             # Legacy: env-default lookup (ignored if llm_provider set)
    llm_for_red_band_only: bool = True             # Only call LLM for RED-band rows
    bank_account_id: str = "1102"                  # CoA account_id (DB row) for the source account
    source_account_code: str = "1102"              # CoA code for journal entries (1102=Bank, 2100=CC)
    source_account_name: str = "Savings Account"   # Display name for journal entry lines
    source_account_class: str = "ASSET"            # Account class: ASSET|LIABILITY|EQUITY|INCOME|EXPENSE
    account_id: str = ""                           # Account for dedup hash
    db_hashes: set[str] | None = None              # committed txn hashes from DB (for cross-session dedup)
    session: object = None                         # SQLAlchemy Session (passed for DB-backed services)


@dataclass
class SmartPipelineResult:
    batch_id: str
    raw_rows_count: int = 0
    normalized_count: int = 0
    new_count: int = 0
    duplicate_count: int = 0
    llm_enhanced_count: int = 0
    green_count: int = 0
    yellow_count: int = 0
    red_count: int = 0
    proposals: ProposalBatchResult | None = None
    normalized_rows: list[NormalizedTransaction] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class SmartProcessor:
    """SM-J: Full AI-powered pipeline orchestrator."""

    def __init__(self) -> None:
        self._normalize = NormalizeService()
        self._dedup     = DedupService()
        self._categorize = CategorizeService()
        self._confidence = ConfidenceService()
        self._propose   = ProposalService()

    async def process_batch(
        self,
        user_id: str,
        batch_id: str,
        raw_rows: list[RawParsedRow],
        options: SmartProcessingOptions | None = None,
    ) -> SmartPipelineResult:
        opts   = options or SmartProcessingOptions()
        result = SmartPipelineResult(batch_id=batch_id, raw_rows_count=len(raw_rows))

        # Stage 1: Normalize (SM-E)
        norm_result = self._normalize.normalize_batch(batch_id, raw_rows)
        result.normalized_count = norm_result.rows_normalized
        result.warnings.extend(norm_result.warnings)
        rows = norm_result.rows

        # Stage 2: Dedup (SM-F)
        dedup_result = self._dedup.dedup_batch(
            user_id=user_id, batch_id=batch_id, account_id=opts.account_id,
            rows=rows, db_hashes=opts.db_hashes,
        )
        result.new_count       = dedup_result.txn_new
        result.duplicate_count = dedup_result.txn_duplicate
        rows = dedup_result.new

        # Stage 3: Categorize (SM-G)
        await self._categorize.categorize_batch(batch_id=batch_id, rows=rows, session=opts.session)

        # Stage 4: Confidence (SM-H)
        conf_result = self._confidence.score_batch(batch_id=batch_id, rows=rows)
        result.green_count  = conf_result.green_count
        result.yellow_count = conf_result.yellow_count
        result.red_count    = conf_result.red_count

        # Stage 5 (optional): LLM enhancement for RED rows (SM-J §5)
        if opts.use_llm and opts.llm_provider is not None:
            red_rows = (
                [r for r in rows if r.extra_fields.get("confidence_band") == ConfidenceBand.RED.value]
                if opts.llm_for_red_band_only
                else rows
            )
            logger.info(
                "LLM stage: provider=%s, total_rows=%d, red_rows=%d, llm_for_red_only=%s",
                opts.llm_provider.PROVIDER_NAME, len(rows), len(red_rows), opts.llm_for_red_band_only,
            )
            if red_rows:
                enhanced = self._enhance_with_llm(
                    user_id=user_id,
                    batch_id=batch_id,
                    rows=red_rows,
                    provider=opts.llm_provider,
                )
                result.llm_enhanced_count = len(enhanced)
            else:
                logger.info("LLM stage: skipped — no RED band rows to enhance")
        else:
            logger.info(
                "LLM stage: skipped — use_llm=%s, provider_set=%s",
                opts.use_llm, opts.llm_provider is not None,
            )

        # Stage 6: Generate journal entry proposals (SM-I)
        proposals = self._propose.propose_batch(
            batch_id=batch_id,
            bank_account_id=opts.bank_account_id,
            rows=rows,
            source_account_code=opts.source_account_code,
            source_account_name=opts.source_account_name,
            source_account_class=opts.source_account_class,
        )
        result.proposals      = proposals
        result.normalized_rows = rows
        return result

    # Max rows per LLM categorize call — keeps the JSON response well within token limits.
    _CATEGORIZE_CHUNK = 20

    def _enhance_with_llm(
        self,
        user_id: str,
        batch_id: str,
        rows: list[NormalizedTransaction],
        provider: "BaseLLMProvider",
    ) -> list[NormalizedTransaction]:
        """Re-categorize low-confidence rows using LLM.

        Rows are sent in chunks of _CATEGORIZE_CHUNK so the JSON response never
        exceeds the model's output-token limit.  Each chunk is an independent LLM
        call; results are merged back by absolute row index.
        """
        enhanced: list[NormalizedTransaction] = []
        for chunk_start in range(0, len(rows), self._CATEGORIZE_CHUNK):
            chunk = rows[chunk_start : chunk_start + self._CATEGORIZE_CHUNK]
            enhanced.extend(
                self._enhance_chunk_with_llm(user_id, batch_id, chunk, provider, chunk_start)
            )
        return enhanced

    def _enhance_chunk_with_llm(
        self,
        user_id: str,
        batch_id: str,
        rows: list[NormalizedTransaction],
        provider: "BaseLLMProvider",
        index_offset: int = 0,
    ) -> list[NormalizedTransaction]:
        """Send one chunk of rows to the LLM and apply results.

        TXN indices in the prompt are 0-based within the chunk; `index_offset` is
        added when logging only (not needed for matching since rows align 1:1).
        Falls back to a +0.15 confidence bump if the LLM call fails.
        """
        from modules.llm.base import TextExtractionRequest  # noqa: PLC0415

        context_lines = [f"TXN_{i}: {r.narration}" for i, r in enumerate(rows)]
        req = TextExtractionRequest(
            batch_id=batch_id,
            source_type="CATEGORIZE",
            partial_text="\n".join(context_lines),
            page_count=1,
            extra_context={"mode": "categorize", "user_id": user_id},
        )

        enhanced: list[NormalizedTransaction] = []
        try:
            response = provider.extract_text(req)

            # Build lookup: chunk-local index → LLM row.
            # raw_narration is either "TXN_3" (new id-only format) or
            # "TXN_3: <narration>" (old echo format) — both handled.
            llm_by_idx: dict[int, object] = {}
            for llm_row in response.rows:
                try:
                    token = llm_row.raw_narration.split(":")[0].strip()  # "TXN_3"
                    idx = int(token.split("_")[1])
                    llm_by_idx[idx] = llm_row
                except (IndexError, ValueError):
                    pass

            for i, row in enumerate(rows):
                old_conf = float(row.extra_fields.get("category_confidence", 0.0))
                if i in llm_by_idx:
                    llm_row = llm_by_idx[i]
                    current_category = row.extra_fields.get("category", "")
                    suggested = llm_row.extra_fields.get("category_code") or current_category
                    row.extra_fields["category"] = suggested
                    row.extra_fields["llm_suggested_category"] = suggested
                    new_conf = min(0.95, max(old_conf + 0.15, float(llm_row.row_confidence)))  # type: ignore[union-attr]
                else:
                    new_conf = min(0.95, old_conf + 0.15)

                row.extra_fields["category_confidence"] = new_conf
                row.extra_fields["category_method"] = "llm"
                row.extra_fields["llm_enhanced"] = True
                enhanced.append(row)
                logger.debug(
                    "LLM enhanced row %d: confidence %.2f → %.2f",
                    index_offset + i, old_conf, new_conf,
                )

        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "LLM categorisation call failed for batch %s (offset %d): %s",
                batch_id, index_offset, exc,
            )
            for row in rows:
                old_conf = float(row.extra_fields.get("category_confidence", 0.0))
                row.extra_fields["category_confidence"] = min(0.95, old_conf + 0.15)
                row.extra_fields["category_method"] = "llm_fallback"
                row.extra_fields["llm_enhanced"] = True
                enhanced.append(row)

        return enhanced
