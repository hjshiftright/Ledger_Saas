"""Persistence model for a finalised, approved Transaction.

A Transaction is created when the user confirms a ProposedJournalEntry.
It is the immutable ledger record — double-entry balanced and approved.

Note: No database layer is wired yet. These models represent the schema
contract for future persistence (SQL / document store / event store).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from core.models.enums import SourceType, TxnTypeHint


@dataclass
class JournalLine:
    """A single debit or credit line in a posted journal entry."""

    account_id: str          # CoA account ID
    account_code: str        # Short ledger code, e.g. "5100"
    account_name: str
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")

    @property
    def is_balanced_zero(self) -> bool:
        return self.debit == Decimal("0") or self.credit == Decimal("0")


@dataclass
class Transaction:
    """Finalised, user-approved double-entry transaction.

    One Transaction = one balanced journal entry (sum(debits) == sum(credits)).
    Created when the user confirms a ProposedJournalEntry from SM-I.
    """

    txn_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    account_id: str = ""          # Primary bank / investment account CoA ID
    batch_id: str = ""            # Source batch from the parsing pipeline

    txn_date: date | None = None
    narration: str = ""
    reference: str | None = None

    # Signed amount: negative = net debit (outflow), positive = net credit (inflow)
    amount: Decimal = Decimal("0")
    is_debit: bool = True

    txn_type: str = TxnTypeHint.UNKNOWN.value
    category_code: str = ""
    confidence: float = 0.0

    source_type: SourceType = SourceType.UNKNOWN
    journal_lines: list[JournalLine] = field(default_factory=list)

    # Provenance / audit
    original_proposal_id: str = ""   # Links back to ProposedJournalEntry.proposal_id
    approved_at: datetime | None = None
    approved_by: str | None = None   # user_id of the approver (None = auto-approved)

    created_at: datetime = field(default_factory=datetime.utcnow)
    extra_fields: dict[str, Any] = field(default_factory=dict)

    @property
    def is_balanced(self) -> bool:
        total_debit  = sum(l.debit  for l in self.journal_lines)
        total_credit = sum(l.credit for l in self.journal_lines)
        return total_debit == total_credit
