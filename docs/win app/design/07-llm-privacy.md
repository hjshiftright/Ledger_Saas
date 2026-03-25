# Ledger Desktop — LLM Integration & Privacy Engine

**Version:** 1.0  
**Status:** Design Review

---

## 1. Design Principles

1. **Opt-in by default.** No LLM call is ever made without explicit user action.
2. **Privacy Mode ON by default.** When LLM is used, the PrivacyTransformer runs automatically unless the user explicitly disables it.
3. **Informed consent.** Privacy Mode OFF requires an acknowledged warning — "Your real financial data will be sent to [Provider]."
4. **Zero cloud egress at rest.** The app runs fully offline. LLM is one optional capability, not a runtime dependency.
5. **Certificate pinning.** All LLM provider HTTPS connections are pinned to known leaf certificate fingerprints.

---

## 2. LLM Provider Architecture

### 2.1 Interface

```csharp
public interface ILlmProvider
{
    string ProviderName { get; }
    bool IsConfigured { get; }

    Task<LlmExtractionResult> ExtractTextAsync(
        LlmTextRequest request,
        CancellationToken ct);

    Task<LlmExtractionResult> ExtractVisionAsync(
        LlmVisionRequest request,
        CancellationToken ct);
}

public record LlmTextRequest(
    string PartialText,
    string SourceType,
    string? Hint,
    bool ApplyPrivacyTransform  // caller decides, based on settings
);

public record LlmVisionRequest(
    IReadOnlyList<byte[]> PageImages,  // PNG bytes per page
    string SourceType,
    string? Hint,
    bool ApplyPrivacyTransform
);

public record LlmExtractionResult(
    IReadOnlyList<RawRow> Rows,
    int InputTokens,
    int OutputTokens,
    double Confidence,
    string? RawResponse
);
```

### 2.2 Provider Implementations

| Class | Endpoint | Models |
|---|---|---|
| `GeminiProvider` | `generativelanguage.googleapis.com/v1beta` | `gemini-2.0-flash-exp` (text), `gemini-2.0-flash-exp` (vision) |
| `OpenAIProvider` | `api.openai.com/v1` | `gpt-4o-mini` (text), `gpt-4o` (vision) |
| `AnthropicProvider` | `api.anthropic.com/v1` | `claude-3-5-haiku-20241022` (text), `claude-opus-4-5` (vision) |

Default provider configured in `app_settings.llm_default_provider`. User can override in Settings.

### 2.3 HTTP Client Configuration

```csharp
// LlmHttpClientFactory.cs
services.AddHttpClient<GeminiProvider>(c => {
    c.BaseAddress = new Uri("https://generativelanguage.googleapis.com/");
    c.Timeout = TimeSpan.FromSeconds(60);
})
.ConfigurePrimaryHttpMessageHandler(() => new HttpClientHandler {
    ServerCertificateCustomValidationCallback = CertificatePinningValidator
})
.AddPolicyHandler(GetRetryPolicy());   // Polly: 3x exponential backoff

IAsyncPolicy<HttpResponseMessage> GetRetryPolicy() =>
    HttpPolicyExtensions
        .HandleTransientHttpError()
        .WaitAndRetryAsync(3, attempt =>
            TimeSpan.FromSeconds(Math.Pow(2, attempt)));  // 2s, 4s, 8s
```

### 2.4 API Key Security

```csharp
// Key stored: ProtectedData.Protect(keyBytes, entropy, DataProtectionScope.CurrentUser)
// Key retrieved: only for the duration of one HTTP request

public async Task<LlmExtractionResult> ExtractTextAsync(LlmTextRequest req, CancellationToken ct)
{
    var keyBlob = await _db.LlmProviders.SingleAsync(p => p.IsDefault, ct);
    var rawKeyBytes = ProtectedData.Unprotect(
        Convert.FromBase64String(keyBlob.ApiKeyDpapi), _entropy,
        DataProtectionScope.CurrentUser);
    using var apiKey = BytesToSecureString(rawKeyBytes);
    Array.Clear(rawKeyBytes, 0, rawKeyBytes.Length);

    var bstr = Marshal.SecureStringToBSTR(apiKey);
    try {
        _httpClient.DefaultRequestHeaders.Authorization =
            new AuthenticationHeaderValue("Bearer", Marshal.PtrToStringBSTR(bstr));
        // ... make request ...
        return result;
    } finally {
        Marshal.ZeroFreeBSTR(bstr);
        _httpClient.DefaultRequestHeaders.Authorization = null;
    }
}
```

---

## 3. Privacy Transformer

### 3.1 Purpose

Before any data leaves the machine (LLM call), the `PrivacyTransformer` replaces sensitive tokens with anonymized placeholders. After the LLM responds, the reverse mapping is applied to re-associate categories/results with the real transactions — **which never left the machine**.

### 3.2 Transformation Rules

| Source Data | Replaced With | Example |
|---|---|---|
| Person names (regex: consecutive Title-cased words) | `PERSON_A`, `PERSON_B`, ... | "Ravi Kumar" → "PERSON_A" |
| Account numbers (10-17 digit sequences) | `ACC_1`, `ACC_2`, ... | "HDFC_12345678901" → "ACC_1" |
| PAN pattern `[A-Z]{5}[0-9]{4}[A-Z]` | `PAN_1` | "ABCDE1234F" → "PAN_1" |
| Mobile numbers (10-digit) | `MOBILE_1` | "9876543210" → "MOBILE_1" |
| Exact amounts | Bucketed range label | `₹45,678` → `MEDIUM_AMOUNT` |
| Merchant names (known: UPI payees, NEFT refs) | Preserved (non-PII) | "AMAZON" stays "AMAZON" |

**Amount Buckets:**
```
₹0          → ZERO_AMOUNT
₹0.01–999   → MICRO_AMOUNT
₹1000–9999  → SMALL_AMOUNT
₹10000–99999 → MEDIUM_AMOUNT
₹100000+    → LARGE_AMOUNT
```

### 3.3 Implementation

```csharp
// PrivacyTransformer.cs
public class PrivacyTransformer
{
    // Session-scoped: created per LLM call, disposed after
    private readonly Dictionary<string, string> _forward = new();
    private readonly Dictionary<string, string> _reverse = new();
    private int _personCounter = 0;
    private int _accCounter = 0;

    public string Transform(string input)
    {
        var result = input;

        // PAN (most specific — apply before person names)
        result = Regex.Replace(result, @"\b[A-Z]{5}[0-9]{4}[A-Z]\b", m =>
            GetOrAdd(m.Value, "PAN_", ref _accCounter));

        // Mobile (10-digit standalone)
        result = Regex.Replace(result, @"\b[6-9][0-9]{9}\b", m =>
            GetOrAdd(m.Value, "MOBILE_", ref _accCounter));

        // Account numbers
        result = Regex.Replace(result, @"\b[0-9]{10,17}\b", m =>
            GetOrAdd(m.Value, "ACC_", ref _accCounter));

        // Person names (Title Case sequences of 2-3 words)
        result = Regex.Replace(result, @"\b[A-Z][a-z]+ [A-Z][a-z]+(?:\s[A-Z][a-z]+)?\b", m =>
            GetOrAdd(m.Value, "PERSON_", ref _personCounter));

        // Amounts (₹ + digits with commas)
        result = Regex.Replace(result, @"₹\s?[\d,]+\.?\d{0,2}", m => {
            var amount = decimal.Parse(m.Value.TrimStart('₹', ' ').Replace(",", ""));
            return BucketAmount(amount);
        });

        return result;
    }

    public string Untransform(string llmOutput)
    {
        var result = llmOutput;
        // Only reverse items that the LLM echoed back (e.g., in categorization output)
        foreach (var (placeholder, original) in _reverse)
            result = result.Replace(placeholder, original);
        return result;
    }
}
```

### 3.4 Chat Endpoint Privacy

```csharp
// ChatEndpoints.cs
app.MapPost("/chat", async (ChatRequest req, IPrivacyTransformer transformer,
    ILlmProviderFactory factory, LedgerDbContext db, CancellationToken ct) =>
{
    var settings = await db.AppSettings.GetAsync("privacy_mode_default", ct);
    bool privacyModeOn = req.OverridePrivacyMode ?? bool.Parse(settings.Value);

    var context = await BuildChatContext(db, ct);  // live ledger summary

    string payload;
    if (privacyModeOn)
    {
        payload = transformer.Transform(context + "\n\n" + req.UserMessage);
        // Response is de-anonymized before returning to React
    }
    else
    {
        // User explicitly disabled Privacy Mode — they accepted the warning
        payload = context + "\n\n" + req.UserMessage;
    }

    var provider = factory.GetDefault();
    var response = await provider.ExtractTextAsync(new LlmTextRequest(payload, ...), ct);

    // Audit log the call (privacy mode state recorded, no payload)
    await _audit.LogAsync("LlmCall", new {
        provider = provider.ProviderName,
        privacy_mode = privacyModeOn,
        tokens_sent = response.InputTokens,
        tokens_received = response.OutputTokens
    }, ct);

    return Results.Ok(new ChatResponse(
        privacyModeOn ? transformer.Untransform(response.RawResponse) : response.RawResponse,
        privacyModeOn
    ));
});
```

---

## 4. Privacy Mode UI

### 4.1 Chat Widget
```
[🔒 Privacy mode: ON]  [Toggle]
┌─────────────────────────────────────────────┐
│ What was my highest expense category in     │
│ January 2025?                               │
└─────────────────────────────────────────────┘

// Privacy Mode OFF — red banner:
⚠️ Privacy Mode is OFF. Your real transaction data including
   amounts, merchant names, and account references will be
   sent to [Gemini]. [Turn ON] [I Accept]
```

### 4.2 File Parse Fallback (LLM Vision)
When all local extraction methods fail (low OCR confidence), the user is offered:
```
┌──────────────────────────────────────────────────┐
│ ⚠️ Could not extract transactions from           │
│    UNION_NOV2024.pdf using local parsing.        │
│                                                  │
│ 🔒 Use AI Vision (Privacy Mode ON)               │
│    Your document will be anonymized before       │
│    sending to Gemini.                            │
│                                                  │
│ [Use AI Vision] [Skip This File] [Enter Password]│
└──────────────────────────────────────────────────┘
```

---

## 5. LLM Provider Configuration (Settings Page)

```
AI Assistant Settings
─────────────────────────────────────
Provider:        [Gemini ▼]
API Key:         [●●●●●●●●●●●●] [Test] [Save]
Text Model:      [gemini-2.0-flash-exp]
Vision Model:    [gemini-2.0-flash-exp]

Privacy Mode:    [ON ▼]
  When ON: names, amounts, and account numbers are
  anonymized before any data leaves this device.

  ⚠️ Turning Privacy Mode OFF sends real financial
  data to the AI provider. Only do this if you
  trust your provider with your financial details.

[Test Connection]  [Save Settings]
```

---

## 6. Certificate Pinning Configuration

`appsettings.json`:
```json
{
  "LlmSecurity": {
    "CertificatePins": {
      "generativelanguage.googleapis.com": [
        "sha256/<thumbprint_primary>",
        "sha256/<thumbprint_backup>"
      ],
      "api.openai.com": [
        "sha256/<thumbprint_primary>",
        "sha256/<thumbprint_backup>"
      ],
      "api.anthropic.com": [
        "sha256/<thumbprint_primary>"
      ]
    },
    "FallbackToChainValidation": false,
    "PinRotationCheckIntervalDays": 30
  }
}
```

**Pin rotation:** A background task checks pinned fingerprints weekly against the live certificate. If mismatch detected: toast warning + `audit_log` entry. App update ships new thumbprints. `FallbackToChainValidation: true` is available for enterprise environments with SSL inspection proxies (requires explicit opt-in and shows persistent warning banner).

---

## 7. Token Cost Awareness

```csharp
// After each LLM call — stored in audit_log detail JSON
var cost = provider.ProviderName switch {
    "Gemini"    => inputTokens * 0.000_000_35  + outputTokens * 0.000_001_05,
    "OpenAI"    => inputTokens * 0.000_000_15  + outputTokens * 0.000_000_60,
    "Anthropic" => inputTokens * 0.000_000_80  + outputTokens * 0.000_004_00,
    _           => 0
};
// Shown in Settings → AI Usage: "Estimated cost this month: $0.04"
```
