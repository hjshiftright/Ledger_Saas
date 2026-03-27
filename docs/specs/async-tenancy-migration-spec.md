# Async Migration & Tenancy Completion Specification
## Ledger SaaS — Phase 2: Route Migration, Missing Tenant Columns, and Alembic

**Version:** 1.0
**Date:** March 27, 2026
**Scope:** Migrate ~28 sync route files to async `TenantDBSession`, add `tenant_id` to 15+ models that are still user-scoped, and establish Alembic as the authoritative schema migration tool.
**Prerequisite:** Phase 1 spec (`postgresql-multitenancy-spec.md`) must be fully applied before beginning this work.

---

## 1. Executive Summary

Phase 1 established the multi-tenancy infrastructure: `TenantScopedMixin`, `TenantDBSession`, `UserTokenPayload`, the `admin_engine`, and the M:N auth flow. However, most of the application's ~28 route files are still using:

- **Sync SQLAlchemy** (`session.scalar()` instead of `await session.execute()`)
- **`DBSession`** (no tenant context) instead of **`TenantDBSession`** (sets `app.tenant_id` for RLS)
- **`CurrentUser`** (user_id string only) instead of **`CurrentUserPayload`** (user_id + tenant_id + role)
- **`user_id`-column isolation** instead of **RLS-enforced tenant isolation**

Additionally, 15+ ORM models are missing the `tenant_id` column entirely, so RLS cannot protect their data. No Alembic setup exists; schema is currently managed by `Base.metadata.create_all`, which cannot be used in production.

This spec covers all three areas in order:

| Phase | Work | Tables / Files Affected |
|---|---|---|
| **A** | Alembic setup and initial migration baseline | `alembic/`, `alembic.ini`, `env.py` |
| **B** | Add `tenant_id` to 15 missing models | 15 ORM model files + migrations |
| **C** | Migrate routers to async + `TenantDBSession` | ~28 route + service files |

---

## 2. Current State Analysis

### 2.1 Session and Auth Pattern Inventory

| Router File | Session Dep | Auth Dep | Mode | Tenant-Aware? |
|---|---|---|---|---|
| `api/routers/accounts.py` | `DBSession` | `CurrentUser` | SYNC | ❌ |
| `api/routers/budgets.py` | `DBSession` | `CurrentUser` | SYNC | ❌ |
| `api/routers/goals.py` | `DBSession` | `CurrentUser` | SYNC | ❌ |
| `api/routers/chat.py` | `DBSession` | `CurrentUser` | SYNC | ❌ |
| `api/routers/dedup.py` | `DBSession` | `CurrentUser` | SYNC | ❌ |
| `api/routers/llm.py` | `DBSession` | `CurrentUser` | SYNC | ❌ |
| `api/routers/reports.py` | `DBSession` | `CurrentUser` | SYNC | ❌ |
| `api/routers/transactions.py` | `DBSession` | `CurrentUser` | SYNC | ❌ |
| `api/routers/pipeline.py` | `DBSession` | `CurrentUser` | SYNC | ❌ |
| `api/routers/proposals.py` | `DBSession` | `CurrentUser` | SYNC | ❌ |
| `api/routers/categorize.py` | `DBSession` | `CurrentUser` | SYNC | ❌ |
| `api/routers/imports.py` | None | `CurrentUser` | ASYNC | ❌ (in-memory) |
| `api/routers/normalize.py` | None | `CurrentUser` | SYNC | ❌ (in-memory) |
| `api/routers/parser.py` | None | `CurrentUser` | SYNC | ❌ (in-memory) |
| `api/routers/confidence.py` | None | `CurrentUser` | SYNC | ❌ (in-memory) |
| `onboarding/profile/router.py` | `DBSession` | `CurrentUser` | SYNC | ❌ |
| `onboarding/coa/router.py` | `DBSession` | None | SYNC | ❌ |
| `onboarding/institution/router.py` | `DBSession` | `CurrentUser` | SYNC | ❌ |
| `onboarding/account/router.py` | `DBSession` | `CurrentUser` | SYNC | ❌ |
| `onboarding/opening_balance/router.py` | `DBSession` | `CurrentUser` | SYNC | ❌ |
| `onboarding/networth/router.py` | `DBSession` | `CurrentUser` | SYNC | ❌ |
| `onboarding/dashboard/router.py` | `DBSession` | `CurrentUser` | SYNC | ❌ |
| `onboarding/orchestrator/router.py` | `DBSession` | `CurrentUser` | SYNC | ❌ |

### 2.2 Models Missing `tenant_id`

These models have `user_id` for isolation but do **not** inherit `TenantScopedMixin`, so PostgreSQL RLS cannot protect them:

| Model | File | Has `user_id`? | Notes |
|---|---|---|---|
| `Budget` | `db/models/budgets.py` | ✓ | Per spec table #21 |
| `BudgetItem` | `db/models/budgets.py` | via FK | Per spec table #22 |
| `Goal` | `db/models/goals.py` | ✓ | Per spec table #17 |
| `GoalMilestone` | `db/models/goals.py` | via FK | Per spec table #19 |
| `GoalContribution` | `db/models/goals.py` | via FK | Per spec table #20 |
| `GoalAccountMapping` | `db/models/goals.py` | via FK | Per spec table #18 |
| `ImportBatch` | `db/models/imports.py` | ✓ | Per spec table #27 |
| `RecurringTransaction` | `db/models/recurring.py` | ❌ none | Per spec table #15 |
| `RecurringTransactionLine` | `db/models/recurring.py` | ❌ none | Per spec table #16 |
| `MonthlySnapshot` | `db/models/reporting.py` | ❌ none | Per spec table #23 |
| `NetWorthHistory` | `db/models/reporting.py` | ❌ none | Per spec table #24 |
| `SavedReport` | `db/models/reporting.py` | ❌ none | Per spec table #25 |
| `TaxSectionMapping` | `db/models/tax.py` | ❌ none | Per spec table #33 |
| `TaxLot` | `db/models/tax.py` | ❌ none | Per spec table #30 |
| `TaxLotDisposal` | `db/models/tax.py` | ❌ none | Per spec table #29 |
| `UserCategoryRule` | `db/models/categories.py` | ✓ (str) | Per spec — rename field |
| `Payee` | `db/models/categories.py` | ❌ none | Per spec table #12 |
| `Tag` | `db/models/categories.py` | ❌ none | Per spec table #13 |
| `TransactionTag` | `db/models/categories.py` | ❌ none | Per spec table #14 |
| `LlmProvider` | `db/models/system.py` | ✓ (str) | Tenant-scoped setting |
| `AppSetting` | `db/models/system.py` | ❌ none | Per spec table #34 |
| `AuditLog` | `db/models/system.py` | ✓ | Per spec table #35 (⚡ hot) |
| `Notification` | `db/models/system.py` | ✓ | Per spec table #36 |
| `FoPosition` | `db/models/securities.py` | ❌ none | Per spec table #31 |
| `HoldingsSummary` | `db/models/securities.py` | ❌ none | Per spec table #32 |

### 2.3 Alembic Status

- Alembic is **installed** (present in `.venv`) but **not configured** for the project.
- No `alembic/` directory exists in `backend/`.
- No `alembic.ini` exists.
- Schema is currently created via `Base.metadata.create_all` in tests and a `migrate.py` script.
- **This is not safe for production** — `create_all` cannot apply incremental changes to an existing database.

---

## 3. Phase A — Alembic Setup

### 3.1 Install and Initialise

```bash
# From backend/
pip install alembic
alembic init alembic
```

This creates:
```
backend/
  alembic/
    env.py          ← configure to use our async engine
    script.py.mako  ← migration file template
    versions/       ← migration files go here
  alembic.ini       ← points to backend/alembic/
```

### 3.2 Configure `alembic.ini`

```ini
# backend/alembic.ini
[alembic]
script_location = alembic
file_template = %%(year)d%%(month).2d%%(day).2d_%%(rev)s_%%(slug)s
prepend_sys_path = src
sqlalchemy.url =    # LEFT BLANK — set dynamically in env.py from config
```

> [!NOTE]
> Leave `sqlalchemy.url` blank. The URL is read from `settings.admin_database_url` at runtime in `env.py` so we never hard-code credentials.

### 3.3 Configure `alembic/env.py`

Replace the generated `env.py` with an async-compatible version:

```python
# backend/alembic/env.py
import asyncio
import sys
from pathlib import Path

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import pool

# Put src/ on the path so models are importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import get_settings

# Import ALL models so Base.metadata is fully populated
from db.models import (  # noqa: F401 — side-effect imports
    users, tenants, accounts, transactions, goals, budgets,
    imports, recurring, reporting, categories, system, tax, securities,
)
from db.models.base import Base

settings = get_settings()
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit SQL to stdout — used for dry-runs and review."""
    context.configure(
        url=settings.admin_database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations against a live database using the async engine."""
    engine = create_async_engine(
        settings.admin_database_url,
        poolclass=pool.NullPool,  # migrations should never pool connections
    )
    async with engine.begin() as conn:
        await conn.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

### 3.4 Migration Workflow

```bash
# Generate a new migration (auto-detects ORM changes vs DB state)
alembic revision --autogenerate -m "description_of_change"

# Apply all pending migrations
alembic upgrade head

# Roll back one migration
alembic downgrade -1

# Show migration history
alembic history --verbose

# Show current DB revision
alembic current
```

### 3.5 Initial Baseline Migration

After Alembic is configured and the database already has the Phase 1 schema applied, stamp the current state without re-running DDL:

```bash
alembic stamp head
```

If starting from a clean database, generate the first migration from the current ORM state:

```bash
alembic revision --autogenerate -m "baseline_phase1_schema"
alembic upgrade head
```

---

## 4. Phase B — Add `tenant_id` to Missing Models

### 4.1 ORM Model Changes

For each model in section 2.2, apply the following pattern:

```python
# BEFORE (old user-scoped pattern)
class Budget(Base):
    __tablename__ = "budgets"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    ...

# AFTER (tenant-scoped)
class Budget(TenantScopedMixin, Base):
    __tablename__ = "budgets"
    # Remove user_id FK — tenant_id from mixin provides isolation via RLS
    ...
```

> [!IMPORTANT]
> The `user_id` column is **removed** from tenant-scoped models. Ownership is tracked at the tenant level (who created the tenant is in `tenants.created_by_user_id`). Individual row ownership within a tenant should be tracked via `audit_log`, not a `user_id` column on every table.

#### 4.1.1 `db/models/budgets.py`

```python
from db.models.base import Base, TenantScopedMixin
from sqlalchemy import String, Numeric, Date, Boolean, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from decimal import Decimal
from datetime import date

class Budget(TenantScopedMixin, Base):
    __tablename__ = "budgets"
    name: Mapped[str] = mapped_column(String, nullable=False)
    period_type: Mapped[str] = mapped_column(String, nullable=False, default="MONTHLY")
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        CheckConstraint("period_type IN ('MONTHLY','QUARTERLY','ANNUAL','CUSTOM')", name="ck_budget_period"),
    )
    items: Mapped[list["BudgetItem"]] = relationship(back_populates="budget", cascade="all, delete-orphan")


class BudgetItem(TenantScopedMixin, Base):
    __tablename__ = "budget_items"
    budget_id: Mapped[int] = mapped_column(ForeignKey("budgets.id", ondelete="CASCADE"), nullable=False)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    planned_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)

    budget: Mapped["Budget"] = relationship(back_populates="items")
```

#### 4.1.2 `db/models/goals.py`

```python
from db.models.base import Base, TenantScopedMixin

class Goal(TenantScopedMixin, Base):
    __tablename__ = "goals"
    name: Mapped[str] = mapped_column(String, nullable=False)
    goal_type: Mapped[str] = mapped_column(String, nullable=False)
    target_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    current_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    sip_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    expected_return_rate: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    currency_code: Mapped[str] = mapped_column(String, nullable=False, default="INR")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)

    milestones: Mapped[list["GoalMilestone"]] = relationship(back_populates="goal", cascade="all, delete-orphan")
    contributions: Mapped[list["GoalContribution"]] = relationship(back_populates="goal", cascade="all, delete-orphan")
    account_mappings: Mapped[list["GoalAccountMapping"]] = relationship(back_populates="goal", cascade="all, delete-orphan")

class GoalMilestone(TenantScopedMixin, Base):
    __tablename__ = "goal_milestones"
    goal_id: Mapped[int] = mapped_column(ForeignKey("goals.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    target_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_achieved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    goal: Mapped["Goal"] = relationship(back_populates="milestones")

class GoalContribution(TenantScopedMixin, Base):
    __tablename__ = "goal_contributions"
    goal_id: Mapped[int] = mapped_column(ForeignKey("goals.id", ondelete="CASCADE"), nullable=False)
    transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.id"), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    contribution_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    goal: Mapped["Goal"] = relationship(back_populates="contributions")

class GoalAccountMapping(TenantScopedMixin, Base):
    __tablename__ = "goal_account_mappings"
    goal_id: Mapped[int] = mapped_column(ForeignKey("goals.id", ondelete="CASCADE"), nullable=False)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    goal: Mapped["Goal"] = relationship(back_populates="account_mappings")
```

#### 4.1.3 `db/models/imports.py`

```python
class ImportBatch(TenantScopedMixin, Base):
    __tablename__ = "import_batches"
    # Remove user_id — tenant_id provides isolation
    filename: Mapped[str] = mapped_column(String, nullable=False)
    file_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    source_type: Mapped[str] = mapped_column(String, nullable=False)
    format: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="PENDING")
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"), nullable=True)
```

#### 4.1.4 `db/models/recurring.py`

```python
class RecurringTransaction(TenantScopedMixin, Base):
    __tablename__ = "recurring_transactions"
    description: Mapped[str] = mapped_column(String, nullable=False)
    transaction_type: Mapped[str] = mapped_column(String, nullable=False)
    frequency: Mapped[str] = mapped_column(String, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)

    lines: Mapped[list["RecurringTransactionLine"]] = relationship(
        back_populates="recurring_transaction", cascade="all, delete-orphan"
    )

class RecurringTransactionLine(TenantScopedMixin, Base):
    __tablename__ = "recurring_transaction_lines"
    recurring_transaction_id: Mapped[int] = mapped_column(
        ForeignKey("recurring_transactions.id", ondelete="CASCADE"), nullable=False
    )
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    line_type: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    recurring_transaction: Mapped["RecurringTransaction"] = relationship(back_populates="lines")
```

#### 4.1.5 `db/models/reporting.py`

```python
class MonthlySnapshot(TenantScopedMixin, Base):
    __tablename__ = "monthly_snapshots"
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    snapshot_year: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_month: Mapped[int] = mapped_column(Integer, nullable=False)
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    closing_balance: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    total_debits: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    total_credits: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("tenant_id", "account_id", "snapshot_year", "snapshot_month",
                         name="uq_snapshot_tenant_account_period"),
    )

class NetWorthHistory(TenantScopedMixin, Base):
    __tablename__ = "net_worth_history"
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_assets: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    total_liabilities: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    net_worth: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)

class SavedReport(TenantScopedMixin, Base):
    __tablename__ = "saved_reports"
    name: Mapped[str] = mapped_column(String, nullable=False)
    report_type: Mapped[str] = mapped_column(String, nullable=False)
    parameters_json: Mapped[str | None] = mapped_column(String, nullable=True)
    # parameters_json should be JSONB in PostgreSQL — update column type when renaming
```

#### 4.1.6 `db/models/categories.py`

```python
class Payee(TenantScopedMixin, Base):
    __tablename__ = "payees"
    name: Mapped[str] = mapped_column(String, nullable=False)
    category_hint: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_payee_tenant_name"),
    )

class Tag(TenantScopedMixin, Base):
    __tablename__ = "tags"
    name: Mapped[str] = mapped_column(String, nullable=False)
    color_hex: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_tag_tenant_name"),
    )

class TransactionTag(TenantScopedMixin, Base):
    __tablename__ = "transaction_tags"
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "transaction_id", "tag_id", name="uq_txn_tag"),
    )

class UserCategoryRule(TenantScopedMixin, Base):
    """Replaces the user_id (str) scoping with proper tenant_id + user_id (int) scoping."""
    __tablename__ = "user_category_rules"
    pattern: Mapped[str] = mapped_column(String, nullable=False)
    category_name: Mapped[str] = mapped_column(String, nullable=False)
    match_type: Mapped[str] = mapped_column(String, nullable=False, default="CONTAINS")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
```

#### 4.1.7 `db/models/system.py`

```python
class LlmProvider(TenantScopedMixin, Base):
    """Per-tenant LLM provider configuration."""
    __tablename__ = "llm_providers"
    provider_id: Mapped[str] = mapped_column(String, nullable=False)
    provider_name: Mapped[str] = mapped_column(String, nullable=False)
    api_key: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # user_id (str) removed — provider is now tenant-scoped, not user-scoped

class AppSetting(TenantScopedMixin, Base):
    """Per-tenant application settings key-value store."""
    __tablename__ = "app_settings"
    setting_key: Mapped[str] = mapped_column(String, nullable=False)
    setting_value: Mapped[str | None] = mapped_column(String, nullable=True)
    setting_type: Mapped[str] = mapped_column(String, nullable=False, default="STRING")
    category: Mapped[str] = mapped_column(String, nullable=False, default="GENERAL")
    description: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "setting_key", name="uq_setting_tenant_key"),
        CheckConstraint(
            "setting_type IN ('STRING','INTEGER','REAL','BOOLEAN','DATE','JSON')",
            name="ck_setting_type",
        ),
    )

class AuditLog(TenantScopedMixin, Base):
    """Append-only audit trail. RLS: INSERT + SELECT only (no UPDATE/DELETE)."""
    __tablename__ = "audit_log"
    entity_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    action: Mapped[str] = mapped_column(String, nullable=False)
    # CREATED, UPDATED, DELETED, IMPORTED, EXPORTED, LOGIN, etc.
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    old_values_json: Mapped[str | None] = mapped_column(String, nullable=True)
    new_values_json: Mapped[str | None] = mapped_column(String, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String, nullable=True)

class Notification(TenantScopedMixin, Base):
    __tablename__ = "notifications"
    recipient_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str] = mapped_column(String, nullable=False)
    notification_type: Mapped[str] = mapped_column(String, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

#### 4.1.8 `db/models/tax.py`

```python
class TaxLot(TenantScopedMixin, Base):
    __tablename__ = "tax_lots"
    security_id: Mapped[int] = mapped_column(ForeignKey("securities.id"), nullable=False)
    brokerage_account_id: Mapped[int] = mapped_column(ForeignKey("brokerage_accounts.id"), nullable=False)
    acquisition_date: Mapped[date] = mapped_column(Date, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    cost_per_unit: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    remaining_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.id"), nullable=True)

class TaxLotDisposal(TenantScopedMixin, Base):
    __tablename__ = "tax_lot_disposals"
    tax_lot_id: Mapped[int] = mapped_column(ForeignKey("tax_lots.id"), nullable=False)
    disposal_date: Mapped[date] = mapped_column(Date, nullable=False)
    quantity_disposed: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    sale_price_per_unit: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.id"), nullable=True)

class TaxSectionMapping(TenantScopedMixin, Base):
    """Custom per-tenant overrides for tax section assignments."""
    __tablename__ = "tax_section_mappings"
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    tax_section_id: Mapped[int] = mapped_column(ForeignKey("tax_sections.id"), nullable=False)
    override_notes: Mapped[str | None] = mapped_column(String, nullable=True)
```

#### 4.1.9 `db/models/securities.py`

```python
class FoPosition(TenantScopedMixin, Base):
    __tablename__ = "fo_positions"
    brokerage_account_id: Mapped[int] = mapped_column(ForeignKey("brokerage_accounts.id"), nullable=False)
    fo_contract_id: Mapped[int] = mapped_column(ForeignKey("fo_contracts.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    avg_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    position_date: Mapped[date] = mapped_column(Date, nullable=False)

class HoldingsSummary(TenantScopedMixin, Base):
    __tablename__ = "holdings_summary"
    security_id: Mapped[int] = mapped_column(ForeignKey("securities.id"), nullable=False)
    brokerage_account_id: Mapped[int] = mapped_column(ForeignKey("brokerage_accounts.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    avg_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "security_id", "brokerage_account_id",
                         name="uq_holdings_tenant_sec_brok"),
    )
```

### 4.2 Alembic Migration for Phase B

After applying the model changes above, generate a single migration:

```bash
alembic revision --autogenerate -m "add_tenant_id_to_missing_models"
```

**Review the generated migration carefully** before applying. Key things to verify:

1. Every `ADD COLUMN tenant_id UUID NOT NULL` must have a **data migration step** to populate existing rows before the `NOT NULL` constraint is added. For tables with existing data use a two-step migration:

```python
# In the generated migration's upgrade() function, split it:

# Step 1: Add as nullable
op.add_column('budgets', sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True))

# Step 2: Back-fill existing rows with the default/system tenant or NULL cleanup
# (Only needed if you have existing data; in a fresh install, skip this step)
op.execute("""
    UPDATE budgets SET tenant_id = (
        SELECT t.id FROM tenants t
        JOIN tenant_memberships tm ON tm.tenant_id = t.id
        WHERE tm.user_id = budgets.user_id
        ORDER BY tm.created_at ASC
        LIMIT 1
    )
    WHERE tenant_id IS NULL
""")

# Step 3: Add NOT NULL constraint and FK
op.alter_column('budgets', 'tenant_id', nullable=False)
op.create_foreign_key('fk_budgets_tenant_id', 'budgets', 'tenants', ['tenant_id'], ['id'], ondelete='CASCADE')
op.create_index('idx_budgets_tenant', 'budgets', ['tenant_id'])
```

2. For tables that had `user_id` but are becoming tenant-scoped, add `DROP COLUMN user_id` **after** verifying no data is lost. This must be its own separate migration after data validation.

3. **Enable RLS** on newly tenant-scoped tables in the migration:

```python
# At the end of upgrade(), enable RLS on new tables
tenant_tables = [
    "budgets", "budget_items", "goals", "goal_milestones",
    "goal_contributions", "goal_account_mappings",
    "import_batches", "recurring_transactions", "recurring_transaction_lines",
    "monthly_snapshots", "net_worth_history", "saved_reports",
    "tax_lots", "tax_lot_disposals", "tax_section_mappings",
    "payees", "tags", "transaction_tags", "user_category_rules",
    "llm_providers", "app_settings", "audit_log", "notifications",
    "fo_positions", "holdings_summary",
]
for table in tenant_tables:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(f"""
        CREATE POLICY tenant_isolation ON {table}
            AS PERMISSIVE FOR ALL TO app_service
            USING (tenant_id = current_tenant_id())
            WITH CHECK (tenant_id = current_tenant_id())
    """)
```

Exception — `audit_log` uses the insert-only policy from the Phase 1 spec instead of the default `tenant_isolation` policy.

---

## 5. Phase C — Router Migration to Async + TenantDBSession

### 5.1 Migration Pattern

Every router file follows the same transformation:

```python
# ─── BEFORE ──────────────────────────────────────────────────────────────────
from sqlalchemy.orm import Session
from api.deps import DBSession, CurrentUser

@router.get("/budgets")
def list_budgets(
    session: DBSession,
    user_id: CurrentUser,
):
    uid = int(user_id)
    result = session.scalars(select(Budget).where(Budget.user_id == uid))
    return result.all()

# ─── AFTER ───────────────────────────────────────────────────────────────────
from sqlalchemy.ext.asyncio import AsyncSession
from api.deps import TenantDBSession, CurrentUserPayload

@router.get("/budgets")
async def list_budgets(
    session: TenantDBSession,     # sets app.tenant_id + app.user_id; RLS enforced
    auth: CurrentUserPayload,     # provides user_id, tenant_id, role
):
    # No WHERE clause needed — RLS filters by tenant automatically
    result = await session.execute(select(Budget))
    return result.scalars().all()
```

**Three specific changes per endpoint:**
1. `def` → `async def`
2. `DBSession` → `TenantDBSession`; `Session` import removed
3. `CurrentUser` → `CurrentUserPayload`; remove manual `user_id == uid` WHERE clauses

### 5.2 Repository Migration Pattern

Repositories already accept `AsyncSession` in their constructors. The issue is that routers pass a sync `Session` to them. After the router change, this mismatch is resolved automatically.

```python
# BEFORE — router passes sync Session; repo breaks
session: DBSession  # sync Session object
repo = AccountRepository(session)  # designed for AsyncSession; mismatch

# AFTER — router passes AsyncSession; repo works correctly
session: TenantDBSession  # AsyncSession, tenant context set
repo = AccountRepository(session)  # correct
```

### 5.3 Service Layer Migration

Services that currently accept `Session` (sync) must be updated to `AsyncSession`:

```python
# backend/src/services/transaction_service.py

# BEFORE
class TransactionService:
    def __init__(self, session: Session):  # sync
        self.txn_repo = TransactionRepository(session)

# AFTER
class TransactionService:
    def __init__(self, session: AsyncSession):  # async
        self.txn_repo = TransactionRepository(session)

    async def get_transactions(self, ...):  # async methods
        ...
```

### 5.4 Router-by-Router Migration Guide

#### 5.4.1 `api/routers/accounts.py`

**Changes required:**
- Replace `DBSession` → `TenantDBSession`
- Replace `CurrentUser` → `CurrentUserPayload`
- Convert all endpoint functions to `async def`
- Replace `session.scalar(...)` → `await session.scalar(...)`
- Replace `session.execute(...)` → `await session.execute(...)`
- Replace `session.scalars(...)` → `(await session.execute(...)).scalars()`
- Remove all `WHERE Account.user_id == uid` filters (RLS replaces them)
- Remove system account fallback (`user_id IS NULL`) — system accounts should now be seeded per-tenant during `provision_new_user`
- `session.add(...)` and `session.flush()` → `session.add(...); await session.flush()`

**Role guard additions:**
```python
# Deleting accounts requires ADMIN or OWNER
@router.delete("/{account_id}", dependencies=[require_role("OWNER", "ADMIN")])
async def delete_account(...):
```

#### 5.4.2 `api/routers/budgets.py`

**Changes required:**
- Same async/session pattern as accounts
- Remove `WHERE Budget.user_id == uid` (now RLS-enforced via `tenant_id`)
- After model change (Phase B), `Budget.user_id` column no longer exists

#### 5.4.3 `api/routers/goals.py`

**Changes required:**
- Same async/session pattern
- Goals router uses `SqlAlchemyGoalRepository` — verify it accepts `AsyncSession` and uses `await`
- Remove `user_id`-based `list(user_id=uid)` calls from repo

#### 5.4.4 `api/routers/transactions.py`

**Changes required:**
- Same async/session pattern
- `TransactionService.__init__` must accept `AsyncSession` (section 5.3)
- Remove any `WHERE Transaction.user_id == uid` filters
- `txn_hash` dedup check: after Phase B, the unique constraint is `(tenant_id, txn_hash)`, so duplicate detection works per-tenant automatically

#### 5.4.5 `api/routers/reports.py`

**Changes required:**
- Same async/session pattern
- Reports query `MonthlySnapshot`, `NetWorthHistory`, etc. — these will have `tenant_id` after Phase B
- Remove any manual `user_id` filters on reporting tables

#### 5.4.6 `api/routers/chat.py`

**Changes required:**
- Same async/session pattern
- Chat context builder queries several tables for context (goals, budgets, recent transactions)
- Replace `LlmProvider.user_id == user_id` with `TenantDBSession` (RLS filters by tenant_id after Phase B)

**Note:** `chat.py` passes `user_id` to sub-context functions. Replace all `user_id=user_id` params with `tenant_id=auth.tenant_id` where the data is tenant-scoped.

#### 5.4.7 `api/routers/dedup.py`

**Changes required:**
- Replace `DBSession` → `TenantDBSession`
- `AccountRepository(session)` already expects `AsyncSession`; remove `user_id` constructor arg
- `TransactionRepository.get_committed_hashes_for_account()`: remove `user_id` param — RLS enforces tenant isolation

#### 5.4.8 `api/routers/llm.py`

**Changes required:**
- Replace `DBSession` → `TenantDBSession`
- `LlmProvider` will have `tenant_id` after Phase B; remove `WHERE LlmProvider.user_id == user_id` queries

#### 5.4.9 `api/routers/pipeline.py` and `api/routers/proposals.py`

**Changes required:**
- Same async/session pattern
- These routers orchestrate parsing + normalization + approval; verify each stage passes the correct session

#### 5.4.10 `api/routers/categorize.py`

**Changes required:**
- `CategorizeService` currently accepts `user_id` string; update to accept `tenant_id`
- `UserCategoryRule` will have `tenant_id` after Phase B; category rules load per-tenant via RLS

#### 5.4.11 `api/routers/imports.py`

**Changes required:**
- Currently uses an in-memory `_batches` dict for job state — this is lost on process restart
- After Phase B, `ImportBatch` has `tenant_id`; persist batches to DB
- Replace in-memory dict with DB-backed session queries
- `user_id` batch filtering → RLS-based tenant filtering

#### 5.4.12 `api/routers/normalize.py` and `api/routers/parser.py`

**Changes required:**
- These routers are stateless (in-memory store only); no DB session changes needed
- Replace `CurrentUser` → `CurrentUserPayload` for tenant context on any batch lookups

#### 5.4.13 `api/routers/confidence.py`

**Changes required:**
- Fully stateless; only auth change: `CurrentUser` → `CurrentUserPayload`

### 5.5 Onboarding Router Migration

All onboarding routers follow the same pattern. The key additional change for onboarding is that they currently take `user_id` to create and look up accounts/institutions. After migration, these operations use `TenantDBSession` (which sets `app.tenant_id`), so RLS handles isolation and the `user_id` parameter serves only for audit purposes.

#### Common onboarding migration pattern:

```python
# BEFORE
@router.post("/institutions")
def create_institution(
    request: CreateInstitutionRequest,
    session: DBSession,
    user_id: CurrentUser,
):
    uid = _parse_user_id(user_id)
    inst = FinancialInstitution(user_id=uid, ...)
    session.add(inst)
    session.flush()
    return inst

# AFTER
@router.post("/institutions")
async def create_institution(
    request: CreateInstitutionRequest,
    session: TenantDBSession,
    auth: CurrentUserPayload,
):
    # tenant_id is set on the session context; RLS enforces isolation
    # FinancialInstitution inherits TenantScopedMixin — tenant_id must be set explicitly
    inst = FinancialInstitution(
        tenant_id=auth.tenant_id,  # explicit until trigger/default is added
        ...
    )
    session.add(inst)
    await session.flush()
    return inst
```

> [!TIP]
> To avoid having to pass `tenant_id=auth.tenant_id` on every model creation, add a PostgreSQL trigger or SQLAlchemy event listener that automatically sets `tenant_id = current_tenant_id()` on INSERT for all tenant-scoped tables. This is cleaner but optional.

#### 5.5.1 `onboarding/coa/router.py`

**Special case:** COA setup runs during provisioning (no user auth header). Add a separate admin-protected route for this, and the normal user-facing route should use `TenantDBSession`.

```python
# The provisioning path (called from auth.py during signup) must use admin_session
# The user-facing "reset CoA" path uses TenantDBSession + require_role("OWNER")
```

#### 5.5.2 `onboarding/orchestrator/router.py`

The orchestrator triggers the full onboarding sequence. After migration it should:
1. Use `TenantDBSession`
2. Pass `auth.tenant_id` to each step service
3. Mark `app_settings['onboarding_completed'] = '1'` via the AppSetting model (Phase B)

---

## 6. Dependency Update Reference

### 6.1 Import Changes

Every migrated router file must update its imports:

```python
# Remove
from sqlalchemy.orm import Session
from api.deps import DBSession, CurrentUser

# Add
from sqlalchemy.ext.asyncio import AsyncSession
from api.deps import TenantDBSession, CurrentUserPayload
# For role-guarded endpoints:
from api.deps import require_role
```

### 6.2 Dependency Injection in Service Constructors

Service classes that receive a session via `Depends` need updating too:

```python
# In deps.py — update service factories
def get_transaction_service(session: TenantDBSession):  # was DBSession
    from services.transaction_service import TransactionService
    return TransactionService(session)  # service now receives AsyncSession
```

### 6.3 `_parse_user_id` Helper Removal

Many onboarding routers call a helper `_parse_user_id(user_id: str) -> int` to convert the `CurrentUser` string. After switching to `CurrentUserPayload`, use `auth.user_id` directly (it is already a string of the int):

```python
# Remove this pattern
uid = _parse_user_id(user_id)

# Replace with
uid = int(auth.user_id)
```

---

## 7. RLS Policy for Newly Tenant-Scoped Tables

After Phase B adds `tenant_id` to the new models, the following PostgreSQL functions and policies must be created (via the Alembic migration as shown in section 4.2):

```sql
-- Verify current_tenant_id() and current_user_id() functions exist (from Phase 1)
-- If not, create them:
CREATE OR REPLACE FUNCTION current_tenant_id() RETURNS UUID
    LANGUAGE sql STABLE SECURITY DEFINER AS $$
        SELECT NULLIF(current_setting('app.tenant_id', TRUE), '')::UUID;
    $$;

CREATE OR REPLACE FUNCTION current_user_id() RETURNS BIGINT
    LANGUAGE sql STABLE SECURITY DEFINER AS $$
        SELECT NULLIF(current_setting('app.user_id', TRUE), '')::BIGINT;
    $$;
```

Special policy for `audit_log` (insert-only — from Phase 1 spec section 6.4):

```sql
-- audit_log: tenants can INSERT and SELECT their own records; no UPDATE or DELETE
CREATE POLICY audit_insert ON audit_log
    AS PERMISSIVE FOR INSERT TO app_service
    WITH CHECK (tenant_id = current_tenant_id());

CREATE POLICY audit_select ON audit_log
    AS PERMISSIVE FOR SELECT TO app_service
    USING (tenant_id = current_tenant_id());

CREATE POLICY audit_no_update ON audit_log AS RESTRICTIVE FOR UPDATE TO app_service USING (FALSE);
CREATE POLICY audit_no_delete ON audit_log AS RESTRICTIVE FOR DELETE TO app_service USING (FALSE);
```

---

## 8. Test Infrastructure Updates

### 8.1 Update `conftest.py` Tenant Tables List

The `postgres_engine` fixture in `backend/tests/conftest.py` explicitly lists tables to enable RLS on. This list must be extended to include all newly tenant-scoped tables from Phase B:

```python
# In the postgres_engine fixture
tenant_tables = [
    # Phase 1 tables (already in conftest)
    "transactions", "transaction_lines", "transaction_charges", "attachments",
    "accounts", "financial_institutions", "bank_accounts", "fixed_deposits",
    "credit_cards", "loans", "brokerage_accounts",
    # Phase B additions
    "budgets", "budget_items",
    "goals", "goal_milestones", "goal_contributions", "goal_account_mappings",
    "import_batches",
    "recurring_transactions", "recurring_transaction_lines",
    "monthly_snapshots", "net_worth_history", "saved_reports",
    "tax_lots", "tax_lot_disposals", "tax_section_mappings",
    "payees", "tags", "transaction_tags", "user_category_rules",
    "llm_providers", "app_settings",
    "audit_log",  # uses special insert-only policy (see section 7)
    "notifications",
    "fo_positions", "holdings_summary",
]
```

### 8.2 New Integration Tests

Add the following integration tests to `backend/tests/integration/test_multitenancy.py`:

```python
@pytest.mark.asyncio
async def test_budget_rls_isolation(db_session):
    """Tenant A's budgets are invisible to Tenant B."""
    ...

@pytest.mark.asyncio
async def test_goal_rls_isolation(db_session):
    """Tenant A's goals are invisible to Tenant B."""
    ...

@pytest.mark.asyncio
async def test_audit_log_no_delete(db_session):
    """app_service cannot DELETE from audit_log."""
    ...

@pytest.mark.asyncio
async def test_category_rules_rls(db_session):
    """Categorisation rules are tenant-scoped."""
    ...
```

### 8.3 Update Existing Unit Tests

Unit tests in `backend/tests/unit/` and `backend/tests/api/` that use `DBSession` or `Session` must be updated to use the async fixtures. The pattern:

```python
# BEFORE — sync session in tests
def test_create_budget(session: Session):
    budget = Budget(user_id=1, name="Monthly")
    session.add(budget)
    session.commit()

# AFTER — async session with tenant context
@pytest.mark.asyncio
async def test_create_budget(db_session: AsyncSession):
    # Set tenant context (done manually in tests; in production done by TenantDBSession dep)
    await db_session.execute(
        text("SELECT set_config('app.tenant_id', :tid, TRUE)"),
        {"tid": str(TENANT_A_ID)},
    )
    budget = Budget(tenant_id=TENANT_A_ID, name="Monthly")
    db_session.add(budget)
    await db_session.flush()
    assert budget.id is not None
```

---

## 9. Migration Execution Order

Execute the phases in this strict order to avoid constraint violations or data loss:

```
Phase A: Alembic setup
  └─ A1. Install alembic, run `alembic init alembic`
  └─ A2. Write env.py (async, reads from config)
  └─ A3. `alembic stamp head` (baseline existing Phase 1 schema)

Phase B: Model changes → Alembic migrations
  └─ B1. Update all ORM models (section 4.1)
  └─ B2. `alembic revision --autogenerate -m "add_tenant_id_phase_b"`
  └─ B3. Edit generated migration: add NOT NULL back-fill, FK, RLS
  └─ B4. `alembic upgrade head` (apply to dev DB)
  └─ B5. Separate migration: drop old user_id columns (after data validation)
  └─ B6. Update conftest.py tenant_tables list (section 8.1)
  └─ B7. Add integration tests (section 8.2)

Phase C: Router migration (can be done incrementally, router by router)
  └─ C1. Migrate service constructors to AsyncSession (section 5.3)
  └─ C2. Migrate routers in dependency order (section 5.4)
        Suggested order:
          1. accounts.py  (core — many others depend on it)
          2. transactions.py
          3. budgets.py
          4. goals.py
          5. reports.py
          6. dedup.py
          7. imports.py  (in-memory → DB-backed, larger change)
          8. categorize.py
          9. chat.py
          10. llm.py
          11. pipeline.py + proposals.py
          12. normalize.py + parser.py + confidence.py
          13. All onboarding/* routers
  └─ C3. Update unit + API tests to use async (section 8.3)
  └─ C4. Run full test suite: `pytest backend/tests/`
```

---

## 10. Breaking Changes and Rollout Notes

### 10.1 API Contract Changes

| Endpoint | Breaking Change | Migration Path |
|---|---|---|
| `POST /auth/signup` | Response changed from `{token}` to `{tenants[]}` | Frontend must call `/auth/select-tenant` to get token |
| `POST /auth/login` | Response changed from `{token}` to `{tenants[]}` | Frontend must call `/auth/select-tenant` to get token |
| All data endpoints | JWT must now contain `tenant_id` claim | Old tokens without `tenant_id` get 401 with `TOKEN_NO_TENANT` |
| `GET /budgets` | `user_id` filter removed; RLS replaces it | No change from client perspective |

### 10.2 JWT Migration

Tokens issued before Phase 1 (containing only `sub` but no `tenant_id`) will return `TOKEN_NO_TENANT` (401). Users must log in again to receive a scoped token.

### 10.3 Data Migration Risk

For any existing deployment with production data:
- All rows in non-tenant-scoped tables need a `tenant_id` back-filled before the `NOT NULL` constraint is applied (see section 4.2 back-fill logic)
- If a user had data but no `tenant_memberships` row, those rows cannot be back-filled and will need manual resolution
- Run the back-fill SQL in a transaction and verify `COUNT(*)` before committing

---

## 11. Acceptance Criteria

A complete implementation satisfies all of the following:

- [ ] `alembic history` shows a clean migration chain from baseline
- [ ] `alembic upgrade head` succeeds on a fresh database
- [ ] All 25+ models that need `tenant_id` have it, with RLS enabled and `tenant_isolation` policy applied
- [ ] `pytest backend/tests/integration/` passes with no failures, including `test_rls_isolation`
- [ ] No router file imports `from sqlalchemy.orm import Session` (all use `AsyncSession`)
- [ ] No router file uses `DBSession` (all use `TenantDBSession` or `get_admin_session`)
- [ ] No router file contains a manual `WHERE <model>.user_id == uid` filter on a tenant-scoped table
- [ ] `CurrentUser` dependency is only used in the auth router; all other routers use `CurrentUserPayload`
- [ ] `require_role("OWNER", "ADMIN")` guards are applied to all destructive operations (DELETE, bulk import, settings changes)
- [ ] `pytest backend/tests/` passes with no failures (unit + integration + parser tests)
