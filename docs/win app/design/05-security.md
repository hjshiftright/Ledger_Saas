# Ledger Desktop — Security Design

**Version:** 1.0  
**Status:** Design Review

---

## 1. Threat Model

| Actor | Attack Vector | Asset at Risk |
|---|---|---|
| Physical machine theft | Raw disk read of DB file | All financial data |
| Memory scraper / debugger | Live process inspection | DB key, PDF passwords, PAN/DOB |
| DLL injection | In-process malicious DLL | Intercept DB key derivation |
| Network MITM (LLM calls) | Intercept HTTPS traffic | LLM payloads containing financial summaries |
| Malicious file | Drop crafted PDF/CSV | PDFium/PdfPig RCE via malformed file |
| Stale cracker process | Password brute-force tool reuse | PAN/DOB in memory after cracking |
| Log/audit exfiltration | Read log files | PAN numbers, passwords inadvertently logged |

---

## 2. Database Encryption (SQLCipher)

### 2.1 Key Derivation

```
Input 1: WindowsMachineGuid
  └── Registry.LocalMachine.OpenSubKey(@"SOFTWARE\Microsoft\Cryptography")
            .GetValue("MachineGuid") as string
  └── Cached in process memory as pinned byte array

Input 2: AppSalt (compile-time embedded resource)
  └── 32 random bytes embedded in Ledger.Infrastructure.dll
  └── Not a string literal — embedded as binary resource to avoid IL string scanning

Key Derivation (no PIN):
  masterKey = Rfc2898DeriveBytes(
      password: Encoding.UTF8.GetBytes(machineGuid + appSalt),
      salt: Encoding.UTF8.GetBytes(staticSalt16),    // 16 bytes, hardcoded
      iterations: 200_000,
      hashAlgorithm: HashAlgorithmName.SHA256
  ).GetBytes(32)

Key Derivation (with PIN enabled):
  pinFactor = Argon2id(PIN, pinSalt, iterations=4, memory=65536, parallelism=1)
  finalKey = Rfc2898DeriveBytes(
      password: masterKey XOR pinFactor,
      salt: pinSalt,
      iterations: 50_000,
      hashAlgorithm: HashAlgorithmName.SHA256
  ).GetBytes(32)

SQLCipher PRAGMA:
  PRAGMA key = "x'{finalKeyHex}'";
  PRAGMA cipher_page_size = 4096;
  PRAGMA kdf_iter = 256000;          // SQLCipher's own internal KDF on top
  PRAGMA cipher_hmac_algorithm = HMAC_SHA512;
  PRAGMA cipher_kdf_algorithm = PBKDF2_HMAC_SHA512;
```

### 2.2 DB File Properties
- Format: Binary SQLite with SQLCipher header — unreadable without correct key
- `strings ledger.db` returns no SQL text
- File located: `%AppData%\Roaming\LedgerApp\data\ledger.db`
- DB folder protected: `icacls "%APPDATA%\LedgerApp\data" /inheritance:r /grant:r "%USERNAME%":(F)`

### 2.3 Machine Migration
If the original machine is unavailable (hardware failure, OS reinstall):
- The DB is tied to `WindowsMachineGuid` — cannot be restored without it
- Mitigation: `Settings → Export Encrypted Backup` feature (v2) exports DB re-encrypted with a user-supplied passphrase
- V1: users are informed during setup that the DB is machine-locked; they should export reports/statements regularly as human-readable backups

---

## 3. Column-Level Encryption

Sensitive fields are encrypted a second time at the application layer, on top of the SQLCipher full-database encryption. This provides defense-in-depth:

| Field | Table | Encryption |
|---|---|---|
| `dob_encrypted` | `family_members` | AES-256-GCM |
| `pan_encrypted` | `family_members` | AES-256-GCM |
| `mobile_encrypted` | `family_members` | AES-256-GCM |
| `api_key_dpapi` | `llm_providers` | Windows DPAPI (additional layer) |

### 3.1 AES-256-GCM Field Encryption

```csharp
// FieldEncryptor.cs
public byte[] Encrypt(string plaintext)
{
    var key = _keyProvider.GetDerivedKey();  // same 32-byte key as SQLCipher input
    var nonce = new byte[12];
    RandomNumberGenerator.Fill(nonce);

    var pt = Encoding.UTF8.GetBytes(plaintext);
    var ct = new byte[pt.Length];
    var tag = new byte[16];

    using var aes = new AesGcm(key, 16);
    aes.Encrypt(nonce, pt, ct, tag);

    // Layout: nonce(12) || ciphertext || tag(16) → base64
    return nonce.Concat(ct).Concat(tag).ToArray();
}

public string Decrypt(byte[] blob)
{
    var key = _keyProvider.GetDerivedKey();
    var nonce = blob[..12];
    var tag   = blob[^16..];
    var ct    = blob[12..^16];
    var pt    = new byte[ct.Length];

    using var aes = new AesGcm(key, 16);
    aes.Decrypt(nonce, ct, tag, pt);
    return Encoding.UTF8.GetString(pt);
}
```

**EF Core Value Converter (transparent on read/write):**
```csharp
builder.Entity<FamilyMember>(e => {
    e.Property(m => m.DobEncrypted)
     .HasConversion(
         v => _enc.Encrypt(v),
         v => _enc.Decrypt(v));
});
```

---

## 4. PIN Security

### 4.1 PIN Hash — Argon2id

```
Argon2id Parameters (OWASP 2024 Recommendations):
  iterations (time cost):   4
  memory cost:              65536 KB (64 MB)
  parallelism:              1
  hash length:              32 bytes

Rationale: 64 MB forces each guess to allocate 64 MB RAM.
  At 1 guess/attempt on modern hardware: ~4 seconds.
  6-digit PIN space: 1,000,000 combinations.
  Exhaustive search: ~46 days on CPU (infeasible without GPU cluster).
```

```csharp
// PinVaultService.cs
public bool VerifyPin(SecureString pin)
{
    var pinBytes = SecureStringToBytes(pin);
    try {
        var storedHash = GetStoredHashFromCredentialStore();
        var storedSalt = GetStoredSalt();
        var computed = Argon2id.Hash(pinBytes, storedSalt, 4, 65536, 1, 32);
        return CryptographicOperations.FixedTimeEquals(computed, storedHash);
    } finally {
        CryptographicOperations.ZeroMemory(pinBytes);
    }
}
```

### 4.2 PIN Storage
- Hash + salt stored in **Windows Credential Store** (not in DB)
- `PasswordVault.Add(new PasswordCredential("LedgerApp", "pin_hash", hashHex))`
- Credential Manager is per-user; not accessible by other Windows users or processes

### 4.3 PIN Lock Screen
```
PinLockScreen.xaml (WPF window, shown BEFORE WebView2 is created):
  - 6-digit numeric PIN input (masked)
  - "Forgot PIN?" link → explains recovery requires re-setup (by design)
  - After 5 failed attempts: 30-second lockout (doubles each subsequent failure)
  - Lockout state stored in memory only (not on disk — prevents lockout persistence)
```

---

## 5. Memory Hardening

### 5.1 SecureString Usage

All passwords (PDF passwords cracked or user-entered, PIN) are held as `SecureString`:

```csharp
// Never: var password = "ABCDE1234F"
// Always:
using var pw = new SecureString();
foreach (char c in crackedPassword) pw.AppendChar(c);
pw.MakeReadOnly();

// When needing to pass to PDFium:
var bstr = Marshal.SecureStringToBSTR(pw);
try {
    Docnet.Load(fileBytes, Marshal.PtrToStringBSTR(bstr));
} finally {
    Marshal.ZeroFreeBSTR(bstr);   // zeros the BSTR before freeing
}
```

### 5.2 Pinned Memory for Key Material

```csharp
// SecureMemory.cs
public static T UseFixed<T>(byte[] data, Func<byte[], T> action)
{
    var handle = GCHandle.Alloc(data, GCHandleType.Pinned);
    try {
        RuntimeHelpers.PrepareConstrainedRegions();
        try { return action(data); }
        finally { Array.Clear(data, 0, data.Length); }
    } finally {
        handle.Free();
    }
}
```

### 5.3 LLM API Key Handling

```csharp
// LlmProvider (call sequence)
var keyBlob = _db.LlmProviders.Single(p => p.IsDefault).ApiKeyDpapi;
var keyBytes = ProtectedData.Unprotect(Convert.FromBase64String(keyBlob), 
                   _entropy, DataProtectionScope.CurrentUser);
SecureString apiKey = BytesToSecureString(keyBytes);
Array.Clear(keyBytes, 0, keyBytes.Length);

// Use for one HTTP request only
var bstr = Marshal.SecureStringToBSTR(apiKey);
try {
    _httpClient.DefaultRequestHeaders.Authorization =
        new AuthenticationHeaderValue("Bearer", Marshal.PtrToStringBSTR(bstr));
    await _httpClient.PostAsync(...);
} finally {
    Marshal.ZeroFreeBSTR(bstr);
    _httpClient.DefaultRequestHeaders.Authorization = null;
    apiKey.Dispose();
}
```

---

## 6. Anti-Tamper (RELEASE Builds Only)

```csharp
// AntiTamperGuard.cs  — called from App.OnStartup() before IHost start
#if !DEBUG
public static void Check()
{
    // 1. Debugger presence
    if (System.Diagnostics.Debugger.IsAttached)
        Environment.FailFast("Integrity check failed.");

    // 2. Remote debugger (JIT debugger)
    if (System.Diagnostics.Process.GetCurrentProcess()
            .HasExited == false &&
        IsDebuggerPresent_PInvoke())
        Environment.FailFast("Integrity check failed.");

    // 3. Block non-Microsoft DLL injection
    ApplyMitigationPolicies();
}

[DllImport("kernel32.dll")]
private static extern bool IsDebuggerPresent();

private static void ApplyMitigationPolicies()
{
    // PROCESS_CREATION_MITIGATION_POLICY_BLOCK_NON_MICROSOFT_BINARIES_ALWAYS_ON
    const long policy = 0x100000000000;
    NativeMethods.SetProcessMitigationPolicy(
        PROCESS_MITIGATION_POLICY.ProcessSignaturePolicy,
        ref policy, sizeof(long));
}
#endif
```

---

## 7. HTTPS Certificate Pinning (LLM Calls)

```csharp
// LlmHttpClientFactory.cs
var handler = new HttpClientHandler {
    ServerCertificateCustomValidationCallback = (msg, cert, chain, errors) => {
        var host = msg.RequestUri!.Host;
        var thumbprint = cert!.GetCertHashString(HashAlgorithmName.SHA256);
        return _pinnedThumbprints.TryGetValue(host, out var expected) &&
               expected.Contains(thumbprint, StringComparer.OrdinalIgnoreCase);
    }
};
```

**Pinned thumbprints (in `appsettings.json` under `LlmCertPins`):**
```json
{
  "LlmCertPins": {
    "api.openai.com": ["<SHA256>", "<SHA256-backup>"],
    "generativelanguage.googleapis.com": ["<SHA256>"],
    "api.anthropic.com": ["<SHA256>"]
  },
  "LlmCertPinsFallbackToChainValidation": false
}
```

**Note:** Provider cert rotation requires an app update. `LlmCertPinsFallbackToChainValidation = true` can be set for enterprise environments with SSL inspection proxies (trade-off, user-acknowledged).

---

## 8. Audit Log Policy

Every security-relevant event is written to `audit_log` asynchronously:

| Action | Logged Fields |
|---|---|
| `DbUnlock` | `{ timestamp, method: "Machine" or "PIN", success: true/false }` |
| `PinVerify` | `{ timestamp, success, attempts_since_last_success }` |
| `PinChange` | `{ timestamp, action: "Enabled" or "Disabled" or "Changed" }` |
| `LlmCall` | `{ timestamp, provider, model, privacy_mode, tokens_sent, tokens_received }` |
| `FileAdded` | `{ timestamp, file_hash, detected_bank, was_encrypted, unlock_method }` |
| `FileProcessed` | `{ timestamp, file_hash, row_count, proposed_count }` |
| `FileRemoved` | `{ timestamp, file_hash, transaction_count, confirmed_by_user }` |
| `PasswordCrack` | `{ timestamp, file_hash, success: true/false, attempts_count }` — **no passwords** |
| `ManualTransaction` | `{ timestamp, transaction_id, amount_range }` — not exact amount |

**What is NEVER logged:**
- Attempted passwords (even partial)
- PAN numbers
- DOB in any format
- Account numbers
- Exact transaction amounts (only ranges in some audit entries)

---

## 9. Cracker Process Sandbox

```csharp
// PasswordCrackerService.cs — spawn with Job Object restrictions
var job = CreateJobObject(null, null);
var limitInfo = new JOBOBJECT_BASIC_LIMIT_INFORMATION {
    LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE |  // kill when parent dies
                 JOB_OBJECT_LIMIT_ACTIVE_PROCESS      |  // max 1 subprocess
                 JOB_OBJECT_LIMIT_JOB_TIME               // 30s CPU time
};
SetInformationJobObject(job, JobObjectBasicLimitInformation, ref limitInfo, ...);

// Network restriction via job extended limit
var netLimit = new JOBOBJECT_NET_RATE_CONTROL_INFORMATION {
    ControlFlags = JOB_OBJECT_NET_RATE_CONTROL_ENABLE |
                   JOB_OBJECT_NET_RATE_CONTROL_MAX_BANDWIDTH,
    MaxBandwidth = 0  // zero bandwidth = no network
};
SetInformationJobObject(job, JobObjectNetRateControlInformation, ref netLimit, ...);

var psi = new ProcessStartInfo("Ledger.Shell.CrackerProcess.exe") {
    CreateNoWindow = true,
    UseShellExecute = false,
    RedirectStandardInput = true,
    RedirectStandardOutput = true
};
var proc = Process.Start(psi)!;
AssignProcessToJobObject(job, proc.Handle);
```

---

## 10. Security Summary Matrix

| Threat | Defense Layer 1 | Defense Layer 2 | Defense Layer 3 |
|---|---|---|---|
| DB file theft | SQLCipher AES-256 | Machine-GUID key binding | Column-level AES-GCM |
| Memory dump | SecureString + ZeroFreeBSTR | GCHandle.Pinned + Array.Clear | Anti-debugger gate |
| DLL injection | SetProcessMitigationPolicy (non-MS DLLs blocked) | RELEASE build anti-tamper | — |
| PIN brute-force | Argon2id (64MB, 4 iter) | Windows Credential Store | Lockout (30s doubling) |
| LLM data leak | PrivacyTransformer (always on by default) | HTTPS cert pinning | User consent required |
| PDF password leak | Isolated child process (no disk/net) | SecureString in pipe | 30s kill timeout |
| Log scraping | Sensitive fields never serialized | Audit log records results only | — |
| App tampering | Debugger.IsAttached guard | Non-MS binary block | MSIX code signing (EV) |
