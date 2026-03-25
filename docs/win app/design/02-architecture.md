# Ledger Desktop — System Architecture

**Version:** 1.0  
**Status:** Design Review

---

## 1. Process Model

Ledger Desktop runs as a **single Windows process**. There is no separate server process, no background service daemon, and no subprocess to manage at runtime (except the isolated cracker process, which is spawned on demand and killed after 30 seconds).

```
┌──────────────────────────────────────────────────────────┐
│              Ledger.exe  (Single .NET 9 Process)          │
│                                                            │
│  ┌─────────────────────┐   ┌───────────────────────────┐ │
│  │   WPF Shell Thread   │   │   ASP.NET Core IHost      │ │
│  │  MainWindow.xaml     │   │   (Kestrel on localhost)  │ │
│  │  WebView2 (Chromium) │◄──┤   Endpoints + SignalR Hub │ │
│  │  System Tray         │   │   Background Services     │ │
│  │  PinLockScreen.xaml  │   └──────────────┬────────────┘ │
│  └─────────────────────┘                  │               │
│                                    Thread Pool            │
│                          ┌───────────────────────────┐   │
│                          │  IHostedService workers:   │   │
│                          │  FileWatcherService        │   │
│                          │  ProcessingQueueService    │   │
│                          │  VaultSyncService          │   │
│                          └───────────────────────────┘   │
└──────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────┐
  │  Ledger.Shell.CrackerProcess.exe          │
  │  (Spawned on demand, sandboxed, no net)  │
  │  Named pipe IPC ↔ parent process         │
  │  Kill timeout: 30 seconds                │
  └──────────────────────────────────────────┘

  ┌──────────────────────────────────────────┐
  │  Ledger.ShellExtension.dll (COM in-proc) │
  │  Loaded by Windows Explorer process      │
  │  Read-only SQLite connection (no writes) │
  └──────────────────────────────────────────┘
```

### Why Single Process?
- Simpler MSIX packaging (one executable)
- No IPC complexity between shell and API
- EF Core + services share a single DI container
- WPF dispatcher and Kestrel coexist via `IHost` hosting model

---

## 2. Component Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Ledger.Shell (WPF)                          │
│                                                                      │
│  App.xaml.cs ──► IHost.StartAsync() ──► binds random localhost port │
│  MainWindow.xaml ──► WebView2 navigates to http://localhost:{port}/  │
│  LedgerBridge.cs ──► window.__ledger.* JS bridge                    │
│  AntiTamperGuard.cs (RELEASE) ──► anti-debug, no-inject             │
│  PinLockScreen.xaml ──► Argon2id PIN gate (if PIN enabled)          │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ IHost (in-process)
┌───────────────────────────▼─────────────────────────────────────────┐
│                       Ledger.Api (ASP.NET Core 9)                   │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Endpoint Groups (Minimal API)                                │   │
│  │  SetupEndpoints  ProfileEndpoints  FilesEndpoints            │   │
│  │  AccountsEndpoints  TransactionsEndpoints  ProposalsEndpoints│   │
│  │  ReportsEndpoints  BudgetsEndpoints  GoalsEndpoints          │   │
│  │  ChatEndpoints  SettingsEndpoints  FamilyEndpoints(v2)       │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌───────────────────┐  ┌──────────────────────────────────────┐   │
│  │  FileStatusHub     │  │  Background Services                 │   │
│  │  (SignalR)         │  │  FileWatcherService (FileSystemWatch)│   │
│  │  Events:           │  │  ProcessingQueueService (SemaphoreS.)│   │
│  │  file.detected     │  │  VaultSyncService (deletion handler) │   │
│  │  file.parsing      │  └──────────────────────────────────────┘   │
│  │  file.proposed     │                                              │
│  │  file.organized    │       wwwroot/ → React 19 production build  │
│  │  file.failed       │       Served as static files                │
│  │  file.pw_required  │                                              │
│  │  file.rm_confirm   │                                              │
│  └───────────────────┘                                              │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ DI Container
┌───────────────────────────▼─────────────────────────────────────────┐
│                     Ledger.Infrastructure                           │
│                                                                      │
│  Database/                   Security/                              │
│    LedgerDbContext             DatabaseKeyProvider (SQLCipher)       │
│    DbConnectionInterceptor     FieldEncryptor (AES-256-GCM)         │
│    FieldEncryptor              PinVaultService (Argon2id + DPAPI)   │
│    Migrations/                 SecureMemory (pinned byte arrays)     │
│                                PasswordCrackerService (child proc)  │
│  FileSystem/                                                         │
│    LedgerDriveManager        LLM/                                   │
│    VaultManager                ILlmProvider                         │
│    FileOrganizerService        GeminiProvider                       │
│                                OpenAIProvider                       │
│  Parsing/                      AnthropicProvider                    │
│    FileDetectorService         PrivacyTransformer                   │
│    OcrEngine (dual)                                                  │
│    Pdf/ (15+ bank parsers)   Notifications/                         │
│    Csv/ (7+ parsers)           ToastService                         │
│                                                                      │
│  Services/                   WindowsSearch/                         │
│    NormalizerService           SearchIndexService                   │
│    DeduplicationService        SearchPropertyWriter                 │
│    CategorizationService                                             │
│    ProposalService                                                   │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ EF Core 9
┌───────────────────────────▼─────────────────────────────────────────┐
│             SQLite + SQLCipher 4.6                                  │
│   Key = PBKDF2(MachineGuid + salt, 200k iter, SHA-256)             │
│        + optional Argon2id PIN factor                               │
│   Path: %AppData%\Roaming\LedgerApp\data\ledger.db                 │
└─────────────────────────────────────────────────────────────────────┘
                            │ Read-only mirror for Shell Extension
┌───────────────────────────▼─────────────────────────────────────────┐
│             Ledger.ShellExtension (COM DLL, Explorer-hosted)        │
│   LedgerOverlayHandler → reads FileRegistry.ShellOverlayState      │
│   LedgerContextMenu → "Add to LedgerDrive", "View in Ledger"       │
│   SearchPropertyHandler → writes IPropertyStore on organized files  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Project Layout

```
Ledger.Desktop.sln
├── Ledger.Shell/                    net9.0-windows (WPF)
│   ├── App.xaml.cs                  IHost startup, singleton mutex
│   ├── MainWindow.xaml(.cs)         WebView2 host
│   ├── PinLockScreen.xaml(.cs)      PIN overlay WPF window
│   ├── SplashScreen.xaml(.cs)       Loading splash while Kestrel starts
│   ├── TrayIcon.cs                  System.Windows.Forms.NotifyIcon
│   ├── Security/
│   │   └── AntiTamperGuard.cs
│   └── Bridge/
│       └── LedgerBridge.cs          COM-visible bridge object
│
├── Ledger.Api/                      net9.0
│   ├── Program.cs                   IHostBuilder, DI, middleware
│   ├── Features/
│   │   ├── SetupEndpoints.cs
│   │   ├── ProfileEndpoints.cs
│   │   ├── FilesEndpoints.cs
│   │   ├── AccountsEndpoints.cs
│   │   ├── TransactionsEndpoints.cs
│   │   ├── ProposalsEndpoints.cs
│   │   ├── ReportsEndpoints.cs
│   │   ├── BudgetsEndpoints.cs
│   │   ├── GoalsEndpoints.cs
│   │   ├── ChatEndpoints.cs
│   │   ├── SettingsEndpoints.cs
│   │   └── FamilyEndpoints.cs       (stub in v1, implemented v2)
│   ├── Hubs/
│   │   └── FileStatusHub.cs
│   ├── Background/
│   │   ├── FileWatcherService.cs
│   │   ├── ProcessingQueueService.cs
│   │   └── VaultSyncService.cs
│   └── wwwroot/                     React production build (at build time)
│
├── Ledger.Domain/                   net9.0 (no framework deps)
│   ├── Entities/                    All EF Core entity classes
│   │   ├── UserProfile.cs
│   │   ├── FamilyMember.cs          (v1: seeded with Self record)
│   │   ├── FileRegistry.cs
│   │   ├── ProcessingQueueItem.cs
│   │   ├── Account.cs
│   │   ├── Transaction.cs
│   │   ├── TransactionLine.cs
│   │   ├── ImportBatch.cs
│   │   └── ... (25+ entities)
│   ├── Enums/
│   │   ├── ProcessingStatus.cs
│   │   ├── ShellOverlayState.cs
│   │   ├── FamilyRelationship.cs
│   │   └── ...
│   └── Interfaces/
│       ├── IDocumentParser.cs
│       ├── ILlmProvider.cs
│       └── IBackgroundTaskQueue.cs
│
├── Ledger.Infrastructure/           net9.0
│   ├── Database/
│   │   ├── LedgerDbContext.cs
│   │   ├── DatabaseKeyProvider.cs
│   │   ├── DbConnectionInterceptor.cs
│   │   ├── FieldEncryptor.cs
│   │   └── Migrations/
│   ├── Security/
│   │   ├── PinVaultService.cs
│   │   ├── SecureMemory.cs
│   │   └── PasswordCrackerService.cs
│   ├── FileSystem/
│   │   ├── LedgerDriveManager.cs
│   │   ├── VaultManager.cs
│   │   └── FileOrganizerService.cs
│   ├── Parsing/
│   │   ├── FileDetectorService.cs
│   │   ├── Ocr/
│   │   │   └── OcrEngine.cs
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
│   │   ├── CategorizationService.cs
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
│       ├── SearchIndexService.cs
│       └── SearchPropertyWriter.cs
│
├── Ledger.Shell.CrackerProcess/     net9.0 (sandboxed exe)
│   └── Program.cs
│
├── Ledger.ShellExtension/           net9.0-windows (COM DLL)
│   ├── LedgerOverlayHandler.cs
│   ├── LedgerContextMenu.cs
│   └── SearchPropertyHandler.cs
│
├── Ledger.Shell.Package/            Windows Application Packaging Project
│   ├── Package.appxmanifest
│   └── Assets/
│
└── Ledger.Tests/                    net9.0 (xUnit 2.9)
    ├── Parsing/
    ├── Security/
    ├── Services/
    └── Fixtures/
```

---

## 4. Startup Sequence

```
1. App.xaml.cs: Application.OnStartup()
   ├── Acquire Global\LedgerApp mutex
   │     └── If fails: activate existing window via named pipe → exit
   ├── Show SplashScreen.xaml (WPF, non-WebView2)
   ├── Build IHost:
   │     ├── Register all DI services (Infrastructure, Api)
   │     ├── EF Core database migration (Database.MigrateAsync)
   │     ├── Seed default COA if first run
   │     └── Bind Kestrel on random ephemeral port
   ├── IHost.StartAsync():
   │     ├── FileWatcherService.StartAsync() → begins watching LedgerDrive
   │     ├── ProcessingQueueService.StartAsync() → resumes pending queue items
   │     └── VaultSyncService.StartAsync() → watches for deletions
   ├── AntiTamperGuard.Check() (RELEASE)
   ├── If PinEnabled:
   │     └── Show PinLockScreen.xaml → block until correct PIN
   ├── Create MainWindow → init WebView2 environment
   ├── Poll GET /health every 500ms
   └── On 200: navigate WebView2 to http://localhost:{port}/

2. React App loads:
   ├── Calls GET /setup/status
   │     └── If SetupComplete=false → show QuickStartWizard
   │     └── If SetupComplete=true → navigate to /dashboard
   └── Opens SignalR connection to /hubs/files
```

---

## 5. Data Flow: File Drop to Ledger

```
User drops HDFC_2025_01.pdf into LedgerDrive\

FileSystemWatcher.Created event
  └── FileWatcherService (debounce 2.5s)
        └── VaultManager.CopyToVaultAsync()
              └── Compute SHA-256
              └── Check FileRegistry for duplicate → skip if found
              └── Copy → .stash\2025-01\HDFC_2025_01.pdf
              └── INSERT FileRegistry { Hash, OriginalName, Status=Stashed }
        └── Enqueue ProcessingQueueItem

ProcessingQueueService (semaphore max 2)
  └── Stage 1: DETECT
        └── FileDetectorService.DetectAsync()
              → DetectionResult { BankName=HDFC, Confidence=0.95, IsEncrypted=false }
        └── SignalR: file.detected
  └── Stage 2: PARSE
        └── ParserRegistry.GetParser(HDFC_PDF) → HdfcPdfParser
        └── HdfcPdfParser.ParseAsync(stream)
              → ExtractionChain: TextLayer → Tables → (OCR if needed)
        └── ParseResult { Rows[120], Confidence=0.97, ExtractionMethod=TextLayer }
        └── SignalR: file.parsing
  └── Stage 3: NORMALIZE
        └── NormalizerService.Normalize(rows)
              → NormalizedTransaction[120]
  └── Stage 4: DEDUPLICATE
        └── DeduplicationService.FindDuplicates(rows)
              → 3 duplicates skipped
  └── Stage 5: CATEGORIZE
        └── CategorizationService.Categorize(rows)
              → Category assigned per row
  └── Stage 6: PROPOSE
        └── ProposalService.Generate(rows)
              → TransactionProposal[117] inserted to DB
        └── SignalR: file.proposed
  └── Stage 7: ORGANIZE
        └── FileOrganizerService.Organize(fileReg)
              → Move to Banks\HDFC\2025\January.pdf
              → Update FileRegistry.OrganizedPath, Status=Organized
        └── SearchPropertyWriter.WriteAsync(organizedPath, metadata)
        └── UPDATE FileRegistry.ShellOverlayState = Done
        └── SignalR: file.organized
        └── Toast: "HDFC Jan 2025 processed — 117 transactions pending review"
```

---

## 6. Dependency Injection Registration

```csharp
// Ledger.Api/Program.cs (simplified)
builder.Services
    // Infrastructure — Database
    .AddDbContext<LedgerDbContext>(opt => opt.UseSqlite())
    .AddSingleton<IDatabaseKeyProvider, DatabaseKeyProvider>()
    .AddSingleton<IFieldEncryptor, FieldEncryptor>()
    // Infrastructure — Security
    .AddSingleton<IPinVaultService, PinVaultService>()
    .AddSingleton<IPasswordCrackerService, PasswordCrackerService>()
    // Infrastructure — File System
    .AddSingleton<ILedgerDriveManager, LedgerDriveManager>()
    .AddSingleton<IVaultManager, VaultManager>()
    .AddSingleton<IFileOrganizerService, FileOrganizerService>()
    // Infrastructure — Parsing
    .AddSingleton<IFileDetectorService, FileDetectorService>()
    .AddSingleton<IOcrEngine, OcrEngine>()
    .AddSingleton<IParserRegistry, ParserRegistry>()
    // -- Individual parsers auto-registered via ParserRegistry scan
    // Infrastructure — Services
    .AddScoped<INormalizerService, NormalizerService>()
    .AddScoped<IDeduplicationService, DeduplicationService>()
    .AddScoped<ICategorizationService, CategorizationService>()
    .AddScoped<IProposalService, ProposalService>()
    // Infrastructure — LLM
    .AddSingleton<ILlmProviderFactory, LlmProviderFactory>()
    .AddSingleton<IPrivacyTransformer, PrivacyTransformer>()
    // Infrastructure — Notifications  
    .AddSingleton<IToastService, ToastService>()
    // Background Services
    .AddHostedService<FileWatcherService>()
    .AddHostedService<ProcessingQueueService>()
    .AddHostedService<VaultSyncService>()
    .AddSingleton<IBackgroundTaskQueue, DefaultBackgroundTaskQueue>()
    // SignalR
    .AddSignalR();
```

---

## 7. Technology Versions (Pinned)

| Package | Version | License |
|---|---|---|
| .NET | 9.0 | MIT |
| ASP.NET Core | 9.0 | MIT |
| EF Core | 9.0.x | MIT |
| SQLitePCLRaw.bundle_e_sqlcipher | 2.1.x | Apache 2 |
| PdfPig | 0.1.9 | MIT |
| Docnet.Core | 2.6.x | Apache 2 |
| Tesseract (.NET) | 5.2.x | Apache 2 |
| CsvHelper | 33.x | MS-PL/Apache 2 |
| ClosedXML | 0.102.x | MIT |
| ML.NET | 3.0.x | MIT |
| SharpShell | 2.7.x | MIT |
| Konscious.Security.Cryptography | 1.3.x | MIT |
| Microsoft.Web.WebView2 | 1.0.x | MS |
| Microsoft.Toolkit.Win32.UI.Notifications | 7.x | MIT |
| Polly | 8.x | BSD-3 |
| xUnit | 2.9.x | Apache 2 |
| Moq | 4.x | BSD-3 |
| FluentAssertions | 7.x | Apache 2 |

---

## 8. Platform Boundary & Cross-Platform Migration Path

> **Current stance:** Windows-only (v1 and v2). Cross-platform is an explicit non-goal for v1. This section documents which components create the Windows dependency and what a future migration to Tauri would require, so the migration cost is understood up-front and the design avoids unnecessary lock-in.

### 8.1 Windows-Specific Components

| Component | Why Windows-only | Removable? |
|---|---|---|
| **WPF** (`MainWindow.xaml`, `App.xaml.cs`) | Windows-only UI framework — no macOS/Linux support | Yes — entire shell replaced |
| **WebView2** (`Microsoft.Web.WebView2`) | Wraps Chromium Edge; Windows only | Yes — replaced by platform-native WebView |
| **Windows Shell integration** (`SharpShell`, `NotifyIcon`, `FileSystemWatcher` notifications) | Win32/COM APIs | Yes — platform-specific adapters |
| **MSIX packaging** | Windows App Installer format | Yes — replaced by Tauri bundler |
| **`FileAttributes.ReadOnly`** (vault immutability) | Works on all platforms | No change needed |
| **SQLCipher** (`SQLitePCLRaw.bundle_e_sqlcipher`) | Cross-platform | No change needed |
| **ASP.NET Core API** (all routes, business logic, parsers) | Cross-platform .NET | No change needed |
| **React UI** (`frontend/src/`) | Browser-rendered; platform-agnostic | No change needed |

### 8.2 Cross-Platform Shell Options

Three viable paths if cross-platform becomes a requirement:

| Option | Shell technology | React UI | C# parsers | Effort vs WPF baseline |
|---|---|---|---|---|
| **A — Electron** | Node.js / Chromium | Zero changes | Sidecar process | Medium — Electron APIs differ from Win32; PDF parsing needs JS shim or sidecar |
| **B — .NET MAUI** | MAUI + `BlazorWebView` | Zero changes | In-process (same .NET) | Medium — MAUI macOS is solid; Linux is community-only and rough |
| **C — Tauri** *(recommended)* | Rust shell + OS WebView | Zero changes | Sidecar process | Low-Medium — Rust learning curve; smallest binary (~10 MB vs ~150 MB Electron) |

**Recommendation:** Tauri is the least disruptive future migration. The React UI and all .NET business logic remain unchanged. Only the WPF shell (~500 lines) is rewritten in Rust.

### 8.3 Tauri Migration: What Changes vs What Stays

| Layer | WPF (current) | Tauri equivalent | Migration effort |
|---|---|---|---|
| Shell host | `App.xaml.cs` + `MainWindow.xaml` | `src-tauri/src/main.rs` | **Medium** — ~300–500 lines Rust |
| File watcher | `FileSystemWatcher` (.NET) | `notify` crate (Rust) | **Low** — 1:1 equivalent API |
| System tray | `NotifyIcon` (WPF) | `tauri-plugin-system-tray` | **Low** — Tauri plugin |
| API base URL injection | `window.LEDGER_API_BASE` via WebView2 | Same pattern via Tauri `window.__TAURI__` bridge | **Trivial** |
| Vault file operations | `System.IO` | Tauri `fs` plugin or Rust `std::fs` | **Low** |
| App packaging | MSIX + WiX | Tauri bundler (`.msi`, `.dmg`, `.AppImage`) | **Zero** — Tauri handles it |
| ASP.NET Core API | In-process `IHost` inside WPF | .NET sidecar process spawned by Tauri | **Low-Medium** — spawn + lifecycle management (~50 lines) |
| React UI | `wwwroot/` served by Kestrel → WebView2 | Same — served by Kestrel sidecar → OS WebView | **Zero changes** |
| SQLite / SQLCipher DB | `Microsoft.Data.Sqlite` | Same — .NET sidecar owns the DB | **Zero changes** |
| All parsers & business logic | C# in-process | C# in sidecar process | **Zero changes** |

### 8.4 Tauri Sidecar Pattern (for reference)

In Tauri, the ASP.NET Core API runs as a separate self-contained process that Tauri spawns at startup:

```
Tauri shell (Rust, ~10 MB)
  │
  ├─ spawn ──► LedgerApi.exe  (ASP.NET Core, self-contained .NET publish)
  │                │  listens on localhost:{dynamicPort}
  │                │
  └─ WebView ◄────── window.LEDGER_API_BASE = "http://localhost:{port}"
                        │
                      React app (unchanged)
```

- Tauri's sidecar API handles spawn + kill automatically on app open/close
- Port negotiation: pick a free port at startup, pass to both Tauri (for injection) and the .NET process (via `--urls` argument)
- The `.NET` app is published as a single-file self-contained executable bundled alongside the Tauri app

### 8.5 Design Choices That Keep Migration Cost Low

The following decisions in the current WPF design deliberately avoid deeper lock-in:

| Design choice | Why it helps |
|---|---|
| ASP.NET Core API is the single source of truth — WPF only hosts it | Decouples all business logic from the shell |
| `window.LEDGER_API_BASE` injection pattern (not hardcoded port) | Tauri can inject the same variable — no React code changes |
| React UI has no WPF/Win32 dependencies | Runs unchanged in any WebView |
| SQLite file is portable | Same DB file works across platforms |
| `IFileWatcher` abstraction over `FileSystemWatcher` | Swap implementation without touching callers |
