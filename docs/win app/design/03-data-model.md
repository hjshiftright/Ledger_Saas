# Ledger Desktop — Data Model

**Version:** 1.0  
**Status:** Design Review

> **Family Mode Extensibility:** All core tables carry a nullable `FamilyMemberId` FK from migration 0001. In v1, only a single `FamilyMember` row exists (`Relationship = Self`, seeded at install). v2 adds the Family Management UI without requiring a schema migration.

---

## 1. Entity Relationship Overview

```
FamilyMember (1) ──────────────────────────────────────────────────────────┐
     │                                                                      │
     │ (1:N)                                                                │
     ▼                                                                      │
UserProfile (1)          BankAccount (N)  ──────► FinancialInstitution (1) │
     │                        │                                             │
     │                        │ (1:N)                                       │
     │                        ▼                                             │
     │              ReconciliationRecord (N)                                │
     │                                                                      │
FileRegistry (N) ──────► ImportBatch (1) ──────► Transaction (N) ◄─────────┘
     │                                                │
     │                                         TransactionLine (N)
     │                                         TransactionCharge (N)
     │                                         Attachment (N)
     │                                         TransactionTag (N)
     │                                               │
ProcessingQueueItem (1)                         Tag (N)
                                                Budget ──► BudgetItem
                                                Goal ──► Milestone ──► Contribution
```

---

## 2. Core Entities

### 2.1 FamilyMember
Represents the primary user and any family members added in v2.

```sql
CREATE TABLE family_members (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    relationship          TEXT NOT NULL,  -- Self|Spouse|Child|Parent|Other
    display_name          TEXT NOT NULL,
    dob_encrypted         BLOB,           -- AES-256-GCM(DOB, dbKey)
    pan_encrypted         BLOB,           -- AES-256-GCM(PAN, dbKey)
    mobile_encrypted      BLOB,           -- AES-256-GCM(mobile, dbKey)
    password_hint         TEXT,           -- display-safe, no sensitive data
    is_active             INTEGER NOT NULL DEFAULT 1,
    created_at            TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at            TEXT NOT NULL DEFAULT (datetime('now'))
);
```

**Seeded row (v1 install):**
```json
{ "id": 1, "relationship": "Self", "display_name": "[from setup]", "is_active": 1 }
```

### 2.2 UserProfile
Application preferences and settings for the primary user.

```sql
CREATE TABLE user_profiles (
    id                             INTEGER PRIMARY KEY AUTOINCREMENT,
    family_member_id               INTEGER REFERENCES family_members(id),
    display_name                   TEXT NOT NULL,
    base_currency                  TEXT NOT NULL DEFAULT 'INR',
    financial_year_start_month     INTEGER NOT NULL DEFAULT 4,
    tax_regime                     TEXT,       -- NEW|OLD
    date_format                    TEXT NOT NULL DEFAULT 'DD/MM/YYYY',
    number_format                  TEXT NOT NULL DEFAULT 'INDIAN',
    created_at                     TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at                     TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### 2.3 AppSettings
Key-value store for application configuration.

```sql
CREATE TABLE app_settings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_key     TEXT NOT NULL UNIQUE,
    setting_value   TEXT,
    category        TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
```

**Critical keys (seeded on setup completion):**

| Key | Value | Notes |
|---|---|---|
| `ledger_drive_path` | `C:\Users\...\LedgerDrive` | Set in Quick-Start Wizard |
| `setup_complete` | `true` | Gate for QuickStartWizard |
| `pin_enabled` | `false` | PIN state |
| `pin_salt` | `<base64>` | For Argon2id |
| `ocr_preference` | `WindowsFirst` | WindowsFirst/TesseractFirst |
| `privacy_mode_default` | `true` | LLM privacy mode default |
| `family_mode_enabled` | `false` | Feature flag for v2 |
| `api_port` | `5177` (or random) | Persisted after first bind |

### 2.4 FileRegistry
Tracks every file ever seen by LedgerDrive — from vault copy through organization.

```sql
CREATE TABLE file_registry (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    file_hash             TEXT NOT NULL UNIQUE,  -- SHA-256 hex
    original_name         TEXT NOT NULL,
    original_path         TEXT,
    vault_path            TEXT NOT NULL,
    organized_path        TEXT,
    detected_bank         TEXT,
    detected_file_type    TEXT,                  -- PDF|CSV|XLSX|Unknown
    detected_source_type  TEXT,                  -- HDFC_PDF|SBI_CSV|...
    detection_confidence  REAL,
    processing_status     TEXT NOT NULL DEFAULT 'Vaulted',
    was_encrypted         INTEGER NOT NULL DEFAULT 0,
    unlock_method         TEXT,                  -- AutoCracked|UserProvided|None
    import_batch_id       INTEGER REFERENCES import_batches(id),
    attributed_member_id  INTEGER REFERENCES family_members(id), -- v2 family attribution
    shell_overlay_state   TEXT NOT NULL DEFAULT 'Syncing', -- Syncing|Done|Error|Missing
    created_at            TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at            TEXT NOT NULL DEFAULT (datetime('now'))
);
```

**ProcessingStatus enum values:**
`Vaulted → Detecting → PasswordRequired → Parsing → Normalized → Deduplicating → Categorizing → Proposing → Organized → Failed → Removed | Unsupported`

### 2.5 ProcessingQueueItem
Persisted queue — survives crash/restart.

```sql
CREATE TABLE processing_queue_items (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    file_registry_id  INTEGER NOT NULL REFERENCES file_registry(id),
    status            TEXT NOT NULL DEFAULT 'Pending',  -- Pending|InProgress|Done|Failed
    attempts          INTEGER NOT NULL DEFAULT 0,
    last_error        TEXT,
    locked_at         TEXT,  -- timestamp when picked up; cleared on completion
    created_at        TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at        TEXT NOT NULL DEFAULT (datetime('now'))
);
```

---

## 3. Account & Financial Entities

### 3.1 Account (Chart of Accounts)
```sql
CREATE TABLE accounts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_id       INTEGER REFERENCES accounts(id),
    family_member_id INTEGER REFERENCES family_members(id),  -- v2: per-member COA
    code            TEXT NOT NULL,
    name            TEXT NOT NULL,
    account_type    TEXT NOT NULL,  -- Asset|Liability|Income|Expense|Equity
    normal_balance  TEXT NOT NULL,  -- Debit|Credit
    is_placeholder  INTEGER NOT NULL DEFAULT 0,
    is_system       INTEGER NOT NULL DEFAULT 0,
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### 3.2 FinancialInstitution
```sql
CREATE TABLE financial_institutions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    type        TEXT NOT NULL,  -- Bank|Brokerage|InsuranceCompany|MutualFund|NBFC
    logo_path   TEXT,
    website     TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### 3.3 BankAccount
```sql
CREATE TABLE bank_accounts (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    family_member_id      INTEGER REFERENCES family_members(id),
    institution_id        INTEGER REFERENCES financial_institutions(id),
    account_id            INTEGER REFERENCES accounts(id),
    account_number_masked TEXT,
    ifsc_code             TEXT,
    branch                TEXT,
    nick_name             TEXT,
    is_primary            INTEGER NOT NULL DEFAULT 0,
    opening_date          TEXT,
    created_at            TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at            TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### 3.4 CreditCard
```sql
CREATE TABLE credit_cards (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    family_member_id  INTEGER REFERENCES family_members(id),
    institution_id    INTEGER REFERENCES financial_institutions(id),
    account_id        INTEGER REFERENCES accounts(id),
    card_number_masked TEXT,
    credit_limit      REAL,
    billing_cycle_day INTEGER,
    annual_fee        REAL,
    created_at        TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at        TEXT NOT NULL DEFAULT (datetime('now'))
);
```

---

## 4. Transaction Entities

### 4.1 Transaction
```sql
CREATE TABLE transactions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    family_member_id INTEGER REFERENCES family_members(id),
    transaction_date TEXT NOT NULL,
    effective_date   TEXT,
    type             TEXT NOT NULL,  -- Journal|BankImport|ManualCash
    description      TEXT,
    status           TEXT NOT NULL DEFAULT 'Draft',  -- Draft|Posted|Void
    txn_hash         TEXT UNIQUE,    -- deduplication fingerprint
    import_batch_id  INTEGER REFERENCES import_batches(id),
    is_manual        INTEGER NOT NULL DEFAULT 0,
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at       TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### 4.2 TransactionLine
```sql
CREATE TABLE transaction_lines (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id  INTEGER NOT NULL REFERENCES transactions(id),
    account_id      INTEGER NOT NULL REFERENCES accounts(id),
    amount          REAL NOT NULL,
    line_type       TEXT NOT NULL,  -- Debit|Credit
    description     TEXT,
    security_id     INTEGER REFERENCES securities(id),
    quantity        REAL,
    price_per_unit  REAL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### 4.3 ImportBatch
```sql
CREATE TABLE import_batches (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    family_member_id INTEGER REFERENCES family_members(id),
    file_hash        TEXT NOT NULL,
    source_type      TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'Uploaded',
    total_records    INTEGER,
    imported_count   INTEGER,
    duplicate_count  INTEGER,
    error_log        TEXT,
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at       TEXT NOT NULL DEFAULT (datetime('now'))
);
```

---

## 5. Categorization & Rules

### 5.1 UserCategoryRule
```sql
CREATE TABLE user_category_rules (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    family_member_id INTEGER REFERENCES family_members(id),
    pattern         TEXT NOT NULL,  -- regex
    category_code   TEXT NOT NULL,
    priority        INTEGER NOT NULL DEFAULT 100,
    match_count     INTEGER NOT NULL DEFAULT 0,
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### 5.2 Payee
```sql
CREATE TABLE payees (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    name                TEXT NOT NULL,
    type                TEXT,  -- Individual|Business|Government
    default_account_id  INTEGER REFERENCES accounts(id),
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);
```

---

## 6. Planning Entities

### 6.1 Budget
```sql
CREATE TABLE budgets (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    family_member_id INTEGER REFERENCES family_members(id),  -- NULL = family-wide
    name             TEXT NOT NULL,
    period_type      TEXT NOT NULL,  -- Monthly|Quarterly|Yearly
    start_date       TEXT NOT NULL,
    end_date         TEXT,
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at       TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### 6.2 Goal
```sql
CREATE TABLE goals (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    family_member_id INTEGER REFERENCES family_members(id),  -- NULL = family-wide
    name             TEXT NOT NULL,
    type             TEXT,  -- Retirement|Education|Emergency|Vacation|Home|Car|Other
    target_amount    REAL NOT NULL,
    target_date      TEXT,
    current_value    REAL NOT NULL DEFAULT 0,
    status           TEXT NOT NULL DEFAULT 'Active',  -- Active|Achieved|Abandoned
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at       TEXT NOT NULL DEFAULT (datetime('now'))
);
```

---

## 7. System & Security Entities

### 7.1 AuditLog
```sql
CREATE TABLE audit_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type  TEXT,
    entity_id    INTEGER,
    action       TEXT NOT NULL,  -- DbUnlock|PinVerify|LlmCall|FileAdded|FileRemoved|TransactionManual
    detail       TEXT,           -- JSON — never contains passwords or PAN
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### 7.2 LlmProvider
```sql
CREATE TABLE llm_providers (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_name  TEXT NOT NULL,  -- Gemini|OpenAI|Anthropic
    api_key_dpapi  TEXT NOT NULL,  -- DPAPI-encrypted base64
    text_model     TEXT,
    vision_model   TEXT,
    is_default     INTEGER NOT NULL DEFAULT 0,
    created_at     TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at     TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### 7.3 NetWorthHistory
```sql
CREATE TABLE net_worth_history (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    family_member_id INTEGER REFERENCES family_members(id),  -- NULL = consolidated
    snapshot_date    TEXT NOT NULL,
    total_assets     REAL NOT NULL,
    total_liabilities REAL NOT NULL,
    net_worth        REAL NOT NULL,
    created_at       TEXT NOT NULL DEFAULT (datetime('now'))
);
```

---

## 7a. Manual Lending & Loan Tracking

### 7a.1 ManualLoan

Tracks money lent to or borrowed from friends/family outside bank statements.

```sql
CREATE TABLE manual_loans (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    family_member_id     INTEGER REFERENCES family_members(id),
    direction            TEXT NOT NULL,   -- Lent | Borrowed
    counterparty_name    TEXT NOT NULL,   -- "Ravi", "Priya's Brother", etc.
    principal_amount     REAL NOT NULL,
    interest_rate        REAL NOT NULL DEFAULT 0,  -- annual %, 0 = interest-free
    interest_mode        TEXT NOT NULL DEFAULT 'None',  -- None|Simple|CompoundMonthly
    start_date           TEXT NOT NULL,
    due_date             TEXT,            -- NULL = open-ended
    repayment_schedule   TEXT,           -- JSON: [{date, amount}...] optional plan
    notes                TEXT,
    is_settled           INTEGER NOT NULL DEFAULT 0,
    settled_date         TEXT,
    created_at           TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at           TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### 7a.2 LoanRepayment

Each payment against a `ManualLoan`.

```sql
CREATE TABLE loan_repayments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    loan_id         INTEGER NOT NULL REFERENCES manual_loans(id),
    repayment_date  TEXT NOT NULL,
    principal_paid  REAL NOT NULL,
    interest_paid   REAL NOT NULL DEFAULT 0,
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
```

---

## 7b. EMI / Home Loan Prepayment Insights

### 7b.1 HomeLoanProfile

Stores the current state of a home loan for prepayment calculations. Auto-populated from parsed loan statements; user-editable.

```sql
CREATE TABLE home_loan_profiles (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    family_member_id        INTEGER REFERENCES family_members(id),
    bank_account_id         INTEGER REFERENCES bank_accounts(id),  -- nullable if manual
    lender_name             TEXT NOT NULL,
    outstanding_principal   REAL NOT NULL,
    annual_interest_rate    REAL NOT NULL,
    original_loan_amount    REAL,
    monthly_emi             REAL NOT NULL,
    remaining_months        INTEGER NOT NULL,
    loan_start_date         TEXT,
    last_updated_from       TEXT,   -- 'Statement' | 'Manual'
    last_updated_at         TEXT NOT NULL DEFAULT (datetime('now')),
    created_at              TEXT NOT NULL DEFAULT (datetime('now'))
);
```

**Prepayment calculations are computed on-the-fly** (not stored) using the reducing-balance EMI formula. No separate table needed — results are returned from `GET /insights/emi/{loanId}/prepayment?extra=5000`.

---

## 8. Family Mode Extensibility Design

### How v1 Schema Supports v2 Without Migration

All tables with `family_member_id` are designed with a **nullable FK**:
- `NULL` = ownership not yet attributed (legacy or shared)
- `1` = primary user (Self, always exists)
- `2+` = additional family members (added in v2)

In v1:
- `FamilyMember` table has exactly 1 row: `{ id: 1, relationship: "Self" }`
- All entities are effectively attributed to `member_id = 1`
- `family_mode_enabled = false` in AppSettings hides all family UI

In v2:
- Set `family_mode_enabled = true`
- Add family member rows
- `Family/{Name}/` subfolders appear in LedgerDrive
- New files in those subfolders set `attributed_member_id` to the matched member
- No schema migration required

### Password Cracking Attribution
```
File dropped in LedgerDrive\Family\Priya\SBI_2025.pdf
  │
  └── VaultManager: attributed_member_id resolved from folder path "Priya"
        └── Look up FamilyMember WHERE display_name = 'Priya'
  │
  └── PasswordCrackerService:
        1. Attempt with Priya's credentials (DOB, PAN, mobile, combos)
        2. On failure: attempt with primary user's credentials
        3. On failure: emit file.pw_required { fileName, memberName: "Priya" }
        4. Toast: "Password needed for SBI_2025.pdf (Priya's file)"
```

### Family Net Worth Query (v2)
```sql
-- Consolidated family net worth
SELECT
    SUM(CASE WHEN a.account_type = 'Asset' THEN tl.amount ELSE 0 END) AS total_assets,
    SUM(CASE WHEN a.account_type = 'Liability' THEN tl.amount ELSE 0 END) AS total_liabilities
FROM transaction_lines tl
JOIN transactions t ON tl.transaction_id = t.id
JOIN accounts a ON tl.account_id = a.id
WHERE t.status = 'Posted'
  AND (t.family_member_id IS NULL OR t.family_member_id IN (
    SELECT id FROM family_members WHERE is_active = 1
  ));

-- Per-member net worth
-- Add: AND t.family_member_id = :memberId
```

---

## 9. Migration Strategy

| Migration | Description |
|---|---|
| `0001_InitialSchema` | All tables including `family_member_id` FKs (nullable), seeds Self member, seeds COA |
| `0002_AddFileRegistry` | `file_registry` and `processing_queue_items` tables |
| `0003_AddMlSettings` | `app_settings` keys for ML model path and OCR preference |
| Future `0004_FamilyMode` | No schema changes needed — just set `family_mode_enabled = true` and expose folder watcher for subfolders |

EF Core applies migrations on startup: `await db.Database.MigrateAsync()`
