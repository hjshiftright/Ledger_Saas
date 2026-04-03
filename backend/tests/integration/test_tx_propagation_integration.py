"""Integration tests for transaction propagation against real PostgreSQL.

Uses the postgres_engine testcontainer fixture from conftest.py.
Each test gets a function-scoped session factory via tx_session_factory.

These tests prove that SAVEPOINT, ROLLBACK TO SAVEPOINT, and independent
sessions work correctly in the actual asyncpg + SQLAlchemy 2.0 stack.
"""
from __future__ import annotations

import uuid
from datetime import date
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from db.transaction import (
    Propagation,
    TransactionContext,
    _active_tx,
    transactional,
    get_active_transaction,
)
from db.models.transactions import Transaction

TEST_TENANT = uuid.UUID("00000000-0000-0000-0000-000000000099")
TEST_USER = "99"


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def pg_session(tx_session_factory) -> AsyncSession:
    """Open a session with RLS context + ambient TransactionContext.

    Rolls back after each test to leave the DB clean.
    """
    async with tx_session_factory() as session:
        await session.execute(
            text(
                "SELECT set_config('app.tenant_id', :tid, TRUE),"
                "       set_config('app.user_id',   :uid, TRUE)"
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


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_transaction(tenant_id: uuid.UUID, description: str) -> Transaction:
    return Transaction(
        tenant_id=tenant_id,
        transaction_date=date(2026, 1, 15),
        transaction_type="IMPORT",
        description=description,
        status="CONFIRMED",
    )


async def _count_by_description(session: AsyncSession, desc: str, tenant_id: uuid.UUID) -> int:
    r = await session.execute(
        text(
            "SELECT COUNT(*) FROM transactions"
            " WHERE description = :d AND tenant_id = :tid"
        ),
        {"d": desc, "tid": str(tenant_id)},
    )
    return r.scalar_one()


# ── NESTED savepoint — core DB behaviour ──────────────────────────────────────

class TestNestedSavepointDB:
    async def test_nested_rollback_undoes_only_inner_work(self, pg_session):
        """Outer inserts tx_A; inner (NESTED) inserts tx_B then raises.
        After: tx_A still in session; tx_B gone (rolled back to savepoint).
        """
        tx_a = _make_transaction(TEST_TENANT, "outer-tx-A")
        pg_session.add(tx_a)
        await pg_session.flush()
        outer_id = tx_a.id
        assert outer_id is not None

        with pytest.raises(ValueError, match="inner failure"):
            async with transactional(Propagation.NESTED):
                tx_b = _make_transaction(TEST_TENANT, "inner-tx-B")
                pg_session.add(tx_b)
                await pg_session.flush()
                raise ValueError("inner failure")

        # tx_A still in the session
        await pg_session.refresh(tx_a)
        assert tx_a.id == outer_id

        # tx_B rolled back
        count = await _count_by_description(pg_session, "inner-tx-B", TEST_TENANT)
        assert count == 0

    async def test_nested_success_visible_to_outer_session(self, pg_session):
        """Successful NESTED work is visible via the same session."""
        async with transactional(Propagation.NESTED):
            tx = _make_transaction(TEST_TENANT, "nested-success")
            pg_session.add(tx)
            await pg_session.flush()
            nested_id = tx.id

        r = await pg_session.execute(
            text("SELECT COUNT(*) FROM transactions WHERE id = :id"),
            {"id": nested_id},
        )
        assert r.scalar_one() == 1

    async def test_multiple_independent_savepoints(self, pg_session):
        """Three NESTED blocks: block-1 succeeds, block-2 fails, block-3 succeeds.
        Only work from blocks 1 and 3 must survive.
        """
        # Block 1
        async with transactional(Propagation.NESTED):
            t = _make_transaction(TEST_TENANT, "sp-block-1")
            pg_session.add(t)
            await pg_session.flush()

        # Block 2 — fails
        with pytest.raises(RuntimeError):
            async with transactional(Propagation.NESTED):
                t = _make_transaction(TEST_TENANT, "sp-block-2")
                pg_session.add(t)
                await pg_session.flush()
                raise RuntimeError("block 2 fails")

        # Block 3
        async with transactional(Propagation.NESTED):
            t = _make_transaction(TEST_TENANT, "sp-block-3")
            pg_session.add(t)
            await pg_session.flush()

        for desc, should_exist in [
            ("sp-block-1", True),
            ("sp-block-2", False),
            ("sp-block-3", True),
        ]:
            count = await _count_by_description(pg_session, desc, TEST_TENANT)
            assert count == (1 if should_exist else 0), (
                f"'{desc}' expected to {'exist' if should_exist else 'not exist'}"
            )

    async def test_nested_within_nested(self, pg_session):
        """Two levels of savepoints: inner-inner fails; inner survives."""
        async with transactional(Propagation.NESTED):
            t_inner = _make_transaction(TEST_TENANT, "depth-1")
            pg_session.add(t_inner)
            await pg_session.flush()

            with pytest.raises(ValueError):
                async with transactional(Propagation.NESTED):
                    t2 = _make_transaction(TEST_TENANT, "depth-2")
                    pg_session.add(t2)
                    await pg_session.flush()
                    raise ValueError("depth-2 fails")

        for desc, expected in [("depth-1", 1), ("depth-2", 0)]:
            count = await _count_by_description(pg_session, desc, TEST_TENANT)
            assert count == expected


# ── REQUIRES_NEW — independent transaction isolation ──────────────────────────

class TestRequiresNewDB:
    """REQUIRES_NEW opens a second session via SessionFactory.

    In tests we patch db.engine.SessionFactory with the testcontainer factory
    so the inner session hits the real test DB instead of the production URL.
    """

    async def test_requires_new_commits_independently(self, tx_session_factory):
        """Outer rolls back; inner REQUIRES_NEW must still be committed."""
        from unittest.mock import patch

        unique_outer = f"outer-{uuid.uuid4().hex[:8]}"
        unique_inner = f"inner-{uuid.uuid4().hex[:8]}"

        # Patch the production SessionFactory with the testcontainer one so
        # REQUIRES_NEW's _new_root_transaction opens a testcontainer session.
        with patch("db.engine.SessionFactory", tx_session_factory):
            try:
                async with tx_session_factory() as outer_session:
                    await outer_session.execute(
                        text(
                            "SELECT set_config('app.tenant_id', :tid, TRUE),"
                            "       set_config('app.user_id', :uid, TRUE)"
                        ),
                        {"tid": str(TEST_TENANT), "uid": TEST_USER},
                    )
                    outer_ctx = TransactionContext(
                        session=outer_session,
                        tenant_id=str(TEST_TENANT),
                        user_id=TEST_USER,
                        is_root=True,
                    )
                    _active_tx.set(outer_ctx)

                    # Outer work
                    tx_a = _make_transaction(TEST_TENANT, unique_outer)
                    outer_session.add(tx_a)
                    await outer_session.flush()

                    # Inner — commits independently via REQUIRES_NEW
                    async with transactional(Propagation.REQUIRES_NEW) as inner_ctx:
                        tx_b = _make_transaction(TEST_TENANT, unique_inner)
                        inner_ctx.session.add(tx_b)
                        await inner_ctx.session.flush()

                    # Simulate outer failure after inner has committed
                    raise RuntimeError("outer fails")

            except RuntimeError:
                pass

        _active_tx.set(None)

        # Verify with a fresh read session (outside the patch context)
        async with tx_session_factory() as verify:
            await verify.execute(
                text(
                    "SELECT set_config('app.tenant_id', :tid, TRUE),"
                    "       set_config('app.user_id', :uid, TRUE)"
                ),
                {"tid": str(TEST_TENANT), "uid": TEST_USER},
            )
            for desc, should_exist in [
                (unique_outer, False),
                (unique_inner, True),
            ]:
                r = await verify.execute(
                    text(
                        "SELECT COUNT(*) FROM transactions"
                        " WHERE description = :d AND tenant_id = :tid"
                    ),
                    {"d": desc, "tid": str(TEST_TENANT)},
                )
                count = r.scalar_one()
                assert count == (1 if should_exist else 0), (
                    f"'{desc}' expected to {'exist' if should_exist else 'not exist'}"
                )

    async def test_requires_new_copies_tenant_rls(self, tx_session_factory):
        """REQUIRES_NEW must re-issue SET LOCAL on the new session."""
        from unittest.mock import patch

        with patch("db.engine.SessionFactory", tx_session_factory):
            async with tx_session_factory() as outer_session:
                await outer_session.execute(
                    text(
                        "SELECT set_config('app.tenant_id', :tid, TRUE),"
                        "       set_config('app.user_id', :uid, TRUE)"
                    ),
                    {"tid": str(TEST_TENANT), "uid": TEST_USER},
                )
                outer_ctx = TransactionContext(
                    session=outer_session,
                    tenant_id=str(TEST_TENANT),
                    user_id=TEST_USER,
                    is_root=True,
                )
                _active_tx.set(outer_ctx)

                async with transactional(Propagation.REQUIRES_NEW) as inner_ctx:
                    r = await inner_ctx.session.execute(
                        text("SELECT current_setting('app.tenant_id', true)")
                    )
                    observed = r.scalar_one()
                    assert observed == str(TEST_TENANT)

                await outer_session.rollback()

        _active_tx.set(None)


# ── RLS context safety ────────────────────────────────────────────────────────

class TestRLSSafety:
    async def test_set_local_resets_after_commit(self, tx_session_factory):
        """SET LOCAL app.tenant_id must be cleared after COMMIT.

        This simulates PgBouncer recycling a server connection to a new client:
        the next transaction must NOT inherit the previous client's tenant_id.
        """
        async with tx_session_factory() as session:
            # First transaction
            await session.execute(
                text("SELECT set_config('app.tenant_id', :tid, TRUE)"),
                {"tid": str(TEST_TENANT)},
            )
            r = await session.execute(
                text("SELECT current_setting('app.tenant_id', true)")
            )
            assert r.scalar_one() == str(TEST_TENANT)
            await session.commit()

            # Second transaction — SET LOCAL must have been cleared
            r2 = await session.execute(
                text("SELECT current_setting('app.tenant_id', true)")
            )
            val = r2.scalar_one()
            assert val in ("", None), (
                f"Expected tenant_id cleared after commit, got: {val!r}"
            )

    async def test_rls_context_scoped_to_root_transaction(self, pg_session):
        """SET LOCAL set at root must be visible inside NESTED blocks."""
        async with transactional(Propagation.NESTED):
            r = await pg_session.execute(
                text("SELECT current_setting('app.tenant_id', true)")
            )
            assert r.scalar_one() == str(TEST_TENANT)
