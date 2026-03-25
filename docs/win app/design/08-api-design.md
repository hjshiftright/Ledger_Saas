# Ledger Desktop — API Design

**Version:** 1.0  
**Status:** Design Review

---

## 1. Conventions

- **Base URL:** `http://localhost:{port}` (ephemeral port, stored in `app_settings`)
- **Format:** JSON (`Content-Type: application/json`)
- **Auth:** None (single-user, local machine — PIN gate is at WPF layer, not API layer)
- **Errors:** `{ "error": "message", "code": "SNAKE_CASE_CODE" }`
- **Pagination:** `?page=1&pageSize=50` where applicable
- **Family filter (v2):** `?memberId=1` (specific) or `?memberId=all` (consolidated)

---

## 2. Setup Endpoints

### GET /setup/status
Returns whether Quick-Start Wizard has been completed.

**Response:**
```json
{
  "setupComplete": false,
  "ledgerDrivePath": null,
  "hasProfile": false
}
```

### POST /setup/complete
Completes Quick-Start Wizard — creates LedgerDrive folder, saves profile, starts file watcher.

**Request:**
```json
{
  "ledgerDrivePath": "C:\\Users\\Ravi\\Documents\\LedgerDrive",
  "displayName": "Ravi Kumar",
  "dateOfBirth": "1985-04-15",
  "mobileNumber": "9876543210",
  "currency": "INR",
  "taxRegime": "NEW"
}
```

**Response:** `201 Created`
```json
{ "setupComplete": true, "ledgerDrivePath": "C:\\Users\\Ravi\\Documents\\LedgerDrive" }
```

---

## 3. Profile Endpoints

### GET /profile
```json
{
  "id": 1,
  "displayName": "Ravi Kumar",
  "dateOfBirth": "****-04-15",   // year masked for display
  "panNumber": "****E1234F",     // partially masked
  "mobileNumber": "98765*****",  // partially masked
  "currency": "INR",
  "taxRegime": "NEW",
  "financialYearStartMonth": 4
}
```

### PUT /profile
```json
{
  "displayName": "Ravi Kumar",
  "dateOfBirth": "1985-04-15",   // full value accepted
  "panNumber": "ABCDE1234F",
  "mobileNumber": "9876543210",
  "currency": "INR",
  "taxRegime": "NEW"
}
```

---

## 4. Files Endpoints

### GET /files/queue
Live queue of all files currently processing or needing attention.

```json
{
  "items": [
    {
      "id": 42,
      "originalName": "HDFC_2025_01.pdf",
      "organizedPath": "Banks/HDFC/2025/January.pdf",
      "status": "Organized",
      "detectedBank": "HDFC",
      "wasEncrypted": false,
      "transactionCount": 117,
      "createdAt": "2025-01-15T10:30:00Z"
    },
    {
      "id": 43,
      "originalName": "union_2024_12.pdf",
      "status": "PasswordRequired",
      "detectedBank": "UnionBank",
      "wasEncrypted": true,
      "unlockMethod": null
    }
  ],
  "pendingCount": 1,
  "failedCount": 0
}
```

### GET /files/{id}
Single file detail with processing history.

### POST /files/{id}/unlock
User provides a password for a `PasswordRequired` file.

**Request:**
```json
{ "password": "ABCDE1234F" }
```

**Response:** `202 Accepted` (re-queues file for processing)
```json
{ "queued": true, "estimatedProcessingSeconds": 15 }
```

### GET /files/vault
List of all files in `.vault\`.

```json
{
  "totalFiles": 48,
  "totalSizeBytes": 125000000,
  "months": [
    {
      "month": "2025-01",
      "files": [
        { "name": "HDFC_2025_01.pdf", "sizeBytes": 2500000, "sha256": "abc..." }
      ]
    }
  ]
}
```

### GET /files/vault/verify
Run on-demand SHA-256 integrity check of all vault files.

**Response:**
```json
{
  "verified": 46,
  "missing": [],
  "corrupted": []
}
```

### POST /files/{id}/reprocess
Re-queue a previously Failed or Removed file for processing (re-drop use case).

**Request:**
```json
{ "createNewBatch": true }
```

**Response:** `202 Accepted`
```json
{ "queued": true }
```

### DELETE /files/{id}/remove-transactions
After user confirms deletion prompt.

**Request:**
```json
{ "confirmed": true }
```

**Response:** `200 OK`
```json
{ "transactionsRemoved": 117, "fileStatus": "Removed" }
```

---

## 5. Accounts Endpoints

### GET /accounts
Returns flat list of all accounts.

### GET /coa/tree
Returns Chart of Accounts as nested tree.

```json
{
  "nodes": [
    {
      "id": 1, "code": "1000", "name": "Assets", "type": "Asset",
      "children": [
        { "id": 2, "code": "1100", "name": "Bank Accounts", "type": "Asset",
          "children": [
            { "id": 3, "code": "1101", "name": "HDFC Savings", "type": "Asset",
              "balance": 245678.50, "children": [] }
          ]
        }
      ]
    }
  ]
}
```

### POST /accounts
Create new account (bank account, credit card, loan, etc.)

### PATCH /accounts/{id}
Update account details.

### DELETE /accounts/{id}
Deactivate account. If transactions exist:
```json
{ "error": "Account has 234 transactions. Deactivate instead?", "code": "HAS_TRANSACTIONS" }
```

---

## 6. Transactions Endpoints

### GET /transactions
```
GET /transactions?page=1&pageSize=50&from=2025-01-01&to=2025-01-31
                 &accountId=3&category=Food&memberId=1&search=SWIGGY
```

**Response:**
```json
{
  "total": 234,
  "page": 1,
  "pageSize": 50,
  "items": [
    {
      "id": 1001,
      "date": "2025-01-15",
      "description": "SWIGGY ORDER 123",
      "debit": 485.00,
      "credit": 0,
      "balance": 245678.50,
      "category": "Food & Dining",
      "accountName": "HDFC Savings",
      "status": "Posted",
      "isManual": false
    }
  ]
}
```

### POST /transactions/manual
Create a cash or manual transaction.

**Request:**
```json
{
  "date": "2025-01-20",
  "description": "Grocery shopping at D-Mart",
  "amount": 1250.00,
  "type": "Expense",
  "accountId": 3,
  "categoryCode": "5200",
  "notes": "Monthly grocery run"
}
```

### PATCH /transactions/{id}
Update description, category, or notes.

### DELETE /transactions/{id}
Soft-delete a transaction (requires confirmation if approved).

---

## 7. Proposals Endpoints

### GET /proposals
Pending transaction proposals awaiting approval.

```json
{
  "total": 45,
  "items": [
    {
      "id": 201,
      "date": "2025-01-05",
      "description": "HDFC BANK NEFT 12345",
      "amount": 50000.00,
      "suggestedCategory": "Salary",
      "confidence": 0.92,
      "lines": [
        { "accountCode": "1101", "accountName": "HDFC Savings", "type": "Debit", "amount": 50000 },
        { "accountCode": "4001", "accountName": "Salary Income", "type": "Credit", "amount": 50000 }
      ]
    }
  ]
}
```

### PATCH /proposals/{id}
Approve or modify a proposal.

**Request (approve):**
```json
{ "action": "approve" }
```

**Request (modify and approve):**
```json
{
  "action": "approve",
  "categoryCode": "4002",
  "description": "Salary Jan 2025"
}
```

**Request (reject):**
```json
{ "action": "reject", "reason": "Duplicate" }
```

### POST /proposals/bulk-approve
Approve multiple proposals at once.

```json
{ "ids": [201, 202, 203, 204] }
```

---

## 8. Reports Endpoints

All reports accept `?from=YYYY-MM-DD&to=YYYY-MM-DD&memberId=1` parameters.

| Method | Path | Description |
|---|---|---|
| GET | `/reports/summary` | Monthly income/expense/net summary |
| GET | `/reports/income-expense` | Detailed I&E statement |
| GET | `/reports/balance-sheet` | Point-in-time balance sheet |
| GET | `/reports/cash-flow` | Cash flow statement |
| GET | `/reports/net-worth` | Net worth trend data |
| GET | `/reports/categories` | Spending by category breakdown |
| GET | `/reports/tax-summary` | Interest, dividends, capital gains |
| GET | `/reports/budget-vs-actual` | Budget adherence |
| GET | `/reports/monthly-snapshots` | Month-over-month summary table |

**Export:**
```
GET /reports/income-expense?format=pdf&from=2025-04-01&to=2026-03-31
GET /reports/income-expense?format=csv&from=2025-04-01&to=2026-03-31
```

### Family Consolidated Report (v2)
```
GET /reports/net-worth?memberId=all
→ Aggregates across all active family members
→ Response includes per-member breakdown + consolidated total
```

---

## 9. Settings Endpoints

### GET /settings
Returns all app settings.

### PATCH /settings
Update one or more settings.

```json
{
  "privacyModeDefault": true,
  "ocrPreference": "WindowsFirst"
}
```

### POST /settings/pin/enable
Enable PIN protection.

**Request:** `{ "pin": "123456" }`
**Response:** `200 OK` `{ "pinEnabled": true }`

### POST /settings/pin/disable
**Request:** `{ "currentPin": "123456" }`

### POST /settings/pin/verify
**Request:** `{ "pin": "123456" }`
**Response:** `{ "valid": true }`

### POST /settings/llm
Save LLM provider configuration.

**Request:**
```json
{
  "providerName": "Gemini",
  "apiKey": "AIzaSy...",
  "textModel": "gemini-2.0-flash-exp",
  "visionModel": "gemini-2.0-flash-exp",
  "isDefault": true
}
```

### POST /settings/llm/test
Test API key connectivity.

---

## 10a. Lending Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/lending` | List all manual loans (with computed `balance_remaining`, `interest_accrued`) |
| POST | `/lending` | Create a new manual loan record |
| PUT | `/lending/{id}` | Update loan details |
| POST | `/lending/{id}/repayments` | Record a repayment (principal + interest split) |
| GET | `/lending/{id}/schedule` | Compute full repayment schedule with interest |
| POST | `/lending/{id}/settle` | Mark loan as fully settled |

**Response shape for `GET /lending`:**
```json
{
  "summary": {
    "totalLentOut": 42000,
    "totalOwed": 0,
    "overdue": 18000,
    "interestEarnedThisYear": 2100
  },
  "loans": [
    {
      "id": 1, "direction": "Lent", "counterpartyName": "Ravi Kumar",
      "principal": 15000, "balanceRemaining": 15000,
      "interestRate": 12, "interestMode": "Simple",
      "dueDate": "2025-04-15", "isOverdue": false
    }
  ]
}
```

---

## 10b. Folio / Portfolio Insights Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/insights/folio` | Portfolio breakdown + concentration warnings |
| GET | `/insights/folio/{holdingId}` | Detail for one holding (XIRR, return %) |

**Response shape for `GET /insights/folio`:**
```json
{
  "totalInvested": 850000,
  "breakdown": [
    { "category": "Equity Large-cap", "percentage": 62, "amount": 527000 },
    { "category": "Debt / Liquid",    "percentage": 12, "amount": 102000 }
  ],
  "concentrationAlerts": [
    {
      "holdingName": "HDFC Flexicap Fund",
      "percentage": 38,
      "message": "This fund makes up 38% of your portfolio. Consider diversifying.",
      "suggestion": "Nifty 50 Index Fund or Nifty Next 50 Index Fund"
    }
  ],
  "overlapAlerts": [
    {
      "fund1": "HDFC Top 100", "fund2": "ICICI Bluechip",
      "overlapEstimate": 70,
      "message": "These two funds hold similar stocks — you may be doubling up."
    }
  ],
  "disclaimer": "Informational only. Not financial advice."
}
```

---

## 10c. EMI & Prepayment Insights Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/insights/emi` | List all home loan profiles |
| GET | `/insights/emi/{loanId}` | Get loan profile details |
| PUT | `/insights/emi/{loanId}` | Update loan profile (override auto-detected values) |
| GET | `/insights/emi/{loanId}/prepayment` | Compute prepayment projections |

**Query params for `GET /insights/emi/{loanId}/prepayment`:**
- `extra` — extra monthly payment (integer, INR)
- `lumpsum` — one-time prepayment amount (integer, optional)

**Response shape:**
```json
{
  "loanId": 1, "lenderName": "HDFC Home Loan",
  "outstanding": 3200000, "annualRate": 8.5, "monthlyEmi": 28500,
  "currentSchedule": {
    "monthsRemaining": 204, "completionDate": "2042-02",
    "totalInterestPayable": 1840000
  },
  "boostedSchedule": {
    "extraPerMonth": 5000, "monthsRemaining": 152,
    "completionDate": "2037-06", "totalInterestPayable": 1320000,
    "interestSaved": 520000, "monthsSaved": 52
  },
  "plainEnglishSummary": "Paying ₹5,000 extra per month saves ₹5.2L in interest and closes your loan 4 years 8 months earlier."
}
```

---

## 10. Family Endpoints (v2 stub — stub returns 501 in v1)

| Method | Path | Description |
|---|---|---|
| GET | `/family/members` | List all family members |
| POST | `/family/members` | Add a family member |
| PUT | `/family/members/{id}` | Update member profile |
| DELETE | `/family/members/{id}` | Remove member (with transaction confirmation) |
| GET | `/family/members/{id}/summary` | Net worth + account summary for one member |

---

## 11. SignalR Events (FileStatusHub)

**Hub URL:** `/hubs/files`

**Client connection:**
```javascript
// frontend/src/hooks/useFileHub.js
const connection = new signalR.HubConnectionBuilder()
    .withUrl("/hubs/files")
    .withAutomaticReconnect()
    .build();
```

### Events Emitted by Server

| Event | Payload | When |
|---|---|---|
| `file.vaulted` | `{ fileId, fileName, sha256 }` | File copied to .vault |
| `file.detected` | `{ fileId, bank, confidence, isEncrypted }` | Detection complete |
| `file.parsing` | `{ fileId, method, pageCount }` | Parse started |
| `file.parsed` | `{ fileId, rowCount, confidence }` | Parse complete |
| `file.normalizing` | `{ fileId }` | Normalizing |
| `file.proposing` | `{ fileId, proposalCount }` | Proposals generated |
| `file.organized` | `{ fileId, organizedPath }` | File moved and indexed |
| `file.failed` | `{ fileId, stage, error }` | Pipeline failure |
| `file.pw_required` | `{ fileId, fileName, memberName? }` | All crack attempts failed |
| `file.removal_pending` | `{ fileId, organizedPath, txnCount }` | User deleted file |
| `proposal.created` | `{ count, batchId }` | New proposals awaiting review |

### Client → Server

| Method | Args | Description |
|---|---|---|
| `SubscribeToFile` | `fileId` | Subscribe to one file's events |
| `UnsubscribeFromFile` | `fileId` | Unsubscribe |

---

## 12. Health Endpoint

### GET /health
Used by WPF shell to know when Kestrel is ready.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "dbConnected": true,
  "ledgerDriveMounted": true,
  "queueDepth": 3
}
```
