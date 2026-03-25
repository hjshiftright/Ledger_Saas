# Transaction Manager — ERD, Architecture & Design
## Ledger 3.0 — Module 2 | Version 0.1 | March 15, 2026

---

## 1. Document Purpose

This document is the technical design reference for the Transaction Manager (Module 2 of Ledger 3.0). It covers the complete entity-relationship model, system architecture, component interactions, data-flow sequences, state machines, and key design decisions. It is the engineering counterpart to `transaction-manager-spec.md` (product/UX design) and `pdf-parser.md` (parser implementation detail).

---

## 2. Entity Relationship Diagram

### 2.1 Entity Overview

Every financial event passes through two lifecycle stages before becoming permanent:

| Stage | Entity | Description |
|---|---|---|
| Pre-approval | `PendingTransaction` | Raw parsed transaction in the Review Queue. Can be adjusted, split, linked, excluded, or approved. |
| Post-approval | `JournalEntry` + `JournalEntryLeg` | Immutable double-entry accounting record. Cannot be deleted — only reversed. |

Supporting entities: `Account` (Chart of Accounts tree), `ImportBatch` (groups transactions by source file), `RecurringRule` (schedule templates), `CategorizationRule` (narration → account dictionary), `InvestmentLot` (FIFO purchase lots), `Security` (stocks, MFs, ETFs), `PriceHistory` (market prices), and `ReconciliationRecord` (balance verification checkpoints).

### 2.2 Complete ERD

```mermaid
erDiagram
    USER {
        uuid    user_id         PK
        string  email           UK
        string  full_name
        string  preferred_period    "CALENDAR | FY_INDIA"
        string  llm_provider
        string  llm_api_key_enc     "AES-256 encrypted, never logged"
        timestamp created_at
    }

    ACCOUNT {
        uuid    account_id      PK
        uuid    user_id         FK
        uuid    parent_id       FK  "null = root-level account"
        string  name
        string  account_type        "ASSET|LIABILITY|EQUITY|INCOME|EXPENSE"
        bool    is_investment        "enables Holdings tab"
        bool    is_qty_tracked       "tracks units and shares"
        string  currency            "default INR"
        date    opening_date        "no transactions before this date"
        bool    is_active
    }

    IMPORT_BATCH {
        uuid    batch_id        PK
        uuid    user_id         FK
        string  filename
        string  file_hash           "SHA-256 of original file bytes"
        string  source_type         "HDFC_PDF | CAMS_CAS | ZERODHA_CSV | ..."
        date    statement_from
        date    statement_to
        int     txn_found
        int     txn_new
        int     txn_duplicate
        float   parse_confidence
        string  status              "PARSING|IN_REVIEW|COMPLETED|FAILED|ROLLED_BACK"
        timestamp created_at
    }

    PENDING_TRANSACTION {
        uuid    pending_id      PK
        uuid    batch_id        FK  "null = manual entry or recurring"
        string  txn_hash        UK  "deterministic dedup hash"
        date    txn_date
        date    value_date
        string  narration
        string  narration_raw
        uuid    source_acct_id  FK
        decimal debit_amount
        decimal credit_amount
        decimal amount_signed
        decimal running_balance
        string  reference_num
        uuid    suggested_cat   FK  "suggested category account_id"
        float   cat_confidence
        string  review_status       "PENDING|APPROVED|SKIPPED|EXCLUDED"
        uuid    linked_id       FK  "transfer pair counterpart pending_id"
        timestamp created_at
    }

    TRANSACTION_FLAG {
        uuid    flag_id         PK
        uuid    pending_id      FK
        string  flag_type           "DUPLICATE|TRANSFER_PAIR|LOW_CONF|MANUAL_REV|SPLIT"
        string  description
    }

    SPLIT_LINE {
        uuid    split_id        PK
        uuid    pending_id      FK
        uuid    account_id      FK
        decimal amount
        int     line_order
    }

    JOURNAL_ENTRY {
        uuid    entry_id        PK
        uuid    user_id         FK
        string  entry_number    UK  "JE-YYYY-NNNNNN sequential"
        date    entry_date
        string  narration
        string  entry_type          "NORMAL|OPENING_BAL|REVERSAL|CORRECTION|RECURRING"
        uuid    source_pending  FK  "null if manual or system-generated"
        uuid    batch_id        FK  "null if manual entry"
        uuid    reversal_of     FK  "self-ref: entry_id this entry reverses"
        uuid    corrected_by    FK  "self-ref: correction entry_id"
        bool    is_system
        text    notes
        uuid    recon_period    FK  "null if not reconciled"
        timestamp created_at
    }

    JOURNAL_ENTRY_LEG {
        uuid    leg_id          PK
        uuid    entry_id        FK
        uuid    account_id      FK
        decimal debit_amount        "0 if this is a credit leg"
        decimal credit_amount       "0 if this is a debit leg"
        decimal quantity            "null for non-investment accounts"
        decimal unit_price          "null for non-investment accounts"
        uuid    lot_id          FK  "null if not a sell transaction"
        decimal running_balance     "account balance after this leg"
    }

    ENTRY_TAG {
        uuid    tag_id          PK
        uuid    entry_id        FK
        string  tag_value
    }

    ATTACHMENT {
        uuid    attachment_id   PK
        string  entity_type         "JOURNAL_ENTRY | PENDING_TXN"
        uuid    entity_id
        string  filename
        int     size_bytes
        string  storage_key
        string  content_type
        timestamp created_at
    }

    RECURRING_RULE {
        uuid    rule_id         PK
        uuid    user_id         FK
        string  label
        string  frequency           "WEEKLY|MONTHLY|QUARTERLY|HALF_YEARLY|ANNUALLY"
        int     day_of_period
        date    start_date
        string  end_condition       "NEVER|AFTER_N|UNTIL_DATE"
        int     end_after_n
        date    end_until_date
        bool    is_auto_approve
        string  status              "ACTIVE|PAUSED|ENDED"
        date    last_gen_date
        date    next_due_date
    }

    RECURRING_LEG {
        uuid    leg_id          PK
        uuid    rule_id         FK
        uuid    account_id      FK
        decimal debit_amount
        decimal credit_amount
        int     line_order
    }

    CATEGORIZATION_RULE {
        uuid    rule_id         PK
        uuid    user_id         FK  "null = system-level rule"
        string  pattern_type        "CONTAINS|STARTS_WITH|ENDS_WITH|REGEX"
        string  pattern
        uuid    target_acct_id  FK
        bool    is_case_sensitive
        int     priority
        string  source              "SYSTEM|USER_MANUAL|USER_LEARNED"
        int     match_count
        bool    is_enabled
        timestamp created_at
    }

    SECURITY {
        uuid    security_id     PK
        string  isin            UK
        string  name
        string  security_type       "EQUITY|MF|ETF|GOLD|SGB|BOND"
        string  exchange            "NSE|BSE|AMFI"
        string  amfi_code
        string  ticker
    }

    INVESTMENT_LOT {
        uuid    lot_id          PK
        uuid    account_id      FK
        uuid    security_id     FK
        uuid    buy_entry_id    FK  "journal entry that opened this lot"
        date    buy_date
        decimal buy_quantity
        decimal buy_price
        decimal remaining_qty       "decremented on each SELL"
        bool    is_closed           "true when remaining_qty reaches 0"
    }

    PRICE_HISTORY {
        uuid    price_id        PK
        uuid    security_id     FK
        date    price_date
        decimal price
        string  source              "AMFI_API|NSE_API|BSE_API|MANUAL"
        timestamp fetched_at
    }

    RECONCILIATION_RECORD {
        uuid    recon_id        PK
        uuid    account_id      FK
        uuid    user_id         FK
        decimal statement_bal
        date    target_date
        string  status              "IN_PROGRESS|COMPLETED"
        timestamp completed_at
    }

    RECONCILIATION_TXN {
        uuid    recon_id        FK
        uuid    entry_id        FK
        timestamp cleared_at
    }

    %% --- Relationships ---
    USER                    ||--o{    ACCOUNT                 : "owns"
    USER                    ||--o{    IMPORT_BATCH            : "uploads"
    USER                    ||--o{    JOURNAL_ENTRY           : "has"
    USER                    ||--o{    RECURRING_RULE          : "defines"
    USER                    ||--o{    CATEGORIZATION_RULE     : "creates"
    USER                    ||--o{    RECONCILIATION_RECORD   : "performs"

    ACCOUNT                 |o--o{    ACCOUNT                 : "parent of"
    ACCOUNT                 ||--o{    PENDING_TRANSACTION     : "source account of"
    ACCOUNT                 ||--o{    JOURNAL_ENTRY_LEG       : "posted to"
    ACCOUNT                 ||--o{    SPLIT_LINE              : "receives"
    ACCOUNT                 ||--o{    INVESTMENT_LOT          : "holds lots in"
    ACCOUNT                 ||--o{    RECONCILIATION_RECORD   : "reconciled via"

    IMPORT_BATCH            ||--o{    PENDING_TRANSACTION     : "contains"
    IMPORT_BATCH            ||--o{    JOURNAL_ENTRY           : "sourced"

    PENDING_TRANSACTION     ||--o{    TRANSACTION_FLAG        : "has"
    PENDING_TRANSACTION     ||--o{    SPLIT_LINE              : "splits into"
    PENDING_TRANSACTION     |o--o|    PENDING_TRANSACTION     : "transfer pair"
    PENDING_TRANSACTION     |o--o|    JOURNAL_ENTRY           : "becomes"

    JOURNAL_ENTRY           ||--|{    JOURNAL_ENTRY_LEG       : "has legs"
    JOURNAL_ENTRY           ||--o{    ENTRY_TAG               : "tagged with"
    JOURNAL_ENTRY           |o--o|    JOURNAL_ENTRY           : "reverses or corrects"
    JOURNAL_ENTRY           ||--o{    RECONCILIATION_TXN      : "cleared in"

    JOURNAL_ENTRY_LEG       |o--o|    INVESTMENT_LOT          : "consumes lot"

    RECURRING_RULE          ||--|{    RECURRING_LEG           : "has template legs"
    RECURRING_LEG           }o--||    ACCOUNT                 : "posts to"

    CATEGORIZATION_RULE     }o--||    ACCOUNT                 : "maps to"

    SECURITY                ||--o{    INVESTMENT_LOT          : "tracked via lots"
    SECURITY                ||--o{    PRICE_HISTORY           : "has price history"
    INVESTMENT_LOT          }o--||    JOURNAL_ENTRY           : "created by"

    RECONCILIATION_RECORD   ||--o{    RECONCILIATION_TXN      : "clears"
    RECONCILIATION_TXN      }o--||    JOURNAL_ENTRY           : "marks as cleared"
```

---

## 3. System Architecture

### 3.1 Architectural Overview

The Transaction Manager follows a layered architecture:

- **Client Layer** — React (web) and React Native (mobile) apps. PDF password decryption is performed entirely client-side; only decrypted bytes reach the server.
- **API Gateway** — Authenticates requests, enforces rate limits, routes to services.
- **Backend Services** — Purpose-specific services: importing, reviewing, accounting, categorisation, deduplication, investment tracking, and reconciliation.
- **Parser Registry** — Source-specific parser modules dispatched by a central Source Detector.
- **External Integrations** — AMFI (MF NAVs), NSE/BSE (equity prices), LLM providers.
- **Data Layer** — PostgreSQL (source of truth), Redis (balance cache), file storage (original PDFs + attachments), task queue (background parse jobs).

### 3.2 Component Architecture

```mermaid
graph TD
    subgraph "Client Layer"
        WEB["Web App — React + TypeScript"]
        MOBILE["Mobile App — React Native"]
        CLIENT_DECRYPT["Client-Side PDF Decryption\npdf-lib / pdfjs-dist\nPassword NEVER sent to server"]
    end

    subgraph "API Gateway"
        GW["REST API Gateway\nJWT Auth · Rate Limiting · CORS"]
    end

    subgraph "Core Backend Services"
        SVC_IMPORT["Import Service\nOrchestrates upload → parse → dedup → queue"]
        SVC_REVIEW["Review Service\nQueue management · approval trigger"]
        SVC_ACCOUNTING["Accounting Engine\nJE creation · balance updates · invariants"]
        SVC_CATEGORY["Categorisation Engine\nRule cascade · AI inference · rule learning"]
        SVC_DEDUP["Deduplication Engine\nHash check · near-duplicate · transfer pair"]
        SVC_RECURRING["Recurring Engine\nDaily scheduler · occurrence generation"]
        SVC_INVEST["Investment Engine\nFIFO lots · XIRR · price updates"]
        SVC_RECON["Reconciliation Service\nPeriod management · clearing · locking"]
    end

    subgraph "Parser Registry"
        DETECT["Source Detector\nPage-1 fingerprinting · CSV header analysis"]
        P_CAS["CAS Parser\nCAMS · KFintech · MF Central"]
        P_ZRD["Zerodha Parser\nHoldings · Tradebook · Tax P&L · Capital Gains"]
        P_HDFC["HDFC Bank Parser"]
        P_SBI["SBI Bank Parser"]
        P_ICICI["ICICI Bank Parser"]
        P_OTHER["Axis · Kotak · IndusInd · IDFC Parsers"]
        P_GENERIC["Generic CSV / XLS Parser\n+ Column Mapper UI"]
    end

    subgraph "External Integrations"
        EXT_AMFI["AMFI API — Free\nMutual Fund NAVs (daily)"]
        EXT_MARKET["Market Data\nNSE / BSE equity prices"]
        EXT_LLM["LLM Provider\nOpenAI · Anthropic · Gemini\nUser BYOK key"]
    end

    subgraph "Data Layer"
        DB[("PostgreSQL\nPrimary Database")]
        REDIS[("Redis\nBalance Cache · Session Store")]
        S3["File Storage\nOriginal PDFs + Attachments\nUser-scoped paths + signed URLs"]
        QUEUE["Task Queue\nBackground parse jobs for large files"]
    end

    WEB --> CLIENT_DECRYPT
    MOBILE --> CLIENT_DECRYPT
    CLIENT_DECRYPT -->|"Decrypted bytes only"| GW
    WEB --> GW
    MOBILE --> GW

    GW --> SVC_IMPORT
    GW --> SVC_REVIEW
    GW --> SVC_ACCOUNTING
    GW --> SVC_CATEGORY
    GW --> SVC_RECURRING
    GW --> SVC_INVEST
    GW --> SVC_RECON

    SVC_IMPORT --> DETECT
    DETECT --> P_CAS
    DETECT --> P_ZRD
    DETECT --> P_HDFC
    DETECT --> P_SBI
    DETECT --> P_ICICI
    DETECT --> P_OTHER
    DETECT --> P_GENERIC

    SVC_IMPORT --> SVC_DEDUP
    SVC_IMPORT --> SVC_CATEGORY
    SVC_REVIEW --> SVC_ACCOUNTING
    SVC_RECURRING --> SVC_ACCOUNTING

    SVC_INVEST --> EXT_AMFI
    SVC_INVEST --> EXT_MARKET
    SVC_CATEGORY --> EXT_LLM

    SVC_IMPORT --> DB
    SVC_REVIEW --> DB
    SVC_ACCOUNTING --> DB
    SVC_ACCOUNTING --> REDIS
    SVC_CATEGORY --> DB
    SVC_DEDUP --> DB
    SVC_RECURRING --> DB
    SVC_INVEST --> DB
    SVC_RECON --> DB

    SVC_IMPORT --> S3
    SVC_IMPORT --> QUEUE
    QUEUE --> P_CAS
    QUEUE --> P_ZRD
    QUEUE --> P_HDFC
```

### 3.3 Backend Service Responsibilities

| Service | Core Responsibility | Key Operations |
|---|---|---|
| **Import Service** | Orchestrate file upload → parse → dedup → queue | Upload validate, dispatch parser, create `ImportBatch` + `PendingTransaction` records |
| **Review Service** | Manage the Review Queue | Fetch queue with filters/sort, update review status, trigger bulk approval |
| **Accounting Engine** | Core double-entry engine — sole writer to `journal_entry` | Create JE + legs (atomic), enforce invariants, run reversals, update running balances |
| **Categorisation Engine** | Determine which account a transaction belongs to | Rule-cascade match, LLM tool-call inference, auto-promote rules after repetitive corrections |
| **Deduplication Engine** | Prevent duplicate transactions from entering the ledger | Hash exact-match, near-duplicate fuzzy match, transfer-pair detection across accounts |
| **Recurring Engine** | Generate pending transactions from active recurring rules | Daily scheduler, produce `PendingTransaction` from rule template, place in purple queue section |
| **Investment Engine** | FIFO lot management, XIRR, price fetching | Create lot on BUY, consume lots on SELL, compute capital gains + classification (STCG/LTCG), fetch prices |
| **Reconciliation Service** | Bank reconciliation periods | Create period, mark transactions cleared, compute running difference, lock cleared transactions on completion |

---

## 4. PDF Parser Pipeline

### 4.1 The 8-Stage Pipeline

All documents flow through a common 8-stage pipeline regardless of source. Source-specific parsers handle Stage 5 only.

```mermaid
flowchart TD
    S1["① Upload & Validation\nMIME type check · 50 MB size limit\nQueue file in upload-queue row"]
    S2{"② Password Check\nIs PDF encrypted?"}
    S2_YES["Prompt user for password\nClient-side decryption in browser/app\nPassword discarded immediately after use\nOnly decrypted bytes sent to server"]
    S2_NO["Proceed with plaintext bytes"]
    S3["③ Source Detection\nPage-1 text fingerprinting for PDFs\nCSV header pattern matching\nEmit DetectedSource enum\nLow-confidence → Column Mapper UI"]
    S4["④ Text & Table Extraction\npdfminer text layer for digital PDFs\nCamelot / pdfplumber for structured tables\nTesseract OCR fallback for scanned PDFs\nChunked processing for files over 500 pages"]
    S5["⑤ Source-Specific Parser\nDispatched by ParserRegistry\nbased on DetectedSource enum"]
    S6["⑥ Schema Normalisation\nMap to canonical NormalizedTransaction\nCurrency symbol cleaning · date parsing\nDebit/credit sign normalisation\nRunning balance cross-check"]
    S7["⑦ Deduplication Check\nHash-based exact-match against all prior txn_hashes\nNear-duplicate fuzzy check (amount + date + narration)\nTransfer-pair detection across all user accounts"]
    S8["⑧ Review Queue\nCreate PendingTransaction records with flags\nAI categorisation via rule cascade + LLM\nRoute to user confirmation gate"]

    S1 --> S2
    S2 -->|"Encrypted"| S2_YES
    S2 -->|"Plaintext"| S2_NO
    S2_YES --> S3
    S2_NO --> S3
    S3 --> S4
    S4 --> S5
    S5 --> S6
    S6 --> S7
    S7 --> S8
```

### 4.2 Parser Registry

| Source Type | Enum | Formats | Detection Signal |
|---|---|---|---|
| CAMS CAS | `CAS_CAMS` | PDF (password-protected) | "Computer Age Management Services" in page 1 |
| KFintech CAS | `CAS_KFINTECH` | PDF (password-protected) | "KFintech" or "Karvy" in page 1 |
| MF Central CAS | `CAS_MFCENTRAL` | PDF | "MF Central" in page 1 |
| Zerodha Holdings | `ZERODHA_HOLDINGS` | XLSX / CSV | Header: `ISIN,Stock Symbol,...` |
| Zerodha Tradebook | `ZERODHA_TRADEBOOK` | XLSX / CSV | Header: `symbol,isin,trade_date,trade_type,...` |
| Zerodha Tax P&L | `ZERODHA_TAX_PL` | XLSX / CSV | Sheet name "Tax P&L" or column "Capital Gains" |
| HDFC Bank | `HDFC_PDF` | PDF, CSV | "HDFC Bank" + "Statement of Account" |
| SBI Bank | `SBI_PDF` | PDF, CSV | "State Bank of India" or SBI CSV header |
| ICICI Bank | `ICICI_PDF` | PDF | "ICICI Bank" account statement markers |
| Axis Bank | `AXIS_PDF` | PDF | "Axis Bank" statement header |
| Kotak Bank | `KOTAK_PDF` | PDF | "Kotak Mahindra Bank" |
| IndusInd Bank | `INDUSIND_PDF` | PDF | "IndusInd Bank" |
| IDFC First Bank | `IDFC_PDF` | PDF | "IDFC FIRST Bank" |
| Generic fallback | `GENERIC_CSV` | CSV / XLS / XLSX | Triggered when no other parser matches |

### 4.3 Canonical NormalizedTransaction Schema

Every parser outputs records matching this schema before Stage 6:

| Field | Type | Notes |
|---|---|---|
| `source_type` | string | `DetectedSource` enum value |
| `source_account_hint` | string | Account number, folio number, or identifier extracted from the document |
| `date` | Date | Transaction date |
| `value_date` | Date \| null | Settlement date if available |
| `narration` | string | Cleaned, normalised description |
| `narration_raw` | string | Verbatim as extracted from document |
| `debit_amount` | decimal \| null | Positive — money leaving this account |
| `credit_amount` | decimal \| null | Positive — money entering this account |
| `running_balance` | decimal \| null | Account balance after this transaction |
| `reference_number` | string \| null | UPI ref, NEFT ref, cheque number |
| `quantity` | decimal \| null | Units or shares (investment transactions only) |
| `unit_price` | decimal \| null | NAV or price per unit (investment transactions only) |
| `txn_type_hint` | string \| null | Parser hint: `PURCHASE`, `REDEMPTION`, `DIVIDEND_PAYOUT`, etc. |

---

## 5. Sub-module Interaction Map

The nine sub-modules share the same database and accounting engine. This diagram shows primary data flows.

```mermaid
graph TD
    SM1["Sub-module 1\nImport Hub"]
    SM2["Sub-module 2\nReview Queue"]
    SM3["Sub-module 3\nTransaction List"]
    SM4["Sub-module 4\nManual Entry"]
    SM5["Sub-module 5\nRecurring Rules"]
    SM6["Sub-module 6\nCategorization Rules"]
    SM7["Sub-module 7\nImport History"]
    SM8["Sub-module 8\nReconciliation"]
    SM9["Sub-module 9\nInvestment Holdings"]

    AE(["Accounting Engine"])
    DB[("Database")]

    SM1 -->|"PendingTransactions created"| SM2
    SM2 -->|"Approval event"| AE
    AE -->|"JournalEntries written"| SM3
    SM4 -->|"Manual JE trigger"| AE
    SM5 -->|"Generated PendingTransactions"| SM2
    SM6 -->|"Rules applied during parse"| SM1
    SM6 -->|"Rules applied during review"| SM2
    SM1 -->|"ImportBatch record"| SM7
    SM7 -->|"Undo / rollback event"| AE
    AE -->|"Confirmed entries"| SM8
    AE -->|"InvestmentLot creation\nPriceHistory lookup"| SM9
    SM3 -->|"Edit triggers reversal via"| AE
    AE -->|"All writes"| DB
```

---

## 6. Transaction Lifecycle

### 6.1 PendingTransaction State Machine

A `PendingTransaction` is created when a document is parsed (SM1) or the Recurring Engine fires (SM5). It exists only until approved or permanently excluded.

```mermaid
stateDiagram-v2
    [*] --> PENDING : Created by parser or recurring engine

    PENDING --> PENDING    : User edits category, adds note/tag, adjusts split
    PENDING --> APPROVED   : User approves (individually or via bulk action)
    PENDING --> SKIPPED    : User skips — leaves queue but stays pending
    PENDING --> EXCLUDED   : User intentionally ignores this transaction

    SKIPPED --> PENDING    : User returns to review it
    SKIPPED --> APPROVED   : User approves later
    SKIPPED --> EXCLUDED   : User excludes later

    APPROVED --> [*] : JournalEntry created atomically — PendingTxn archived
    EXCLUDED --> [*] : Archived (visible in import detail, not in active queue)

    note right of APPROVED
        Accounting Engine validates SUM(debits) = SUM(credits)
        JournalEntry + JournalEntryLegs written in single transaction
        Account running balances updated for all affected accounts
        ImportBatch status recalculated
    end note
```

### 6.2 ImportBatch State Machine

```mermaid
stateDiagram-v2
    [*] --> PARSING : File upload received and queued

    PARSING --> IN_REVIEW         : Parse complete — PendingTransactions created
    PARSING --> FAILED            : Fatal parse error (corrupt file, unknown format)

    IN_REVIEW --> COMPLETED        : All PendingTransactions approved or excluded
    IN_REVIEW --> PARTIALLY_REVIEWED : Some approved, some still pending
    PARTIALLY_REVIEWED --> COMPLETED : Remaining items resolved

    COMPLETED --> ROLLED_BACK     : User triggers Undo Import
    IN_REVIEW --> ROLLED_BACK     : User undoes before full approval

    ROLLED_BACK --> [*] : Reversal JEs created for all approved entries in batch\nBatch stays in ImportHistory with ROLLED_BACK status

    note right of ROLLED_BACK
        Reversal JEs created for every approved JournalEntry in the batch
        Pending items discarded (never confirmed — no reversal needed)
        All affected account running balances updated
        Batch archived — visible in Import History with all original transactions
    end note
```

### 6.3 RecurringRule State Machine

```mermaid
stateDiagram-v2
    [*] --> ACTIVE : Rule created by user

    ACTIVE --> ACTIVE  : Scheduled occurrence generated and placed in queue
    ACTIVE --> PAUSED  : User pauses the rule
    PAUSED --> ACTIVE  : User resumes the rule
    ACTIVE --> ENDED   : End condition met (AFTER_N occurrences or UNTIL_DATE reached)
    PAUSED --> ENDED   : User manually ends rule while paused
    ACTIVE --> ENDED   : User manually ends rule

    ENDED --> [*] : No further occurrences generated\nAll historical entries preserved

    note right of ACTIVE
        Recurring Engine runs a daily scheduler job
        Each occurrence becomes a PendingTransaction (purple section)
        If is_auto_approve = true and amount unchanged: bypass queue
        Otherwise: sits in Review Queue for confirmation
        Monthly digest lists all auto-approved occurrences
    end note
```

---

## 7. Data Flow Diagrams

### 7.1 Import-to-Ledger Sequence

```mermaid
sequenceDiagram
    actor User
    participant Client  as Client (Browser / App)
    participant GW      as API Gateway
    participant Import  as Import Service
    participant Parser  as Parser (source-specific)
    participant Dedup   as Dedup Engine
    participant Cat     as Categorisation Engine
    participant DB      as Database
    participant AE      as Accounting Engine

    User->>Client: Drop or select a file
    Client->>Client: Detect if PDF is encrypted

    alt Encrypted PDF
        Client-->>User: Show password prompt with source-specific hint
        User->>Client: Enter password
        Client->>Client: Decrypt PDF locally (pdf-lib)\nPassword discarded from memory immediately
    end

    Client->>GW: POST /import  { file_bytes, filename }
    GW->>Import: Create ImportBatch  status=PARSING
    Import->>DB: Store original file bytes in S3 (user-scoped path)
    Import->>Parser: Dispatch to detected source parser

    Parser->>Parser: Extract text / tables, parse all rows
    Parser-->>Import: List of NormalizedTransaction records

    Import->>Dedup: Check hashes for all new transactions
    Dedup->>DB: Lookup txn_hash in pending_transaction + journal_entry_leg
    Dedup->>Dedup: Near-duplicate check + transfer-pair detection
    Dedup-->>Import: { new_txns, duplicate_txns, transfer_pairs }

    Import->>Cat: Categorise all new transactions
    Cat->>DB: Lookup matching categorisation rules (user rules first)
    Cat->>Cat: Apply rule cascade (user exact → user contains → system exact → system contains → AI)
    Cat-->>Import: { suggested_category_id, confidence } per transaction

    Import->>DB: INSERT PendingTransaction records with suggestions, flags, transfer links
    Import->>DB: UPDATE ImportBatch  status=IN_REVIEW
    Import-->>GW: { batch_id, found: 143, new: 98, duplicate: 45 }
    GW-->>Client: Batch summary card + "Review Transactions →" button
    Client-->>User: "98 transactions ready for review"

    User->>GW: POST /review/approve  { pending_ids: [...] }
    GW->>AE: Create JournalEntries for approved pending transactions

    AE->>AE: Validate SUM(debits) = SUM(credits) per entry
    AE->>DB: INSERT JournalEntry + JournalEntryLegs\n(atomic transaction — all or nothing)
    AE->>DB: UPDATE account running_balance for all affected accounts
    AE->>DB: UPDATE PendingTransactions status=APPROVED
    AE->>DB: Recalculate ImportBatch status
    AE-->>GW: { entries_created: 98 }

    GW-->>Client: Review Queue badge count drops to 0\nTransaction List now shows 98 new entries
```

### 7.2 Correction Flow (Edit a Confirmed Transaction)

```mermaid
sequenceDiagram
    actor User
    participant TxnList as Transaction List (SM3)
    participant GW      as API Gateway
    participant AE      as Accounting Engine
    participant DB      as Database

    User->>TxnList: Click "Edit" on JE-2026-001234
    TxnList-->>User: Detail pane opens in edit mode (all fields pre-populated)

    User->>TxnList: Change category from "Dining Out" to "Groceries"
    User->>TxnList: Click "Save Changes"

    TxnList->>GW: POST /journal-entries/correct\n{ original_entry_id, new_legs }
    GW->>AE: Correct JE-2026-001234

    AE->>DB: CHECK — entry_id not in any COMPLETED reconciliation period
    AE->>DB: INSERT reversal JE-2026-001235\n(mirrored legs, entry_type=REVERSAL, reversal_of=JE-001234)
    AE->>DB: INSERT correction JE-2026-001236\n(new legs, entry_type=CORRECTION)
    AE->>DB: UPDATE JE-001234  corrected_by = JE-001236
    AE->>DB: Recalculate running_balance for all affected accounts

    AE-->>GW: { correction_entry_id: "JE-2026-001236" }
    GW-->>TxnList: Transaction updated — "Edited" badge visible

    User->>TxnList: Click "View Edit History"
    TxnList-->>User: Shows 3 entries:\n  JE-001234 NORMAL (original)\n  JE-001235 REVERSAL\n  JE-001236 CORRECTION (current)
```

### 7.3 Transfer Pair Detection Flow

```mermaid
flowchart TD
    IN["New NormalizedTransaction arrives\nfrom a bank statement parser"]
    CHK_TYPE{"Debit or credit?"}

    QUERY_DEBIT["Query: find recent CREDIT transactions\nacross all other bank/wallet accounts\nfor this user\nSame amount ± ₹1 · Date ± 1 day\nMatching UPI / NEFT / IMPS reference number"]
    QUERY_CREDIT["Query: find recent DEBIT transactions\nacross all other bank/wallet accounts\nfor this user\nSame amount ± ₹1 · Date ± 1 day\nMatching UPI / NEFT / IMPS reference number"]

    MATCH{"Match found?"}
    HIGH["Confidence ≥ 0.90\nAuto-link as Transfer Pair\nSet linked_id on both PendingTransactions\nAdd TRANSFER_PAIR flag\nColour both rows blue in Review Queue"]
    MED["Confidence 0.70 – 0.89\nFlag for user review\nHighlight in queue\nUser confirms or breaks the link"]
    NO_MATCH["No match found\nRoute through categorisation engine\nas standard expense or income"]

    APPROVE["Approval of either row\napproves both simultaneously\nCreates single inter-account transfer JE\nNo income or expense account involved"]

    IN --> CHK_TYPE
    CHK_TYPE -->|"Debit"| QUERY_DEBIT
    CHK_TYPE -->|"Credit"| QUERY_CREDIT
    QUERY_DEBIT --> MATCH
    QUERY_CREDIT --> MATCH
    MATCH -->|"High confidence"| HIGH
    MATCH -->|"Medium confidence"| MED
    MATCH -->|"No match"| NO_MATCH
    HIGH --> APPROVE
    MED --> APPROVE
```

### 7.4 Categorisation Cascade

```mermaid
flowchart TD
    IN["PendingTransaction narration\ne.g. 'UPI/DR/407812/SWIGGY ORDER'"]

    R1{"User rules\nexact match"}
    R2{"User rules\ncontains or regex"}
    R3{"System rules\nexact match"}
    R4{"System rules\ncontains or regex"}
    AI{"LLM Categorisation\nAPI key configured?"}
    AI_NO["Apply 'Miscellaneous'\nLow-confidence flag\nRed row in Review Queue"]

    APPLY["Apply matched category\nconfidence = 1.0\nIncrement rule match_count"]
    AI_APPLY["Apply AI suggestion\nconfidence from model score\nAuto-promote to user rule\nafter 3 identical user corrections"]
    AI_LOW["Apply 'Miscellaneous'\nLow-confidence flag\nYellow or red row in queue"]

    IN --> R1
    R1 -->|"Match"| APPLY
    R1 -->|"No match"| R2
    R2 -->|"Match"| APPLY
    R2 -->|"No match"| R3
    R3 -->|"Match"| APPLY
    R3 -->|"No match"| R4
    R4 -->|"Match"| APPLY
    R4 -->|"No match"| AI
    AI -->|"No key configured"| AI_NO
    AI -->|"Confidence ≥ 0.75"| AI_APPLY
    AI -->|"Confidence < 0.75"| AI_LOW
```

---

## 8. Accounting Engine Design

### 8.1 Core Invariants

The Accounting Engine enforces four invariants. They cannot be bypassed by any service or API call.

| Invariant | Rule | Enforcement |
|---|---|---|
| **Balancing Rule** | `SUM(debit_amounts) = SUM(credit_amounts)` for every `JournalEntry` | Hard reject — database transaction rolled back; the UI disables Save until the entry balances |
| **Immutability** | Confirmed `JournalEntry` rows cannot be updated or deleted | Only `INSERT` is permitted on `journal_entry` and `journal_entry_leg`; corrections create new reversal + correction entries |
| **Period Boundary** | Entry date ≥ account's `opening_date` | Soft block with override confirmation prompt |
| **Locked Period** | Entries in a `COMPLETED` reconciliation period cannot be edited without unlocking | System checks `reconciliation_record.status`; warns before allowing edit |

### 8.2 Journal Entry Generation Patterns

| Transaction Class | Debit Account(s) | Credit Account(s) | Notes |
|---|---|---|---|
| Bank expense (import) | Expense account (suggested category) | Asset › Bank | Standard single-leg import |
| Salary credit (multi-leg) | Asset › Bank (net) · Asset › EPF · Expense › TDS | Income › Salary (gross) | AI suggests split from user's salary structure |
| Bank income / refund | Asset › Bank | Income account | Interest, refunds, rental |
| Inter-account transfer | Asset › Destination Bank | Asset › Source Bank | No income/expense leg |
| Opening balance | Asset account | Equity › Opening Balance Equity | entry_type = `OPENING_BAL` · system-generated |
| MF purchase / SIP | Asset › MF Fund (cost value) | Asset › Bank | Plus quantity + unit_price on debit leg |
| MF redemption | Asset › Bank · Income or Expense › Capital Gains | Asset › MF Fund (book cost of lots consumed) | FIFO lot consumption; STCG / LTCG split |
| Dividend payout | Asset › Bank | Income › Dividends | |
| Stock buy | Asset › Equity Account (cost) | Asset › Bank | New `InvestmentLot` created |
| Stock sell | Asset › Bank · Income or Expense › Capital Gains | Asset › Equity (book cost) | FIFO lot(s) consumed |
| Loan EMI | Liability › Loan (principal) · Expense › Interest | Asset › Bank | AI computes principal/interest split from loan schedule |
| Reversal | Mirror of original (debits ↔ credits swapped) | Mirror of original | entry_type = `REVERSAL` |
| Correction | New user-specified legs | New user-specified legs | entry_type = `CORRECTION` |
| Recurring | Per rule's template legs | Per rule's template legs | entry_type = `RECURRING` |

### 8.3 Reversal and Correction Chain

```mermaid
flowchart LR
    JE1["JE-2026-001234\nentry_type: NORMAL\ncorrected_by: JE-001236\n\nOriginal confirmed entry"]
    JE2["JE-2026-001235\nentry_type: REVERSAL\nreversal_of: JE-001234\n\nMirror legs created silently"]
    JE3["JE-2026-001236\nentry_type: CORRECTION\n\nNew correct legs — what user intended"]

    JE1 -->|"User clicks Edit\n→ Save Changes"| JE2
    JE2 -->|"Immediately followed by"| JE3
    JE1 -.->|"corrected_by"| JE3
    JE2 -.->|"reversal_of"| JE1
```

The user sees only JE-001234 with an **Edited** badge in the Transaction List. The reversal and correction entries appear under "View Edit History."

---

## 9. Investment Account Design

### 9.1 FIFO Lot Model

Every BUY confirmation creates an `InvestmentLot`. Every SELL consumes lots in FIFO order, decrementing `remaining_qty` until the sell quantity is satisfied.

```mermaid
flowchart TD
    BUY1["BUY confirmed — 50 units HDFC Bank @ ₹2,340\n12 Jan 2023"]
    BUY2["BUY confirmed — 30 units HDFC Bank @ ₹2,890\n08 Sep 2024"]
    SELL["SELL confirmed — 70 units HDFC Bank\n15 Mar 2026"]

    LOT1["Lot 1 created\nbuy_date: 12 Jan 2023\nbuy_qty: 50 · buy_price: ₹2,340\nremaining_qty: 50"]
    LOT2["Lot 2 created\nbuy_date: 08 Sep 2024\nbuy_qty: 30 · buy_price: ₹2,890\nremaining_qty: 30"]

    FIFO["FIFO consumption\nConsume all 50 units from Lot 1 first\nConsume 20 units from Lot 2"]

    LOT1_OUT["Lot 1 closed\nremaining_qty: 0\nis_closed: true"]
    LOT2_OUT["Lot 2 partially consumed\nremaining_qty: 10"]

    GAINS["Capital Gains Computed\nLot 1 (50 units, held 3 yr 2 mo) → LTCG\nLot 2 (20 units, held 6 mo) → STCG\nDisplayed to user before confirmation"]

    JE["JournalEntry created\nDr Asset › Bank  ₹X (sale proceeds)\nDr/Cr Income › Capital Gains (LTCG + STCG split)\nCr Asset › Equity Account (book cost of consumed lots)"]

    BUY1 --> LOT1
    BUY2 --> LOT2
    SELL --> FIFO
    LOT1 --> FIFO
    LOT2 --> FIFO
    FIFO --> LOT1_OUT
    FIFO --> LOT2_OUT
    FIFO --> GAINS
    GAINS --> JE
```

### 9.2 XIRR Calculation

XIRR is the discount rate $r$ that satisfies:

$$\sum_{i=1}^{n} \frac{C_i}{\left(1+r\right)^{(d_i - d_0)/365}} = 0$$

Where $C_i$ is the cash flow on date $d_i$ (negative for purchases, positive for redemptions and the current notional market value), and $d_0$ is the date of the first cash flow. Each `journal_entry_leg` with `quantity != null` on an investment account contributes a dated cash flow. The current market value from `price_history` contributes a notional positive cash flow dated today. XIRR is computed per security for the individual row and across all investment accounts for the portfolio summary.

---

## 10. Security Architecture

### 10.1 PDF Password Handling

PDF passwords are processed entirely client-side using `pdf-lib` (web) or `react-native-pdf-lib` (mobile). The password is used to decrypt the PDF bytes in the browser or native app process. Immediately after decryption, the password string is removed from memory. Only the decrypted document content is uploaded to the server. The server never receives, processes, stores, or logs the password at any point.

### 10.2 LLM API Key Security

The user's LLM API key is stored encrypted at rest using AES-256. The encryption key is derived from a server-side secret that is not stored in the database. The plaintext key is decrypted in memory only at the moment of an LLM API call and for the duration of that call only. It is never included in application logs, error reports, debug output, or API responses. The user can rotate or delete their key at any time from Settings.

### 10.3 Data Access Scoping

All backend service queries include a `user_id` filter derived from the authenticated JWT. No API endpoint can return data belonging to a different user. The LLM tool-calling architecture enforces this at the tool function level — `user_id` is a non-overridable parameter injected server-side, never derived from the LLM's output.

### 10.4 Immutability as an Audit Control

The immutable ledger is also a security control. An attacker with write access to the database cannot silently alter historical financial records without leaving a trace: every correction requires a reversal entry, and every entry carries a `created_at` timestamp that cannot be backdated. The combination makes retroactive manipulation detectable.

### 10.5 File Storage

Original uploaded files are stored in user-scoped storage paths (`/users/{user_id}/imports/{batch_id}/{filename}`). Access is via time-limited signed URLs generated at request time. Path scoping combined with signed URL authentication prevents cross-user access through URL guessing or enumeration.

---

## 11. Database Design Notes

### 11.1 Primary Indexes

| Table | Index | Rationale |
|---|---|---|
| `pending_transaction` | `(user_id, review_status)` | Primary Review Queue fetch |
| `pending_transaction` | `txn_hash` unique | Deduplication hash lookup |
| `pending_transaction` | `(batch_id, review_status)` | Batch-level queue filtering |
| `journal_entry` | `(user_id, entry_date DESC)` | Transaction List default sort |
| `journal_entry` | `entry_number` unique | JE number lookup |
| `journal_entry_leg` | `account_id` | Account-level ledger queries |
| `journal_entry_leg` | `(account_id, entry_date DESC)` | Passbook view ordered by date |
| `investment_lot` | `(account_id, security_id, is_closed)` | Open lot lookup for FIFO |
| `price_history` | `(security_id, price_date DESC)` | Latest price lookup |
| `categorization_rule` | `(user_id, is_enabled, priority DESC)` | Rule cascade evaluation order |
| `reconciliation_record` | `(account_id, status)` | Active reconciliation check |

### 11.2 Partitioning

`journal_entry` and `journal_entry_leg` are the largest tables over the long term. Partition `journal_entry` by `user_id` using hash partitioning to distribute load. Alternatively, partition by `entry_date` year for date-range report optimisation where full cross-year queries are rare.

### 11.3 Integrity Constraints

| Constraint | Implementation |
|---|---|
| JE must balance | Application-level validation in Accounting Engine + DB trigger as safety net: asserts `SUM(debit_amount) = SUM(credit_amount)` per `entry_id` before commit |
| JE minimum 2 legs | Enforced at application layer; DB-level count check on insert |
| Lot quantity non-negative | `CHECK (remaining_qty >= 0)` on `investment_lot` |
| Dedup hash unique per user | Unique index on `(user_id, txn_hash)` — constraint enforced at DB level, not just application |
| Account type hierarchy | Enum constraint on `account_type`; parent account must exist and be of the same or parent-compatible type |

### 11.4 Soft Deletes and Archiving

No rows are hard-deleted from any financial table. `import_batch`, `pending_transaction`, `journal_entry`, and `investment_lot` use a soft-delete pattern (`is_archived`, `archived_at`). All standard API queries filter `WHERE is_archived = false`. The Import History sub-module explicitly queries archived records to provide the complete audit trail.

---

## 12. Key Design Decisions

| Decision | Choice Made | Rationale |
|---|---|---|
| **Client-side PDF decryption** | Password handling entirely in browser or native app | User trust: no PAN-derived password ever transmitted to a server. Regulatory: avoids any server-side handling of authentication credentials |
| **Mandatory review gate** | All import transactions require human confirmation before becoming JEs | Prevents silent AI miscategorisation errors and corrupted parser output from entering the permanent ledger undetected |
| **Immutable ledger with reversal** | No `UPDATE` or `DELETE` on `journal_entry`; corrections via reversal + re-entry | Full audit trail, compliance with double-entry accounting principles, tamper-evidence, and protection against silent data corruption |
| **Two-stage transaction model** | `PendingTransaction` → `JournalEntry` separation | Separates the parsing "intent" from the ledger "fact". Allows safe rejection, editing, splitting, and annulment before any accounting commitment is made |
| **BYOK LLM** | User supplies their own API key; system stores it encrypted, never in plaintext | Financial data is never sent to an LLM service without explicit user setup. No SaaS LLM vendor dependency for core features |
| **FIFO by default, user override on SELL** | Default lot matching is oldest-first; user can pick specific lots before confirming | Aligns with Indian tax authority default guidance on cost basis; user override supports tax-optimisation strategies (loss harvesting, LTCG planning) |
| **Rule learning from corrections** | After 3 identical user re-categorisations for the same narration pattern, a user rule is auto-promoted | Reduces repetitive manual work without requiring users to explicitly manage rules they may not know exist |
| **Recurring = confirm by default** | Recurring transactions land in the Review Queue; auto-approve is opt-in per rule | Prevents silent incorrect amounts when recurring values change (rent increase, SIP change, rate-linked EMI fluctuation) |
| **Import undo as batch, not per-transaction** | Undo reverses all JEs in a batch atomically | Maintains ledger and deduplication hash consistency — a partial undo would leave the system in an inconsistent state where some transactions appear to exist and some do not |
| **Hash-based deduplication** | `hash(account_id + date + narration + amount + running_balance)` | Deterministic and reproducible: the same statement re-imported always produces the same hashes and is guaranteed to skip. No need to store the original file content for dedup purposes |
| **Transfer pair detection before categorisation** | Dedup Engine runs transfer-pair detection before the Categorisation Engine assigns a category | Prevents inter-account transfers from being incorrectly categorised as income or expenses — the most common source of spending report inflation in personal finance tools |
