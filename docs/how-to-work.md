# Developer Guide — Ledger 3.0

Practical reference for anyone writing code in this repository. Covers the
patterns you'll encounter in every file, how to add new features, and how to
write tests that actually work with the async + RLS architecture.

---

## 1. Tech Stack at a Glance

| Concern | Choice |
|---|---|
| Python | 3.12 |
| Web framework | FastAPI (fully async) |
| ORM | SQLAlchemy 2.0 — `AsyncSession`, `mapped_column`, `Mapped[T]` |
| Database | PostgreSQL 15 with Row-Level Security |
| DB drivers | `asyncpg` (app connections), `aiosqlite` (tests) |
| Auth | JWT via `python-jose`; payload carries `sub`, `tenant_id`, `role` |
| Migrations | Alembic (async engine) |
| Validation | Pydantic v2 |
| Testing | pytest + pytest-asyncio (`asyncio_mode = auto`) |

All I/O — database queries, file reads, LLM calls — is `async/await`. There
is no synchronous SQLAlchemy in the application path.

---

## 2. Repository Structure

```
backend/src/
├── api/
│   ├── deps.py              # FastAPI dependency functions (auth + DB sessions)
│   └── routers/             # One file per API surface (imports, pipeline, …)
├── core/                    # In-memory pipeline data models (Pydantic, no DB)
├── db/
│   ├── engine.py            # create_async_engine, session factories, get_session*
│   └── models/              # SQLAlchemy ORM models
│       ├── base.py          # Base, TenantScopedMixin
│       ├── accounts.py
│       ├── transactions.py
│       └── …
├── modules/
│   ├── llm/                 # LLM provider abstraction layer
│   └── parser/              # Bank-statement parsers (SM-C)
├── onboarding/              # Onboarding sub-modules (profile, COA, accounts, …)
│   ├── account/
│   ├── coa/
│   ├── institution/
│   ├── opening_balance/
│   ├── dashboard/
│   ├── networth/
│   ├── orchestrator/
│   └── profile/
├── repositories/            # SQLAlchemy repository implementations
├── services/                # Pipeline services (normalize, dedup, categorize, …)
├── config.py                # Settings (pydantic-settings, reads .env)
└── main.py                  # FastAPI app factory + router registration
```

---

## 3. The Three Core Dependencies

Every route uses one or more of these. Understand them before writing anything.

### 3.1 `TenantDBSession`

```python
from api.deps import TenantDBSession   # Annotated[AsyncSession, Depends(get_tenant_db)]
```

Opens an `AsyncSession` and sets both `app.tenant_id` and `app.user_id` as
PostgreSQL session-local variables before the first query. RLS policies read
`current_tenant_id()` from that variable — so every query is automatically
filtered to the calling tenant's rows.

**Use this for any route that reads or writes tenant-scoped tables.**
You never need to add `WHERE tenant_id = ...` — the database enforces it.

### 3.2 `DBSession`

```python
from api.deps import DBSession         # Annotated[AsyncSession, Depends(get_db)]
```

Opens an `AsyncSession` without setting tenant context. Use this only for
genuinely global tables that have no tenant isolation: `users`, `tenants`,
`tenant_memberships`, `profiles`.

### 3.3 `CurrentUserPayload`

```python
from api.deps import CurrentUserPayload   # Annotated[UserTokenPayload, Depends(get_current_user_payload)]
```

Decodes the JWT and returns a `UserTokenPayload` with three attributes:

```python
auth.user_id    # str  — numeric user ID from "sub" claim
auth.tenant_id  # str  — UUID string from "tenant_id" claim
auth.role       # str  — "OWNER" | "ADMIN" | "MEMBER"
```

**Dev shortcut:** When `APP_ENV=development` and no `Authorization` header is
sent, a default payload is returned (`user_id="1"`,
`tenant_id="00000000-0000-0000-0000-000000000001"`, `role="OWNER"`). This lets
you use Swagger without headers locally.

---

## 4. Writing a New Route

### Minimal pattern

```python
# src/api/routers/my_feature.py
from fastapi import APIRouter
from api.deps import TenantDBSession, CurrentUserPayload

router = APIRouter(prefix="/my-feature", tags=["My Feature"])


@router.get("/")
async def list_items(
    session: TenantDBSession,
    auth: CurrentUserPayload,
) -> list[dict]:
    from sqlalchemy import select
    from db.models.my_model import MyModel          # import inside function is fine

    rows = (await session.scalars(select(MyModel))).all()
    return [{"id": r.id, "name": r.name} for r in rows]
```

### Register in `main.py`

```python
from api.routers.my_feature import router as my_feature_router
# … inside create_app():
app.include_router(my_feature_router, prefix=PREFIX)
```

### Rules

- Every route function must be `async def`.
- Never call `session.commit()` in a route — the dependency manages the
  transaction lifecycle.
- Never write `WHERE tenant_id = :tid` — RLS handles isolation automatically.
- Use `await session.scalars(select(Model))` for multi-row queries;
  `await session.get(Model, pk)` for primary-key lookups.

---

## 5. ORM Models

### Base classes

```python
# db/models/base.py
class Base(DeclarativeBase): ...

class TenantScopedMixin:
    """Add to any model that is tenant-scoped (has RLS policy)."""
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True, native_uuid=True), nullable=False, index=True
    )
    created_at: Mapped[datetime] = ...
    updated_at: Mapped[datetime] = ...
```

Every tenant-scoped table inherits from **both** `TenantScopedMixin` and `Base`:

```python
class Account(TenantScopedMixin, Base):
    __tablename__ = "accounts"
    name: Mapped[str] = mapped_column(String, nullable=False)
    …
```

Do **not** set `tenant_id` manually in application code. The session dependency
sets it via the PostgreSQL session variable; RLS enforces it on every row.

### Async lazy-load rule

SQLAlchemy async sessions **cannot** lazy-load relationships. If you need
related rows, either:

```python
# Option A: use selectinload in the query
from sqlalchemy.orm import selectinload
stmt = select(Account).options(selectinload(Account.children))

# Option B: build the relationship from the flat list (preferred for trees)
tree = await account_repo.get_tree()           # returns ALL accounts, flat
by_id = {_attr(n, "id"): n for n in tree}
children_of = {}
for n in tree:
    pid = _attr(n, "parent_id")
    if pid:
        children_of.setdefault(pid, []).append(n)
```

Never access `obj.relationship_attr` on an ORM object outside an async context
or without eager-loading — it will raise `MissingGreenlet`.

---

## 6. Multi-Tenancy Model

```
┌─────────────┐       ┌──────────────────────┐       ┌──────────┐
│    users    │──────<│  tenant_memberships  │>──────│ tenants  │
│  (global)   │       │  user_id, tenant_id  │       │          │
│  no RLS     │       │  role (OWNER/ADMIN/  │       │          │
└─────────────┘       │        MEMBER)       │       └──────────┘
                      └──────────────────────┘
                                │
                                │ JWT carries tenant_id
                                ▼
                      ┌──────────────────────┐
                      │  app_service role    │
                      │  SET app.tenant_id   │  ← get_tenant_db sets this
                      │  RLS auto-filters    │
                      └──────────────────────┘
```

- **One database, one schema** — all tenants share the same tables.
- **RLS enforces isolation** — `current_tenant_id()` reads `app.tenant_id`
  from the session; every SELECT/INSERT/UPDATE/DELETE is filtered by it.
- **M:N user ↔ tenant** — a user can belong to multiple tenants with different
  roles in each.
- **JWT must contain `tenant_id`** — routes that use `TenantDBSession` need the
  claim to be present; they return `401 TOKEN_NO_TENANT` otherwise.

### JWT structure

```json
{
  "sub": "42",
  "tenant_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "role": "OWNER",
  "exp": 1234567890
}
```

---

## 7. Writing Tests

### Test configuration

`backend/tests/pytest.ini`:

```ini
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = session
asyncio_default_test_loop_scope = session
```

`asyncio_mode = auto` means every `async def test_*` and `async def` fixture
runs in the event loop automatically — no `@pytest.mark.asyncio` decorator
needed.

### Unit tests (`tests/unit/`)

Fixtures live in `tests/unit/conftest.py`. They provide an `AsyncSession`
backed by aiosqlite in-memory. An event listener auto-sets `tenant_id` on every
new ORM object so constraints don't fire.

```python
# tests/unit/conftest.py (pattern)
@pytest.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", ...)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionFactory() as sess:
        @sa_event.listens_for(sess.sync_session, "before_flush")
        def _auto_tenant(session, ctx, instances):
            for obj in session.new:
                if hasattr(obj, "tenant_id") and obj.tenant_id is None:
                    obj.tenant_id = TEST_TENANT_ID
        yield sess
```

Write unit tests like this:

```python
# tests/unit/test_my_service.py
async def test_create_account(session):
    repo = SqlAlchemyAccountRepository(session)
    service = MyService(repo)

    result = await service.create({"name": "Test", "code": "1000"})

    assert result.name == "Test"
```

No `@pytest.mark.asyncio` needed — the `auto` mode handles it.

### API tests (`tests/api/`)

`tests/api/conftest.py` provides a `client` fixture that:

1. Creates an aiosqlite in-memory engine.
2. Overrides `get_tenant_db` and `get_db` to yield sessions from that engine.
3. Wraps the app in `TestClient`.

```python
async def test_create_profile(client):
    resp = client.post("/api/v1/onboarding/profiles", json={
        "display_name": "Jane",
        "base_currency": "INR",
        "financial_year_start_month": 4,
        "tax_regime": "NEW",
        "date_format": "DD/MM/YYYY",
        "number_format": "INDIAN",
    })
    assert resp.status_code == 201
```

Note: the test function can be `async def` or plain `def` — both work because
`TestClient` handles async deps internally. Prefer plain `def` for API tests
unless you need to `await` something directly.

### Integration tests (`tests/integration/`)

`tests/integration/conftest.py` applies the same aiosqlite override at
session scope so all integration tests share one in-memory database without
needing PostgreSQL.

For services called directly (not via HTTP), wrap async calls in `asyncio.run()`
if the test function is synchronous:

```python
def test_categorize(batch_id, user_id):
    result = asyncio.run(
        CategorizeService().categorize_batch(batch_id=batch_id, rows=rows)
    )
    assert result.results[0].category_code == "EXPENSE_FOOD"
```

---

## 8. Import Pipeline Architecture

The statement-import pipeline is a chain of independent services (SM-* modules):

```
Upload file
    │
    ▼ SM-B  (/imports/upload)
ImportBatch created in memory (_batches dict)
    │
    ▼ SM-C  (/pipeline/parse)
ExtractionChain → parser detects bank format → RawParsedRow list
    │
    ▼ SM-E  NormalizeService.normalize_batch()
NormalizedTransaction list (amounts, dates, narrations standardised)
    │
    ▼ SM-F  DedupService.dedup_batch()
Split into .new / .duplicate by txn_hash
    │
    ▼ SM-G  CategorizeService.categorize_batch(session=...)
Category codes assigned by keyword rules (+ optional user-defined rules from DB)
    │
    ▼ SM-H  ConfidenceService.score_batch()
Confidence band: GREEN / YELLOW / RED
    │
    ▼ SM-J  SmartProcessor.process_batch()   (orchestrates SM-E→SM-H)
    │
    ▼ SM-I  ProposalService.propose_batch()
Journal entry proposals (debit/credit pairs)
```

`SmartProcessor.process_batch()` is `async` — call it with `await`.

`CategorizeService.categorize_batch()` accepts an optional `session=` argument:
- `session=None` → uses only built-in keyword rules (no DB query, safe in tests).
- `session=<AsyncSession>` → also loads user-defined rules from `user_category_rules`.

---

## 9. Adding a New Parser

1. Create `src/modules/parser/parsers/my_bank_pdf.py` implementing
   `BaseParser.parse_text_content(text: str) -> ParseResult`.
2. Register it in `src/modules/parser/registry.py`:
   ```python
   registry.register(SourceType.MY_BANK_PDF, MyBankPdfParser())
   ```
3. Add detection signatures in `src/modules/parser/detector.py` if the format
   can be auto-detected from column headers or filename patterns.
4. Add fixture files under `tests/fixtures/` and write tests in
   `tests/parser/test_my_bank_parser.py`.

---

## 10. Database Migrations

Migrations live in `backend/alembic/versions/`. The Alembic env uses the
`superadmin` role so it can bypass RLS and create tables.

```bash
cd backend

# Generate a new migration after changing ORM models
PYTHONPATH=src alembic revision --autogenerate -m "add_foo_column"

# Apply all pending migrations
PYTHONPATH=src alembic upgrade head

# Roll back one step
PYTHONPATH=src alembic downgrade -1
```

**Important:** after adding a new tenant-scoped table, manually add to the
migration:

```python
op.execute(text("ALTER TABLE my_table ENABLE ROW LEVEL SECURITY"))
op.execute(text("ALTER TABLE my_table FORCE ROW LEVEL SECURITY"))
op.execute(text("""
    CREATE POLICY tenant_isolation ON my_table
        AS PERMISSIVE FOR ALL TO app_service
        USING (tenant_id = current_tenant_id())
        WITH CHECK (tenant_id = current_tenant_id())
"""))
```

---

## 11. Common Mistakes

| Mistake | Fix |
|---|---|
| Accessing ORM relationship without eager-load | Use `selectinload` in the query, or traverse the flat list from `get_tree()` |
| Calling `await session.commit()` inside a route | Don't — `get_tenant_db` commits on exit |
| Adding `WHERE tenant_id = ...` to queries | Remove it — RLS handles isolation |
| Calling async service method without `await` | You get a coroutine, not a result |
| Using `get_current_user_id` in new routes | Use `CurrentUserPayload` instead; it also provides `tenant_id` |
| Token missing `tenant_id` claim | `get_tenant_db` returns `401 TOKEN_NO_TENANT` |
| `NOT NULL constraint failed: *.tenant_id` in tests | Add the auto-tenant event listener to your test fixture (see unit test conftest) |
| `CHECK constraint failed: ck_transaction_status` | Valid values are `PENDING`, `CONFIRMED`, `VOID`, `RECONCILED` — not `POSTED` |

---

## 12. Development Workflow

```bash
# Run all tests (no PostgreSQL needed)
cd backend
PYTHONPATH=src python -m pytest tests/ --ignore=tests/api/test_reports_api.py -q

# Run a single test module
PYTHONPATH=src python -m pytest tests/unit/test_coa_service.py -v

# Run with output on failures
PYTHONPATH=src python -m pytest tests/unit/ -x --tb=short

# Start API server in dev mode (auto-reload)
PYTHONPATH=src uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Format / lint (if configured)
ruff check src/
ruff format src/
```

---

## 13. Key Files to Know

| File | What it does |
|---|---|
| [src/api/deps.py](../backend/src/api/deps.py) | All FastAPI dependencies: auth, TenantDBSession, DBSession |
| [src/db/engine.py](../backend/src/db/engine.py) | Async engine setup, `get_session`, `get_session_with_context` |
| [src/db/models/base.py](../backend/src/db/models/base.py) | `Base`, `TenantScopedMixin` |
| [src/config.py](../backend/src/config.py) | All env-var settings with defaults |
| [src/main.py](../backend/src/main.py) | App factory, router wiring, middleware |
| [src/services/smart_service.py](../backend/src/services/smart_service.py) | Full pipeline orchestrator (SM-J) |
| [src/services/categorize_service.py](../backend/src/services/categorize_service.py) | Category rules engine (SM-G) |
| [tests/unit/conftest.py](../backend/tests/unit/conftest.py) | Async aiosqlite session for unit tests |
| [tests/api/conftest.py](../backend/tests/api/conftest.py) | TestClient with dependency overrides |
| [tests/integration/conftest.py](../backend/tests/integration/conftest.py) | Session-scoped DB override for integration tests |
| [alembic/versions/](../backend/alembic/versions/) | Migration files |

---

## 14. Specs and Design Docs

| Document | Topic |
|---|---|
| [docs/specs/postgresql-multitenancy-spec.md](specs/postgresql-multitenancy-spec.md) | Full RLS design, roles, policies |
| [docs/specs/async-tenancy-migration-spec.md](specs/async-tenancy-migration-spec.md) | Async migration implementation guide |
| [docs/specs/SM-B-document-ingestion.md](specs/SM-B-document-ingestion.md) | Import pipeline design |
| [docs/specs/SM-C-parser-engine.md](specs/SM-C-parser-engine.md) | Parser framework |
| [docs/specs/SM-G-categorization-engine.md](specs/SM-G-categorization-engine.md) | Categorisation rules |
| [docs/specs/SM-J-smart-ai-processing.md](specs/SM-J-smart-ai-processing.md) | AI pipeline orchestration |
| [docs/architecture-design.md](architecture-design.md) | High-level architecture |
