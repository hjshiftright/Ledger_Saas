# Ledger Desktop — Requirements

**Version:** 1.0  
**Status:** Design Review

---

## 1. Functional Requirements

### 1.1 Setup & First Launch

| ID | Requirement | Priority |
|---|---|---|
| F-001 | App shows a 2-screen Quick-Start Wizard on first launch (before any files processed) | Must |
| F-002 | Screen 1: folder picker for LedgerDrive location + display name + DOB + mobile | Must |
| F-003 | Screen 2: success confirmation + "Open LedgerDrive" shortcut | Must |
| F-004 | After setup, app navigates directly to Dashboard — no further onboarding | Must |
| F-005 | App creates LedgerDrive folder structure on demand (not requiring admin rights) | Must |
| F-006 | `ledger_profile.json` written to LedgerDrive root with display-safe name and hint only | Must |
| F-007 | Profile page allows updating personal details (name, DOB, PAN, mobile) post-setup | Must |

### 1.2 LedgerDrive & File Watching

| ID | Requirement | Priority |
|---|---|---|
| F-010 | App monitors LedgerDrive root folder continuously via OS file system events | Must |
| F-011 | Any new file dropped in LedgerDrive root is automatically picked up and queued | Must |
| F-012 | App debounces file events 2.5 seconds to handle in-progress large file copies | Must |
| F-013 | On app startup, scanning catches any files added while app was closed | Must |
| F-014 | Duplicate file detection uses SHA-256 content hash (not filename) | Must |
| F-014a | Duplicate of already-organized file: delete dropped copy silently + toast "already imported" | Must |
| F-014b | Duplicate of a previously-failed file: offer Retry or Skip via toast | Must |
| F-014c | Duplicate of a previously-removed file (transactions deleted): offer Re-import or Skip | Must |
| F-014d | Duplicate of PasswordRequired file: surface existing password prompt, do not create second record | Must |
| F-014e | Different content but same bank+period as an existing organized statement: warn before proposals | Should |
| F-015 | Maximum 2 files processed concurrently | Should |
| F-016 | Processing queue is persisted in DB — survives app crash/restart | Must |

### 1.3 Vault & Backup

| ID | Requirement | Priority |
|---|---|---|
| F-020 | Every new unique file is immediately copied to `.vault\.incoming\{YYYY-MM-DD}\` before any processing begins | Must |
| F-020a | After organization, the vault copy is moved to mirror the organized path: `.vault\{same relative path as organized destination}` | Must |
| F-020b | `FileRegistry.vault_path` is updated atomically when the vault copy moves from staging to final position | Must |
| F-021 | `.vault\` folder is set Hidden + System — not visible in normal Explorer browsing | Must |
| F-022 | Vault files are set ReadOnly and are never modified or deleted by the app | Must |
| F-023 | User can view vault contents (file list, sizes, drop dates) in the Files page in-app | Should |
| F-024 | User can clear vault from Settings with explicit confirmation | Should |
| F-024a | User can trigger on-demand SHA-256 integrity check of all vault files from Settings | Should |
| F-024b | Vault structure mirrors organized folder structure so users can navigate and restore files without the app | Must |

### 1.4 File Detection

| ID | Requirement | Priority |
|---|---|---|
| F-030 | App detects file type (PDF / CSV / XLSX) from magic bytes, not just extension | Must |
| F-031 | Bank/institution detected from filename regex patterns (HDFC*.pdf → HDFC Bank) | Must |
| F-032 | Bank/institution confirmed from PDF content keywords (first 4KB text scan) | Must |
| F-033 | Detection confidence score computed (0.0–1.0) — low confidence files flagged | Must |
| F-034 | Encrypted PDFs detected and flagged before parse attempt | Must |
| F-035 | Undetected/unsupported file types moved to `.unprocessed\` with status `Unsupported` | Must |

### 1.5 Password Candidate Matching

> **Terminology note:** The app does not "crack" or brute-force passwords. It generates a deterministic, finite list of candidate passwords from the user's own personal data (PAN, DOB, name, mobile) — the exact values Indian banks use when generating PDF passwords for their customers.

| ID | Requirement | Priority |
|---|---|---|
| F-040 | Encrypted PDFs tried with a deterministic candidate list derived from the user's own profile fields | Must |
| F-041 | Candidates include: PAN variants, DOB format combinations, first/full name variants, mobile variants, and standard combos | Must |
| F-042 | Candidate matching runs in an isolated child process with no network/disk write access | Must |
| F-043 | Attempt timeout: 30 seconds. File moves to `.unprocessed\` on timeout | Must |
| F-044 | Successfully matched password used immediately for parsing; never stored anywhere | Must |
| F-045 | If no candidate matches, user is prompted via toast "We couldn't unlock [filename] — tap to enter the password" | Must |
| F-046 | User can enter password in Files page inline form; app re-attempts parse immediately | Must |
| F-047 | In Family Mode (v2): candidates built from the attributed family member's profile first, then primary user's profile | Future |

### 1.6 Document Parsing

| ID | Requirement | Priority |
|---|---|---|
| F-050 | PDF parsers support: HDFC, SBI, ICICI, Axis, Kotak, IDFC, Union, IndusInd, YES CC, HDFC CC, ICICI CC | Must |
| F-051 | Mutual fund parsers support: CAMS CAS statement | Must |
| F-052 | CSV parsers support: HDFC, SBI, ICICI, Axis, Kotak, Zerodha, generic auto-detect | Must |
| F-053 | XLSX support: generic Excel statement parser | Should |
| F-054 | Extraction chain: text layer → table extraction → Windows OCR → Tesseract OCR → LLM Vision | Must |
| F-055 | Each parser extraction reports confidence score per row | Must |
| F-056 | Low-confidence rows flagged for user review in Proposals | Should |

### 1.7 Data Processing Pipeline

| ID | Requirement | Priority |
|---|---|---|
| F-060 | Normalization: date format unification, decimal/lakh handling, currency detection | Must |
| F-061 | Deduplication: SHA-256 fingerprinting + fuzzy near-duplicate detection | Must |
| F-062 | Categorization: regex rules first, ML.NET text classifier second | Must |
| F-063 | ML model retrains incrementally when user approves or corrects a category | Should |
| F-064 | Double-entry proposals generated for every normalized transaction | Must |
| F-065 | Proposals viewable in Proposals page with confidence score and suggested category | Must |
| F-066 | User can approve, edit-then-approve, or reject individual proposals | Must |
| F-067 | Approved transactions permanently committed to ledger in one DB transaction | Must |
| F-067a | Bulk actions in Proposals page: Approve All, Approve High Confidence (≥ 95%), Approve Selected | Must |
| F-067b | Setting: `auto_approve_threshold` — proposals at or above threshold auto-committed (default: OFF) | Should |
| F-067c | Auto-approved transactions flagged `is_auto_approved = true` with visible "Auto" badge | Should |
| F-067d | Auto-approve exclusions (always manual regardless of score): first-seen payees, Uncategorized, amount > configurable limit, inter-account transfers, credit card reversals | Must |

### 1.8 File Organization

| ID | Requirement | Priority |
|---|---|---|
| F-070 | After parse, bank account files moved to: `Assets\Banks\{Bank}\{Year}\{Month}.pdf` | Must |
| F-070a | Home loan / mortgage files moved to: `Assets\House\{Lender}\{Year}\{Month}.pdf` | Must |
| F-070b | Investment files (stocks, MF, FD) moved to: `Assets\Investments\{Provider}\{Year}\` | Must |
| F-070c | Cash / manual entries recorded under: `Assets\Cash\` | Should |
| F-071 | Credit card files → `CreditCards\{CardName_LastFour}\{Year}\{Month}.pdf` | Must |
| F-072 | Other loan files (vehicle, personal, etc.) → `Loans\{Lender}\{Year}\` | Must |
| F-073 | Name collisions resolved by appending `_2`, `_3`, etc. | Must |
| F-074 | `FileRegistry` DB record updated with organized path | Must |
| F-075 | Shell overlay icon updated to Done (green check) after organization | Must |

### 1.9 File Deletion Handling

| ID | Requirement | Priority |
|---|---|---|
| F-080 | If user deletes an organized file from LedgerDrive, app detects the deletion | Must |
| F-081 | App prompts user with count of transactions that will be removed | Must |
| F-082 | Transactions are soft-deleted only after explicit user confirmation | Must |
| F-083 | Original in `.vault\` is never deleted as part of this flow | Must |

### 1.10 Manual Transactions

| ID | Requirement | Priority |
|---|---|---|
| F-090 | User can create manual cash/other transactions via a form in the UI | Must |
| F-091 | Manual transactions require: date, amount, description, account, category | Must |
| F-092 | Manual transactions participate in reports, budgets, and net-worth calculations | Must |

### 1.10a Manual Lending Tracker

Track money lent to or borrowed from friends/family — outside bank statements.

| ID | Requirement | Priority |
|---|---|---|
| F-093 | User can record a manual loan: borrower/lender name, principal, date, optional interest rate, repayment schedule | Must |
| F-094 | App tracks each partial repayment (principal + interest split) and running balance | Must |
| F-095 | Interest calculation modes: simple interest, compound monthly, no interest | Must |
| F-096 | Lending dashboard shows: total lent out, total owed to user, overdue loans, total interest earned/paid | Should |
| F-097 | Loan entries appear in Net Worth as assets (money lent) or liabilities (money borrowed) | Must |
| F-098 | User can mark a loan as settled; settled loans archived (not deleted) | Must |
| F-099 | Reminder: configurable due-date toast "₹5,000 from Ravi's loan is due in 3 days" | Should |

### 1.11 Accounts & COA

| ID | Requirement | Priority |
|---|---|---|
| F-100 | Default Chart of Accounts seeded on first run (Indian COA template) | Must |
| F-101 | User can add, edit, deactivate bank accounts and credit cards | Must |
| F-102 | User can remove accounts (with confirmation, if transactions exist) | Must |
| F-103 | Brokerage accounts, loans, FDs, insurance can be added | Should |

### 1.12 Reporting

| ID | Requirement | Priority |
|---|---|---|
| F-110 | Income & Expense statement (month/quarter/year) | Must |
| F-111 | Balance Sheet (assets and liabilities snapshot) | Must |
| F-112 | Net Worth trend over time | Must |
| F-113 | Cash Flow statement | Must |
| F-114 | Category-wise spending breakdown | Must |
| F-115 | Tax summary (capital gains, dividends, interest income) | Should |
| F-116 | Budget vs Actual comparison | Must |
| F-117 | All reports exportable as PDF or CSV | Should |

### 1.13 Chatbot

| ID | Requirement | Priority |
|---|---|---|
| F-120 | In-app conversational chatbot with live ledger data context | Should |
| F-121 | Privacy Mode must be configurable before any LLM call | Must |
| F-122 | Privacy Mode OFF requires explicit user acknowledgement | Must |
| F-123 | Chat available without LLM (rule-based quick answers) in offline mode | Nice |

### 1.14 Windows Shell Integration

| ID | Requirement | Priority |
|---|---|---|
| F-130 | File overlay icon shows Syncing/Done/Error/Missing states in Explorer | Should |
| F-131 | Right-click any file in Explorer → "Add to LedgerDrive" context menu item | Should |
| F-132 | System tray icon: "Open Ledger", "Scan Now", "Exit" | Must |
| F-133 | Toast notifications: file processed, file needs password, errors | Must |
| F-134 | LedgerDrive folder has custom icon + description in Explorer | Should |
| F-135 | Windows Search can find LedgerDrive files by bank name, year, month | Nice |

### 1.15 UX Language Standards

Every user-facing string — labels, buttons, toasts, status text, empty states, confirmation dialogs — must use plain, conversational language. Technical terms, internal status codes, and system jargon must never appear in the UI.

**Principle:** Write as if explaining to a family member who has never used accounting software.

| ID | Requirement | Priority |
|---|---|---|
| F-140 | No internal status codes (e.g. `Vaulted`, `PasswordRequired`, `NF-001`) in any visible UI text | Must |
| F-141 | File pipeline statuses shown in conversational English (see UX language map below) | Must |
| F-142 | Error messages explain what happened and what the user should do — never show raw exceptions or stack traces | Must |
| F-143 | Confirmation dialogs state the consequence in plain terms ("This will remove 117 transactions from your ledger") | Must |
| F-144 | Empty states use encouraging, actionable language ("Drop a bank statement here to get started") | Must |
| F-145 | All button labels use action verbs in plain English ("Save changes", "Unlock this file", "Yes, remove them") | Must |
| F-146 | Toast notifications read as a person talking to the user, not as a system log entry | Must |

**UX Language Map — File Status:**

| Internal Status | Displayed As |
|---|---|
| `Vaulted` | "Saved safely" |
| `Detecting` | "Figuring out what this is…" |
| `PasswordRequired` | "We need your password for this file" |
| `Parsing` | "Reading your statement…" |
| `Normalized` | "Cleaning up the numbers…" |
| `Deduplicating` | "Checking for duplicates…" |
| `Categorizing` | "Sorting transactions into categories…" |
| `Proposing` | "Getting ready for your review…" |
| `Organized` | "Done ✓" |
| `Failed` | "Couldn't process this file" |
| `Unsupported` | "We don't support this file type yet" |

**UX Language Map — Toast Notifications:**

| Event | Displayed As |
|---|---|
| File processed | "HDFC January 2025 is ready — 117 transactions waiting for your review" |
| Password needed | "We couldn't unlock [filename]. Tap here to enter the password." |
| Parse failed | "We had trouble reading [filename]. You can try again or skip it." |
| Duplicate dropped | "You already imported this file — skipping it." |
| Update available | "A new version of Ledger is ready to install." |

### 1.17 Folio / Portfolio Concentration Insights

Alert users when their portfolio is over-concentrated and suggest diversification.

| ID | Requirement | Priority |
|---|---|---|
| F-160 | App aggregates mutual fund + stock holdings from Investments into a single Folio view | Must |
| F-161 | Folio view shows holdings breakdown by: asset class (equity/debt/hybrid), sector, individual stock/fund | Must |
| F-162 | Concentration alert: if any single fund or stock > 30% of total invested value, show a warning dashlet | Must |
| F-163 | Overlap detection: if user holds multiple large-cap equity MF schemes from same benchmark, alert "These funds hold similar stocks — consider consolidating" | Should |
| F-164 | Rebalance suggestion: for MF portfolios, suggest moving over-weight positions into index funds (e.g. Nifty 50 / Nifty Next 50 index funds) with a plain-English rationale | Should |
| F-165 | Suggestions are educational, not financial advice — always include a disclaimer | Must |
| F-166 | Folio dashlet shows XIRR / absolute return per holding where price data is available | Should |

### 1.18 EMI & Loan Prepayment Insights

Help users understand the impact of making extra EMI payments on home loans.

| ID | Requirement | Priority |
|---|---|---|
| F-170 | For any home loan account, user can enter or confirm: outstanding principal, interest rate, remaining term, EMI amount | Must |
| F-171 | "Pay extra & finish early" calculator: user enters an extra monthly amount and the app shows the new payoff date and total interest saved | Must |
| F-172 | Prepayment dashlet shows side-by-side: current schedule (months left, total interest) vs. boosted schedule | Must |
| F-173 | Interactive slider: drag extra EMI amount (₹0 – ₹50,000) and see payoff date update in real time | Should |
| F-174 | Lump-sum prepayment variant: "If I pay ₹1L today, how much sooner will I be debt-free?" | Should |
| F-175 | Savings highlighted in plain English: "Paying ₹5,000 extra per month saves ₹3.2L in interest and closes the loan 4 years earlier" | Must |
| F-176 | EMI dashlet auto-populates values from parsed loan statements; user can override | Should |

### 1.16 Customizable Dashboard (Dashlets)

| ID | Requirement | Priority |
|---|---|---|
| F-150 | Dashboard is composed of independently movable, addable, and removable panels (dashlets) | Must |
| F-151 | User can drag dashlets to any position on the dashboard grid | Must |
| F-152 | User can resize dashlets (small / medium / large) by dragging the resize handle | Should |
| F-153 | User can add dashlets from a "+ Add card" picker that shows all available dashlets | Must |
| F-154 | User can remove any dashlet via a remove button on the dashlet header | Must |
| F-155 | Dashboard layout persists between sessions (saved to app_settings as JSON) | Must |
| F-156 | "Reset to default" option restores the factory dashboard layout | Should |
| F-157 | Layout auto-adjusts when window is resized (responsive grid) | Must |
| F-158 | Dashboard page is labelled "Your Financial Picture" or equivalent plain-language title | Should |

---

## 2. Non-Functional Requirements

### 2.1 Performance

| ID | Requirement | Target |
|---|---|---|
| NF-001 | App startup to interactive dashboard | < 5 seconds on i5 / 8GB RAM |
| NF-002 | Single PDF parse (text layer, < 20 pages) | < 3 seconds |
| NF-003 | Single PDF parse (OCR, 20 pages) | < 30 seconds |
| NF-004 | Processing queue not blocking UI thread | Always (background service) |
| NF-005 | Concurrent file processing | Max 2 simultaneous |
| NF-006 | DB query response for transaction list (5000 rows) | < 200ms |

### 2.2 Security

| ID | Requirement |
|---|---|
| NF-010 | Database encrypted with SQLCipher 4.6 (AES-256-CBC, PBKDF2 200k iterations) |
| NF-011 | Sensitive columns (DOB, PAN, Mobile) additionally AES-256-GCM encrypted |
| NF-012 | DB encryption key derived from machine hardware GUID + compile-time salt |
| NF-013 | Optional PIN (Argon2id) as second factor for DB key |
| NF-014 | All passwords (PDF, user PIN) held only in `SecureString` or pinned byte arrays |
| NF-015 | Passwords never written to log files, DB audit tables, or temp files |
| NF-016 | LLM API keys encrypted with Windows DPAPI (per-user scope) |
| NF-017 | Anti-debug gate in RELEASE builds (app terminates if debugger attached) |
| NF-018 | DLL injection protection via `SetProcessMitigationPolicy` |
| NF-019 | All external HTTPS calls use certificate pinning for known LLM providers |
| NF-020 | Audit log captures all security-relevant events |

### 2.3 Reliability

| ID | Requirement |
|---|---|
| NF-030 | Processing queue survives app crash — resumes on next launch |
| NF-031 | DB writes use EF Core transactions — no partial commits |
| NF-032 | Vault copy completed before any processing begins on a file |
| NF-033 | If organizer fails after parse, file stays in root with `Parsed` status — not lost |

### 2.4 Usability

| ID | Requirement |
|---|---|
| NF-040 | No IT skills required — installer (MSIX) and first-use setup is self-guiding |
| NF-041 | All error states surfaced in plain English with actionable guidance |
| NF-042 | "Needs Password" files never silently fail — always visible in Files page |
| NF-043 | Deletion of ledger data requires minimum 2 user confirmations |

### 2.5 Maintainability & Extensibility

| ID | Requirement |
|---|---|
| NF-050 | All parsers implement `IDocumentParser` — adding new bank = 1 new class |
| NF-051 | `FamilyMemberId` FK present (nullable) on all core entities from v1 migration 0001 |
| NF-052 | `FileRegistry.AttributedToMemberId` present from v1 for future family attribution |
| NF-053 | All services are DI-registered interfaces — testable via mock injection |
| NF-054 | Parser test fixtures from `backend/tests/fixtures/` ported to `Ledger.Tests` |

### 2.6 Privacy

| ID | Requirement |
|---|---|
| NF-060 | Zero network calls made by default (no telemetry, no update check without user action) |
| NF-061 | LLM calls only made on explicit user opt-in per-batch or via chat |
| NF-062 | Privacy Mode ON (default): PrivacyTransformer applied to all LLM payloads |
| NF-063 | `ledger_profile.json` contains no sensitive fields (no PAN, no full DOB) |
| NF-064 | No analytics or crash-reporting SDK included |

---

## 3. Constraints

| Constraint | Detail |
|---|---|
| OS | Windows 10 22H2+ (x64) or Windows 11. WebView2 runtime required (bundled or evergreen). |
| .NET | .NET 9 runtime (bundled in MSIX) |
| Disk | ~200MB install (incl. Tesseract tessdata). ~50MB DB per year of statements (typical). |
| Network | None required at runtime. Only for LLM calls (opt-in) and MSIX updates (opt-in). |
| Code signing | EV certificate required for SharpShell overlay icons + MSIX Store distribution |
| Admin rights | Not required for install (per-user MSIX). Required only for SharpShell COM registration (handled automatically by MSIX custom action). |
| SQLCipher | `SQLitePCLRaw.bundle_e_sqlcipher` NuGet — Apache 2.0 license |

---

## 4. Family Mode Requirements (v2 — Future)

These are captured here as future requirements to ensure v1 schema and architecture are extensible:

| ID | Requirement |
|---|---|
| FM-001 | User can add family member profiles (spouse, child, parent, other) with name, DOB, PAN, mobile |
| FM-002 | Each family member's credentials stored encrypted using the same column-level AES-GCM as primary user |
| FM-003 | LedgerDrive contains `Family/{MemberName}/` subfolders; files dropped there are attributed to that member |
| FM-004 | Password cracking for family files uses that member's credentials first, then falls back to primary |
| FM-005 | If all cracks fail, toast: "Password needed for [filename] — likely belonging to [MemberName]" |
| FM-006 | Dashboard shows "My View" / "Family View" toggle |
| FM-007 | Family View shows consolidated net worth across all members |
| FM-008 | All reports filterable by `?memberId=` parameter or `all` for consolidated |
| FM-009 | Goals and budgets can be scoped to a specific member or shared family |
| FM-010 | FileWatcher extended to watch `Family/*` subfolders in addition to root |
| FM-011 | Family member can be removed; associated transactions are soft-deleted with confirmation |
