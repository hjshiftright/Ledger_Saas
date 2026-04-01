# PgBouncer Connection Pooling — Integration Specification

**Status:** Draft  
**Date:** 2026-04-01  
**Project:** Ledger 3.0 SaaS  
**Scope:** Backend connection layer only (no frontend changes)

---

## 1. Problem Statement

### 1.1 Current Architecture

```
Users (HTTP)
    │
    ▼
FastAPI / Uvicorn workers (N processes)
    │
    ├── app_service engine   →  pool_size=20, max_overflow=40  ─┐
    └── admin engine         →  pool_size=3,  max_overflow=5   ─┤
                                                                  ▼
                                                        PostgreSQL :5432
                                                        (direct TCP connections)
```

### 1.2 The Problem

Each **Uvicorn process** (or worker) maintains its own `QueuePool` inside SQLAlchemy. When running multiple replicas or processes, the number of real PostgreSQL connections grows linearly:

| Replicas | app_service max | admin max | Total |
|----------|----------------|-----------|-------|
| 1        | 60             | 8         | 68    |
| 3        | 180            | 24        | 204   |
| 5        | 300            | 40        | 340   |

Each connection is an **SSL socket** in PostgreSQL — it forks a backend process (~5 MB RSS) and holds an open file descriptor.  
This creates:

- **SSL socket saturation** — PostgreSQL's `max_connections` is typically 100–200 on small instances.
- **Backend fork overhead** — PostgreSQL process-per-connection model; idle backends waste RAM.
- **Connection churn** — `pool_recycle=3600` causes 60 connections to close/reopen every hour per replica.
- **Burst instability** — `max_overflow=40` can spike to 60 connections instantly during traffic bursts.

### 1.3 Why PgBouncer, Not Just Tuning the Pool

| Alternative | Why It Falls Short |
|-------------|-------------------|
| Reduce `pool_size` | Increases wait latency; doesn't help cross-process sharing |
| Use `NullPool` | Creates/destroys a connection per request — much worse SSL overhead |
| Single-process uvicorn | Eliminates horizontal scalability |
| PgBouncer (transaction mode) | **Multiplexes N app connections → M server connections (M ≪ N)** |

---

## 2. Proposed Architecture

```
Users (HTTPS)
    │
    ▼
Nginx (TLS termination, reverse proxy)
    │
    ▼
FastAPI / Uvicorn workers  ←── scales horizontally
    │
    ├── app_service engine  →  pool_size=5, max_overflow=10
    │       asyncpg (statement_cache_size=0)
    │
    └── admin engine  ──────────────────────────────────────── bypasses PgBouncer
                             (direct to PostgreSQL :5432)
                                    │
                                    ▼  ┌──────────────────────────┐
                                       │  Alembic migrations      │
                                       │  Superadmin DDL          │
                                       │  REINDEX / VACUUM / COPY │
                                       └──────────────────────────┘
    │
    ▼ (app_service traffic only)
PgBouncer :6432
    │  Transaction-mode pooling
    │  pool_mode = transaction
    │  server_pool_size = 10   (max server connections per user/db pair)
    │  max_client_conn = 200   (accept many app-side connections)
    │
    ▼
PostgreSQL :5432
    │  app_service role   (RLS enforced)
    │  superadmin role    (admin engine direct connection)
    └── max_connections = 50  (can be reduced significantly)
```

### 2.1 Connection Count Math (Post-PgBouncer)

| Component | Client Connections | Server Connections |
|-----------|-------------------|-------------------|
| 5 replicas × app_service pool (5+10) | up to 75 clients | **10** (PgBouncer cap) |
| admin engine (direct, per replica) | 5 × 8 = 40 | 40 (DDL/admin only) |
| Alembic (NullPool, migration-time only) | 1 | 1 (transient) |
| **Total peak server connections** | | **~51** |

This is a **~85% reduction** in PostgreSQL server-side connections vs. the current architecture at 5 replicas.

---

## 3. Compatibility Analysis

### 3.1 asyncpg + PgBouncer Transaction Mode

**Critical constraint:** asyncpg by default caches prepared statements per connection (PostgreSQL extended query protocol). PgBouncer in transaction mode reassigns server connections between transactions, so a cached statement prepared on connection A may be sent to connection B — causing protocol errors.

**Resolution:** Disable the prepared statement cache in asyncpg:

```python
connect_args={
    "statement_cache_size": 0,       # asyncpg: disable prepared statement cache
    "prepared_statement_cache_size": 0,  # asyncpg >=0.29 alternate key
    "server_settings": {
        "application_name": "ledger_api",
        "jit": "off",
    },
}
```

No other code changes are required; SQLAlchemy's `text()`, ORM queries, and `execute()` all work correctly with this setting.

### 3.2 RLS Session Variables (`SET LOCAL`)

The app sets tenant context using:

```python
SELECT set_config('app.tenant_id', :tid, TRUE),
       set_config('app.user_id',   :uid, TRUE)
```

The third argument `TRUE` maps to `is_local = TRUE` in PostgreSQL, which means the variable is scoped to the **current transaction** only and is reset automatically at `COMMIT` or `ROLLBACK`.

**This is fully compatible with PgBouncer transaction mode.** When PgBouncer releases a server connection back to the pool after a transaction ends, the `app.tenant_id`/`app.user_id` variables are already cleared by PostgreSQL itself. There is no risk of tenant context leaking to another client's transaction.

### 3.3 `pool_pre_ping` with PgBouncer

`pool_pre_ping=True` issues a lightweight `SELECT 1` before each checkout. This works correctly with PgBouncer — PgBouncer relays it to a server connection and returns the result. No changes needed.

### 3.4 `pool_recycle` with PgBouncer

`pool_recycle=3600` closes SQLAlchemy-side connections (client→PgBouncer) after 1 hour. This is still useful to prevent stale client connections to PgBouncer. The value can be relaxed (e.g. 7200) since PgBouncer's own `server_lifetime` setting handles the PostgreSQL-side recycling independently.

### 3.5 Alembic Migrations — Must Bypass PgBouncer

Migrations use `DDL` statements and set PostgreSQL session-level variables (e.g. `SET search_path`). These require a dedicated, persistent server connection. Alembic already uses `NullPool`:

```python
engine = create_async_engine(
    settings.admin_database_url,  # points directly to :5432, NOT :6432
    poolclass=pool.NullPool,
)
```

The `admin_database_url` must always point directly to PostgreSQL `:5432`, never through PgBouncer. This is the existing correct pattern and requires no change.

### 3.5a SSL Socket Reduction — App → PgBouncer Segment

This section directly answers: **does the spec reduce SSL sockets between the application and PgBouncer?**

#### What the spec reduces

The pool size changes in `engine.py` reduce the maximum number of persistent connections from the app to PgBouncer:

| | Per Replica | 5 Replicas |
|---|------------|------------|
| Before | pool_size=20 + max_overflow=40 = **60 SSL sockets** | **300** |
| After | pool_size=5 + max_overflow=10 = **15 SSL sockets** | **75** |

That is a **75% reduction** in app→pgbouncer SSL sockets. However, this is not the primary technique — the real answer is to **remove SSL entirely** on this segment.

#### Why SSL on app → pgbouncer is unnecessary

Both the `api` container and the `pgbouncer` container run on the same **Docker private bridge network**. Traffic on a Docker bridge network never leaves the host machine — it is routed through the kernel's virtual network stack with no exposure to the public internet.

SSL on this segment:
- Adds ~1–5 ms of TLS handshake overhead per new connection
- Burns CPU on both ends (asymmetric key ops during handshake)
- Provides zero security benefit (the attacker would already be inside the host)

#### The fix — disable SSL on app → pgbouncer

**In `pgbouncer.ini`**, explicitly reject SSL from clients (within the private network):

```ini
; Client connections from the Docker network: no SSL needed
client_tls_sslmode = disable
```

**In `engine.py`**, add `sslmode=disable` to the asyncpg connect args so asyncpg does not attempt SSL negotiation:

```python
connect_args={
    "statement_cache_size": 0,
    "prepared_statement_cache_size": 0,
    "ssl": False,                        # no SSL for app → pgbouncer (same private network)
    "server_settings": {
        "application_name": "ledger_api",
        "jit": "off",
    },
},
```

Alternatively, encode it in the `DATABASE_URL` connection string:

```
DATABASE_URL=postgresql+asyncpg://app_service:...@pgbouncer:6432/ledger?ssl=false
```

#### What remains protected by SSL

The **pgbouncer → PostgreSQL** leg (`db:5432`) should still use SSL in production (outside a private VPC), controlled by:

```ini
; pgbouncer.ini — server side (pgbouncer → PostgreSQL)
server_tls_sslmode = require
```

#### Summary of SSL socket reduction

```
Before:
  app ─[SSL × 60/replica]──► PostgreSQL :5432

After (this spec, fully applied):
  app ─[plain TCP × 15/replica]──► pgbouncer :6432 ─[SSL × 10]──► PostgreSQL :5432
       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^
       75% fewer, SSL removed entirely               Single shared SSL pool
```

Total SSL sockets: from **60+ per replica** to **10 globally** (shared by all replicas via PgBouncer's server pool).

---

### 3.6 Unsupported Features in PgBouncer Transaction Mode

The following PostgreSQL features do **not** work in transaction mode:

| Feature | Used in Ledger? | Action |
|---------|----------------|--------|
| `SET` (session-level, without `is_local`) | No | N/A |
| `LISTEN` / `NOTIFY` | No | N/A |
| Advisory locks (`pg_advisory_lock`) | No | N/A |
| Prepared statements (`PREPARE/EXECUTE`) | No (asyncpg handles internally) | Mitigated by `statement_cache_size=0` |
| Cursors (server-side) | No | N/A |
| `LOAD` (load shared library) | No | N/A |

No existing Ledger feature uses any of these — the codebase is safe to move to transaction mode.

---

## 4. Implementation Plan

### 4.1 PgBouncer Configuration File

**File:** `pgbouncer/pgbouncer.ini`

```ini
[databases]
; Route app_service database to PostgreSQL
ledger = host=db port=5432 dbname=ledger user=app_service

[pgbouncer]
; Networking
listen_addr = 0.0.0.0
listen_port = 6432
unix_socket_dir =

; Pooling mode — MUST be transaction for asyncpg compatibility
pool_mode = transaction

; Connection limits
max_client_conn = 200          ; Accept up to 200 client-side connections
default_pool_size = 10         ; Max server connections per (user, database) pair
reserve_pool_size = 2          ; Emergency extra connections for bursts
reserve_pool_timeout = 3.0     ; Seconds to wait before using reserve pool
min_pool_size = 2              ; Keep at least 2 server connections warm

; Server connection lifecycle
server_lifetime = 3600         ; Recycle server connections after 1 hour
server_idle_timeout = 600      ; Close idle server connections after 10 minutes
server_connect_timeout = 10    ; Fail fast if PostgreSQL is unreachable
server_login_retry = 15        ; Retry interval for failed server connections

; Client connection lifecycle
client_idle_timeout = 0        ; Do not close idle client connections (app pools reconnect)
query_timeout = 0              ; No per-query timeout (let app/PostgreSQL handle)
query_wait_timeout = 30        ; Fail client if no server connection available in 30s

; Authentication
auth_type = scram-sha-256      ; Match PostgreSQL pg_hba.conf
auth_file = /etc/pgbouncer/userlist.txt

; Logging
log_connections = 0            ; Do not log every connection (high volume)
log_disconnections = 0
log_pooler_errors = 1
stats_period = 60              ; Log pool stats every 60 seconds

; Admin console
admin_users = pgbouncer_admin
stats_users = pgbouncer_stats

; TLS (optional, enable for production if PostgreSQL requires SSL)
; server_tls_sslmode = require
; server_tls_ca_file = /etc/ssl/certs/ca-certificates.crt
```

**File:** `pgbouncer/userlist.txt`

```
; Format: "username" "scram-sha-256$<iterations>:<salt>$<client_key>:<server_key>"
; Or plain MD5 for testing: "username" "md5<md5hash>"
; Generate with: psql -c "SELECT concat('\"', rolname, '\" \"', rolpassword, '\"') FROM pg_authid WHERE rolname = 'app_service';"
"app_service" "scram-sha-256$4096:..."
```

### 4.2 Docker Compose Changes

**File:** `docker-compose.yml` — add pgbouncer service and update api environment:

```yaml
services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: ledger
      POSTGRES_USER: ledger           # superadmin for init
      POSTGRES_PASSWORD: ledger_secret
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./pgbouncer/init.sql:/docker-entrypoint-initdb.d/01_roles.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ledger -d ledger"]
      interval: 5s
      timeout: 5s
      retries: 10

  pgbouncer:
    image: pgbouncer/pgbouncer:1.22
    depends_on:
      db:
        condition: service_healthy
    environment:
      DATABASES_HOST: db
      DATABASES_PORT: "5432"
      DATABASES_USER: app_service
      DATABASES_PASSWORD: "${APP_SERVICE_PASSWORD}"
      DATABASES_DBNAME: ledger
      PGBOUNCER_POOL_MODE: transaction
      PGBOUNCER_MAX_CLIENT_CONN: "200"
      PGBOUNCER_DEFAULT_POOL_SIZE: "10"
      PGBOUNCER_MIN_POOL_SIZE: "2"
      PGBOUNCER_RESERVE_POOL_SIZE: "2"
      PGBOUNCER_SERVER_LIFETIME: "3600"
      PGBOUNCER_SERVER_IDLE_TIMEOUT: "600"
      PGBOUNCER_AUTH_TYPE: scram-sha-256
      PGBOUNCER_LISTEN_PORT: "6432"
    ports:
      - "6432:6432"
    healthcheck:
      test: ["CMD", "psql", "-h", "localhost", "-p", "6432", "-U", "app_service", "-d", "ledger", "-c", "SELECT 1"]
      interval: 10s
      timeout: 5s
      retries: 5

  api:
    build:
      context: ./backend
      dockerfile: Dockerfile
    depends_on:
      db:
        condition: service_healthy
      pgbouncer:
        condition: service_healthy
    environment:
      # app_service role → goes THROUGH PgBouncer
      DATABASE_URL: "postgresql+asyncpg://app_service:${APP_SERVICE_PASSWORD}@pgbouncer:6432/ledger"
      # superadmin role → bypasses PgBouncer (DDL, admin tasks)
      ADMIN_DATABASE_URL: "postgresql+asyncpg://superadmin:${SUPERADMIN_PASSWORD}@db:5432/ledger"
      APP_ENV: production
      APP_HOST: 0.0.0.0
      APP_PORT: "8000"
      APP_DEBUG: "false"
      SECRET_KEY: "${SECRET_KEY}"

  web:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    depends_on:
      - api
    ports:
      - "80:80"

volumes:
  postgres_data:
```

### 4.3 Backend Engine Changes

**File:** `backend/src/db/engine.py`

Three changes:
1. Set `statement_cache_size=0` in asyncpg connect args (PgBouncer compatibility)
2. Reduce `pool_size` and `max_overflow` (PgBouncer handles multiplexing)
3. Relax `pool_recycle` (PgBouncer owns server-side lifecycle)

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
from config import get_settings

settings = get_settings()

# ── App service engine: routes THROUGH PgBouncer ──────────────────────────────
engine = create_async_engine(
    settings.database_url,           # postgresql+asyncpg://...@pgbouncer:6432/ledger
    pool_size=5,                     # reduced: PgBouncer multiplexes N→M
    max_overflow=10,                 # reduced: PgBouncer's max_client_conn is the real limit
    pool_pre_ping=True,              # still useful: detects dead client→PgBouncer connections
    pool_recycle=7200,               # relaxed: PgBouncer manages server-side recycling
    connect_args={
        "statement_cache_size": 0,           # REQUIRED: disable asyncpg prepared statement cache
        "prepared_statement_cache_size": 0,  # asyncpg >=0.29 alias
        "server_settings": {
            "application_name": "ledger_api",
            "jit": "off",
        },
    },
)

SessionFactory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# ── Admin engine: BYPASSES PgBouncer, direct to PostgreSQL :5432 ──────────────
# Used for: superadmin operations, schema introspection, heavy analytics
admin_engine = create_async_engine(
    settings.admin_database_url,     # postgresql+asyncpg://superadmin@db:5432/ledger
    pool_size=3,
    max_overflow=5,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={
        "server_settings": {
            "application_name": "ledger_admin",
        },
    },
)

AdminSessionFactory = async_sessionmaker(
    admin_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)
```

> **Note:** No changes to `get_session_with_context()` — `set_config(..., TRUE)` is already transaction-scoped and compatible with PgBouncer transaction mode.

### 4.4 Environment Variable Updates

**File:** `.env.example`

```bash
# ── Database roles ─────────────────────────────────────────────────────────────
APP_SERVICE_PASSWORD=change_me_app_service
SUPERADMIN_PASSWORD=change_me_superadmin

# app_service: routes through PgBouncer
DATABASE_URL=postgresql+asyncpg://app_service:change_me_app_service@pgbouncer:6432/ledger

# superadmin: bypasses PgBouncer (DDL, admin, alembic)
ADMIN_DATABASE_URL=postgresql+asyncpg://superadmin:change_me_superadmin@db:5432/ledger

# ── Application ────────────────────────────────────────────────────────────────
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
APP_DEBUG=false
SECRET_KEY=change-me-before-going-to-production
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:80

# ── LLM Providers ──────────────────────────────────────────────────────────────
GEMINI_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
DEFAULT_LLM_PROVIDER=GOOGLE
```

### 4.5 Alembic — No Change Required

`backend/alembic/env.py` already uses:

```python
engine = create_async_engine(
    settings.admin_database_url,  # direct to :5432
    poolclass=pool.NullPool,
)
```

`admin_database_url` must remain pointed at `db:5432` (not `pgbouncer:6432`). The existing code is correct as-is.

### 4.6 Entrypoint Health Check Update

**File:** `backend/entrypoint.sh` — wait for PgBouncer to be healthy before starting:

```sh
#!/bin/sh
set -e

echo "Waiting for PostgreSQL via PgBouncer..."
until python - <<'EOF'
import asyncio
import asyncpg
import os
import sys

async def check():
    url = os.environ.get("DATABASE_URL", "")
    # Parse postgresql+asyncpg:// → asyncpg DSN
    dsn = url.replace("postgresql+asyncpg://", "postgresql://")
    try:
        conn = await asyncpg.connect(dsn, statement_cache_size=0)
        await conn.fetchval("SELECT 1")
        await conn.close()
        sys.exit(0)
    except Exception as e:
        print(f"  pgbouncer not ready: {e}")
        sys.exit(1)

asyncio.run(check())
EOF
do
    sleep 2
done
echo "PgBouncer ready. Starting API..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## 5. PgBouncer Operational Details

### 5.1 Pool Sizing Formula

```
server_pool_size = ceil(max_db_connections * 0.8 / num_user_db_pairs)
```

For Ledger's current setup:
- PostgreSQL `max_connections = 50`
- Reserve 5 for admin/superadmin direct connections
- Available for app_service: 45
- `server_pool_size = 10` (leaves headroom for spikes)

Adjust `server_pool_size` upward if you observe `query_wait_timeout` errors in PgBouncer logs.

### 5.2 Monitoring PgBouncer

Connect to the PgBouncer admin console:

```bash
psql -h localhost -p 6432 -U pgbouncer_admin pgbouncer
```

Useful commands:

```sql
-- Pool statistics (client connections, server connections, queue depth)
SHOW POOLS;

-- Per-database stats (queries/sec, bytes in/out)
SHOW STATS;

-- Current server connections
SHOW SERVERS;

-- Current client connections
SHOW CLIENTS;

-- Reload config without restart
RELOAD;

-- Pause all connections (for maintenance)
PAUSE ledger;

-- Resume
RESUME ledger;
```

### 5.3 Key Metrics to Alert On

| Metric (`SHOW POOLS`) | Column | Alert Threshold |
|-----------------------|--------|----------------|
| Clients waiting in queue | `cl_waiting` | > 5 |
| Server connections used | `sv_used` | > `server_pool_size * 0.9` |
| Server connections idle | `sv_idle` | < `min_pool_size` |
| Clients connected | `cl_active + cl_waiting` | > `max_client_conn * 0.8` |

---

## 6. PostgreSQL Configuration Adjustments

With PgBouncer in place, reduce PostgreSQL `max_connections`:

**File:** `postgres.conf` (or via Docker environment):

```conf
# Reduce from default 100–200 to match PgBouncer's actual server connections
max_connections = 50

# Shared buffers can be increased since we freed memory from fewer backends
shared_buffers = 256MB
work_mem = 4MB
maintenance_work_mem = 64MB

# Connection-related
tcp_keepalives_idle = 60
tcp_keepalives_interval = 10
tcp_keepalives_count = 5
```

For Docker Compose:

```yaml
db:
  image: postgres:15-alpine
  command:
    - postgres
    - -c
    - max_connections=50
    - -c
    - shared_buffers=256MB
    - -c
    - work_mem=4MB
```

---

## 7. Security Considerations

### 7.1 PgBouncer Authentication

- Use `auth_type = scram-sha-256` (matches PostgreSQL 15 default `pg_hba.conf`)
- Do **not** use `trust` or `md5` in production
- The `userlist.txt` file must contain hashed passwords — never plaintext
- Generate the hash with:

```sql
-- In PostgreSQL, run as superuser:
SELECT concat('"', rolname, '" "', rolpassword, '"')
FROM pg_authid
WHERE rolname = 'app_service';
```

### 7.2 Network Isolation

- PgBouncer should **not** be exposed outside the Docker network
- Only the `api` container needs access to `pgbouncer:6432`
- PostgreSQL should only accept connections from `pgbouncer` and the `api` container (for admin)
- `pg_hba.conf` should restrict `app_service` login to PgBouncer's IP range only

```
# pg_hba.conf
# TYPE  DATABASE  USER          ADDRESS         METHOD
host    ledger    app_service   pgbouncer_ip/32  scram-sha-256
host    ledger    superadmin    api_ip/32        scram-sha-256
local   all       postgres                        peer
```

### 7.3 TLS

For production deployments outside a private VPC:

```ini
; pgbouncer.ini — server TLS (PgBouncer → PostgreSQL)
server_tls_sslmode = require
server_tls_ca_file = /etc/ssl/certs/ca-certificates.crt

; client TLS (App → PgBouncer) — optional if inside same private network
client_tls_sslmode = allow
client_tls_cert_file = /etc/pgbouncer/server.crt
client_tls_key_file = /etc/pgbouncer/server.key
```

---

## 8. Testing Plan

### 8.1 Functional Verification

After deploying PgBouncer, run the existing test suite against the real stack:

```bash
# Start full stack with PgBouncer
docker compose up --build

# Run integration tests
cd backend
PYTHONPATH=src python -m pytest tests/integration/ -v

# Run API tests against live server
PYTHONPATH=src python -m pytest tests/api/ -v
```

Expected: all existing tests pass without modification — no application code changes other than `engine.py` and environment variables.

### 8.2 RLS Context Leak Test

Critical correctness test — verify tenant isolation is maintained through PgBouncer:

```python
import asyncio
import asyncpg

async def test_rls_no_leak():
    """
    Simulate two concurrent tenants.
    Verify tenant A cannot see tenant B's data through a recycled connection.
    """
    dsn = "postgresql://app_service:password@pgbouncer:6432/ledger"
    
    async def set_tenant_and_read(tenant_id: str) -> str:
        conn = await asyncpg.connect(dsn, statement_cache_size=0)
        async with conn.transaction():
            await conn.execute(
                "SELECT set_config('app.tenant_id', $1, TRUE)", tenant_id
            )
            result = await conn.fetchval("SELECT current_setting('app.tenant_id', TRUE)")
        # After transaction end, app.tenant_id must be cleared
        leaked = await conn.fetchval("SELECT current_setting('app.tenant_id', TRUE)")
        await conn.close()
        return result, leaked
    
    results = await asyncio.gather(
        set_tenant_and_read("tenant-A"),
        set_tenant_and_read("tenant-B"),
    )
    
    for (inside_tx, after_tx) in results:
        assert after_tx == ""  # must be empty after transaction — no leak
```

### 8.3 Connection Count Verification

```bash
# Check actual server connections to PostgreSQL
psql -h localhost -p 5432 -U postgres -c "
  SELECT count(*), state, wait_event_type, application_name
  FROM pg_stat_activity
  WHERE datname = 'ledger'
  GROUP BY state, wait_event_type, application_name
  ORDER BY count DESC;
"

# Check PgBouncer pool utilization
psql -h localhost -p 6432 -U pgbouncer_admin pgbouncer -c "SHOW POOLS;"
```

### 8.4 Load Test

```bash
# Using k6 or wrk — 50 concurrent users, 60 seconds
wrk -t 10 -c 50 -d 60s http://localhost:8000/api/v1/transactions

# While running, monitor:
watch -n1 'psql -h localhost -p 6432 -U pgbouncer_admin pgbouncer -c "SHOW POOLS;" 2>&1'
```

---

## 9. Migration Steps (Ordered)

```
Step 1: Create pgbouncer/ directory with pgbouncer.ini and userlist.txt
Step 2: Add pgbouncer service to docker-compose.yml
Step 3: Update .env.example with DATABASE_URL pointing to pgbouncer:6432
Step 4: Update backend/src/db/engine.py (statement_cache_size=0, reduced pool sizes)
Step 5: Update backend/entrypoint.sh to wait for PgBouncer
Step 6: Run: docker compose down && docker compose up --build
Step 7: Run Alembic migrations via admin_database_url (direct to :5432)
Step 8: Run full test suite
Step 9: Verify SHOW POOLS; shows sv_used ≤ 10 under normal load
Step 10: Set PostgreSQL max_connections = 50
```

---

## 10. Rollback Plan

PgBouncer is transparent to the application. To roll back:

1. Set `DATABASE_URL` back to `postgresql+asyncpg://app_service:...@db:5432/ledger`
2. Restore `pool_size=20, max_overflow=40` in `engine.py`
3. Remove `statement_cache_size=0` from connect_args (optional — it's harmless without PgBouncer)
4. Remove pgbouncer service from docker-compose.yml
5. Restart api container

No database schema changes are involved — rollback is instant.

---

## 11. Future Considerations

| Item | Notes |
|------|-------|
| **PgBouncer HA** | Run two PgBouncer instances behind a load balancer for production HA |
| **Odyssey** | Yandex Odyssey is a multi-threaded alternative to PgBouncer; supports statement-level parallelism |
| **Connection pooling in PostgreSQL 17+** | PostgreSQL 17 introduces built-in connection pooling (early stages); revisit when stable |
| **Prometheus monitoring** | Use `pgbouncer_exporter` to expose PgBouncer metrics to Prometheus/Grafana |
| **Read replicas** | Add a second PgBouncer instance routing to a read replica for reports/analytics queries |
| **`server_reset_query`** | If `SET` session-level state is ever introduced, configure `server_reset_query = DISCARD ALL` in PgBouncer as a safety net |

---

## Appendix A: Quick Reference — What Changes

| File | Change |
|------|--------|
| `docker-compose.yml` | Add `pgbouncer` service; update `api.environment.DATABASE_URL` to `pgbouncer:6432` |
| `backend/src/db/engine.py` | Add `statement_cache_size=0`; reduce `pool_size`/`max_overflow` |
| `backend/entrypoint.sh` | Update health check to use asyncpg (optional improvement) |
| `.env.example` | Update `DATABASE_URL` to `pgbouncer:6432`; `ADMIN_DATABASE_URL` stays at `db:5432` |
| `pgbouncer/pgbouncer.ini` | New file — PgBouncer configuration |
| `pgbouncer/userlist.txt` | New file — hashed credentials |

**No changes to:** routes, models, repositories, services, migrations, RLS policies, session factories (logic), frontend.

---

## Appendix B: Why Not Session Mode?

PgBouncer supports three pooling modes:

| Mode | Server connection held for | Prepared statements | `SET LOCAL` | Ledger use |
|------|---------------------------|---------------------|-------------|-----------|
| **session** | Entire client session | Yes | Yes | No saving — 1 client = 1 server |
| **transaction** | Duration of one transaction | No (disable cache) | Yes | **Recommended** |
| **statement** | Single statement | No | No | Incompatible with multi-statement transactions |

Session mode provides zero connection multiplexing benefit — each FastAPI connection would hold a dedicated PostgreSQL server connection for its entire lifetime, identical to connecting directly.

Transaction mode is the correct choice for Ledger because:
- All queries are wrapped in SQLAlchemy transactions (either explicit or autocommit)
- `SET LOCAL` (is_local=TRUE) is transaction-scoped — safe to recycle after COMMIT
- asyncpg prepared statement cache can be cleanly disabled via `statement_cache_size=0`
