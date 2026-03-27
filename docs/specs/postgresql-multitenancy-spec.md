# PostgreSQL Multi-Tenancy Specification
## Ledger Personal Finance Application — SQLite → PostgreSQL Migration

**Version:** 2.0  
**Date:** March 26, 2026  
**Scope:** Migration from single-user SQLite to a multi-tenant PostgreSQL database supporting 100,000 tenants with Row-Level Security (RLS), optional table partitioning, and M:N user-to-tenant membership with per-tenant roles  

---

## 1. Executive Summary

The Ledger application currently runs against a local SQLite file (`backend/src/ledger.db`). Each user effectively has their own database file. This specification describes the migration to a **shared PostgreSQL database** where all 100,000 tenants coexist in a single schema, isolated by **Row-Level Security (RLS)** enforced at the database engine level.

### Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| **Tenancy model** | Shared schema, RLS isolation | One DB for 100K tenants, lowest operational overhead |
| **Tenant key** | `tenant_id UUID` on every table | UUID avoids enumeration attacks; no sequential ID guessing |
| **User/role model** | DB roles: `app_service`, `tenant_roles` | App uses one service role; RLS checks `current_setting('app.tenant_id')` |
| **Admin bypass** | `superadmin` role bypasses RLS | Trusted ops only; not exposed through the API |
| **Partitioning** | RANGE by `tenant_id` hash on hot tables | Scales I/O for transactions, transaction_lines, audit_log |
| **Connection pooling** | PgBouncer (transaction mode) | 100K tenants cannot hold persistent connections |
| **Monetary types** | `NUMERIC(18,4)` (already used in ORM; ensure DDL matches) | No floating-point rounding errors |
| **Timestamps** | `TIMESTAMPTZ` everywhere | All times stored and compared in UTC |

---

## 2. Multi-Tenancy Architecture

### 2.1 Tenant Model — M:N User ↔ Tenant Relationship

A **tenant** is an isolated financial account/entity (e.g., Ravi's Personal Account, or Ravi's Business Pvt. Ltd.). A **user** is a login identity (email + password). One user can belong to many tenants, and one tenant can have many users — each membership carrying its own role.

```
┌─────────────────────────────────────────────────────────────────┐
│                    PostgreSQL (single DB)                        │
│                                                                  │
│  users (GLOBAL)          tenant_memberships (junction)          │
│  ┌──────────────┐        ┌────────────────────────────────────┐ │
│  │ ravi@...    │───────▶│ ravi + Personal A/c  → OWNER      │ │
│  │ anita@...    │───────▶│ ravi + Business A/c  → ADMIN      │ │
│  │ advisor@...  │───────▶│ anita + Personal A/c  → MEMBER     │ │
│  └──────────────┘        │ advisor + ravi A/c   → VIEWER     │ │
│                          │ advisor + anita A/c   → VIEWER     │ │
│                          └────────────────────────────────────┘ │
│                                    │                             │
│                                    ▼                             │
│  tenants (GLOBAL)        All application tables                  │
│  ┌──────────────┐        ┌────────────────────────────────────┐ │
│  │ Personal A/c │───────▶│ tenant_id on every data row        │ │
│  │ Business A/c │        │ RLS: session sets app.tenant_id    │ │
│  │ Anita A/c    │        │ → only that tenant's rows visible  │ │
│  └──────────────┘        └────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

**Key flows:**
1. **Sign up**: User registers → creates a `users` row (global) → creates a `tenants` row → auto-assigned `OWNER` role in `tenant_memberships`.
2. **Login**: User authenticates by email → server returns a list of their accessible tenants.
3. **Tenant selection**: User picks which tenant to work in → server issues a JWT with `active_tenant_id`.
4. **Every API request**: JWT is decoded → `active_tenant_id` is set as `app.tenant_id` → RLS enforces data isolation automatically.
5. **Adding a member**: Tenant ADMIN/OWNER invites another user by email → creates a `tenant_memberships` row with chosen role.
6. **Switching tenant**: User calls `/auth/switch-tenant` → server validates membership → issues new JWT with new `active_tenant_id`.

### 2.2 Tables Without tenant_id (Global / Reference Tables)

These tables are global — either shared reference data or cross-tenant identity tables:

| Table | Reason |
|---|---|
| `users` | Global identity — a user exists independently of any tenant |
| `tenants` | Management table, admin-only |
| `tenant_memberships` | Junction table — governs access, not data |
| `currencies` | ISO 4217 reference, same for all |
| `exchange_rates` | Market data, shared |
| `securities` | Stock/MF master, shared |
| `security_prices` | Market prices, shared |
| `fo_contracts` | Exchange-defined contracts, shared |
| `tax_sections` | Indian IT Act sections, same for all |

All other tables get a `tenant_id UUID NOT NULL` column.

---

## 3. Database Role Hierarchy

```sql
-- ─────────────────────────────────────────────────────────────
-- Role: superadmin
-- Purpose: Full unrestricted access. For DBA/ops only.
--          NEVER used by application API code.
-- ─────────────────────────────────────────────────────────────
CREATE ROLE superadmin LOGIN PASSWORD '...' SUPERUSER;

-- ─────────────────────────────────────────────────────────────
-- Role: app_service
-- Purpose: The single role used by all FastAPI instances.
--          Has RLS enabled; cannot bypass it.
--          Sets app.tenant_id per request before any DML.
-- ─────────────────────────────────────────────────────────────
CREATE ROLE app_service LOGIN PASSWORD '...' NOSUPERUSER NOCREATEDB NOCREATEROLE;
GRANT CONNECT ON DATABASE ledger TO app_service;
GRANT USAGE ON SCHEMA public TO app_service;

-- Grant per-table privileges (generated for all 37 tables):
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_service;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_service;

-- ─────────────────────────────────────────────────────────────
-- Role: readonly_analyst
-- Purpose: Analytics / BI queries. Read-only, bypasses RLS
--          for cross-tenant aggregates (admin reports only).
-- ─────────────────────────────────────────────────────────────
CREATE ROLE readonly_analyst LOGIN PASSWORD '...' NOSUPERUSER;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_analyst;
ALTER ROLE readonly_analyst SET row_security = off; -- analyst sees all rows
```

> [!CAUTION]
> The `app_service` role is the **only** role used by the FastAPI application. It must NEVER have `BYPASSRLS` privilege. Ensure PgBouncer and all connection strings use `app_service`.

---

## 4. New Global Tables: `tenants`, `users`, `tenant_memberships`

### 4.1 `tenants`

```sql
CREATE TABLE tenants (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                TEXT NOT NULL,
        -- display name: "Ravi Personal", "Ravi Enterprises Pvt Ltd"
    entity_type         TEXT NOT NULL DEFAULT 'PERSONAL',
        -- PERSONAL, SOLE_PROPRIETOR, PARTNERSHIP, PRIVATE_LIMITED,
        -- LLP, TRUST, HUF, OTHER
        -- Needed for correct ITR form selection
    pan_number          TEXT,
        -- Entity PAN (not the user's personal PAN)
    plan                TEXT NOT NULL DEFAULT 'FREE',
        -- FREE, BASIC, PRO, ENTERPRISE
    status              TEXT NOT NULL DEFAULT 'ACTIVE',
        -- ACTIVE, SUSPENDED, DELETED
    created_by_user_id  BIGINT,
        -- which user originally created this tenant
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at          TIMESTAMPTZ
        -- soft-delete; data retained for 90 days
);

-- Only superadmin and app_service (for reads during auth) can access.
-- app_service needs SELECT to validate tenant exists during JWT verification.
GRANT SELECT ON tenants TO app_service;
REVOKE INSERT, UPDATE, DELETE ON tenants FROM app_service;
    -- Mutations go through stored procedures running as SECURITY DEFINER
```

### 4.2 `users` — Global Identity Table

Users are **not tenant-scoped**. A user exists once globally and can access many tenants.

```sql
CREATE TABLE users (
    id                  BIGSERIAL PRIMARY KEY,
    email               TEXT NOT NULL UNIQUE,
        -- globally unique; the login identifier
    hashed_password     TEXT NOT NULL,
    full_name           TEXT,
    phone               TEXT,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    is_email_verified   BOOLEAN NOT NULL DEFAULT FALSE,
    last_login_at       TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);

-- users is a GLOBAL table: no tenant_id, no RLS tenant isolation.
-- RLS is still enabled to prevent app_service from doing arbitrary writes.
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE users FORCE ROW LEVEL SECURITY;

-- Any authenticated session can read all users (needed for member invite lookup)
CREATE POLICY users_select ON users
    AS PERMISSIVE FOR SELECT TO app_service
    USING (TRUE);

-- A user can only update their OWN profile row
CREATE POLICY users_update ON users
    AS PERMISSIVE FOR UPDATE TO app_service
    USING (id = current_setting('app.user_id', TRUE)::BIGINT);

-- Only the provisioning stored procedure (SECURITY DEFINER) can INSERT
CREATE POLICY users_insert_block ON users
    AS RESTRICTIVE FOR INSERT TO app_service
    USING (FALSE);  -- direct INSERT blocked; use provision_user() procedure
```

### 4.3 `tenant_memberships` — M:N Junction Table

This is the **core access control table**. Every user-tenant relationship is recorded here with an explicit role.

```sql
CREATE TABLE tenant_memberships (
    id                  BIGSERIAL PRIMARY KEY,
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id             BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role                TEXT NOT NULL DEFAULT 'MEMBER'
        CHECK (role IN (
            'OWNER',        -- created the tenant; full control; can delete tenant
            'ADMIN',        -- full data access; can manage members; cannot delete tenant
            'MEMBER',       -- full data read/write; cannot manage members
            'VIEWER',       -- read-only access to all tenant data
            'ADVISOR',      -- read-only; can be cross-tenant (Financial Advisor use case)
            'ACCOUNTANT'    -- read/write transactions; cannot manage settings/members
        )),
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
        -- OWNER/ADMIN can deactivate a membership without deleting
    invited_by_user_id  BIGINT REFERENCES users(id),
        -- who added this member
    invited_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    accepted_at         TIMESTAMPTZ,
        -- NULL = invite sent but not yet accepted
    last_accessed_at    TIMESTAMPTZ,
        -- when this user last switched to this tenant
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, user_id)  -- one membership record per user per tenant
);

CREATE INDEX idx_membership_user   ON tenant_memberships(user_id);
CREATE INDEX idx_membership_tenant ON tenant_memberships(tenant_id);
CREATE INDEX idx_membership_active ON tenant_memberships(user_id, is_active);

-- RLS: a user can see memberships for tenants they already belong to
ALTER TABLE tenant_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_memberships FORCE ROW LEVEL SECURITY;

CREATE POLICY membership_select ON tenant_memberships
    AS PERMISSIVE FOR SELECT TO app_service
    USING (
        -- Can see all memberships of the currently active tenant
        tenant_id = current_tenant_id()
        OR
        -- Can see their own memberships across all tenants (for tenant-switcher UI)
        user_id = current_setting('app.user_id', TRUE)::BIGINT
    );

-- Only OWNER/ADMIN of a tenant can insert/update/delete memberships
-- Enforced at application layer; DB enforces via stored procedure
CREATE POLICY membership_write ON tenant_memberships
    AS PERMISSIVE FOR INSERT, UPDATE, DELETE TO app_service
    USING (tenant_id = current_tenant_id());
```

> [!IMPORTANT]
> The `tenant_memberships.role` column is the **application-level** role (what a user can do within Ledger). This is separate from PostgreSQL DB roles (`app_service`, `superadmin`). The API must check `tenant_memberships.role` before allowing write operations like deleting transactions or changing settings.

---

## 5. Schema Changes: Adding `tenant_id` to All Tables

Every tenant-scoped table receives:

```sql
ALTER TABLE <table_name>
    ADD COLUMN tenant_id UUID NOT NULL 
        REFERENCES tenants(id) ON DELETE CASCADE;

CREATE INDEX idx_<table_name>_tenant ON <table_name>(tenant_id);
```

### 5.1 Complete Table Inventory

Tables **requiring `tenant_id`** (all financial/operational data tables):

| # | Table | Notes |
|---|---|---|
| 1 | `accounts` | Chart of Accounts is per-tenant |
| 2 | `financial_institutions` | Bank relationships per-tenant |
| 3 | `bank_accounts` | Per-tenant |
| 4 | `fixed_deposits` | Per-tenant |
| 5 | `credit_cards` | Per-tenant |
| 6 | `loans` | Per-tenant |
| 7 | `brokerage_accounts` | Per-tenant |
| 8 | `transactions` | ⚡ HOT TABLE — partition this |
| 9 | `transaction_lines` | ⚡ HOT TABLE — partition this |
| 10 | `transaction_charges` | Per-tenant |
| 11 | `attachments` | Per-tenant |
| 12 | `payees` | Per-tenant |
| 13 | `tags` | Per-tenant |
| 14 | `transaction_tags` | Per-tenant |
| 15 | `recurring_transactions` | Per-tenant |
| 16 | `recurring_transaction_lines` | Per-tenant |
| 17 | `goals` | Per-tenant |
| 18 | `goal_account_mappings` | Per-tenant |
| 19 | `goal_milestones` | Per-tenant |
| 20 | `goal_contributions` | Per-tenant |
| 21 | `budgets` | Per-tenant |
| 22 | `budget_items` | Per-tenant |
| 23 | `monthly_snapshots` | ⚡ HOT TABLE — consider partitioning |
| 24 | `net_worth_history` | Per-tenant |
| 25 | `saved_reports` | Per-tenant |
| 26 | `import_profiles` | Per-tenant |
| 27 | `import_batches` | Per-tenant |
| 28 | `reconciliation_records` | Per-tenant |
| 29 | `tax_lot_disposals` | Per-tenant |
| 30 | `tax_lots` | Per-tenant |
| 31 | `fo_positions` | Per-tenant |
| 32 | `holdings_summary` | Per-tenant |
| 33 | `tax_section_mappings` | Per-tenant |
| 34 | `app_settings` | Per-tenant |
| 35 | `audit_log` | ⚡ HOT TABLE — partition this |
| 36 | `notifications` | Per-tenant |
| 37 | `backup_history` | Per-tenant |

**Global tables (NO `tenant_id`) — unchanged from current schema or new cross-tenant tables:**

`users`, `tenants`, `tenant_memberships`, `currencies`, `exchange_rates`, `securities`, `security_prices`, `fo_contracts`, `tax_sections`

> [!NOTE]
> `users` and `user_profiles` are **removed from the tenant-scoped list**. A user exists once globally. The `user_profiles` table (household sub-profiles like Spouse/Dependent) should also be global, linked to `users.id`, not tenant-scoped — a user's family structure does not change per tenant.

---

## 6. Row-Level Security (RLS) Design

### 6.1 The Security Context Pattern

The API sets the tenant context at the start of every request. The DB enforces it automatically on every query, without any application-layer WHERE clauses.

```python
# In FastAPI middleware / dependency (engine.py)
async def set_tenant_context(session: AsyncSession, tenant_id: str):
    await session.execute(
        text("SELECT set_config('app.tenant_id', :tid, TRUE)"),
        {"tid": tenant_id}
    )
    # TRUE = local to transaction only (resets on COMMIT/ROLLBACK)
```

```sql
-- Helper function used by all RLS policies
CREATE OR REPLACE FUNCTION current_tenant_id() RETURNS UUID
    LANGUAGE sql STABLE SECURITY DEFINER
AS $$
    SELECT NULLIF(current_setting('app.tenant_id', TRUE), '')::UUID;
$$;
```

> [!IMPORTANT]
> `SECURITY DEFINER` on `current_tenant_id()` ensures the function always runs with the definer's search_path, preventing a malicious user from overriding it. The `TRUE` parameter in `current_setting` returns NULL instead of raising an error if the setting is not set, which prevents crashes during schema migrations.

### 6.2 Enabling RLS on Every Tenant-Scoped Table

```sql
-- Template — apply to all 39 tenant-scoped tables:
ALTER TABLE <table_name> ENABLE ROW LEVEL SECURITY;
ALTER TABLE <table_name> FORCE ROW LEVEL SECURITY;
    -- FORCE applies even to the table owner

-- Policy: tenant can only see their own rows
CREATE POLICY tenant_isolation ON <table_name>
    AS PERMISSIVE
    FOR ALL
    TO app_service
    USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());
```

> [!NOTE]
> `FORCE ROW LEVEL SECURITY` is critical. Without it, the table owner (who might be `app_service`) would bypass RLS. Always use both `ENABLE` and `FORCE`.

### 6.3 Read-Only Global Tables: Protect from Write

Global reference tables are readable by all but can only be written by `superadmin`:

```sql
-- Global tables: all can read, only superadmin writes
ALTER TABLE securities ENABLE ROW LEVEL SECURITY;
ALTER TABLE securities FORCE ROW LEVEL SECURITY;

-- Allow all authenticated roles to read
CREATE POLICY global_read ON securities
    AS PERMISSIVE FOR SELECT
    TO app_service, readonly_analyst
    USING (TRUE);

-- Block writes from app_service
CREATE POLICY global_write_block ON securities
    AS RESTRICTIVE FOR INSERT, UPDATE, DELETE
    TO app_service
    USING (FALSE);
    -- Only superadmin (who bypasses RLS) can mutate
```

### 6.4 Audit Log: Insert-Only Policy

```sql
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log FORCE ROW LEVEL SECURITY;

-- Tenants can insert and read their own audit records only
CREATE POLICY audit_insert ON audit_log
    AS PERMISSIVE FOR INSERT
    TO app_service
    WITH CHECK (tenant_id = current_tenant_id());

CREATE POLICY audit_select ON audit_log
    AS PERMISSIVE FOR SELECT
    TO app_service
    USING (tenant_id = current_tenant_id());

-- Nobody (not even app_service) can UPDATE or DELETE audit_log
CREATE POLICY audit_no_update ON audit_log
    AS RESTRICTIVE FOR UPDATE
    TO app_service
    USING (FALSE);

CREATE POLICY audit_no_delete ON audit_log
    AS RESTRICTIVE FOR DELETE
    TO app_service
    USING (FALSE);
```

### 6.5 Administrator Cross-Tenant Access

Administrators use the `superadmin` role, which is a `SUPERUSER` and inherently bypasses all RLS. For admin API endpoints (e.g., support tools, billing), the FastAPI app connects with a **separate admin connection pool** using `superadmin` credentials — never the same pool as tenant requests.

```python
# Separate admin session factory — ONLY for admin API routes
admin_engine = create_async_engine(settings.admin_database_url, ...)
AdminSessionFactory = async_sessionmaker(admin_engine, ...)

# Protect admin routes with a separate role-check dependency
async def require_admin(token: str = Depends(oauth2_scheme)):
    user = verify_jwt(token)
    if user.role != "ADMIN":
        raise HTTPException(403)
    return user
```

---

## 7. PostgreSQL Partitioning Strategy

With 100K tenants and potentially millions of rows in hot tables, partitioning prevents table bloat and enables efficient per-tenant data management.

### 7.1 Partition Strategy by Table

#### Option A — RANGE Partitioning by `tenant_id` (Hash Bucket)

Hash the `tenant_id` UUID into N buckets and create RANGE partitions. This distributes tenants evenly across shards.

```sql
-- transactions: partition by hash of tenant_id (256 partitions)
CREATE TABLE transactions (
    id              BIGSERIAL,
    tenant_id       UUID NOT NULL,
    transaction_date DATE NOT NULL,
    -- ... all other columns ...
    PRIMARY KEY (id, tenant_id)   -- tenant_id must be in PK for partitioning
) PARTITION BY HASH (tenant_id);

-- Create 8 initial partitions (scale up as needed)
CREATE TABLE transactions_p0 PARTITION OF transactions
    FOR VALUES WITH (MODULUS 8, REMAINDER 0);
CREATE TABLE transactions_p1 PARTITION OF transactions
    FOR VALUES WITH (MODULUS 8, REMAINDER 1);
-- ... p2 through p7
```

> [!TIP]
> Start with 8 HASH partitions. PostgreSQL allows splitting partitions later but it requires a brief table lock. Plan for 64 partitions at 1M+ tenants. For 100K tenants, 8–16 partitions are sufficient.

#### Hot Tables to Partition

| Table | Partition Type | Key | Initial Partitions |
|---|---|---|---|
| `transactions` | HASH | `tenant_id` | 8 |
| `transaction_lines` | HASH | `tenant_id` | 8 |
| `audit_log` | HASH | `tenant_id` | 16 (higher volume) |
| `monthly_snapshots` | HASH | `tenant_id` | 4 |
| `reconciliation_records` | HASH | `tenant_id` | 4 |
| `security_prices` | RANGE | `price_date` (monthly) | 1 per month (time-series) |

#### Option B — Sub-partitioning `audit_log` (HASH × RANGE)

For `audit_log`, combine HASH by `tenant_id` and RANGE by `timestamp` month for efficient purging:

```sql
CREATE TABLE audit_log (
    id          BIGSERIAL,
    tenant_id   UUID NOT NULL,
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- ... other columns ...
    PRIMARY KEY (id, tenant_id, timestamp)
) PARTITION BY HASH (tenant_id);

-- Each hash partition is further sub-partitioned by month
CREATE TABLE audit_log_p0 PARTITION OF audit_log
    FOR VALUES WITH (MODULUS 16, REMAINDER 0)
    PARTITION BY RANGE (timestamp);

CREATE TABLE audit_log_p0_2026_01 PARTITION OF audit_log_p0
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
-- Created monthly via cron/scheduled job
```

### 7.2 Partition-Aware Indexes

Every partition automatically inherits indexes from the parent table. Define indexes on the parent:

```sql
CREATE INDEX idx_transactions_tenant_date 
    ON transactions (tenant_id, transaction_date DESC);

CREATE INDEX idx_transactions_type 
    ON transactions (tenant_id, transaction_type);

CREATE INDEX idx_txn_lines_tenant_account 
    ON transaction_lines (tenant_id, account_id);

CREATE INDEX idx_audit_tenant_ts 
    ON audit_log (tenant_id, timestamp DESC);
```

> [!NOTE]
> Indexes on partitioned tables are automatically created on all partitions. This means choosing 8 partitions creates 8 × (number of indexes) index objects. Balance partition count against index maintenance overhead.

### 7.3 Partition Maintenance

```sql
-- Cron job: create next month's audit_log sub-partitions
-- Run on the 25th of each month
CREATE OR REPLACE PROCEDURE create_audit_log_partition(year INT, month INT)
LANGUAGE plpgsql AS $$
DECLARE
    start_date DATE := make_date(year, month, 1);
    end_date   DATE := start_date + INTERVAL '1 month';
    part_name  TEXT;
BEGIN
    FOR i IN 0..15 LOOP
        part_name := format('audit_log_p%s_%s_%s', i, year, lpad(month::TEXT, 2, '0'));
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I PARTITION OF audit_log_p%s FOR VALUES FROM (%L) TO (%L)',
            part_name, i, start_date, end_date
        );
    END LOOP;
END;
$$;
```

---

## 8. Data Type Upgrades (SQLite → PostgreSQL)

| SQLite Type | PostgreSQL Type | Notes |
|---|---|---|
| `INTEGER PRIMARY KEY AUTOINCREMENT` | `BIGSERIAL PRIMARY KEY` | 64-bit to support 100K tenants × millions of rows |
| `REAL` | `NUMERIC(18,4)` | No rounding errors for monetary values |
| `TEXT` (for booleans like `is_active`) | `BOOLEAN` | Native boolean; not `0`/`1` integer |
| `TEXT` (for dates) | `DATE` | Native date comparisons and range queries |
| `TEXT` (for timestamps/datetimes) | `TIMESTAMPTZ` | Timezone-aware; stored in UTC |
| `TEXT` (for JSON blobs) | `JSONB` | Binary JSON with GIN indexing support |
| `TEXT` (for UUIDs) | `UUID` | Native UUID type |
| `TEXT` (status enums) | `TEXT` + `CHECK` constraint or custom `ENUM` | Use CHECK for flexibility; ENUM for strict enforcement |

### 8.1 Type Migration Map Per Table (Key Columns)

```sql
-- accounts
id                  BIGSERIAL PRIMARY KEY
parent_id           BIGINT REFERENCES accounts(id)
is_active           BOOLEAN NOT NULL DEFAULT TRUE
is_system           BOOLEAN NOT NULL DEFAULT FALSE
is_placeholder      BOOLEAN NOT NULL DEFAULT FALSE
created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()

-- transactions
id                  BIGSERIAL
tenant_id           UUID NOT NULL
transaction_date    DATE NOT NULL
effective_date      DATE
status              TEXT NOT NULL DEFAULT 'CONFIRMED'
    CHECK (status IN ('PENDING','CONFIRMED','VOID','RECONCILED'))
voided_at           TIMESTAMPTZ
created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()

-- transaction_lines
amount              NUMERIC(18,4) NOT NULL
quantity            NUMERIC(18,8)  -- higher precision for unit quantities
price_per_unit      NUMERIC(18,4)
exchange_rate       NUMERIC(18,8)

-- goals
current_amount      NUMERIC(18,4) NOT NULL DEFAULT 0
target_amount       NUMERIC(18,4) NOT NULL
sip_amount          NUMERIC(18,4)
expected_return_rate NUMERIC(8,4)

-- app_settings (parameters JSON)
parameters_json     JSONB          -- was TEXT; enables GIN index on JSON paths

-- import_profiles
column_mapping_json JSONB

-- reconciliation_records
confidence_score    NUMERIC(4,3)   -- 0.000 to 1.000
```

---

## 9. Complete DDL for New / Modified Key Tables

### 9.1 `users` (Global — already defined in Section 4.2)

See Section 4.2 for the full `users` DDL. Key points:
- **No `tenant_id` column** — users are global identities.
- `email` is **globally unique** (`UNIQUE(email)`) — one email, one login.
- RLS allows any authenticated session to `SELECT` users (for member invite lookup), but `UPDATE` is restricted to the user's own row via `app.user_id`.
- Direct `INSERT` is blocked; use the `provision_user()` stored procedure.

#### Helper Function: Set Both Context Variables per Request

```sql
-- Two context variables are now required per request:
-- app.tenant_id  → scopes all tenant data (used by RLS on data tables)
-- app.user_id    → identifies the acting user (used by users/membership RLS)
CREATE OR REPLACE FUNCTION current_user_id() RETURNS BIGINT
    LANGUAGE sql STABLE SECURITY DEFINER
AS $$
    SELECT NULLIF(current_setting('app.user_id', TRUE), '')::BIGINT;
$$;
```

### 9.2 `accounts` (Updated)

```sql
CREATE TABLE accounts (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    parent_id       BIGINT REFERENCES accounts(id),
    code            TEXT NOT NULL,
    name            TEXT NOT NULL,
    account_type    TEXT NOT NULL
        CHECK (account_type IN ('ASSET','LIABILITY','INCOME','EXPENSE','EQUITY')),
    account_subtype TEXT,
    currency_code   TEXT NOT NULL DEFAULT 'INR' REFERENCES currencies(code),
    description     TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    is_system       BOOLEAN NOT NULL DEFAULT FALSE,
    is_placeholder  BOOLEAN NOT NULL DEFAULT FALSE,
    normal_balance  TEXT NOT NULL CHECK (normal_balance IN ('DEBIT','CREDIT')),
    display_order   INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, code)    -- account code unique per tenant
);

CREATE INDEX idx_accounts_tenant        ON accounts(tenant_id);
CREATE INDEX idx_accounts_tenant_parent ON accounts(tenant_id, parent_id);
CREATE INDEX idx_accounts_tenant_type   ON accounts(tenant_id, account_type);

ALTER TABLE accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE accounts FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON accounts
    FOR ALL TO app_service
    USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());
```

### 9.3 `transactions` (Partitioned)

```sql
CREATE TABLE transactions (
    id                          BIGSERIAL,
    tenant_id                   UUID NOT NULL,
    transaction_date            DATE NOT NULL,
    effective_date              DATE,
    transaction_number          TEXT,
    transaction_type            TEXT NOT NULL,
    description                 TEXT NOT NULL,
    payee_id                    BIGINT,
    reference_number            TEXT,
    status                      TEXT NOT NULL DEFAULT 'CONFIRMED'
        CHECK (status IN ('PENDING','CONFIRMED','VOID','RECONCILED')),
    is_void                     BOOLEAN NOT NULL DEFAULT FALSE,
    void_reason                 TEXT,
    voided_at                   TIMESTAMPTZ,
    reversal_of_transaction_id  BIGINT,
    import_batch_id             BIGINT,
    recurring_transaction_id    BIGINT,
    notes                       TEXT,
    txn_hash                    TEXT,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, tenant_id)
) PARTITION BY HASH (tenant_id);

-- Create 8 hash partitions
DO $$
BEGIN
    FOR i IN 0..7 LOOP
        EXECUTE format(
            'CREATE TABLE transactions_p%s PARTITION OF transactions
             FOR VALUES WITH (MODULUS 8, REMAINDER %s)',
            i, i
        );
    END LOOP;
END;
$$;

-- Indexes on parent (propagate to all partitions)
CREATE INDEX idx_txn_tenant_date    ON transactions (tenant_id, transaction_date DESC);
CREATE INDEX idx_txn_tenant_type    ON transactions (tenant_id, transaction_type);
CREATE INDEX idx_txn_tenant_status  ON transactions (tenant_id, status);
CREATE INDEX idx_txn_hash           ON transactions (tenant_id, txn_hash) WHERE txn_hash IS NOT NULL;
CREATE UNIQUE INDEX idx_txn_number  ON transactions (tenant_id, transaction_number)
    WHERE transaction_number IS NOT NULL;

ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON transactions
    FOR ALL TO app_service
    USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());
```

### 9.4 `app_settings` (Per-Tenant Key-Value Store)

```sql
CREATE TABLE app_settings (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    setting_key     TEXT NOT NULL,
    setting_value   TEXT,
    setting_type    TEXT NOT NULL DEFAULT 'STRING'
        CHECK (setting_type IN ('STRING','INTEGER','REAL','BOOLEAN','DATE','JSON')),
    category        TEXT NOT NULL DEFAULT 'GENERAL',
    description     TEXT,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, setting_key)
);

ALTER TABLE app_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE app_settings FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON app_settings
    FOR ALL TO app_service
    USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());
```

---

## 10. SQLAlchemy ORM Changes

### 10.1 Base Model Update

```python
# backend/src/db/models/base.py
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import BigInteger, UUID as PgUUID
import uuid

class Base(DeclarativeBase):
    """All ORM models inherit from this base."""
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # tenant_id is declared in each model explicitly for partitioned tables


class TenantScopedMixin:
    """Add this mixin to every tenant-scoped model."""
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        nullable=False,
        index=True,
    )
```

### 10.2 Example: Updated Transaction Model

```python
# backend/src/db/models/transactions.py
import uuid
from sqlalchemy import String, Boolean, Numeric, Date, DateTime, BigInteger, UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.models.base import Base, TenantScopedMixin

class Transaction(TenantScopedMixin, Base):
    __tablename__ = "transactions"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), nullable=False
    )
    # primary key must include tenant_id for partitioned table
    # Use __table_args__ to declare composite PK:
    __table_args__ = (
        {"postgresql_partition_by": "HASH (tenant_id)"},
    )
    # ... rest of columns unchanged except types:
    # TEXT date fields → Date/DateTime
    # REAL amounts → Numeric(18,4)
    # INTEGER booleans → Boolean
```

### 10.3 Engine Update with Tenant Context Middleware

```python
# backend/src/db/engine.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text, event
from config import get_settings

settings = get_settings()

# Primary engine for tenant requests
engine = create_async_engine(
    settings.database_url,          # postgresql+asyncpg://app_service:...@host/ledger
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=3600,              # recycle connections every hour
    connect_args={
        "server_settings": {
            "application_name": "ledger_api",
            "jit": "off",           # disable JIT for OLTP workloads
        }
    },
)

# Admin engine (superadmin) — separate pool for admin API routes only
admin_engine = create_async_engine(
    settings.admin_database_url,    # postgresql+asyncpg://superadmin:...@host/ledger
    pool_size=3,
    max_overflow=5,
    pool_pre_ping=True,
)

SessionFactory = async_sessionmaker(
    engine, 
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

AdminSessionFactory = async_sessionmaker(
    admin_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session(tenant_id: str) -> AsyncSession:
    """FastAPI dependency: open session and set tenant context on every request."""
    async with SessionFactory() as session:
        # Set tenant context for RLS; TRUE = transaction-local
        await session.execute(
            text("SELECT set_config('app.tenant_id', :tid, TRUE)"),
            {"tid": str(tenant_id)},
        )
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_admin_session() -> AsyncSession:
    """FastAPI dependency for admin routes — bypasses RLS via superadmin role."""
    async with AdminSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

### 10.4 Authentication & Tenant-Switching Flow

#### Step 1 — Login (email + password)

```python
# POST /auth/login  →  returns user info + list of accessible tenants
@router.post("/auth/login")
async def login(credentials: LoginRequest, session = Depends(get_admin_session)):
    user = await authenticate_user(session, credentials.email, credentials.password)

    # Fetch all tenants this user can access (M:N lookup)
    memberships = await session.execute(
        select(TenantMembership)
        .where(TenantMembership.user_id == user.id)
        .where(TenantMembership.is_active == True)
    )
    tenants_list = [
        {"tenant_id": str(m.tenant_id), "name": m.tenant.name, "role": m.role}
        for m in memberships.scalars()
    ]
    # Return tenant list — frontend shows a picker if > 1 tenant
    return {"user_id": user.id, "email": user.email, "tenants": tenants_list}
```

#### Step 2 — Tenant Selection (issue scoped JWT)

```python
# POST /auth/select-tenant  →  issues a JWT with active_tenant_id
@router.post("/auth/select-tenant")
async def select_tenant(
    body: SelectTenantRequest,   # {tenant_id: uuid}
    user: User = Depends(get_current_user),
    session = Depends(get_admin_session),
):
    # Verify membership exists and is active
    membership = await session.execute(
        select(TenantMembership)
        .where(TenantMembership.user_id == user.id)
        .where(TenantMembership.tenant_id == body.tenant_id)
        .where(TenantMembership.is_active == True)
    )
    m = membership.scalar_one_or_none()
    if not m:
        raise HTTPException(403, "No access to this tenant")

    # JWT carries BOTH user identity AND active tenant context
    token = create_jwt({
        "sub": str(user.id),          # user_id
        "email": user.email,
        "tenant_id": str(m.tenant_id), # active tenant
        "role": m.role,                # OWNER/ADMIN/MEMBER/VIEWER/ADVISOR
        "exp": ...
    })
    return {"access_token": token, "token_type": "bearer"}
```

#### Step 3 — Per-Request Context (RLS activation)

```python
# FastAPI dependency: sets BOTH app.tenant_id AND app.user_id
async def get_session_with_context(
    token: str = Depends(oauth2_scheme),
) -> AsyncSession:
    payload = verify_jwt(token)
    tenant_id = payload["tenant_id"]
    user_id   = payload["sub"]

    async with SessionFactory() as session:
        # Set both context variables — transaction-local (safe with PgBouncer)
        await session.execute(
            text("SELECT set_config('app.tenant_id', :tid, TRUE),"
                 "       set_config('app.user_id',   :uid, TRUE)"),
            {"tid": str(tenant_id), "uid": str(user_id)},
        )
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

# Endpoint example:
@router.get("/transactions")
async def list_transactions(
    session: AsyncSession = Depends(get_session_with_context),
):
    # RLS auto-filters by app.tenant_id — no WHERE clause needed
    result = await session.execute(select(Transaction))
    return result.scalars().all()

# Role-guard decorator for write operations:
def require_role(*allowed_roles: str):
    def dependency(token: str = Depends(oauth2_scheme)):
        payload = verify_jwt(token)
        if payload["role"] not in allowed_roles:
            raise HTTPException(403, f"Requires one of: {allowed_roles}")
        return payload
    return Depends(dependency)

# Only OWNER or ADMIN can invite members:
@router.post("/tenants/{tenant_id}/members")
async def invite_member(
    body: InviteMemberRequest,
    _auth = require_role("OWNER", "ADMIN"),
    session: AsyncSession = Depends(get_session_with_context),
):
    ...
```

---

## 11. Connection Pooling with PgBouncer

100K tenants cannot hold persistent connections. Use **PgBouncer in transaction mode**.

```ini
# pgbouncer.ini
[databases]
ledger = host=postgres port=5432 dbname=ledger user=app_service

[pgbouncer]
listen_port = 6432
listen_addr = *
auth_type = scram-sha-256
auth_file = /etc/pgbouncer/userlist.txt

pool_mode = transaction       ; Transaction-mode pooling
max_client_conn = 10000       ; Max simultaneous client connections
default_pool_size = 50        ; Server connections to PostgreSQL
min_pool_size = 10
reserve_pool_size = 10
reserve_pool_timeout = 5

; Timeouts
server_idle_timeout = 600
client_idle_timeout = 0       ; Clients can hold connections (PgBouncer handles)
query_timeout = 30000         ; 30s max per query
server_connect_timeout = 15

; Logging
log_connections = 0           ; Suppress in production
log_disconnections = 0
log_pooler_errors = 1
```

> [!WARNING]
> In transaction-mode PgBouncer, `SET` commands do **not** persist across transactions. This is why we use `set_config('app.tenant_id', tid, TRUE)` with `is_local=TRUE` — it is scoped to the current transaction, which aligns perfectly with PgBouncer transaction mode. Do NOT use `SET LOCAL` or session-level `SET` in transaction pooling mode.

---

## 12. Index Strategy for 100K Tenants

### 12.1 Universal Composite Index Pattern

All indexes on tenant-scoped tables must **lead with `tenant_id`**:

```sql
-- ✅ CORRECT: tenant_id first, then query column
CREATE INDEX idx_transactions_date ON transactions (tenant_id, transaction_date DESC);

-- ❌ WRONG: query column first (useless for tenant queries under RLS)
CREATE INDEX idx_transactions_date ON transactions (transaction_date DESC);
```

### 12.2 Critical Index Set

```sql
-- Transactions (most queried)
CREATE INDEX idx_txn_tenant_date       ON transactions (tenant_id, transaction_date DESC);
CREATE INDEX idx_txn_tenant_type_date  ON transactions (tenant_id, transaction_type, transaction_date DESC);
CREATE INDEX idx_txn_tenant_payee      ON transactions (tenant_id, payee_id);
CREATE INDEX idx_txn_tenant_import     ON transactions (tenant_id, import_batch_id);

-- Transaction lines (balance queries)
CREATE INDEX idx_tl_tenant_account     ON transaction_lines (tenant_id, account_id);
CREATE INDEX idx_tl_tenant_txn         ON transaction_lines (tenant_id, transaction_id);
CREATE INDEX idx_tl_account_date       ON transaction_lines (tenant_id, account_id)
    INCLUDE (line_type, amount);     -- covering index for balance queries

-- Monthly snapshots (reporting)
CREATE INDEX idx_ms_tenant_account_period ON monthly_snapshots 
    (tenant_id, account_id, snapshot_year DESC, snapshot_month DESC);

-- Accounts
CREATE INDEX idx_acc_tenant_type       ON accounts (tenant_id, account_type);
CREATE INDEX idx_acc_tenant_parent     ON accounts (tenant_id, parent_id);

-- Audit log
CREATE INDEX idx_audit_tenant_ts       ON audit_log (tenant_id, timestamp DESC);
CREATE INDEX idx_audit_tenant_entity   ON audit_log (tenant_id, entity_type, entity_id);

-- Securities and prices (global, no tenant_id)
CREATE INDEX idx_prices_security_date  ON security_prices (security_id, price_date DESC);
CREATE INDEX idx_sec_isin              ON securities (isin);
CREATE INDEX idx_sec_type              ON securities (security_type);

-- Holdings
CREATE UNIQUE INDEX idx_holdings_tenant_sec_brok ON holdings_summary 
    (tenant_id, security_id, brokerage_account_id);
```

### 12.3 JSONB Indexes for Flexible Queries

```sql
-- GIN index for app_settings JSON value queries
CREATE INDEX idx_settings_value_gin ON app_settings USING gin(setting_value jsonb_path_ops)
    WHERE setting_type = 'JSON';

-- GIN index for column_mapping_json in import_profiles
CREATE INDEX idx_import_profiles_mapping ON import_profiles USING gin(column_mapping_json);
```

---

## 13. Tenant Data Lifecycle Management

### 13.1 Provisioning Flows

#### New User Signup (creates user + first tenant + OWNER membership)

```sql
CREATE OR REPLACE PROCEDURE provision_new_user(
    p_email           TEXT,
    p_hashed_password TEXT,
    p_full_name       TEXT,
    p_tenant_name     TEXT,
    p_entity_type     TEXT DEFAULT 'PERSONAL',
    OUT p_user_id     BIGINT,
    OUT p_tenant_id   UUID
)
LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    -- 1. Create the global user record
    INSERT INTO users (email, hashed_password, full_name)
    VALUES (p_email, p_hashed_password, p_full_name)
    RETURNING id INTO p_user_id;

    -- 2. Create the first tenant (their personal / primary account)
    INSERT INTO tenants (name, entity_type, created_by_user_id)
    VALUES (p_tenant_name, p_entity_type, p_user_id)
    RETURNING id INTO p_tenant_id;

    -- 3. Grant OWNER membership (full control)
    INSERT INTO tenant_memberships (tenant_id, user_id, role, accepted_at)
    VALUES (p_tenant_id, p_user_id, 'OWNER', NOW());

    -- 4. Seed default app_settings for the new tenant
    INSERT INTO app_settings (tenant_id, setting_key, setting_value, category) VALUES
        (p_tenant_id, 'financial_year_start_month', '4', 'GENERAL'),
        (p_tenant_id, 'base_currency', 'INR', 'GENERAL'),
        (p_tenant_id, 'tax_regime', 'OLD', 'TAX'),
        (p_tenant_id, 'cost_basis_method', 'FIFO', 'GENERAL'),
        (p_tenant_id, 'onboarding_completed', '0', 'GENERAL');

    -- 5. Seed default Chart of Accounts
    PERFORM seed_default_accounts(p_tenant_id);
END;
$$;
```

#### Existing User Adds a New Tenant

```sql
CREATE OR REPLACE PROCEDURE provision_additional_tenant(
    p_user_id       BIGINT,
    p_tenant_name   TEXT,
    p_entity_type   TEXT DEFAULT 'PERSONAL',
    OUT p_tenant_id UUID
)
LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    -- 1. Create the new tenant
    INSERT INTO tenants (name, entity_type, created_by_user_id)
    VALUES (p_tenant_name, p_entity_type, p_user_id)
    RETURNING id INTO p_tenant_id;

    -- 2. Grant OWNER membership to the requesting user
    INSERT INTO tenant_memberships (tenant_id, user_id, role, accepted_at)
    VALUES (p_tenant_id, p_user_id, 'OWNER', NOW());

    -- 3. Seed settings and accounts
    INSERT INTO app_settings (tenant_id, setting_key, setting_value, category) VALUES
        (p_tenant_id, 'financial_year_start_month', '4', 'GENERAL'),
        (p_tenant_id, 'base_currency', 'INR', 'GENERAL'),
        (p_tenant_id, 'tax_regime', 'OLD', 'TAX'),
        (p_tenant_id, 'cost_basis_method', 'FIFO', 'GENERAL'),
        (p_tenant_id, 'onboarding_completed', '0', 'GENERAL');

    PERFORM seed_default_accounts(p_tenant_id);
END;
$$;
```

#### Admin/Owner Invites a Member to an Existing Tenant

```sql
CREATE OR REPLACE PROCEDURE invite_member_to_tenant(
    p_tenant_id         UUID,
    p_invitee_email     TEXT,
    p_role              TEXT,
    p_invited_by_user_id BIGINT
)
LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE
    v_invitee_user_id BIGINT;
BEGIN
    -- Look up the invitee (they must already have a Ledger account)
    SELECT id INTO v_invitee_user_id FROM users WHERE email = p_invitee_email;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'User % not found. They must register first.', p_invitee_email;
    END IF;

    -- Create membership (accepted_at NULL = pending invite)
    INSERT INTO tenant_memberships (tenant_id, user_id, role, invited_by_user_id)
    VALUES (p_tenant_id, v_invitee_user_id, p_role, p_invited_by_user_id)
    ON CONFLICT (tenant_id, user_id)
    DO UPDATE SET role = EXCLUDED.role, is_active = TRUE, updated_at = NOW();
END;
$$;
```

### 13.2 Tenant Deletion (GDPR / Account Closure)

```sql
-- Soft-delete: set deleted_at, suspend access
UPDATE tenants SET status = 'DELETED', deleted_at = NOW() WHERE id = p_tenant_id;

-- Hard purge (scheduled 90 days after soft-delete):
-- CASCADE DELETE on tenants.id handles all tenant_id FK cascades automatically
DELETE FROM tenants WHERE id = p_tenant_id AND deleted_at < NOW() - INTERVAL '90 days';
```

### 13.3 Per-Tenant Data Export (Portability)

```sql
-- Admin-only export function
CREATE OR REPLACE FUNCTION export_tenant_data(p_tenant_id UUID)
RETURNS JSONB LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE result JSONB;
BEGIN
    SELECT jsonb_build_object(
        'tenant_id', p_tenant_id,
        'exported_at', NOW(),
        'accounts',     (SELECT jsonb_agg(row_to_json(a)) FROM accounts a WHERE tenant_id = p_tenant_id),
        'transactions', (SELECT jsonb_agg(row_to_json(t)) FROM transactions t WHERE tenant_id = p_tenant_id),
        'goals',        (SELECT jsonb_agg(row_to_json(g)) FROM goals g WHERE tenant_id = p_tenant_id)
        -- include all other tables...
    ) INTO result;
    RETURN result;
END;
$$;
```

---

## 14. Security Hardening Checklist

### 14.1 PostgreSQL Server Configuration

```sql
-- Revoke default public schema access
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON DATABASE ledger FROM PUBLIC;

-- Enable SSL (enforce in postgresql.conf)
-- ssl = on
-- ssl_cert_file = 'server.crt'
-- ssl_key_file = 'server.key'

-- Enable audit logging extension
CREATE EXTENSION IF NOT EXISTS pgaudit;

-- Require scram-sha-256 authentication (pg_hba.conf)
-- host all all 0.0.0.0/0 scram-sha-256

-- Enable pg_stat_statements for query monitoring
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Set statement timeout to prevent runaway queries
ALTER ROLE app_service SET statement_timeout = '30s';
ALTER ROLE app_service SET lock_timeout = '5s';
ALTER ROLE app_service SET idle_in_transaction_session_timeout = '60s';
```

### 14.2 RLS Verification Test Query

```sql
-- Verify RLS is working: as app_service with tenant A's context
-- Should return only tenant A's data
SET ROLE app_service;
SELECT set_config('app.tenant_id', 'aaaaaaaa-0000-0000-0000-000000000001', TRUE);
SELECT COUNT(*) FROM transactions;   -- should only see tenant A's rows

-- Switch to tenant B context
SELECT set_config('app.tenant_id', 'bbbbbbbb-0000-0000-0000-000000000002', TRUE);
SELECT COUNT(*) FROM transactions;   -- should only see tenant B's rows

-- Verify: tenant A cannot see tenant B's data
SELECT set_config('app.tenant_id', 'aaaaaaaa-0000-0000-0000-000000000001', TRUE);
SELECT * FROM transactions WHERE tenant_id = 'bbbbbbbb-0000-0000-0000-000000000002'::UUID;
-- Must return 0 rows
RESET ROLE;
```

---

## 15. Alembic Migration Plan

### 15.1 Migration Phases

**Phase 1 — Global Infrastructure (no data loss)**
```
migrations/
  0001_add_tenants_table.py
  0002_add_pg_extensions.py          -- uuid-ossp, pgcrypto, pg_stat_statements
  0003_add_rls_helper_function.py    -- current_tenant_id()
  0004_update_global_tables_types.py -- exchange_rates, security_prices: TEXT→TIMESTAMPTZ
```

**Phase 2 — Add tenant_id to all tables**
```
  0005_add_tenant_id_users.py
  0006_add_tenant_id_accounts.py
  0007_add_tenant_id_transactions.py
  -- ... one migration per table group
  0020_add_tenant_id_audit_log.py
```

**Phase 3 — Enable RLS**
```
  0021_enable_rls_all_tables.py          -- enable + force + create policies
  0022_rls_global_tables.py              -- read policy for currencies, securities etc.
  0023_rls_audit_log_insert_only.py      -- insert+select only, no update/delete
```

**Phase 4 — Partitioning (zero-downtime with pg_partman)**
```
  0024_partition_transactions.py         -- create partitioned table, swap, backfill
  0025_partition_transaction_lines.py
  0026_partition_audit_log.py
```

**Phase 5 — Type migration**
```
  0027_convert_real_to_numeric.py        -- REAL → NUMERIC(18,4) on monetary columns
  0028_convert_text_to_timestamptz.py    -- TEXT dates → DATE/TIMESTAMPTZ
  0029_convert_text_to_boolean.py        -- INTEGER 0/1 → BOOLEAN
  0030_convert_json_to_jsonb.py          -- TEXT JSON columns → JSONB
```

**Phase 6 — Index optimization**
```
  0031_add_tenant_composite_indexes.py
  0032_add_covering_indexes.py
  0033_add_gin_indexes_jsonb.py
```

### 15.2 Zero-Downtime Partitioned Table Migration Pattern

```python
# 0024_partition_transactions.py
def upgrade():
    # 1. Create new partitioned table
    op.execute("""
        CREATE TABLE transactions_partitioned (LIKE transactions INCLUDING ALL)
        PARTITION BY HASH (tenant_id);
    """)
    # 2. Create partitions
    for i in range(8):
        op.execute(f"""
            CREATE TABLE transactions_p{i} PARTITION OF transactions_partitioned
            FOR VALUES WITH (MODULUS 8, REMAINDER {i});
        """)
    # 3. Copy data in batches (low-lock)
    op.execute("""
        INSERT INTO transactions_partitioned SELECT * FROM transactions;
    """)
    # 4. Rename tables (fast lock)
    op.execute("ALTER TABLE transactions RENAME TO transactions_old;")
    op.execute("ALTER TABLE transactions_partitioned RENAME TO transactions;")
    # 5. Drop old table after validation
    # op.execute("DROP TABLE transactions_old;")  -- run separately after validation
```

---

## 16. Performance Expectations

### 16.1 Sizing Estimates

| Metric | Estimate |
|---|---|
| Tenants | 100,000 |
| Avg transactions/tenant/month | 200 |
| Total transactions (3 years) | ~720M rows |
| Avg transaction_lines/transaction | 3 |
| Total transaction_lines (3 years) | ~2.16B rows |
| audit_log entries (3 years) | ~500M rows |

### 16.2 Hardware Recommendations

| Resource | Minimum | Recommended |
|---|---|---|
| CPU | 8 vCPU | 32 vCPU |
| RAM | 32 GB | 128 GB |
| Storage | 2 TB SSD | 10 TB NVMe SSD |
| PostgreSQL | 15+ | 16+ |
| Shared buffers | 8 GB | 32 GB |
| effective_cache_size | 24 GB | 96 GB |

### 16.3 PostgreSQL Configuration (`postgresql.conf`)

```ini
# Memory
shared_buffers = 32GB            # ~25% of RAM
effective_cache_size = 96GB      # ~75% of RAM
work_mem = 64MB                  # per sort operation (be careful with many connections)
maintenance_work_mem = 2GB       # for VACUUM, index creation

# Checkpoints
checkpoint_completion_target = 0.9
wal_buffers = 64MB
min_wal_size = 1GB
max_wal_size = 8GB

# Query planner
random_page_cost = 1.1           # SSD: closer to seq_page_cost
effective_io_concurrency = 200   # SSD: high parallelism

# Parallelism
max_worker_processes = 16
max_parallel_workers_per_gather = 4
max_parallel_workers = 16

# Connections (handled by PgBouncer)
max_connections = 200            # PgBouncer server connections

# JIT (disable for OLTP)
jit = off
```

---

## 17. Tenant Isolation Verification Matrix

| Scenario | Mechanism | Test |
|---|---|---|
| Tenant A cannot read Tenant B's transactions | RLS USING clause | `SET app.tenant_id='A'; SELECT WHERE tenant_id='B'` → 0 rows |
| Tenant A cannot insert row with Tenant B's ID | RLS WITH CHECK clause | `INSERT INTO transactions (tenant_id) VALUES ('B')` → ERROR |
| Admin can read all tenants | `superadmin` bypasses RLS | `SET ROLE superadmin; SELECT COUNT(*) FROM transactions` → all rows |
| app_service cannot access tenants table | `REVOKE ALL ON tenants FROM app_service` | `SET ROLE app_service; SELECT * FROM tenants` → ERROR |
| Audit log is append-only | Restrictive UPDATE/DELETE policy | `UPDATE audit_log SET summary='x'` as app_service → ERROR |
| Global tables readable by all | SELECT policy USING(TRUE) | `SET app.tenant_id='A'; SELECT * FROM securities` → all securities |
| Global tables not writable by app_service | Restrictive write policy | `SET ROLE app_service; INSERT INTO securities ...` → ERROR |
| No tenant_id = no data visible | RLS USING: tenant_id = current_tenant_id() | `SET app.tenant_id=''; SELECT * FROM transactions` → 0 rows (NULL UUID match) |

---

## 18. Configuration Changes

### 18.1 Environment Variables (`.env`)

```bash
# Replace SQLite URL:
# OLD: DATABASE_URL=sqlite:///./ledger.db
# NEW:
DATABASE_URL=postgresql+asyncpg://app_service:STRONG_PASS@localhost:6432/ledger
ADMIN_DATABASE_URL=postgresql+asyncpg://superadmin:ADMIN_PASS@localhost:5432/ledger

# PgBouncer
PGBOUNCER_HOST=localhost
PGBOUNCER_PORT=6432
PG_POOL_SIZE=20
PG_MAX_OVERFLOW=40

# Tenant context
JWT_ALGORITHM=HS256
JWT_EXPIRY_MINUTES=60
# JWT payload must include: {"sub": user_id, "tenant_id": "uuid-here", "role": "USER|ADMIN"}
```

### 18.2 `requirements.txt` Updates

```txt
# Remove:
# (no SQLite-specific drivers needed)

# Add:
asyncpg>=0.29.0           # async PostgreSQL driver for SQLAlchemy
psycopg2-binary>=2.9.9    # sync driver (for Alembic migrations)
sqlalchemy[asyncio]>=2.0.0
alembic>=1.13.0
```

---

## 19. Summary: What Changes vs. What Stays the Same

### ✅ No Changes Needed
- All SQLAlchemy ORM relationship definitions (one-to-many, many-to-many) for financial data
- Business logic in services layer (repositories handle DB queries)
- PDF parser and CSV import logic
- Frontend/React data display components

### 🔄 Must Change
- `engine.py` — switch to `create_async_engine` with `asyncpg`; set BOTH `app.tenant_id` AND `app.user_id` per request
- `users.py` ORM model — remove `tenant_id`; email becomes globally `UNIQUE`
- `user_profiles.py` ORM model — remove `tenant_id`; link only to `users.id`
- All other ORM models — add `tenant_id: Mapped[uuid.UUID]` via `TenantScopedMixin`
- Model column types — REAL → Numeric, TEXT dates → Date/DateTime, INTEGER booleans → Boolean
- `config.py` — add `ADMIN_DATABASE_URL`, `PG_POOL_SIZE`
- JWT — must carry `sub` (user_id), `tenant_id` (active tenant), `role` (membership role), `exp`
- Auth flow — add `/auth/login` (returns tenant list) + `/auth/select-tenant` (issues scoped JWT)
- Every FastAPI dependency that yields a session — set both context vars from JWT
- All write endpoints — add `require_role(...)` guard based on JWT `role` claim

### ➕ New Additions
- `tenants` table (global) with `entity_type` for ITR filing
- `users` table redesigned as global (no `tenant_id`)
- `tenant_memberships` junction table (M:N with roles)
- `current_tenant_id()` and `current_user_id()` PostgreSQL helper functions
- RLS policies on all 37 data tables + separate policies for global tables
- PgBouncer configuration (transaction mode)
- Alembic migration scripts (Phases 1–6)
- Admin connection pool and `require_admin` dependency
- Three stored procedures: `provision_new_user()`, `provision_additional_tenant()`, `invite_member_to_tenant()`
- Partition maintenance cron job for `audit_log`
- Role permission matrix (OWNER > ADMIN > ACCOUNTANT > MEMBER > VIEWER > ADVISOR)

---

## 20. Test-Driven Development (TDD) Strategy

The migration to a multi-tenant PostgreSQL architecture follows a strict Test-Driven Development approach. All architectural components—including Row-Level Security (RLS), table partitioning, and data isolation—must be verified through an automated test suite before application integration.

### 20.1 Test Infrastructure Overview

1. **PostgreSQL Testcontainers (`testcontainers-postgres`)**:
   Instead of mocking the database, the test suite spins up a real PostgreSQL container (matching the production version, e.g., `postgres:16-alpine`) for every test session. The container is configured automatically in `tests/conftest.py`.
2. **`pytest-asyncio` & `SQLAlchemy AsyncSession`**:
   The test session leverages async sessions. Setup functions create the test schema programmatically (or by running Alembic migrations) and prepare the database.
3. **Transaction Isolation**:
   Tests run within a nested transaction created via `session.begin_nested()`. After the test assertions execute, the nested transaction is rolled back, guaranteeing a clean slate for the next test without needing `TRUNCATE` operations on hot tables.

### 20.2 Core Test Fixtures

The TDD pipeline relies heavily on defining context-aware session fixtures in `conftest.py`.

* **`tenant_a_session` & `tenant_b_session`**:
  Fixtures that automatically call `set_config('app.tenant_id', ...)` with pre-defined UUIDs before yielding the session. These accurately simulate application-level requests bound to specific tenants.
* **`admin_session`**:
  A session acting as `superadmin` to test bypass behaviors on RLS and global management flows.

### 20.3 RLS Isolation Testing Strategy

Row-Level Security is the foundation of multi-tenancy and must be tested rigorously.

* **Cross-Tenant Read Isolation**:
  A test will insert data for `Tenant A` and `Tenant B` as a superuser. Then, a query using `tenant_a_session` must assert that only `Tenant A`'s data is returned.
* **Insert `WITH CHECK` Validation**:
  A test will attempt to insert a record for `Tenant B` while active in `tenant_a_session`. The framework must assert that a `sqlalchemy.exc.InternalError` (or PostgreSQL equivalent check violation) is raised.
* **Global Tables Mutability**:
  Tests will verify that reference tables (e.g., `currencies`) are globally readable by tenant sessions, but any `INSERT/UPDATE/DELETE` operations by a scoped tenant session are explicitly rejected. Only `admin_session` should succeed in writes.

### 20.4 Partitioning and Scaling Tests

* **Partition Strategy Validation**:
  Tests will inspect the PostgreSQL catalog (`pg_class` and `pg_inherits`) to confirm that hot tables like `transactions` have correctly created hash partitions.
* **Routing Logic Validation**:
  Data inserted under various `tenant_id`s will be queried directly from the partition tables (e.g., `transactions_p0`, `transactions_p1`) to verify that the PostgreSQL `PARTITION BY HASH` routes tuples to the expected partition evenly.

### 20.5 Migration Validation Tests

The test suite must validate real `alembic` operations.
A dedicated pytest marker (`@pytest.mark.migration`) runs tests that execute `alembic upgrade head` and `alembic downgrade base` against a fresh testcontainer. This validates that the schema scripts run idempotently and safely without manual intervention during CI/CD.
