<think>The user is making two important points:

1. The ERS (Engineering Requirements Specification) went too deep into code - it should stay at the requirements/specification level and not include actual code implementations. They liked the content though, so they want to keep it.

2. They want me to create Architecture and Design documents for the overall Ledger product (not just onboarding) that can serve as reference documents before proceeding with spec-driven development.

Let me create two documents:
1. **Architecture Document** - High-level system architecture, principles, constraints, technology decisions, component decomposition, deployment model
2. **Design Document** - Detailed design covering patterns, data model, API design standards, module interactions, cross-cutting concerns


These documents need to stay conceptual and avoid implementation details. I'm mapping out the core Ledger product modules: onboarding, transaction management with double-entry accounting, account operations, financial reporting (P&L, balance sheet, cash flow), Indian tax computation and 80C tracking, investment portfolio tracking with NAV and returns, budget tracking with variance analysis, and goal progress monitoring.

Now I'm adding the remaining modules—net worth snapshots for periodic tracking, recurring transaction automation, and import/export capabilities—then organizing everything into two comprehensive documents: an Architecture document covering vision, system context, containers, components, module decomposition, technology decisions, data architecture, cross-cutting concerns, quality attributes, and deployment; and a Design document detailing design philosophy, layered architecture, API standards, conceptual data models, module interactions, and error handling strategy.

I'll also incorporate event system design, security considerations, configuration management, migration strategy, and extension points throughout both documents, using prose, ASCII diagrams, and tables rather than code examples to keep the focus on architectural and design decisions.</think>You're right — an ERS should specify *what* the system must do and *how it behaves*, not dictate implementation code. That's the job of the developer guided by the architecture and design docs. Good call retaining the content but noting the boundary.

Below are the two documents: **Architecture Document** first (the "what are the big pieces and why"), then **Design Document** (the "how do the pieces work together"). Both are deliberately code-free — they describe structure, principles, contracts, and patterns at a level that guides developers without prescribing syntax.

---

# Document 1: Architecture Document

**System:** PFMS — Personal Finance Management System (Ledger)
**Version:** 1.0
**Date:** March 14, 2026
**Status:** Baseline

---

## 1. Vision and Context

PFMS is a single-user, desktop/local-first personal finance ledger rooted in double-entry bookkeeping principles. It is built for the Indian financial context — Rupee-denominated, Indian Financial Year (April–March), Indian tax regimes, and Indian financial instruments — while keeping the core engine country-agnostic enough to extend later.

The system is **not** a bank aggregator, payment gateway, or trading platform. It is a record-keeping and analysis tool. The user manually enters or imports transactions, and the system provides accurate reports, budgets, goal tracking, and tax-relevant summaries.

### 1.1 Key Stakeholders

The primary stakeholder is a single individual managing personal or household finances. There is no multi-user, multi-tenant, or organizational use case in scope.

### 1.2 System Boundaries

PFMS owns the following concerns: transaction recording, account management, Chart of Accounts, reporting (financial statements, cash flow, spending analysis), budgeting, goal tracking, net worth computation, recurring transaction management, and tax-relevant categorization.

PFMS does **not** own: fetching data from banks or brokerages (future import adapters may feed data in), stock price or NAV lookups (future market data adapters may supply this), or tax filing (the system provides data useful for filing but does not file returns).

---

## 2. Architectural Goals

**AG-1: Correctness over Convenience.** Every monetary state change is a balanced double-entry transaction. There are no shortcuts — no direct balance mutations, no single-sided entries. If the books don't balance, the system is broken.

**AG-2: API-First, Interface-Last.** All functionality is exposed as versioned HTTP APIs with OpenAPI specifications. Any user interface — CLI, web, desktop, mobile — is a client of these APIs. No business logic lives in any interface layer.

**AG-3: Testability as Architecture.** The system is structured so that every module can be tested in complete isolation using in-memory substitutes for data access. Integration tests use real storage. End-to-end tests use real APIs. This is not a testing strategy bolted on afterward — it is an architectural constraint that drives how modules are decomposed and how dependencies flow.

**AG-4: Local-First, Single-User.** The system runs entirely on the user's machine. Data is stored in a local embedded database. There are no remote servers, cloud dependencies, or network requirements for core functionality. This simplifies security (no authentication needed for V1), deployment, and privacy.

**AG-5: Extensibility through Modules.** New capabilities (investment tracking, tax computation, import adapters) are added as new modules that plug into the existing event bus and data layer. Existing modules should not need modification when new modules are added (Open/Closed Principle at the module level).

**AG-6: Indian Context as Default, Not Hardcoded.** Indian financial concepts (FY starting April, ₹, lakh/crore formatting, PPF/EPF/NPS, Section 80C) are the default configuration, not hardcoded assumptions. The data model and engine support configurable FY start months, currencies, and instrument types so that regional adaptation is possible without re-architecture.

---

## 3. Architectural Constraints

**AC-1: Python only.** The entire system — API server, services, data access, CLI, tests — is written in Python 3.11+. No polyglot complexity.

**AC-2: Embedded database by default.** SQLite is the default data store — no external database servers required for basic operation. The database file lives alongside the application. The database engine is configurable via connection string; PostgreSQL is supported for household-server or cloud-hosted deployments. The architectural constraint is "no external server required for default operation," not "SQLite only."

**AC-3: SQLAlchemy Core for data access.** Data access uses SQLAlchemy Core's SQL expression language — not the full ORM session/model layer. Table definitions are Python objects (`Table` / `MetaData`). Queries are built with the expression API (`select()`, `insert()`, `where()`), which generates database-agnostic SQL. This keeps queries explicit and visible while enabling database portability. Repository methods encapsulate all data access — calling code never constructs queries directly.

**AC-4: Synchronous processing.** The system is single-user and local. There is no need for async I/O, message queues, or background workers in V1. All operations are synchronous request-response. FastAPI's async capabilities are available but not required.

**AC-5: No external runtime server dependencies.** The system must start with `python -m pfms` and nothing else. No Redis, no Docker requirement in the default configuration. If a PostgreSQL connection string is configured, the system connects to that instead of SQLite — but this is an opt-in deployment choice, not a default requirement. Python library dependencies (SQLAlchemy, Alembic, FastAPI, Pydantic) are pure Python and installable via pip.

---

## 4. System Context (C4 Level 1)

```
┌─────────────────────────────────────────────────┐
│                                                 │
│                  PFMS User                      │
│           (Individual / Household)              │
│                                                 │
└────────┬────────────────────┬───────────────────┘
         │                    │
         │ CLI commands       │ Browser (Swagger / future Web UI)
         │                    │
         ▼                    ▼
┌─────────────────────────────────────────────────┐
│                                                 │
│          PFMS Ledger System                     │
│                                                 │
│  • Record transactions                          │
│  • Manage accounts & Chart of Accounts          │
│  • Track budgets, goals, net worth              │
│  • Generate financial reports                   │
│  • Manage recurring transactions                │
│  • Provide tax-relevant categorization          │
│                                                 │
└────────┬────────────────────────────────────────┘
         │
         │ Read/Write
         ▼
┌─────────────────────┐     ┌─────────────────────┐
│  Database             │     │  CSV / File Import   │
│  (SQLite default)     │     │  (Future)            │
└─────────────────────┘     └─────────────────────┘
```

There are no external systems that PFMS depends on at runtime. Future adapters for bank statement import and market data are inbound data feeders and are not required for core operation.

---

## 5. Container View (C4 Level 2)

The system consists of three runtime containers, all running in the same process or invoked from the same machine.

```
┌──────────────────────────────────────────────────────────────┐
│  PFMS Process                                                │
│                                                              │
│  ┌──────────────────────┐    ┌──────────────────────┐       │
│  │   API Server          │    │   CLI Application     │       │
│  │   (FastAPI)           │    │   (Typer)             │       │
│  │                       │    │                       │       │
│  │  • Hosts REST APIs    │    │  • Terminal commands  │       │
│  │  • Serves Swagger UI  │    │  • Calls REST APIs    │       │
│  │  • Validates requests │    │  • Formats output     │       │
│  │  • Returns JSON       │    │  • Human-readable     │       │
│  └──────────┬────────────┘    └───────────┬───────────┘       │
│             │                             │                   │
│             │  Depends on                 │ HTTP calls to     │
│             ▼                             │ API Server        │
│  ┌──────────────────────┐                 │                   │
│  │   Core Engine         │ ◄──────────────┘                   │
│  │   (Python Package)    │                                    │
│  │                       │                                    │
│  │  • Service layer      │                                    │
│  │  • Repository layer   │                                    │
│  │  • Domain models      │                                    │
│  │  • Event bus          │                                    │
│  └──────────┬────────────┘                                    │
│             │                                                 │
│             │ Reads / Writes                                  │
│             ▼                                                 │
│  ┌──────────────────────┐                                    │
│  │   Database             │                                    │
│  │   (SQLite default)     │                                    │
│  └──────────────────────┘                                    │
└──────────────────────────────────────────────────────────────┘
```

The **API Server** is the primary interface. It imports and delegates to the Core Engine directly (in-process call). The **CLI Application** is a separate entry point that can either call the Core Engine directly (SDK mode) or call the API Server over HTTP (client mode). During development and testing, the CLI operates in client mode against the running API server, validating that all functionality is accessible over HTTP.

---

## 6. Component View (C4 Level 3) — Module Decomposition

The Core Engine is decomposed into functional modules. Each module is a self-contained Python package with its own schemas, service, and router. Modules communicate through the event bus — never by importing each other's services directly.

```
┌─────────────────────────────────────────────────────────────────┐
│  Core Engine                                                     │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ Onboarding   │  │ Transactions │  │ Reporting               │ │
│  │              │  │              │  │                         │ │
│  │ • Profile    │  │ • Recording  │  │ • Balance Sheet         │ │
│  │ • COA Setup  │  │ • Voiding    │  │ • Income & Expense Stmt │ │
│  │ • Institution│  │ • Transfers  │  │ • Cash Flow             │ │
│  │ • Accounts   │  │ • Splits     │  │ • Spending Analysis     │ │
│  │ • Opening Bal│  │ • Search     │  │ • Category Reports      │ │
│  │ • Goals      │  │ • Filtering  │  │ • Custom Date Ranges    │ │
│  │ • Budget     │  │              │  │                         │ │
│  │ • Recurring  │  │              │  │                         │ │
│  │ • Net Worth  │  │              │  │                         │ │
│  │ • Orchestratr│  │              │  │                         │ │
│  └──────┬───────┘  └──────┬───────┘  └────────────┬────────────┘ │
│         │                 │                       │              │
│         ▼                 ▼                       ▼              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Event Bus                              │   │
│  │  (In-process synchronous pub/sub)                        │   │
│  └──────────────────────────────────────────────────────────┘   │
│         │                 │                       │              │
│         ▼                 ▼                       ▼              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ Budget       │  │ Goal         │  │ Investment              │ │
│  │ Tracking     │  │ Tracking     │  │ Tracking                │ │
│  │              │  │              │  │                         │ │
│  │ • Actual vs  │  │ • Progress   │  │ • Holdings              │ │
│  │   Budgeted   │  │ • Projections│  │ • Cost basis            │ │
│  │ • Alerts     │  │ • Milestones │  │ • Returns (XIRR)        │ │
│  │ • Rollover   │  │              │  │ • Asset allocation      │ │
│  └──────────────┘  └──────────────┘  └─────────────────────────┘ │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ Recurring    │  │ Tax          │  │ Import / Export          │ │
│  │ Processing   │  │ Module       │  │                         │ │
│  │              │  │              │  │ • CSV bank statement     │ │
│  │ • Scheduling │  │ • 80C/80D    │  │ • PDF parsing (future)  │ │
│  │ • Auto-post  │  │ • HRA calc   │  │ • Data export           │ │
│  │ • Reminders  │  │ • Tax summary│  │ • Backup / Restore      │ │
│  └──────────────┘  └──────────────┘  └─────────────────────────┘ │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │               Repository Layer                            │   │
│  │  (Protocol interfaces + SQLAlchemy Core implementations) │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 6.1 Module Catalog

| Module | Package | Status | Description |
|--------|---------|--------|-------------|
| Onboarding | `pfms.onboarding` | V1 — In scope | First-run setup: profile, COA, accounts, opening balances, goals, budgets, recurring, net worth, orchestrator |
| Transactions | `pfms.transactions` | V1 — In scope | Core transaction recording engine: create, void, split, transfer, search, filter |
| Reporting | `pfms.reporting` | V1 — In scope | Financial statements and analysis: balance sheet, income/expense, cash flow, spending breakdown |
| Budget Tracking | `pfms.budget_tracking` | V1 — In scope | Ongoing budget vs actual comparison, variance analysis, period rollover |
| Goal Tracking | `pfms.goal_tracking` | V1 — In scope | Goal progress monitoring, contribution tracking, milestone management |
| Net Worth Tracking | `pfms.networth_tracking` | V1 — In scope | Periodic net worth snapshots, trend analysis |
| Recurring Processing | `pfms.recurring_processing` | V1 — In scope | Generate transactions from templates, manage schedule, reminders |
| Account Management | `pfms.account_management` | V1 — In scope | Post-onboarding account operations: close, reopen, modify details, merge |
| Investment Tracking | `pfms.investments` | V2 — Deferred | Holdings, cost basis (FIFO/average), XIRR returns, asset allocation |
| Tax Module | `pfms.tax` | V2 — Deferred | Section 80C/80D tracking, HRA exemption calculator, annual tax summary |
| Import / Export | `pfms.import_export` | V2 — Deferred | CSV import with column mapping, data export, backup/restore |

### 6.2 Module Dependency Rules

Modules are classified into three tiers based on dependency direction.

**Tier 1 — Foundation (no module dependencies):** Common utilities, Repository layer, Event Bus. These are infrastructure that every other module depends on.

**Tier 2 — Core Domain (depends only on Tier 1):** Onboarding, Transactions, Account Management. These define the fundamental data structures and operations. They emit events but do not consume events from other Tier 2 modules.

**Tier 3 — Derived Domain (depends on Tier 1, consumes events from Tier 2):** Reporting, Budget Tracking, Goal Tracking, Net Worth Tracking, Recurring Processing, Investment Tracking, Tax Module, Import/Export. These modules read data produced by Tier 2 modules and react to events. They never write to Tier 2 tables directly — they either call Tier 2 services (for commands) or query repositories (for reads).

The critical rule: **Tier 2 modules never import or depend on Tier 3 modules.** If a Tier 3 module needs to trigger a Tier 2 action (e.g., Recurring Processing needs to create a transaction), it calls the Tier 2 service through the same dependency injection mechanism — not through a direct import.

---

## 7. Technology Architecture Decisions

Each decision is recorded as a lightweight Architecture Decision Record (ADR).

### ADR-001: FastAPI as API Framework

**Context:** We need an API framework that auto-generates OpenAPI specs, supports Pydantic validation natively, and enables Swagger UI testing out of the box.

**Decision:** Use FastAPI.

**Consequences:** Tight coupling to Pydantic for DTOs (acceptable — Pydantic is also our validation layer). Async support available but not required. Excellent developer experience with auto-complete and type checking.

### ADR-002: SQLite as Default Database (Engine-Configurable)

**Context:** The system is single-user and local-first. We need zero-config persistence with ACID transactions. However, future deployments (household server, cloud-hosted version) may benefit from PostgreSQL.

**Decision:** Use SQLite as the default database engine. The engine is configurable via connection string in the application configuration. SQLAlchemy Core's `create_engine()` abstracts engine selection — switching from SQLite to PostgreSQL requires only a connection string change, not code changes. The default configuration uses a local SQLite file.

**Consequences:** No concurrent write support in the default SQLite mode (not needed for single-user). Database is a single file — easy to back up, move, or reset. No need for database server management in default mode. If PostgreSQL is configured, the system gains concurrent access and advanced features (full-text search, JSONB, window functions). The repository layer is engine-agnostic through SQLAlchemy Core, so no separate repository implementations are needed per database.

### ADR-003: Repository Pattern with Protocol-Based Interfaces

**Context:** We need to test business logic without touching the database, and we need the ability to swap storage implementations.

**Decision:** Define all data access contracts as Python `Protocol` classes. Provide two implementations: in-memory stubs (for unit tests) and SQLAlchemy Core implementations (for integration tests and production). The SQLAlchemy Core implementation works with any engine that SQLAlchemy supports — the same repository code runs against SQLite and PostgreSQL.

**Consequences:** Every repository must have two implementations kept in sync (in-memory and SQLAlchemy Core). The in-memory implementation serves as executable documentation of the expected behavior. Database portability is handled by SQLAlchemy Core — no separate repository implementations are needed per database engine.

### ADR-004: Pydantic v2 for All Data Transfer Objects

**Context:** We need input validation, serialization, and OpenAPI schema generation from a single source of truth.

**Decision:** All request and response models are Pydantic `BaseModel` subclasses. Internal DTOs between service and repository layers are either Pydantic models or Python `dataclass`es (for simplicity where validation is not needed).

**Consequences:** Pydantic becomes a core dependency. Validation logic is declarative and testable. Field-level constraints are defined once and enforced at the API boundary.

### ADR-005: Synchronous In-Process Event Bus

**Context:** Modules need to react to events from other modules (e.g., when a transaction is posted, budget tracking needs to update). We don't need distributed messaging for a single-user desktop app.

**Decision:** Implement a simple publish-subscribe event bus that runs synchronously in the same process. Events are plain dictionaries with a type string.

**Consequences:** Event handlers run in the same thread and transaction context as the publisher. If a handler fails, the publishing operation can catch and handle the error. No message persistence, no retry logic. This is deliberately simple — if the system evolves to need async processing, the event bus interface can be swapped without changing publishers or subscribers.

### ADR-006: SQLAlchemy Core for Data Access (No ORM Session/Model Layer)

**Context:** Raw SQL via `sqlite3` provides full visibility but locks the system to SQLite's dialect. A full ORM (SQLAlchemy ORM with sessions, mapped classes, lazy loading) hides query behavior — exactly what a ledger system needs to see. The middle path is SQLAlchemy Core: a SQL expression builder that generates database-agnostic SQL while keeping queries explicit and composable.

**Decision:** Use SQLAlchemy Core's expression language inside repository implementations. Define tables as `Table` objects with `MetaData`. Write queries using `select()`, `insert()`, `update()`, `delete()` with explicit `where()` clauses. Do not use the ORM session layer, mapped model classes, or relationship loading. Use Alembic for schema migrations.

**Consequences:** SQLAlchemy becomes a core dependency (pure Python, no system libraries). Queries are slightly more verbose than raw SQL strings but are type-checked, composable, and database-portable. Generated SQL can be inspected via `echo=True` engine mode. Alembic auto-generates migration scripts by diffing table definitions against the database — eliminating manual versioned SQL scripts. Table definitions in Python serve as a single source of truth for the schema. The Repository Pattern is preserved — SQLAlchemy Core usage is entirely encapsulated within repository implementations.

**Supersedes:** Original ADR-006 ("Explicit SQL, No ORM") established in the initial architecture baseline.

### ADR-007: API Versioning via URL Path

**Context:** We need to evolve APIs without breaking existing clients.

**Decision:** All API routes are prefixed with `/api/v1/`. Breaking changes require a new version prefix (`/api/v2/`). Non-breaking additions (new optional fields, new endpoints) are added to the current version.

**Consequences:** Multiple API versions may coexist temporarily. The router structure supports this naturally — each version is a separate router module.

---

## 8. Data Architecture

### 8.1 Conceptual Data Model

The system's data is organized around six core entity groups.

```
┌─────────────────────────────────────────────────────────────────┐
│                      PFMS Conceptual Data Model                  │
│                                                                  │
│  CONFIGURATION         STRUCTURE            OPERATIONS           │
│  ┌──────────┐         ┌──────────┐         ┌──────────────────┐ │
│  │ Settings  │         │ Accounts │◄────────│ Transactions     │ │
│  │ (Profile, │         │ (COA     │         │ (Double-entry    │ │
│  │  prefs)   │         │  tree)   │         │  journal entries)│ │
│  └──────────┘         └─────┬────┘         └────────┬─────────┘ │
│                             │                       │            │
│                       ┌─────┴─────┐           ┌─────┴─────┐     │
│                       │Institution│           │ Txn Lines  │     │
│                       │ (Banks,   │           │ (Debits &  │     │
│                       │  brokers) │           │  Credits)  │     │
│                       └───────────┘           └───────────┘     │
│                                                                  │
│  PLANNING              TRACKING              ANALYSIS           │
│  ┌──────────┐         ┌──────────────┐      ┌───────────────┐  │
│  │ Goals     │         │ Budget Lines  │      │ Net Worth     │  │
│  │ (Targets, │         │ (Category     │      │ Snapshots     │  │
│  │  dates)   │         │  allocations) │      │ (Periodic)    │  │
│  └──────┬───┘         └──────────────┘      └───────────────┘  │
│         │                                                        │
│  ┌──────┴────┐        ┌──────────────┐                          │
│  │ Milestones │        │ Recurring    │                          │
│  │ (Sub-goals)│        │ Templates    │                          │
│  └───────────┘        │ (SIP, EMI,   │                          │
│                       │  rent, etc.) │                          │
│                       └──────────────┘                          │
└─────────────────────────────────────────────────────────────────┘
```

### 8.2 Entity Relationships (Logical)

**Account** is the central entity. It belongs to the COA tree (has a parent account), may be linked to an Institution, and has type-specific detail records. Transactions reference accounts through transaction lines.

**Transaction** is immutable once posted. It is never edited — only voided and replaced. Every transaction has two or more transaction lines. The sum of all debit amounts must equal the sum of all credit amounts within a transaction (the fundamental double-entry invariant).

**Goal** is linked to one or more accounts (the accounts whose balances contribute toward the goal). It has milestones as sub-targets.

**Budget** is linked to a time period and contains line items. Each line item references an expense or income account from the COA and specifies a budgeted amount.

**Recurring Template** describes a future repeating transaction pattern. It references a source account (from) and destination account (to), along with scheduling information. It is not a transaction itself — it is a blueprint used to generate transactions.

**Net Worth Snapshot** is a point-in-time capture of all account balances, grouped and summed. It is a denormalized snapshot for historical tracking — not a live view.

### 8.3 Data Integrity Rules

**DI-1: Referential Integrity.** Foreign keys are enforced at the database level. For SQLite, `PRAGMA foreign_keys = ON` is set on every connection (handled automatically by SQLAlchemy's event system). For PostgreSQL, foreign keys are enforced natively. Every transaction line references a valid account. Every account detail record references a valid account. Every goal-account mapping references valid goal and account IDs.

**DI-2: Double-Entry Balance.** Enforced at the service layer before any transaction is persisted: `SUM(debit_amounts) == SUM(credit_amounts)`. A database-level trigger serves as a safety net.

**DI-3: Account Code Uniqueness.** Every account in the COA has a unique code. Enforced by a UNIQUE constraint on the code column.

**DI-4: No Orphan Transaction Lines.** Transaction lines cannot exist without a parent transaction. Enforced by foreign key with CASCADE on delete (though transactions are never deleted — only voided).

**DI-5: Immutable Posted Transactions.** Once a transaction has status POSTED, its lines cannot be modified. The application layer enforces this — there is no UPDATE endpoint for transaction lines. Corrections are made by voiding the original and creating a new transaction.

**DI-6: System Account Protection.** Accounts flagged as `is_system = 1` cannot be renamed, deactivated, or deleted through any API. Enforced at the service layer.

### 8.4 Storage Sizing

For a personal finance system with moderate usage (approximately 50 accounts, 30 transactions per day, 10 years of data), the estimated database size is under 100 MB. SQLite handles databases up to 281 TB, so storage is not a concern. If PostgreSQL is used, storage is effectively unlimited for personal finance workloads.

---

## 9. Cross-Cutting Concerns

### 9.1 Logging

Every service method logs entry and exit at DEBUG level, and logs business-significant events (account created, transaction posted, onboarding step completed) at INFO level. Errors are logged at ERROR level with full context. Python's standard `logging` module is used with structured log formatting. No third-party logging frameworks.

### 9.2 Configuration

Application configuration is managed through a `config.py` module that reads from environment variables with sensible defaults. Configuration values include database connection string (defaulting to a local SQLite file path), log level, API host and port, and feature flags. Configuration is loaded once at startup and passed through dependency injection — services never read environment variables directly.

### 9.3 Error Handling Strategy

Errors are classified into three categories.

**Validation Errors** (bad input from the user): Caught at the Pydantic layer or service layer. Returned as HTTP 422 with field-level details. These are expected and handled gracefully.

**Business Rule Violations** (input is valid but violates domain rules): Caught at the service layer. Returned as HTTP 400 or 409 with a descriptive message and error code. Examples: attempting to post to a placeholder account, setting a negative opening balance, skipping a mandatory onboarding step.

**System Errors** (unexpected failures): Database connection issues, file system errors, bugs. Caught by a global exception handler. Returned as HTTP 500 with a generic message. Full details are logged but not exposed to the client.

### 9.4 Data Backup and Recovery

The backup strategy depends on the configured database engine. For SQLite (the default), the entire database is a single file — backup is a file copy operation using SQLite's online backup API. For PostgreSQL, backup uses `pg_dump` or equivalent tooling. The system provides an API endpoint and CLI command for creating a backup and restoring from one. Backups are timestamped and stored in a configurable directory.

### 9.5 Money Representation

All monetary values are stored as real numbers and represented as floats in Python. For V1, this is acceptable for personal finance amounts (we are not handling fractions of paisa in high-frequency trading). Amounts are rounded to 2 decimal places at the point of storage. Display formatting (₹, Indian numbering) is handled at the presentation layer, never at the storage layer.

A future enhancement may introduce `decimal.Decimal` throughout the stack if precision issues arise, but the repository interface would not change — only the internal representation.

---

## 10. Quality Attributes

| Attribute | Target | How Achieved |
|-----------|--------|-------------|
| Correctness | Books always balance; no data corruption | Double-entry invariant enforced at service layer and verified by database trigger; immutable transactions |
| Testability | 90%+ line coverage; every service testable in isolation | Repository abstraction with in-memory stubs; dependency injection; TDD workflow |
| Performance | Any API call returns in < 200ms for 10 years of data | SQLite with proper indexes; queries scoped to date ranges; net worth computation is snapshot-based, not real-time scan |
| Usability | A new developer can run the full test suite within 5 minutes of cloning | Zero external dependencies beyond Python and pip; `make setup && make test` works from clean checkout |
| Maintainability | Adding a new account type requires changes in ≤ 3 files | Account type metadata is data-driven (enums + detail tables); COA tree is configurable; service logic is type-parameterized |
| Recoverability | User can restore to any previous backup within 2 minutes | Single-file database; backup is file copy; restore is file replace + restart |

---

## 11. Deployment Architecture

```
User's Machine
├── pfms/                     (installed Python package)
│   ├── API Server            (runs on localhost:8000)
│   └── Core Engine           (imported by server)
├── pfms-cli                  (installed CLI tool)
├── ~/.pfms/
│   ├── pfms.db              (SQLite database)
│   ├── pfms.log             (application log)
│   ├── config.toml          (optional user overrides)
│   └── backups/
│       ├── pfms_20260314_120000.db
│       └── pfms_20260301_090000.db
└── Browser → http://localhost:8000/docs    (Swagger UI)
```

The system is distributed as a Python package installable via pip. The user starts the server with `pfms serve` and interacts via Swagger UI or the CLI. No Docker, no cloud, no external services.

---

## 12. Phased Delivery Roadmap

| Phase | Scope | Modules | Target |
|-------|-------|---------|--------|
| V1.0 | Core Ledger | Onboarding, Transactions, Reporting, Account Management | Month 1-2 |
| V1.1 | Active Tracking | Budget Tracking, Goal Tracking, Recurring Processing, Net Worth Tracking | Month 2-3 |
| V2.0 | Financial Intelligence | Investment Tracking, Tax Module, Import/Export | Month 4-6 |

---

# Document 2: Design Document

**System:** PFMS — Personal Finance Management System (Ledger)
**Version:** 1.0
**Date:** March 14, 2026

---

## 1. Design Philosophy

Three sentences that guide every design decision in this system.

**"It's a ledger, not an app."** The system's core value is accurate record-keeping. Every design choice that trades correctness for convenience is wrong. If the UI is ugly but the books balance, the system is working. If the UI is beautiful but the books are wrong, the system is broken.

**"The API is the product."** The REST API is not a backend for a frontend — it is the product itself. Every interaction a user can have with the system is expressible as an API call. Interfaces (CLI, web, mobile) are thin rendering layers that translate API responses into human-friendly formats.

**"Test the behavior, not the implementation."** Tests verify what the system does (given these inputs, I expect these outputs and these side effects), not how it does it (which method was called, which SQL was executed). This keeps tests stable as implementations evolve.

---

## 2. Layered Architecture Design

### 2.1 Layer Responsibilities

**Router Layer (API Controllers):** Receives HTTP requests. Deserializes request bodies into Pydantic DTOs. Calls the appropriate service method. Serializes the service result into an HTTP response. Maps service errors to HTTP status codes. Contains no business logic — not even a single `if` statement about domain rules.

**Service Layer (Business Logic):** Receives validated DTOs from the router. Applies business rules and domain logic. Orchestrates calls to one or more repositories. Emits events for cross-module communication. Returns result objects (Success or Failure) — never raises exceptions for expected business conditions. This is the most important layer. All complexity lives here.

**Repository Layer (Data Access):** Receives simple data transfer objects and persists or retrieves them. Contains no business logic. Does not validate inputs (the service layer already did). Does not transform data shapes (DTOs in, DTOs out). Each method corresponds to a single database operation or a small, well-defined set of operations.

**Common Layer (Shared Utilities):** Enumerations, type aliases, exception definitions, event bus, validators, and utility functions used across modules. This layer has no dependencies on any module — modules depend on it.

### 2.2 Dependency Flow

Dependencies flow strictly downward: Router → Service → Repository → Database. Additionally, all layers depend on Common.

No layer may call upward. No module's service may import another module's service directly. Cross-module interaction happens exclusively through events (fire-and-forget notifications) or through shared repository interfaces (when a Tier 3 module needs to read data produced by a Tier 2 module).

### 2.3 Dependency Injection Design

The system uses FastAPI's built-in `Depends()` mechanism for wiring. A central `dependencies.py` module defines provider functions for every repository and service. This is the single place where concrete implementations are chosen.

For production: providers return SQLAlchemy Core repository implementations (which work with whatever engine is configured — SQLite or PostgreSQL).
For testing: providers are overridden to return in-memory stubs.

The provider functions form a dependency graph that FastAPI resolves automatically. Services declare their dependencies as constructor parameters — they never create their own dependencies.

---

## 3. API Design Standards

### 3.1 URL Structure

All URLs follow the pattern: `/api/v{version}/{module}/{resource}`. Resources are plural nouns. Actions that don't map to CRUD are expressed as sub-resources (e.g., `/accounts/{id}/close` rather than `/close-account/{id}`).

### 3.2 HTTP Method Semantics

POST creates a new resource or triggers an action. Returns 201 with the created resource in the body and a `Location` header.

GET retrieves a resource or collection. Never modifies state. Returns 200.

PUT replaces a resource entirely. The request body contains the complete new representation. Returns 200.

PATCH partially updates a resource. The request body contains only the fields to change. Returns 200.

DELETE removes or deactivates a resource. Returns 204 with no body.

### 3.3 Response Envelope

All successful responses return the resource directly (no wrapper). Error responses use a consistent envelope.

Success: the response body is the resource JSON itself (or an array of resources for collections).

Error: the response body follows this structure —

```
{
  "error_code": "VALIDATION_ERROR",
  "message": "Display name cannot be empty",
  "details": {                        // optional
    "field": "display_name",
    "constraint": "min_length=1"
  }
}
```

### 3.4 Pagination

Collection endpoints that may return large result sets support cursor-based pagination with `limit` and `offset` query parameters. Default limit is 50, maximum is 200. The response includes a `total_count` field in a pagination wrapper.

### 3.5 Filtering and Sorting

Collection endpoints support filtering via query parameters named after the fields being filtered (e.g., `?account_type=ASSET&is_active=true`). Sorting is specified via `sort_by` and `sort_order` query parameters (e.g., `?sort_by=created_at&sort_order=desc`).

### 3.6 Date and Time Formats

All dates in API requests and responses use ISO 8601 format. Dates without time use `YYYY-MM-DD`. Timestamps use `YYYY-MM-DDTHH:MM:SS` in UTC. The system stores all timestamps in UTC internally and converts to the user's display format only at the presentation layer.

### 3.7 OpenAPI Documentation Standards

Every endpoint must have a summary (short, appears in Swagger sidebar), a description (detailed, appears in expanded view), documented request body with field descriptions, documented response schemas for all status codes (200/201, 400, 404, 409, 422), and at least one example request/response pair embedded in the schema.

---

## 4. Double-Entry Engine Design

This is the most critical subsystem in PFMS. Everything else is built on top of it.

### 4.1 Fundamental Invariant

For every transaction in the system:

$$
\sum \text{Debit Amounts} = \sum \text{Credit Amounts}
$$

This is enforced at three levels. The service layer checks this before calling the repository. The repository layer verifies it after constructing the SQL (belt-and-suspenders). A SQLite trigger rejects any insert into `transaction_lines` that would leave its parent transaction unbalanced. If all three levels fail and an unbalanced transaction reaches the database, the system is considered to be in a corrupt state and must refuse further operations until the inconsistency is resolved.

### 4.2 Account Balance Derivation

Account balances are **never stored** — they are always computed by summing transaction lines. The balance of an account as of a given date is:

For accounts with normal balance = DEBIT (assets, expenses):

$$
\text{Balance} = \sum \text{Debits} - \sum \text{Credits}
$$

For accounts with normal balance = CREDIT (liabilities, income, equity):

$$
\text{Balance} = \sum \text{Credits} - \sum \text{Debits}
$$

Only POSTED transactions are included. VOIDED transactions are excluded from all balance calculations.

This derived approach means there is no "balance" column to get out of sync. The trade-off is that balance computation requires scanning transaction lines. For performance, the system can maintain a materialized balance cache that is rebuilt on demand — but this is an optimization, not a source of truth.

### 4.3 Transaction Types

The system recognizes the following transaction types, each with specific validation rules.

**OPENING_BALANCE:** Created during onboarding. Always involves exactly two lines: the target account and the Opening Balances Equity account. Only one active (non-voided) opening balance transaction may exist per account.

**STANDARD:** A regular income or expense transaction. Minimum two lines. Common pattern: one expense/income account and one asset/liability account. Split transactions (one debit, multiple credits or vice versa) are supported.

**TRANSFER:** Movement of money between the user's own accounts (e.g., bank to FD, savings to credit card payment). Always involves exactly two asset and/or liability accounts. Does not affect income or expense. Net effect on net worth is zero.

**ADJUSTMENT:** Manual correction entries. Same rules as STANDARD but tagged for audit trail purposes.

### 4.4 Transaction Lifecycle

```
                    ┌──────────┐
                    │  DRAFT   │  (Future: for multi-step entry)
                    └────┬─────┘
                         │ post()
                         ▼
                    ┌──────────┐
                    │  POSTED  │  ← Normal state. Included in all reports.
                    └────┬─────┘
                         │ void()
                         ▼
                    ┌──────────┐
                    │  VOIDED  │  ← Excluded from all calculations.
                    └──────────┘     Original data preserved for audit trail.
```

In V1, transactions go directly from creation to POSTED. The DRAFT state is reserved for a future multi-step entry workflow.

### 4.5 Void and Correct Pattern

Transactions are never edited. To correct a mistake, the user voids the original transaction and creates a new one. The voided transaction remains in the database with `status = VOIDED` and is excluded from all balance computations and reports. The new transaction has a `reference` field pointing to the voided transaction's ID for audit trail.

---

## 5. Chart of Accounts Design

### 5.1 Tree Structure

The COA is a single-rooted forest (five root nodes, one for each account type: Asset, Liability, Income, Expense, Equity). Each node has a numeric code, a name, a type inherited from its root ancestor, a normal balance determined by its type, a flag indicating whether it is a placeholder (branch) or a leaf, and a flag indicating whether it is system-managed.

The numeric code serves as both an identifier and an ordering mechanism. Codes are assigned hierarchically: root nodes get 1000, 2000, 3000, 4000, 6000. First-level children get x100 increments. Second-level children get x10 or x1 increments. This scheme supports up to 9 root categories, 9 subcategories per root, and 10–99 leaf accounts per subcategory — more than sufficient for personal finance.

### 5.2 Placeholder vs Leaf

Placeholder accounts are organizational containers. They cannot have transactions posted to them. Their balance is the sum of their children's balances. They exist to give the COA tree its hierarchical structure.

Leaf accounts are where transactions are actually recorded. Every transaction line must reference a leaf account. When the user creates a new account (e.g., a new bank account), a new leaf node is added under the appropriate placeholder in the COA tree.

### 5.3 System Accounts

Certain accounts are created and managed by the system itself. They cannot be modified or deleted by the user. Currently, the system accounts are Opening Balances Equity (used as the counterpart for all opening balance entries) and Retained Earnings (used for year-end closing entries, where net income for the year is transferred into equity).

---

## 6. Module Interaction Design

### 6.1 Event Catalog

| Event | Published By | Consumed By | Payload |
|-------|-------------|-------------|---------|
| `profile.created` | Onboarding: Profile | Orchestrator | profile settings |
| `coa.initialized` | Onboarding: COA | Orchestrator | root account count |
| `account.created` | Onboarding: Account | Orchestrator, Net Worth | account ID, type, subtype |
| `account.closed` | Account Management | Net Worth, Goal Tracking | account ID |
| `opening_balance.set` | Onboarding: OB | Orchestrator, Net Worth | account ID, amount |
| `transaction.posted` | Transactions | Budget Tracking, Goal Tracking, Net Worth | transaction ID, lines summary |
| `transaction.voided` | Transactions | Budget Tracking, Goal Tracking, Net Worth | transaction ID |
| `goal.created` | Onboarding: Goal | Orchestrator | goal ID, type |
| `goal.achieved` | Goal Tracking | (notification/logging) | goal ID, name |
| `budget.created` | Onboarding: Budget | Orchestrator | budget ID |
| `budget.exceeded` | Budget Tracking | (notification/logging) | budget ID, category, amount |
| `recurring.due` | Recurring Processing | (notification/logging) | template ID, amount, date |
| `recurring.posted` | Recurring Processing | Budget Tracking | transaction ID |
| `onboarding.completed` | Orchestrator | (system-wide flag) | completion timestamp |

### 6.2 Key Interaction Flows

**Flow 1: Recording a Daily Expense**

```
User → POST /api/v1/transactions
         │
         ▼
    Transaction Router
         │ deserialize & validate DTO
         ▼
    Transaction Service
         │ 1. Validate all account IDs exist and are leaf accounts
         │ 2. Validate debit sum == credit sum
         │ 3. Determine transaction type
         │ 4. Call TransactionRepository.create()
         │ 5. Emit "transaction.posted" event
         │
         ├──► Budget Tracking (event handler)
         │    └─ Update actual spend for the expense category
         │
         ├──► Goal Tracking (event handler)
         │    └─ If transaction involves a goal-linked account, recalc progress
         │
         └──► Net Worth (event handler)
              └─ Invalidate cached net worth (force recompute on next request)
```

**Flow 2: Monthly Recurring Processing**

```
User → POST /api/v1/recurring/process (or automatic on app start)
         │
         ▼
    Recurring Processing Service
         │ 1. Query all active templates where next_occurrence_date <= today
         │ 2. For each due template:
         │    a. Build transaction DTO from template
         │    b. Call Transaction Service.create()  ← Tier 2 service call
         │    c. Update next_occurrence_date on template
         │    d. Emit "recurring.posted" event
         │
         └──► Transaction Service handles the rest
              (validation, persistence, event emission)
```

**Flow 3: Generating a Balance Sheet Report**

```
User → GET /api/v1/reports/balance-sheet?as_of=2026-03-31
         │
         ▼
    Reporting Router
         │
         ▼
    Reporting Service
         │ 1. Get all active accounts of type ASSET, LIABILITY, EQUITY
         │ 2. For each leaf account, compute balance as of the given date
         │    (via AccountRepository.get_balance)
         │ 3. Aggregate balances up the COA tree hierarchy
         │ 4. Verify: Total Assets == Total Liabilities + Total Equity
         │    (the accounting equation)
         │ 5. Format into report structure
         │
         └──► Return BalanceSheetResponse
```

---

## 7. Transaction Service Design — Detail

Since the Transaction module is the heart of the system, its design merits additional detail.

### 7.1 Service Interface

The Transaction Service exposes the following operations.

**create(dto) → TransactionResponse:** Validate, persist, and post a new transaction. This is the most-called method in the system.

**void(transaction_id, reason) → TransactionResponse:** Mark a posted transaction as voided. Returns the voided transaction. Does not delete any data.

**get(transaction_id) → TransactionResponse:** Retrieve a transaction with all its lines.

**search(filters) → PaginatedResult[TransactionSummary]:** Search transactions by date range, account, type, amount range, description keyword. Returns paginated summaries (without full line details).

**get_account_ledger(account_id, date_from, date_to) → list[LedgerEntry]:** Get all transaction lines for a specific account in a date range. This is the foundation for account-level reporting. Each ledger entry includes the running balance.

### 7.2 Split Transaction Handling

A split transaction has more than two lines. Common examples: a salary credit that is split into basic, HRA, and special allowance components; a grocery purchase split across multiple expense categories.

The service validates that split transactions still satisfy the double-entry invariant. There is no limit on the number of lines, but each line must reference a leaf account and have either a debit or credit amount (not both, and not zero).

### 7.3 Transfer Detection

When a transaction involves only asset and liability accounts (no income or expense accounts), the service classifies it as a TRANSFER. Transfers are excluded from income/expense reports but included in cash flow reports. The service auto-detects this — the user does not need to explicitly tag a transaction as a transfer.

---

## 8. Reporting Module Design

### 8.1 Report Types

**Balance Sheet (Statement of Financial Position):** Shows total assets, total liabilities, and equity (net worth) as of a specific date. Assets and liabilities are broken down by COA subcategory. The accounting equation (Assets = Liabilities + Equity) must hold.

**Income and Expense Statement (Profit and Loss equivalent for personal finance):** Shows total income and total expenses over a date range. Broken down by COA subcategory. The difference (income minus expenses) is the net savings for the period.

**Cash Flow Statement:** Shows cash inflows and outflows by category over a date range. Includes transfers between accounts (which the income/expense statement excludes). Useful for understanding where money is actually going.

**Spending Analysis:** A more granular, user-friendly view of expenses. Supports grouping by top-level category, subcategory, or individual account. Supports comparison across periods (this month vs last month, this year vs last year).

**Account Ledger:** A chronological list of all transactions affecting a specific account over a date range. Shows running balance. This is the most basic report and is used for reconciliation.

### 8.2 Report Date Range Handling

All reports that operate on a date range respect the Financial Year configuration from the user's profile. When a user requests "this FY" and their FY starts in April, the system computes the date range as April 1 of the current FY to today (or March 31 if the FY is complete). Pre-built ranges include: this month, last month, this quarter, last quarter, this FY, last FY, calendar year, and custom range.

### 8.3 Report Computation Strategy

Reports are computed on-demand, not pre-materialized. The Reporting Service queries the transaction lines through the repository, applies date filters, groups by account, and aggregates. For the Balance Sheet, it computes balances for all accounts as of the target date. For the Income/Expense Statement, it sums debits and credits for income and expense accounts within the date range.

The performance target is < 200ms for any report query over 10 years of data. This is achievable with proper indexes on `transaction_date` and `account_id` in the `transaction_lines` table.

---

## 9. Recurring Processing Design

### 9.1 Processing Model

Recurring templates are processed in two modes.

**On-Demand Processing:** The user (or CLI) explicitly triggers processing via `POST /api/v1/recurring/process`. The service scans for all active templates where `next_occurrence_date <= today` and creates transactions for each.

**Startup Processing:** When the API server starts, it optionally runs a check for overdue recurring templates and processes them. This handles the case where the user hasn't opened the application for several days — all overdue recurring transactions are generated on startup.

### 9.2 Catch-Up Logic

If a monthly SIP with `day_of_occurrence = 10` has `next_occurrence_date = 2026-01-10` and the user opens the application on March 14, the system generates three transactions: January 10, February 10, and March 10. Each generation advances `next_occurrence_date` by one frequency interval. The system processes one occurrence at a time in chronological order.

### 9.3 End Date Handling

If a template has an `end_date` and the `next_occurrence_date` exceeds it, the template is marked inactive (`is_active = false`) and no further transactions are generated.

---

## 10. Indian Financial Context — Design Considerations

### 10.1 Financial Year

The system's concept of "current FY" is derived from the profile setting `financial_year_start_month` and today's date. All FY-aware operations (tax summaries, annual reports, budget periods) use this derived FY range. The formula: if today's month >= FY start month, FY start is this calendar year; otherwise, FY start is last calendar year.

### 10.2 Indian Numbering Format

When `number_format = INDIAN`, amounts are formatted with the Indian grouping system: the last three digits are grouped, then every two digits. The formatter handles this at the presentation layer (CLI output, API responses that include formatted strings). Raw numeric values in JSON responses are always standard numbers — the formatting is applied only in display contexts.

### 10.3 Instrument-Specific Rules

**PPF:** Maximum annual contribution of ₹1,50,000 (as of current rules). Lock-in period of 15 years with partial withdrawal rules. The system tracks contributions per FY and warns if the limit is approached. Interest rate is government-declared and changes quarterly.

**EPF:** Employer and employee contribution tracking. The COA has an EPF account under retirement assets. Contributions are typically salary-proportional and recorded through payroll templates.

**NPS:** Tier 1 and Tier 2 sub-accounts. Tax deduction under Section 80CCD. The system tracks contributions separately from market-linked growth.

**Fixed Deposits:** Maturity tracking with alert when an FD is nearing maturity. Interest accrual can be modeled as periodic income entries (for cumulative FDs, this is a book entry; for non-cumulative FDs, it corresponds to actual interest credits).

These rules are enforced and surfaced at the service layer — they are not baked into the data model. The data model stores the raw facts; the service interprets them in the Indian financial context.

### 10.4 Tax-Relevant Tagging

Certain accounts and transactions are relevant for income tax computation. Rather than building a full tax engine in V1, the system supports tagging accounts with tax-relevant metadata: Section 80C eligible (PPF, ELSS, life insurance premiums, principal portion of home loan EMI), Section 80D eligible (health insurance premiums), HRA relevant (rent payments, HRA received), and capital gains relevant (equity, mutual fund, property transactions).

This tagging is metadata — it does not affect transaction recording or reporting. The Tax Module in V2 reads these tags to generate tax summaries.

---

## 11. Extension Points

The architecture has deliberate seams where future capabilities can be added without modifying existing code.

**New Account Types:** Add a new entry to `AccountSubType` enum, a new detail table, a new endpoint in the Account router, and a new handler in the account type registry. Existing account types are unaffected.

**New Report Types:** Add a new service method in the Reporting module and a new router endpoint. Reports are purely read operations — they never modify data.

**New Recurring Types:** Add a new entry to `RecurringType` enum. The recurring processing engine treats all templates identically — the type is metadata for display, not for processing logic.

**Import Adapters:** Each bank or data source gets its own adapter that parses the source format and produces standard transaction DTOs. The Import Service calls the Transaction Service to persist them. Adding a new bank adapter does not modify the import framework or the transaction engine.

**New Event Subscribers:** Any new module can subscribe to existing events without modifying the publishing module. The event bus uses a registration pattern — publishers don't know who is listening.

**Alternative Database Engines:** Change the database connection string in configuration to point to PostgreSQL (or any other SQLAlchemy-supported engine). The same SQLAlchemy Core repository code runs against any supported database. No new repository implementations needed — this is a configuration change, not a code change.

---

## 12. Development Workflow Standards

### 12.1 Spec-Driven Development Sequence

For every feature, the development follows this sequence.

**Step 1 — Specification:** Define the API endpoint (URL, method, request schema, response schema, error cases) in the ERS. Review with stakeholders.

**Step 2 — Contract Test:** Write an integration test that calls the endpoint and asserts on the response shape, status codes, and error behavior. This test fails because the endpoint doesn't exist yet.

**Step 3 — Unit Tests:** Write unit tests for the service method that the endpoint will call. Test happy path, validation failures, and business rule violations. These tests fail because the service doesn't exist yet.

**Step 4 — Service Implementation:** Implement the service method, making all unit tests pass. Use in-memory repository stubs.

**Step 5 — Repository Implementation:** Implement the SQLAlchemy Core repository methods needed by the service. Write repository-level tests if the queries are complex.

**Step 6 — Router Implementation:** Wire the FastAPI endpoint to call the service via dependency injection. The integration test from Step 2 should now pass.

**Step 7 — CLI Command:** Add a CLI command that calls the API endpoint and formats the response. Manual verification.

**Step 8 — Swagger Verification:** Open Swagger UI, execute the endpoint manually, verify the request/response matches the specification.

### 12.2 Branch and Commit Strategy

One branch per sub-module (e.g., `feature/onboarding-profile`, `feature/onboarding-coa`). Commits reference task IDs from the ERS (e.g., `ON-PROF-1: Add profile DTOs and validation`). A sub-module branch is merged only when all quality gates pass (tests green, linting clean, type checking clean, Swagger verified).

### 12.3 Documentation as Code

API documentation lives in the OpenAPI spec generated by FastAPI — not in a separate document that can get out of sync. Architecture and design decisions live in the Architecture and Design documents (these documents). Module-specific behavior and rules live in the ERS. Code comments explain *why*, not *what*.

---

This pair of documents — Architecture and Design — together with the ERS for each module, form the complete specification stack. The Architecture Document answers "what are the pieces and why are they structured this way." The Design Document answers "how do the pieces interact and what patterns do they follow." The ERS answers "what exactly does each piece do, input by input, output by output."

Shall I proceed with the ERS for the Transaction Management module next, or would you like to refine either of these documents first?