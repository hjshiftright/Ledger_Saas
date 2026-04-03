"""Integration tests for ApprovalService with NESTED propagation.

Before: commit_proposals() had no savepoints — one bad proposal could leave the
session in an aborted state, silently dropping all subsequent proposals.

After: each proposal runs in its own transactional(Propagation.NESTED) context.
A failure rolls back only that savepoint; all other proposals are unaffected.

TDD:
  - Write tests first (RED — ApprovalService has no NESTED wrapping yet)
  - Update approval_service.py (GREEN)
  - Run full suite to confirm no regressions
"""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from db.transaction import TransactionContext, _active_tx, Propagation, transactional
from db.models.accounts import Account
from db.models.transactions import Transaction
from services.proposal_service import ProposedJournalEntry, JournalEntryLine
from services.approval_service import ApprovalService
from core.models.import_batch import ImportBatch as PydanticBatch
from core.models.enums import SourceType, FileFormat

TEST_TENANT = uuid.UUID("00000000-0000-0000-0000-000000000099")
TEST_USER = "99"


# ── Session fixture ───────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def approval_session(tx_session_factory) -> AsyncSession:
    """Session with RLS context + ambient TransactionContext, rolls back after test."""
    async with tx_session_factory() as session:
        await session.execute(
            text(
                "SELECT set_config('app.tenant_id', :tid, TRUE),"
                "       set_config('app.user_id', :uid, TRUE)"
            ),
            {"tid": str(TEST_TENANT), "uid": TEST_USER},
        )
        ctx = TransactionContext(
            session=session,
            tenant_id=str(TEST_TENANT),
            user_id=TEST_USER,
            is_root=True,
        )
        token = _active_tx.set(ctx)
        try:
            yield session
        finally:
            _active_tx.reset(token)
            await session.rollback()


# ── Account fixtures ──────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def cash_account(approval_session) -> Account:
    acc = Account(
        tenant_id=TEST_TENANT,
        code="CASH-TEST-01",
        name="Cash",
        account_type="ASSET",
        normal_balance="DEBIT",
        is_system=False,
        is_active=True,
    )
    approval_session.add(acc)
    await approval_session.flush()
    return acc


@pytest_asyncio.fixture
async def expense_account(approval_session) -> Account:
    acc = Account(
        tenant_id=TEST_TENANT,
        code="EXP-TEST-01",
        name="Expense",
        account_type="EXPENSE",
        normal_balance="DEBIT",
        is_system=False,
        is_active=True,
    )
    approval_session.add(acc)
    await approval_session.flush()
    return acc


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_pydantic_batch() -> PydanticBatch:
    return PydanticBatch(
        batch_id=str(uuid.uuid4()),
        user_id=TEST_USER,
        account_id="CASH-TEST-01",
        filename="test.csv",
        file_hash=uuid.uuid4().hex,
        source_type=SourceType.HDFC_BANK,
        format=FileFormat.CSV,
    )


def _make_proposal(
    cash_code: str,
    expense_code: str,
    amount: str = "1000.00",
    narration: str = "Test payment",
) -> ProposedJournalEntry:
    """Create a balanced CONFIRMED ProposedJournalEntry."""
    amt = Decimal(amount)
    return ProposedJournalEntry(
        proposal_id=str(uuid.uuid4()),
        txn_date=date(2026, 1, 15),
        narration=narration,
        txn_hash=uuid.uuid4().hex,
        status="CONFIRMED",
        lines=[
            JournalEntryLine(
                account_id=expense_code,
                account_code=expense_code,
                account_name="Expense",
                debit=amt,
                credit=Decimal("0"),
            ),
            JournalEntryLine(
                account_id=cash_code,
                account_code=cash_code,
                account_name="Cash",
                debit=Decimal("0"),
                credit=amt,
            ),
        ],
    )


def _make_bad_proposal(narration: str = "Bad proposal") -> ProposedJournalEntry:
    """A proposal referencing non-existent account codes — will fail resolution."""
    return ProposedJournalEntry(
        proposal_id=str(uuid.uuid4()),
        txn_date=date(2026, 1, 15),
        narration=narration,
        txn_hash=uuid.uuid4().hex,
        status="CONFIRMED",
        lines=[
            JournalEntryLine(
                account_id="NO-SUCH-CODE",
                account_code="NO-SUCH-CODE",
                account_name="Ghost",
                debit=Decimal("500"),
                credit=Decimal("0"),
            ),
            JournalEntryLine(
                account_id="ALSO-GONE",
                account_code="ALSO-GONE",
                account_name="Ghost2",
                debit=Decimal("0"),
                credit=Decimal("500"),
            ),
        ],
    )


# ── ApprovalService with NESTED savepoints ────────────────────────────────────

class TestApprovalServiceWithNested:
    async def test_all_good_proposals_committed(
        self, approval_session, cash_account, expense_account
    ):
        """Happy path: three valid proposals all commit successfully."""
        svc = ApprovalService(approval_session, str(TEST_TENANT))
        proposals = [
            _make_proposal(cash_account.code, expense_account.code,
                           narration=f"payment-{i}")
            for i in range(3)
        ]
        batch = _make_pydantic_batch()

        result = await svc.commit_proposals(proposals, batch)

        assert result["committed"] == 3
        assert result["skipped"] == 0
        assert result["already_posted"] == 0
        assert len(result["transaction_ids"]) == 3

    async def test_bad_proposal_does_not_abort_good_ones(
        self, approval_session, cash_account, expense_account
    ):
        """Mix: good, bad (unresolvable account), good.
        Expected: 2 committed, 1 skipped.
        This test is RED without NESTED savepoints in ApprovalService.
        """
        proposals = [
            _make_proposal(cash_account.code, expense_account.code,
                           narration="payment-first"),
            _make_bad_proposal(narration="payment-bad"),
            _make_proposal(cash_account.code, expense_account.code,
                           narration="payment-third"),
        ]
        batch = _make_pydantic_batch()
        svc = ApprovalService(approval_session, str(TEST_TENANT))

        result = await svc.commit_proposals(proposals, batch)

        assert result["committed"] == 2
        assert result["skipped"] == 1
        assert len(result["transaction_ids"]) == 2

    async def test_all_bad_proposals_zero_commits(
        self, approval_session, cash_account, expense_account
    ):
        proposals = [_make_bad_proposal(narration=f"bad-{i}") for i in range(3)]
        batch = _make_pydantic_batch()
        svc = ApprovalService(approval_session, str(TEST_TENANT))

        result = await svc.commit_proposals(proposals, batch)

        assert result["committed"] == 0
        assert result["skipped"] == 3

    async def test_idempotency_skips_already_posted(
        self, approval_session, cash_account, expense_account
    ):
        """Posting the same txn_hash twice must skip the second attempt."""
        proposal = _make_proposal(cash_account.code, expense_account.code)
        batch = _make_pydantic_batch()
        svc = ApprovalService(approval_session, str(TEST_TENANT))

        result1 = await svc.commit_proposals([proposal], batch)
        result2 = await svc.commit_proposals([proposal], batch)

        assert result1["committed"] == 1
        assert result2["committed"] == 0
        assert result2["already_posted"] == 1

    async def test_non_confirmed_proposals_skipped(
        self, approval_session, cash_account, expense_account
    ):
        """Proposals not in CONFIRMED status must be silently ignored."""
        proposal = _make_proposal(cash_account.code, expense_account.code)
        proposal.status = "PENDING"
        batch = _make_pydantic_batch()
        svc = ApprovalService(approval_session, str(TEST_TENANT))

        result = await svc.commit_proposals([proposal], batch)

        assert result["committed"] == 0
        assert result["skipped"] == 0

    async def test_each_confirmed_proposal_gets_own_savepoint(
        self, approval_session, cash_account, expense_account
    ):
        """begin_nested must be called once per CONFIRMED proposal."""
        proposals = [
            _make_proposal(cash_account.code, expense_account.code,
                           narration=f"sp-test-{i}")
            for i in range(4)
        ]
        batch = _make_pydantic_batch()
        svc = ApprovalService(approval_session, str(TEST_TENANT))

        original_begin_nested = approval_session.begin_nested
        call_count = 0

        async def counting_begin_nested():
            nonlocal call_count
            call_count += 1
            return await original_begin_nested()

        approval_session.begin_nested = counting_begin_nested

        await svc.commit_proposals(proposals, batch)

        assert call_count == 4

    async def test_batch_status_set_to_completed(
        self, approval_session, cash_account, expense_account
    ):
        """ImportBatch.status must be COMPLETED after commit_proposals."""
        from db.models.imports import ImportBatch as OrmBatch
        from sqlalchemy import select

        proposals = [
            _make_proposal(cash_account.code, expense_account.code)
        ]
        batch = _make_pydantic_batch()
        svc = ApprovalService(approval_session, str(TEST_TENANT))

        result = await svc.commit_proposals(proposals, batch)

        orm_batch = await approval_session.scalar(
            select(OrmBatch).where(OrmBatch.id == result["orm_batch_id"])
        )
        assert orm_batch is not None
        assert orm_batch.status == "COMPLETED"

    async def test_many_bad_then_good_all_skipped_then_committed(
        self, approval_session, cash_account, expense_account
    ):
        """5 bad + 1 good: exactly 1 committed, 5 skipped."""
        proposals = [_make_bad_proposal(narration=f"bad-{i}") for i in range(5)]
        proposals.append(
            _make_proposal(cash_account.code, expense_account.code,
                           narration="the-one-good-one")
        )
        batch = _make_pydantic_batch()
        svc = ApprovalService(approval_session, str(TEST_TENANT))

        result = await svc.commit_proposals(proposals, batch)

        assert result["committed"] == 1
        assert result["skipped"] == 5


# ── Backward compatibility: unit_of_work ─────────────────────────────────────

class TestUnitOfWorkBackwardCompat:
    async def test_creates_new_transaction_when_called_without_args(self):
        from db.unit_of_work import unit_of_work
        from unittest.mock import AsyncMock, patch

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()
        mock_session.execute = AsyncMock()

        # Patch db.engine.SessionFactory — the actual attribute used by
        # _new_root_transaction via `import db.engine as _db_engine`.
        with patch("db.engine.SessionFactory", return_value=mock_session):
            async with unit_of_work() as session:
                assert session is mock_session

        mock_session.commit.assert_called_once()

    async def test_joins_passed_session_without_committing(self):
        from db.unit_of_work import unit_of_work
        from unittest.mock import AsyncMock

        external_session = AsyncMock()

        async with unit_of_work(existing_session=external_session) as session:
            assert session is external_session

        external_session.commit.assert_not_called()

    async def test_uses_ambient_contextvar_session(self, approval_session):
        from db.unit_of_work import unit_of_work

        # approval_session fixture pushes a TransactionContext into ContextVar
        async with unit_of_work() as session:
            assert session is approval_session

        # Outer context owns commit — unit_of_work must NOT commit
        # (this is verified indirectly: if it tried to commit it would error
        # because the session is still in use by the fixture)
