

<think>The user wants me to create a comprehensive database schema document for their personal finance management application. This needs to cover all four modules we've discussed (Onboarding Manager, Goal Manager, Transaction Manager, Reports Manager) plus the cross-cutting concerns I identified (audit trail, recurring transactions, settings, etc.).

Let me think through all the tables needed:

**Core Accounting Tables:**
1. Chart of Accounts (tree structure)
2. Journal Entries (header)
3. Journal Entry Lines (detail - debit/credit lines)
4. Account Balances (monthly snapshots)

**Account & Institution Tables:**
5. Financial Institutions (banks, brokerages)


6. Bank Accounts
7. Credit Cards
8. Loans
9. Brokerage Accounts

**Investment Tables:**
10. Securities Master (stocks, mutual funds, ETFs)
11. Holdings (current portfolio)
12. Market Prices (time-series NAV/price data)
13. Mutual Fund Schemes
14. F&O Contracts
15. F&O Positions
16. Lots/Tax Lots (for FIFO/specific identification)

**Transaction Tables:**
17. Transactions (the user-facing transaction - wraps journal entries)
18. Transaction Splits (for split transactions)
19. Transaction Tags
20. Transaction Attachments
21. Recurring Transaction Templates

**Goal Tables:**
22. Goals
23. Goal Milestones
24. Goal Account Links
25. Goal Contributions

**Budget Tables:**
26. Budgets
27. Budget Line Items

**Category & Classification Tables:**
28. Categories (could be part of chart of accounts)
29. Tags
30. Merchants/Payees

**Report Tables:**
31. Saved Reports
32. Report Schedules
33. Monthly Snapshots
34. Dashboard Configurations

**Settings & Configuration Tables:**
35. App Settings
36. Import Profiles
37. Import History

**Audit Tables:**
38. Audit Log

**Other:**
39. Currencies
40. Exchange Rates
41. Tax Deduction Sections (80C, 80D, etc.)

Now I need to step back and think through the schema design more systematically.

For the Chart of Accounts, I should structure it around the standard accounting categories: Assets covering bank accounts and investments, Liabilities for credit cards and loans, Income for salary and investment returns, Expenses broken down by type, and Equity for opening balances. Each account needs to map to actual financial entities the user holds.

I'm going to organize this comprehensively into modules—starting with Core Accounting for the fundamental double-entry bookkeeping structure, then Financial Accounts for managing institutions and their accounts. Now I'm mapping out the core relationships between these modules—transactions create journal entries that post to accounts, securities track price history, holdings connect them to brokerage accounts, and recurring templates automate transaction generation. I'll document each table comprehensively with columns, types, and relationships, keeping descriptions concise and using standard SQL types that work across most databases.

Starting with the foundational tables: accounts as the Chart of Accounts backbone, account_types for the standard categories, journal entries and their line items for double-entry bookkeeping, transactions as the user-facing layer, and then the institution and account-specific tables like bank accounts, credit cards, loans, and brokerage accounts.

Now I'm mapping out the investment and securities side: a securities master table for stocks, mutual funds, and ETFs, with time-series price data, current holdings, and tax lot tracking for cost basis. I also need F&O contract definitions and positions for derivatives, plus expense and income categorization through either accounts or a separate categories table, user tags, payees, and recurring transaction templates with their generated history.

Rounding out the schema with goals and milestones for financial planning, and the relationship tables to tie everything together. I'm reconsidering whether all these tables are necessary for an MVP—the user did ask for exhaustive coverage, so I'll keep them but flag which ones are essential versus future additions. More importantly, I need to clarify the relationship between transactions and journal entries. A transaction is really just the user-facing event, while the journal entry with its debit and credit lines is the accounting mechanism underneath. I think I can simplify this by merging them into a single transactions table rather than maintaining both, since they're describing the same thing from different angles. the debits and credits must balance. I'll keep it simple with just transactions and transaction_lines for the MVP.

Now I'm thinking through the Chart of Accounts structure—I'll use a parent_id field to create a tree hierarchy, which is straightforward and flexible enough for what we need. As I draft the full schema document, I want to be comprehensive but concise, so I'll organize it by domain and include the essential details for each table: purpose, columns with their types and descriptions, keys, and indexes. I'll focus on clarity over SQL syntax since the implementation details can vary.

Let me start mapping out the core tables and their fields carefully, beginning with the accounts table and its hierarchy of account types and subtypes.

For the accounts table, I need to distinguish between system-created accounts and user-created ones, and track whether each account is a placeholder node or a leaf that can hold transactions. The opening balance should come from a dedicated journal entry rather than being stored directly on the account. I'll also need to track the normal balance side for each account based on its type.

Now moving to financial institutions—I'm defining a table to store banks, brokerages, and other financial entities with their basic metadata like name, type, logo, and website.

For bank accounts, I'm creating a junction table that links the chart of accounts to actual bank accounts at specific institutions, capturing details like account number, IFSC code, and account type. Similarly, I'm setting up a credit cards table that tracks card details linked to accounts, including the card network and type.

Now I'm defining the loans table to capture liability accounts, with fields for loan type, principal amount, interest details, EMI calculations, and tenure information, plus an optional link to asset accounts for secured loans like mortgages.

Continuing with brokerage accounts to track demat and trading accounts, including depository information and PAN linkage, then securities to store equity, mutual fund, and bond data with ISIN identifiers. I'm defining the tax_lots table to track individual purchase batches with their acquisition details, remaining quantities, and status as they're sold off, then moving into the derivatives schema with fo_contracts to represent futures and options with their expiry dates and strike prices, and fo_positions to track open derivative positions.

Defining transaction schema... Continuing with the transaction_lines table, each line tracks the debit or credit side with the amount, line type, and optional security details for investments including quantity and price per unit. Then I'm mapping transactions to tags through a join table, defining the tags themselves with names and colors for organization, and finally setting up the payees table to store vendor or recipient information with categories.

For attachments, I'm linking files directly to transactions so users can store receipts and documents, capturing the file metadata like type and size. Recurring transactions will handle automated entries with a template name, frequency pattern from daily to yearly, and date range to control when they generate new transaction instances.

I'm thinking about keeping the recurring template straightforward for the MVP—just tracking the debit and credit accounts with the amount, rather than building out complex multi-line templates right now. For the goals feature, I'm defining tables to track financial objectives with their current progress, target milestones, and how different accounts contribute toward each goal. The goal_account_mappings table lets users allocate portions of their accounts to specific goals, while goal_milestones will track progress checkpoints. Defining the remaining schema tables... Defining the import profile structure with file format handling, column mapping configuration, and batch tracking for different statement types like bank statements, brokerage trades, and mutual fund documents.

Now I'm laying out the application settings schema with configurable parameters across categories like display, tax, notifications, and security, then moving into Indian tax section definitions with deduction limits and applicable regimes.

Defining the tax section mappings to link deductions to specific accounts or securities like ELSS funds, along with an audit log to track all entity changes with detailed field-level history and a notifications table for user alerts.

Now I'm thinking through what else might be needed—fixed assets like property and vehicles can just be regular accounts in the chart of accounts, and for the MVP I'll track insurance policies as recurring transactions rather than creating a separate table.

For retirement accounts like EPF and PPF, those fit as account subtypes, and SIP registrations are already covered through recurring transactions linked to securities. I'm also accounting for dividend tracking and stock splits through transaction types that impact tax lots.

I'm considering whether to add a holdings table to track securities across brokerage accounts—it could be materialized for performance rather than computed on the fly.

Now I'm thinking through the default chart of accounts structure, starting with the asset hierarchy for cash and bank accounts.

Continuing with the investment categories like equities, mutual funds, ETFs, bonds, and retirement accounts such as EPF, PPF, and NPS. Then fixed assets covering real estate, vehicles, and physical gold, plus receivables for loans and deposits.

Now I'm mapping out the liability side with credit cards, various loan types including home, car, personal, education, and gold loans, along with payables for bills and taxes. On the income side, I'm breaking down salary components like basic pay, HRA, allowances, and bonuses, then investment income from interest, dividends, and capital gains.

Continuing with the expense categories, I'm organizing housing costs like rent and maintenance, utilities including electricity and water, and food expenses split between groceries and dining out. I'm finishing out the expense categories with hobbies, travel, financial charges, and miscellaneous items, then moving into the equity section with opening balances and retained earnings. Now I'll switch to SQL DDL format to structure this as a proper database schema.

I'm thinking through the best approach here—mixing DDL statements with explanatory prose for each table group, organized by domain. For the MVP I'll skip user_id columns since it's single-user, but I should note where those would be added for multi-user scaling. Let me start writing out the schema with table purposes, creation statements, and design notes where they matter. I've established the naming conventions and structure, so now I'm ready to write out the complete specification document with all the tables and their relationships clearly laid out.</think># Database Schema Design Document

## Personal Finance Management Application — Single-User MVP

**Version:** 1.0
**Date:** March 14, 2026
**Scope:** Complete relational schema for a local-first, double-entry personal finance application targeting Indian users

---

## 1. Design Principles

The schema is built on five foundational principles. First, double-entry integrity: every financial movement is recorded as balanced debit and credit lines against a unified Chart of Accounts. No money appears or disappears. Second, immutability of accounting records: journal entries (transactions) are never edited in place. Corrections are made through reversal entries followed by new correcting entries. The audit log captures all activity. Third, temporal queryability: every financial record carries date information, and monthly snapshot tables allow efficient point-in-time balance queries without scanning the full transaction history. Fourth, extensibility for multi-user: the current schema is single-user. Every table that would require user scoping in a multi-user version is noted. Adding a `user_id` foreign key and appropriate indexes is the primary migration path. Fifth, local-first storage with engine portability: the schema uses generic SQL types compatible with SQLite (the default local engine) while remaining portable to PostgreSQL or MySQL. SQLAlchemy Core is the data access layer — table definitions are `Table` objects in Python, queries use the SQL expression language, and Alembic manages schema migrations. The raw SQL DDL in this document serves as the **reference schema specification**; the actual table definitions are SQLAlchemy `Table` objects that produce equivalent DDL for any supported engine.

**Naming Conventions:** Table names are lowercase, plural, and snake_cased. Primary keys are `id` with auto-increment. Foreign keys follow the pattern `referenced_table_singular_id`. Booleans use the `is_` prefix. Timestamps use `created_at` and `updated_at`. Enumerated values are stored as `TEXT` with application-level validation.

---

## 2. Schema Overview by Domain

The schema is organized into ten domains: Core Accounting, Financial Institutions and Accounts, Investments and Securities, Transactions and Journal Entries, Categories and Classification, Goals, Budgets, Reporting and Snapshots, Import and Reconciliation, and System and Configuration. A total of 37 tables are defined.

---

## 3. Core Accounting

### 3.1 `accounts` — Chart of Accounts

This is the backbone of the entire system. Every financial entity — a bank account, a credit card, an expense category, an income source, an investment holding — is represented as a node in this tree. The tree structure uses the adjacency list model via `parent_id`.

```sql
CREATE TABLE accounts (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_id           INTEGER,
    code                TEXT NOT NULL UNIQUE,
    name                TEXT NOT NULL,
    account_type        TEXT NOT NULL,
        -- ASSET, LIABILITY, INCOME, EXPENSE, EQUITY
    account_subtype     TEXT,
        -- BANK, CREDIT_CARD, LOAN, BROKERAGE, CASH,
        -- FIXED_DEPOSIT, RECURRING_DEPOSIT, PROVIDENT_FUND,
        -- FIXED_ASSET, RECEIVABLE, PAYABLE,
        -- MUTUAL_FUND, EQUITY_STOCK, ETF, BOND, GOLD,
        -- FO_MARGIN, SALARY, INTEREST, DIVIDEND, CAPITAL_GAIN,
        -- GENERAL, CUSTOM
    currency_code       TEXT NOT NULL DEFAULT 'INR',
    description         TEXT,
    is_active           INTEGER NOT NULL DEFAULT 1,
    is_system           INTEGER NOT NULL DEFAULT 0,
        -- 1 = created during onboarding/seeding, not deletable
    is_placeholder      INTEGER NOT NULL DEFAULT 0,
        -- 1 = group/parent node, cannot hold direct transactions
        -- 0 = leaf node, can hold transaction lines
    normal_balance      TEXT NOT NULL,
        -- DEBIT (for Asset, Expense) or CREDIT (for Liability, Income, Equity)
    display_order       INTEGER NOT NULL DEFAULT 0,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (parent_id) REFERENCES accounts(id),
    FOREIGN KEY (currency_code) REFERENCES currencies(code)
);

CREATE INDEX idx_accounts_parent ON accounts(parent_id);
CREATE INDEX idx_accounts_type ON accounts(account_type);
CREATE INDEX idx_accounts_subtype ON accounts(account_subtype);
CREATE INDEX idx_accounts_active ON accounts(is_active);
```

**Design Notes:** The `code` field uses a hierarchical numbering scheme. Root-level accounts use codes like 1000 (Assets), 2000 (Liabilities), 3000 (Income), 4000 (Expenses), 5000 (Equity). Children are numbered within their parent's range — 1100 for Cash and Bank, 1110 for Savings Accounts, and so on. The `is_placeholder` field distinguishes group nodes (which aggregate child balances) from leaf nodes (which directly participate in transactions). A bank account's corresponding leaf node in the Chart of Accounts will have `is_placeholder = 0` and will be linked from the `bank_accounts` table. The `normal_balance` field is determined by `account_type` and is used to compute display balances correctly — a debit to an asset account increases it, while a debit to a liability account decreases it.

---

### 3.2 `currencies`

Stores currency definitions. For MVP, only INR is active, but the table exists so that the schema does not require structural changes when multi-currency support is added.

```sql
CREATE TABLE currencies (
    code                TEXT PRIMARY KEY,
        -- ISO 4217: INR, USD, EUR, GBP, etc.
    name                TEXT NOT NULL,
    symbol              TEXT NOT NULL,
    decimal_places      INTEGER NOT NULL DEFAULT 2,
    is_active           INTEGER NOT NULL DEFAULT 1,
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### 3.3 `exchange_rates`

Historical exchange rate data for multi-currency support. Seeded with INR baseline. Stored as a time series.

```sql
CREATE TABLE exchange_rates (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    from_currency_code  TEXT NOT NULL,
    to_currency_code    TEXT NOT NULL,
    rate                REAL NOT NULL,
    rate_date           TEXT NOT NULL,
    source              TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (from_currency_code) REFERENCES currencies(code),
    FOREIGN KEY (to_currency_code) REFERENCES currencies(code)
);

CREATE UNIQUE INDEX idx_exchange_rates_pair_date
    ON exchange_rates(from_currency_code, to_currency_code, rate_date);
```

---

## 4. Financial Institutions and Accounts

### 4.1 `financial_institutions`

Master table for banks, brokerages, AMCs, NBFCs, and insurance companies the user has relationships with.

```sql
CREATE TABLE financial_institutions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    name                TEXT NOT NULL,
    institution_type    TEXT NOT NULL,
        -- BANK, BROKERAGE, AMC, NBFC, INSURANCE, COOPERATIVE, POST_OFFICE, OTHER
    logo_path           TEXT,
    website             TEXT,
    is_active           INTEGER NOT NULL DEFAULT 1,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### 4.2 `bank_accounts`

Extended metadata for bank accounts. Each record links to exactly one leaf node in the `accounts` table.

```sql
CREATE TABLE bank_accounts (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id          INTEGER NOT NULL UNIQUE,
        -- FK to accounts table (the CoA leaf node)
    institution_id      INTEGER NOT NULL,
    account_number_masked TEXT,
        -- last 4 digits or masked format: XXXX-XXXX-1234
    bank_account_type   TEXT NOT NULL,
        -- SAVINGS, CURRENT, SALARY, NRE, NRO, OVERDRAFT
    ifsc_code           TEXT,
    branch_name         TEXT,
    nominee_name        TEXT,
    opening_date        TEXT,
    is_primary          INTEGER NOT NULL DEFAULT 0,
    is_active           INTEGER NOT NULL DEFAULT 1,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (account_id) REFERENCES accounts(id),
    FOREIGN KEY (institution_id) REFERENCES financial_institutions(id)
);
```

### 4.3 `fixed_deposits`

Fixed deposits and recurring deposits have specific maturity and interest characteristics that distinguish them from regular bank accounts.

```sql
CREATE TABLE fixed_deposits (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id          INTEGER NOT NULL UNIQUE,
    institution_id      INTEGER NOT NULL,
    fd_number           TEXT,
    deposit_type        TEXT NOT NULL,
        -- FD, RD, TAX_SAVER_FD
    principal_amount    REAL NOT NULL,
    interest_rate       REAL NOT NULL,
    compounding_frequency TEXT NOT NULL DEFAULT 'QUARTERLY',
        -- MONTHLY, QUARTERLY, HALF_YEARLY, YEARLY, ON_MATURITY
    deposit_date        TEXT NOT NULL,
    maturity_date       TEXT NOT NULL,
    maturity_amount     REAL,
    auto_renew          INTEGER NOT NULL DEFAULT 0,
    linked_bank_account_id INTEGER,
        -- FK to bank_accounts for interest credit
    is_active           INTEGER NOT NULL DEFAULT 1,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (account_id) REFERENCES accounts(id),
    FOREIGN KEY (institution_id) REFERENCES financial_institutions(id),
    FOREIGN KEY (linked_bank_account_id) REFERENCES bank_accounts(id)
);
```

### 4.4 `credit_cards`

```sql
CREATE TABLE credit_cards (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id          INTEGER NOT NULL UNIQUE,
    institution_id      INTEGER NOT NULL,
    card_number_masked  TEXT,
        -- last 4 digits only
    card_network        TEXT,
        -- VISA, MASTERCARD, RUPAY, AMEX, DINERS
    card_variant        TEXT,
        -- BASIC, GOLD, PLATINUM, SIGNATURE, INFINITE, CUSTOM
    credit_limit        REAL,
    billing_cycle_day   INTEGER,
        -- day of month when statement is generated (1-28)
    payment_due_day     INTEGER,
        -- day of month when payment is due
    annual_fee          REAL DEFAULT 0,
    reward_program_name TEXT,
    is_active           INTEGER NOT NULL DEFAULT 1,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (account_id) REFERENCES accounts(id),
    FOREIGN KEY (institution_id) REFERENCES financial_institutions(id)
);
```

### 4.5 `loans`

```sql
CREATE TABLE loans (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id          INTEGER NOT NULL UNIQUE,
        -- FK to accounts (a LIABILITY leaf node)
    institution_id      INTEGER NOT NULL,
    loan_account_number TEXT,
    loan_type           TEXT NOT NULL,
        -- HOME, PERSONAL, CAR, EDUCATION, GOLD, LAP, CONSUMER_DURABLE, OTHER
    principal_amount    REAL NOT NULL,
    current_outstanding REAL,
        -- denormalized; recomputed from transaction history
    interest_rate       REAL NOT NULL,
    interest_type       TEXT NOT NULL DEFAULT 'FLOATING',
        -- FIXED, FLOATING, HYBRID
    tenure_months       INTEGER NOT NULL,
    emi_amount          REAL,
    disbursement_date   TEXT,
    emi_start_date      TEXT,
    expected_end_date   TEXT,
    linked_asset_account_id INTEGER,
        -- FK to accounts; e.g., home loan links to the house asset account
    prepayment_charges_applicable INTEGER DEFAULT 0,
    is_active           INTEGER NOT NULL DEFAULT 1,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (account_id) REFERENCES accounts(id),
    FOREIGN KEY (institution_id) REFERENCES financial_institutions(id),
    FOREIGN KEY (linked_asset_account_id) REFERENCES accounts(id)
);
```

**Design Note on EMI Transactions:** When an EMI is recorded, the transaction has at least three lines: a debit to the loan account (principal repayment reducing the liability), a debit to an interest expense account (interest component), and a credit to the bank account (total EMI outflow). The split between principal and interest changes each month per the amortization schedule. The `recurring_transactions` table stores the EMI template, and the application computes the principal-interest split for each occurrence.

### 4.6 `brokerage_accounts`

```sql
CREATE TABLE brokerage_accounts (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id          INTEGER NOT NULL UNIQUE,
    institution_id      INTEGER NOT NULL,
    account_identifier  TEXT,
        -- demat number, trading ID, or MF folio number
    brokerage_account_type TEXT NOT NULL,
        -- DEMAT, TRADING, MF_FOLIO, NPS, PMS
    depository          TEXT,
        -- CDSL, NSDL, NA
    is_active           INTEGER NOT NULL DEFAULT 1,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (account_id) REFERENCES accounts(id),
    FOREIGN KEY (institution_id) REFERENCES financial_institutions(id)
);
```

---

## 5. Investments and Securities

### 5.1 `securities`

Master reference table for all investable instruments — equities, mutual funds, ETFs, bonds, sovereign gold bonds, REITs, InvITs.

```sql
CREATE TABLE securities (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol              TEXT,
        -- BSE/NSE ticker symbol; NULL for mutual funds
    isin                TEXT UNIQUE,
        -- International Securities Identification Number
    name                TEXT NOT NULL,
    security_type       TEXT NOT NULL,
        -- EQUITY, MUTUAL_FUND, ETF, BOND, GOVT_SECURITY,
        -- SOVEREIGN_GOLD_BOND, REIT, INVIT, NPS_SCHEME
    exchange            TEXT,
        -- NSE, BSE, NA (for mutual funds)
    sector              TEXT,
    industry            TEXT,
    mf_category         TEXT,
        -- EQUITY_LARGE_CAP, EQUITY_MID_CAP, EQUITY_SMALL_CAP,
        -- EQUITY_FLEXI_CAP, EQUITY_ELSS, DEBT_LIQUID,
        -- DEBT_SHORT_DURATION, DEBT_GILT, HYBRID_AGGRESSIVE,
        -- HYBRID_CONSERVATIVE, INDEX_FUND, SECTORAL, INTERNATIONAL
    mf_amc              TEXT,
        -- AMC name for mutual funds
    mf_plan             TEXT,
        -- DIRECT, REGULAR
    mf_option           TEXT,
        -- GROWTH, IDCW_PAYOUT, IDCW_REINVEST
    face_value          REAL,
    lot_size            INTEGER DEFAULT 1,
        -- trading lot size; relevant for F&O underliers
    is_active           INTEGER NOT NULL DEFAULT 1,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_securities_type ON securities(security_type);
CREATE INDEX idx_securities_symbol ON securities(symbol);
```

### 5.2 `security_prices`

Time-series price and NAV data. This table is append-only and can grow large. The application fetches prices periodically or allows manual entry.

```sql
CREATE TABLE security_prices (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    security_id         INTEGER NOT NULL,
    price_date          TEXT NOT NULL,
    close_price         REAL NOT NULL,
        -- closing price for stocks; NAV for mutual funds
    open_price          REAL,
    high_price          REAL,
    low_price           REAL,
    volume              INTEGER,
    source              TEXT,
        -- MANUAL, API_BSE, API_NSE, API_AMFI, IMPORTED
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (security_id) REFERENCES securities(id)
);

CREATE UNIQUE INDEX idx_security_prices_date
    ON security_prices(security_id, price_date);
CREATE INDEX idx_security_prices_security ON security_prices(security_id);
```

### 5.3 `tax_lots`

Tracks individual purchase lots for cost basis computation. Supports FIFO, specific identification, and average cost methods. Each buy transaction creates a new lot. Each sell transaction depletes one or more lots based on the chosen cost basis method.

```sql
CREATE TABLE tax_lots (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    security_id         INTEGER NOT NULL,
    brokerage_account_id INTEGER NOT NULL,
    buy_transaction_id  INTEGER NOT NULL,
        -- FK to transactions — the purchase entry
    acquisition_date    TEXT NOT NULL,
    quantity            REAL NOT NULL,
        -- original quantity purchased
    cost_per_unit       REAL NOT NULL,
        -- purchase price per unit
    acquisition_cost    REAL NOT NULL,
        -- total cost including brokerage, STT, GST, stamp duty
    remaining_quantity  REAL NOT NULL,
        -- decreases as units are sold
    status              TEXT NOT NULL DEFAULT 'OPEN',
        -- OPEN, PARTIALLY_CLOSED, CLOSED
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (security_id) REFERENCES securities(id),
    FOREIGN KEY (brokerage_account_id) REFERENCES brokerage_accounts(id),
    FOREIGN KEY (buy_transaction_id) REFERENCES transactions(id)
);

CREATE INDEX idx_tax_lots_security ON tax_lots(security_id, status);
CREATE INDEX idx_tax_lots_brokerage ON tax_lots(brokerage_account_id);
```

### 5.4 `tax_lot_disposals`

When a sell transaction depletes one or more tax lots, this table records which lots were consumed and in what quantity. This is essential for capital gains computation, as different lots may have different acquisition dates (affecting STCG vs. LTCG classification) and different costs.

```sql
CREATE TABLE tax_lot_disposals (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    tax_lot_id          INTEGER NOT NULL,
    sell_transaction_id INTEGER NOT NULL,
    disposal_date       TEXT NOT NULL,
    quantity_disposed   REAL NOT NULL,
    sale_price_per_unit REAL NOT NULL,
    sale_proceeds       REAL NOT NULL,
        -- net of brokerage, STT, GST, stamp duty
    cost_of_acquisition REAL NOT NULL,
        -- proportional cost from the tax lot
    realized_gain_loss  REAL NOT NULL,
        -- sale_proceeds - cost_of_acquisition
    holding_period_days INTEGER NOT NULL,
    gain_type           TEXT NOT NULL,
        -- STCG, LTCG (determined by holding period and security type)
    grandfathering_applicable INTEGER DEFAULT 0,
        -- for equity shares held before Jan 31, 2018
    grandfathered_cost  REAL,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (tax_lot_id) REFERENCES tax_lots(id),
    FOREIGN KEY (sell_transaction_id) REFERENCES transactions(id)
);

CREATE INDEX idx_disposals_sell_txn ON tax_lot_disposals(sell_transaction_id);
CREATE INDEX idx_disposals_lot ON tax_lot_disposals(tax_lot_id);
```

### 5.5 `fo_contracts`

Defines F&O contract specifications. Each unique futures or options contract (identified by underlying, expiry, strike, and type) gets one row.

```sql
CREATE TABLE fo_contracts (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    underlying_security_id INTEGER NOT NULL,
    contract_type       TEXT NOT NULL,
        -- FUTURES, CALL_OPTION, PUT_OPTION
    expiry_date         TEXT NOT NULL,
    strike_price        REAL,
        -- NULL for futures
    lot_size            INTEGER NOT NULL,
    exchange            TEXT NOT NULL DEFAULT 'NSE',
    contract_symbol     TEXT NOT NULL,
        -- e.g., NIFTY24MAR22000CE, RELIANCE24APRFUT
    is_active           INTEGER NOT NULL DEFAULT 1,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (underlying_security_id) REFERENCES securities(id)
);

CREATE UNIQUE INDEX idx_fo_contracts_symbol ON fo_contracts(contract_symbol);
CREATE INDEX idx_fo_contracts_expiry ON fo_contracts(expiry_date);
```

### 5.6 `fo_positions`

Tracks F&O positions from entry to exit. A position represents a directional exposure opened by one trade and closed by another (or by expiry).

```sql
CREATE TABLE fo_positions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    fo_contract_id      INTEGER NOT NULL,
    brokerage_account_id INTEGER NOT NULL,
    position_type       TEXT NOT NULL,
        -- LONG, SHORT
    quantity_lots       INTEGER NOT NULL,
    quantity_units      INTEGER NOT NULL,
        -- lots × lot_size
    entry_price         REAL NOT NULL,
    entry_date          TEXT NOT NULL,
    entry_transaction_id INTEGER NOT NULL,
    exit_price          REAL,
    exit_date           TEXT,
    exit_transaction_id INTEGER,
    margin_blocked      REAL DEFAULT 0,
    premium_paid        REAL DEFAULT 0,
        -- for option buyers
    premium_received    REAL DEFAULT 0,
        -- for option sellers
    realized_pnl        REAL,
        -- computed on position close or expiry
    settlement_type     TEXT,
        -- SQUARED_OFF, EXERCISED, EXPIRED_OTM, EXPIRED_ITM, PHYSICAL_DELIVERY
    status              TEXT NOT NULL DEFAULT 'OPEN',
        -- OPEN, CLOSED
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (fo_contract_id) REFERENCES fo_contracts(id),
    FOREIGN KEY (brokerage_account_id) REFERENCES brokerage_accounts(id),
    FOREIGN KEY (entry_transaction_id) REFERENCES transactions(id),
    FOREIGN KEY (exit_transaction_id) REFERENCES transactions(id)
);

CREATE INDEX idx_fo_positions_status ON fo_positions(status);
CREATE INDEX idx_fo_positions_contract ON fo_positions(fo_contract_id);
```

### 5.7 `holdings_summary`

Denormalized aggregate table computed from `tax_lots`. Rebuilt on each transaction affecting holdings. Provides fast lookup for portfolio views and reports without scanning all open tax lots.

```sql
CREATE TABLE holdings_summary (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    security_id         INTEGER NOT NULL,
    brokerage_account_id INTEGER NOT NULL,
    account_id          INTEGER NOT NULL,
        -- the CoA leaf node for this holding
    total_quantity      REAL NOT NULL,
    average_cost_per_unit REAL NOT NULL,
    total_invested_value REAL NOT NULL,
    latest_price        REAL,
    latest_price_date   TEXT,
    current_market_value REAL,
    unrealized_pnl      REAL,
    unrealized_pnl_pct  REAL,
    absolute_return_pct REAL,
    day_change          REAL,
    day_change_pct      REAL,
    last_recomputed_at  TEXT NOT NULL,

    FOREIGN KEY (security_id) REFERENCES securities(id),
    FOREIGN KEY (brokerage_account_id) REFERENCES brokerage_accounts(id),
    FOREIGN KEY (account_id) REFERENCES accounts(id)
);

CREATE UNIQUE INDEX idx_holdings_security_brokerage
    ON holdings_summary(security_id, brokerage_account_id);
```

---

## 6. Transactions and Journal Entries

### 6.1 `transactions`

The header table for every financial event in the system. A transaction represents a single economic event — a purchase, a salary credit, a fund transfer, an SIP execution, an EMI payment, an F&O trade. Every transaction must have two or more balanced lines in the `transaction_lines` table.

```sql
CREATE TABLE transactions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_date    TEXT NOT NULL,
        -- the date the event occurred
    effective_date      TEXT,
        -- value date; defaults to transaction_date if NULL
    transaction_number  TEXT UNIQUE,
        -- system-generated sequential reference (e.g., TXN-2026-00001)
    transaction_type    TEXT NOT NULL,
        -- EXPENSE, INCOME, TRANSFER, INVESTMENT_BUY, INVESTMENT_SELL,
        -- INVESTMENT_DIVIDEND, INVESTMENT_BONUS, INVESTMENT_SPLIT,
        -- SIP_PURCHASE, EMI_PAYMENT, FO_BUY, FO_SELL, FO_EXPIRY,
        -- INTEREST_CREDIT, INTEREST_DEBIT, OPENING_BALANCE,
        -- ADJUSTMENT, REVERSAL, CREDIT_CARD_PAYMENT, TAX_PAYMENT
    description         TEXT NOT NULL,
    payee_id            INTEGER,
    reference_number    TEXT,
        -- UPI ref, cheque number, bank transaction ID, etc.
    status              TEXT NOT NULL DEFAULT 'CONFIRMED',
        -- PENDING, CONFIRMED, VOID, RECONCILED
    is_void             INTEGER NOT NULL DEFAULT 0,
    void_reason         TEXT,
    voided_at           TEXT,
    reversal_of_transaction_id INTEGER,
        -- if this transaction reverses another, link to the original
    import_batch_id     INTEGER,
        -- FK to import_batches; NULL for manually entered transactions
    recurring_transaction_id INTEGER,
        -- FK to recurring_transactions; set if generated from a template
    notes               TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (payee_id) REFERENCES payees(id),
    FOREIGN KEY (import_batch_id) REFERENCES import_batches(id),
    FOREIGN KEY (recurring_transaction_id) REFERENCES recurring_transactions(id),
    FOREIGN KEY (reversal_of_transaction_id) REFERENCES transactions(id)
);

CREATE INDEX idx_transactions_date ON transactions(transaction_date);
CREATE INDEX idx_transactions_type ON transactions(transaction_type);
CREATE INDEX idx_transactions_status ON transactions(status);
CREATE INDEX idx_transactions_payee ON transactions(payee_id);
CREATE INDEX idx_transactions_import ON transactions(import_batch_id);
CREATE INDEX idx_transactions_recurring ON transactions(recurring_transaction_id);
```

### 6.2 `transaction_lines`

The individual debit and credit legs of a transaction. For every transaction, the sum of all DEBIT amounts must equal the sum of all CREDIT amounts. This is the core double-entry constraint, enforced at the application level.

```sql
CREATE TABLE transaction_lines (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id      INTEGER NOT NULL,
    account_id          INTEGER NOT NULL,
        -- which CoA account this line hits
    line_type           TEXT NOT NULL,
        -- DEBIT or CREDIT
    amount              REAL NOT NULL,
        -- always positive; direction determined by line_type
    description         TEXT,
        -- optional line-level narration
    security_id         INTEGER,
        -- populated for investment transaction lines
    quantity            REAL,
        -- number of units/shares for investment lines
    price_per_unit      REAL,
        -- per-unit price for investment lines
    tax_lot_id          INTEGER,
        -- for sell lines, references the specific lot being disposed
    currency_code       TEXT NOT NULL DEFAULT 'INR',
    exchange_rate       REAL NOT NULL DEFAULT 1.0,
        -- conversion rate to base currency (INR)
    display_order       INTEGER NOT NULL DEFAULT 0,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (transaction_id) REFERENCES transactions(id),
    FOREIGN KEY (account_id) REFERENCES accounts(id),
    FOREIGN KEY (security_id) REFERENCES securities(id),
    FOREIGN KEY (tax_lot_id) REFERENCES tax_lots(id)
);

CREATE INDEX idx_txn_lines_transaction ON transaction_lines(transaction_id);
CREATE INDEX idx_txn_lines_account ON transaction_lines(account_id);
CREATE INDEX idx_txn_lines_security ON transaction_lines(security_id);
CREATE INDEX idx_txn_lines_account_date ON transaction_lines(account_id);
    -- for efficient balance queries; compound index with transaction date
    -- achieved via join with transactions table
```

**How Common Transactions Map to Lines:**

A grocery purchase of ₹2,000 paid from HDFC Savings creates two lines: a DEBIT to Expenses → Food → Groceries for ₹2,000, and a CREDIT to Assets → HDFC Savings for ₹2,000.

A salary credit of ₹1,00,000 with ₹80,000 net, ₹12,000 TDS, ₹5,000 PF, and ₹3,000 professional tax creates five lines: a DEBIT to Assets → HDFC Savings for ₹80,000, a DEBIT to Assets → EPF for ₹5,000, a DEBIT to Expenses → Tax Paid (TDS) for ₹12,000, a DEBIT to Expenses → Professional Tax for ₹3,000, and a CREDIT to Income → Salary for ₹1,00,000.

An EMI payment of ₹25,000 where ₹18,000 is principal and ₹7,000 is interest creates three lines: a DEBIT to Liabilities → Home Loan for ₹18,000 (reducing the liability), a DEBIT to Expenses → Interest Paid for ₹7,000, and a CREDIT to Assets → SBI Savings for ₹25,000.

A mutual fund SIP purchase of ₹10,000 for 50.25 units at NAV ₹199.00 creates two lines: a DEBIT to Assets → Investments → Mutual Funds (with security_id, quantity=50.25, price_per_unit=199.00) for ₹10,000, and a CREDIT to Assets → HDFC Savings for ₹10,000.

### 6.3 `transaction_charges`

Investment transactions in India carry multiple charges — brokerage, STT, exchange transaction charges, GST, SEBI turnover fees, stamp duty. Rather than embedding all of these as columns in `transaction_lines`, this table stores them separately and links them to the transaction. The total charges are summed into the `acquisition_cost` of the relevant `tax_lot`.

```sql
CREATE TABLE transaction_charges (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id      INTEGER NOT NULL,
    charge_type         TEXT NOT NULL,
        -- BROKERAGE, STT, EXCHANGE_TXN_CHARGE, GST,
        -- SEBI_TURNOVER_FEE, STAMP_DUTY, DP_CHARGES,
        -- EXIT_LOAD, CLEARING_CHARGE, OTHER
    amount              REAL NOT NULL,
    description         TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (transaction_id) REFERENCES transactions(id)
);

CREATE INDEX idx_txn_charges_transaction ON transaction_charges(transaction_id);
```

### 6.4 `attachments`

Receipts, invoices, bank statements, and other documents linked to transactions.

```sql
CREATE TABLE attachments (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id      INTEGER NOT NULL,
    file_name           TEXT NOT NULL,
    file_path           TEXT NOT NULL,
        -- local filesystem path
    file_type           TEXT NOT NULL,
        -- PDF, JPG, PNG, HEIC, WEBP
    file_size_bytes     INTEGER,
    description         TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (transaction_id) REFERENCES transactions(id)
);

CREATE INDEX idx_attachments_transaction ON attachments(transaction_id);
```

---

## 7. Categories, Tags, and Payees

### 7.1 `payees`

Merchants, employers, service providers, and individuals the user transacts with. When a payee is recognized (either by name match during import or by user selection), the system can auto-suggest the default expense/income category.

```sql
CREATE TABLE payees (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    name                TEXT NOT NULL,
    default_account_id  INTEGER,
        -- default CoA account to use when this payee is selected
        -- e.g., Swiggy defaults to Expenses → Food → Food Delivery
    payee_type          TEXT DEFAULT 'OTHER',
        -- MERCHANT, EMPLOYER, INDIVIDUAL, GOVERNMENT, UTILITY, OTHER
    notes               TEXT,
    is_active           INTEGER NOT NULL DEFAULT 1,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (default_account_id) REFERENCES accounts(id)
);

CREATE INDEX idx_payees_name ON payees(name);
```

### 7.2 `tags`

User-defined labels that cut across the Chart of Accounts hierarchy. A transaction can have multiple tags. Tags enable analytical dimensions that do not map to the account tree — for example, tagging expenses as "Vacation-Goa-2026" or "Wedding-Prep" across multiple expense categories.

```sql
CREATE TABLE tags (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    name                TEXT NOT NULL UNIQUE,
    color               TEXT,
        -- hex color code for UI display: #FF5733
    is_active           INTEGER NOT NULL DEFAULT 1,
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### 7.3 `transaction_tags`

Many-to-many join table between transactions and tags.

```sql
CREATE TABLE transaction_tags (
    transaction_id      INTEGER NOT NULL,
    tag_id              INTEGER NOT NULL,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),

    PRIMARY KEY (transaction_id, tag_id),
    FOREIGN KEY (transaction_id) REFERENCES transactions(id),
    FOREIGN KEY (tag_id) REFERENCES tags(id)
);
```

---

## 8. Recurring Transactions

### 8.1 `recurring_transactions`

Templates for transactions that repeat on a schedule — SIPs, EMIs, rent, subscriptions, salary, utility bills. The application engine uses this table to generate pending transaction instances as their scheduled dates approach.

```sql
CREATE TABLE recurring_transactions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    template_name       TEXT NOT NULL,
        -- user-readable name: "Monthly Rent", "Axis Bluechip SIP"
    transaction_type    TEXT NOT NULL,
    description         TEXT,
    payee_id            INTEGER,
    estimated_amount    REAL,
        -- expected amount; actual may vary (e.g., utility bills)
    is_amount_fixed     INTEGER NOT NULL DEFAULT 1,
        -- 1 = exact amount every time, 0 = amount varies
    frequency           TEXT NOT NULL,
        -- DAILY, WEEKLY, BIWEEKLY, MONTHLY, QUARTERLY,
        -- HALF_YEARLY, YEARLY, CUSTOM
    interval_value      INTEGER NOT NULL DEFAULT 1,
        -- every N frequency units; e.g., interval=2 + frequency=MONTHLY = bimonthly
    day_of_month        INTEGER,
        -- for MONTHLY: which day (1-28)
    day_of_week         INTEGER,
        -- for WEEKLY: 0=Monday through 6=Sunday
    month_of_year       INTEGER,
        -- for YEARLY: which month (1-12)
    start_date          TEXT NOT NULL,
    end_date            TEXT,
        -- NULL = indefinite
    next_occurrence_date TEXT NOT NULL,
    last_generated_date TEXT,
    total_occurrences   INTEGER,
        -- NULL = unlimited; set for fixed-count (e.g., EMI for 240 months)
    completed_occurrences INTEGER NOT NULL DEFAULT 0,
    auto_confirm        INTEGER NOT NULL DEFAULT 0,
        -- 1 = auto-create confirmed transaction
        -- 0 = create as PENDING, user must confirm
    security_id         INTEGER,
        -- for SIP recurring entries
    sip_units           REAL,
        -- NULL = amount-based SIP, populated = unit-based
    goal_id             INTEGER,
        -- if this recurring entry is linked to a goal
    is_active           INTEGER NOT NULL DEFAULT 1,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (payee_id) REFERENCES payees(id),
    FOREIGN KEY (security_id) REFERENCES securities(id),
    FOREIGN KEY (goal_id) REFERENCES goals(id)
);
```

### 8.2 `recurring_transaction_lines`

Template lines for the recurring transaction. Mirrors `transaction_lines` structure but stores the template rather than actual entries. When the engine generates a transaction instance, it copies these lines into `transaction_lines`.

```sql
CREATE TABLE recurring_transaction_lines (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    recurring_transaction_id INTEGER NOT NULL,
    account_id          INTEGER NOT NULL,
    line_type           TEXT NOT NULL,
        -- DEBIT or CREDIT
    amount              REAL NOT NULL,
    description         TEXT,
    display_order       INTEGER NOT NULL DEFAULT 0,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (recurring_transaction_id) REFERENCES recurring_transactions(id),
    FOREIGN KEY (account_id) REFERENCES accounts(id)
);
```

---

## 9. Goals

### 9.1 `goals`

```sql
CREATE TABLE goals (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    name                TEXT NOT NULL,
    goal_type           TEXT NOT NULL,
        -- EMERGENCY_FUND, RETIREMENT, HOME_PURCHASE, VEHICLE,
        -- EDUCATION, WEDDING, VACATION, DEBT_PAYOFF,
        -- INVESTMENT_TARGET, CUSTOM
    target_amount       REAL NOT NULL,
    current_amount      REAL NOT NULL DEFAULT 0,
        -- denormalized; recomputed from linked accounts and contributions
    target_date         TEXT,
    start_date          TEXT NOT NULL,
    priority            TEXT NOT NULL DEFAULT 'MEDIUM',
        -- HIGH, MEDIUM, LOW
    status              TEXT NOT NULL DEFAULT 'ACTIVE',
        -- ACTIVE, PAUSED, ACHIEVED, ABANDONED
    icon                TEXT,
    color               TEXT,
    sip_amount          REAL,
        -- suggested monthly contribution to stay on track
    expected_return_rate REAL,
        -- assumed annual return rate for projection calculations
    notes               TEXT,
    achieved_date       TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### 9.2 `goal_account_mappings`

Links CoA accounts to goals. A single account can be mapped to multiple goals with allocation percentages. For example, a mutual fund account might be 60% allocated to the Retirement goal and 40% to the Home Purchase goal.

```sql
CREATE TABLE goal_account_mappings (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    goal_id             INTEGER NOT NULL,
    account_id          INTEGER NOT NULL,
    allocation_percentage REAL NOT NULL DEFAULT 100.0,
        -- what percentage of this account's balance counts toward this goal
        -- sum of all allocations for one account across all goals should not exceed 100
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (goal_id) REFERENCES goals(id),
    FOREIGN KEY (account_id) REFERENCES accounts(id)
);

CREATE UNIQUE INDEX idx_goal_account ON goal_account_mappings(goal_id, account_id);
```

### 9.3 `goal_milestones`

Sub-targets within a goal that provide intermediate markers of progress.

```sql
CREATE TABLE goal_milestones (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    goal_id             INTEGER NOT NULL,
    name                TEXT NOT NULL,
    target_amount       REAL NOT NULL,
    target_date         TEXT,
    achieved_date       TEXT,
    status              TEXT NOT NULL DEFAULT 'PENDING',
        -- PENDING, ACHIEVED
    display_order       INTEGER NOT NULL DEFAULT 0,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (goal_id) REFERENCES goals(id)
);
```

### 9.4 `goal_contributions`

Tracks individual contributions toward a goal, linked back to the actual transaction when possible. Supports both manually recorded contributions and auto-detected ones (when a transaction hits a goal-linked account).

```sql
CREATE TABLE goal_contributions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    goal_id             INTEGER NOT NULL,
    transaction_id      INTEGER,
        -- NULL for manually tracked contributions without a matching transaction
    amount              REAL NOT NULL,
    contribution_date   TEXT NOT NULL,
    contribution_type   TEXT NOT NULL DEFAULT 'MANUAL',
        -- MANUAL, AUTO_DETECTED, SIP, LUMP_SUM
    notes               TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (goal_id) REFERENCES goals(id),
    FOREIGN KEY (transaction_id) REFERENCES transactions(id)
);

CREATE INDEX idx_goal_contributions_goal ON goal_contributions(goal_id);
```

---

## 10. Budgets

### 10.1 `budgets`

A budget defines spending limits for a specific time period. The system supports monthly, quarterly, and yearly budgets. A monthly recurring budget automatically spawns the next month's budget as the current period ends.

```sql
CREATE TABLE budgets (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    name                TEXT NOT NULL,
    period_type         TEXT NOT NULL,
        -- MONTHLY, QUARTERLY, YEARLY, CUSTOM
    start_date          TEXT NOT NULL,
    end_date            TEXT NOT NULL,
    total_budgeted      REAL NOT NULL DEFAULT 0,
        -- sum of all budget_items; denormalized
    total_spent         REAL NOT NULL DEFAULT 0,
        -- denormalized; recomputed from transactions
    is_active           INTEGER NOT NULL DEFAULT 1,
    is_recurring        INTEGER NOT NULL DEFAULT 0,
        -- auto-create next period's budget from this template
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_budgets_period ON budgets(start_date, end_date);
```

### 10.2 `budget_items`

Individual line items within a budget, each mapping to an expense category account.

```sql
CREATE TABLE budget_items (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    budget_id           INTEGER NOT NULL,
    account_id          INTEGER NOT NULL,
        -- FK to an expense category account in CoA
    budgeted_amount     REAL NOT NULL,
    spent_amount        REAL NOT NULL DEFAULT 0,
        -- denormalized; recomputed from transactions in this period
    rollover_amount     REAL NOT NULL DEFAULT 0,
        -- unused amount carried over from previous period
    rollover_unused     INTEGER NOT NULL DEFAULT 0,
        -- whether to carry forward unused budget to next period
    alert_threshold_pct REAL DEFAULT 80.0,
        -- notify user when this percentage is reached
    notes               TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (budget_id) REFERENCES budgets(id),
    FOREIGN KEY (account_id) REFERENCES accounts(id)
);

CREATE INDEX idx_budget_items_budget ON budget_items(budget_id);
CREATE UNIQUE INDEX idx_budget_items_account ON budget_items(budget_id, account_id);
```

---

## 11. Reporting and Snapshots

### 11.1 `monthly_snapshots`

Pre-computed monthly balance snapshots for every account. Dramatically accelerates report generation. Without this table, computing the balance of an account on any given date requires summing all transaction lines from inception. With snapshots, the system finds the nearest prior snapshot and sums only the delta.

```sql
CREATE TABLE monthly_snapshots (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id          INTEGER NOT NULL,
    snapshot_year       INTEGER NOT NULL,
    snapshot_month      INTEGER NOT NULL,
        -- 1-12
    opening_balance     REAL NOT NULL,
        -- balance at the start of the month
    total_debits        REAL NOT NULL DEFAULT 0,
    total_credits       REAL NOT NULL DEFAULT 0,
    closing_balance     REAL NOT NULL,
        -- balance at the end of the month
    transaction_count   INTEGER NOT NULL DEFAULT 0,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (account_id) REFERENCES accounts(id)
);

CREATE UNIQUE INDEX idx_monthly_snapshots_account_period
    ON monthly_snapshots(account_id, snapshot_year, snapshot_month);
```

**Computation Logic:** Closing balance for DEBIT-normal accounts (Assets, Expenses) is: `opening_balance + total_debits - total_credits`. For CREDIT-normal accounts (Liabilities, Income, Equity): `opening_balance + total_credits - total_debits`. The snapshot for month M uses the closing balance of month M-1 as its opening balance.

### 11.2 `net_worth_history`

A daily or periodic snapshot of aggregate net worth. While this can be computed from `monthly_snapshots`, storing it explicitly enables fast net worth trend charts without recomputation.

```sql
CREATE TABLE net_worth_history (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_date       TEXT NOT NULL,
    total_assets        REAL NOT NULL,
    total_liabilities   REAL NOT NULL,
    net_worth           REAL NOT NULL,
    liquid_assets       REAL,
        -- cash + bank + liquid investments
    investment_value    REAL,
        -- total market value of all investments
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX idx_net_worth_date ON net_worth_history(snapshot_date);
```

### 11.3 `saved_reports`

User-saved report configurations — filters, date ranges, groupings, and display preferences — so that frequently accessed reports can be recalled without reconfiguring.

```sql
CREATE TABLE saved_reports (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    name                TEXT NOT NULL,
    report_type         TEXT NOT NULL,
        -- NET_WORTH, INCOME_EXPENSE, CASH_FLOW, BALANCE_SHEET,
        -- TRIAL_BALANCE, INVESTMENT_PERFORMANCE, GOAL_PROGRESS,
        -- TAX_SUMMARY, CATEGORY_ANALYSIS, TREND_ANALYSIS,
        -- FO_PNL, DIVIDEND_REPORT, CUSTOM
    parameters_json     TEXT NOT NULL,
        -- JSON blob containing all report configuration:
        -- date_range, accounts, grouping, filters, comparison_periods, etc.
    is_favorite         INTEGER NOT NULL DEFAULT 0,
    last_run_at         TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);
```

---

## 12. Import and Reconciliation

### 12.1 `import_profiles`

Templates that define how to parse and map data from external sources — bank CSV statements, brokerage tradebooks, mutual fund CAS PDFs.

```sql
CREATE TABLE import_profiles (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    name                TEXT NOT NULL,
        -- "HDFC Bank Savings CSV", "Zerodha Tradebook", "CAMS CAS"
    institution_id      INTEGER,
    source_type         TEXT NOT NULL,
        -- BANK_STATEMENT, CREDIT_CARD_STATEMENT, BROKERAGE_TRADEBOOK,
        -- MF_CAS, NPS_STATEMENT, MANUAL_CSV
    file_format         TEXT NOT NULL,
        -- CSV, XLSX, PDF, OFX, QIF
    column_mapping_json TEXT,
        -- JSON defining source-to-system field mapping:
        -- {"date_column": "Transaction Date", "amount_column": "Amount",
        --  "description_column": "Narration", "debit_column": "Withdrawal",
        --  "credit_column": "Deposit", "balance_column": "Balance"}
    date_format         TEXT DEFAULT 'DD/MM/YYYY',
    delimiter           TEXT DEFAULT ',',
    skip_header_rows    INTEGER DEFAULT 1,
    skip_footer_rows    INTEGER DEFAULT 0,
    encoding            TEXT DEFAULT 'UTF-8',
    notes               TEXT,
    is_active           INTEGER NOT NULL DEFAULT 1,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (institution_id) REFERENCES financial_institutions(id)
);
```

### 12.2 `import_batches`

Tracks each import operation — what was imported, when, from where, and what happened.

```sql
CREATE TABLE import_batches (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    import_profile_id   INTEGER,
    file_name           TEXT NOT NULL,
    file_hash           TEXT,
        -- SHA-256 hash to detect re-import of same file
    source_type         TEXT NOT NULL,
    import_started_at   TEXT NOT NULL,
    import_completed_at TEXT,
    status              TEXT NOT NULL DEFAULT 'IN_PROGRESS',
        -- IN_PROGRESS, COMPLETED, FAILED, PARTIALLY_COMPLETED, ROLLED_BACK
    total_records       INTEGER DEFAULT 0,
    imported_count      INTEGER DEFAULT 0,
    duplicate_count     INTEGER DEFAULT 0,
    skipped_count       INTEGER DEFAULT 0,
    error_count         INTEGER DEFAULT 0,
    error_log           TEXT,
        -- JSON array of error details per record
    target_account_id   INTEGER,
        -- the primary CoA account being imported into
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (import_profile_id) REFERENCES import_profiles(id),
    FOREIGN KEY (target_account_id) REFERENCES accounts(id)
);
```

### 12.3 `reconciliation_records`

When a bank statement is imported, each incoming record goes through reconciliation — matching against existing transactions or creating new ones. This table tracks the outcome of each record in the reconciliation process.

```sql
CREATE TABLE reconciliation_records (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    import_batch_id     INTEGER NOT NULL,
    external_date       TEXT NOT NULL,
    external_description TEXT NOT NULL,
    external_amount     REAL NOT NULL,
    external_reference  TEXT,
    external_balance    REAL,
    match_status        TEXT NOT NULL DEFAULT 'UNMATCHED',
        -- MATCHED, UNMATCHED, DUPLICATE, SKIPPED, MANUAL_MATCH
    matched_transaction_id INTEGER,
        -- FK to existing transaction if matched
    created_transaction_id INTEGER,
        -- FK to newly created transaction if unmatched and confirmed
    confidence_score    REAL,
        -- 0.0 to 1.0; matching algorithm confidence
    user_action         TEXT,
        -- CONFIRMED, REJECTED, MERGED, PENDING
    processed_at        TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (import_batch_id) REFERENCES import_batches(id),
    FOREIGN KEY (matched_transaction_id) REFERENCES transactions(id),
    FOREIGN KEY (created_transaction_id) REFERENCES transactions(id)
);

CREATE INDEX idx_reconciliation_batch ON reconciliation_records(import_batch_id);
CREATE INDEX idx_reconciliation_status ON reconciliation_records(match_status);
```

---

## 13. Tax Management

### 13.1 `tax_sections`

Indian Income Tax deduction sections with their limits. Seeded with standard sections and updated for each financial year.

```sql
CREATE TABLE tax_sections (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    section_code        TEXT NOT NULL,
        -- 80C, 80CCC, 80CCD_1, 80CCD_1B, 80CCD_2,
        -- 80D, 80E, 80G, 80GG, 80TTA, 80TTB,
        -- 24B, 10_14, HRA
    name                TEXT NOT NULL,
    description         TEXT,
    max_deduction_limit REAL,
        -- NULL for sections with no cap (e.g., 80E)
    applicable_regime   TEXT NOT NULL DEFAULT 'OLD',
        -- OLD, NEW, BOTH
    financial_year      TEXT NOT NULL,
        -- e.g., "2025-26"
    is_active           INTEGER NOT NULL DEFAULT 1,
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_tax_sections_fy ON tax_sections(financial_year);
```

### 13.2 `tax_section_mappings`

Maps specific accounts, securities, or transaction types to tax sections. This enables the system to automatically compute tax-eligible amounts.

```sql
CREATE TABLE tax_section_mappings (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    tax_section_id      INTEGER NOT NULL,
    account_id          INTEGER,
        -- e.g., PPF account maps to 80C
    security_id         INTEGER,
        -- e.g., ELSS fund maps to 80C
    transaction_type    TEXT,
        -- specific transaction types that qualify
    description         TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (tax_section_id) REFERENCES tax_sections(id),
    FOREIGN KEY (account_id) REFERENCES accounts(id),
    FOREIGN KEY (security_id) REFERENCES securities(id)
);
```

---

## 14. System, Configuration, and Audit

### 14.1 `app_settings`

Key-value store for application-wide configuration.

```sql
CREATE TABLE app_settings (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_key         TEXT NOT NULL UNIQUE,
    setting_value       TEXT,
    setting_type        TEXT NOT NULL DEFAULT 'STRING',
        -- STRING, INTEGER, REAL, BOOLEAN, DATE, JSON
    category            TEXT NOT NULL DEFAULT 'GENERAL',
        -- GENERAL, DISPLAY, TAX, NOTIFICATION, SECURITY, BACKUP, IMPORT
    description         TEXT,
    updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);
```

**Default Settings (seeded on first launch):**

| Key | Value | Category | Description |
|-----|-------|----------|-------------|
| `financial_year_start_month` | `4` | GENERAL | April for India |
| `base_currency` | `INR` | GENERAL | Primary currency |
| `number_format` | `INDIAN` | DISPLAY | Lakhs/Crores vs. Million/Billion |
| `date_format` | `DD/MM/YYYY` | DISPLAY | Display date format |
| `tax_regime` | `OLD` | TAX | OLD or NEW income tax regime |
| `cost_basis_method` | `FIFO` | GENERAL | FIFO, AVERAGE, SPECIFIC |
| `pan_number` | `NULL` | TAX | For tax report generation |
| `backup_frequency` | `WEEKLY` | BACKUP | Auto-backup schedule |
| `backup_path` | `NULL` | BACKUP | Local backup directory |
| `onboarding_completed` | `0` | GENERAL | Onboarding completion flag |
| `app_lock_enabled` | `0` | SECURITY | Biometric/PIN lock |
| `last_price_update` | `NULL` | GENERAL | Last security price refresh |

### 14.2 `audit_log`

Immutable, append-only log of every data modification in the system. Critical for traceability and debugging. This table should never be updated or deleted from — only inserted into.

```sql
CREATE TABLE audit_log (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type         TEXT NOT NULL,
        -- TRANSACTION, ACCOUNT, GOAL, BUDGET, PAYEE,
        -- RECURRING_TRANSACTION, SECURITY, TAG, SETTING,
        -- BANK_ACCOUNT, CREDIT_CARD, LOAN, BROKERAGE_ACCOUNT,
        -- IMPORT, RECONCILIATION
    entity_id           INTEGER NOT NULL,
    action              TEXT NOT NULL,
        -- CREATE, UPDATE, DELETE, VOID, RECONCILE,
        -- IMPORT, RESTORE, STATUS_CHANGE
    changes_json        TEXT,
        -- JSON object with field-level changes:
        -- {"field": "amount", "old": 500.00, "new": 550.00}
        -- For CREATE: full snapshot of created record
        -- For DELETE: full snapshot of deleted record
    summary             TEXT,
        -- human-readable description:
        -- "Updated transaction TXN-2026-00453: amount changed from 500 to 550"
    source              TEXT NOT NULL DEFAULT 'USER',
        -- USER, SYSTEM, IMPORT, RECURRING_ENGINE, RECONCILIATION
    ip_address          TEXT,
        -- reserved for future multi-device support
    timestamp           TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_audit_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_timestamp ON audit_log(timestamp);
CREATE INDEX idx_audit_action ON audit_log(action);
```

### 14.3 `notifications`

System-generated alerts and reminders.

```sql
CREATE TABLE notifications (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    notification_type   TEXT NOT NULL,
        -- BUDGET_THRESHOLD, BUDGET_EXCEEDED, GOAL_MILESTONE,
        -- GOAL_ON_TRACK, GOAL_BEHIND, BILL_DUE, EMI_DUE,
        -- SIP_DUE, RECURRING_PENDING, CREDIT_CARD_DUE,
        -- FD_MATURING, LOAN_PAYMENT_DUE, ANOMALY_DETECTED,
        -- LARGE_TRANSACTION, PRICE_ALERT, IMPORT_COMPLETE,
        -- BACKUP_REMINDER
    title               TEXT NOT NULL,
    message             TEXT NOT NULL,
    related_entity_type TEXT,
    related_entity_id   INTEGER,
    priority            TEXT NOT NULL DEFAULT 'MEDIUM',
        -- LOW, MEDIUM, HIGH, CRITICAL
    is_read             INTEGER NOT NULL DEFAULT 0,
    is_dismissed        INTEGER NOT NULL DEFAULT 0,
    scheduled_date      TEXT,
        -- when this notification should be shown
    action_url          TEXT,
        -- deep link within the app to the relevant screen
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    read_at             TEXT,
    dismissed_at        TEXT
);

CREATE INDEX idx_notifications_unread ON notifications(is_read, is_dismissed);
CREATE INDEX idx_notifications_scheduled ON notifications(scheduled_date);
CREATE INDEX idx_notifications_type ON notifications(notification_type);
```

### 14.4 `backup_history`

Tracks backup operations for the local-first database.

```sql
CREATE TABLE backup_history (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    backup_type         TEXT NOT NULL,
        -- AUTO, MANUAL, PRE_IMPORT, PRE_RESTORE
    file_path           TEXT NOT NULL,
    file_size_bytes     INTEGER,
    file_hash           TEXT,
        -- SHA-256 for integrity verification
    record_counts_json  TEXT,
        -- JSON with row counts per table at backup time
    status              TEXT NOT NULL DEFAULT 'COMPLETED',
        -- COMPLETED, FAILED, IN_PROGRESS
    notes               TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);
```

---

## 15. Seed Data — Default Chart of Accounts

The following account tree is created during onboarding. Accounts marked with `is_system = 1` cannot be deleted. Users can add, rename, or deactivate accounts but cannot break the fundamental tree structure.

```
1000  Assets (ASSET, placeholder)
├── 1100  Cash and Bank Accounts (ASSET, placeholder)
│   ├── 1101  Cash in Hand (ASSET/CASH)
│   ├── 1110  Savings Accounts (ASSET/BANK, placeholder)
│   ├── 1120  Current Accounts (ASSET/BANK, placeholder)
│   └── 1130  Salary Accounts (ASSET/BANK, placeholder)
├── 1200  Deposits (ASSET, placeholder)
│   ├── 1210  Fixed Deposits (ASSET/FIXED_DEPOSIT, placeholder)
│   └── 1220  Recurring Deposits (ASSET/RECURRING_DEPOSIT, placeholder)
├── 1300  Investments (ASSET, placeholder)
│   ├── 1310  Equity Stocks (ASSET/EQUITY_STOCK, placeholder)
│   ├── 1320  Mutual Funds (ASSET/MUTUAL_FUND, placeholder)
│   ├── 1330  ETFs (ASSET/ETF, placeholder)
│   ├── 1340  Bonds and Debentures (ASSET/BOND, placeholder)
│   ├── 1350  Government Securities (ASSET/BOND, placeholder)
│   ├── 1360  Gold Investments (ASSET/GOLD, placeholder)
│   │   ├── 1361  Sovereign Gold Bonds
│   │   ├── 1362  Gold ETFs
│   │   └── 1363  Digital Gold
│   └── 1370  F&O Margin (ASSET/FO_MARGIN)
├── 1400  Retirement Accounts (ASSET, placeholder)
│   ├── 1410  EPF (ASSET/PROVIDENT_FUND)
│   ├── 1420  PPF (ASSET/PROVIDENT_FUND)
│   ├── 1430  NPS (ASSET/PROVIDENT_FUND)
│   └── 1440  VPF (ASSET/PROVIDENT_FUND)
├── 1500  Fixed Assets (ASSET/FIXED_ASSET, placeholder)
│   ├── 1510  Real Estate
│   ├── 1520  Vehicles
│   ├── 1530  Physical Gold and Jewellery
│   └── 1540  Other Fixed Assets
├── 1600  Receivables (ASSET/RECEIVABLE, placeholder)
│   ├── 1610  Loans Given
│   └── 1620  Security Deposits
│
2000  Liabilities (LIABILITY, placeholder)
├── 2100  Credit Cards (LIABILITY/CREDIT_CARD, placeholder)
├── 2200  Loans (LIABILITY/LOAN, placeholder)
│   ├── 2210  Home Loan
│   ├── 2220  Car Loan
│   ├── 2230  Personal Loan
│   ├── 2240  Education Loan
│   ├── 2250  Gold Loan
│   ├── 2260  Loan Against Property
│   └── 2270  Consumer Durable Loan
├── 2300  Payables (LIABILITY/PAYABLE, placeholder)
│   ├── 2310  Bills Payable
│   └── 2320  Taxes Payable
│
3000  Income (INCOME, placeholder)
├── 3100  Salary Income (INCOME/SALARY, placeholder)
│   ├── 3110  Basic Salary
│   ├── 3120  HRA
│   ├── 3130  Special Allowance
│   ├── 3140  Bonus and Incentives
│   └── 3150  Other Allowances
├── 3200  Investment Income (INCOME, placeholder)
│   ├── 3210  Interest Income
│   ├── 3220  Dividend Income
│   ├── 3230  Realized Capital Gains — Equity STCG
│   ├── 3231  Realized Capital Gains — Equity LTCG
│   ├── 3232  Realized Capital Gains — Debt
│   ├── 3233  Realized Capital Gains — MF Equity
│   ├── 3234  Realized Capital Gains — MF Debt
│   ├── 3240  F&O Realized P&L
│   └── 3250  Rental Income from Investments
├── 3300  Other Income (INCOME, placeholder)
│   ├── 3310  Freelance and Consulting Income
│   ├── 3320  Rental Income
│   ├── 3330  Gifts Received
│   ├── 3340  Cashback and Rewards
│   └── 3350  Tax Refunds
│
4000  Expenses (EXPENSE, placeholder)
├── 4100  Housing (EXPENSE, placeholder)
│   ├── 4110  Rent
│   ├── 4120  Society Maintenance
│   ├── 4130  Property Tax
│   ├── 4140  Home Insurance
│   └── 4150  Home Repairs and Maintenance
├── 4200  Utilities (EXPENSE, placeholder)
│   ├── 4210  Electricity
│   ├── 4220  Water
│   ├── 4230  Piped Gas
│   ├── 4240  Internet and Broadband
│   └── 4250  Mobile and Telecom
├── 4300  Food and Dining (EXPENSE, placeholder)
│   ├── 4310  Groceries
│   ├── 4320  Dining Out
│   ├── 4330  Food Delivery
│   └── 4340  Beverages and Snacks
├── 4400  Transportation (EXPENSE, placeholder)
│   ├── 4410  Fuel
│   ├── 4420  Public Transport
│   ├── 4430  Cab and Auto
│   ├── 4440  Vehicle Maintenance and Service
│   ├── 4450  Vehicle Insurance
│   ├── 4460  Parking and Toll
│   └── 4470  Vehicle EMI Interest
├── 4500  Health and Wellness (EXPENSE, placeholder)
│   ├── 4510  Doctor and Hospital
│   ├── 4520  Medicines and Pharmacy
│   ├── 4530  Health Insurance Premium
│   ├── 4540  Gym and Fitness
│   └── 4550  Alternative Therapies
├── 4600  Personal and Lifestyle (EXPENSE, placeholder)
│   ├── 4610  Clothing and Footwear
│   ├── 4620  Personal Care and Grooming
│   ├── 4630  Education and Courses
│   ├── 4640  Books and Stationery
│   └── 4650  Gadgets and Electronics
├── 4700  Entertainment and Leisure (EXPENSE, placeholder)
│   ├── 4710  Subscriptions (OTT, Music, Apps)
│   ├── 4720  Movies and Events
│   ├── 4730  Hobbies
│   └── 4740  Travel and Vacation
├── 4800  Financial Charges (EXPENSE, placeholder)
│   ├── 4810  Bank Charges and Fees
│   ├── 4820  Brokerage and STT
│   ├── 4830  Loan Interest Paid
│   ├── 4840  Credit Card Interest and Fees
│   ├── 4850  Insurance Premiums (non-health)
│   └── 4860  Advisory and PMS Fees
├── 4900  Taxes (EXPENSE, placeholder)
│   ├── 4910  Income Tax (TDS and Advance Tax)
│   ├── 4920  Professional Tax
│   └── 4930  GST on Services
├── 4950  Miscellaneous (EXPENSE, placeholder)
│   ├── 4951  Gifts Given
│   ├── 4952  Donations and Charity
│   ├── 4953  Household Supplies
│   ├── 4954  Domestic Help
│   ├── 4955  Pet Expenses
│   ├── 4956  Children Education and Activities
│   └── 4999  Other Expenses
│
5000  Equity (EQUITY, placeholder)
├── 5100  Opening Balances (EQUITY)
└── 5200  Retained Earnings (EQUITY)
```

During onboarding, when the user adds a specific bank account (e.g., "HDFC Savings — Primary"), a new leaf account is created under node 1110 with code 1111, name "HDFC Savings — Primary", `is_placeholder = 0`, `is_system = 0`, and linked via the `bank_accounts` table.

---

## 16. Entity Relationship Summary

The following describes the key relationships between tables, organized by the direction of foreign key references.

**`accounts`** is the central node. It is referenced by `transaction_lines.account_id`, `bank_accounts.account_id`, `credit_cards.account_id`, `loans.account_id`, `brokerage_accounts.account_id`, `fixed_deposits.account_id`, `goal_account_mappings.account_id`, `budget_items.account_id`, `monthly_snapshots.account_id`, `payees.default_account_id`, `recurring_transaction_lines.account_id`, `import_batches.target_account_id`, and `tax_section_mappings.account_id`. It self-references via `parent_id`.

**`transactions`** is referenced by `transaction_lines.transaction_id`, `transaction_charges.transaction_id`, `transaction_tags.transaction_id`, `attachments.transaction_id`, `tax_lots.buy_transaction_id`, `tax_lot_disposals.sell_transaction_id`, `fo_positions.entry_transaction_id`, `fo_positions.exit_transaction_id`, `goal_contributions.transaction_id`, `reconciliation_records.matched_transaction_id`, and `reconciliation_records.created_transaction_id`. It self-references via `reversal_of_transaction_id`.

**`securities`** is referenced by `security_prices.security_id`, `tax_lots.security_id`, `fo_contracts.underlying_security_id`, `transaction_lines.security_id`, `holdings_summary.security_id`, `recurring_transactions.security_id`, and `tax_section_mappings.security_id`.

**`financial_institutions`** is referenced by `bank_accounts`, `credit_cards`, `loans`, `brokerage_accounts`, `fixed_deposits`, and `import_profiles`.

**`goals`** is referenced by `goal_account_mappings`, `goal_milestones`, `goal_contributions`, and `recurring_transactions.goal_id`.

---

## 17. Indexing Strategy

Beyond the indexes defined inline with each table, the following compound indexes are recommended for common query patterns.

For the transaction listing screen (filtered by date range and account):

```sql
CREATE INDEX idx_txn_lines_account_txn
    ON transaction_lines(account_id, transaction_id);
```

For report generation (transactions in a date range):

```sql
CREATE INDEX idx_transactions_date_type
    ON transactions(transaction_date, transaction_type);

CREATE INDEX idx_transactions_date_status
    ON transactions(transaction_date, status);
```

For investment portfolio queries:

```sql
CREATE INDEX idx_tax_lots_status_security
    ON tax_lots(status, security_id, brokerage_account_id);
```

For monthly snapshot lookups:

```sql
-- Already covered by the unique index on (account_id, snapshot_year, snapshot_month)
```

For full-text search across transaction descriptions and payee names (SQLite FTS5):

```sql
CREATE VIRTUAL TABLE transactions_fts USING fts5(
    description,
    notes,
    content='transactions',
    content_rowid='id'
);

CREATE VIRTUAL TABLE payees_fts USING fts5(
    name,
    content='payees',
    content_rowid='id'
);
```

---

## 18. Data Integrity Constraints

The following constraints are enforced at the application level. SQLAlchemy Core's expression language handles dialect-specific SQL differences, so these constraints are expressed through the expression API rather than engine-specific raw SQL.

**Double-Entry Balance Constraint:** For every transaction, `SUM(amount) WHERE line_type = 'DEBIT'` must equal `SUM(amount) WHERE line_type = 'CREDIT'`. Every transaction must have at least two lines. This is validated before any transaction insert or update.

**Goal Allocation Constraint:** For any single account, the sum of `allocation_percentage` across all `goal_account_mappings` must not exceed 100.

**Budget Uniqueness Constraint:** A single account should not appear in two overlapping budgets of the same period type.

**Account Deletion Protection:** Accounts with any associated `transaction_lines` cannot be deleted, only deactivated (`is_active = 0`). System accounts (`is_system = 1`) cannot be deactivated.

**Void Immutability:** Once a transaction's `is_void` is set to 1, no further modifications are permitted to that transaction or its lines.

**Audit Log Immutability:** No UPDATE or DELETE operations on the `audit_log` table. Application-level enforcement, optionally backed by a database trigger.

---

## 19. Migration Path to Multi-User

When the application evolves beyond single-user, the following changes are required. The schema has been designed to make this transition additive rather than structural.

A `users` table is added with standard authentication fields. A `user_id INTEGER NOT NULL` column is added to every table except `currencies`, `tax_sections`, and `app_settings` (which become `user_settings`). All unique indexes are expanded to include `user_id`. All queries add `WHERE user_id = ?` filtering. Row-level security or application-level tenant isolation is implemented.

No table structures need to change. No columns need to be removed or renamed. The migration is purely additive.

---

## 20. Table Count Summary

| Domain | Tables | Table Names |
|--------|--------|-------------|
| Core Accounting | 3 | `accounts`, `currencies`, `exchange_rates` |
| Financial Institutions & Accounts | 5 | `financial_institutions`, `bank_accounts`, `fixed_deposits`, `credit_cards`, `loans`, `brokerage_accounts` |
| Investments & Securities | 6 | `securities`, `security_prices`, `tax_lots`, `tax_lot_disposals`, `fo_contracts`, `fo_positions`, `holdings_summary` |
| Transactions | 4 | `transactions`, `transaction_lines`, `transaction_charges`, `attachments` |
| Categories & Classification | 3 | `payees`, `tags`, `transaction_tags` |
| Recurring Transactions | 2 | `recurring_transactions`, `recurring_transaction_lines` |
| Goals | 4 | `goals`, `goal_account_mappings`, `goal_milestones`, `goal_contributions` |
| Budgets | 2 | `budgets`, `budget_items` |
| Reporting & Snapshots | 3 | `monthly_snapshots`, `net_worth_history`, `saved_reports` |
| Import & Reconciliation | 3 | `import_profiles`, `import_batches`, `reconciliation_records` |
| Tax Management | 2 | `tax_sections`, `tax_section_mappings` |
| System & Configuration | 4 | `app_settings`, `audit_log`, `notifications`, `backup_history` |
| **Total** | **37 (+2 FTS)** | |

---

This schema provides complete coverage for the Onboarding, Transaction, Goal, Budget, and Reporting modules we designed, along with the cross-cutting concerns (audit, import, reconciliation, tax, notifications, and backup). Your colleague working on the database can use this as the implementation specification. If they need clarification on any specific table's role, relationships, or the data flow through a particular use case, I'm happy to walk through it.