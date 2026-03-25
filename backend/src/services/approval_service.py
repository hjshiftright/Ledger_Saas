"""SM-I Approval Service — commit user-approved proposals to SQLite.

Converts ProposedJournalEntry objects (from the in-memory proposal store) into
ORM Transaction + TransactionLine + ReconciliationRecord rows.

Flow:
    1. Ensure an ORM ImportBatch row exists for the Pydantic batch (create if absent).
    2. For each CONFIRMED proposal:
       a. Resolve each JournalEntryLine.account_code → Account.id via AccountRepository.
       b. Skip the entire proposal if any code is unresolvable (never partially post).
       c. Build Transaction + TransactionLine; set txn_hash for idempotency.
       d. Create a ReconciliationRecord linking the raw row to the new Transaction.
    3. Update ImportBatch counters and mark COMPLETED.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.models.import_batch import ImportBatch as PydanticBatch
from db.models.imports import ImportBatch as OrmImportBatch, ReconciliationRecord
from db.models.transactions import Transaction, TransactionLine
from repositories.sqla_account_repo import AccountRepository
from repositories.sqla_transaction_repo import TransactionRepository
from services.proposal_service import ProposedJournalEntry


class ApprovalService:
    """Persist CONFIRMED proposals to the SQLite database."""

    def __init__(self, session: Session):
        self._session = session
        self._tx_repo = TransactionRepository(session)
        self._acc_repo = AccountRepository(session)

    # ── Public API ───────────────────────────────────────────────────────────

    def commit_proposals(
        self,
        proposals: list[ProposedJournalEntry],
        pydantic_batch: PydanticBatch,
    ) -> dict:
        """Persist all CONFIRMED proposals for one batch.

        Returns:
            {
                "orm_batch_id": int,
                "committed": int,
                "skipped": int,
                "already_posted": int,
                "transaction_ids": list[int],
            }
        """
        orm_batch = self._ensure_orm_batch(pydantic_batch)

        committed_ids: list[int] = []
        skipped: list[str] = []
        already_posted: int = 0

        for proposal in proposals:
            if proposal.status != "CONFIRMED":
                continue

            # Idempotency: skip if this hash was already committed
            if proposal.txn_hash and self._tx_repo.find_by_hash(proposal.txn_hash):
                already_posted += 1
                continue

            tx = self._commit_one(proposal, orm_batch.id)
            if tx:
                committed_ids.append(tx.id)
            else:
                skipped.append(proposal.proposal_id)

        # Update batch counters
        orm_batch.imported_count = len(committed_ids)
        orm_batch.skipped_count = (orm_batch.skipped_count or 0) + len(skipped)
        orm_batch.status = "COMPLETED"
        orm_batch.import_completed_at = datetime.utcnow()
        self._session.flush()

        return {
            "orm_batch_id": orm_batch.id,
            "committed": len(committed_ids),
            "skipped": len(skipped),
            "already_posted": already_posted,
            "transaction_ids": committed_ids,
        }

    # ── Internal ─────────────────────────────────────────────────────────────

    def _ensure_orm_batch(self, pb: PydanticBatch) -> OrmImportBatch:
        """Return existing ORM ImportBatch for this Pydantic batch, or create one."""
        stmt = select(OrmImportBatch).where(OrmImportBatch.batch_id == pb.batch_id)
        existing = self._session.scalar(stmt)
        if existing:
            return existing

        orm = OrmImportBatch(
            batch_id=pb.batch_id,
            file_name=pb.filename,
            file_hash=pb.file_hash,
            source_type=pb.source_type.value if pb.source_type else "UNKNOWN",
            import_started_at=pb.created_at,
            status="IN_PROGRESS",
            total_records=pb.txn_found,
            duplicate_count=pb.txn_duplicate,
        )
        self._session.add(orm)
        self._session.flush()
        return orm

    def _commit_one(
        self,
        proposal: ProposedJournalEntry,
        import_batch_id: int,
    ) -> Transaction | None:
        """Map one CONFIRMED proposal to ORM rows.

        Returns None (and skips DB writes) if:
        - proposal has no date or is not balanced
        - any account code cannot be resolved to an Account row
        """
        if not proposal.is_balanced or proposal.txn_date is None:
            return None

        # Resolve every account code to an integer id; abort if any is missing
        resolved: list[tuple[int, str, Decimal]] = []  # (account_id, line_type, amount)
        for line in proposal.lines:
            acc = self._acc_repo.find_by_code(line.account_code)
            if not acc:
                return None  # unresolvable → skip entire proposal
            if line.debit > 0:
                resolved.append((acc.id, "DEBIT", line.debit))
            if line.credit > 0:
                resolved.append((acc.id, "CREDIT", line.credit))

        if len(resolved) < 2:
            return None

        tx = Transaction(
            transaction_date=proposal.txn_date,
            transaction_type="IMPORT",
            description=proposal.narration,
            reference_number=proposal.reference,
            status="CONFIRMED",
            import_batch_id=import_batch_id,
            txn_hash=proposal.txn_hash,  # SHA-256 dedup fingerprint
        )
        for acc_id, line_type, amount in resolved:
            tx.lines.append(TransactionLine(
                account_id=acc_id,
                line_type=line_type,
                amount=amount,
            ))

        self._tx_repo.create_with_children(tx)

        # ReconciliationRecord — raw import row ↔ committed transaction
        recon = ReconciliationRecord(
            import_batch_id=import_batch_id,
            external_date=proposal.txn_date,
            external_description=proposal.narration[:500],
            external_amount=proposal.total_amount,
            external_reference=proposal.reference,
            match_status="CREATED",
            created_transaction_id=tx.id,
            confidence_score=Decimal(str(round(proposal.overall_confidence, 4))),
            processed_at=datetime.utcnow(),
        )
        self._session.add(recon)

        return tx
