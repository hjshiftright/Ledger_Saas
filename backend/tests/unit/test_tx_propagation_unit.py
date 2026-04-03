"""Unit tests for db/transaction.py — propagation logic without a live database.

All DB interactions are replaced with AsyncMock so these tests run in CI
without Docker / testcontainers.

TDD order (implemented in this file):
  MANDATORY → NEVER → REQUIRED → SUPPORTS → NOT_SUPPORTED →
  NESTED (no outer) → NESTED (savepoint) → REQUIRES_NEW →
  @transactional_method → ContextVar task isolation
"""
from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from db.transaction import (
    Propagation,
    TransactionContext,
    TransactionRequired,
    TransactionProhibited,
    _active_tx,
    get_active_transaction,
    transactional,
    transactional_method,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_mock_session() -> AsyncMock:
    """Return an AsyncMock that satisfies the AsyncSession interface."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.execute = AsyncMock()
    session.begin_nested = AsyncMock()
    return session


def _push_context(session=None, tenant_id="T1", user_id="1") -> TransactionContext:
    """Push a TransactionContext into _active_tx and return it."""
    ctx = TransactionContext(
        session=session or _make_mock_session(),
        tenant_id=tenant_id,
        user_id=user_id,
        is_root=True,
    )
    _active_tx.set(ctx)
    return ctx


# ── get_active_transaction ────────────────────────────────────────────────────

class TestGetActiveTransaction:
    def test_returns_none_when_no_context(self):
        assert get_active_transaction() is None

    def test_returns_context_after_set(self):
        ctx = _push_context()
        assert get_active_transaction() is ctx

    def test_returns_none_after_reset(self):
        _push_context()
        token = _active_tx.set(None)
        assert get_active_transaction() is None
        _active_tx.reset(token)


# ── MANDATORY ─────────────────────────────────────────────────────────────────

class TestMandatory:
    async def test_raises_when_no_active_transaction(self):
        with pytest.raises(TransactionRequired, match="MANDATORY"):
            async with transactional(Propagation.MANDATORY):
                pass  # pragma: no cover

    async def test_joins_when_active_transaction_exists(self):
        outer_ctx = _push_context()

        async with transactional(Propagation.MANDATORY) as ctx:
            assert ctx is outer_ctx
            assert ctx.session is outer_ctx.session

    async def test_does_not_commit_on_exit(self):
        outer_ctx = _push_context()

        async with transactional(Propagation.MANDATORY):
            pass

        outer_ctx.session.commit.assert_not_called()


# ── NEVER ─────────────────────────────────────────────────────────────────────

class TestNever:
    async def test_raises_when_inside_transaction(self):
        _push_context()

        with pytest.raises(TransactionProhibited, match="NEVER"):
            async with transactional(Propagation.NEVER):
                pass  # pragma: no cover

    async def test_yields_none_when_no_transaction(self):
        async with transactional(Propagation.NEVER) as ctx:
            assert ctx is None

    async def test_contextvar_unchanged_after_never(self):
        async with transactional(Propagation.NEVER):
            pass

        assert get_active_transaction() is None


# ── REQUIRED ──────────────────────────────────────────────────────────────────

class TestRequired:
    async def test_joins_existing_session(self):
        outer_ctx = _push_context()

        async with transactional(Propagation.REQUIRED) as ctx:
            assert ctx is outer_ctx

    async def test_does_not_commit_when_joining(self):
        outer_ctx = _push_context()

        async with transactional(Propagation.REQUIRED):
            pass

        outer_ctx.session.commit.assert_not_called()

    async def test_contextvar_unchanged_when_joining(self):
        outer_ctx = _push_context()

        async with transactional(Propagation.REQUIRED):
            inner_ctx = get_active_transaction()

        assert inner_ctx is outer_ctx

    async def test_creates_new_session_when_none(self):
        mock_session = _make_mock_session()

        with patch("db.engine.SessionFactory", return_value=mock_session):
            async with transactional(Propagation.REQUIRED, tenant_id=None) as ctx:
                assert ctx is not None
                assert ctx.is_root is True

        mock_session.commit.assert_called_once()

    async def test_rollback_on_exception_in_new_root(self):
        mock_session = _make_mock_session()

        with patch("db.engine.SessionFactory", return_value=mock_session):
            with pytest.raises(ValueError, match="boom"):
                async with transactional(Propagation.REQUIRED, tenant_id=None):
                    raise ValueError("boom")

        mock_session.rollback.assert_called_once()
        mock_session.commit.assert_not_called()

    async def test_contextvar_restored_after_new_root_exits(self):
        mock_session = _make_mock_session()

        with patch("db.engine.SessionFactory", return_value=mock_session):
            async with transactional(Propagation.REQUIRED, tenant_id=None):
                pass

        assert get_active_transaction() is None

    async def test_contextvar_restored_after_new_root_raises(self):
        mock_session = _make_mock_session()

        with patch("db.engine.SessionFactory", return_value=mock_session):
            with pytest.raises(RuntimeError):
                async with transactional(Propagation.REQUIRED, tenant_id=None):
                    raise RuntimeError("err")

        assert get_active_transaction() is None


# ── SUPPORTS ──────────────────────────────────────────────────────────────────

class TestSupports:
    async def test_joins_when_active(self):
        outer_ctx = _push_context()

        async with transactional(Propagation.SUPPORTS) as ctx:
            assert ctx is outer_ctx

    async def test_yields_none_when_no_transaction(self):
        async with transactional(Propagation.SUPPORTS) as ctx:
            assert ctx is None

    async def test_does_not_open_new_session_when_none(self):
        with patch("db.engine.SessionFactory") as mock_factory:
            async with transactional(Propagation.SUPPORTS):
                pass

            mock_factory.assert_not_called()


# ── NOT_SUPPORTED ─────────────────────────────────────────────────────────────

class TestNotSupported:
    async def test_inner_sees_no_transaction(self):
        _push_context()

        async with transactional(Propagation.NOT_SUPPORTED):
            assert get_active_transaction() is None

    async def test_outer_context_restored_after(self):
        outer_ctx = _push_context()

        async with transactional(Propagation.NOT_SUPPORTED):
            pass

        assert get_active_transaction() is outer_ctx

    async def test_outer_restored_even_on_exception(self):
        outer_ctx = _push_context()

        with pytest.raises(ValueError):
            async with transactional(Propagation.NOT_SUPPORTED):
                raise ValueError("inner error")

        assert get_active_transaction() is outer_ctx

    async def test_yields_none_when_no_outer_tx(self):
        async with transactional(Propagation.NOT_SUPPORTED) as ctx:
            assert ctx is None


# ── NESTED (no outer tx — falls back to REQUIRED) ─────────────────────────────

class TestNestedWithNoOuterTransaction:
    async def test_creates_root_when_no_ambient_tx(self):
        mock_session = _make_mock_session()

        with patch("db.engine.SessionFactory", return_value=mock_session):
            async with transactional(Propagation.NESTED, tenant_id=None) as ctx:
                assert ctx is not None
                assert ctx.is_root is True
                assert ctx.savepoint is None

        mock_session.commit.assert_called_once()

    async def test_rollback_on_failure_when_no_ambient_tx(self):
        mock_session = _make_mock_session()

        with patch("db.engine.SessionFactory", return_value=mock_session):
            with pytest.raises(RuntimeError):
                async with transactional(Propagation.NESTED, tenant_id=None):
                    raise RuntimeError("fail")

        mock_session.rollback.assert_called_once()


# ── NESTED (with outer tx — savepoint) ───────────────────────────────────────

class TestNestedSavepoint:
    async def test_uses_same_session_as_outer(self):
        outer_ctx = _push_context()
        mock_sp = AsyncMock()
        outer_ctx.session.begin_nested = AsyncMock(return_value=mock_sp)

        async with transactional(Propagation.NESTED) as ctx:
            assert ctx.session is outer_ctx.session

    async def test_begin_nested_called_once(self):
        outer_ctx = _push_context()
        mock_sp = AsyncMock()
        outer_ctx.session.begin_nested = AsyncMock(return_value=mock_sp)

        async with transactional(Propagation.NESTED):
            pass

        outer_ctx.session.begin_nested.assert_called_once()

    async def test_savepoint_committed_on_success(self):
        outer_ctx = _push_context()
        mock_sp = AsyncMock()
        outer_ctx.session.begin_nested = AsyncMock(return_value=mock_sp)

        async with transactional(Propagation.NESTED):
            pass

        mock_sp.commit.assert_called_once()
        mock_sp.rollback.assert_not_called()

    async def test_savepoint_rolled_back_on_exception(self):
        outer_ctx = _push_context()
        mock_sp = AsyncMock()
        outer_ctx.session.begin_nested = AsyncMock(return_value=mock_sp)

        with pytest.raises(ValueError, match="nested failure"):
            async with transactional(Propagation.NESTED):
                raise ValueError("nested failure")

        mock_sp.rollback.assert_called_once()
        mock_sp.commit.assert_not_called()

    async def test_outer_session_not_committed_by_nested(self):
        outer_ctx = _push_context()
        mock_sp = AsyncMock()
        outer_ctx.session.begin_nested = AsyncMock(return_value=mock_sp)

        async with transactional(Propagation.NESTED):
            pass

        outer_ctx.session.commit.assert_not_called()

    async def test_ctx_is_root_false_for_savepoint(self):
        outer_ctx = _push_context()
        mock_sp = AsyncMock()
        outer_ctx.session.begin_nested = AsyncMock(return_value=mock_sp)

        async with transactional(Propagation.NESTED) as ctx:
            assert ctx.is_root is False
            assert ctx.savepoint is mock_sp

    async def test_contextvar_restored_after_savepoint(self):
        outer_ctx = _push_context()
        mock_sp = AsyncMock()
        outer_ctx.session.begin_nested = AsyncMock(return_value=mock_sp)

        async with transactional(Propagation.NESTED):
            pass

        assert get_active_transaction() is outer_ctx

    async def test_contextvar_restored_after_savepoint_rollback(self):
        outer_ctx = _push_context()
        mock_sp = AsyncMock()
        outer_ctx.session.begin_nested = AsyncMock(return_value=mock_sp)

        with pytest.raises(RuntimeError):
            async with transactional(Propagation.NESTED):
                raise RuntimeError("roll me back")

        assert get_active_transaction() is outer_ctx


# ── REQUIRES_NEW ──────────────────────────────────────────────────────────────

class TestRequiresNew:
    async def test_opens_new_session_when_no_outer_tx(self):
        mock_session = _make_mock_session()

        with patch("db.engine.SessionFactory", return_value=mock_session):
            async with transactional(Propagation.REQUIRES_NEW, tenant_id=None) as ctx:
                assert ctx.is_root is True

        mock_session.commit.assert_called_once()

    async def test_opens_new_session_even_when_outer_tx_exists(self):
        outer_ctx = _push_context()
        inner_mock = _make_mock_session()

        with patch("db.engine.SessionFactory", return_value=inner_mock):
            async with transactional(Propagation.REQUIRES_NEW) as ctx:
                assert ctx.session is inner_mock
                assert ctx.session is not outer_ctx.session

    async def test_inner_session_committed_independently(self):
        outer_ctx = _push_context()
        inner_mock = _make_mock_session()

        with patch("db.engine.SessionFactory", return_value=inner_mock):
            async with transactional(Propagation.REQUIRES_NEW):
                pass

        inner_mock.commit.assert_called_once()
        outer_ctx.session.commit.assert_not_called()

    async def test_inner_rollback_does_not_affect_outer(self):
        outer_ctx = _push_context()
        inner_mock = _make_mock_session()

        with patch("db.engine.SessionFactory", return_value=inner_mock):
            with pytest.raises(ValueError):
                async with transactional(Propagation.REQUIRES_NEW):
                    raise ValueError("inner fails")

        inner_mock.rollback.assert_called_once()
        outer_ctx.session.rollback.assert_not_called()

    async def test_outer_context_restored_after_requires_new(self):
        outer_ctx = _push_context()
        inner_mock = _make_mock_session()

        with patch("db.engine.SessionFactory", return_value=inner_mock):
            async with transactional(Propagation.REQUIRES_NEW):
                assert get_active_transaction().session is inner_mock

        assert get_active_transaction() is outer_ctx

    async def test_outer_context_restored_even_on_inner_failure(self):
        outer_ctx = _push_context()
        inner_mock = _make_mock_session()

        with patch("db.engine.SessionFactory", return_value=inner_mock):
            with pytest.raises(RuntimeError):
                async with transactional(Propagation.REQUIRES_NEW):
                    raise RuntimeError("boom")

        assert get_active_transaction() is outer_ctx

    async def test_copies_tenant_id_from_outer_context(self):
        outer_ctx = _push_context(tenant_id="TENANT-ABC")
        inner_mock = _make_mock_session()

        with patch("db.engine.SessionFactory", return_value=inner_mock):
            async with transactional(Propagation.REQUIRES_NEW) as ctx:
                assert ctx.tenant_id == "TENANT-ABC"


# ── @transactional_method decorator ──────────────────────────────────────────

class TestTransactionalMethodDecorator:
    async def test_decorator_preserves_function_name(self):
        @transactional_method(Propagation.MANDATORY)
        async def my_method():
            """Original docstring."""
            return 42

        assert my_method.__name__ == "my_method"
        assert my_method.__doc__ == "Original docstring."

    async def test_mandatory_decorator_raises_outside_tx(self):
        @transactional_method(Propagation.MANDATORY)
        async def must_be_in_tx():
            return "ok"

        with pytest.raises(TransactionRequired):
            await must_be_in_tx()

    async def test_mandatory_decorator_passes_inside_tx(self):
        outer_ctx = _push_context()

        @transactional_method(Propagation.MANDATORY)
        async def must_be_in_tx():
            return get_active_transaction()

        result = await must_be_in_tx()
        assert result is outer_ctx

    async def test_never_decorator_raises_inside_tx(self):
        _push_context()

        @transactional_method(Propagation.NEVER)
        async def must_be_outside_tx():
            pass  # pragma: no cover

        with pytest.raises(TransactionProhibited):
            await must_be_outside_tx()

    async def test_decorator_passes_args_through(self):
        outer_ctx = _push_context()

        @transactional_method(Propagation.MANDATORY)
        async def add(a: int, b: int) -> int:
            return a + b

        result = await add(3, 4)
        assert result == 7

    async def test_nested_decorator_on_method(self):
        outer_ctx = _push_context()
        mock_sp = AsyncMock()
        outer_ctx.session.begin_nested = AsyncMock(return_value=mock_sp)

        class MyService:
            @transactional_method(Propagation.NESTED)
            async def do_work(self):
                return get_active_transaction()

        svc = MyService()
        ctx = await svc.do_work()
        assert ctx.savepoint is mock_sp

    async def test_requires_new_decorator_creates_independent_tx(self):
        outer_ctx = _push_context()
        inner_mock = _make_mock_session()

        class AuditService:
            @transactional_method(Propagation.REQUIRES_NEW)
            async def log(self):
                return get_active_transaction()

        svc = AuditService()
        with patch("db.engine.SessionFactory", return_value=inner_mock):
            ctx = await svc.log()

        assert ctx.session is inner_mock
        assert ctx.session is not outer_ctx.session


# ── ContextVar isolation across asyncio tasks ─────────────────────────────────

class TestContextVarTaskIsolation:
    async def test_child_task_inherits_parent_context(self):
        outer_ctx = _push_context(tenant_id="parent-tenant")
        result = {}

        async def child():
            result["ctx"] = get_active_transaction()

        await asyncio.create_task(child())
        assert result["ctx"] is outer_ctx

    async def test_child_task_mutation_does_not_affect_parent(self):
        outer_ctx = _push_context(tenant_id="parent-tenant")

        async def child():
            _active_tx.set(None)

        await asyncio.create_task(child())

        # Parent must still see its own context.
        assert get_active_transaction() is outer_ctx
