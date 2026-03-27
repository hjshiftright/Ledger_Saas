# Async Migration & Tenancy Completion Specification
## Ledger SaaS — Phase 2: Route Migration, Missing Tenant Columns, and Alembic

**Version:** 2.0
**Date:** March 27, 2026
**Scope:** Migrate ~28 sync route files to async `TenantDBSession`, add `tenant_id` to all missing models, and establish Alembic as the authoritative schema migration tool.
**Prerequisite:** Phase 1 spec (`postgresql-multitenancy-spec.md`) ORM and engine changes are in place.
**Database approach:** Clean slate — drop and recreate the database. No back-fill migrations required.

---

## 1. Executive Summary

Phase 1 established the multi-tenancy infrastructure: `TenantScopedMixin`, `TenantDBSession`, `UserTokenPayload`, the `admin_engine`, and the M:N auth flow. However, most of the application's ~28 route files are still using:

- **Sync SQLAlchemy** (`session.scalar()` instead of `await session.execute()`)
- **`DBSession`** (no tenant context) instead of **`TenantDBSession`** (sets `app.tenant_id` for RLS)
- **`CurrentUser`** (user_id string only) instead of **`CurrentUserPayload`** (user_id + tenant_id + role)
- **`user_id`-column isolation** instead of **RLS-enforced tenant isolation**

Additionally, 25+ ORM models are missing the `tenant_id` column entirely, so RLS cannot protect their data.

Since there is **no existing data**, the database can be dropped and recreated at any point. This eliminates all back-fill complexity: ORM models are updated to their final correct state, Alembic generates a single clean initial migration from scratch, and `alembic upgrade head` builds the entire schema in one step.

| Phase | Work | Files Affected |
|---|---|---|
| **A** | Drop DB + Alembic setup + single initial migration | `alembic/`, `alembic.ini`, `env.py` |
| **B** | Add `tenant_id` to all missing models | 10 ORM model files |
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

These models have `user_id` for isolation (or nothing at all) but do **not** inherit `TenantScopedMixin`, so PostgreSQL RLS cannot protect their rows:

| Model | File | Current Isolation | Phase 1 Spec Table |
|---|---|---|---|
| `Budget` | `db/models/budgets.py` | `user_id` FK | #21 |
| `BudgetItem` | `db/models/budgets.py` | via budget FK | #22 |
| `Goal` | `db/models/goals.py` | `user_id` FK | #17 |
| `GoalMilestone` | `db/models/goals.py` | via goal FK | #19 |
| `GoalContribution` | `db/models/goals.py` | via goal FK | #20 |
| `GoalAccountMapping` | `db/models/goals.py` | via goal FK | #18 |
| `ImportBatch` | `db/models/imports.py` | `user_id` FK | #27 |
| `RecurringTransaction` | `db/models/recurring.py` | none | #15 |
| `RecurringTransactionLine` | `db/models/recurring.py` | none | #16 |
| `MonthlySnapshot` | `db/models/reporting.py` | none | #23 |
| `NetWorthHistory` | `db/models/reporting.py` | none | #24 |
| `SavedReport` | `db/models/reporting.py` | none | #25 |
| `TaxLot` | `db/models/tax.py` | none | #30 |
| `TaxLotDisposal` | `db/models/tax.py` | none | #29 |
| `TaxSectionMapping` | `db/models/tax.py` | none | #33 |
| `Payee` | `db/models/categories.py` | none | #12 |
| `Tag` | `db/models/categories.py` | none | #13 |
| `TransactionTag` | `db/models/categories.py` | none | #14 |
| `UserCategoryRule` | `db/models/categories.py` | `user_id` str | — |
| `LlmProvider` | `db/models/system.py` | `user_id` str | — |
| `AppSetting` | `db/models/system.py` | none | #34 |
| `AuditLog` | `db/models/system.py` | `user_id` FK | #35 (⚡ hot) |
| `Notification` | `db/models/system.py` | `user_id` FK | #36 |
| `FoPosition` | `db/models/securities.py` | none | #31 |
| `HoldingsSummary` | `db/models/securities.py` | none | #32 |

---

## 3. Phase A — Database Reset + Alembic Setup

### 3.1 Drop and Recreate the Database

Since there is no data to preserve, start completely fresh:

```sql
-- Connect as superadmin or postgres system user
DROP DATABASE IF EXISTS ledger;
CREATE DATABASE ledger;

-- Recreate application roles (if they were dropped with the DB)
CREATE ROLE app_service LOGIN PASSWORD 'your_password' NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE ROLE superadmin LOGIN PASSWORD 'your_password' SUPERUSER;
CREATE ROLE readonly_analyst LOGIN PASSWORD 'your_password' NOSUPERUSER;

-- Grant baseline access
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON DATABASE ledger FROM PUBLIC;
GRANT CONNECT ON DATABASE ledger TO app_service;
GRANT CONNECT ON DATABASE ledger TO readonly_analyst;
GRANT USAGE ON SCHEMA public TO app_service;
GRANT USAGE ON SCHEMA public TO readonly_analyst;

-- Analyst bypasses RLS for cross-tenant reporting
ALTER ROLE readonly_analyst SET row_security = off;
```

### 3.2 Install and Initialise Alembic

```bash
# From backend/
pip install alembic
alembic init alembic
```

Directory structure after init:

```
backend/
  alembic/
    env.py            ← rewrite this (section 3.4)
    script.py.mako    ← migration file template
    versions/         ← generated migration files go here
  alembic.ini         ← update this (section 3.3)
```

### 3.3 Configure `alembic.ini`

```ini
[alembic]
script_location = alembic
file_template = %%(year)d%%(month).2d%%(day).2d_%%(rev)s_%%(slug)s
prepend_sys_path = src
# URL is intentionally blank — read from config in env.py
sqlalchemy.url =

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

### 3.4 Configure `alembic/env.py`

Replace the generated file entirely:

```python
# backend/alembic/env.py
import asyncio
import sys
from pathlib import Path

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import pool

# Put backend/src on the path so all app modules are importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import get_settings

# Import every model module so Base.metadata is fully populated before
# Alembic compares it against the live database schema.
from db.models import (  # noqa: F401
    users, tenants, accounts, transactions,
    goals, budgets, imports, recurring,
    reporting, categories, system, tax, securities,
)
from db.models.base import Base

settings = get_settings()
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit SQL to stdout without connecting to the database.
    Useful for reviewing what will be applied before running it.
    """
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


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Apply migrations against a live database via the async engine."""
    engine = create_async_engine(
        settings.admin_database_url,
        poolclass=pool.NullPool,  # migrations should not pool connections
    )
    async with engine.begin() as conn:
        await conn.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

### 3.5 Generate the Initial Migration

After completing **all** ORM model changes in Phase B, generate a single initial migration that creates the entire schema from scratch:

```bash
# From backend/
alembic revision --autogenerate -m "initial_schema"
```

This produces one file in `alembic/versions/`. Open it and **append the RLS setup** at the end of `upgrade()` (see section 3.6). Then apply it:

```bash
alembic upgrade head
```

### 3.6 RLS Infrastructure in the Initial Migration

At the end of the generated `upgrade()` function, add the PostgreSQL RLS setup. This must be part of the migration so that `alembic upgrade head` on any fresh database is fully self-contained:

```python
def upgrade() -> None:
    # --- auto-generated DDL above this line ---

    # ── Helper functions ────────────────────────────────────────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION current_tenant_id() RETURNS UUID
            LANGUAGE sql STABLE SECURITY DEFINER AS $$
                SELECT NULLIF(current_setting('app.tenant_id', TRUE), '')::UUID;
            $$
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION current_user_id() RETURNS BIGINT
            LANGUAGE sql STABLE SECURITY DEFINER AS $$
                SELECT NULLIF(current_setting('app.user_id', TRUE), '')::BIGINT;
            $$
    """)

    # ── Grants for app_service ───────────────────────────────────────────────
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_service")
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_service")
    op.execute("GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_analyst")

    # ── Global tables: read-only for app_service ─────────────────────────────
    # app_service can SELECT; only superadmin can mutate.
    for global_table in ["securities", "security_prices", "fo_contracts",
                          "tax_sections", "currencies", "exchange_rates"]:
        op.execute(f"ALTER TABLE {global_table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {global_table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY global_read ON {global_table}
                AS PERMISSIVE FOR SELECT TO app_service, readonly_analyst
                USING (TRUE)
        """)
        op.execute(f"""
            CREATE POLICY global_write_block ON {global_table}
                AS RESTRICTIVE FOR INSERT, UPDATE, DELETE TO app_service
                USING (FALSE)
        """)

    # ── users table: global identity, selective RLS ───────────────────────────
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE users FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY users_select ON users
            AS PERMISSIVE FOR SELECT TO app_service USING (TRUE)
    """)
    op.execute("""
        CREATE POLICY users_update ON users
            AS PERMISSIVE FOR UPDATE TO app_service
            USING (id = current_user_id())
    """)
    op.execute("""
        CREATE POLICY users_insert_block ON users
            AS RESTRICTIVE FOR INSERT TO app_service USING (FALSE)
    """)

    # ── tenant_memberships: cross-tenant visibility ───────────────────────────
    op.execute("ALTER TABLE tenant_memberships ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE tenant_memberships FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY membership_select ON tenant_memberships
            AS PERMISSIVE FOR SELECT TO app_service
            USING (
                tenant_id = current_tenant_id()
                OR user_id = current_user_id()
            )
    """)
    op.execute("""
        CREATE POLICY membership_write ON tenant_memberships
            AS PERMISSIVE FOR INSERT, UPDATE, DELETE TO app_service
            USING (tenant_id = current_tenant_id())
    """)

    # ── Standard tenant isolation policy (all tenant-scoped tables) ───────────
    standard_tenant_tables = [
        # Phase 1 tables
        "accounts", "financial_institutions", "bank_accounts", "fixed_deposits",
        "credit_cards", "loans", "brokerage_accounts",
        "transactions", "transaction_lines", "transaction_charges", "attachments",
        # Phase B tables
        "budgets", "budget_items",
        "goals", "goal_milestones", "goal_contributions", "goal_account_mappings",
        "import_batches",
        "recurring_transactions", "recurring_transaction_lines",
        "monthly_snapshots", "net_worth_history", "saved_reports",
        "tax_lots", "tax_lot_disposals", "tax_section_mappings",
        "payees", "tags", "transaction_tags", "user_category_rules",
        "llm_providers", "app_settings",
        "notifications",
        "fo_positions", "holdings_summary",
    ]
    for table in standard_tenant_tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY tenant_isolation ON {table}
                AS PERMISSIVE FOR ALL TO app_service
                USING (tenant_id = current_tenant_id())
                WITH CHECK (tenant_id = current_tenant_id())
        """)

    # ── audit_log: insert + select only; no update or delete ─────────────────
    op.execute("ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_log FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY audit_insert ON audit_log
            AS PERMISSIVE FOR INSERT TO app_service
            WITH CHECK (tenant_id = current_tenant_id())
    """)
    op.execute("""
        CREATE POLICY audit_select ON audit_log
            AS PERMISSIVE FOR SELECT TO app_service
            USING (tenant_id = current_tenant_id())
    """)
    op.execute("""
        CREATE POLICY audit_no_update ON audit_log
            AS RESTRICTIVE FOR UPDATE TO app_service USING (FALSE)
    """)
    op.execute("""
        CREATE POLICY audit_no_delete ON audit_log
            AS RESTRICTIVE FOR DELETE TO app_service USING (FALSE)
    """)


def downgrade() -> None:
    # Drop all policies before dropping tables
    # (Alembic auto-generates the DROP TABLE statements; policies are dropped with the table)
    op.execute("DROP FUNCTION IF EXISTS current_tenant_id()")
    op.execute("DROP FUNCTION IF EXISTS current_user_id()")
    # --- auto-generated DROP TABLE statements below ---
```

### 3.7 Ongoing Migration Workflow

For every future schema change:

```bash
# 1. Update the ORM model in Python
# 2. Generate the migration
alembic revision --autogenerate -m "short_description"

# 3. Review the generated file in alembic/versions/ before applying
# 4. Apply
alembic upgrade head

# Roll back one step if needed
alembic downgrade -1

# Inspect history
alembic history --verbose
alembic current
```

---

## 4. Phase B — Add `tenant_id` to All Missing Models

Update each ORM model file as specified below. Since the database is dropped and recreated, these are **final column definitions** — no back-fill, no nullable transitional step.

The rule for every model in this section:
- Add `TenantScopedMixin` as the **first** parent class (before `Base`)
- Remove `user_id` FK column — tenant isolation replaces it
- `tenant_id` comes from the mixin automatically

### 4.1 `db/models/budgets.py`

```python
from datetime import date
from decimal import Decimal
from sqlalchemy import String, Numeric, Date, Boolean, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.models.base import Base, TenantScopedMixin


class Budget(TenantScopedMixin, Base):
    __tablename__ = "budgets"

    name: Mapped[str] = mapped_column(String, nullable=False)
    period_type: Mapped[str] = mapped_column(String, nullable=False, default="MONTHLY")
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "period_type IN ('MONTHLY','QUARTERLY','ANNUAL','CUSTOM')",
            name="ck_budget_period_type",
        ),
    )

    items: Mapped[list["BudgetItem"]] = relationship(
        back_populates="budget", cascade="all, delete-orphan"
    )


class BudgetItem(TenantScopedMixin, Base):
    __tablename__ = "budget_items"

    budget_id: Mapped[int] = mapped_column(
        ForeignKey("budgets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    planned_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)

    budget: Mapped["Budget"] = relationship(back_populates="items")
```

### 4.2 `db/models/goals.py`

```python
from datetime import date
from decimal import Decimal
from sqlalchemy import String, Numeric, Date, Boolean, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
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

    milestones: Mapped[list["GoalMilestone"]] = relationship(
        back_populates="goal", cascade="all, delete-orphan"
    )
    contributions: Mapped[list["GoalContribution"]] = relationship(
        back_populates="goal", cascade="all, delete-orphan"
    )
    account_mappings: Mapped[list["GoalAccountMapping"]] = relationship(
        back_populates="goal", cascade="all, delete-orphan"
    )


class GoalMilestone(TenantScopedMixin, Base):
    __tablename__ = "goal_milestones"

    goal_id: Mapped[int] = mapped_column(
        ForeignKey("goals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    target_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_achieved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    goal: Mapped["Goal"] = relationship(back_populates="milestones")


class GoalContribution(TenantScopedMixin, Base):
    __tablename__ = "goal_contributions"

    goal_id: Mapped[int] = mapped_column(
        ForeignKey("goals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("transactions.id"), nullable=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    contribution_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)

    goal: Mapped["Goal"] = relationship(back_populates="contributions")


class GoalAccountMapping(TenantScopedMixin, Base):
    __tablename__ = "goal_account_mappings"

    goal_id: Mapped[int] = mapped_column(
        ForeignKey("goals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)

    goal: Mapped["Goal"] = relationship(back_populates="account_mappings")
```

### 4.3 `db/models/imports.py`

```python
from sqlalchemy import String, Integer, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from db.models.base import Base, TenantScopedMixin


class ImportBatch(TenantScopedMixin, Base):
    __tablename__ = "import_batches"

    filename: Mapped[str] = mapped_column(String, nullable=False)
    file_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    source_type: Mapped[str] = mapped_column(String, nullable=False)
    format: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="PENDING")
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING','PROCESSING','COMPLETED','FAILED','CANCELLED')",
            name="ck_import_batch_status",
        ),
    )
```

### 4.4 `db/models/recurring.py`

```python
from datetime import date
from decimal import Decimal
from sqlalchemy import String, Numeric, Date, Boolean, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.models.base import Base, TenantScopedMixin


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

    __table_args__ = (
        CheckConstraint(
            "frequency IN ('DAILY','WEEKLY','FORTNIGHTLY','MONTHLY','QUARTERLY','ANNUAL')",
            name="ck_recurring_frequency",
        ),
    )

    lines: Mapped[list["RecurringTransactionLine"]] = relationship(
        back_populates="recurring_transaction", cascade="all, delete-orphan"
    )


class RecurringTransactionLine(TenantScopedMixin, Base):
    __tablename__ = "recurring_transaction_lines"

    recurring_transaction_id: Mapped[int] = mapped_column(
        ForeignKey("recurring_transactions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    line_type: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)

    recurring_transaction: Mapped["RecurringTransaction"] = relationship(back_populates="lines")
```

### 4.5 `db/models/reporting.py`

```python
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import String, Numeric, Date, DateTime, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from db.models.base import Base, TenantScopedMixin


class MonthlySnapshot(TenantScopedMixin, Base):
    __tablename__ = "monthly_snapshots"

    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False, index=True)
    snapshot_year: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_month: Mapped[int] = mapped_column(Integer, nullable=False)
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    closing_balance: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    total_debits: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    total_credits: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "account_id", "snapshot_year", "snapshot_month",
            name="uq_snapshot_tenant_account_period",
        ),
    )


class NetWorthHistory(TenantScopedMixin, Base):
    __tablename__ = "net_worth_history"

    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    total_assets: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    total_liabilities: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    net_worth: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)


class SavedReport(TenantScopedMixin, Base):
    __tablename__ = "saved_reports"

    name: Mapped[str] = mapped_column(String, nullable=False)
    report_type: Mapped[str] = mapped_column(String, nullable=False)
    parameters_json: Mapped[str | None] = mapped_column(String, nullable=True)
    is_shared: Mapped[bool] = mapped_column(
        __import__("sqlalchemy").Boolean, nullable=False, default=False
    )
```

### 4.6 `db/models/categories.py`

```python
from sqlalchemy import String, Boolean, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from db.models.base import Base, TenantScopedMixin


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

    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"), nullable=False, index=True
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "transaction_id", "tag_id", name="uq_txn_tag"),
    )


class UserCategoryRule(TenantScopedMixin, Base):
    """Categorisation rules — tenant-scoped, replacing the old user_id (str) pattern."""
    __tablename__ = "user_category_rules"

    pattern: Mapped[str] = mapped_column(String, nullable=False)
    category_name: Mapped[str] = mapped_column(String, nullable=False)
    match_type: Mapped[str] = mapped_column(String, nullable=False, default="CONTAINS")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
```

### 4.7 `db/models/system.py`

```python
from datetime import datetime
from sqlalchemy import String, Boolean, ForeignKey, Integer, DateTime, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from db.models.base import Base, TenantScopedMixin


class LlmProvider(TenantScopedMixin, Base):
    """Per-tenant LLM provider configuration. Replaces the old user_id (str) pattern."""
    __tablename__ = "llm_providers"

    provider_id: Mapped[str] = mapped_column(String, nullable=False)
    provider_name: Mapped[str] = mapped_column(String, nullable=False)
    api_key: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


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
    """Append-only audit trail per tenant. RLS allows INSERT + SELECT only."""
    __tablename__ = "audit_log"

    entity_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    action: Mapped[str] = mapped_column(String, nullable=False)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    old_values_json: Mapped[str | None] = mapped_column(String, nullable=True)
    new_values_json: Mapped[str | None] = mapped_column(String, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String, nullable=True)


class Notification(TenantScopedMixin, Base):
    __tablename__ = "notifications"

    recipient_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str] = mapped_column(String, nullable=False)
    notification_type: Mapped[str] = mapped_column(String, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

### 4.8 `db/models/tax.py`

```python
from datetime import date
from decimal import Decimal
from sqlalchemy import String, Numeric, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from db.models.base import Base, TenantScopedMixin


class TaxLot(TenantScopedMixin, Base):
    __tablename__ = "tax_lots"

    security_id: Mapped[int] = mapped_column(ForeignKey("securities.id"), nullable=False)
    brokerage_account_id: Mapped[int] = mapped_column(
        ForeignKey("brokerage_accounts.id"), nullable=False
    )
    acquisition_date: Mapped[date] = mapped_column(Date, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    cost_per_unit: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    remaining_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.id"), nullable=True)


class TaxLotDisposal(TenantScopedMixin, Base):
    __tablename__ = "tax_lot_disposals"

    tax_lot_id: Mapped[int] = mapped_column(
        ForeignKey("tax_lots.id"), nullable=False, index=True
    )
    disposal_date: Mapped[date] = mapped_column(Date, nullable=False)
    quantity_disposed: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    sale_price_per_unit: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.id"), nullable=True)


class TaxSectionMapping(TenantScopedMixin, Base):
    """Per-tenant overrides for Indian IT Act section assignments on accounts."""
    __tablename__ = "tax_section_mappings"

    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    tax_section_id: Mapped[int] = mapped_column(ForeignKey("tax_sections.id"), nullable=False)
    override_notes: Mapped[str | None] = mapped_column(String, nullable=True)
```

### 4.9 `db/models/securities.py`

```python
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Numeric, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from db.models.base import Base, TenantScopedMixin


class FoPosition(TenantScopedMixin, Base):
    __tablename__ = "fo_positions"

    brokerage_account_id: Mapped[int] = mapped_column(
        ForeignKey("brokerage_accounts.id"), nullable=False, index=True
    )
    fo_contract_id: Mapped[int] = mapped_column(ForeignKey("fo_contracts.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    avg_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    position_date: Mapped[date] = mapped_column(Date, nullable=False)


class HoldingsSummary(TenantScopedMixin, Base):
    __tablename__ = "holdings_summary"

    security_id: Mapped[int] = mapped_column(ForeignKey("securities.id"), nullable=False)
    brokerage_account_id: Mapped[int] = mapped_column(
        ForeignKey("brokerage_accounts.id"), nullable=False
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    avg_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "security_id", "brokerage_account_id",
            name="uq_holdings_tenant_sec_brok",
        ),
    )
```

---

## 5. Phase C — Router Migration to Async + TenantDBSession

### 5.1 The Transformation Pattern

Every router file follows this identical transformation:

```python
# ─── BEFORE ──────────────────────────────────────────────────────────────────
from sqlalchemy.orm import Session
from api.deps import DBSession, CurrentUser

@router.get("/budgets")
def list_budgets(session: DBSession, user_id: CurrentUser):
    uid = int(user_id)
    result = session.scalars(select(Budget).where(Budget.user_id == uid))
    return result.all()

# ─── AFTER ───────────────────────────────────────────────────────────────────
from sqlalchemy.ext.asyncio import AsyncSession
from api.deps import TenantDBSession, CurrentUserPayload

@router.get("/budgets")
async def list_budgets(session: TenantDBSession, auth: CurrentUserPayload):
    # No WHERE clause — RLS filters by app.tenant_id automatically
    result = await session.execute(select(Budget))
    return result.scalars().all()
```

**Three changes per endpoint, no exceptions:**

| Old | New | Reason |
|---|---|---|
| `def` | `async def` | Required for `await` |
| `DBSession` | `TenantDBSession` | Sets `app.tenant_id` + `app.user_id` for RLS |
| `CurrentUser` | `CurrentUserPayload` | Provides `tenant_id` and `role`, not just `user_id` |
| `session.scalar(q)` | `await session.scalar(q)` | Async engine |
| `session.execute(q)` | `await session.execute(q)` | Async engine |
| `session.scalars(q)` | `(await session.execute(q)).scalars()` | Async engine |
| `session.flush()` | `await session.flush()` | Async engine |
| `.where(Model.user_id == uid)` | *(remove entirely)* | RLS replaces this |

### 5.2 Removing `_parse_user_id`

Many onboarding routers call `_parse_user_id(user_id: str) -> int` to convert the `CurrentUser` string to int. After switching to `CurrentUserPayload`, remove this helper and use `auth.user_id` directly:

```python
# Remove
uid = _parse_user_id(user_id)

# Replace with
uid = int(auth.user_id)
```

### 5.3 Service Layer — Update Constructors to `AsyncSession`

Services that currently accept a sync `Session` must be updated:

```python
# BEFORE
class TransactionService:
    def __init__(self, session: Session):  # sync
        ...

# AFTER
class TransactionService:
    def __init__(self, session: AsyncSession):
        ...

    # All service methods become async
    async def create_transaction(self, ...):
        ...
        await self.session.flush()
```

Update the service factory dependencies in `api/deps.py`:

```python
def get_transaction_service(session: TenantDBSession):  # was DBSession
    from services.transaction_service import TransactionService
    return TransactionService(session)
```

### 5.4 Router-by-Router Changes

#### `api/routers/accounts.py`
- Apply standard async transformation
- Remove all `WHERE Account.user_id == uid` filters — RLS handles this
- Remove system-account fallback (`WHERE user_id IS NULL`) — system accounts are now seeded per-tenant during `provision_new_user` and will be visible naturally via RLS
- Add role guard on destructive operations:
  ```python
  @router.delete("/{account_id}", dependencies=[require_role("OWNER", "ADMIN")])
  async def delete_account(...):
  ```

#### `api/routers/transactions.py`
- Apply standard async transformation
- `TransactionService` constructor update (section 5.3)
- `txn_hash` duplicate detection works automatically — the `UNIQUE(tenant_id, txn_hash)` constraint from Phase 1 is per-tenant
- Role guard on delete and void operations

#### `api/routers/budgets.py`
- Apply standard async transformation
- `Budget.user_id` column no longer exists after Phase B — remove all references

#### `api/routers/goals.py`
- Apply standard async transformation
- `SqlAlchemyGoalRepository` already accepts `AsyncSession` — the router change is sufficient
- Remove `repo.list(user_id=uid)` — replace with `repo.list()` (RLS filters by tenant)

#### `api/routers/reports.py`
- Apply standard async transformation
- `MonthlySnapshot`, `NetWorthHistory`, `SavedReport` all have `tenant_id` after Phase B — no WHERE changes needed

#### `api/routers/chat.py`
- Apply standard async transformation
- Replace all `user_id=user_id` arguments to sub-context functions with `tenant_id=auth.tenant_id`
- `LlmProvider.user_id` no longer exists after Phase B — query via RLS

#### `api/routers/dedup.py`
- Apply standard async transformation
- `AccountRepository(session)` — remove `user_id` constructor argument (no longer needed)
- `TransactionRepository.get_committed_hashes_for_account()` — remove `user_id` parameter

#### `api/routers/llm.py`
- Apply standard async transformation
- `LlmProvider` queries: remove `WHERE LlmProvider.user_id == user_id` — RLS filters by tenant

#### `api/routers/pipeline.py` and `api/routers/proposals.py`
- Apply standard async transformation
- Ensure each pipeline stage receives the same `AsyncSession` (do not open new sessions mid-request)

#### `api/routers/categorize.py`
- Apply standard async transformation
- `CategorizeService`: replace `user_id` parameter with `tenant_id` from `auth.tenant_id`
- `UserCategoryRule` queries now via RLS — no manual filter needed

#### `api/routers/imports.py`
- Currently backed by an in-memory `_batches` dict — this state is lost on process restart
- After Phase B, `ImportBatch` has `tenant_id`; migrate all batch state to the database
- Replace in-memory lookups with `await session.get(ImportBatch, batch_id)` queries
- Apply standard async transformation to all endpoints

#### `api/routers/normalize.py`, `api/routers/parser.py`, `api/routers/confidence.py`
- No DB session changes (in-memory only)
- Change `CurrentUser` → `CurrentUserPayload` for consistency
- All endpoint functions: `def` → `async def`

#### `onboarding/coa/router.py`
- Apply standard async transformation
- COA setup during signup is called from `auth.py` using the admin session; the user-facing "reset CoA" endpoint uses `TenantDBSession` with `require_role("OWNER")`

#### All other `onboarding/*` routers
- Apply standard async transformation
- When creating models that inherit `TenantScopedMixin`, set `tenant_id` explicitly from `auth.tenant_id`:
  ```python
  inst = FinancialInstitution(tenant_id=auth.tenant_id, name=request.name, ...)
  ```

> [!TIP]
> To avoid passing `tenant_id=auth.tenant_id` on every model instantiation, add a SQLAlchemy `@event.listens_for(Session, "before_flush")` listener that sets `tenant_id = current_tenant_id()` on any tenant-scoped model where `tenant_id` is `None`. This is optional but reduces boilerplate significantly.

---

## 6. Test Infrastructure Updates

### 6.1 Extend `conftest.py` Tenant Table List

The `postgres_engine` fixture in `backend/tests/conftest.py` lists tables to enable RLS on. Extend it with all Phase B tables:

```python
# In postgres_engine fixture — replace the existing tenant_tables list
tenant_tables = [
    # Phase 1 — already present
    "accounts", "financial_institutions", "bank_accounts", "fixed_deposits",
    "credit_cards", "loans", "brokerage_accounts",
    "transactions", "transaction_lines", "transaction_charges", "attachments",
    # Phase B additions
    "budgets", "budget_items",
    "goals", "goal_milestones", "goal_contributions", "goal_account_mappings",
    "import_batches",
    "recurring_transactions", "recurring_transaction_lines",
    "monthly_snapshots", "net_worth_history", "saved_reports",
    "tax_lots", "tax_lot_disposals", "tax_section_mappings",
    "payees", "tags", "transaction_tags", "user_category_rules",
    "llm_providers", "app_settings",
    "notifications",
    "fo_positions", "holdings_summary",
    # audit_log uses special insert-only policy — added separately below
]
for table in tenant_tables:
    await conn.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
    await conn.execute(text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))
    await conn.execute(text(f"""
        CREATE POLICY tenant_isolation ON {table}
            AS PERMISSIVE FOR ALL TO app_service
            USING (tenant_id = current_tenant_id())
            WITH CHECK (tenant_id = current_tenant_id())
    """))

# audit_log: insert + select only
await conn.execute(text("ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY"))
await conn.execute(text("ALTER TABLE audit_log FORCE ROW LEVEL SECURITY"))
await conn.execute(text("""
    CREATE POLICY audit_insert ON audit_log AS PERMISSIVE FOR INSERT TO app_service
    WITH CHECK (tenant_id = current_tenant_id())
"""))
await conn.execute(text("""
    CREATE POLICY audit_select ON audit_log AS PERMISSIVE FOR SELECT TO app_service
    USING (tenant_id = current_tenant_id())
"""))
await conn.execute(text("""
    CREATE POLICY audit_no_update ON audit_log AS RESTRICTIVE FOR UPDATE TO app_service USING (FALSE)
"""))
await conn.execute(text("""
    CREATE POLICY audit_no_delete ON audit_log AS RESTRICTIVE FOR DELETE TO app_service USING (FALSE)
"""))
```

### 6.2 Update Existing Tests

All existing unit and API tests that use `Session` (sync) must be updated to use `AsyncSession`. The pattern:

```python
# BEFORE — sync
def test_create_budget(session: Session):
    budget = Budget(user_id=1, name="Monthly")
    session.add(budget)
    session.commit()
    assert budget.id is not None

# AFTER — async with tenant context
@pytest.mark.asyncio
async def test_create_budget(db_session: AsyncSession):
    await db_session.execute(
        text("SELECT set_config('app.tenant_id', :tid, TRUE)"),
        {"tid": str(TENANT_A_ID)},
    )
    budget = Budget(tenant_id=TENANT_A_ID, name="Monthly")
    db_session.add(budget)
    await db_session.flush()
    assert budget.id is not None
```

### 6.3 Additional Integration Tests

Add to `backend/tests/integration/test_multitenancy.py`:

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
async def test_audit_log_insert_only(db_session):
    """app_service cannot UPDATE or DELETE audit_log rows."""
    ...

@pytest.mark.asyncio
async def test_category_rules_rls(db_session):
    """Categorisation rules from Tenant A are not visible to Tenant B."""
    ...

@pytest.mark.asyncio
async def test_import_batch_rls(db_session):
    """Import batches are scoped to the creating tenant."""
    ...
```

---

## 7. Execution Order

Execute in this order. Phases A and B must be fully complete before Phase C begins.

```
Phase A — Alembic setup (do this first, before any code changes)
  A1. DROP DATABASE ledger; CREATE DATABASE ledger; recreate roles
  A2. alembic init alembic
  A3. Write alembic.ini and env.py
  (Do NOT generate the migration yet — wait for Phase B to be complete)

Phase B — ORM model changes (all in one pass, then generate migration once)
  B1. Update db/models/budgets.py    (section 4.1)
  B2. Update db/models/goals.py      (section 4.2)
  B3. Update db/models/imports.py    (section 4.3)
  B4. Update db/models/recurring.py  (section 4.4)
  B5. Update db/models/reporting.py  (section 4.5)
  B6. Update db/models/categories.py (section 4.6)
  B7. Update db/models/system.py     (section 4.7)
  B8. Update db/models/tax.py        (section 4.8)
  B9. Update db/models/securities.py (section 4.9)
  B10. alembic revision --autogenerate -m "initial_schema"
  B11. Edit generated migration: append RLS setup block (section 3.6)
  B12. alembic upgrade head
  B13. Verify: psql -c "\dt" shows all tables; \d transactions shows tenant_id

Phase C — Router migration (one router at a time; run tests after each)
  Suggested order (most used / most depended-upon first):
  C1.  services/transaction_service.py + services/* (AsyncSession constructors)
  C2.  api/deps.py service factories (DBSession → TenantDBSession)
  C3.  api/routers/accounts.py
  C4.  api/routers/transactions.py
  C5.  api/routers/budgets.py
  C6.  api/routers/goals.py
  C7.  api/routers/reports.py
  C8.  api/routers/dedup.py
  C9.  api/routers/imports.py
  C10. api/routers/categorize.py
  C11. api/routers/chat.py
  C12. api/routers/llm.py
  C13. api/routers/pipeline.py + proposals.py
  C14. api/routers/normalize.py + parser.py + confidence.py
  C15. onboarding/coa/router.py
  C16. onboarding/institution/router.py
  C17. onboarding/account/router.py
  C18. onboarding/opening_balance/router.py
  C19. onboarding/networth/router.py
  C20. onboarding/dashboard/router.py
  C21. onboarding/orchestrator/router.py
  C22. onboarding/profile/router.py
  C23. Update tests (section 6.1, 6.2, 6.3)
  C24. pytest backend/tests/ — all green
```

---

## 8. Acceptance Criteria

A complete implementation satisfies all of the following:

- [ ] `alembic upgrade head` on a fresh empty database creates the full schema with no errors
- [ ] `alembic history` shows a single clean migration chain from `base` to `head`
- [ ] Every table in section 2.2 has a `tenant_id UUID NOT NULL` column (`\d <table>` in psql confirms)
- [ ] RLS is enabled on all tenant-scoped tables (`SELECT relname, relrowsecurity FROM pg_class WHERE relrowsecurity = true`)
- [ ] `pytest backend/tests/integration/` passes, including `test_rls_isolation` and all new tests from section 6.3
- [ ] No router file contains `from sqlalchemy.orm import Session`
- [ ] No router file uses `DBSession` (grep confirms zero matches outside `deps.py`)
- [ ] No router file contains a manual `.where(<Model>.user_id == uid)` filter on a tenant-scoped table
- [ ] `CurrentUser` is only used in `api/routers/auth.py`; all other routers use `CurrentUserPayload`
- [ ] Destructive operations (DELETE, bulk import, settings reset) are guarded by `require_role("OWNER", "ADMIN")`
- [ ] `pytest backend/tests/` passes with no failures (unit + integration + parser tests)
