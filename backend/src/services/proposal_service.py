"""SM-I Transaction Proposal — generate double-entry journal entry proposals.

DR/CR assignment is derived directly from the account-class table:

  Account class       | Normal (increasing) side | Decreasing side
  ──────────────────────────────────────────────────────────────────
  ASSET, EXPENSE      | Debit  (DR)              | Credit (CR)
  LIABILITY, EQUITY,  | Credit (CR)              | Debit  (DR)
  INCOME              |                          |

For the SOURCE account the parser's ``is_debit`` flag encodes directionality:
  - ASSET source,     is_debit=True  → withdrawal   → asset DECREASES     → CR source
  - ASSET source,     is_debit=False → deposit       → asset INCREASES     → DR source
  - LIABILITY source, is_debit=True  → purchase      → liability INCREASES → CR source
  - LIABILITY source, is_debit=False → refund/payment→ liability DECREASES → DR source

Both map to the same compact rule: is_debit=True → CR source, False → DR source.
The counterpart always takes the opposite side to keep sum(DR) == sum(CR).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from core.models.enums import ConfidenceBand
from core.models.coa_categories import CATEGORY_TO_ACCOUNT, DEFAULT_COUNTERPART
from services.normalize_service import NormalizedTransaction

# ── Models ────────────────────────────────────────────────────────────────────

@dataclass
class JournalEntryLine:
    account_id: str             # CoA account_id (may be code if not yet mapped)
    account_code: str           # Short code: "5100", "1102", etc.
    account_name: str
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")
    is_inferred: bool = True    # False = confirmed by user


@dataclass
class ProposedJournalEntry:
    """A balanced double-entry proposal awaiting user confirmation."""

    proposal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    batch_id: str = ""
    row_id: str = ""
    txn_date: date | None = None
    narration: str = ""
    reference: str | None = None

    lines: list[JournalEntryLine] = field(default_factory=list)
    overall_confidence: float = 0.0
    confidence_band: str = ConfidenceBand.RED.value
    status: str = "PENDING"     # PENDING | CONFIRMED | REJECTED | REVISED
    # Dedup fingerprint carried from DedupService (SHA-256); written to Transaction.txn_hash on commit
    txn_hash: str | None = None

    @property
    def is_balanced(self) -> bool:
        return sum(l.debit for l in self.lines) == sum(l.credit for l in self.lines)

    @property
    def total_amount(self) -> Decimal:
        return sum(l.debit for l in self.lines if l.debit > 0)


@dataclass
class ProposalBatchResult:
    batch_id: str
    proposals: list[ProposedJournalEntry] = field(default_factory=list)
    unproposable: list[str] = field(default_factory=list)   # row_ids that had no mapping


# Category → CoA mapping imported from the single source of truth.
# See core/models/coa_categories.py — codes match POST /api/v1/accounts/provision-defaults.
_CATEGORY_TO_ACCOUNT = CATEGORY_TO_ACCOUNT

# Default source account — used when none is specified in the pipeline request.
_DEFAULT_SOURCE_CODE  = "1102"
_DEFAULT_SOURCE_NAME  = "Savings Account"
_DEFAULT_SOURCE_CLASS = "ASSET"

# Account classes where DR is the *increasing* (normal) side.
# Complement (LIABILITY, EQUITY, INCOME) → CR is the normal side.
_DR_NORMAL_CLASSES = frozenset({"ASSET", "EXPENSE"})


def _account_class_from_code(code: str) -> str:
    """Derive account class from CoA code prefix.
    1xxx=ASSET | 2xxx=LIABILITY | 3xxx=EQUITY | 4xxx=INCOME | 5xxx=EXPENSE
    """
    return {
        "1": "ASSET", "2": "LIABILITY", "3": "EQUITY",
        "4": "INCOME", "5": "EXPENSE",
    }.get(code[:1], "ASSET")


class ProposalService:
    """SM-I: Generate double-entry proposal for each NormalizedTransaction."""

    def propose_batch(
        self,
        batch_id: str,
        bank_account_id: str,
        rows: list[NormalizedTransaction],
        source_account_code: str = _DEFAULT_SOURCE_CODE,
        source_account_name: str = _DEFAULT_SOURCE_NAME,
        source_account_class: str = _DEFAULT_SOURCE_CLASS,
    ) -> ProposalBatchResult:
        result = ProposalBatchResult(batch_id=batch_id)
        for row in rows:
            proposal = self._propose_row(
                batch_id, bank_account_id, row,
                source_account_code, source_account_name, source_account_class,
            )
            if proposal:
                result.proposals.append(proposal)
            else:
                result.unproposable.append(row.row_id)
        return result

    def _propose_row(
        self,
        batch_id: str,
        bank_account_id: str,
        row: NormalizedTransaction,
        source_account_code: str = _DEFAULT_SOURCE_CODE,
        source_account_name: str = _DEFAULT_SOURCE_NAME,
        source_account_class: str = _DEFAULT_SOURCE_CLASS,
    ) -> ProposedJournalEntry | None:
        if row.txn_date is None or row.amount <= 0:
            return None

        category    = row.extra_fields.get("category", "EXPENSE_OTHER")
        confidence  = float(row.extra_fields.get("overall_confidence", row.row_confidence))
        band        = row.extra_fields.get("confidence_band", ConfidenceBand.RED.value)
        counterpart = _CATEGORY_TO_ACCOUNT.get(category, DEFAULT_COUNTERPART)
        amount      = row.amount.quantize(Decimal("0.01"))

        # ── DR/CR from the account-class table ───────────────────────────────
        # ASSET/EXPENSE: DR increases | LIABILITY/EQUITY/INCOME: CR increases
        #
        # Step 1 — does the source account increase or decrease?
        #   ASSET (is_dr_normal=True):  is_debit=True  → withdrawal → DECREASES
        #                               is_debit=False → deposit    → INCREASES
        #   LIABILITY (is_dr_normal=False): is_debit=True  → purchase  → INCREASES
        #                                  is_debit=False → refund    → DECREASES
        #   General:  source_increases = (is_debit XOR is_dr_normal)
        #
        # Step 2 — place source on its normal side if increasing, opposite if decreasing:
        #   src_on_dr = (source_increases == is_dr_normal)
        #             = ((is_debit != is_dr_normal) == is_dr_normal)
        #             = not is_debit   ← identical for all account classes
        #
        # Step 3 — counterpart always takes the opposite side (sum DR == sum CR).
        src_is_dr_normal = source_account_class in _DR_NORMAL_CLASSES
        source_increases = row.is_debit != src_is_dr_normal   # XOR
        src_on_dr        = source_increases == src_is_dr_normal  # == not row.is_debit
        ctr_on_dr        = not src_on_dr

        lines = [
            JournalEntryLine(
                account_id=bank_account_id, account_code=source_account_code,
                account_name=source_account_name,
                debit =amount if src_on_dr else Decimal("0"),
                credit=amount if not src_on_dr else Decimal("0"),
            ),
            JournalEntryLine(
                account_id=counterpart[0], account_code=counterpart[0],
                account_name=counterpart[1],
                debit =amount if ctr_on_dr else Decimal("0"),
                credit=amount if not ctr_on_dr else Decimal("0"),
            ),
        ]

        return ProposedJournalEntry(
            batch_id=batch_id,
            row_id=row.row_id,
            txn_date=row.txn_date,
            narration=row.narration,
            reference=row.reference,
            lines=lines,
            overall_confidence=confidence,
            confidence_band=band,
            txn_hash=row.extra_fields.get("txn_hash"),
        )
