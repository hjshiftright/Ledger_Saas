# Ledger 3.0

Personal finance management platform for Indian investors. Handles bank statement imports, double-entry bookkeeping, investment tracking, goals, budgets, and reports — all with AI-assisted categorisation.

## Tech Stack

| Layer | Choice |
|---|---|
| API | FastAPI (async) |
| ORM | SQLAlchemy 2.0 (async, ORM-style) |
| Database | PostgreSQL 15 + Row-Level Security |
| DB driver | asyncpg (app), psycopg2 (healthcheck) |
| Validation | Pydantic v2 |
| Auth | JWT (python-jose) |
| Migrations | Alembic (async) |
| LLM | Gemini / OpenAI / Anthropic (pluggable) |
| Frontend | React + Vite |
| Testing | pytest-asyncio + aiosqlite (unit/API) |

## Quick Start

### Option 1 — Docker Compose (recommended)

```bash
cp .env.example .env          # fill in SECRET_KEY and any LLM keys
docker compose up --build
```

API available at `http://localhost:8000`.
Frontend at `http://localhost:80`.
API docs at `http://localhost:8000/docs`.

### Option 2 — run.sh (local PostgreSQL via Docker, backend only)

```bash
chmod +x run.sh
./run.sh
```

This script starts the PostgreSQL Docker container, creates a Python venv, installs dependencies, builds the frontend, and launches the API server.

### Option 3 — manual

```bash
# 1. Start PostgreSQL (or use your own instance)
docker compose up -d db

# 2. Set up Python environment
cd Ledger_Saas
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env    # edit as needed

# 4. Run migrations
cd backend
PYTHONPATH=src alembic upgrade head

# 5. Launch API
cd src
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Environment Variables

Copy `.env.example` to `.env` and fill in the values below.

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://app_service:password@localhost:6432/ledger` | App-service role URL (RLS enforced) |
| `ADMIN_DATABASE_URL` | `postgresql+asyncpg://superadmin:password@localhost:5432/ledger` | Superadmin role URL (bypasses RLS) |
| `SECRET_KEY` | `change-me-in-production` | JWT signing secret — **change this** |
| `APP_ENV` | `development` | `development` \| `staging` \| `production` |
| `APP_PORT` | `8000` | Uvicorn bind port |
| `APP_DEBUG` | `false` | FastAPI debug mode |
| `ALLOWED_ORIGINS` | `*` | Comma-separated CORS origins |
| `GEMINI_API_KEY` | _(empty)_ | Google AI Studio key — enables AI categorisation |
| `OPENAI_API_KEY` | _(empty)_ | OpenAI key |
| `ANTHROPIC_API_KEY` | _(empty)_ | Anthropic key |
| `DEFAULT_LLM_PROVIDER` | `GOOGLE` | `GOOGLE` \| `OPENAI` \| `ANTHROPIC` |
| `MAX_UPLOAD_SIZE_MB` | `50` | File upload size limit |
| `CONFIDENCE_THRESHOLD` | `0.75` | Minimum parse confidence for auto-accept |

> **Development shortcut:** When `APP_ENV=development` and no `Authorization` header is sent, the API automatically uses a default dev user (`user_id=1`, `tenant_id=00000000-0000-0000-0000-000000000001`). Remove this shortcut for staging/production.

## Database Setup

Ledger uses **PostgreSQL Row-Level Security (RLS)** for tenant isolation. Two DB roles are required:

```sql
-- Application role — used by all API requests, cannot bypass RLS
CREATE ROLE app_service LOGIN PASSWORD 'your-password' NOSUPERUSER NOCREATEDB NOCREATEROLE;

-- Admin role — used only by Alembic migrations and provisioning
CREATE ROLE superadmin LOGIN PASSWORD 'your-password' SUPERUSER BYPASSRLS;

-- Create database
CREATE DATABASE ledger OWNER superadmin;
GRANT CONNECT ON DATABASE ledger TO app_service;
GRANT USAGE ON SCHEMA public TO app_service;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_service;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_service;
```

Then apply migrations:

```bash
cd backend
PYTHONPATH=src alembic upgrade head
```

The migration creates all tables and enables RLS with `tenant_isolation` policies on every tenant-scoped table.

## Running Tests

Tests run against an in-memory aiosqlite database — no PostgreSQL required.

```bash
cd backend
PYTHONPATH=src python -m pytest tests/ --ignore=tests/api/test_reports_api.py -q
```

Expected: **~1013 passed, 18 skipped**.

Subdirectories:

| Path | Coverage |
|---|---|
| `tests/unit/` | Service layer — onboarding, COA, accounts, goals, etc. |
| `tests/api/` | HTTP endpoints via FastAPI TestClient + aiosqlite |
| `tests/integration/` | Full pipeline (parse → normalize → categorize → propose) |
| `tests/parser/` | Bank-specific CSV/PDF parsers |
| `tests/smart/` | SmartProcessor pipeline |
| `tests/core/` | Core model schemas and enums |

## Project Layout

```
Ledger_Saas/
├── backend/
│   ├── alembic/               Alembic env + migration versions
│   ├── src/
│   │   ├── api/
│   │   │   ├── deps.py        FastAPI dependencies (auth, DB sessions)
│   │   │   └── routers/       One file per API surface area
│   │   ├── core/              In-memory pipeline models (not ORM)
│   │   ├── db/
│   │   │   ├── engine.py      Async engine, session factories
│   │   │   └── models/        SQLAlchemy ORM models
│   │   ├── modules/
│   │   │   ├── llm/           LLM provider abstraction
│   │   │   └── parser/        Bank-statement parsers
│   │   ├── onboarding/        Onboarding routers + services
│   │   ├── repositories/      SQLAlchemy repository implementations
│   │   ├── services/          Pipeline services (normalize, dedup, etc.)
│   │   ├── config.py          Settings (pydantic-settings)
│   │   └── main.py            FastAPI app factory + router wiring
│   └── tests/
├── docs/                      Architecture, specs, how-to guides
├── frontend/                  React + Vite SPA
├── docker-compose.yml
└── run.sh                     One-command local startup
```

## API Overview

Base path: `/api/v1`

| Tag | Routes | Notes |
|---|---|---|
| Auth | `/auth/*` | JWT issue, tenant selection |
| Onboarding | `/onboarding/*` | Profile, COA, institutions, accounts, opening balances, net worth |
| Document Ingestion | `/imports/*` | Upload, detect, batch lifecycle |
| Parser Pipeline | `/pipeline/*` | Parse, normalize, dedup, categorize, smart-process |
| Transactions | `/transactions/*` | CRUD on committed transactions |
| Reports | `/reports/*` | Summary, income-expense, balance sheet, net worth history |
| Goals | `/goals/*` | Goal tracking |
| Budgets | `/budgets/*` | Budget management |
| LLM | `/llm/*` | Provider registration |
| Chat | `/chat/*` | AI financial assistant |

Interactive docs: `http://localhost:8000/docs`

## Multi-Tenancy Model

- Every API request must carry a JWT with `sub` (user ID), `tenant_id` (UUID), and `role`.
- The API sets `app.tenant_id` as a PostgreSQL session variable before every query.
- RLS policies on all 35 tenant-scoped tables automatically filter rows by `current_tenant_id()`.
- App code never writes `WHERE tenant_id = ...` — isolation is enforced at the database level.
- A single user can belong to multiple tenants (M:N via `tenant_memberships`).

See [docs/specs/postgresql-multitenancy-spec.md](docs/specs/postgresql-multitenancy-spec.md) for the full design.
