# Ledger Desktop — File Intelligence Engine

**Version:** 1.0  
**Status:** Design Review

---

## 1. Overview

The File Intelligence Engine is the core value proposition of Ledger Desktop. It turns raw dropped files into structured, categorized, double-entry journal transactions — fully automatically. The engine runs as a background hosted service and progresses each file through a deterministic pipeline of stages.

---

## 2. LedgerDrive Folder Structure

Created by `LedgerDriveManager.InitializeFolderAsync()` after Quick-Start Wizard completion.

```
{chosen_path}\LedgerDrive\
│
├── [Files dropped here by user — auto-processed]
│
├── .vault\                    [HIDDEN + SYSTEM]
│   ├── .incoming\             ← Staging area — every dropped file lands here first
│   │   └── 2025-01-15\
│   │       └── HDFC_raw.pdf   (ReadOnly, awaiting organization)
│   ├── Assets\                ← Mirrors organized folder tree (see §4.2)
│   │   ├── Banks\HDFC\2025\
│   │   └── Investments\CAMS\2025\
│   └── CreditCards\
│
├── .unprocessed\              [HIDDEN]
│   ├── unknown_file.pdf       (unsupported format)
│   └── encrypted_union.pdf    (all candidate attempts failed)
│
├── Assets\
│   ├── Banks\                 ← Bank account statements
│   │   ├── HDFC\
│   │   │   ├── 2024\
│   │   │   │   ├── January.pdf
│   │   │   │   └── February.pdf
│   │   │   └── 2025\
│   │   ├── SBI\
│   │   ├── ICICI\
│   │   ├── Axis\
│   │   ├── Kotak\
│   │   ├── IDFC\
│   │   ├── UnionBank\
│   │   └── IndusInd\
│   │
│   ├── Cash\                  ← Manual cash entries / petty cash
│   │
│   ├── Investments\           ← Stocks, mutual funds, FDs, ETFs
│   │   ├── Zerodha\
│   │   └── CAMS\
│   │
│   └── House\                 ← Home loan statements, property docs
│       ├── HDFC_HomeLoan\
│       └── SBI_HomeLoan\
│
├── CreditCards\
│   ├── HDFC_CC_1234\
│   ├── ICICI_CC_5678\
│   └── YES_CC_9012\
│
├── Loans\                     ← Vehicle loan, personal loan, etc. (non-home)
│   └── SBI_CarLoan\
│
├── Insurance\
│
├── Other\
│
├── Family\                    [v2 — created when Family Mode enabled]
│   ├── Priya\                 [spouse drop-zone]
│   │   ├── Assets\
│   │   └── CreditCards\
│   └── Rohan\                 [child]
│
├── ledger_profile.json        [Display-safe: {display_name, hint}]
├── desktop.ini                [Custom folder icon settings]
└── Folder.ico                 [LedgerDrive custom icon]
```

### Hidden Folder Attributes
```csharp
// LedgerDriveManager.cs
var vaultDir = new DirectoryInfo(vaultPath);
vaultDir.Attributes |= FileAttributes.Hidden | FileAttributes.System;
```

---

## 3. File Watcher Service

### 3.1 FileWatcherService (IHostedService)

```
Watch scope:    LedgerDrive\ (root only — IncludeSubdirectories = false in v1)
Watch scope v2: LedgerDrive\ + LedgerDrive\Family\*\ (one level deep)
Filter:         *.* (type determined inside pipeline)
Events:         Created, Renamed (new extension after copy), Deleted
```

**Debounce Pattern (handles large file copies):**
```
File copy begins → Created event fires (file still open by OS)
  └── Start CancellationTokenSource with 2500ms delay
      └── If another event for same file within 2500ms → reset timer
      └── On timer expiry: check file is not locked (retry 3x, 500ms apart)
              → If locked: retry after 2s (max 10 retries = 20 seconds)
              → If repeatedly locked: mark as Failed("File locked"), notify user
              → If unlocked: proceed to pipeline
```

**Startup Scan (Crash Recovery):**
```csharp
// On service start, scan for files with no FileRegistry record
var knownFiles = await _db.FileRegistry
    .Select(f => f.OriginalPath).ToHashSetAsync();
foreach (var file in Directory.EnumerateFiles(ledgerDrivePath, "*.*"))
{
    if (!knownFiles.Contains(file) && !IsHiddenSystemFile(file))
        _queue.Enqueue(new ProcessingWorkItem { FilePath = file });
}
```

### 3.2 Family Mode Watcher (v2)
```
// When family_mode_enabled = true:
foreach (var memberDir in Directory.GetDirectories(familySubPath))
{
    var memberName = Path.GetFileName(memberDir);
    var member = await ResolveFamilyMember(memberName);
    if (member != null)
        _watchers.Add(CreateWatcher(memberDir, attributedMemberId: member.Id));
}
```

---

## 4. Vault Manager

### 4.1 Responsibilities
1. Compute SHA-256 hash of incoming file
2. Resolve the re-drop scenario — see § 4.4 Duplicate & Re-drop Handling
3. Copy original to `.vault\{YYYY-MM}\{filename}` (collision-safe naming)
4. Set `FileAttributes.ReadOnly` on the vault copy
5. Insert `FileRegistry` row with `Status = Vaulted`

### 4.2 Vault Path Rules

The vault mirrors the **organized folder structure** of the file's destination — not a flat date folder. This means the vault is human-navigable without the app, and restoring after a disaster is as simple as finding the file where you'd expect it.

```
Source dropped:   LedgerDrive\HDFC_Jan2025.pdf       (dropped Jan 15 2025)
Organized to:     LedgerDrive\Assets\Banks\HDFC\2025\January.pdf
Vault copy:       LedgerDrive\.vault\Assets\Banks\HDFC\2025\January.pdf

Source dropped:   LedgerDrive\CAMS_CAS_2025.pdf
Organized to:     LedgerDrive\Assets\Investments\CAMS\2025\Portfolio_Jan2025.pdf
Vault copy:       LedgerDrive\.vault\Assets\Investments\CAMS\2025\Portfolio_Jan2025.pdf

Collision:        LedgerDrive\.vault\Assets\Banks\HDFC\2025\January_2.pdf
```

**Before organize completes** (while file is still in root, status is `Vaulted`/`Parsing`):
```
Temporary vault path:  LedgerDrive\.vault\.incoming\{YYYY-MM-DD}\{original_filename}
Final vault path:      LedgerDrive\.vault\{same relative path as organized destination}
```

The `FileRegistry.vault_path` is updated atomically when the file moves from `.incoming\` to its final vault position. The `incoming` subfolder serves as a safe staging area — every file dropped is immediately protected there, even before the detector knows its bank or type.

### 4.3 Deletion Detection
```
User deletes:  LedgerDrive\Banks\HDFC\2025\January.pdf
                │
                └── FileSystemWatcher.Deleted event
                      └── Look up FileRegistry WHERE OrganizedPath = deleted_path
                              → Found FileRegistry { ImportBatchId = 42 }
                      └── Count transactions WHERE ImportBatchId = 42
                              → 117 transactions
                      └── SignalR: file.removal_pending {
                              fileId, organizedPath, transactionCount: 117
                          }
                      └── React shows: "Deleting HDFC Jan 2025 will remove 117 
                              transactions. Are you sure?"
                      └── User confirms → soft-delete (Status='Removed')
                      └── .vault\ copy NEVER touched
```

### 4.4 Duplicate & Re-drop File Handling

When a file is dropped, the VaultManager computes its SHA-256 and checks `FileRegistry.content_hash` **before** doing anything else. This single check covers all re-drop scenarios without creating orphaned records.

#### Decision Tree

```
File dropped into LedgerDrive root
      │
      ├─ Compute SHA-256 hash
      │
      ├── CASE A: Hash EXISTS in FileRegistry (same binary content re-dropped)
      │     │
      │     ├── Status = Organized
      │     │     → Delete dropped copy from root (cleanup)
      │     │     → Toast: "Already imported as Banks/HDFC/2025/January.pdf – skipped"
      │     │
      │     ├── Status = Failed (parse failed on a previous drop)
      │     │     → Toast: "[file] previously failed to parse. Retry processing?"
      │     │       [Retry] → reset Status = Queued, re-enqueue existing record
      │     │       [Skip]  → delete dropped copy, no other change
      │     │
      │     ├── Status = Removed (user deleted the transactions at some point)
      │     │     → Toast: "[file] was imported before but transactions were removed. Re-import?"
      │     │       [Re-import] → new ImportBatch, Status = Queued, full re-process
      │     │       [Skip]      → delete dropped copy, no other change
      │     │
      │     ├── Status = PasswordRequired
      │     │     → Toast: "[file] is already waiting for a password"
      │     │     → Navigate to /files, highlight the waiting entry
      │     │     → Delete dropped duplicate from root
      │     │
      │     └── Status = Queued / Processing
      │           → Silently discard (OS filesystem double-event)
      │
      └── CASE B: Hash NOT FOUND (genuinely new file content)
            │
            ├─ Copy to .vault\ (immutable archive)
            ├─ INSERT FileRegistry { Status = Vaulted }
            ├─ Queue for processing pipeline
            │
            └─ After parsing identifies bank + statement period:
                  Check FileRegistry WHERE DetectedBank = X
                                      AND StatementPeriod = same month/year
                                      AND Status = Organized
                  │
                  ├── MATCH FOUND (corrected statement / bank re-issue)
                  │     → Warning before producing proposals:
                  │       "You already have 117 HDFC Jan 2025 transactions.
                  │        Import anyway? Deduplication will filter exact matches,
                  │        but net-new rows from a corrected statement will be added."
                  │       [Import Anyway]  → continue to proposals
                  │       [Review First]   → hold at Normalized status, show diff
                  │       [Cancel]         → discard proposals, mark file Removed
                  │
                  └── NO MATCH → Normal proposal pipeline
```

#### Checksum Validation Code

```csharp
// VaultManager.cs
public async Task<VaultResult> VaultAsync(string filePath, CancellationToken ct)
{
    var bytes    = await File.ReadAllBytesAsync(filePath, ct);
    var hash     = Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant();
    var existing = await _db.FileRegistry
        .FirstOrDefaultAsync(f => f.ContentHash == hash, ct);

    if (existing != null)
        return existing.ProcessingStatus switch {
            "Organized"        => new VaultResult(VaultAction.SkipAlreadyDone,    existing),
            "Failed"           => new VaultResult(VaultAction.OfferRetry,         existing),
            "Removed"          => new VaultResult(VaultAction.OfferReimport,      existing),
            "PasswordRequired" => new VaultResult(VaultAction.ShowPasswordPrompt, existing),
            _                  => new VaultResult(VaultAction.SkipAlreadyQueued,  existing)
        };

    // Genuinely new — copy to vault
    var vaultPath = BuildVaultPath(filePath, datetime.now(UTC));
    File.Copy(filePath, vaultPath);
    File.SetAttributes(vaultPath, FileAttributes.ReadOnly);  // immutable protection

    _db.FileRegistry.Add(new FileRegistry {
        OriginalName     = Path.GetFileName(filePath),
        OriginalPath     = filePath,
        VaultPath        = vaultPath,
        ContentHash      = hash,
        FileSizeBytes    = bytes.Length,
        ProcessingStatus = "Vaulted",
        DroppedAt        = datetime.now(UTC)
    });
    await _db.SaveChangesAsync(ct);
    return new VaultResult(VaultAction.Proceed, null);
}
```

The dropped file in the LedgerDrive root is **not deleted immediately** — it remains visible as an "in progress" indicator until `FileOrganizerService` moves it to the canonical organized path as the final pipeline step.

### 4.5 Vault File Attributes & Integrity

#### Storage Details

```
.vault\
├── .incoming\               ← Staging: files land here immediately on drop
│   └── 2025-01-15\
│       └── HDFC_raw.pdf        (ReadOnly, awaiting detection + organization)
│
├── Assets\                  ← Mirrors organized folder tree exactly
│   ├── Banks\
│   │   ├── HDFC\
│   │   │   └── 2025\
│   │   │       ├── January.pdf      (byte-exact, ReadOnly)
│   │   │       └── February.pdf
│   │   └── SBI\
│   │       └── 2024\
│   │           └── December.csv
│   ├── Investments\
│   │   └── CAMS\
│   │       └── 2025\
│   │           └── Portfolio_Jan2025.pdf
│   └── House\
│       └── HDFC_HomeLoan\
│           └── 2025\
│               └── March.pdf
│
└── CreditCards\             ← CC files also mirrored
    └── HDFC_CC_1234\
        └── 2025\
            └── January.pdf
```

**Design rationale:** A user who needs to manually restore after a disaster (app won't start, DB corrupted) can navigate `.vault\` in Windows Explorer, find their files exactly where they expect them, and copy them back. No app required.

| Property | Value |
|---|---|
| Copy method | Byte-exact (`File.Copy`) — no compression, no encoding, no modification |
| Staging path | `.vault\.incoming\{YYYY-MM-DD}\{original_name}` — set immediately on drop |
| Final path | `.vault\{same relative path as organized destination}` — set after detection |
| File attribute | `ReadOnly` set immediately after copy in staging |
| Folder attribute | `Hidden + System` (invisible in Explorer by default) |
| Encryption | None — files are on the user's own local drive, protected by Windows permissions. Encrypting vault copies would make manual disaster recovery (without the app) impossible. |
| SHA-256 | Stored in `FileRegistry.content_hash` — used for all duplicate detection and integrity checks |

#### Collision Naming

```
First copy:   .vault\Assets\Banks\HDFC\2025\January.pdf
Re-import:    .vault\Assets\Banks\HDFC\2025\January_2.pdf   ← different content
Third copy:   .vault\Assets\Banks\HDFC\2025\January_3.pdf
```

Suffix number determined by scanning existing files in the target folder at vault time.

#### On-Demand Integrity Verification

```csharp
// GET /files/vault/verify   →   VaultService.VerifyIntegrityAsync()
public async Task<VaultIntegrityReport> VerifyIntegrityAsync(CancellationToken ct)
{
    var records = await _db.FileRegistry
        .Where(f => f.VaultPath != null)
        .ToListAsync(ct);

    var report = new VaultIntegrityReport();
    foreach (var reg in records)
    {
        if (!File.Exists(reg.VaultPath))
        { report.Missing.Add(reg.OriginalName); continue; }

        var bytes = await File.ReadAllBytesAsync(reg.VaultPath, ct);
        var hash  = Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant();

        if (hash != reg.ContentHash) report.Corrupted.Add(reg.OriginalName);
        else                         report.Verified++;
    }
    return report;
    // Result shown in Settings → Vault. Warns if files are missing or corrupted.
}

---

## 5. File Detector Service

### 5.1 Detection Algorithm

```
Step 1: Magic Bytes
  Buffer first 8 bytes:
  %PDF-          → PDF
  PK\x03\x04     → ZIP/XLSX
  \xFF\xFE       → UTF-16 LE CSV
  \xEF\xBB\xBF   → UTF-8 BOM CSV
  Printable ASCII lines → CSV (auto-detect columns)

Step 2: Filename Pattern (Regex Dictionary)
  HDFC.*\.pdf     → SourceType=HDFC_PDF       confidence +0.4
  SBI.*\.pdf      → SourceType=SBI_PDF        confidence +0.4
  zerodha.*\.csv  → SourceType=ZERODHA_CSV    confidence +0.4
  CAS.*\.pdf      → SourceType=CAS_PDF        confidence +0.3
  (...30+ patterns)

Step 3: PDF Keyword Scan (first 4KB via PdfPig page 1)
  "HDFC Bank" + "Withdrawal Amt."      → HDFC_PDF   confidence +0.5
  "State Bank of India" + "Narration"  → SBI_PDF    confidence +0.5
  "ICICI Bank" + "Transaction Remarks" → ICICI_PDF  confidence +0.5
  (...one signature per supported bank)

Step 4: Encryption Check
  Docnet.Core.DocLib.Instance.LoadDocument(bytes) throws DocnetException
    → IsEncrypted = true

Step 5: Confidence Threshold
  >= 0.70: proceed to matched parser
  < 0.70 and IsEncrypted=false: GenericCsvParser fallback if CSV magic bytes
  < 0.70 and PDF: mark as NeedsReview; user can manually assign parser in UI
```

### 5.2 Return Type
```csharp
public record DetectionResult(
    SourceType SourceType,
    string BankName,
    double Confidence,
    bool IsEncrypted,
    bool IsSupported
);
```

---

## 6. Password Attempt Service

> **Important:** This service does **not** "crack" or guess passwords in the cryptographic sense. It generates a deterministic list of candidate passwords derived from the user's own known personal data (PAN, DOB, name, mobile) — the exact same patterns Indian banks use when they encrypt PDFs they send to customers. The service iterates through these candidates in order. If none succeed, the user is asked to enter the password manually. No brute-force, no dictionary attacks, no hallucination of random strings.

### 6.1 Process Isolation Design

```
Ledger.exe (parent)
  │
  ├── Build candidate list from UserProfile (SecureString)
  ├── Spawn: Ledger.Shell.CrackerProcess.exe
  │       Job Object: no network, no additional processes
  │       Named pipe: \\.\pipe\LedgerCracker_{guid}
  │
  ├── Send via pipe: { fileBytes: Base64, candidateList: string[] }
  ├── Start 30-second kill timer
  │
  └── Child receives:
        foreach (candidate in candidateList)
          try Docnet.Core.LoadDocument(fileBytes, candidate)
          → on success: send back { success: true, password: "ABCDE1234F" }
          → on exception: continue next
        → on all fail: send { success: false }
        → pipe close → parent kills child process
```

**Why isolated process?**
- PAN, DOB, mobile loaded into child only during the attempt window
- Child has no disk write access → candidates cannot be written to disk by accident
- Child has no network access → cannot beacon the password to anywhere
- Kill timeout prevents hanging if PDFium deadlocks on a malformed PDF

### 6.2 Candidate List Generation

Candidates are built strictly from values the user has already provided. The list is deterministic — the same inputs always produce the same candidates in the same order. No random attempts are ever made.

```csharp
// Built from decrypted UserProfile fields
// Fields loaded as SecureString, converted in-memory, cleared after list built
var candidates = new List<SecureString>();

// PAN variants   (e.g. ABCDE1234F)
AddIfNotNull(pan.ToUpper());
AddIfNotNull(pan.ToLower());
AddIfNotNull(pan[5..]);          // last 5 chars (e.g. "1234F")

// DOB variants
var dob = DecryptField(profile.DobEncrypted);
AddIfNotNull($"{dob:ddMMyyyy}");
AddIfNotNull($"{dob:ddMMyy}");
AddIfNotNull($"{dob:yyyy}");
AddIfNotNull($"{dob:ddMM}");
AddIfNotNull($"{dob:MMyyyy}");

// Name variants
var firstName = profile.DisplayName.Split(' ')[0].ToLower();
var fullNameNoSpace = profile.DisplayName.Replace(" ", "").ToLower();
AddIfNotNull(firstName);
AddIfNotNull(fullNameNoSpace);

// Mobile variants
var mobile = DecryptField(profile.MobileEncrypted);
AddIfNotNull(mobile);            // 10-digit
AddIfNotNull(mobile[6..]);       // last 4 digits

// Combo patterns (common bank PDF password conventions)
AddIfNotNull($"{firstName}{dob:ddMMyyyy}");
AddIfNotNull($"{pan.ToUpper()}{dob:yyyy}");
AddIfNotNull($"{dob:ddMMyyyy}{firstName}");
AddIfNotNull($"{firstName}{dob:yyyy}");
```

**Family Mode (v2):** The attributed `FamilyMember`'s encrypted fields are decrypted and candidates built from their profile first. The primary user's candidates are appended as a fallback pass.

### 6.3 Toast on Failure

```
Toast Title: "Password Required"
Toast Body: "Could not unlock [filename]. Tap to enter password."
Action: "Enter Password" → app.BringToFront() + navigate to /files?highlight={fileId}

// In Files page: inline form
<PasswordInput placeholder="Enter PDF password" />
<Button onClick={submitPassword}>Unlock & Process</Button>

// POST /files/{id}/unlock { password: "..." }
// → BackgroundTaskQueue.Enqueue(re-parse with provided password)
```

---

## 7. Document Parser Architecture

### 7.1 IDocumentParser Interface

```csharp
public interface IDocumentParser
{
    SourceType SourceType { get; }
    string BankName { get; }

    Task<ParseResult> ParseAsync(
        Stream stream,
        SecureString? password,
        CancellationToken ct);
}

public record ParseResult(
    IReadOnlyList<RawRow> Rows,
    ExtractionMethod Method,
    double Confidence,
    int PageCount,
    string? ErrorMessage
);

public record RawRow(
    string? Date,
    string? Description,
    string? Debit,
    string? Credit,
    string? Balance,
    string? RawLine,
    int PageNumber,
    double RowConfidence
);
```

### 7.2 Extraction Chain (Per Parser)

Each parser attempts extraction methods in order, stopping at first success:

```
1. TEXT_LAYER
   └── PdfPig.PdfDocument.GetPage(n).Text
   └── Regex extraction against bank-specific patterns
   └── Confidence = field_completeness * 0.95 (text layer is reliable)

2. TABLE_EXTRACTION
   └── PdfPig bounding-box grouping (columns by x-coordinate)
   └── Used when text layer present but no structured line patterns
   └── Confidence = column_match_score

3. OCR_WINDOWS (primary)
   └── Docnet.Core renders page to BGRA bitmap (300 DPI)
   └── Convert to SoftwareBitmap
   └── Windows.Media.Ocr.OcrEngine.RecognizeAsync()
   └── Parse OcrResult.Lines[].Text with bank-specific regex
   └── Confidence = OcrEngine line-level confidence average

4. OCR_TESSERACT (fallback — if Windows OCR confidence < 0.75)
   └── Same BGRA bitmap → Pix conversion
   └── TesseractEngine("./tessdata", "eng+hin", LstmOnly)
   └── HOCR output → bounding boxes for column detection
   └── Confidence = HOCR mean word confidence / 100

5. LLM_VISION (opt-in + privacy-anonymized only)
   └── Docnet.Core renders pages to PNG (150 DPI — cheaper tokens)
   └── PrivacyTransformer applied to file name + metadata context
   └── POST to LLM provider vision endpoint
   └── LLMResponse.Rows mapped to RawRow[]
   └── Confidence = LLMResponse.Confidence
```

### 7.3 Supported Parsers

| Parser Class | Bank | Format | Key Fields |
|---|---|---|---|
| `HdfcPdfParser` | HDFC Bank | PDF text layer | Date, Narration, Withdrawal, Deposit, Closing Balance |
| `SbiPdfParser` | State Bank of India | PDF text layer | Txn Date, Description, Debit, Credit, Balance |
| `IciciPdfParser` | ICICI Bank | PDF text layer + table | Date, Transaction Remarks, Withdrawal, Deposit, Balance |
| `AxisPdfParser` | Axis Bank | PDF table | Tran Date, PARTICULARS, DR, CR, BAL |
| `KotakPdfParser` | Kotak Mahindra | PDF text | Date, Description, Amount, Dr/Cr, Balance |
| `IdfcPdfParser` | IDFC FIRST Bank | PDF text | Date, Particulars, Debit, Credit, Balance |
| `UnionPdfParser` | Union Bank of India | Encrypted PDF | Date, Description, Debit, Credit, Balance |
| `IndusIndPdfParser` | IndusInd Bank | PDF text | Value Dt, Narration, Dr Amount, Cr Amount, Balance |
| `YesCcPdfParser` | YES Bank Credit Card | PDF text | Date, Description, Amount |
| `HdfcCcPdfParser` | HDFC Credit Card | PDF text | Date, Description, Amount, Cr |
| `IciciCcPdfParser` | ICICI Credit Card | PDF text + table | Date, Description, Amount |
| `CasCamsParser` | CAMS CAS Statement | PDF text (complex) | Fund, FOLIO, Date, Amount, NAV, Units |
| `HdfcCsvParser` | HDFC Bank | CSV | Date, Narration, Value Dt, Debit, Credit, Chq/Ref, Closing Bal |
| `SbiCsvParser` | SBI | CSV | Txn Date, Value Date, Description, Ref No, Debit, Credit, Balance |
| `IciciCsvParser` | ICICI Bank | CSV | Transaction Date, Value Date, Description, Debit, Credit, Balance |
| `AxisCsvParser` | Axis Bank | CSV | Tran Date, PARTICULARS, CHQNO, VALUE DATE, DEBIT, CREDIT, BAL |
| `KotakCsvParser` | Kotak | CSV | Transaction Date, Description, Chq/Ref No, Value Date, Withdrawal, Deposit, Balance |
| `ZerodhaCsvParser` | Zerodha | CSV (Tax P&L) | Symbol, Trade Type, Date, Quantity, Price, P&L |
| `GenericCsvParser` | Any | CSV | Auto-detect via header keyword matching |

---

## 8. Normalizer Service

Converts bank-specific raw rows into uniform `NormalizedTransaction` records.

```csharp
public record NormalizedTransaction(
    DateOnly Date,
    DateOnly? ValueDate,
    string Description,
    decimal Debit,
    decimal Credit,
    decimal? Balance,
    string Currency,
    string RawText,
    double ParserConfidence,
    int? FamilyMemberId      // v2: carries through for DB write
);
```

**Date Parsing (multi-format):**
```
DD/MM/YYYY  → DateOnly.ParseExact("31/01/2025")
DD-Mon-YY   → "31-Jan-25"   → interpret 25 as 2025
YYYY-MM-DD  → ISO 8601
DD-MM-YYYY  → variant
D/M/YYYY    → "1/1/2025"
```

**Amount Parsing (Indian lakh format):**
```
"1,23,456.78"  →  123456.78
"₹ 1,234.56"  →  1234.56
"(1,234.56)"  →  -1234.56  (credit card statement negative)
"1234.56 DR"  →  debit = 1234.56
"1234.56 CR"  →  credit = 1234.56
```

---

## 9. Deduplication Service

```
Fingerprint: SHA256($"{date:yyyyMMdd}|{Math.Abs(debit - credit):F2}|{NormalizeDesc(desc)}")

NormalizeDesc(desc):
  - Lowercase
  - Remove extra whitespace
  - Remove reference numbers: "UPI-12345678" → "UPI-"
  - Remove trailing date stamps
  - Trim to first 60 chars

Near-duplicate fuzzy match:
  - Same fingerprint date ± 1 day
  - Same amount (within ₹0.50 tolerance)
  - Levenshtein similarity on description > 85%
  → Mark as SOFT_DUPLICATE, show in review
```

---

## 10. File Organizer

After proposals generated → move file to canonical path:

```csharp
string CanonicalPath(FileRegistry reg) => reg.DetectedSourceType switch {
    "HDFC_PDF"    or
    "SBI_PDF"     or
    "ICICI_PDF"      => $@"Banks\{reg.DetectedBank}\{year}\{monthName}.pdf",
    "HDFC_CC_PDF" or
    "ICICI_CC_PDF"   => $@"CreditCards\{reg.DetectedBank}_{cardSuffix}\{year}\{monthName}.pdf",
    "ZERODHA_CSV"    => $@"Investments\Zerodha\{year}\{reg.OriginalName}",
    "CAS_PDF"        => $@"Investments\CAMS\{year}\{reg.OriginalName}",
    _                => $@"Other\{reg.OriginalName}"
};

// Family Mode extension (v2):
// prefix = member.Relationship == "Self" ? "" : $"Family\\{member.DisplayName}\\"
// return prefix + CanonicalPath(reg)
```

**Collision handling:** if target exists, append `_2`, `_3` etc.

---

## 11. Proposal Pipeline & Approval Flow

### 11.1 What is a Proposal?

After normalization and deduplication, `PipelineService` generates a **double-entry proposal** for each transaction. A proposal is:
- A suggested debit + credit journal entry (double-entry bookkeeping)
- Assigned a category from the ML classifier
- Scored with a confidence value (0.0–1.0)
- **Not yet committed to the ledger** — it lives in `transaction_proposals` until acted on

This means: **importing a statement does not immediately change your ledger**. All transactions wait in the Proposals queue for your review.

### 11.2 Default Behavior: Manual Review for All Proposals

By default, every proposal requires explicit user action (approve / edit + approve / reject). This is intentional:
- On first use, the user needs to verify category assignments fit their financial situation
- First imports of a new bank/account have unknown payees
- Double-entry account mappings may need correction

Setting: `auto_approve_threshold = 0.0` (disabled, the default)

### 11.3 Optional Auto-Approve Mode

Once the user trusts the model (typically after several months of statements have been reviewed), they can enable auto-approval:

```
Settings → Pipeline
  ┌──────────────────────────────────────────────────────┐
  │ Auto-Approve Proposals                               │
  │ Enable:    [OFF  ●──────────]                        │
  │ Threshold: [95%  ▼] (auto-commit if confidence ≥ X) │
  │ Max amount: [₹50,000] (never auto-approve above this)│
  │                                                      │
  │ ⚠ Transactions above this confidence will be         │
  │   committed to your ledger without review.          │
  │   You can always review and edit them later.         │
  └──────────────────────────────────────────────────────┘
```

- Auto-approved transactions are flagged `is_auto_approved = true` in `transactions` table
- They appear in the transaction list with a small "Auto" badge
- User can click any auto-approved transaction → edit category → re-save (no "un-approve" complexity)

### 11.4 Auto-Approve Exclusions — Always Require Manual Review

Regardless of confidence score, these cases are never auto-approved:

| Condition | Reason |
|---|---|
| Payee seen for the **first time** | ML model has no training signal for this payee — false high confidence is possible |
| Category = `Uncategorized` | Model could not assign a category — requires user selection |
| Amount > `auto_approve_max_amount` (default ₹50,000, user-configurable) | High-value transactions warrant explicit human review |
| Credit card refund or reversal | Ambiguous double-entry treatment (reduce expense? or income?) |
| Transfer between own accounts | Requires correct contra-account selection by user |

### 11.5 Confidence Bands

| Band | Score | Default Behavior |
|---|---|---|
| High | ≥ 95% | Auto-approvable (if setting enabled + no exclusion applies) |
| Medium | 70–94% | Manual review — shown first in Proposals queue |
| Low | < 70% | Manual review + category suggestion dropdown shown |

### 11.6 Bulk Approval in the UI

In the Proposals page, the user can:
- **Approve All** — all currently visible proposals (after any active filter)
- **Approve High Confidence** — all proposals ≥ 95% in the current view
- **Approve Selected** — multi-select with Space key, then Approve
- **Edit then Approve** — change category/description before committing

Bulk approve posts all selected proposals in a single DB transaction — partial failure rolls back the whole batch.

### 11.7 ML Feedback Loop

```
User approves category "Food & Dining" for "SWIGGY ORDER 123"
    │
    └── ProposalService.OnApproval(proposalId, acceptedCategory)
          ├── If acceptedCategory != suggestedCategory:
          │       → TrainingSignal { text: "SWIGGY ORDER 123", label: "Food & Dining" }
          │       → Append to ml_training_buffer table
          └── If buffer.Count >= 50:
                    ML.NET incremental retrain on buffer
                    Save updated model → models\category_classifier.zip
                    Clear buffer
```

The model improves continuously based on the specific user's approval and correction patterns.
