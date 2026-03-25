# Plan: Ledger Desktop — Secure On-Premises Windows App

**What:** Replace the current web SaaS + onboarding flow with a self-contained Windows desktop application. The user drops financial files into a watched "LedgerDrive" folder; the app auto-parses, auto-organizes, and builds their ledger hands-free — no onboarding wizard, encrypted local database, optional privacy-first LLM.

**How:** WPF shell hosts React via WebView2; full .NET 9 ASP.NET Core API (rewrite from Python) handles all logic; SQLCipher encrypts the database; a background `FileWatcherService` drives the entire import pipeline automatically.

---

## Core Technology Stack

| Layer | Technology | Why |
|---|---|---|
| Host shell | WPF + WebView2 (.NET 9, `net9.0-windows`) | Native Windows, WebView2 = Chromium-grade React rendering |
| API backend | ASP.NET Core 9 Minimal API (in-process) | Single process, no subprocess management |
| UI | React 19 + Vite 6 + Tailwind CSS 4 | Existing frontend, serve from `wwwroot/` |
| Real-time | SignalR Core (WebSockets) | Live file status feed to React |
| Database | SQLite + **SQLCipher 4.6** | Encrypted at rest, zero server dependency |
| ORM | EF Core 9 + `SQLitePCLRaw.bundle_e_sqlcipher` | Full migrations, type-safe queries |
| PDF text | **PdfPig 0.1.9** (MIT) | Best open-source text/table extraction |
| PDF render | **Docnet.Core 2.6** (PDFium/Apache 2) | Chrome's PDF engine — renders pages, decrypts password-protected PDFs |
| OCR primary | **Windows.Media.Ocr** (WinRT, built-in) | Zero install, offline, fast, supports 50+ languages incl. Hindi |
| OCR fallback | **Tesseract 5.x LSTM** (`Tesseract` NuGet) | Highest accuracy for tabular bank statement data |
| CSV | **CsvHelper 33** | Industry standard, RFC 4180 compliant |
| XLSX | **ClosedXML 0.102** | Some banks export Excel statements |
| ML/Categorize | **ML.NET 3.0** `TextClassification` | On-device, no cloud, learns from user corrections |
| Shell hooks | **SharpShell 2.7** | Overlay icons, context menus, property handlers |
| PIN hashing | **Konscious.Security.Cryptography** (Argon2id) | OWASP-recommended KDF for PINs |
| Notifications | **Microsoft.Toolkit.Win32.UI.Notifications** | Windows toast notifications |
| Distribution | **MSIX** + AppInstaller delta updates | Store-compatible, signed, sandboxed |

---

## Architecture Diagram

```
┌────────────────────────────────────────────────────────────────┐
│                    WPF Shell (net9.0-windows)                  │
│  WebView2 ──► http://localhost:{port}    System Tray           │
│  JS Bridge  ← window.__ledger.*         IPC: pickFolder()      │
└────────────────────────┬───────────────────────────────────────┘
                         │  Same process: IHost in-process
┌────────────────────────▼───────────────────────────────────────┐
│               ASP.NET Core 9 Minimal API (Ledger.Api)          │
│                                                                  │
│  Endpoints: /profile /files /accounts /transactions /reports   │
│             /budgets /goals /chat /setup /settings             │
│  SignalR Hub: /hubs/files  (real-time file status)             │
│  Static files: /  (React build served from wwwroot/)           │
│                                                                  │
│  Background Services (IHostedService):                          │
│    FileWatcherService    ─ FileSystemWatcher on LedgerDrive     │
│    ProcessingQueueService ─ concurrent pipeline dispatcher      │
│    VaultSyncService      ─ handles file deletions               │
│                                                                  │
│  Core Services:                                                  │
│    FileDetectorService   NormalizerService   CategorizationSvc  │
│    PasswordCrackerService  FileOrganizerService  LlmProviderSvc │
│    DeduplicationService  PrivacyTransformer  ProposalService    │
│                                                                  │
│  Parsers (IDocumentParser):                                     │
│    HdfcPdfParser  SbiPdfParser  IciciPdfParser  + 12 more      │
│    HdfcCsvParser  SbiCsvParser  GenericCsvParser + 6 more      │
│                                                                  │
│  Infrastructure:                                                 │
│    LedgerDbContext (SQLCipher, EF Core)                         │
│    VaultManager  LedgerDriveManager                             │
│    DPAPI key store  SQLCipher key derivation                    │
└────────────────────────┬───────────────────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────────────────┐
│                 Encrypted SQLite (SQLCipher 4.6)               │
│    Key = PBKDF2(WindowsMachineGuid + salt, 200k iter, SHA256)  │
│    Optional PIN = Argon2id 2nd factor                          │
│    Column-level: DOB/PAN/Mobile = AES-256-GCM                  │
│    Location: %AppData%\Roaming\LedgerApp\data\ledger.db        │
└────────────────────────────────────────────────────────────────┘

    External (opt-in, privacy-anonymized first):
    ┌──────────────────────────────────────────┐
    │  Gemini / OpenAI / Anthropic API          │
    │  ← PrivacyTransformer anonymizes first    │
    │  ← HTTPS cert pinning enforced            │
    └──────────────────────────────────────────┘

    Isolated child process (no disk/network):
    ┌──────────────────────────────────────────┐
    │  Ledger.Shell.CrackerProcess.exe          │
    │  Named-pipe IPC ← file bytes in           │
    │  Named-pipe IPC → cracked password out    │
    │  30-second timeout, killed after          │
    └──────────────────────────────────────────┘

    Windows Shell Extension (COM DLL):
    ┌──────────────────────────────────────────┐
    │  Ledger.ShellExtension.dll                │
    │  - Overlay icons (Syncing/Done/Error)     │
    │  - Context menu (Add to LedgerDrive)      │
    │  - Windows Search crawl scope             │
    │  - Custom property metadata               │
    └──────────────────────────────────────────┘
```

---

## Solution Structure

```
Ledger.Desktop.sln
├── Ledger.Shell/                    WPF host, net9.0-windows
│   ├── App.xaml.cs                  IHost startup, mutex, tray
│   ├── MainWindow.xaml              WebView2 fullscreen host
│   ├── Security/
│   │   └── AntiTamperGuard.cs       Anti-debug, DLL injection block
│   └── Bridge/
│       └── LedgerBridge.cs          JS ↔ WPF COM bridge
├── Ledger.Api/                      ASP.NET Core 9 Minimal API
│   ├── Features/                    Endpoint groups per domain
│   ├── Hubs/
│   │   └── FileStatusHub.cs         SignalR hub
│   └── Background/
│       ├── FileWatcherService.cs
│       └── ProcessingQueueService.cs
├── Ledger.Domain/                   Pure C# — zero framework deps
│   ├── Entities/                    25+ EF Core entity classes
│   ├── Enums/
│   └── Interfaces/
├── Ledger.Infrastructure/           EF Core, parsers, services
│   ├── Database/
│   │   ├── LedgerDbContext.cs
│   │   ├── DatabaseKeyProvider.cs   SQLCipher key derivation
│   │   └── FieldEncryptor.cs        AES-256-GCM column crypto
│   ├── Security/
│   │   ├── PinVaultService.cs       Argon2id + Windows Credential Store
│   │   ├── SecureMemory.cs          Pinned memory, zero-on-dispose
│   │   └── PasswordCrackerService.cs Isolated cracker process spawn
│   ├── FileSystem/
│   │   ├── LedgerDriveManager.cs
│   │   ├── VaultManager.cs
│   │   └── FileOrganizerService.cs
│   ├── Parsing/
│   │   ├── FileDetectorService.cs
│   │   ├── Ocr/
│   │   │   └── OcrEngine.cs         Windows OCR + Tesseract dual-engine
│   │   ├── Pdf/
│   │   │   ├── HdfcPdfParser.cs
│   │   │   ├── SbiPdfParser.cs
│   │   │   ├── IciciPdfParser.cs
│   │   │   ├── AxisPdfParser.cs
│   │   │   ├── KotakPdfParser.cs
│   │   │   ├── IdfcPdfParser.cs
│   │   │   ├── UnionPdfParser.cs
│   │   │   ├── IndusIndPdfParser.cs
│   │   │   ├── YesCcPdfParser.cs
│   │   │   ├── HdfcCcPdfParser.cs
│   │   │   ├── IciciCcPdfParser.cs
│   │   │   └── CasCamsParser.cs
│   │   └── Csv/
│   │       ├── GenericCsvParser.cs
│   │       ├── HdfcCsvParser.cs
│   │       ├── SbiCsvParser.cs
│   │       ├── IciciCsvParser.cs
│   │       ├── AxisCsvParser.cs
│   │       ├── KotakCsvParser.cs
│   │       └── ZerodhaCsvParser.cs
│   ├── Services/
│   │   ├── NormalizerService.cs
│   │   ├── DeduplicationService.cs
│   │   ├── CategorizationService.cs  (ML.NET)
│   │   └── ProposalService.cs
│   ├── LLM/
│   │   ├── ILlmProvider.cs
│   │   ├── GeminiProvider.cs
│   │   ├── OpenAIProvider.cs
│   │   ├── AnthropicProvider.cs
│   │   └── PrivacyTransformer.cs
│   ├── Notifications/
│   │   └── ToastService.cs
│   └── WindowsSearch/
│       └── SearchIndexService.cs
├── Ledger.Shell.CrackerProcess/     Isolated sandboxed exe
│   └── Program.cs                  Named-pipe listener, PDFium cracker
├── Ledger.ShellExtension/          COM-visible Shell DLL
│   ├── LedgerOverlayHandler.cs     SharpShell overlay icons
│   ├── LedgerContextMenu.cs        SharpShell context menu
│   └── SearchPropertyHandler.cs   Windows Search metadata
├── Ledger.Shell.Package/           MSIX packaging project
│   └── Package.appxmanifest
└── Ledger.Tests/                   xUnit 2.9
    ├── Parsing/                    Per-bank parser tests (fixture PDFs)
    ├── Security/                   SQLCipher, field encryption
    └── Services/                   Normalizer, dedup, categorization
```

---

## Phase 0 — Solution Bootstrap

1. Create `Ledger.Desktop.sln` with all projects listed above
2. **Single-process model**: `Ledger.Shell/App.xaml.cs` builds `IHost` with Ledger.Api services → starts `IHost.StartAsync()` → creates `MainWindow` (WebView2) → opens `http://localhost:{ephemeral_port}/`
   - Ephemeral port stored in `app_settings` table after first valid bind
   - Mutex (`Global\LedgerApp`) prevents second instance; second activates first via named pipe
3. WPF↔JavaScript bridge via `CoreWebView2.AddHostObjectToScript("__ledger", bridge)`:
   - `pickFolder()` → `FolderBrowserDialog` → returns chosen path
   - `openExplorer(path)` → `Process.Start("explorer.exe", path)`
   - `getAppVersion()` → assembly version
   - `showNotification(title, body)` → WinRT toast
   - `openFile(fileHash)` → navigates React to that file's record

---

## Phase 1 — Security Foundation (Build First)

4. **SQLCipher key derivation** (`DatabaseKeyProvider.cs`):
   - Read `HKLM\SOFTWARE\Microsoft\Cryptography\MachineGuid`
   - `Rfc2898DeriveBytes(machineGuid + appSalt, staticSalt16, 200_000, SHA256)` → 32-byte key
   - If PIN enabled: `Rfc2898DeriveBytes(PIN + derivedKey, pinSalt, 200_000, SHA256)` — PIN is 2nd factor
   - Apply as `PRAGMA key="x'<hexkey>'"` via `DbConnectionInterceptor.ConnectionOpenedAsync`
   - DB path: `%AppData%\Roaming\LedgerApp\data\ledger.db`

5. **PIN management** (`PinVaultService.cs`):
   - Hash: `Argon2id(PIN, randomSalt, iterations=4, memory=65536KB, parallelism=1)` → 32-byte hash
   - Stored in Windows Credential Store: `PasswordVault.Add(new PasswordCredential("LedgerApp", "pin_hash", hashHex))`
   - PIN state (enabled/disabled) in `app_settings` table
   - On app launch: WPF `PinLockScreen.xaml` overlays WebView2 until correct PIN entered

6. **Memory hardening** (`SecureMemory.cs`):
   - All passwords: `SecureString` — never plain `string`
   - DB key + PIN hash: `GCHandle.Alloc(bytes, GCHandleType.Pinned)` → `Array.Clear()` + `handle.Free()` in finally
   - `RuntimeHelpers.PrepareConstrainedRegions()` around sensitive try/finally
   - `SecureString` conversions: `Marshal.SecureStringToBSTR` + `Marshal.ZeroFreeBSTR` after use
   - LLM API keys: `ProtectedData.Protect(keyBytes, entropy, DataProtectionScope.CurrentUser)` stored as base64

7. **Anti-tamper** (`AntiTamperGuard.cs`, RELEASE only):
   - `Debugger.IsAttached` → terminate silently if true
   - P/Invoke `SetProcessMitigationPolicy(PROCESS_CREATION_MITIGATION_POLICY_BLOCK_NON_MICROSOFT_BINARIES)` → blocks DLL injection

8. **Audit log**: every security event fires into `audit_log` table via fire-and-forget background queue — DB unlock, PIN verify/change, LLM call (privacy mode state logged), file events, password crack result (never the attempted passwords)

---

## Phase 2 — Database & Domain Entities

9. Port all 25+ SQLAlchemy models → EF Core 9 entities in `Ledger.Domain/Entities/`
   - **New**: `FileRegistry` (`FileHash` SHA-256, `OriginalName`, `VaultPath`, `OrganizedPath`, `DetectedBank`, `DetectedFileType`, `ProcessingStatus` enum, `WasEncrypted`, `UnlockMethod`, `ImportBatchId`, `ShellOverlayState`)
   - **New**: `ProcessingQueueItem` (`FileRegistryId`, `Status`, `Attempts`, `LastError`, `LockedAt`)
   - **Modified** `UserProfile`: add `DateOfBirthEncrypted` (AES-256-GCM blob), `PanNumberEncrypted` (AES-256-GCM blob), `MobileNumberEncrypted`, `PasswordHint` (plain, display-safe)
   - **Modified** `AppSettings`: add `LedgerDrivePath`, `SetupComplete`, `PinEnabled`, `PinSalt`, `OcrPreference`, `PrivacyModeDefault`

10. EF Core migrations in `Ledger.Infrastructure/Migrations/` — initial migration covers full schema, applied via `Database.MigrateAsync()` in `IHost` startup lifespan

11. **Sensitive field encryption** (`FieldEncryptor.cs`):
    - DOB, PAN, Mobile: `AES-256-GCM` using derived DB key — doubly protected (column AES + SQLCipher database AES)
    - Storage format: `nonce(12) || ciphertext || tag(16)` → base64
    - EF Core `ValueConverter<string, string>` applies transparently on read/write

---

## Phase 3 — LedgerDrive & File Watching

12. **LedgerDriveManager** — creates on first Quick-Start setup:
    ```
    {chosen}\LedgerDrive\
      .vault\          [Hidden + System attrs]
      .unprocessed\    [Hidden]
      Banks\
        HDFC\  SBI\  ICICI\  Axis\  ...
      CreditCards\
        HDFC_CC\  ICICI_CC\  ...
      Investments\
        Zerodha\  CAMS\  ...
      Loans\
      Insurance\
      Other\
    ```
    - `ledger_profile.json` in root: `{ "display_name": "...", "hint": "..." }` — display-safe only
    - `desktop.ini` sets custom folder icon + description

13. **VaultManager**:
    - On new file: SHA-256 → duplicate check via `FileRegistry` → copy to `.vault\{YYYY-MM}\{filename}` → insert `FileRegistry` row `Status = Vaulted`
    - `.vault\` is write-once; never auto-deleted
    - On file deleted: look up by original path → emit `file.removal_pending` SignalR → UI confirmation → soft-delete transactions on confirm

14. **FileWatcherService** (IHostedService):
    - `FileSystemWatcher` on LedgerDrive root, `IncludeSubdirectories = false`
    - 2.5-second debounce (handles in-progress large file copies)
    - On startup: scan for unprocessed files (crash recovery)

15. **ProcessingQueueService** (IHostedService):
    - Max 2 concurrent files (`SemaphoreSlim(2)`)
    - Per-file pipeline stages: `Detect → [PasswordCrack?] → Parse → Normalize → Dedup → Categorize → Propose → Organize → IndexSearch`
    - Failed files (3 attempts): moves to `.unprocessed\` + SignalR `file.failed` + Windows toast
    - SignalR broadcast at every stage → React FilesPage live progress

---

## Phase 4 — PDF & Document Intelligence Engine

16. **FileDetectorService**:
    - Magic bytes: `%PDF` → PDF; `PK\x03\x04` → XLSX; BOM/UTF-8 → CSV
    - Filename regex dictionary (HDFC*.pdf → HDFC_PDF, etc.)
    - PDF keyword scan (first 4KB via PdfPig page 1 text): bank keyword signatures
    - Encryption check via Docnet.Core — throws on locked PDF
    - Returns `DetectionResult { SourceType, BankName, Confidence, IsEncrypted }`
    - Confidence < 0.70 → flag for manual review or LLM vision detection

17. **PasswordCrackerService**:
    - Spawns `Ledger.Shell.CrackerProcess.exe` as sandboxed child:
      - Windows Job Object blocks all network access
      - Communication: named pipe `\\.\pipe\LedgerCracker_{guid}`
      - Parent enforces 30-second kill timeout
    - Attempt list (built from decrypted UserProfile fields, held in SecureString, cleared after list generation):
      1. PAN: uppercase, lowercase, last 5 chars
      2. DOB: `DDMMYYYY`, `DDMMYY`, `YYYY`, `DDMM`, `MMYYYY`, `D/M/YYYY`
      3. First name lowercase, full name nospace lowercase
      4. Mobile: 10-digit, last 4 digits
      5. Combos: `{firstname}{DDMMYYYY}`, `{pan}{dob}`, `{name}{year}`
    - Child uses `Docnet.Core.DocLib.Instance.LoadDocument(bytes, password)` — PDFium native decryption
    - Passwords never written to disk, never in logs, cleared immediately after pipe send

18. **PDF parsers** (`IDocumentParser` interface, one class per bank):
    - Extraction strategy chain per parser:
      1. PdfPig text layer + regex
      2. PdfPig table extraction (bounding box grouping)
      3. PDFium render → Windows.Media.Ocr (primary OCR, 300 DPI)
      4. PDFium render → Tesseract 5 LSTM (fallback, if Windows OCR confidence < 0.75)
      5. LLM Vision (opt-in, privacy-anonymized) — only if all above fail
    - Banks: `Hdfc`, `Sbi`, `Icici`, `Axis`, `Kotak`, `Idfc`, `Union`, `IndusInd`, `YesCc`, `HdfcCc`, `IciciCc`, `CasCams`

19. **OCR Engine** (`OcrEngine.cs`):
    - PDFium renders page to BGRA bitmap (300 DPI)
    - **Windows.Media.Ocr path**: `OcrEngine.TryCreateFromUserProfileLanguages()` → `RecognizeAsync(SoftwareBitmap)` → `OcrResult.Lines[].Text`
    - **Tesseract path**: `TesseractEngine("./tessdata", "eng+hin", EngineMode.LstmOnly)` with HOCR output for bounding boxes
    - If Tesseract HOCR mean confidence < 60% → flag for LLM Vision

20. **CSV parsers** (`CsvHelper 33`, lenient mode):
    - `GenericCsvParser`: header keyword matching (Date/Narration/Withdrawal/Deposit/Balance)
    - Bank-specific: `HdfcCsv`, `SbiCsv`, `IciciCsv`, `AxisCsv`, `KotakCsv`, `ZerodhaCsv`
    - XLSX: `ClosedXML 0.102` for Excel statements

---

## Phase 5 — Normalization, ML Categorization, Proposals

21. **NormalizerService**:
    - Multi-format date parsing: `DD/MM/YYYY`, `DD-Mon-YY`, `YYYY-MM-DD`
    - Indian lakh decimal normalization
    - Output: `NormalizedTransaction { Date, ValueDate, Description, Debit, Credit, Balance, Currency, RawRow, ParserConfidence }`

22. **DeduplicationService**:
    - Fingerprint: `SHA256($"{date:yyyyMMdd}|{Math.Abs(debit-credit):F2}|{NormalizeDesc(description)}")`
    - Fuzzy match: Levenshtein on description for near-duplicates (same amount ±1 day, description similarity > 85%)

23. **CategorizationService**:
    - Pass 1: regex rules from `user_category_rules` ordered by priority
    - Pass 2: ML.NET `TextClassificationPredictor` (initial model seeded from 500+ labeled entries in `seed_training.tsv`)
    - Retrains incrementally when user approves/changes a proposal category
    - Model stored: `%AppData%\Roaming\LedgerApp\ml\categorization_v{n}.zip`

24. **ProposalService**: generates double-entry journal proposals (debit/credit COA accounts) for each normalized transaction; surfaces as "Pending Review" on Dashboard

---

## Phase 6 — Windows Shell Integration (Full)

25. **`Ledger.ShellExtension` COM DLL** (registered via MSIX custom action):

    **a) File Overlay Icons** (`LedgerOverlayHandler : SharpIconOverlayHandler`):
    - Registered: `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\ShellIconOverlayIdentifiers\`
    - 4 states: `LedgerSyncing` (spinner), `LedgerDone` (green check), `LedgerError` (red X), `LedgerMissing` (yellow warning)
    - `GetOverlayIndex()`: reads `FileRegistry.ShellOverlayState` via read-only SQLite connection (no writes from shell process)
    - Custom `.ico` files bundled in extension resources
    - Installer warns if overlay slots are full (Windows limit: 15)

    **b) Context Menu** (`LedgerContextMenu : SharpContextMenu`):
    - Registered for `HKCR\*\shellex\ContextMenuHandlers\LedgerContextMenu`
    - Path check: shows "View in Ledger" / "View Vault Copy" only inside LedgerDrive
    - Shows "Add to LedgerDrive" when right-clicking any file anywhere in Explorer
    - "View in Ledger" → activates app + `__ledger.openFile(fileHash)`

    **c) Custom Folder Icon**: `desktop.ini` + `Folder.ico` written by `LedgerDriveManager.InitializeFolderAsync()`

26. **Windows Search Indexing** (`SearchIndexService.cs`):
    - `ISearchManager` COM → `ICrawlScopeManager.AddUserScopeRule(ledgerDrivePath, true)` registers LedgerDrive
    - Post-parse: writes custom `IPropertyStore` metadata on organized files:
      - `BankName`, `AccountType`, `StatementYear`, `TransactionCount`
    - Files appear in Windows Search: "HDFC statements 2024" → results with metadata

27. **Windows Toast Notifications** (`ToastService.cs`):
    - `AppNotificationManager.Default.Register()` on startup
    - Toasts: file detected, processed, needs password (inline "Enter Password" action), failed, low-disk warning for `.vault\`
    - `AppNotificationManager.NotificationInvoked` → `CoreWebView2.PostWebMessageAsJson` to React

---

## Phase 7 — LLM & Privacy Engine

28. **LLM providers** (`ILlmProvider` interface):
    - `GeminiProvider`, `OpenAIProvider`, `AnthropicProvider` — `HttpClient` + `Polly` (3x exponential backoff)
    - **HTTPS cert pinning**: `HttpClientHandler.ServerCertificateCustomValidationCallback` validates leaf cert SHA-256 fingerprint against hardcoded values for `api.openai.com`, `generativelanguage.googleapis.com`, `api.anthropic.com`
    - API keys: decrypted from DPAPI blob only for HTTP request duration; `SecureString` intermediate; cleared immediately

29. **PrivacyTransformer**:
    - Session-scoped reverse-mapping dictionary in pinned memory block
    - Rules before any LLM send:
      1. Named entities → `PERSON_A`, `PERSON_B`
      2. Account numbers → `ACC_1`, `ACC_2`
      3. Amounts bucketed: `< ₹1k=MICRO`, `₹1k-10k=SMALL`, `₹10k-1L=MEDIUM`, `₹1L+=LARGE`
      4. PAN pattern → `PANXXXXXX`
      5. Mobile numbers → `MOBILE_1`
    - Chat endpoint: Privacy Mode ON → all context through transformer first
    - Privacy Mode OFF: explicit red warning banner in React "Real transaction data will be sent to [Provider]"

---

## Phase 8 — API Endpoints & Frontend

30. **API endpoint groups** (`Ledger.Api/Features/`):
    - `SetupEndpoints`: `GET /setup/status`, `POST /setup/complete`
    - `ProfileEndpoints`: `GET /profile`, `PUT /profile`
    - `FilesEndpoints`: `GET /files/queue`, `GET /files/{id}`, `POST /files/{id}/unlock`, `GET /files/vault`, `GET /files/vault/verify`, `POST /files/{id}/reprocess`, `DELETE /files/{id}/remove-transactions`
    - `AccountsEndpoints`: COA CRUD, `GET /coa/tree`
    - `TransactionsEndpoints`: all CRUD + `POST /transactions/manual`
    - `ProposalsEndpoints`: review, approve, reject
    - `ReportsEndpoints`: 20+ report endpoints (income/expense, balance sheet, tax, cash flow, etc.)
    - `BudgetsEndpoints`, `GoalsEndpoints`, `ChatEndpoints`
    - `SettingsEndpoints`: PIN management, LLM config, Privacy Mode toggle, LedgerDrive path

31. **React frontend changes**:
    - **Delete** `OnboardingV2.jsx` — replaced by QuickStartWizard
    - **New** `QuickStartWizard.jsx` (2 screens): Screen 1 = folder picker + Name + DOB + mobile; Screen 2 = success → dashboard
    - **New** `ProfilePage.jsx`: DisplayName, DOB, PAN (masked `****1234A`), Mobile, Currency, Tax Regime, PIN setup, LLM + Privacy Mode settings
    - **New** `FilesPage.jsx`: SignalR live feed, status badges, inline password entry, vault viewer
    - **Modify** `PersonalDashboard.jsx`: add "Recent File Activity" widget, "Pending Review" badge, quick actions (+ Cash Transaction, Open LedgerDrive)
    - **Modify** `App.jsx`: new nav (Dashboard | Files | Accounts | Transactions | Reports | Budgets | Goals | Chat | Settings), first-launch gate via `GET /setup/status`, `@microsoft/signalr` client
    - **Modify** `ChatWidget.jsx`: Privacy Mode toggle, red warning banner when OFF

---

## Phase 9 — Packaging, Signing & Distribution

32. **MSIX project** (`Ledger.Shell.Package/`):
    - Bundles: WPF shell, API DLL, ShellExtension DLL, Tesseract tessdata (`eng.traineddata` + `hin.traineddata`), React production build (`wwwroot/`), ML.NET seed model
    - `Package.appxmanifest` `comServer` extension: registers `Ledger.ShellExtension` COM classes
    - `AppInstaller` file for delta updates: toast notification when update available
    - **Code signing**: EV cert required for overlay icons + MSIX Store; use Azure Trusted Signing in CI

33. **WebView2 bootstrap** (`MainWindow.xaml.cs`):
    - `CoreWebView2Environment.CreateAsync()` → user data at `%AppData%\LedgerApp\webview2\`
    - Shows WPF loading splash, polls `GET /health` every 500ms → navigates on 200
    - Policy: all non-localhost navigations blocked via `NavigationStarting` event handler

---

## Security Summary

| Threat | Mitigation |
|---|---|
| DB stolen from disk | SQLCipher 4.6 (AES-256-CBC, PBKDF2 200k iter) — opaque binary |
| Sensitive column data | AES-256-GCM column encryption on top of SQLCipher |
| API keys leaked | Windows DPAPI per-user, SecureString in memory, HTTPS cert pinning |
| PIN brute-force | Argon2id (64MB memory, 4 iter) — infeasible to brute-force |
| PAN/DOB in logs | SecureString never serialized; audit log records result only |
| Memory scraping | GCHandle.Pinned + Array.Clear() + ZeroFreeBSTR |
| DLL injection | SetProcessMitigationPolicy blocks non-Microsoft binaries (RELEASE) |
| LLM data exfiltration | PrivacyTransformer anonymizes first; cert pinning prevents MITM |
| PDF password cracking | Isolated sandboxed child process, no disk/network, 30s kill timeout |
| Real data in LLM chat | Explicit consent + red banner when Privacy Mode OFF |
| File deletion = data loss | Two-stage: SignalR confirm → user approves → soft delete; `.vault\` immutable |

---

## Verification Checklist

1. `dotnet build Ledger.Desktop.sln -c Release` — zero errors, zero warnings
2. `dotnet test Ledger.Tests/` — all parsers produce expected row counts against fixture PDFs
3. Drop real HDFC PDF → `.vault\` copy, overlay icon Syncing→Done, organized to `Banks\HDFC\2025\`, transactions proposed
4. Drop Union Bank encrypted PDF → cracker succeeds with DOB-based password, organized correctly
5. Drop unknown file → moves to `.unprocessed\`, toast + yellow overlay + inline password prompt in UI
6. Delete organized file → UI shows transaction count confirmation before any DB change
7. `strings ledger.db | head` → zero readable SQL (SQLCipher verification)
8. Enable PIN → restart → PIN lock screen appears, wrong PIN rejected, correct PIN unlocks
9. Process Monitor trace: no plaintext passwords written to filesystem or registry during cracking
10. Privacy Mode ON + LLM chat → Fiddler/Wireshark shows bucketed amounts, `PERSON_A` not real names
11. Right-click any Explorer file → "Add to LedgerDrive" visible in context menu
12. Windows Search: type "HDFC 2025" in Start → organized PDFs appear with BankName metadata
13. Fresh VM MSIX install → Quick-Start Wizard → folder created → end-to-end works

---

## Key Decisions

- **Full .NET 9 rewrite** — Python backend retired; all 15+ parsers ported to C#
- **PDFium (Docnet.Core) + PdfPig** — PDFium for rendering/decryption, PdfPig for text layout
- **OCR dual-engine** — Windows.Media.Ocr primary (zero install), Tesseract 5 LSTM fallback (bundled, ~30MB adds)
- **Isolated cracker process** — password cracking sandboxed; PAN/DOB never logged
- **SharpShell overlay + context menu** — requires EV code signing; handled by MSIX custom action
- **Windows Search** — LedgerDrive registered as crawl scope; custom property metadata written post-parse
- **ledger_profile.json** — display-safe only (name + hint); DOB/PAN stay encrypted in DB exclusively
- **`.vault\` immutable** — write-once backup; user can only clear manually via Settings

## Out of Scope (v1)

- Multi-machine sync or cloud backup
- Android/iOS companion app
- GST filing or ITR export
- Multi-user / family profiles (UI — schema is ready)
- Voice commands
- Broker API live feed integrations

---

## Family Mode (v2) — Design Hooks in v1

Family Mode is a planned v2 feature. The v1 schema and codebase are pre-extended so no migration is needed when v2 ships.

**v1 schema hooks already in place:**
- `family_members` table seeded with `id=1, relationship='Self'` at install
- All core tables (`accounts`, `transactions`, `file_registry`, `bank_accounts`, `credit_cards`, `budgets`, `goals`, `net_worth_history`) have a nullable `family_member_id` FK from migration 0001
- `family_mode_enabled` key in `app_settings` defaults to `false`
- `FileRegistry.attributed_to_member_id` column present from v1

**What v2 adds (no schema migration needed):**
- Family member CRUD UI + `POST/PUT/DELETE /family/members` endpoints
- `Family/{MemberName}/` watched subfolders inside LedgerDrive
- File attribution from folder path → `attributed_to_member_id`
- Password cracking: tries attributed member's credentials first
- "Family View" dashboard toggle (consolidated net worth)
- `?memberId=all` consolidated queries on all report endpoints
- Per-member reports, budgets, and goals

**Design document:** See `docs/win app/design/10-family-mode.md` for the complete family mode design.
