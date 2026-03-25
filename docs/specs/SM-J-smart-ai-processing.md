# SM-J — Smart AI Processing Mode
## Ledger 3.0 | Sub-module Spec | Version 0.1 | March 15, 2026

---

## 1. Purpose & Scope

Smart AI Processing Mode is the **optional, user-triggered enhancement layer** that re-runs the entire extraction pipeline using LLM assistance on every row, then presents a side-by-side comparison of the original parse result and the AI-enhanced result. The user chooses to accept, reject, or partially accept the AI version.

Smart mode is designed for situations where the standard pipeline (SM-C text/OCR extraction → SM-D fallback) produced low-confidence results, the document was scanned or handwritten, or the user wants to verify AI's interpretation before committing.

It is **not automatic** — the user explicitly activates it for a specific import batch.

### 1.1 Objectives

- Accept the original PDF/CSV bytes plus the current proposal set as context
- Call SM-D vision extraction path on every page of the document with an enriched prompt
- Produce an `AIEnhancedResult` per row — mirroring the structure of `NormalizedTransaction` + scores
- Allow the user to compare original and AI results side-by-side
- Support selective acceptance: accept some AI rows, reject others, accept field-level overrides
- Re-run SM-E → SM-F → SM-G → SM-H on accepted AI rows to refresh proposals
- Maintain a clear audit trail of which fields came from AI vs. standard parse

### 1.2 Out of Scope

- Standard LLM fallback for parsing (that is SM-D's job during the normal pipeline)
- Bulk AI categorization (SM-G handles that in the standard pipeline)
- Retroactive Smart Mode on already-approved transactions (v1 only: active for IN_REVIEW batches)

---

## 2. When Smart Mode is Available

Smart mode activates only when a batch is in the `IN_REVIEW` status and has not yet been fully approved.

```mermaid
stateDiagram-v2
    [*]          --> UPLOADING
    UPLOADING    --> DETECTING
    DETECTING    --> QUEUED
    QUEUED       --> PARSING
    PARSING      --> IN_REVIEW   : Standard pipeline completed
    IN_REVIEW    --> SMART_PENDING : User triggers Smart Mode
    SMART_PENDING --> SMART_RUNNING : SM-J starts jobs
    SMART_RUNNING --> SMART_COMPLETE : All pages processed
    SMART_COMPLETE --> SMART_ACCEPTED : User accepts AI results
    SMART_COMPLETE --> IN_REVIEW  : User rejects all AI results\n(not used, batch stays in review)
    SMART_ACCEPTED --> RESCORING  : Pipe through SM-E → SM-F → SM-G → SM-H
    RESCORING    --> IN_REVIEW   : Updated proposals ready
    IN_REVIEW    --> COMPLETED   : All proposals resolved
```

---

## 3. Data Models

### 3.1 SmartProcessingJob

One job per batch activation of Smart Mode.

| Field | Type | Description |
|---|---|---|
| `smart_job_id` | UUID | PK |
| `batch_id` | UUID | FK → ImportBatch |
| `user_id` | UUID | FK |
| `status` | enum | QUEUED / RUNNING / COMPLETE / FAILED |
| `triggered_at` | timestamp | |
| `completed_at` | timestamp | nullable |
| `page_count` | integer | Total pages processed |
| `pages_completed` | integer | Running count for progress polling |
| `total_tokens_used` | integer | Tokens consumed across all pages |
| `estimated_cost_usd` | decimal | nullable — calculated if provider reports token pricing |
| `provider_id` | UUID | FK → LLMProvider used |
| `error_detail` | string | nullable — last error if FAILED |

### 3.2 AIEnhancedResult

One row per transaction the LLM extracted from the document. Some rows may be entirely new (missed by standard parse), some may differ from standard parse, and some may be identical.

| Field | Type | Description |
|---|---|---|
| `ai_row_id` | UUID | PK |
| `smart_job_id` | UUID | FK |
| `batch_id` | UUID | FK → ImportBatch |
| `page_number` | integer | Page in the original document |
| `txn_date` | date | nullable |
| `value_date` | date | nullable |
| `narration` | string | |
| `debit_amount` | decimal | nullable |
| `credit_amount` | decimal | nullable |
| `amount_signed` | decimal | |
| `running_balance` | decimal | nullable |
| `reference_number` | string | nullable |
| `currency` | string | ISO 4217 |
| `quantity` | decimal | nullable (investment) |
| `unit_price` | decimal | nullable (investment) |
| `ai_confidence_per_field` | JSON | `{ "txn_date": 0.95, "amount_signed": 0.99, "narration": 0.88, ... }` |
| `ai_overall_confidence` | float | Aggregate field confidence |
| `match_type` | enum | IDENTICAL / IMPROVED / DEGRADED / NEW / AI_ONLY (standard parse missed this row) |
| `matched_pending_id` | UUID | nullable — FK → PendingTransaction (if this AI row corresponds to an existing proposal) |
| `accepted` | boolean | null=pending, true=accepted, false=rejected |
| `accepted_at` | timestamp | nullable |
| `diff_fields` | string[] | Which fields differ from the original parse result |

### 3.3 SmartComparison (API Response View)

Assembled on read from AIEnhancedResult + PendingTransaction.

| Field | Type | Description |
|---|---|---|
| `ai_row_id` | UUID | |
| `match_type` | enum | |
| `original` | ProposalSnapshot | nullable — the existing PendingTransaction fields |
| `ai_enhanced` | AIEnhancedResult | The AI version |
| `diff_fields` | FieldDiff[] | List of `{ field, original_value, ai_value, ai_confidence }` |
| `recommendation` | enum | ACCEPT_AI / KEEP_ORIGINAL / REVIEW_MANUALLY |
| `accepted` | boolean | null = user has not yet decided |

---

## 4. Context Assembly

### 4.1 Prompt Construction Strategy

Smart mode sends each page of the document as a separate vision call to SM-D. The prompt is enriched with context from the existing draft proposals to help the LLM resolve ambiguities.

```mermaid
sequenceDiagram
    participant SMJ  as SM-J Smart Mode
    participant SMI  as SM-I (read proposals)
    participant SMD  as SM-D LLM
    participant LLM  as LLM Provider (Vision)

    SMJ->>SMI: GET /imports/{batch_id}/proposals (all)
    SMI-->>SMJ: PendingTransaction[] — current draft proposals

    SMJ->>SMJ: Build page-level processing plan:\n- Split document into page images (10 pages/chunk)\n- Each chunk carries:\n  a) Page image bytes (base64 or file handle)\n  b) source_type → determines prompt template\n  c) Existing draft rows for these page numbers\n     (gives LLM a reference/comparison baseline)\n  d) Account list (id + full_path) for categorization hint

    loop For each page chunk (10 pages)
        SMJ->>SMD: POST /llm/extract-vision\n{ images, source_type, existing_rows_context,\n  account_hint_list, mode: "smart_enhance" }
        SMD->>LLM: Vision API call with enriched prompt
        LLM-->>SMD: Structured JSON:\n[{ date, narration, debit, credit, balance,\n   reference, confidence: { per_field } }]
        SMD-->>SMJ: LLMExtractedRow[] with per-field confidence
        SMJ->>SMJ: Store AIEnhancedResult rows\nUpdate pages_completed counter
    end
```

### 4.2 Enriched Prompt Structure

The system prompt for Smart mode (stored as a versioned `PromptTemplate` in SM-D's template library):

```
System:
You are an expert financial document analysis assistant for an Indian personal finance application.
You are reviewing a bank/investment statement page that has already been partially parsed by
automated tools. Your task is to extract ALL transactions with maximum accuracy.

Where the automated parse may have failed:
- Scanned/photographed pages
- Tables with merged cells or unusual formatting
- Two-column transaction layouts
- Transactions split across page breaks

Context (previously parsed transactions nearby for reference):
[INJECTED: existing_rows_context — plain text table of date/narration/amount/balance]

Extract every transaction you can see. For each transaction, provide confidence scores per field.
Return JSON array: [{ date, narration, debit_amount, credit_amount, running_balance, ... }]
Do not invent transactions. If a field is not visible, set it to null.
```

---

## 5. Result Comparison and Diff Computation

### 5.1 Row Matching Logic

After all AIEnhancedResult rows are collected, SM-J runs a matching pass to link AI rows to existing PendingTransactions:

```mermaid
flowchart TD
    AI_ROWS["AIEnhancedResult rows (unmatched)"]
    ORIG_ROWS["PendingTransaction rows (existing)"]

    STEP1["STEP 1: Exact match\nSame amount_signed ± 0.00\nSame date (± 0 days)\nNarration Jaccard similarity ≥ 0.90\n→ match_type = IDENTICAL or IMPROVED"]

    STEP2["STEP 2: Near match\nSame amount_signed ± ₹1\nDate ± 1 day\nNarration Jaccard similarity ≥ 0.60\n→ match_type = IMPROVED or DEGRADED\n(compare AI confidence vs original parse_confidence)"]

    STEP3["STEP 3: Unmatched AI rows\nNo PendingTransaction found for this row\n→ match_type = NEW\nUser must decide: accept as extra transaction\nor reject as hallucination"]

    STEP4["STEP 4: Unmatched original rows\nExisting PendingTransaction has no AI counterpart\n→ AI may have missed it\nFlag: 'Only in original parse — AI did not find this row'"]

    AI_ROWS --> STEP1 --> STEP2 --> STEP3
    ORIG_ROWS --> STEP4
```

### 5.2 Recommendation Engine

For each matched pair, SM-J computes a recommendation:

| Condition | Recommendation |
|---|---|
| AI field confidence > original confidence AND no degraded fields | `ACCEPT_AI` |
| Original parse confidence > 0.95 and AI match is IDENTICAL | `KEEP_ORIGINAL` (no change needed) |
| Any AI field confidence < 0.60 in a key field (date, amount) | `REVIEW_MANUALLY` |
| match_type = NEW | `REVIEW_MANUALLY` (could be hallucination) |
| AI narration differs significantly (Jaccard < 0.70) but amounts match | `REVIEW_MANUALLY` |

---

## 6. Acceptance Flow

### 6.1 Full Accept/Reject Flow

```mermaid
sequenceDiagram
    actor User
    participant App  as Client
    participant SMJ  as SM-J Smart Mode
    participant SME  as SM-E Normalizer
    participant SMF  as SM-F Dedup
    participant SMG  as SM-G Categorizer
    participant SMH  as SM-H Scorer
    participant SMI  as SM-I Proposals

    Note over User, App: User opens Smart Mode comparison view

    App->>SMJ: GET /imports/{batch_id}/smart-process/comparison
    SMJ-->>App: SmartComparison[] — all rows with diff, recommendation

    App-->>User: Side-by-side table:\n| Date | Amount | Narration | AI Confidence\n[Original] vs [AI Enhanced]\nRECOMMENDATION per row

    User->>App: Click "Accept All AI Improvements"\n(or cherry-pick rows to accept)
    App->>SMJ: POST /imports/{batch_id}/smart-process/accept\n{ ai_row_ids: [...accepted rows...] }

    SMJ->>SMJ: For accepted rows:\n  - Build updated NormalizedTransaction from AIEnhancedResult\n  - Set source_flag = AI_ENHANCED on the row

    SMJ->>SME: POST /normalize (re-normalize accepted rows)
    SME-->>SMJ: NormalizedTransaction[] (refreshed)

    SMJ->>SMF: POST /dedup/check (re-check dedup for updated rows)
    SMF-->>SMJ: DedupResult[] (refreshed)

    SMJ->>SMG: POST /categorize/{batch_id} (re-categorize changed rows)
    SMG-->>SMJ: CategorizedTransaction[] (refreshed)

    SMJ->>SMH: POST /score/{batch_id} (re-score changed rows)
    SMH-->>SMJ: ScoredTransaction[] (refreshed)

    SMJ->>SMI: Update PendingTransaction records:\n  - overwrite fields from AI Enhanced version\n  - update overall_confidence + confidence_band\n  - set source_flag = AI_ENHANCED

    SMJ-->>App: { accepted_rows: N, batch_status: "IN_REVIEW" }
    App-->>User: Review Queue updates with improved scores\nOriginal values preserved in history
```

### 6.2 Partial Field-Level Accept

For IMPROVED rows where only some fields are better:

`PATCH /imports/{batch_id}/smart-process/comparison/{ai_row_id}/field-accept`

Body: `{ fields: ["narration", "reference_number"] }` — accepts only these fields from the AI result, keeping all other fields from the original parse.

---

## 7. Cost Estimation Before Activation

Before the user triggers Smart Mode, SM-J provides an upfront cost estimate.

```mermaid
sequenceDiagram
    actor User
    participant App  as Client
    participant SMJ  as SM-J Smart Mode
    participant SMD  as SM-D LLM

    User->>App: Click "Try Smart Mode" button
    App->>SMJ: GET /imports/{batch_id}/smart-process/estimate
    SMJ->>SMJ: Compute estimate:\n- page_count from ImportBatch\n- page_images_size_avg = 150KB/page\n- tokens_per_page (text + image tokens) = ~1,500\n- total_tokens_est = page_count × 1,500
    SMJ->>SMD: GET /llm/providers — get active provider + pricing
    SMD-->>SMJ: { provider, input_cost_per_1k, output_cost_per_1k }
    SMJ-->>App: {\n  page_count: 18,\n  estimated_tokens: 27000,\n  estimated_cost_usd: 0.27,\n  estimated_cost_inr: "~₹22",\n  estimated_time_seconds: 45,\n  provider: "OpenAI GPT-4o"\n}
    App-->>User: "Smart Mode will process 18 pages\nEstimated: ₹22, ~45 seconds\nUsing: OpenAI GPT-4o"\n[Proceed] [Cancel]
```

---

## 8. API Specification

### 8.1 Base Path

`/api/v1/imports/{batch_id}/smart-process`

### 8.2 Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/estimate` | Return cost and time estimate before activating |
| `POST` | `/` | Trigger Smart Mode for the batch. Responds immediately; processing is async |
| `GET` | `/status` | Poll job status: QUEUED / RUNNING / COMPLETE / FAILED; includes pages_completed/page_count |
| `GET` | `/comparison` | Full SmartComparison[] once status = COMPLETE. Supports same filters as SM-I proposals |
| `POST` | `/accept` | Accept a list of AI rows (full-row accept). Triggers re-pipeline |
| `POST` | `/accept-all-recommended` | Accept all rows where recommendation = ACCEPT_AI |
| `POST` | `/reject` | Reject a list of AI rows (keep original). No re-pipeline needed |
| `PATCH` | `/comparison/{ai_row_id}/field-accept` | Accept specific fields from an AI row |
| `DELETE` | `/` | Discard Smart Mode results entirely — batch reverts to original proposals |

### 8.3 Status Poll Response

`GET /api/v1/imports/{batch_id}/smart-process/status`

```
{
  "smart_job_id": "uuid",
  "status": "RUNNING",
  "page_count": 18,
  "pages_completed": 11,
  "percent_complete": 61,
  "estimated_seconds_remaining": 17,
  "total_tokens_used": 16500
}
```

### 8.4 Comparison Response (partial example)

`GET /api/v1/imports/{batch_id}/smart-process/comparison`

```
[
  {
    "ai_row_id": "uuid",
    "match_type": "IMPROVED",
    "recommendation": "ACCEPT_AI",
    "diff_fields": [
      { "field": "narration", "original_value": "UPI/DR/8427/Pay", "ai_value": "UPI payment to Swiggy Order #8427", "ai_confidence": 0.94 },
      { "field": "reference_number", "original_value": null, "ai_value": "UPI8427219102KK", "ai_confidence": 0.91 }
    ],
    "original": {
      "txn_date": "2026-03-14",
      "amount_signed": -450.00,
      "narration": "UPI/DR/8427/Pay",
      "overall_confidence": 0.71
    },
    "ai_enhanced": {
      "txn_date": "2026-03-14",
      "amount_signed": -450.00,
      "narration": "UPI payment to Swiggy Order #8427",
      "reference_number": "UPI8427219102KK",
      "ai_overall_confidence": 0.93
    },
    "accepted": null
  },
  ...
]
```

---

## 9. Business Rules & Constraints

| Rule | Description |
|---|---|
| BR-J-01 | Smart Mode requires an active, configured LLM provider with vision capability. If no vision-capable provider exists, the Smart Mode button is disabled with "Configure an AI provider to enable this feature." |
| BR-J-02 | Smart Mode can only be triggered on batches in `IN_REVIEW` status. It cannot run on already-approved (COMPLETED) batches. |
| BR-J-03 | Only one SmartProcessingJob can be active per batch at a time. If a job is already RUNNING, triggering again returns the existing job status. |
| BR-J-04 | NEW rows returned by AI (match_type = NEW) are never auto-accepted. They always require explicit user review (recommendation = REVIEW_MANUALLY). |
| BR-J-05 | Accepted AI rows re-run the full downstream pipeline (SM-E → SM-F → SM-G → SM-H). They are NOT reprocessed by SM-C or SM-B — only the normalized field values are updated. |
| BR-J-06 | Original parse values are preserved in `AIEnhancedResult.original` at the time of comparison and are never overwritten. The audit trail always shows both versions. |
| BR-J-07 | Cost and token tracking is recorded even if the user rejects all AI results. Tokens consumed are non-refundable from the user's LLM API key. |
| BR-J-08 | If a SmartProcessingJob fails mid-way (network error, provider timeout), the completed pages are preserved. The user can retry from the failed page rather than restarting from page 1. |
| BR-J-09 | Deleting a Smart Mode job (`DELETE /smart-process`) removes all AIEnhancedResult rows and reverts the ImportBatch status to IN_REVIEW. It does NOT refund tokens already used. |

---

## 10. Error Catalog

| HTTP Status | Error Code | Scenario |
|---|---|---|
| 400 | `BATCH_NOT_IN_REVIEW` | Smart Mode triggered on a batch that is not in IN_REVIEW status |
| 400 | `NO_VISION_PROVIDER` | No LLM provider with vision capability configured |
| 409 | `JOB_ALREADY_RUNNING` | A SmartProcessingJob is already active for this batch |
| 409 | `COMPARISON_NOT_READY` | Comparison endpoint called before status = COMPLETE |
| 422 | `ACCEPT_ROW_NOT_FOUND` | ai_row_id in accept request not found for this batch |
| 422 | `FIELD_ACCEPT_INVALID` | Field-level accept references a field that is not in `diff_fields` |
| 503 | `PROVIDER_UNAVAILABLE` | LLM provider returned a non-retryable error during processing |

---

## 11. Integration Points Summary

```mermaid
flowchart TD
    SMB["SM-B: Document Ingestion\n(file bytes for vision input)"]
    SMI_READ["SM-I: Proposal Service\n(read existing proposals as context)"]
    SMD_VISION["SM-D: LLM Processing\nVision path (mode = smart_enhance)"]
    SME["SM-E: Schema Normalization\n(re-normalize accepted rows)"]
    SMF["SM-F: Deduplication\n(re-dedup accepted rows)"]
    SMG["SM-G: Categorization\n(re-categorize accepted rows)"]
    SMH["SM-H: Confidence Scoring\n(re-score accepted rows)"]
    SMI_WRITE["SM-I: Proposal Service\n(update PendingTransactions with AI results)"]

    SMJ["SM-J: Smart AI Mode"]

    SMB -->|"file bytes"| SMJ
    SMI_READ -->|"draft proposals as context"| SMJ
    SMJ -->|"enriched vision calls"| SMD_VISION
    SMD_VISION -->|"AIEnhancedResult rows"| SMJ
    SMJ -->|"accepted rows"| SME
    SME --> SMF --> SMG --> SMH --> SMI_WRITE
```
