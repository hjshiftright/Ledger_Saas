"""Persistence model for a PendingTransaction (review queue entry).

A PendingTransaction wraps a ProposedJournalEntry and tracks the user's
review decision (PENDING → APPROVED / EXCLUDED / SKIPPED).

When a user approves a PendingTransaction, the system creates a Transaction
(see core.models.transaction) and marks this record APPROVED.

Note: No database layer is wired yet. These models represent the schema
contract for future persistence.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any

from core.models.enums import ConfidenceBand, ReviewStatus
from services.proposal_service import ProposedJournalEntry


@dataclass
class PendingTransaction:
    """A proposed journal entry awaiting user review.

    Lifecycle:
        PENDING → user confirms  → APPROVED  (Transaction record created)
        PENDING → user excludes  → EXCLUDED  (skipped, not posted)
        PENDING → user defers    → SKIPPED   (re-queued for later)
        PENDING → user revises   → PENDING   (proposal updated, stays in queue)
    """

    pending_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    batch_id: str = ""

    # Embedded proposal (from SM-I)
    proposal: ProposedJournalEntry | None = None

    # Review state
    review_status: ReviewStatus = ReviewStatus.PENDING
    confidence_band: str = ConfidenceBand.RED.value

    # LLM suggestion metadata (populated by SM-J when use_llm=True)
    llm_suggested_category: str | None = None
    llm_suggestion_reasoning: str | None = None

    # User feedback
    user_notes: str | None = None
    revised_category: str | None = None   # Set when user overrides the category

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    reviewed_at: datetime | None = None   # Set when user acts on this item

    # Link to the approved Transaction (set after APPROVED)
    approved_txn_id: str | None = None

    extra_fields: dict[str, Any] = field(default_factory=dict)

    @property
    def is_actionable(self) -> bool:
        """True when this entry still requires user action."""
        return self.review_status == ReviewStatus.PENDING

    @property
    def effective_category(self) -> str | None:
        """User-revised category if set, otherwise the LLM suggestion."""
        if self.revised_category:
            return self.revised_category
        if self.llm_suggested_category:
            return self.llm_suggested_category
        return self.proposal.lines[0].account_code if self.proposal and self.proposal.lines else None
