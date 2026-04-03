"""SM-I Approval Service — commit user-approved proposals to the database.

Converts ProposedJournalEntry objects (from the in-memory proposal store) into
ORM Transaction + TransactionLine rows.

Flow:
    1. Ensure an ORM ImportBatch row exists for the Pydantic batch (create if absent).
    2. For each CONFIRMED proposal (each wrapped in a NESTED savepoint):
       a. Resolve each JournalEntryLine.account_code → Account.id via AccountRepository.
       b. Skip the entire proposal if any code is unresolvable (never partially post).
       c. Build Transaction + TransactionLine; set txn_hash for idempotency.
       d. If an unexpected exception occurs, roll back to the savepoint only —
          other already-committed proposals are unaffected.
    3. Update ImportBatch status to COMPLETED.

Propagation:
    Each proposal runs inside transactional(Propagation.NESTED).  A failure in
    proposal N rolls back only that savepoint; proposals 1…N-1 remain intact
    in the outer transaction.  The outer transaction is committed by the FastAPI
    route handler (via get_tenant_db() teardown).
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models.import_batch import ImportBatch as PydanticBatch
from db.models.imports import ImportBatch as OrmImportBatch
from db.models.transactions import Transaction, TransactionLine
from db.transaction import Propagation, transactional
from repositories.sqla_account_repo import AccountRepository
from repositories.sqla_transaction_repo import TransactionRepository
from services.proposal_service import ProposedJournalEntry


class ApprovalService:
    """Persist CONFIRMED proposals to the database."""

    def __init__(self, session: AsyncSession, tenant_id: str):
        self._session = session
        self._tenant_id = uuid.UUID(tenant_id)
        self._tx_repo = TransactionRepository(session)
        self._acc_repo = AccountRepository(session)

    # ── Public API ───────────────────────────────────────────────────────────

    async def commit_proposals(
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
        orm_batch = await self._ensure_orm_batch(pydantic_batch)

        committed_ids: list[int] = []
        skipped: list[str] = []
        already_posted: int = 0

        for proposal in proposals:
            if proposal.status != "CONFIRMED":
                continue

            # Idempotency check outside the savepoint — read-only, safe.
            if proposal.txn_hash and await self._tx_repo.find_by_hash(proposal.txn_hash):
                already_posted += 1
                continue

            # Each proposal gets its own SAVEPOINT.  A failure (unresolvable
            # account code, constraint violation, etc.) rolls back only this
            # savepoint; previously committed proposals are unaffected.
            try:
                async with transactional(Propagation.NESTED):
                    tx = await self._commit_one(proposal, orm_batch.id)
                    if tx:
                        committed_ids.append(tx.id)
                    else:
                        skipped.append(proposal.proposal_id)
            except Exception:
                # _commit_one returns None for unresolvable accounts (no raise),
                # but unexpected DB exceptions must also be caught here so the
                # outer session remains usable.
                skipped.append(proposal.proposal_id)

        # Update batch status
        orm_batch.status = "COMPLETED"
        orm_batch.row_count = len(committed_ids)
        await self._session.flush()

        return {
            "orm_batch_id": orm_batch.id,
            "committed": len(committed_ids),
            "skipped": len(skipped),
            "already_posted": already_posted,
            "transaction_ids": committed_ids,
        }

    # ── Internal ─────────────────────────────────────────────────────────────

    async def _ensure_orm_batch(self, pb: PydanticBatch) -> OrmImportBatch:
        """Return existing ORM ImportBatch for this Pydantic batch, or create one."""
        stmt = select(OrmImportBatch).where(OrmImportBatch.batch_id == pb.batch_id)
        existing = await self._session.scalar(stmt)
        if existing:
            return existing

        orm = OrmImportBatch(
            tenant_id=self._tenant_id,
            batch_id=pb.batch_id,
            filename=pb.filename,
            file_hash=pb.file_hash,
            source_type=pb.source_type.value if pb.source_type else "UNKNOWN",
            format=pb.format.value if pb.format else "CSV",
            status="PROCESSING",
            row_count=pb.txn_found,
        )
        self._session.add(orm)
        await self._session.flush()
        return orm

    async def _commit_one(
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
            acc = await self._acc_repo.find_by_code(line.account_code)
            if not acc:
                return None  # unresolvable → skip entire proposal
            if line.debit > 0:
                resolved.append((acc.id, "DEBIT", line.debit))
            if line.credit > 0:
                resolved.append((acc.id, "CREDIT", line.credit))

        if len(resolved) < 2:
            return None

        tx = Transaction(
            tenant_id=self._tenant_id,
            transaction_date=proposal.txn_date,
            transaction_type="IMPORT",
            description=proposal.narration,
            reference_number=proposal.reference,
            status="CONFIRMED",
            import_batch_id=import_batch_id,
            txn_hash=proposal.txn_hash,
        )
        for acc_id, line_type, amount in resolved:
            tx.lines.append(TransactionLine(
                tenant_id=self._tenant_id,
                account_id=acc_id,
                line_type=line_type,
                amount=amount,
            ))

        await self._tx_repo.create_with_children(tx)
        return tx
