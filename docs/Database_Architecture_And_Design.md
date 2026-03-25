# Ledger — Database Architecture & Design Document

## 1. Introduction & Product Vision

Ledger is a personal wealth management tool designed for the Indian market. It bridges the gap between the rigor of professional double-entry accounting and the accessibility of AI-driven conversational interfaces. The target audience includes salaried professionals, small business owners, and early investors who need a consolidated, accurate, and easy-to-understand view of their financial health, including net worth, capital gains, tax optimization, and goal planning.

This document outlines the **Database Architecture and Schema Design** necessary to support Ledger's core product requirements (PRD). It addresses the complex data modeling needed for accurate financial reporting, tax compliance (including FIFO lot tracking for capital gains), and high-performance ingestion of bank statements, mutual fund CAS, and broker reports.

---

## 2. Architectural Principles & Key Decisions

To ensure the integrity, scalability, and security of financial data, the database architecture is built upon several foundational decisions:

### 2.1 Technology Stack
*   **Primary Database:** PostgreSQL 16+ is chosen due to its strict ACID compliance, robust support for JSONB (for flexible metadata), full-text search capabilities, and native Row-Level Security (RLS).
*   **Time-Series Extension:** The TimescaleDB extension is recommended for managing high-volume, time-series market pricing data (daily mutual fund NAVs, stock prices, gold prices).
*   **Object Storage (Blob):** AWS S3 or GCP Cloud Storage is used for storing uploaded documents (PDFs, CSVs). The database only stores metadata and secure references to these objects.

> **Reconciliation with V1 Local-First Architecture**
>
> This document describes the **future cloud/multi-user architecture vision** for Ledger. The **V1 local-first architecture** (documented in `architecture-design.md`) uses a different default stack:
>
> | Concern | V1 (Local-First) | Future (Cloud/Multi-User) |
> |---------|-------------------|---------------------------|
> | Database Engine | SQLite (default), PostgreSQL (configurable) | PostgreSQL 16+ |
> | Data Access Layer | SQLAlchemy Core (expression builder, no ORM) | SQLAlchemy Core (same) |
> | Schema Migrations | Alembic | Alembic |
> | Multi-Tenancy | Single-user, no RLS | Row-Level Security (RLS) |
> | Object Storage | Local filesystem | AWS S3 / GCP Cloud Storage |
> | Time-Series Data | Standard tables | TimescaleDB extension |
>
> Both architectures share the same **SQLAlchemy Core data access layer** and **Alembic migration tooling**. This means the V1 codebase can migrate to the cloud architecture by changing the database connection string and adding RLS policies — the repository code remains identical. The schema designs in this document are forward-compatible with V1's table definitions.

### 2.2 Core Design Philosophies
1.  **Immutable Append-Only Ledger:** Journal entries are never updated in place. Edits or corrections are executed using a reversal entry (negating the original) followed by a new correcting entry, maintaining a strict audit trail.
2.  **Separate Debit/Credit Columns:** To prevent sign-confusion bugs, journal entry lines feature explicit `debit_amount` and `credit_amount` columns. Integrity is guaranteed via deferred database triggers checking that `SUM(debits) = SUM(credits)` before committing any transaction.
3.  **Hybrid Balance Computation:** To balance real-time accuracy and performance queries, account balances are computed on-the-fly from the most recent checkpoint. These periodic materialized checkpoints (`account_balance_checkpoints`) allow O(1) lookups for historical data without continually summing millions of rows.
4.  **Soft Deletes Everywhere:** Financial entities use `deleted_at` timestamps. Hard deletes are reserved exclusively for full user account deletion to comply with GDPR/data privacy regulations.
5.  **Multi-Tenancy via Row-Level Security (RLS):** Every table carries a `user_id` foreign key. PostgreSQL RLS policies enforce that a session can only view rows matching its authenticated `user_id`, providing defense-in-depth against application-level data leaks.

---

## 3. Entity Relationship Overview

The core data domains are interconnected to provide a complete view of a user's financial life.

```text
┌──────────┐       ┌──────────────────┐       ┌─────────────────────┐
│  users   │──1:N──│    accounts      │──1:N──│ account_balance_    │
└──────────┘       │  (Chart of Accts)│       │ checkpoints         │
                   │  self-ref:       │       └─────────────────────┘
                   │  parent_account  │
                   └───────┬──────────┘
                           │ 1:N
                           ▼
              ┌────────────────────────┐
              │  journal_entry_lines   │◄──N:1──┐
              │  (legs of each entry)  │        │
              └────────┬───────────────┘  ┌─────┴──────────────┐
                       │ N:1              │  journal_entries   │
                       ▼                  │  (txn header)      │
              ┌────────────────────┐      │                    │
              │  investment_lots   │      └────────┬───────────┘
              │  (purchase lots)   │               │ N:1
              └────────┬───────────┘      ┌────────┴───────────┐
                       │ 1:N              │  import_jobs       │
                       ▼                  └────────┬───────────┘
              ┌────────────────────┐               │ N:1
              │  lot_disposals     │      ┌────────┴───────────┐
              │  (sales from lots) │      │  documents         │
              └────────────────────┘      └────────────────────┘

              ┌────────────────────┐      ┌────────────────────┐
              │  instruments       │──1:N─│  instrument_prices │
              │  (master data)     │      │  (time-series)     │
              └────────────────────┘      └────────────────────┘

                         ┌──────────────────────┐
                         │   recurring_         │
                         │   transactions       │
                         │   (SIP, EMIs, etc.)  │
                         └──────┬───────┬───────┘
                          feeds │       │ funds
                     ┌──────────┘       └──────────┐
                     ▼                             ▼
           ┌──────────────────┐           ┌──────────────────────┐
           │    budgets       │           │  financial_goals     │
           │   (monthly plan) │           │  (target + timeline) │
           └───────┬──────────┘           └──────┬──────┬────────┘
                   │ 1:N                    1:N  │      │ 1:N
                   ▼                             ▼      ▼
           ┌───────────────────┐   ┌──────────────┐  ┌─────────────────────┐
           │ budget_line_items │   │ goal_funding_│  │ goal_projection_    │
           │ (envelopes)       │   │ allocations  │  │ scenarios           │
           │                   │   │ (acct → goal)│  │ (what-if models)    │
           └───────┬───────────┘   └──────┬───────┘  └─────────────────────┘
                   │ optional             │
                   │ goal link            │ references
                   └──────────►───────────┘
                                          │
                              ┌───────────┴──────────────┐
                              │  accounts                │
                              │  (from core schema)      │
                              │  journal_entry_lines     │
                              │  (actuals computation)   │
                              └──────────────────────────┘

           ┌──────────────────┐           ┌──────────────────────┐
           │ budget_templates │──1:N────► │ budget_template_items│
           │ (reusable plans) │           └──────────────────────┘
           └──────────────────┘

           ┌──────────────────┐           ┌──────────────────────┐
           │ goal_templates   │           │ goal_milestones      │
           │ (system presets) │           │ (intermediate        │
           └──────────────────┘           │  checkpoints)        │
                                          └──────────────────────┘

                                          ┌──────────────────────┐
                                          │ goal_progress_       │
                                          │ snapshots            │
                                          │ (historical tracking)│
                                          └──────────────────────┘
```

---

## 4. Fundamental Subsystems & Schema Design

### 4.1 Accounting Engine
The Accounting Engine is the single source of truth, enforcing double-entry rules.

*   **Users (`users`):** Tracks identity, preferences, tax regime (Old/New), and FY start month. 
*   **Chart of Accounts (`accounts`):** A hierarchical structure defining Assets, Liabilities, Equity, Income, and Expenses. It supports quantity tracking for investment accounts.
*   **Journal Entries (`journal_entries` & `journal_entry_lines`):** Every financial event is a multi-leg `journal_entry`. The `journal_entry_lines` record the debit/credit values and quantities for investments. 
*   **Balance Checkpoints (`account_balance_checkpoints`):** Stores cumulative totals (total_debit, total_credit, balance, quantity) up to a specific date for an account.

### 4.2 Investment Lot Model (Tax & Valuation)
Crucial for accurately identifying STCG/LTCG components based on specific Indian tax rules.

*   **Instruments Master (`instruments`):** A shared, global reference table containing all valid Indian financial entities (AMFI codes, ISINs, SGBs, equities), including metadata representing tax categories and indexation rules.
*   **Instrument Prices (`instrument_prices`):** A time-series table logging daily closure prices (NAV/Market Price), allowing retroactive portfolio valuations.
*   **Investment Lots (`investment_lots`):** Tracks individual purchases (FIFO queue). Records purchase date, initial quantity, price, and *remaining* quantity. It handles grandfathering rules (e.g., pre-Feb 1 2018 equity valuations).
*   **Lot Disposals (`lot_disposals`):** Links a sale action (`journal_entry_line`) back to the specific `investment_lot` consumed. It permanently records the computed capital gain, holding period, and gain classification (STCG vs. LTCG) for tax reports.

### 4.3 Import & Reconciliation Pipeline
Automates the ingestion of standard PDF, Excel, and CSV statements.

*   **Documents (`documents`):** Logs uploaded files, their hashes (to prevent duplicate processing), and their secure object storage path.
*   **Import Jobs (`import_jobs` & `import_job_rows`):** A state machine managing the extraction workflow (Uploaded → Parsing → Parsed → Categorizing → Ready → Confirmed). It logs success, duplicate skipping (via transaction hash), and errors. Staging table `import_job_rows` hold raw vs. localized data.
*   **Categorization Rules (`categorization_rules`):** An AI and user-driven regex/keyword pattern matching table. Maps transaction narrations (e.g., "SWIGGY") to target accounts. Incorporates hit_counts and priority resolving conflicts.
*   **Reconciliation Links (`reconciliation_links`):** Solves the cross-account transfer problem (e.g., UPI from HDFC to Paytm) by pairing independent journal entries based on matching amounts, dates, and reference numbers (UTR/IMPS).

### 4.4 Planning & Envelope Budgeting
The budgeting engine uses a zero-based envelope architecture, where all income is allocated across various line types.

*   **Budgets (`budgets`):** The header table tracking a specific calendar block (typically monthly). It summarizes high-level expected vs. actual totals, along with unspent rolled-over amounts from past budgets.
*   **Budget Line Items (`budget_line_items`):** Tracks period-specific allocations mapped to `accounts`. A crucial distinction uses `budget_line_type_enum` (INCOME, FIXED_EXPENSE, VARIABLE_EXPENSE, SAVINGS_GOAL, BUFFER) to define how a ledger amount behaves within the envelope. It also tracks `rollover_cap` and `rollover_amount` to handle unspent money.
*   **Budget Templates (`budget_templates` & `budget_template_items`):** Stored defaults allowing users to auto-generate the following month's budget without starting from scratch. These can be user-created or AI-generated based on past spending trends.

### 4.5 Goal Planning (Target Projections)
Goals project target inflation-adjusted amounts over time and pair multiple investments together. Accounts mapped to a goal behave as "savings envelopes" in the broader budgeting ecosystem.

*   **Goal Templates (`goal_templates`):** System-provided defaults modeling complex financial scenarios like Retirement (25x expenses) or Child Education (higher inflation). These contain system defaults for `inflation_rate_pct` and asset allocation.
*   **Financial Goals (`financial_goals`):** The core tracking component. Recomputes dynamically between the absolute `target_amount` and the time-weighted `target_amount_inflated`. Tracks `monthly_required` savings to automatically update budget line items.
*   **Funding Allocations (`goal_funding_allocations`):** A many-to-many junction decoupling accounts from goals. It uses `allocation_type_enum` to dictate if an account funds a goal fully ('FULL'), partially ('PERCENTAGE'), or up to a fixed threshold ('FIXED_AMOUNT').

### 4.6 Recurring Transactions (Shared Primitive)
A critical primitive that bridges both historical accounting generation and future budget expectations.

*   **Recurring Transactions (`recurring_transactions`):** Tracks SIPs, EMI payments, salary intervals, and rent. It features smart `annual_step_up_pct` (essential for compounding Indian SIP scaling) and auto-generates draft or confirmed double-entry journal records on schedule via an external chron worker. It links natively into both `budget_line_items` and `financial_goals`.

### 4.7 Conversational AI Storage
*   **AI Storage (`conversations`, `messages`, `tool_calls`):** Persists chat history, tokens used, and specific tool invocations, offering strict explainability of how AI arrived at a specific conclusion.

---

## 5. Security & Multi-Tenant Data Isolation Strategy

Given the highly sensitive nature of financial data, isolation and security are paramount.

*   **Data Isolation Model:** Operating on a single database, multi-tenancy is enforced strictly using **PostgreSQL Row-Level Security (RLS)**. Every application connection sets context (`SET app.current_user_id`), making all cross-user data completely invisible at the query execution tier.
*   **Encryption at Rest & In Transit:** AES-256 for data on disk; TLS 1.3 for all data in transit.  
*   **BYOK (Bring Your Own Key):** Users configuring external LLMs (OpenAI, Anthropic) enter their API keys, which are encrypted using a symmetric key derived from the user's login session credentials. Keys exist in plaintext only in-memory during API calls.
*   **Data Logging limits:** PII and transactional specifics are minimized or obfuscated before hitting centralized logging or being sent to external LLM providers (to prevent data harvesting).

---

## 6. Advanced Technical Considerations

1.  **Deduplication:** Every transaction is processed through a hashing algorithm upon importation: `SHA256(account_id + date + narration + amount + running_balance)`. A unique constraint on this hash prevents silent duplicate ledger entries.
2.  **Full-Text Search:** Users can inherently search across transaction narrations. PostgreSQL native `tsvector` and `tsquery` search indexes are applied directly to the `narration` field of `journal_entries` and the `extracted_text` of the `documents` table.
3.  **Concurrency Management:** Optimistic concurrency control is employed. If a user tries importing a statement simultaneously while manually adding an expense to the same account, the checkpoint triggers evaluate iteratively in the final transaction commit to compute accurate running balances avoiding race conditions. 
4.  **Portfolio Snapshot Caching:** A nightly cron job iterates across users that experienced transactions on that day, recalculating their book vs market net-worth. This avoids real-time bottlenecks upon opening the dashboard by logging precomputed snapshots into the `portfolio_snapshots` table.
