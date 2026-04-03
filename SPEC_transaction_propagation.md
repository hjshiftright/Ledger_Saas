# SPEC: Transaction Management with Propagation
## Ledger SaaS — SQLAlchemy 2.0 Async + PostgreSQL + PgBouncer

**Version**: 1.0  
**Date**: 2026-04-03  
**Status**: Draft — Pending Implementation

---

## 1. Executive Summary

This spec defines a transaction propagation system for the Ledger backend, modelled on the semantics of Spring's `@Transactional` annotation, adapted for Python async and the project's specific infrastructure constraints (SQLAlchemy 2.0 async, asyncpg, PgBouncer transaction-mode pooling, PostgreSQL Row-Level Security).

The current system has no propagation concept: every service method either receives a session from FastAPI DI or creates one via `unit_of_work()`. There is no way to declare "I need to run in a new independent transaction" or "I need a savepoint here so only my work can be rolled back". This spec closes that gap.

---

## 2. Current State Analysis

### 2.1 Transaction Lifecycle Today

```
HTTP Request
    │
    ▼
FastAPI DI: get_tenant_db()
    │  ┌─ SessionFactory() → AsyncSession
    │  ├─ SET LOCAL app.tenant_id = :tid   (RLS context, transaction-scoped)
    │  └─ SET LOCAL app.user_id   = :uid
    │
    ▼
Route handler receives: session: AsyncSession
    │
    ▼
Services and Repositories (session passed explicitly)
    │  ├─ BaseRepository.create()   → session.add() + session.flush()
    │  ├─ BaseRepository.update()   → session.merge() + session.flush()
    │  └─ ApprovalService           → flush() only, never commits
    │
    ▼
FastAPI DI teardown:
    ├─ No exception → session.commit()
    └─ Exception    → session.rollback()
```

### 2.2 What Exists in unit_of_work.py

```python
@asynccontextmanager
async def unit_of_work(existing_session: AsyncSession | None = None):
    if existing_session is not None:
        yield existing_session   # ← primitive REQUIRED: join if exists
        return                   # ← no commit here — caller owns commit

    session = SessionFactory()   # ← primitive REQUIRED: create if not exists
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
```

**Problems**:
- Session is passed explicitly through every call chain — no ambient access.
- Joining an existing session silently skips the `commit` — the calling code must remember who owns the commit.
- No savepoint support for partial rollbacks.
- No REQUIRES_NEW (independent inner transaction).
- No guard modes (MANDATORY / NEVER).
- No propagation of RLS context when opening a new session.

### 2.3 Infrastructure Constraints That Shape the Design

| Constraint | Impact on Transaction Design |
|---|---|
| **PgBouncer — transaction mode** | Each SQLAlchemy transaction may land on a different PostgreSQL server connection. Session-level `SET` is unsafe (leaks to next client). Only `SET LOCAL` (transaction-scoped) is safe. |
| **asyncpg `statement_cache_size=0`** | Prepared statements disabled; no impact on transaction semantics but prevents protocol errors on connection re-use. |
| **SQLAlchemy `autoflush=False`** | Services control flush timing explicitly. Must not change. |
| **asyncpg + PostgreSQL savepoints** | `SAVEPOINT` / `ROLLBACK TO SAVEPOINT` / `RELEASE SAVEPOINT` are fully supported inside a transaction. `session.begin_nested()` uses these. Safe with PgBouncer because savepoints live within a single transaction (= single server connection). |
| **PostgreSQL RLS** | `SET LOCAL app.tenant_id` must be re-issued whenever a new database transaction starts, including for REQUIRES_NEW. |
| **`expire_on_commit=False`** | Objects are not expired after commit; safe for read-after-commit patterns. |

---

## 3. Design Goals

1. **Declarative API** — services declare propagation intent with a decorator or context manager, not by passing sessions around.
2. **Backward-compatible** — existing code (FastAPI DI, direct session passing, `unit_of_work`) continues to work unchanged.
3. **RLS-safe** — any new transaction automatically inherits (or re-applies) the correct tenant context.
4. **PgBouncer-safe** — never uses session-scoped `SET`; always `SET LOCAL`.
5. **Zero magic on the happy path** — `REQUIRED` mode (the default) behaves identically to today's code.
6. **Composable** — nested calls with different propagation modes compose correctly.

---

## 4. Propagation Modes

These map directly to Spring's propagation semantics, adapted for async Python:

| Mode | No Active Transaction | Active Transaction Exists |
|---|---|---|
| **REQUIRED** (default) | Start new transaction | Join existing transaction |
| **REQUIRES_NEW** | Start new transaction | Suspend existing; start independent transaction; resume after |
| **NESTED** | Start new transaction | Create savepoint; roll back to savepoint on error |
| **SUPPORTS** | Run without transaction | Join existing transaction |
| **NOT_SUPPORTED** | Run without transaction | Suspend existing; run without transaction; resume after |
| **MANDATORY** | Raise `TransactionRequired` | Join existing transaction |
| **NEVER** | Run without transaction | Raise `TransactionProhibited` |

---

## 5. Core Components

### 5.1 `TransactionContext` — the ambient transaction state

```python
# backend/src/db/transaction.py

from __future__ import annotations
import enum
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


class Propagation(enum.Enum):
    REQUIRED      = "REQUIRED"
    REQUIRES_NEW  = "REQUIRES_NEW"
    NESTED        = "NESTED"
    SUPPORTS      = "SUPPORTS"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    MANDATORY     = "MANDATORY"
    NEVER         = "NEVER"


@dataclass
class TransactionContext:
    """Holds the ambient transaction state for the current async task."""

    session: AsyncSession
    tenant_id: str | None = None        # RLS: app.tenant_id
    user_id: str | None = None          # RLS: app.user_id
    is_root: bool = True                # True iff this context created the transaction
    savepoint: Any | None = None        # Set when NESTED mode created a savepoint


# Task-local (not coroutine-local) ContextVar.
# Child coroutines inherit the parent's value automatically.
# A new copy is made on `copy_context()`, which happens in asyncio tasks.
_active_tx: ContextVar[TransactionContext | None] = ContextVar(
    "_active_tx", default=None
)


def get_active_transaction() -> TransactionContext | None:
    """Return the ambient transaction context for the current async task, or None."""
    return _active_tx.get()
```

**Why `ContextVar`?**
Python's `contextvars.ContextVar` is the correct primitive for task-local state in async code. When asyncio creates a new task (via `asyncio.create_task()`), it automatically makes a shallow copy of the current `Context`. Coroutines called within the same task share the same `Context` — so a value set by `get_tenant_db()` is visible in services called by the same request handler, with no explicit passing required.

### 5.2 `transactional()` — the propagation context manager

```python
# backend/src/db/transaction.py  (continued)

from contextlib import asynccontextmanager
from sqlalchemy import text
from db.engine import SessionFactory


class TransactionRequired(RuntimeError):
    """Raised by MANDATORY propagation when no active transaction exists."""

class TransactionProhibited(RuntimeError):
    """Raised by NEVER propagation when an active transaction exists."""


@asynccontextmanager
async def transactional(
    propagation: Propagation = Propagation.REQUIRED,
    *,
    tenant_id: str | None = None,   # Override RLS context (rarely needed)
    user_id: str | None = None,     # Override RLS context (rarely needed)
):
    """Async context manager that implements transaction propagation semantics.

    Usage (context manager):
        async with transactional(Propagation.REQUIRES_NEW):
            await some_service.do_work()

    Usage (decorator):
        @transactional_method(Propagation.NESTED)
        async def my_service_method(self):
            ...

    The ambient session is available via get_active_transaction().session.
    """
    current = _active_tx.get()

    match propagation:

        case Propagation.REQUIRED:
            if current is not None:
                # Join: do nothing special, caller owns commit/rollback
                yield current
            else:
                # Create: open new session + transaction, set RLS, own commit
                async with _new_root_transaction(tenant_id, user_id) as ctx:
                    yield ctx

        case Propagation.REQUIRES_NEW:
            # Always open an independent session.
            # The outer session is "suspended" (still in ContextVar until we reset it).
            tid = tenant_id or (current.tenant_id if current else None)
            uid = user_id or (current.user_id if current else None)
            async with _new_root_transaction(tid, uid) as ctx:
                # Temporarily replace ambient context
                token = _active_tx.set(ctx)
                try:
                    yield ctx
                finally:
                    _active_tx.reset(token)
                    # Outer context (if any) is automatically restored by ContextVar

        case Propagation.NESTED:
            if current is None:
                # No outer tx → behave like REQUIRED (create root)
                async with _new_root_transaction(tenant_id, user_id) as ctx:
                    yield ctx
            else:
                # Create a SAVEPOINT within the existing transaction
                async with _nested_savepoint(current) as ctx:
                    yield ctx

        case Propagation.SUPPORTS:
            if current is not None:
                yield current       # Join existing
            else:
                yield None          # Run without transaction (no session from us)

        case Propagation.NOT_SUPPORTED:
            # Suspend: push None so inner code sees no transaction
            token = _active_tx.set(None)
            try:
                yield None
            finally:
                _active_tx.reset(token)

        case Propagation.MANDATORY:
            if current is None:
                raise TransactionRequired(
                    "MANDATORY propagation requires an active transaction, but none exists."
                )
            yield current

        case Propagation.NEVER:
            if current is not None:
                raise TransactionProhibited(
                    "NEVER propagation forbids calling within an active transaction."
                )
            yield None


@asynccontextmanager
async def _new_root_transaction(
    tenant_id: str | None,
    user_id: str | None,
):
    """Open a new AsyncSession, begin a transaction, set RLS context, push ContextVar."""
    session = SessionFactory()
    ctx = TransactionContext(
        session=session,
        tenant_id=tenant_id,
        user_id=user_id,
        is_root=True,
    )
    token = _active_tx.set(ctx)
    try:
        # Apply RLS if we have tenant context
        if tenant_id is not None:
            await session.execute(
                text(
                    "SELECT set_config('app.tenant_id', :tid, TRUE),"
                    "       set_config('app.user_id',   :uid, TRUE)"
                ),
                {"tid": str(tenant_id), "uid": str(user_id or "0")},
            )
        yield ctx
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        _active_tx.reset(token)
        await session.close()


@asynccontextmanager
async def _nested_savepoint(parent: TransactionContext):
    """Create a SAVEPOINT within the parent transaction."""
    sp = await parent.session.begin_nested()
    ctx = TransactionContext(
        session=parent.session,
        tenant_id=parent.tenant_id,
        user_id=parent.user_id,
        is_root=False,
        savepoint=sp,
    )
    token = _active_tx.set(ctx)
    try:
        yield ctx
        await sp.commit()       # RELEASE SAVEPOINT — makes work permanent within outer tx
    except Exception:
        await sp.rollback()     # ROLLBACK TO SAVEPOINT — only this work is undone
        raise
    finally:
        _active_tx.reset(token)
```

### 5.3 `@transactional_method` — the decorator form

```python
# backend/src/db/transaction.py  (continued)

import functools


def transactional_method(
    propagation: Propagation = Propagation.REQUIRED,
    **kwargs,
):
    """Decorator that wraps an async method with a transactional() context.

    Usage:
        class MyService:
            @transactional_method(Propagation.NESTED)
            async def create_with_savepoint(self):
                ctx = get_active_transaction()
                session = ctx.session
                ...
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kw):
            async with transactional(propagation, **kwargs):
                return await func(*args, **kw)
        return wrapper
    return decorator
```

### 5.4 Integration with FastAPI DI (`api/deps.py`)

The FastAPI dependency `get_tenant_db()` is updated to push the `TransactionContext` into the ContextVar so all services called by that request can access `get_active_transaction()`.

```python
# api/deps.py — updated get_tenant_db

async def get_tenant_db(
    token_payload: UserTokenPayload = Depends(get_current_user_payload),
) -> AsyncSession:
    """Open an async session, set RLS context, push TransactionContext into ContextVar.

    After this change, services can call get_active_transaction() instead of
    receiving the session as a constructor argument.
    """
    from db.engine import get_session_with_rls_and_context
    async for session in get_session_with_rls_and_context(
        tenant_id=token_payload.tenant_id,
        user_id=token_payload.user_id,
    ):
        yield session
```

```python
# db/engine.py — new generator that also pushes TransactionContext

from db.transaction import TransactionContext, _active_tx

async def get_session_with_rls_and_context(
    tenant_id: str,
    user_id: str = "0",
) -> AsyncSession:
    """FastAPI generator: session + RLS + ContextVar. Replaces get_session_with_context()."""
    async with SessionFactory() as session:
        await session.execute(
            text(
                "SELECT set_config('app.tenant_id', :tid, TRUE),"
                "       set_config('app.user_id',   :uid, TRUE)"
            ),
            {"tid": str(tenant_id), "uid": str(user_id)},
        )
        ctx = TransactionContext(
            session=session,
            tenant_id=tenant_id,
            user_id=user_id,
            is_root=True,
        )
        token = _active_tx.set(ctx)
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            _active_tx.reset(token)
```

### 5.5 Updated `unit_of_work.py`

The existing `unit_of_work` is rewritten as a thin alias over `transactional()`, preserving backward compatibility:

```python
# db/unit_of_work.py — backward-compatible wrapper

from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from db.transaction import transactional, get_active_transaction, Propagation


@asynccontextmanager
async def unit_of_work(existing_session: AsyncSession | None = None):
    """Backward-compatible wrapper. Prefer transactional() for new code.

    If existing_session is supplied: join it (REQUIRED semantics).
    Otherwise: use the ambient ContextVar session, or create a new one.
    """
    if existing_session is not None:
        # Legacy: caller passed session explicitly → just yield it
        yield existing_session
        return

    # New path: honour the ContextVar (REQUIRED propagation)
    async with transactional(Propagation.REQUIRED) as ctx:
        if ctx is not None:
            yield ctx.session
        else:
            yield None
```

---

## 6. Usage Examples

### 6.1 Standard service method (no change required — REQUIRED is default)

```python
class AccountService:
    async def create_account(self, data: AccountCreate) -> Account:
        ctx = get_active_transaction()
        session = ctx.session  # Ambient session from request DI
        acc = Account(**data.model_dump())
        session.add(acc)
        await session.flush()
        return acc
```

### 6.2 NESTED: Partial rollback (savepoint)

Use case: importing 50 transactions where each should be independent — one failure should not abort the whole batch.

```python
class ApprovalService:
    async def commit_proposals(self, proposals):
        committed, skipped = [], []

        for proposal in proposals:
            try:
                async with transactional(Propagation.NESTED):
                    # If _commit_one raises, ROLLBACK TO SAVEPOINT fires here.
                    # The outer transaction (and already-committed proposals) are unaffected.
                    tx = await self._commit_one(proposal)
                    committed.append(tx.id)
            except Exception as exc:
                skipped.append((proposal.proposal_id, str(exc)))

        return {"committed": len(committed), "skipped": len(skipped)}
```

### 6.3 REQUIRES_NEW: Audit log that survives rollback

Use case: write an audit entry that must be persisted even when the main transaction rolls back (e.g., a failed login attempt).

```python
class AuditService:
    @transactional_method(Propagation.REQUIRES_NEW)
    async def log_event(self, event_type: str, detail: str):
        ctx = get_active_transaction()
        entry = AuditLog(event_type=event_type, detail=detail)
        ctx.session.add(entry)
        await ctx.session.flush()
        # This commits independently of the outer transaction
```

### 6.4 MANDATORY: Repository method that must run in a caller's transaction

```python
class TransactionRepository(BaseRepository[Transaction]):
    @transactional_method(Propagation.MANDATORY)
    async def find_by_hash(self, txn_hash: str) -> Transaction | None:
        """Must be called within an active transaction — raises if called standalone."""
        ctx = get_active_transaction()
        stmt = select(Transaction).where(Transaction.txn_hash == txn_hash)
        return await ctx.session.scalar(stmt)
```

### 6.5 NEVER: Read-only analytics query (prevents accidentally running in a write tx)

```python
class ReportingService:
    @transactional_method(Propagation.NEVER)
    async def generate_snapshot(self, tenant_id: str) -> NetWorthSummary:
        """Must not run inside a write transaction — uses its own clean read connection."""
        async with transactional(Propagation.SUPPORTS):
            # Will run without tx (since NEVER guarantees no outer tx)
            ...
```

### 6.6 Composing propagation modes

```python
# Route handler — REQUIRED transaction started by FastAPI DI
async def commit_batch(batch_id: str, db: TenantDBSession):
    svc = ApprovalService()

    # Each proposal committed in its own NESTED savepoint:
    for proposal in proposals:
        async with transactional(Propagation.NESTED):
            await svc._commit_one(proposal)   # savepoint per proposal

    # Audit log in a REQUIRES_NEW transaction (independent commit):
    await audit_svc.log_event("BATCH_COMMITTED", f"batch={batch_id}")

    # Outer REQUIRED transaction commits here (via FastAPI DI teardown)
```

---

## 7. RLS Context Propagation Rules

| Propagation Mode | RLS Handling |
|---|---|
| REQUIRED (join) | Inherits outer session's `SET LOCAL` — no action needed |
| REQUIRED (new root) | Issues `SET LOCAL app.tenant_id` + `SET LOCAL app.user_id` |
| REQUIRES_NEW | Copies `tenant_id` / `user_id` from outer context; issues new `SET LOCAL` on new session |
| NESTED (savepoint) | Inherits outer session — same connection, same transaction-scoped settings |
| SUPPORTS (join) | Inherits outer session |
| SUPPORTS (no tx) | No session opened — caller uses raw queries at own risk |
| NOT_SUPPORTED | Outer session suspended — inner code has no session from this system |
| MANDATORY | Inherits outer session |
| NEVER | No session opened |

**Critical**: `SET LOCAL` (not `SET`) must always be used. With PgBouncer transaction mode, the server connection is returned to the pool on `COMMIT` or `ROLLBACK`. `SET LOCAL` variables are automatically cleared when the transaction ends, preventing tenant context leakage to the next client that reuses the same server connection.

---

## 8. Sequence Diagrams

### 8.1 NESTED savepoint within a request transaction

```
HTTP Request
  └─ FastAPI DI: get_tenant_db()
       └─ SESSION_A opened, SET LOCAL tenant_id, push TransactionContext to ContextVar
            │
            ├─ Service A: get_active_transaction() → SESSION_A
            │
            ├─ transactional(NESTED)
            │    └─ SAVEPOINT sp1
            │         ├─ Service B: get_active_transaction() → SESSION_A (same!)
            │         ├─ [error] → ROLLBACK TO SAVEPOINT sp1
            │         └─ only Service B's work undone; SESSION_A still active
            │
            └─ FastAPI DI teardown: SESSION_A.commit() or SESSION_A.rollback()
```

### 8.2 REQUIRES_NEW independent transaction

```
HTTP Request
  └─ FastAPI DI: SESSION_A opened, tenant_id=T1 pushed to ContextVar
       │
       ├─ Service A: works on SESSION_A
       │
       ├─ transactional(REQUIRES_NEW)
       │    └─ SESSION_B opened (new connection from pool)
       │         ├─ SET LOCAL app.tenant_id=T1 (copied from outer context)
       │         ├─ AuditService: works on SESSION_B
       │         ├─ SESSION_B.commit()  ← independent commit
       │         └─ SESSION_B.close()
       │    └─ ContextVar restored to SESSION_A
       │
       └─ FastAPI DI teardown: SESSION_A.commit() or rollback()
            └─ SESSION_B's data persists even if SESSION_A rolls back
```

---

## 9. File Layout

```
backend/src/
└── db/
    ├── engine.py          # Updated: get_session_with_rls_and_context() added
    ├── unit_of_work.py    # Updated: thin wrapper over transactional()
    ├── transaction.py     # NEW: Propagation, TransactionContext, transactional(),
    │                      #      transactional_method(), get_active_transaction()
    └── models/
        └── ...            # No changes

backend/src/api/
└── deps.py                # Updated: get_tenant_db() pushes TransactionContext to ContextVar

backend/src/services/
└── approval_service.py    # Updated: use NESTED for per-proposal savepoints
```

No new dependencies are required. All primitives used (`contextvars`, `sqlalchemy.ext.asyncio.AsyncSession.begin_nested`, `asynccontextmanager`) are already present.

---

## 10. Migration Path (Backward Compatibility)

### Phase 1 — Non-breaking (can ship immediately)
1. Add `db/transaction.py` with all new code.
2. Update `db/engine.py` to add `get_session_with_rls_and_context()` (additive).
3. Update `api/deps.py` to use the new generator (pushes ContextVar, session yield unchanged).
4. Update `db/unit_of_work.py` to the thin wrapper.
5. **No changes to any service or repository** — existing code continues to work.

### Phase 2 — Incremental adoption
6. Update `ApprovalService.commit_proposals()` to use `NESTED` savepoints per proposal.
7. Update `AuditService` (future) to use `REQUIRES_NEW`.
8. Repositories with strict preconditions use `MANDATORY`.

### Phase 3 — Cleanup (optional)
9. Remove explicit session passing from service constructors in favour of `get_active_transaction()`.
10. Retire `existing_session` parameter from `unit_of_work()`.

---

## 11. Implementation Feasibility Assessment

### 11.1 Per-Mode Feasibility

| Mode | Feasibility | Complexity | Notes |
|---|---|---|---|
| **REQUIRED** | ✅ Straightforward | Low | ContextVar lookup; `_new_root_transaction` already modelled after current `get_session_with_context`. |
| **REQUIRES_NEW** | ✅ Feasible | Medium | Opens second `AsyncSession` from same `SessionFactory`. Must re-issue `SET LOCAL`. Two concurrent sessions on separate connections — no deadlock risk unless they touch the same rows in conflicting order. |
| **NESTED** | ✅ Feasible | Medium | `AsyncSession.begin_nested()` → PostgreSQL `SAVEPOINT`. Fully supported in asyncpg + PgBouncer (savepoints live within one transaction = one server connection). `await sp.rollback()` → `ROLLBACK TO SAVEPOINT`. |
| **SUPPORTS** | ✅ Trivial | Low | If ContextVar has session, yield it; else yield None. Caller must handle the None case. |
| **NOT_SUPPORTED** | ✅ Feasible | Low | Push `None` to ContextVar temporarily. The outer session is not touched; it resumes after. Inner code simply cannot call DB methods that require a session. |
| **MANDATORY** | ✅ Trivial | Low | Raise if ContextVar is None. One line. |
| **NEVER** | ✅ Trivial | Low | Raise if ContextVar is not None. One line. |

### 11.2 Risk Areas

#### Risk 1: PgBouncer and REQUIRES_NEW
**Concern**: REQUIRES_NEW opens a second `AsyncSession`. If the outer session is mid-transaction and the inner session also needs the same rows, there is a risk of a deadlock.

**Mitigation**:
- Document that REQUIRES_NEW should be used for structurally independent work (audit logs, notification dispatch, metrics), not for rows shared with the outer transaction.
- REQUIRES_NEW on audit/notification tables (no row contention) is safe.
- PgBouncer's `reserve_pool_size=2` provides capacity for this burst.

#### Risk 2: NESTED savepoints and asyncpg
**Concern**: asyncpg has historically had edge cases with savepoints under `begin_nested()`.

**Analysis**: SQLAlchemy 2.0 abstracts this correctly. `session.begin_nested()` emits raw `SAVEPOINT sp1`, `RELEASE SAVEPOINT sp1`, `ROLLBACK TO SAVEPOINT sp1` — all standard PostgreSQL SQL. asyncpg passes these through without interference. Verified against SQLAlchemy changelog and asyncpg issue tracker.

**Mitigation**: Add an integration test using `testcontainers` that exercises NESTED rollback to confirm behaviour in the actual stack.

#### Risk 3: ContextVar and asyncio task boundaries
**Concern**: `asyncio.create_task()` copies the current Context, so a child task inherits the parent's `_active_tx`. If the child commits or rolls back, the parent's session state is affected.

**Mitigation**: 
- Background tasks spawned via `asyncio.create_task()` that need DB access should always use `transactional(REQUIRES_NEW)` (explicit new session) — never rely on the inherited session.
- Document this clearly in developer guidelines.
- `NOT_SUPPORTED` or `REQUIRES_NEW` are the safe choices for fire-and-forget tasks.

#### Risk 4: RLS context in REQUIRES_NEW
**Concern**: The inner session must re-apply `SET LOCAL app.tenant_id`. If `tenant_id` is `None` in the ContextVar (e.g., called from a background job without a request context), the inner session will not have RLS set and PostgreSQL's `current_setting('app.tenant_id', true)` will return `NULL`, bypassing tenant isolation.

**Mitigation**:
- `_new_root_transaction()` only issues `SET LOCAL` when `tenant_id is not None`.
- For background jobs that need DB access, `tenant_id` must be passed explicitly to `transactional()`: `async with transactional(REQUIRES_NEW, tenant_id=tenant_id)`.
- Add an assertion in `_new_root_transaction()` if the session touches tenant-scoped tables without RLS context (detectable via a read of `current_setting('app.tenant_id', true)`).

#### Risk 5: `expire_on_commit=False` + NESTED
**Concern**: After a savepoint commit (`RELEASE SAVEPOINT`), objects added in the nested scope are flushed to the database but the outer transaction has not committed. The objects are technically in an "in-progress" state.

**Analysis**: `expire_on_commit=False` means SQLAlchemy does not expire object state after the `RELEASE SAVEPOINT`. This is the correct behaviour — the data is in the DB (within the transaction) and readable by the same session. No issue.

#### Risk 6: `autoflush=False` + NESTED
**Concern**: If inner code queries for data added in the outer scope without flushing, it may not see the outer scope's additions.

**Mitigation**: This is the existing behaviour (autoflush is already False). Developers already call `await session.flush()` explicitly in repositories. No change required.

### 11.3 What Cannot Be Implemented

| Feature | Reason |
|---|---|
| **True `NOT_SUPPORTED` suspension** | We can push `None` to ContextVar, but the outer SQLAlchemy `AsyncSession` is still open in the same asyncpg connection. PostgreSQL does not have "suspend transaction" — the outer transaction remains active at the DB level. The semantics hold at the Python application level only: inner code cannot access the session. Acceptable for most use cases (e.g., calling a pure-Python utility). |
| **Cross-service distributed transactions (XA / 2PC)** | Not in scope. PostgreSQL supports prepared transactions, but this requires a separate coordination layer. |
| **Per-request transaction timeout** | PostgreSQL `statement_timeout` / `transaction_timeout` can be set via `SET LOCAL`, but this is orthogonal to propagation and can be added as a separate feature. |

### 11.4 Test Strategy

Full runnable test code is provided in **Section 13 — TDD Implementation**. Tests are organized in three layers:

| Layer | Location | DB Required | Purpose |
|---|---|---|---|
| Unit | `tests/unit/test_tx_propagation_unit.py` | No | ContextVar logic, guard modes, decorator behavior |
| Integration | `tests/integration/test_tx_propagation_integration.py` | PostgreSQL (testcontainers) | NESTED savepoints, REQUIRES_NEW isolation, RLS context |
| Service | `tests/integration/test_approval_service_propagation.py` | PostgreSQL (testcontainers) | ApprovalService with per-proposal savepoints |

TDD cycle per feature: write the failing test → implement the minimal code in `db/transaction.py` → confirm green → refactor.

---

## 12. Summary

| Concern | Decision |
|---|---|
| **Ambient session access** | `contextvars.ContextVar` (`_active_tx`) — task-local, inherited by coroutines |
| **Decorator API** | `@transactional_method(Propagation.NESTED)` wraps async methods |
| **Context manager API** | `async with transactional(Propagation.REQUIRES_NEW):` |
| **Savepoints** | `AsyncSession.begin_nested()` → PostgreSQL `SAVEPOINT` |
| **RLS safety** | Always `SET LOCAL`, re-issued on every new root transaction |
| **PgBouncer safety** | No session-scoped `SET`; savepoints safe within a transaction |
| **Backward compatibility** | 100% — Phase 1 changes are additive; existing code untouched |
| **New dependencies** | None — uses stdlib `contextvars` + existing SQLAlchemy 2.0 APIs |
| **Overall feasibility** | **High** — all modes are implementable with current stack |

The most impactful quick win is **NESTED savepoints in `ApprovalService`**: it allows 49 proposals to commit successfully even when the 50th fails, which is the correct behaviour for a batch import tool and currently not achievable without this spec.

---

## 13. TDD Implementation

This section provides the complete, runnable test suite. Follow the **Red → Green → Refactor** cycle: run the test file first (all tests fail because `db/transaction.py` does not exist), implement the feature incrementally until all tests pass, then refactor.

### 13.1 TDD Cycle Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│  For each propagation mode:                                         │
│                                                                     │
│  1. RED   — Write the test. Run pytest. Confirm ImportError or      │
│             AssertionError (not a false green).                     │
│                                                                     │
│  2. GREEN — Add the minimal code in db/transaction.py to make       │
│             that test pass. Do not touch other tests yet.           │
│                                                                     │
│  3. REFACTOR — Clean up without breaking the green test.            │
│             Then move to the next mode.                             │
│                                                                     │
│  Implementation order (least to most complex):                      │
│    MANDATORY → NEVER → REQUIRED → SUPPORTS → NOT_SUPPORTED          │
│    → NESTED → REQUIRES_NEW                                          │
└─────────────────────────────────────────────────────────────────────┘
```

### 13.2 New pytest Dependencies

Add to `backend/requirements.txt` (test extras only — no runtime impact):

```text
# already present:
pytest>=7.4.0
pytest-asyncio>=0.23.0
testcontainers[postgres]>=4.4.0

# add if missing:
pytest-cov>=4.1.0        # coverage reports
anyio[trio]>=4.0.0       # optional: alternative async backend for sanity checks
```

`pyproject.toml` / `pytest.ini` (already configured in the project — verify):

```ini
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["backend/tests"]
```

### 13.3 Shared Test Fixtures

```python
# backend/tests/conftest.py  (additions — append to existing file)
#
# These fixtures are added alongside the existing postgres_engine and
# db_session fixtures already present in the file.

import uuid
import pytest
import pytest_asyncio
from contextvars import copy_context
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

TEST_TENANT_ID = "00000000-0000-0000-0000-000000000001"
TEST_USER_ID = "1"


@pytest_asyncio.fixture
async def tx_session_factory(postgres_engine):
    """
    Returns an async_sessionmaker bound to the testcontainer engine.

    Used by propagation tests to create sessions that mirror production
    configuration: autoflush=False, expire_on_commit=False.
    """
    return async_sessionmaker(
        bind=postgres_engine,
        autoflush=False,
        expire_on_commit=False,
        class_=AsyncSession,
    )


@pytest_asyncio.fixture(autouse=True)
async def reset_active_tx():
    """
    Reset the _active_tx ContextVar before every test.

    ContextVars are task-local. pytest-asyncio runs each test in the same
    event loop task by default, so a value set in one test leaks into the
    next unless explicitly cleared. This fixture prevents that.
    """
    from db.transaction import _active_tx
    token = _active_tx.set(None)
    yield
    _active_tx.reset(token)


@pytest.fixture
def tenant_id() -> str:
    return TEST_TENANT_ID


@pytest.fixture
def user_id_str() -> str:
    return TEST_USER_ID


@pytest.fixture
def another_tenant_id() -> str:
    """A second distinct tenant UUID — used in RLS isolation tests."""
    return "00000000-0000-0000-0000-000000000002"
```

### 13.4 Layer 1 — Unit Tests (No Database)

These tests verify the ContextVar logic and guard semantics in complete isolation using a mock `AsyncSession`. No PostgreSQL connection is required.

```python
# backend/tests/unit/test_tx_propagation_unit.py
"""
Unit tests for db/transaction.py — propagation logic without a live database.

All DB interactions are replaced with AsyncMock so these tests run in CI
without Docker / testcontainers.

TDD order: MANDATORY → NEVER → REQUIRED (join) → REQUIRED (new) →
           SUPPORTS → NOT_SUPPORTED → NESTED (no outer) → REQUIRES_NEW (no outer)
"""
from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

# ── These imports will FAIL (red) until db/transaction.py is created ──────────
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
        # ContextVar default is None (reset_active_tx fixture ensures clean state)
        assert get_active_transaction() is None

    def test_returns_context_after_set(self):
        ctx = _push_context()
        assert get_active_transaction() is ctx

    def test_returns_none_after_reset(self):
        ctx = _push_context()
        token = _active_tx.set(None)
        assert get_active_transaction() is None
        _active_tx.reset(token)


# ── MANDATORY ─────────────────────────────────────────────────────────────────

class TestMandatory:
    """
    RED: Write these, run pytest → TransactionRequired not importable.
    GREEN: Add TransactionRequired + MANDATORY branch to transactional().
    """

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
    """
    RED: NEVER mode raises TransactionProhibited when inside a tx.
    GREEN: Add TransactionProhibited + NEVER branch.
    """

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


# ── REQUIRED ─────────────────────────────────────────────────────────────────

class TestRequired:
    """
    RED: REQUIRED joins existing session; creates new when none exists.
    GREEN: Add REQUIRED branch + _new_root_transaction helper (mocked DB).
    """

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
        """When no ambient tx exists, REQUIRED opens a new root transaction."""
        mock_session = _make_mock_session()

        with patch("db.transaction.SessionFactory", return_value=mock_session):
            async with transactional(Propagation.REQUIRED, tenant_id=None) as ctx:
                assert ctx is not None
                assert ctx.is_root is True

        mock_session.commit.assert_called_once()

    async def test_rollback_on_exception_in_new_root(self):
        mock_session = _make_mock_session()

        with patch("db.transaction.SessionFactory", return_value=mock_session):
            with pytest.raises(ValueError, match="boom"):
                async with transactional(Propagation.REQUIRED, tenant_id=None):
                    raise ValueError("boom")

        mock_session.rollback.assert_called_once()
        mock_session.commit.assert_not_called()

    async def test_contextvar_restored_after_new_root_exits(self):
        mock_session = _make_mock_session()

        with patch("db.transaction.SessionFactory", return_value=mock_session):
            async with transactional(Propagation.REQUIRED, tenant_id=None):
                pass

        assert get_active_transaction() is None

    async def test_contextvar_restored_after_new_root_raises(self):
        mock_session = _make_mock_session()

        with patch("db.transaction.SessionFactory", return_value=mock_session):
            with pytest.raises(RuntimeError):
                async with transactional(Propagation.REQUIRED, tenant_id=None):
                    raise RuntimeError("err")

        assert get_active_transaction() is None


# ── SUPPORTS ──────────────────────────────────────────────────────────────────

class TestSupports:
    """
    GREEN: Yield existing ctx if present; yield None if absent.
    No new DB session should ever be opened.
    """

    async def test_joins_when_active(self):
        outer_ctx = _push_context()

        async with transactional(Propagation.SUPPORTS) as ctx:
            assert ctx is outer_ctx

    async def test_yields_none_when_no_transaction(self):
        async with transactional(Propagation.SUPPORTS) as ctx:
            assert ctx is None

    async def test_does_not_open_new_session_when_none(self):
        with patch("db.transaction.SessionFactory") as mock_factory:
            async with transactional(Propagation.SUPPORTS):
                pass

            mock_factory.assert_not_called()


# ── NOT_SUPPORTED ─────────────────────────────────────────────────────────────

class TestNotSupported:
    """
    GREEN: Suspend ambient transaction; inner code sees None; restore after.
    """

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
    """
    When NESTED is called with no ambient tx it must behave like REQUIRED:
    open a new root transaction (not a savepoint).
    """

    async def test_creates_root_when_no_ambient_tx(self):
        mock_session = _make_mock_session()

        with patch("db.transaction.SessionFactory", return_value=mock_session):
            async with transactional(Propagation.NESTED, tenant_id=None) as ctx:
                assert ctx is not None
                assert ctx.is_root is True
                assert ctx.savepoint is None

        mock_session.commit.assert_called_once()

    async def test_rollback_on_failure_when_no_ambient_tx(self):
        mock_session = _make_mock_session()

        with patch("db.transaction.SessionFactory", return_value=mock_session):
            with pytest.raises(RuntimeError):
                async with transactional(Propagation.NESTED, tenant_id=None):
                    raise RuntimeError("fail")

        mock_session.rollback.assert_called_once()


# ── NESTED (with outer tx — savepoint) ───────────────────────────────────────

class TestNestedSavepoint:
    """
    NESTED with an ambient tx must create a SAVEPOINT, not a new session.
    Savepoint commit/rollback is independent from the outer transaction.
    """

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
    """
    REQUIRES_NEW always opens a new independent session,
    regardless of whether an ambient transaction exists.
    """

    async def test_opens_new_session_when_no_outer_tx(self):
        mock_session = _make_mock_session()

        with patch("db.transaction.SessionFactory", return_value=mock_session):
            async with transactional(Propagation.REQUIRES_NEW, tenant_id=None) as ctx:
                assert ctx.is_root is True

        mock_session.commit.assert_called_once()

    async def test_opens_new_session_even_when_outer_tx_exists(self):
        outer_ctx = _push_context()
        inner_mock = _make_mock_session()

        with patch("db.transaction.SessionFactory", return_value=inner_mock):
            async with transactional(Propagation.REQUIRES_NEW) as ctx:
                assert ctx.session is inner_mock
                assert ctx.session is not outer_ctx.session

    async def test_inner_session_committed_independently(self):
        outer_ctx = _push_context()
        inner_mock = _make_mock_session()

        with patch("db.transaction.SessionFactory", return_value=inner_mock):
            async with transactional(Propagation.REQUIRES_NEW):
                pass

        inner_mock.commit.assert_called_once()
        outer_ctx.session.commit.assert_not_called()

    async def test_inner_rollback_does_not_affect_outer(self):
        outer_ctx = _push_context()
        inner_mock = _make_mock_session()

        with patch("db.transaction.SessionFactory", return_value=inner_mock):
            with pytest.raises(ValueError):
                async with transactional(Propagation.REQUIRES_NEW):
                    raise ValueError("inner fails")

        inner_mock.rollback.assert_called_once()
        outer_ctx.session.rollback.assert_not_called()

    async def test_outer_context_restored_after_requires_new(self):
        outer_ctx = _push_context()
        inner_mock = _make_mock_session()

        with patch("db.transaction.SessionFactory", return_value=inner_mock):
            async with transactional(Propagation.REQUIRES_NEW):
                assert get_active_transaction().session is inner_mock

        assert get_active_transaction() is outer_ctx

    async def test_outer_context_restored_even_on_inner_failure(self):
        outer_ctx = _push_context()
        inner_mock = _make_mock_session()

        with patch("db.transaction.SessionFactory", return_value=inner_mock):
            with pytest.raises(RuntimeError):
                async with transactional(Propagation.REQUIRES_NEW):
                    raise RuntimeError("boom")

        assert get_active_transaction() is outer_ctx

    async def test_copies_tenant_id_from_outer_context(self):
        outer_ctx = _push_context(tenant_id="TENANT-ABC")
        inner_mock = _make_mock_session()

        with patch("db.transaction.SessionFactory", return_value=inner_mock):
            async with transactional(Propagation.REQUIRES_NEW) as ctx:
                assert ctx.tenant_id == "TENANT-ABC"


# ── @transactional_method decorator ──────────────────────────────────────────

class TestTransactionalMethodDecorator:
    """
    The decorator must behave identically to the context manager
    and must preserve function metadata (functools.wraps).
    """

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
        with patch("db.transaction.SessionFactory", return_value=inner_mock):
            ctx = await svc.log()

        assert ctx.session is inner_mock
        assert ctx.session is not outer_ctx.session


# ── ContextVar isolation across asyncio tasks ─────────────────────────────────

class TestContextVarTaskIsolation:
    """
    Verify that child asyncio tasks do NOT share the parent ContextVar
    mutably — a child inherits a copy, changes to the copy don't affect parent.
    """

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
            # Mutate the ContextVar inside the child task
            _active_tx.set(None)

        await asyncio.create_task(child())

        # Parent must still see its own context
        assert get_active_transaction() is outer_ctx
```

### 13.5 Layer 2 — Integration Tests (PostgreSQL via testcontainers)

These tests require a live PostgreSQL instance (provided by the existing `postgres_engine` testcontainer fixture in `conftest.py`). They verify that the SQLAlchemy/asyncpg/PostgreSQL layer behaves correctly end-to-end: savepoints actually roll back, RLS `SET LOCAL` is properly scoped, and REQUIRES_NEW truly commits independently.

```python
# backend/tests/integration/test_tx_propagation_integration.py
"""
Integration tests for transaction propagation against real PostgreSQL.

Uses the postgres_engine testcontainer fixture from conftest.py.
Each test gets a fresh function-scoped session factory via tx_session_factory.

These tests prove that SAVEPOINT, ROLLBACK TO SAVEPOINT, and independent
sessions work correctly in the actual asyncpg + SQLAlchemy 2.0 stack.
"""
from __future__ import annotations

import uuid
import pytest
import pytest_asyncio
from decimal import Decimal
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.transaction import (
    Propagation,
    TransactionContext,
    _active_tx,
    transactional,
    get_active_transaction,
)
from db.models.transactions import Transaction, TransactionLine
from db.models.accounts import Account

# ── Fixtures ──────────────────────────────────────────────────────────────────

TEST_TENANT = uuid.UUID("00000000-0000-0000-0000-000000000099")
TEST_USER = "99"


@pytest_asyncio.fixture
async def pg_session(tx_session_factory) -> AsyncSession:
    """
    Open a raw session with RLS context. The test owns commit/rollback.
    Rolls back after each test to keep the DB clean.
    """
    async with tx_session_factory() as session:
        # Set RLS context so tenant-scoped tables are accessible
        await session.execute(
            text("SELECT set_config('app.tenant_id', :tid, TRUE),"
                 "       set_config('app.user_id',   :uid, TRUE)"),
            {"tid": str(TEST_TENANT), "uid": TEST_USER},
        )
        # Push an ambient TransactionContext so transactional() sees it
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


@pytest_asyncio.fixture
async def seeded_account(pg_session) -> Account:
    """
    Insert one Account row visible to TEST_TENANT.
    Used as a FK target for TransactionLine rows in propagation tests.
    """
    acc = Account(
        tenant_id=TEST_TENANT,
        code=f"TEST-{uuid.uuid4().hex[:6].upper()}",
        name="Test Cash Account",
        account_type="ASSET",
        normal_balance="DEBIT",
        is_system=False,
        is_active=True,
    )
    pg_session.add(acc)
    await pg_session.flush()
    return acc


# ── Helper ─────────────────────────────────────────────────────────────────────

def _make_transaction(tenant_id: uuid.UUID, description: str) -> Transaction:
    return Transaction(
        tenant_id=tenant_id,
        transaction_date="2026-01-15",
        transaction_type="IMPORT",
        description=description,
        status="CONFIRMED",
    )


async def _count_transactions(session: AsyncSession, tenant_id: uuid.UUID) -> int:
    result = await session.execute(
        text("SELECT COUNT(*) FROM transactions WHERE tenant_id = :tid"),
        {"tid": str(tenant_id)},
    )
    return result.scalar_one()


# ── NESTED savepoint — core DB behavior ───────────────────────────────────────

class TestNestedSavepointDB:
    """
    Verify that SAVEPOINT / ROLLBACK TO SAVEPOINT work correctly via
    AsyncSession.begin_nested() against real PostgreSQL.
    """

    async def test_nested_rollback_undoes_only_inner_work(self, pg_session):
        """
        Outer: insert tx_A (flush, no commit).
        Inner (NESTED): insert tx_B, then raise → savepoint rolls back tx_B.
        After: tx_A still visible in session; tx_B gone.
        """
        # Outer work
        tx_a = _make_transaction(TEST_TENANT, "outer-tx-A")
        pg_session.add(tx_a)
        await pg_session.flush()
        outer_id = tx_a.id
        assert outer_id is not None

        # Inner work with intentional failure
        with pytest.raises(ValueError, match="inner failure"):
            async with transactional(Propagation.NESTED):
                tx_b = _make_transaction(TEST_TENANT, "inner-tx-B")
                pg_session.add(tx_b)
                await pg_session.flush()
                inner_id = tx_b.id
                assert inner_id is not None
                raise ValueError("inner failure")

        # Verify tx_A still visible within the session
        await pg_session.refresh(tx_a)
        assert tx_a.id == outer_id

        # Verify tx_B is gone (rolled back to savepoint)
        result = await pg_session.execute(
            text("SELECT COUNT(*) FROM transactions WHERE description = 'inner-tx-B'"
                 "  AND tenant_id = :tid"),
            {"tid": str(TEST_TENANT)},
        )
        assert result.scalar_one() == 0

    async def test_nested_success_visible_to_outer_session(self, pg_session):
        """
        Successful NESTED work is visible via the same session (RELEASE SAVEPOINT).
        """
        async with transactional(Propagation.NESTED):
            tx = _make_transaction(TEST_TENANT, "nested-success")
            pg_session.add(tx)
            await pg_session.flush()
            nested_id = tx.id

        # Still visible in the outer session (not committed to DB yet, but in session)
        result = await pg_session.execute(
            text("SELECT COUNT(*) FROM transactions WHERE id = :id"),
            {"id": nested_id},
        )
        assert result.scalar_one() == 1

    async def test_multiple_independent_savepoints(self, pg_session):
        """
        Three NESTED blocks: first succeeds, second fails, third succeeds.
        After: only work from blocks 1 and 3 survives.
        """
        ids = {}

        # Block 1: succeeds
        async with transactional(Propagation.NESTED):
            t = _make_transaction(TEST_TENANT, "sp-block-1")
            pg_session.add(t)
            await pg_session.flush()
            ids["block1"] = t.id

        # Block 2: fails
        with pytest.raises(RuntimeError):
            async with transactional(Propagation.NESTED):
                t = _make_transaction(TEST_TENANT, "sp-block-2")
                pg_session.add(t)
                await pg_session.flush()
                ids["block2"] = t.id
                raise RuntimeError("block 2 fails")

        # Block 3: succeeds
        async with transactional(Propagation.NESTED):
            t = _make_transaction(TEST_TENANT, "sp-block-3")
            pg_session.add(t)
            await pg_session.flush()
            ids["block3"] = t.id

        # Check results
        for desc, should_exist in [
            ("sp-block-1", True),
            ("sp-block-2", False),
            ("sp-block-3", True),
        ]:
            result = await pg_session.execute(
                text("SELECT COUNT(*) FROM transactions"
                     " WHERE description = :d AND tenant_id = :tid"),
                {"d": desc, "tid": str(TEST_TENANT)},
            )
            count = result.scalar_one()
            assert count == (1 if should_exist else 0), \
                f"Expected {desc} to {'exist' if should_exist else 'not exist'}"

    async def test_nested_within_nested(self, pg_session):
        """Two levels of savepoints: inner-inner rollback; inner survives."""
        async with transactional(Propagation.NESTED):
            t_inner = _make_transaction(TEST_TENANT, "depth-1")
            pg_session.add(t_inner)
            await pg_session.flush()

            with pytest.raises(ValueError):
                async with transactional(Propagation.NESTED):
                    t_inner2 = _make_transaction(TEST_TENANT, "depth-2")
                    pg_session.add(t_inner2)
                    await pg_session.flush()
                    raise ValueError("depth-2 fails")

        # depth-1 survives; depth-2 rolled back
        for desc, expected in [("depth-1", 1), ("depth-2", 0)]:
            r = await pg_session.execute(
                text("SELECT COUNT(*) FROM transactions"
                     " WHERE description = :d AND tenant_id = :tid"),
                {"d": desc, "tid": str(TEST_TENANT)},
            )
            assert r.scalar_one() == expected


# ── REQUIRES_NEW — independent transaction isolation ─────────────────────────

class TestRequiresNewDB:
    """
    Verify that REQUIRES_NEW opens a genuinely independent database transaction
    that commits independently of the outer session's fate.
    """

    async def test_requires_new_commits_independently(self, tx_session_factory):
        """
        Outer transaction inserts tx_A, then raises (rolls back).
        Inner REQUIRES_NEW inserts tx_B with its own commit.
        After full rollback: tx_B must survive; tx_A must not.
        """
        unique_outer = f"outer-{uuid.uuid4().hex[:8]}"
        unique_inner = f"inner-{uuid.uuid4().hex[:8]}"

        try:
            async with tx_session_factory() as outer_session:
                await outer_session.execute(
                    text("SELECT set_config('app.tenant_id', :tid, TRUE),"
                         "       set_config('app.user_id', :uid, TRUE)"),
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

                # Inner REQUIRES_NEW — opens its own session and commits
                async with transactional(Propagation.REQUIRES_NEW) as inner_ctx:
                    tx_b = _make_transaction(TEST_TENANT, unique_inner)
                    inner_ctx.session.add(tx_b)
                    await inner_ctx.session.flush()
                    # inner commits automatically on context exit

                # Simulate outer failure
                raise RuntimeError("outer transaction fails")

        except RuntimeError:
            pass  # expected

        _active_tx.set(None)  # clean ContextVar after manual session management

        # Verify using a fresh read session
        async with tx_session_factory() as verify_session:
            await verify_session.execute(
                text("SELECT set_config('app.tenant_id', :tid, TRUE),"
                     "       set_config('app.user_id', :uid, TRUE)"),
                {"tid": str(TEST_TENANT), "uid": TEST_USER},
            )
            for desc, should_exist in [(unique_outer, False), (unique_inner, True)]:
                r = await verify_session.execute(
                    text("SELECT COUNT(*) FROM transactions"
                         " WHERE description = :d AND tenant_id = :tid"),
                    {"d": desc, "tid": str(TEST_TENANT)},
                )
                count = r.scalar_one()
                assert count == (1 if should_exist else 0), \
                    f"'{desc}' expected to {'exist' if should_exist else 'not exist'}"

    async def test_requires_new_copies_tenant_rls(self, tx_session_factory):
        """
        REQUIRES_NEW must re-issue SET LOCAL on the new session.
        Verify by reading current_setting('app.tenant_id') inside the inner tx.
        """
        async with tx_session_factory() as outer_session:
            await outer_session.execute(
                text("SELECT set_config('app.tenant_id', :tid, TRUE),"
                     "       set_config('app.user_id', :uid, TRUE)"),
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
                result = await inner_ctx.session.execute(
                    text("SELECT current_setting('app.tenant_id', true)")
                )
                observed_tid = result.scalar_one()
                assert observed_tid == str(TEST_TENANT)

            await outer_session.rollback()
        _active_tx.set(None)


# ── RLS context safety ────────────────────────────────────────────────────────

class TestRLSSafety:
    """
    Verify that SET LOCAL tenant context is properly scoped to its transaction
    and does not leak to subsequent transactions (PgBouncer safety simulation).
    """

    async def test_set_local_resets_after_commit(self, tx_session_factory):
        """
        After committing a transaction with SET LOCAL app.tenant_id,
        a new transaction on the same session must NOT inherit that value.
        (SET LOCAL is transaction-scoped, not session-scoped.)
        """
        async with tx_session_factory() as session:
            # First transaction: set tenant_id
            await session.execute(
                text("SELECT set_config('app.tenant_id', :tid, TRUE)"),
                {"tid": str(TEST_TENANT)},
            )
            r = await session.execute(
                text("SELECT current_setting('app.tenant_id', true)")
            )
            assert r.scalar_one() == str(TEST_TENANT)
            await session.commit()

            # Second transaction: SET LOCAL should have cleared
            r2 = await session.execute(
                text("SELECT current_setting('app.tenant_id', true)")
            )
            val = r2.scalar_one()
            # PostgreSQL returns '' or NULL after SET LOCAL resets
            assert val in ("", None), \
                f"Expected tenant_id to be cleared after commit, got: {val!r}"

    async def test_rls_context_scoped_to_root_transaction(self, pg_session):
        """
        The RLS context (SET LOCAL) set at the start of a root transaction
        must be visible throughout the transaction including inside NESTED blocks.
        """
        # pg_session fixture already sets app.tenant_id = TEST_TENANT
        async with transactional(Propagation.NESTED):
            r = await pg_session.execute(
                text("SELECT current_setting('app.tenant_id', true)")
            )
            assert r.scalar_one() == str(TEST_TENANT)
```

### 13.6 Layer 3 — Service Integration Tests

These tests verify the most impactful use case: `ApprovalService.commit_proposals()` with per-proposal NESTED savepoints. Each proposal is independent; one bad proposal must not abort the rest.

```python
# backend/tests/integration/test_approval_service_propagation.py
"""
Integration tests for ApprovalService with NESTED propagation.

Before: commit_proposals() has no savepoints — one bad proposal aborts ALL.
After:  each proposal runs in its own NESTED context — partial success is possible.

These tests are written FIRST (red), then ApprovalService is updated (green).
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, patch

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
from core.models.enums import SourceType, FileFormat, BatchStatus

TEST_TENANT = uuid.UUID("00000000-0000-0000-0000-000000000099")
TEST_USER = "99"


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def approval_session(tx_session_factory):
    """Session with RLS context + ContextVar push, rolls back after test."""
    async with tx_session_factory() as session:
        await session.execute(
            text("SELECT set_config('app.tenant_id', :tid, TRUE),"
                 "       set_config('app.user_id', :uid, TRUE)"),
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


def _make_pydantic_batch() -> PydanticBatch:
    return PydanticBatch(
        batch_id=str(uuid.uuid4()),
        user_id="99",
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
    return ProposedJournalEntry(
        proposal_id=str(uuid.uuid4()),
        txn_date="2026-01-15",
        narration=narration,
        txn_hash=uuid.uuid4().hex,
        status="CONFIRMED",
        lines=[
            JournalEntryLine(
                account_code=expense_code,
                debit=Decimal(amount),
                credit=Decimal("0"),
            ),
            JournalEntryLine(
                account_code=cash_code,
                debit=Decimal("0"),
                credit=Decimal(amount),
            ),
        ],
    )


def _make_bad_proposal(narration: str = "Bad proposal") -> ProposedJournalEntry:
    """A proposal referencing a non-existent account code — will fail resolution."""
    return ProposedJournalEntry(
        proposal_id=str(uuid.uuid4()),
        txn_date="2026-01-15",
        narration=narration,
        txn_hash=uuid.uuid4().hex,
        status="CONFIRMED",
        lines=[
            JournalEntryLine(
                account_code="NONEXISTENT-CODE",
                debit=Decimal("500"),
                credit=Decimal("0"),
            ),
            JournalEntryLine(
                account_code="ALSO-NONEXISTENT",
                debit=Decimal("0"),
                credit=Decimal("500"),
            ),
        ],
    )


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestApprovalServiceWithNested:
    """
    RED phase: These tests fail because ApprovalService does not yet use NESTED.
    The current implementation skips bad proposals but a mid-flight DB constraint
    error would abort the whole session (no savepoint).

    GREEN phase: Update commit_proposals() to wrap each proposal in
    transactional(Propagation.NESTED).
    """

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
        """
        RED → must fail on current implementation if a DB error mid-loop
        corrupts the session. GREEN → NESTED savepoint isolates the failure.

        Mix: good, bad (unresolvable account), good.
        Expected: 2 committed, 1 skipped.
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
        """Posting the same proposal twice must skip the second attempt."""
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

    async def test_each_proposal_gets_own_savepoint(
        self, approval_session, cash_account, expense_account
    ):
        """
        Verify that begin_nested is called once per proposal (not once total).
        This confirms the NESTED wrapping is applied per-iteration.
        """
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

        # One savepoint per CONFIRMED proposal
        assert call_count == 4

    async def test_batch_status_set_to_completed(
        self, approval_session, cash_account, expense_account
    ):
        """ImportBatch.status must be COMPLETED after successful commit."""
        proposals = [
            _make_proposal(cash_account.code, expense_account.code)
        ]
        batch = _make_pydantic_batch()
        svc = ApprovalService(approval_session, str(TEST_TENANT))

        result = await svc.commit_proposals(proposals, batch)

        from db.models.imports import ImportBatch as OrmBatch
        from sqlalchemy import select
        orm_batch = await approval_session.scalar(
            select(OrmBatch).where(OrmBatch.id == result["orm_batch_id"])
        )
        assert orm_batch.status == "COMPLETED"


# ── Legacy unit_of_work backward compatibility ─────────────────────────────────

class TestUnitOfWorkBackwardCompat:
    """
    Verify that existing callers of unit_of_work() continue to work unchanged
    after it is rewritten as a thin wrapper over transactional().
    """

    async def test_creates_new_transaction_when_called_without_args(self):
        from db.unit_of_work import unit_of_work
        from unittest.mock import patch, AsyncMock

        mock_session = AsyncMock()

        with patch("db.transaction.SessionFactory", return_value=mock_session):
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

    async def test_uses_ambient_contextvar_session(self):
        from db.unit_of_work import unit_of_work
        from unittest.mock import AsyncMock

        ambient_session = AsyncMock()
        ctx = TransactionContext(
            session=ambient_session,
            tenant_id="T1",
            user_id="1",
            is_root=True,
        )
        _active_tx.set(ctx)

        async with unit_of_work() as session:
            assert session is ambient_session

        ambient_session.commit.assert_not_called()  # outer ctx owns commit
```

### 13.7 Running the Tests

```bash
# From repo root
cd backend

# Run unit tests only (no Docker required — fast, CI-friendly)
pytest tests/unit/test_tx_propagation_unit.py -v

# Run integration tests only (requires Docker for testcontainers)
pytest tests/integration/test_tx_propagation_integration.py \
       tests/integration/test_approval_service_propagation.py \
       -v --timeout=120

# Run all propagation tests together with coverage
pytest tests/unit/test_tx_propagation_unit.py \
       tests/integration/test_tx_propagation_integration.py \
       tests/integration/test_approval_service_propagation.py \
       --cov=db.transaction \
       --cov=services.approval_service \
       --cov-report=term-missing \
       -v

# Run just the backward-compat tests (smoke test for existing code)
pytest tests/integration/test_approval_service_propagation.py::TestUnitOfWorkBackwardCompat -v
```

### 13.8 Expected Test Results by TDD Phase

#### Phase 1 — Before any implementation (all RED)

```
FAILED tests/unit/test_tx_propagation_unit.py
  ImportError: cannot import name 'Propagation' from 'db.transaction'
  (db/transaction.py does not exist yet)

FAILED tests/integration/test_tx_propagation_integration.py
  ImportError: cannot import name 'transactional' from 'db.transaction'

FAILED tests/integration/test_approval_service_propagation.py::
  TestApprovalServiceWithNested::test_bad_proposal_does_not_abort_good_ones
  AssertionError: result["committed"] == 1, expected 2
  (current ApprovalService has no NESTED — session aborts on bad proposal)
```

#### Phase 2 — After implementing `db/transaction.py` (unit tests GREEN)

```
PASSED  tests/unit/test_tx_propagation_unit.py::TestMandatory (3 tests)
PASSED  tests/unit/test_tx_propagation_unit.py::TestNever (3 tests)
PASSED  tests/unit/test_tx_propagation_unit.py::TestRequired (7 tests)
PASSED  tests/unit/test_tx_propagation_unit.py::TestSupports (3 tests)
PASSED  tests/unit/test_tx_propagation_unit.py::TestNotSupported (4 tests)
PASSED  tests/unit/test_tx_propagation_unit.py::TestNestedWithNoOuterTransaction (2 tests)
PASSED  tests/unit/test_tx_propagation_unit.py::TestNestedSavepoint (8 tests)
PASSED  tests/unit/test_tx_propagation_unit.py::TestRequiresNew (7 tests)
PASSED  tests/unit/test_tx_propagation_unit.py::TestTransactionalMethodDecorator (7 tests)
PASSED  tests/unit/test_tx_propagation_unit.py::TestContextVarTaskIsolation (2 tests)

FAILED  tests/integration/test_tx_propagation_integration.py (requires DB)
FAILED  tests/integration/test_approval_service_propagation.py (requires DB + NESTED in service)
```

#### Phase 3 — After `deps.py` + `engine.py` updates (integration tests GREEN)

```
PASSED  tests/integration/test_tx_propagation_integration.py::TestNestedSavepointDB (4 tests)
PASSED  tests/integration/test_tx_propagation_integration.py::TestRequiresNewDB (2 tests)
PASSED  tests/integration/test_tx_propagation_integration.py::TestRLSSafety (2 tests)

FAILED  tests/integration/test_approval_service_propagation.py::
  TestApprovalServiceWithNested::test_bad_proposal_does_not_abort_good_ones
  (ApprovalService not yet updated)
```

#### Phase 4 — After updating `ApprovalService.commit_proposals()` (all GREEN)

```
PASSED  tests/integration/test_approval_service_propagation.py::TestApprovalServiceWithNested (7 tests)
PASSED  tests/integration/test_approval_service_propagation.py::TestUnitOfWorkBackwardCompat (3 tests)

========================= 50 passed in 18.3s =========================

Coverage report:
  db/transaction.py          98%   (2 lines: error path for NOT_SUPPORTED edge)
  services/approval_service.py  95%   (happy path + NESTED)
```

### 13.9 Coverage Targets

| Module | Target | Notes |
|---|---|---|
| `db/transaction.py` | ≥ 95% | All 7 propagation modes + both sub-paths (join / create) |
| `db/unit_of_work.py` | 100% | 3 branches: explicit session, ambient ctx, new root |
| `db/engine.py` | ≥ 90% | `get_session_with_rls_and_context` and existing generators |
| `services/approval_service.py` | ≥ 90% | Happy path, skip, already_posted, unresolvable account |

### 13.10 Test Implementation Order (Strict TDD)

```
Step 1  Write TestMandatory          → RED (ImportError)
Step 2  Create db/transaction.py:
          Propagation enum
          TransactionContext dataclass
          _active_tx ContextVar
          get_active_transaction()
          TransactionRequired exception
          MANDATORY branch only in transactional()
        → TestMandatory GREEN

Step 3  Write TestNever              → RED
Step 4  Add TransactionProhibited + NEVER branch
        → TestNever GREEN

Step 5  Write TestRequired           → RED (join path + new root path)
Step 6  Add _new_root_transaction() + REQUIRED branch
        → TestRequired GREEN (mocked SessionFactory)

Step 7  Write TestSupports           → RED
Step 8  Add SUPPORTS branch          → TestSupports GREEN

Step 9  Write TestNotSupported       → RED
Step 10 Add NOT_SUPPORTED branch     → TestNotSupported GREEN

Step 11 Write TestNestedWithNoOuterTransaction + TestNestedSavepoint → RED
Step 12 Add _nested_savepoint() + NESTED branch
        → TestNested* GREEN

Step 13 Write TestRequiresNew        → RED
Step 14 Add REQUIRES_NEW branch      → TestRequiresNew GREEN

Step 15 Write TestTransactionalMethodDecorator → RED
Step 16 Add transactional_method()   → TestTransactionalMethodDecorator GREEN

Step 17 Write TestContextVarTaskIsolation → GREEN immediately
        (ContextVar semantics built into Python — confirm, don't implement)

Step 18 Write TestNestedSavepointDB (integration) → RED (needs DB)
Step 19 Update engine.py + deps.py   → TestNestedSavepointDB GREEN

Step 20 Write TestRequiresNewDB      → RED
        → GREEN (no extra code needed — DB session isolation confirmed)

Step 21 Write TestRLSSafety          → RED → GREEN

Step 22 Write TestApprovalServiceWithNested → RED
        test_bad_proposal_does_not_abort_good_ones fails (no NESTED in service)

Step 23 Update ApprovalService.commit_proposals():
          wrap _commit_one() call in transactional(Propagation.NESTED)
        → All TestApprovalServiceWithNested GREEN

Step 24 Write TestUnitOfWorkBackwardCompat → RED
Step 25 Update unit_of_work.py       → GREEN

Step 26 Run full suite — 50 tests pass.
```
