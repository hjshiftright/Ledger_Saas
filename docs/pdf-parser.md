# PDF Parser Module — Detailed Technical Specification
## Ledger 3.0 — Transaction Manager: Import & Parse Subsystem
### Version 0.1 | Date: March 14, 2026

---

## 1. Module Purpose & Scope

The PDF Parser Module is the ingestion layer of the Transaction Manager. Its job is to accept
user-uploaded financial documents, extract structured transaction data, normalize it into the
Ledger canonical schema, and hand it to the accounting engine for journal entry generation.

**Documents in scope for v1:**

| Category | Sources | Formats |
|---|---|---|
| Mutual Fund — CAS | CAMS, KFintech, MF Central | Password-protected PDF |
| Stock Broker | Zerodha — Holdings, Tradebook, Tax P&L, Capital Gains | CSV, XLSX, PDF |
| Bank Statements | HDFC, SBI, ICICI, Axis, Kotak, IndusInd, IDFC First | PDF, CSV, XLS |
| Generic Fallback | Any unrecognized bank / institution | CSV, XLSX |

**Out of scope for v1:** Credit card statements, EPFO passbook, NPS statements, Form 26AS / AIS
(planned v2).

---

## 2. High-Level Architecture

### 2.1 Processing Pipeline

Every uploaded document — regardless of source — flows through the same 8-stage pipeline:

```
[1. Upload & Validation]
        ↓
[2. Password Decryption]
        ↓
[3. Source Detection]          ← identifies bank / broker / CAS type
        ↓
[4. Text & Table Extraction]   ← PDF text layer → PyMuPDF fallback → OCR
        ↓
[5. Source-Specific Parser]    ← per-source parsing module
        ↓
[6. Schema Normalization]      ← map to canonical NormalizedTransaction
        ↓
[7. Deduplication Check]       ← hash-based + near-duplicate + transfer-pair
        ↓
[8. Review Queue]              ← human confirmation before JE generation
```

### 2.2 Parser Registry

A central `ParserRegistry` maps `(source_type, format) → parser class`. Source detection
(Stage 3) inspects the first 2 pages of the PDF (or headers of CSV) and emits a `DetectedSource`
enum. The registry dispatches to the correct parser. If confidence is low, the Generic Parser is
invoked and the user is shown a column-mapper UI.

### 2.3 Parallelism & Chunking

Large CAS PDFs (100+ pages, 10+ years of history) are chunked into 500-row batches processed
independently and then merged. Parsing is async — the UI shows a progress indicator and the user
can continue using the app while parsing runs in the background. Files over 500 pages trigger a
background job with an in-app notification on completion.

---

## 3. CAS Parser (CAMS & KFintech)

### 3.1 Document Overview

The Consolidated Account Statement (CAS) is a single PDF issued by CAMS or KFintech that
aggregates all mutual fund folios across all AMCs held by an investor (identified by PAN).

| Registrar | Coverage | Source |
|---|---|---|
| CAMS | HDFC MF, Nippon, Kotak, Aditya Birla, and others | camsonline.com |
| KFintech | SBI, ICICI Pru, Axis, Mirae, DSP, and others | kfintech.com |
| MF Central | All AMCs (unified CAMS + KFintech) | mfcentral.com |

**Password convention:**
- CAMS: `PAN_UPPERCASE + DDMMYYYY` (e.g., `ABCDE1234F01011985`)
- KFintech: same convention
- MF Central: same convention

The UI displays a source-specific hint when a password is requested (see §6.3).

### 3.2 Document Structure — CAMS Format

**Page 1 — Investor Header:**
- Statement title: "Consolidated Account Statement — CAMS"
- Period: `From DD-MMM-YYYY To DD-MMM-YYYY`
- Investor Name, PAN, Email, Mobile, KYC Status, Address

**Folio Sections (one per AMC per folio):**

Each section begins with a heading line:
```
[AMC Name] | Folio No: [number] | [Holding mode: Single/Joint]
```

Followed by, for each scheme within the folio:
- Scheme name + ISIN
- Opening balance: `units | NAV | value`
- Transaction table: `Date | Transaction Type | Amount | Units | NAV | Unit Balance | Value`
- Closing balance: `units | NAV | value`

**Summary Page (last page):**
- Portfolio table: Folio No, Scheme Name, Plan, Units, NAV, Value, Cost, Unrealised Gain/Loss

### 3.3 Document Structure — KFintech Format

KFintech follows the same folio-section structure with the following differences:

- Folio heading: `Folio No: [number] | [AMC Name]` (reversed order)
- Transaction table column order may vary — `Amount` and `Units` may be swapped
- NAV date may appear as a separate field in some versions
- Includes `Dividend Reinvestment` transaction type (not present in CAMS)

The parser detects column order from the header row, not by position.

### 3.4 Parsing Steps

**Step 1 — Source Identification:**

| Page 1 Text Pattern | Detected Source |
|---|---|
| "CAMS" or "Computer Age Management Services" | `CAS_CAMS` |
| "KFintech" or "Karvy" or "KFIN Technologies" | `CAS_KFINTECH` |
| "MF Central" | `CAS_MFCENTRAL` → run both parsers, merge |

**Step 2 — Investor Header Extraction:**
- PAN: regex `[A-Z]{5}[0-9]{4}[A-Z]`
- Period: `From\s*(\d{2}-[A-Za-z]{3}-\d{4})\s*To\s*(\d{2}-[A-Za-z]{3}-\d{4})`
- Name: line immediately following "Name:" or "Investor Name"

**Step 3 — Folio Block Splitting:**
Split raw text into folio blocks using heading-line regex:
- CAMS: `^[A-Z ]+\s*\|\s*Folio No:\s*[\w/]+`
- KFintech: `^Folio No:\s*[\w/]+\s*\|`

**Step 4 — Scheme Block Splitting:**
Within each folio block, split by scheme. Each scheme block begins with the scheme name line
(typically bold/capitalized) followed by the ISIN in brackets.

**Step 5 — Opening / Closing Balance Extraction:**
```
Opening Balance\s*[|:]\s*([\d,]+\.\d+)\s*units
```
Same pattern with "Closing Balance". NAV extracted from same line or following line. Value = units × NAV (cross-verify if stated).

**Step 6 — Transaction Table Parsing:**
Detect header row by finding the line containing all of: `Date`, `Transaction`, `Amount`, `Units`, `NAV`. Parse rows below header until the closing balance line.

| Field | Format | Notes |
|---|---|---|
| Date | `DD-[Mon]-YYYY` | e.g., `05-Jan-2024` — parse with dateutil |
| Transaction type | Free text | Map to canonical TxnType (see §3.5) |
| Amount | Float (may have commas, brackets for negatives) | Negative = outflow |
| Units | Float | Negative for redemptions / STP-outs |
| NAV | Float | — |
| Unit Balance | Float | Running unit total after this transaction |

**Step 7 — ISIN & Fund Code Matching:**
Match each scheme name to the AMFI master (fetched from AMFI API or bundled lookup table).
Use fuzzy matching (RapidFuzz, threshold ≥ 0.85) on scheme name, verify against ISIN if present.

### 3.5 Transaction Type Normalization

| CAS Transaction Text | Canonical TxnType | Ledger JE Pattern |
|---|---|---|
| Purchase / SIP / Switch-In / STP-In / NFO Allotment | `PURCHASE` | Dr: MF Account / Cr: Bank Account |
| Redemption / Switch-Out / STP-Out | `REDEMPTION` | Dr: Bank / Cr: MF Account + Capital Gains split |
| Dividend Payout | `DIVIDEND_PAYOUT` | Dr: Bank / Cr: Income > Dividends |
| Dividend Reinvestment | `DIVIDEND_REINVEST` | Dr: MF Account / Cr: Income > Dividends |
| Bonus Units | `BONUS` | Dr: MF Account / Cr: none (cost basis unchanged, units increase) |
| Merger / Segregation | `CORPORATE_ACTION` | → manual review queue |

**Switch pairing:** Switch-In and Switch-Out transactions in the same folio on the same date with
matching amounts are detected as a pair and linked into a single inter-fund transfer transaction.

### 3.6 Opening Balance Handling

- **First import for this fund:** Create a synthetic `OPENING_BALANCE` transaction dated at the
  statement period start date. Units and NAV from the opening balance line. JE posts against
  `Equity > Opening Balance Equity`.
- **Prior import exists:** Cross-check unit count of the new CAS opening balance against the
  prior CAS closing balance (tolerance: 0.001 units). If they match, no synthetic transaction is
  created.
- **Gap between two CAS periods:** Alert the user and create placeholder folio entries for the
  gap period, flagged for manual review.

### 3.7 Output Schema (ParsedCAS)

```typescript
interface ParsedCAS {
  source: 'CAS_CAMS' | 'CAS_KFINTECH' | 'CAS_MFCENTRAL';
  statement_period: { from: Date; to: Date };
  investor: {
    name: string;
    pan: string;       // masked: ABCDE****F
    email?: string;
    mobile?: string;
  };
  folios: Array<{
    folio_number: string;
    amc_name: string;
    schemes: Array<{
      scheme_name: string;
      isin?: string;
      amfi_code?: string;
      plan: 'Direct' | 'Regular';
      option: 'Growth' | 'IDCW';
      opening_balance: { units: number; nav: number; value: number; date: Date };
      closing_balance: { units: number; nav: number; value: number; date: Date };
      transactions: CASTransaction[];
    }>;
  }>;
  parse_confidence: number;    // 0.0 – 1.0
  warnings: string[];
}

interface CASTransaction {
  txn_id: string;              // deterministic hash
  date: Date;
  txn_type: TxnType;
  amount: number;              // INR; negative = outflow from investor
  units: number;               // negative for redemptions
  nav: number;
  unit_balance: number;        // running balance after this transaction
  raw_description: string;
  is_synthetic: boolean;       // true for opening-balance synthetic transactions
}
```

### 3.8 Edge Cases

| Scenario | Handling |
|---|---|
| Multi-PAN joint accounts | Extract all holder PANs; match primary PAN to Ledger user |
| Segregated/side-pocket units (e.g., Franklin 2020) | Parse normally; flag `is_segregated: true` |
| Zero-unit closing balance (fully redeemed) | Include — needed for capital gains history |
| Scanned / image-only PDF | OCR pipeline (rare — CAMS/KFintech always generate digital PDFs) |
| HTML CAS (email delivery) | Out of scope v1; architecture allows plug-in later |

---

## 4. Zerodha Parser (4 Statement Types)

### 4.1 Overview

| Statement | Format | Available From | Contents |
|---|---|---|---|
| Holdings Export | CSV | Console > Portfolio > Holdings | Current equity / ETF holdings with avg price |
| Tradebook | CSV | Console > Reports > Tradebook | Full chronological trade history (equity, F&O) |
| Tax P&L Report | CSV | Console > Reports > Tax P&L | Realized gains/losses per financial year |
| Capital Gains Statement | PDF / XLSX | Console > Reports > Capital Gains | FIFO-based lot-level gain/loss per scrip |

### 4.2 Holdings Parser (CSV)

**Column structure (stable as of 2025):**
```
Instrument, Qty, Avg. cost, LTP, Cur. val, P&L, Net chg., Day chg.
```

**Parsing logic:**
1. Map `Instrument` (NSE ticker) → ISIN via bundled NSE symbol master (refreshed weekly)
2. Classify: Equity or ETF (ETF symbols end with BEES, NIFTY, NEXT50, etc.)
3. Cost basis = `Qty × Avg. cost`; market value = `Qty × LTP`
4. Map to `Asset > Investments > Equities > Zerodha` (or `> ETF > Zerodha` for ETFs)

**Opening balance note:** Holdings represent the current portfolio with no transaction history.
A synthetic "Opening Balance" transaction is created per holding using the reported `Avg. cost`.
User is informed: *"Transaction history is unavailable for these holdings unless you also import
your Tradebook."*

**Output schema:**
```typescript
interface ParsedHoldings {
  as_of_date: Date;
  broker: 'Zerodha';
  holdings: Array<{
    symbol: string;
    isin?: string;
    instrument_type: 'Equity' | 'ETF' | 'Preference Share';
    exchange: 'NSE' | 'BSE';
    qty: number;
    avg_cost: number;
    ltp: number;
    cost_value: number;
    market_value: number;
    unrealised_pnl: number;
  }>;
}
```

### 4.3 Tradebook Parser (CSV)

**Column structure:**
```
symbol, isin, trade_date, exchange, segment, series, trade_type, quantity,
price, order_id, order_execution_time, trade_id
```

**Version detection:**
- Headers contain `order_execution_time` → v2 format (2022+)
- Headers contain `trade_date` but not `order_execution_time` → v1 format (2020–2022)

Both versions are normalized to the same internal schema before processing.

**Processing by segment:**

**EQ / series = EQ (Equity Delivery):**
1. Group trades by symbol
2. Sort by `trade_date` ascending
3. Apply FIFO lot matching per symbol:
   - Each SELL is matched against the oldest unsold BUY lots
   - Holding period per lot determines STCG (< 12 months) vs. LTCG (≥ 12 months)
4. Journal entries:
   - BUY: `Dr: Asset > Equities > Zerodha > [Symbol] / Cr: Asset > Bank > [Settlement]`
   - SELL with gain: `Dr: Bank / Cr: Equities (cost) + Cr: Income > Capital Gains > [STCG/LTCG Equity]`
   - SELL at loss: `Dr: Bank + Dr: Expense > Investment Losses > [STCG/LTCG] / Cr: Equities`

**INTRADAY (Intraday Equity):**
1. Match BUY/SELL pairs within the same trading day per symbol
2. Net P&L = (sell proceeds) − (buy cost) − (charges)
3. Net profit → `Income > Trading Income > Intraday (Speculative)`
4. Net loss → `Expense > Investment Losses > Intraday Trading`

**FNO (Futures & Options):**

Symbol parsing:
- Futures: `NIFTY23JUNFUT` → underlying=NIFTY, expiry=Jun-2023, type=FUT
- Options: `NIFTY23JUN18000CE` → underlying=NIFTY, expiry=Jun-2023, strike=18000, type=CE

| Action | Journal Entry Pattern |
|---|---
| Options BUY | `Dr: Asset > Derivatives > Options Bought > [Underlying] / Cr: Bank` |
| Options SELL (close/expiry) | net P&L → `Income/Expense > F&O (Non-Speculative)` |
| Futures (open) | Track margin; daily MTM settlement recorded separately |
| Futures (close) | net P&L → `Income/Expense > F&O (Non-Speculative)` |

**ETF (EQ segment, ETF symbol):**
Same as Equity Delivery but mapped to `Asset > Investments > ETF > Zerodha`.

### 4.4 Tax P&L Parser (CSV)

The Tax P&L report is a pre-computed FY-level summary organized by income head.

**Sections within the CSV (separated by blank rows + section-header lines):**
1. Equity (Delivery) — STCG and LTCG per symbol, FIFO basis
2. Equity (Intraday) — Speculative P&L
3. Equity Futures — Non-speculative business income
4. Equity Options — Non-speculative business income

**Uses:**
1. Populate Tax Summary Report (Reports Module, Part 9)
2. Cross-validate against Tradebook-derived capital gains — discrepancies flagged for review

### 4.5 Capital Gains Statement (PDF / XLSX)

Lot-level FIFO gain/loss per scrip, including STT and exchange charges.

**Column structure:** Script Name | ISIN | Buy Date | Sell Date | Qty | Buy Price | Sell Price |
Buy Value | Sell Value | STT on Sale | Exchange Charges | Classification (STCG/LTCG) | Gain Amount

**Format preference:** Prefer XLSX if available — table structure is preserved and avoids PDF
layout parsing complexity. Fall back to PDF table extractor (see §6.2) if XLSX unavailable.

**Output:** `CapitalGainLot` records per scrip. These feed directly into:
- Investment Performance Report (realized gains/losses section)
- Tax Summary Report (capital gains schedule)

---

## 5. Bank Statement Parsers

### 5.1 Shared Architecture

All bank parsers extend a shared abstract base class:

```typescript
abstract class BankStatementParser {
  abstract detect(text: string): boolean;          // true if text matches this bank
  abstract extractHeader(text: string): AccountHeader;
  abstract extractTransactions(tables: Table[]): RawTransaction[];

  // Shared — provided by base class:
  normalize(raw: RawTransaction[]): NormalizedTransaction[];
  deduplicate(txns: NormalizedTransaction[]): NormalizedTransaction[];
}
```

**Auto-detection signals used:**
- Distinctive text in page 1 header (e.g., "HDFC BANK LIMITED")
- IFSC code prefix (HDFC0, SBIN0, ICIC0, UTIB0, KKBK0, INDB0, IDFB0)
- Column header patterns in the transaction table

`ParserRegistry.detect()` runs all `detect()` methods in priority order; first match wins.

**Balance cross-check (all banks):**
```
Opening Balance + Σ(Credits) − Σ(Debits) = Closing Balance
```
If the computed value differs from the statement's closing balance, emit a
`BALANCE_MISMATCH` flag (see §11 — Error States).

### 5.2 HDFC Bank

**Formats:** PDF (digital), CSV (NetBanking download — prefer CSV over PDF)

**Transaction table columns:**
```
Date | Narration | Chq./Ref.No. | Value Dt | Withdrawal Amt.(INR) | Deposit Amt.(INR) | Closing Balance(INR)
```

**Date format:** `DD/MM/YY` — 2-digit year, interpret as 20XX.

**Amount columns:** Separate Withdrawal (debit) and Deposit (credit) — always positive values.

**Password convention:** `PAN_UPPERCASE + DDMMYYYY`

**CSV column mapping:** `Date, Narration, Value Dat, Debit Amount, Credit Amount, Chq No, Closing Balance`

**Key narration patterns:**

| Pattern | Category |
|---|---|
| `UPI-[name]-[VPA]-[UTR]` | UPI transfer |
| `NEFT/[ref]-[name]` | NEFT transfer |
| `RTGS/[ref]/[name]` | RTGS transfer |
| `ATW-[location]` | ATM withdrawal → `Asset > Cash in Hand` |
| `EMI [loan ref] [bank]` | Loan EMI → split principal + interest |
| `NACH DR [mandate] [company]` | NACH debit (SIP / insurance) |
| `INT PD` | Interest paid → `Income > Interest Income` |
| `SALARY [company]` | Salary credit |
| `POS [merchant] [card last 4]` | POS / debit card swipe |

### 5.3 SBI (State Bank of India)

**Formats:** PDF (YONO, YONO Lite, branch), XLS (YONO download)

**Transaction table columns:**
```
Txn Date | Value Date | Description | Ref No. | Debit | Credit | Balance
```

**Two layout variants:** YONO export vs. branch-printed — same column semantics, different header styling.

**Special handling:** SBI sometimes includes an "OPENING BALANCE" as the **first data row** of the
table (not a separate header). Parse this row and use its balance as `opening_balance`; do not
create a transaction entry for it.

**Password convention:** `DDMMYYYY` (date of birth)

**Key narration patterns:**

| Pattern | Category |
|---|---|
| `TO TRANSFER-UPI/[ref]/[beneficiary]` | UPI debit |
| `BY TRANSFER-UPI/[ref]/[sender]` | UPI credit |
| `TO SELF TRANSFER` | Inter-account transfer within SBI |
| `ATM WDL` / `ATM WD-[branch]` | ATM withdrawal |
| `INT. CREDIT` | Interest income |
| `CLEAR BAL` | Balance-cleared entry — value ₹0, ignore |

### 5.4 ICICI Bank

**Formats:** PDF, CSV, XLS

**Transaction table columns:**
```
S No. | Transaction Date | Value Date | Description | Cheque No |
Deposit (INR) | Withdrawal (INR) | Balance (INR)
```

**Password convention:** PAN in uppercase (some accounts: `DDMMYYYY`)

**Key narration patterns:**

| Pattern | Category |
|---|---|
| `UPI/[ref]/[merchant or VPA]` | UPI |
| `ITAX REFUND` | `Income > Tax Refunds` |
| `CREDIT CARD PAYMENT` | Transfer to ICICI CC liability account |
| `INT EARNED` | `Income > Interest Income` |
| `AMAZON PAY` | Amazon Pay BNPL / wallet |

**CSV column mapping:** `Transaction Date, Value Date, Description, Amount Debit, Amount Credit, Cheque/Ref Number, Closing Balance`

### 5.5 Axis Bank

**Formats:** PDF, XLS

**Transaction table columns:**
```
Tran Date | CHQNO | PARTICULARS | DR | CR | BAL
```

**Password convention:** `PAN_UPPERCASE + DDMMYYYY`

**Known issue — Multi-page table overflow:** In some Axis PDFs, the transaction table
overflows across pages without repeating the header row. The parser must capture column
positions from the first header occurrence and apply them to all continuation pages.

**Key narration patterns:**

| Pattern | Category / Note |
|---|---|
| `MBK/[ref]/...` | Mobile banking transfer |
| `ATMDP/[ATM ID]` | ATM withdrawal |
| `NACH DR RETURN` | NACH bounce → flag for manual review |
| `INTREST CREDIT` | Interest income (Axis misspells "interest") |

### 5.6 Kotak Mahindra Bank

**Formats:** PDF, CSV

**Transaction table columns:**
```
Date | Description | Chq No | Branch Code | Debit (INR) | Credit (INR) | Balance (INR)
```

**Password convention:** `DDMMYYYY`

**Key narration patterns:**

| Pattern | Category |
|---|---|
| `UPI/[ref]/[name]/[VPA]` | UPI (longer narration format than HDFC/ICICI) |
| `FD INTEREST CREDIT [FD ref]` | Map to corresponding FD account |
| `FD MATURITY CREDIT` | FD → Bank transfer |
| `KOTAK NET BANKING TRANSFER` | Inter-account transfer |

### 5.7 IndusInd Bank

**Formats:** PDF

**Transaction table columns:**
```
Date | Description | Cheque No | Debit | Credit | Balance
```

**Password convention:** Customer ID or `DDMMYYYY`

**Known issue — Two-column page layout:** Some IndusInd PDFs use a two-column page layout
(two table regions side-by-side). The table extractor must detect this layout by checking for
two distinct table regions per page and merge them row-by-row.

**Key narration prefixes:** `INDUPLM` (mobile payment), `CSTP` (cash deposit at branch)

### 5.8 IDFC First Bank

**Formats:** PDF, CSV

**Transaction table columns:**
```
Date | Description | Reference No. | Debit (INR) | Credit (INR) | Balance (INR)
```

**Password convention:** PAN in uppercase

**Key narration patterns:**

| Pattern | Category |
|---|---|
| `REWARD CASHBACK` | `Income > Cashback` |
| `WELCOME BONUS` | `Income > Other Income` |
| High UPI volume generally | IDFC First is popular for UPI due to incentive programs |

### 5.9 Generic / Fallback Parser (AI-Assisted Column Mapping)

For any source not matched by a named parser:

**Step 1 — Table Detection:** Extract tables via pdfplumber. If none found, attempt raw line
parsing with delimiter detection.

**Step 2 — Column Semantic Inference:** Match each column header against a semantic vocabulary:

| Header Variants | Semantic Slot |
|---|---|
| date, txn date, transaction date, value date | `DATE` |
| narration, description, particulars, remarks | `NARRATION` |
| debit, withdrawal, dr, amount_dr, withdrawal amt | `DEBIT` |
| credit, deposit, cr, amount_cr, deposit amt | `CREDIT` |
| balance, closing balance, bal | `BALANCE` |
| reference, ref no, chq no, cheque | `REFERENCE` |

**Step 3 — Amount Column Type Detection:**
- Dual column (separate Debit + Credit): most common in Indian banks
- Single signed column (positive = credit, negative = debit): common in CSV exports
- Single absolute column + Dr/Cr indicator column: some banks

**Step 4 — Confidence Scoring:**

| Score | Meaning | Action |
|---|---|---|
| > 0.85 | All key columns identified, balance cross-check passes | Auto-proceed |
| 0.6 – 0.85 | Columns identified but balance check fails or narration ambiguous | Warn, offer mapper |
| < 0.60 | One or more key columns missing | **Show column-mapper UI** |

**Step 5 — Column Mapper UI:**
A visual drag-and-drop interface showing the first 10 rows of the parsed table. The user drags
column headers to the correct semantic slots. AI suggestions are pre-populated. Mapper is
non-blocking; user confirms the mapping before parse proceeds.

---

## 6. Common Infrastructure

### 6.1 PDF Processing Engine (Layered)

| Layer | Library | Trigger | Notes |
|---|---|---|---|
| 1 (Primary) | pdfplumber | Always tried first | Text + table extraction with bounding coordinates. Covers > 95% of Indian financial PDFs |
| 2 (Fallback) | PyMuPDF / fitz | When pdfplumber table extraction fails | Reconstruct tables by clustering text by Y-coordinate |
| 3 (OCR) | Tesseract | < 50 chars/page average (image PDF) | Pre-process with OpenCV: deskew, denoise, adaptive threshold at 300 DPI. Confidence filter: discard words < 70% confidence. 5–15 s/page — user warned before invocation |

**Selection logic:** Try Layer 1 → if text < 50 chars/page average, assume scanned → invoke
Layer 3 → if tables parse but balance cross-check fails by > 5%, retry with Layer 2.

### 6.2 Table Extractor

A reusable `TableExtractor` component wraps pdfplumber with bank-specific tuning:

- `line_scale=15` for HDFC/ICICI (visible grid lines)
- `text_tolerance=5, intersection_tolerance=5` for Axis (minimal grid lines)
- Header row detection: first row where all/most cells contain alphabetic content
- Multi-page stitching: track page number; if header row repeats on page N+1, recognize and skip it
- Column merge detection: adjacent empty columns treated as visual separators — drop

**Output:** `Table { headers: string[]; rows: string[][] }` with page-number metadata.

### 6.3 Password Handler

```
1. Attempt to open PDF without password
2. If EncryptionError → trigger password collection UI
   - Show detected source name
   - Show expected password format hint (e.g., "For HDFC: your PAN in uppercase
     followed by date of birth in DDMMYYYY, e.g., ABCDE1234F15031990")
3. User enters password
4. Client-side decryption (browser WASM / native app)
5. If success: plaintext PDF bytes passed to extractor — password discarded immediately
6. If failure: offer 2 more attempts with alternate format hints
7. After 3 failures: "Unable to open this PDF. Check the password or download a fresh copy."
```

**Security requirement (PRD R11):** Decryption happens client-side only. The password is never
stored, never logged, and never transmitted to any server. The backend receives only the
decrypted content.

### 6.4 Transaction Normalizer

Maps every source-specific raw transaction to the canonical `NormalizedTransaction` schema:

```typescript
interface NormalizedTransaction {
  txn_hash: string;           // SHA-256(account_id + date_iso + narration_cleaned + amount_signed)
  account_id: string;         // resolved Ledger account UUID
  date: Date;                 // transaction post date (not value date)
  value_date?: Date;
  narration: string;          // cleaned narration
  narration_raw: string;      // original narration from source
  debit_amount?: number;      // INR (mutually exclusive with credit_amount for bank txns)
  credit_amount?: number;     // INR
  amount_signed: number;      // negative = debit, positive = credit
  running_balance?: number;   // from statement (if available)
  reference_number?: string;  // cheque number, UTR, UPI ref, etc.
  source: string;             // parser that generated this (e.g., 'HDFC_BANK_PDF')
  source_file_id: string;     // import batch UUID
  inferred_category?: string; // AI pre-classification (suggestion only — not committed)
  inferred_confidence?: number;
  flags: TransactionFlag[];
}

type TransactionFlag =
  | 'DUPLICATE_SUSPECT'
  | 'NEAR_DUPLICATE'
  | 'BALANCE_MISMATCH'
  | 'NEEDS_SPLIT'
  | 'TRANSFER_PAIR'
  | 'OPENING_BALANCE_MISMATCH'
  | 'NEEDS_ACCOUNT_CREATION';
```

**Narration cleaning rules:**
1. Trim whitespace; normalize multiple spaces to single space
2. Extract reference numbers (UTR, UPI ref ID) into `reference_number` field
3. Remove content-free prefixes: `"BY "`, `"TO "`, `"TXN#"`
4. Do **not** truncate — full narration is needed for AI categorization and deduplication

### 6.5 Deduplication Engine

**Step 1 — Exact hash match:**
If `txn_hash` already exists in the database for the same `account_id` → confirmed duplicate.
Skip, increment duplicate counter.

**Step 2 — Near-duplicate detection:**
Check if all three conditions hold:
- Same `account_id`
- Same `date` (±1 day)
- Same `amount_signed` (exact)
- Narration Jaro-Winkler similarity ≥ 0.85 after stripping UTR/ref numbers

If yes → flag `NEAR_DUPLICATE`. Present to user: *"This transaction looks similar to one
already recorded. Is this the same transaction?"*

**Step 3 — Cross-account transfer detection:**
Find pairs where:
- `txn_A.debit_amount ≈ txn_B.credit_amount` (within ₹1)
- `|txn_A.date − txn_B.date| ≤ 1 day`
- Both accounts belong to the same Ledger user
- Narrations share a matching UPI / NEFT / IMPS reference number

→ Flag both as `TRANSFER_PAIR`. Create a single inter-account transfer JE instead of
two separate income/expense entries.

**Deduplication report emitted after each import batch:**
```typescript
interface DeduplicationReport {
  total_parsed: number;
  new_transactions: number;
  exact_duplicates_skipped: number;
  probable_duplicates_flagged: number;
  transfer_pairs_detected: number;
}
```

### 6.6 Opening Balance Reconciliation

When importing a statement for an account that already has transactions in Ledger:

| Condition | Action |
|---|---|
| Statement opening balance vs. Ledger balance mismatch > ₹1 | Flag `OPENING_BALANCE_MISMATCH`. Warn user, ask to confirm before proceeding |
| Mismatch ≤ ₹1 | Rounding difference — proceed silently |

---

## 7. AI Categorization Layer

### 7.1 Three-Tier Pipeline

**Tier 1 — Rule Engine (deterministic, runs first):**

~150 system-defined rules + user-defined rules. Regex applied to `narration_cleaned`.

Sample rules (not exhaustive):

| Narration Pattern | Category |
|---|---|
| `UPI.*SWIGGY\|UPI.*ZOMATO` | `Expense > Food & Dining > Dining Out` |
| `UPI.*AMAZON\|POS.*AMAZON` | `Expense > Shopping > Online` |
| `SALARY\|SAL CREDIT\|INFOSYS\|TCS\|WIPRO` | `Income > Salary` |
| `ATM WDL\|ATM WD\|ATW-` | Transfer → `Asset > Cash in Hand` (not an expense) |
| `EMI.*HOME LOAN\|HDFC LOAN` | `Liability > Home Loan (principal)` + `Expense > Housing > Loan Interest` (split — requires loan terms) |
| `NACH DR.*[MF company name]` | `Asset > Mutual Funds > [matched fund]` |
| `EPF\|PF CONTRIBUTION` | `Asset > Provident Fund > EPF` |
| `LIC PREMIUM\|MAX TERM\|HDFC LIFE` | `Expense > Insurance > Life Insurance` |
| `ELECTRICITY\|BESCOM\|TATA POWER\|MSEB` | `Expense > Utilities > Electricity` |
| `IRCTC\|RAILWAYS` | `Expense > Travel` |
| `UBER\|OLA\|RAPIDO` | `Expense > Transportation > Cab` |

**Tier 2 — LLM Classification (for unmatched, if API key configured):**

Batch unmatched transactions and send to the user's configured LLM with:
- Transaction narration + amount direction (debit/credit)
- Flattened list of the user's expense and income accounts
- Few-shot examples from prior categorizations

LLM returns: account path + confidence score.

If no API key is configured, unmatched transactions remain `Uncategorized` in the review queue.

**Tier 3 — Learning from corrections:**

When the user re-categorizes a transaction in the review queue, a new user-specific rule is
created: `if narration contains "[merchant keyword]" → [new category]`. After 3 identical
corrections for the same narration pattern, the rule is auto-promoted from "suggestion" to
"applied automatically."

### 7.2 EMI Splitting

When a transaction is identified as a loan EMI, it is split into principal and interest
components using the reducing-balance formula, drawing on loan terms stored during onboarding:

```
interest_component  = outstanding_principal × monthly_rate
principal_component = EMI_amount − interest_component
```

**Journal entry:**
```
Dr: Liability > [Loan Account]          [principal_component]
Dr: Expense > Housing > Loan Interest   [interest_component]
Cr: Asset > Bank > [Source Account]     [total_EMI_amount]
```

If loan terms are not available: post entire EMI to `Expense > EMI Payments (Unallocated)`
and flag `NEEDS_SPLIT` for manual review.

---

## 8. Review Queue

All parsed transactions arrive in the Review Queue before any journal entry is written.

### 8.1 Row Classification

| Color | Confidence | Flags | Action Required |
|---|---|---|---|
| Green | > 0.90 | None | Bulk-approvable |
| Yellow | 0.60 – 0.90 | Minor | Individual review suggested |
| Red | < 0.60 | `BALANCE_MISMATCH`, `NEEDS_SPLIT`, etc. | Must review individually |

### 8.2 User Actions in the Queue

- **"Approve All High Confidence"** → bulk-approve all green rows
- **Select multiple rows → re-assign category** → bulk re-categorization
- **Click a row → detail pane** → edit category, split amount, add note, link to counterpart account

### 8.3 Approval → Journal Entry

When a transaction row is approved:
1. Journal entry created (double-entry engine enforces debit = credit)
2. Account running balance updated
3. Row removed from queue
4. Reporting module cache invalidated for affected accounts and periods

---

## 9. Import History & Audit Trail

Every import batch is logged as an `ImportRecord`:

```typescript
interface ImportRecord {
  import_id: string;           // UUID
  user_id: string;
  filename: string;
  file_hash: string;           // SHA-256 — used to detect re-upload of same file
  source_type: SourceType;
  import_timestamp: Date;
  statement_period?: { from: Date; to: Date };
  transactions_parsed: number;
  transactions_new: number;
  transactions_duplicate: number;
  transactions_flagged: number;
  parse_confidence: number;    // weighted average across all parsed rows
  status: 'PENDING_REVIEW' | 'PARTIAL_REVIEW' | 'COMPLETED' | 'FAILED' | 'ROLLED_BACK';
  error_log?: string;
}
```

**User capabilities:**
- View full import history (sortable by date, filterable by account / source type)
- Click any import → view its deduplication report and parsed transaction list
- **Undo an import:** Creates counter-entries (reversals) for all JEs from that batch. Blocked if
  subsequent imports contain transactions that depend on this batch's running balance.
- **Re-process an import:** Re-runs the updated parser on the original file. Used after parser
  bug fixes.

---

## 10. Core Enums & Data Model Summary

### 10.1 Enums

```typescript
type TxnType =
  | 'PURCHASE' | 'REDEMPTION' | 'DIVIDEND_PAYOUT' | 'DIVIDEND_REINVEST'
  | 'BONUS' | 'CORPORATE_ACTION' | 'TRANSFER_IN' | 'TRANSFER_OUT'
  | 'OPENING_BALANCE';

type SourceType =
  | 'HDFC_BANK_PDF'    | 'HDFC_BANK_CSV'
  | 'SBI_BANK_PDF'     | 'SBI_BANK_XLS'
  | 'ICICI_BANK_PDF'   | 'ICICI_BANK_CSV'
  | 'AXIS_BANK_PDF'    | 'AXIS_BANK_XLS'
  | 'KOTAK_BANK_PDF'   | 'KOTAK_BANK_CSV'
  | 'INDUSIND_BANK_PDF'
  | 'IDFC_BANK_PDF'    | 'IDFC_BANK_CSV'
  | 'CAS_CAMS' | 'CAS_KFINTECH' | 'CAS_MFCENTRAL'
  | 'ZERODHA_HOLDINGS' | 'ZERODHA_TRADEBOOK'
  | 'ZERODHA_TAX_PNL'  | 'ZERODHA_CAPITAL_GAINS'
  | 'GENERIC_CSV' | 'GENERIC_XLSX';

type SegmentType =
  | 'EQUITY_DELIVERY' | 'EQUITY_INTRADAY' | 'FNO_FUTURES' | 'FNO_OPTIONS'
  | 'ETF' | 'MUTUAL_FUND' | 'COMMODITY';

type GainType =
  | 'EQUITY_STCG' | 'EQUITY_LTCG'
  | 'MF_STCG'     | 'MF_LTCG'
  | 'DEBT_STCG'   | 'DEBT_LTCG'
  | 'SPECULATIVE' | 'FNO_BUSINESS';
```

### 10.2 Key Relationships

```
ImportRecord (1) ──────────────── (N) NormalizedTransaction
NormalizedTransaction (1) ─────── (1) JournalEntry           [created on approval]
JournalEntry (1) ──────────────── (2+) JournalEntryLeg
NormalizedTransaction (N) ─────── (1) Account                [source account]
ParsedCAS → CASFolio → CASScheme → CASTransaction
ZerodhaTradebook → TradeRow → CapitalGainLot
```

---

## 11. Error States & Recovery

| Error Condition | User-Facing Message | System Action |
|---|---|---|
| Encrypted PDF, wrong password | Source-specific hint ("For HDFC: PAN + DDMMYYYY DOB") | Allow 3 retries |
| Scanned / image PDF | "Running OCR — this may take 1–2 minutes." | Invoke OCR pipeline |
| Unrecognized format | "We couldn't identify this document. Help us map the columns." | Generic parser + column mapper UI |
| Balance cross-check failure | "Statement balance is off by ₹X. A page may be missing." | Flag `BALANCE_MISMATCH`, proceed with warning |
| Zero transactions extracted | "No transactions found. Ensure the statement covers the correct period." | Abort, surface error |
| Duplicate file (same SHA-256) | "This file was imported before on [date]." | Offer skip or force re-import |
| Opening balance mismatch | "Opening balance mismatch (₹X in statement vs. ₹Y in Ledger)." | Warn, ask to confirm |
| New folio not in Chart of Accounts | "Found a new mutual fund folio [number]. Create an account for it?" | Prompt account creation |
| Unknown AMC in CAS | "Unknown AMC: [name]. Placed under 'Other Mutual Funds' for now." | Create placeholder account |
| File > 10 MB or > 500 pages | "Large file — processing in the background." | Async background job, in-app notification on completion |

---

## 12. Planned Source Files

| File | Responsibility |
|---|---|
| `src/parsers/pipeline.ts` | 8-stage pipeline orchestration |
| `src/parsers/registry.ts` | `ParserRegistry` + auto-detection |
| `src/parsers/cas/cams.ts` | CAMS CAS parser |
| `src/parsers/cas/kfintech.ts` | KFintech CAS parser |
| `src/parsers/cas/mf-central.ts` | MF Central (calls both, merges output) |
| `src/parsers/zerodha/holdings.ts` | Holdings CSV |
| `src/parsers/zerodha/tradebook.ts` | Tradebook CSV + FIFO engine |
| `src/parsers/zerodha/tax-pnl.ts` | Tax P&L CSV |
| `src/parsers/zerodha/capital-gains.ts` | Capital Gains PDF / XLSX |
| `src/parsers/banks/hdfc.ts` | HDFC Bank PDF + CSV |
| `src/parsers/banks/sbi.ts` | SBI Bank PDF + XLS |
| `src/parsers/banks/icici.ts` | ICICI Bank PDF + CSV |
| `src/parsers/banks/axis.ts` | Axis Bank PDF + XLS |
| `src/parsers/banks/kotak.ts` | Kotak Bank PDF + CSV |
| `src/parsers/banks/indusind.ts` | IndusInd Bank PDF |
| `src/parsers/banks/idfc-first.ts` | IDFC First Bank PDF + CSV |
| `src/parsers/banks/generic.ts` | Generic fallback + column mapper |
| `src/parsers/common/pdf-engine.ts` | pdfplumber / PyMuPDF / Tesseract abstraction |
| `src/parsers/common/table-extractor.ts` | Shared table extraction with bank tuning |
| `src/parsers/common/password-handler.ts` | Client-side decryption, hint display |
| `src/parsers/common/normalizer.ts` | Raw → `NormalizedTransaction` mapping |
| `src/parsers/common/deduplication.ts` | Hash + near-duplicate + transfer-pair detection |
| `src/parsers/common/categorization.ts` | Rule engine + LLM integration + learning |
| `src/parsers/common/emi-splitter.ts` | Loan EMI principal / interest split |
| `src/parsers/common/opening-balance.ts` | Opening balance reconciliation |
| `src/parsers/common/import-record.ts` | Import history + undo / re-process |

---

## 13. Testing Strategy

### 13.1 Unit Tests

- **Date parsing:** all format variants per bank (`DD/MM/YY`, `DD-MMM-YYYY`, `YYYY-MM-DD`, etc.)
- **Amount parsing:** commas, negative signs, parentheses for negative amounts
- **Narration cleaning:** whitespace normalization, reference number extraction
- **Hash generation:** deterministic for known fixtures; collision-resistant
- **Balance cross-check:** inject known mismatches, verify flag generation
- **FIFO engine:** boundary cases — partial lots, lots spanning STCG/LTCG boundary, loss lots

### 13.2 Integration Tests

- Full parse pipeline for each supported source using anonymized/synthetic sample statements
- Deduplication: import same statement twice — verify zero new JEs on second import
- Cross-account transfer detection: import matching statements from two accounts
- Opening balance reconciliation: import two consecutive periods for same account

### 13.3 Golden Dataset

A curated set of anonymized/synthetic statements covering all supported sources and known
edge cases. Each file has an expected parse output (JSON fixture). CI pipeline runs each parser
against its fixtures and diffs the output. Any deviation fails the build.

### 13.4 Parse Confidence Monitoring (Production)

Log `parse_confidence` for all imports. Alert if the rolling 7-day average confidence drops
below 0.80 for any source type — this signals a format change by the bank or broker. Trigger
a manual review of the source format and a parser update.

### 13.5 User Acceptance Testing Scenarios

1. Upload a CAMS CAS with 5+ years of history (200+ pages) — validate folio count, transaction
   count, and closing balances against AMFI portal
2. Upload a Zerodha Tradebook with F&O trades — verify STCG/LTCG classification; cross-check
   totals against Zerodha's Tax P&L report
3. Upload a password-protected HDFC PDF — verify password hint displays, decrypt succeeds,
   password is not stored
4. Upload an SBI PDF where "OPENING BALANCE" appears as a data row — verify it becomes the
   opening balance, not a transaction
5. Upload an Axis Bank PDF with a multi-page table (no repeated header) — verify all transactions
   are captured across pages
6. Upload a scanned image PDF — verify OCR pipeline triggers, confidence < 0.85, transactions
   land in the red review queue
7. Upload an unknown bank CSV — verify column mapper displays, manual mapping accepted,
   balance cross-check passes after mapping
8. Import the same HDFC PDF twice — verify deduplication report shows 100% exact duplicates;
   zero new JEs on second import
9. Import overlapping CAS periods (Jan–Jun + Apr–Sep) — verify Apr–Jun transactions appear
   exactly once
10. HDFC loan EMI transaction with loan terms available in Ledger — verify JE splits correctly
    into principal + interest components
11. UPI transfer between two user accounts (both accounts imported in same batch) — verify
    transfer-pair detection and single inter-account JE is created
