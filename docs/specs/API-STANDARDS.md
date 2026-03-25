# API Standards & Conventions
## Ledger 3.0 | Cross-cutting Spec | Version 0.1 | March 15, 2026

---

## 1. Purpose

This document defines the **mandatory REST API conventions** for all Ledger 3.0 sub-modules (SM-A through SM-K). Every endpoint defined in any sub-module spec must conform to the standards here. Code generation tooling (FastAPI route generators, OpenAPI client generators) must treat this document as the authoritative source for boilerplate behavior.

---

## 2. OpenAPI Specification

Every sub-module exposes a self-contained **OpenAPI 3.1** document at:

```
GET /api/v1/{module}/openapi.json
GET /api/v1/{module}/openapi.yaml
```

And interactive docs at:

```
GET /api/v1/{module}/docs        (Swagger UI)
GET /api/v1/{module}/redoc       (ReDoc)
```

Where `{module}` is one of: `accounts`, `imports`, `parser`, `llm`, `normalize`, `dedup`, `categorize`, `score`, `proposals`, `smart-process`, `pipeline`.

### 2.1 Required OpenAPI Fields (per endpoint)

Every endpoint definition must include:

| OpenAPI Field | Requirement |
|---|---|
| `operationId` | Unique, camelCase, descriptive: `listProposals`, `approveProposal`, `uploadImport` |
| `summary` | One line, imperative verb: "List transaction proposals for a batch" |
| `description` | Full description including default behavior, side effects, auth requirements |
| `tags` | One or more module-scoped tags |
| `parameters` | All query/path/header params with `description`, `example`, `schema` |
| `requestBody` | Schema + at least one `example` for all POST/PUT/PATCH |
| `responses` | At minimum: success response + `400` + `401` + `404` (where applicable) + `422` + `500` |
| `security` | `[{ bearerAuth: [] }]` on all protected endpoints |

---

## 3. Authentication & Identity

All endpoints (except public health checks) require a **JWT Bearer token**.

```
Authorization: Bearer <jwt_token>
```

- The `user_id` is **always extracted from the JWT**, never accepted as a query or body parameter.
- Endpoints do not expose a `user_id` filter — the server scopes all queries to the authenticated user automatically.
- Tokens are validated for expiry on every request. Expired tokens return `401 UNAUTHORIZED`.

### 3.1 Standard Auth Error Responses

| HTTP Status | Error Code | Scenario |
|---|---|---|
| 401 | `TOKEN_MISSING` | Authorization header absent |
| 401 | `TOKEN_EXPIRED` | JWT exp claim has passed |
| 401 | `TOKEN_INVALID` | Signature verification failed or malformed |
| 403 | `FORBIDDEN` | Valid token but insufficient permissions (e.g. admin-only endpoint) |

---

## 4. URL Structure

```
/api/{version}/{resource}/{id}/{sub-resource}
```

| Segment | Rule |
|---|---|
| `/api` | Constant prefix |
| `/{version}` | `v1` for this release. Path-versioned — not header versioned. |
| `/{resource}` | Plural noun, lowercase, hyphenated: `pending-transactions`, `import-batches` |
| `/{id}` | UUID. Always a path parameter, never in the query string. |
| `/{sub-resource}` | Nested resource or action noun. Actions use nouns where possible: `/approve`, `/split`, `/score` |

**Examples:**

```
GET    /api/v1/accounts
POST   /api/v1/accounts
GET    /api/v1/accounts/{account_id}
PUT    /api/v1/accounts/{account_id}
DELETE /api/v1/accounts/{account_id}

GET    /api/v1/imports/{batch_id}/proposals
POST   /api/v1/imports/{batch_id}/proposals/{pending_id}/approve
POST   /api/v1/pipeline/import
```

### 4.1 Resource Naming

| Use | Avoid |
|---|---|
| `/import-batches` | `/importBatches`, `/ImportBatches` |
| `/pending-transactions` | `/pendingTransactions`, `/pending_transactions` |
| `/accounts/{id}/source-mappings` | `/accounts/{id}/sourcemappings` |
| `POST /proposals/{id}/approve` | `PUT /proposals/{id}/status` (prefer action nouns) |

---

## 5. HTTP Methods

| Method | Semantics | Body | Idempotent | Safe |
|---|---|---|---|---|
| `GET` | Retrieve. Never mutates. | No | Yes | Yes |
| `POST` | Create a resource; or trigger a non-idempotent action | Yes | No | No |
| `PUT` | Full replace of a resource | Yes | Yes | No |
| `PATCH` | Partial update (only provided fields changed) | Yes | No | No |
| `DELETE` | Soft-delete by default; documented where hard-delete | No | Yes | No |

**PATCH semantics:** Only explicitly provided fields are updated. Fields absent from the body are left unchanged. `null` explicitly clears a nullable field.

---

## 6. Pagination

All list endpoints that can return more than one record **must** support offset pagination. Cursor-based pagination may be added in v2 for high-volume streams.

### 6.1 Request Parameters

| Parameter | Type | Default | Max | Description |
|---|---|---|---|---|
| `page` | integer ≥ 1 | `1` | — | 1-based page number |
| `limit` | integer | `20` | `200` | Records per page |

`offset` is computed server-side as `(page - 1) * limit`. Clients do not send `offset` directly.

**Example:**
```
GET /api/v1/imports/{batch_id}/proposals?page=2&limit=50
```

### 6.2 Response Envelope

All paginated responses are wrapped in a standard envelope:

```json
{
  "data": [ ...records... ],
  "pagination": {
    "page": 2,
    "limit": 50,
    "total_records": 143,
    "total_pages": 3,
    "has_next": true,
    "has_prev": true,
    "next_page": 3,
    "prev_page": 1
  }
}
```

| Field | Description |
|---|---|
| `data` | Array of resource objects for the current page |
| `pagination.page` | Current page number (echoed from request) |
| `pagination.limit` | Records per page (echoed from request) |
| `pagination.total_records` | Total matching records (after filters applied) |
| `pagination.total_pages` | `ceil(total_records / limit)` |
| `pagination.has_next` | `page < total_pages` |
| `pagination.has_prev` | `page > 1` |
| `pagination.next_page` | Next page number; `null` if `has_next = false` |
| `pagination.prev_page` | Previous page number; `null` if `has_prev = false` |

### 6.3 Single-Object Responses

Endpoints returning a single resource (GET by ID, POST that creates one record) do **not** use the envelope. They return the resource object directly:

```json
{
  "account_id": "uuid",
  "name": "HDFC Savings",
  ...
}
```

### 6.4 Empty Results

An empty list is a `200 OK` with `data: []` and `total_records: 0`. It is never a `404`.

---

## 7. Sorting

### 7.1 Request Parameter

```
GET /api/v1/imports/{batch_id}/proposals?sort=txn_date:desc,amount_signed:asc
```

| Parameter | Format | Description |
|---|---|---|
| `sort` | `field:direction` | Comma-separated list. `direction` is `asc` or `desc`. |

**Rules:**
- Default sort is defined per endpoint and documented in its spec (not a global default).
- Multiple sort fields are applied in the order listed.
- Unsupported sort fields return `400 INVALID_SORT_FIELD`.
- Field names in `sort` use snake_case matching the response object's field names.

### 7.2 Sortable Fields (per resource)

Each sub-module spec defines the `sortable_fields` list for each list endpoint. Example for proposals:

| Field | Default direction |
|---|---|
| `txn_date` | desc |
| `amount_signed` | desc |
| `overall_confidence` | asc |
| `confidence_band` | asc (RED first: R < Y < G) |
| `created_at` | desc |

---

## 8. Filtering

### 8.1 Simple Equality Filters

Single-value equality filters are plain query parameters:

```
GET /api/v1/imports/{batch_id}/proposals?confidence_band=RED&dedup_status=NEW
```

### 8.2 Range Filters

For numeric and date fields, range operators use a suffix convention:

| Suffix | Operator | Example |
|---|---|---|
| `__gte` | ≥ | `amount_signed__gte=-5000` |
| `__lte` | ≤ | `amount_signed__lte=-100` |
| `__gt` | > | `overall_confidence__gt=0.85` |
| `__lt` | < | `overall_confidence__lt=0.60` |

Date ranges:
```
GET /api/v1/imports/{batch_id}/proposals?txn_date__gte=2026-01-01&txn_date__lte=2026-01-31
```

### 8.3 Multi-value (IN) Filters

Repeat the parameter to pass multiple values (treated as OR / IN):

```
GET /api/v1/imports/{batch_id}/proposals?confidence_band=RED&confidence_band=YELLOW
```

### 8.4 Boolean Filters

Pass `true` or `false` (lowercase string):

```
GET /api/v1/accounts?is_active=true&is_investment=false
```

### 8.5 Null / Exists Filters

```
GET /api/v1/proposals?transfer_pair__exists=false     (no transfer pair linked)
GET /api/v1/proposals?user_note__exists=true          (has a note)
```

### 8.6 Filterable Fields

Each sub-module spec declares a `filterable_fields` table per list endpoint. Attempting to filter on an undeclared field returns `400 INVALID_FILTER_FIELD`.

---

## 9. Search

### 9.1 Full-Text Search Parameter

```
GET /api/v1/accounts?q=hdfc+savings
GET /api/v1/proposals?q=swiggy
```

| Parameter | Type | Description |
|---|---|---|
| `q` | string | Free-text search. Minimum 2 characters. |

**Behavior:**
- `q` performs a case-insensitive `ILIKE %value%` search across the declared `searchable_fields` for that endpoint.
- `q` is applied **in addition to** any other filters (AND semantics).
- If `q` is less than 2 characters, return `400 SEARCH_QUERY_TOO_SHORT`.

### 9.2 Searchable Fields

Each sub-module spec declares `searchable_fields` per list endpoint. Example for accounts:

```
searchable_fields: [name, full_path, description]
```

Example for proposals:

```
searchable_fields: [narration, reference_number, user_note]
```

---

## 10. Field Selection (Sparse Fieldsets)

Clients can limit returned fields to reduce payload size:

```
GET /api/v1/imports/{batch_id}/proposals?fields=pending_id,txn_date,amount_signed,confidence_band
```

| Parameter | Description |
|---|---|
| `fields` | Comma-separated list of field names to include. Omit for full object. |

**Rules:**
- `id` fields (primary keys, foreign keys named in the path) are always included regardless of `fields`.
- Unknown field names in `fields` are silently ignored (no error).
- `fields` applies to each object in `data[]` in paginated responses.

---

## 11. Request & Response Format

### 11.1 Content Types

| Direction | Required content type |
|---|---|
| JSON request body | `Content-Type: application/json` |
| File upload | `Content-Type: multipart/form-data` |
| All responses | `Content-Type: application/json` |

Binary file downloads (e.g. export):
- `Content-Type: text/csv` or `application/pdf` as appropriate
- `Content-Disposition: attachment; filename="export.csv"`

### 11.2 Date & Time Format

| Type | Format | Example |
|---|---|---|
| Date | ISO 8601 date | `2026-01-31` |
| Datetime | ISO 8601 UTC with Z suffix | `2026-01-31T14:32:00Z` |
| Duration | ISO 8601 duration | `PT45S` (45 seconds) |

All timestamps in API responses are **UTC**. Timezone conversion is the client's responsibility.

### 11.3 Decimal / Amount Fields

- All monetary amounts use **decimal type** (not float) in the database and are serialized as **JSON numbers** in responses (not strings).
- Amounts are always in **INR** unless a `currency` field is present on the object.
- No rounding by the API — amounts are returned with exactly the precision stored.

### 11.4 UUID Format

All `id` fields are lowercase UUID v4 strings: `"3fa85f64-5717-4562-b3fc-2c963f66afa6"`.

### 11.5 Null vs. Absent Fields

- **Nullable fields** that have no value are returned as `null` in the JSON — they are never omitted from the response.
- A field that is absent from the response means it was not requested (via `fields` param) or is a write-only field (e.g. `password`).

---

## 12. Standard Error Response

All errors return a consistent JSON body regardless of status code:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request body is invalid.",
    "details": [
      {
        "field": "amount_signed",
        "issue": "Must be a non-zero decimal number.",
        "received": "0"
      },
      {
        "field": "txn_date",
        "issue": "Date is before account opening_date.",
        "received": "2024-12-01"
      }
    ],
    "request_id": "req_8f3a12bc",
    "docs_url": "https://docs.ledger.app/errors/VALIDATION_ERROR"
  }
}
```

| Field | Description |
|---|---|
| `error.code` | Snake-case machine-readable error code. Unique per error type. |
| `error.message` | Human-readable summary. |
| `error.details` | Optional array. Used for validation errors with per-field context. |
| `error.request_id` | Unique identifier for this request — used in support/debugging. |
| `error.docs_url` | Link to error documentation. Optional. |

### 12.1 Standard HTTP Status Codes

| Status | When |
|---|---|
| `200 OK` | Successful GET, PUT, PATCH, or synchronous POST |
| `201 Created` | Successful resource creation (POST that creates one record) |
| `202 Accepted` | Async operation accepted; poll for result |
| `204 No Content` | Successful DELETE with no body |
| `400 Bad Request` | Malformed request, invalid parameters, business rule violation |
| `401 Unauthorized` | Missing or invalid token |
| `403 Forbidden` | Valid token but access denied |
| `404 Not Found` | Resource does not exist or belongs to another user |
| `409 Conflict` | State conflict (e.g. approve already-approved record) |
| `422 Unprocessable Entity` | Request is well-formed but semantically invalid |
| `429 Too Many Requests` | Rate limit exceeded |
| `500 Internal Server Error` | Unhandled server error |
| `503 Service Unavailable` | Dependency (LLM provider, Accounting Engine) unavailable |

---

## 13. Async Operations

Long-running operations (file parsing, LLM extraction, re-scoring) return `202 Accepted` immediately and are polled via a status endpoint.

### 13.1 Async Response Contract

**Initial `202` response:**

```json
{
  "job_id": "uuid",
  "status": "QUEUED",
  "poll_url": "/api/v1/pipeline/import/status/uuid",
  "poll_interval_seconds": 2
}
```

**Status poll response (in-progress):**

```json
{
  "job_id": "uuid",
  "status": "RUNNING",
  "progress": {
    "current": 11,
    "total": 18,
    "unit": "pages",
    "percent_complete": 61
  },
  "estimated_seconds_remaining": 14,
  "started_at": "2026-03-15T14:32:00Z"
}
```

**Status poll response (complete):**

```json
{
  "job_id": "uuid",
  "status": "COMPLETE",
  "result_url": "/api/v1/imports/uuid/proposals",
  "completed_at": "2026-03-15T14:32:45Z",
  "duration_seconds": 45
}
```

**Status poll response (failed):**

```json
{
  "job_id": "uuid",
  "status": "FAILED",
  "error": {
    "code": "PROVIDER_UNAVAILABLE",
    "message": "LLM provider returned 503 after 3 retries.",
    "request_id": "req_8f3a12bc"
  },
  "failed_at": "2026-03-15T14:32:30Z"
}
```

### 13.2 Status Enum (all async jobs)

`QUEUED` → `RUNNING` → `COMPLETE` | `FAILED` | `CANCELLED`

### 13.3 Poll Frequency

Clients must respect `poll_interval_seconds` from the initial response. Default is 2 seconds. Minimum accepted interval is 1 second — requests faster than this return `429`.

---

## 14. Rate Limiting

Rate limits are applied per `user_id` (from JWT), not per IP.

| Tier | Limit | Window |
|---|---|---|
| Standard list/get endpoints | 300 requests | per minute |
| Write endpoints (POST, PUT, PATCH, DELETE) | 60 requests | per minute |
| File upload endpoints | 10 requests | per minute |
| LLM-dependent endpoints | 20 requests | per minute |

**Rate limit response headers** (included on every response):

```
X-RateLimit-Limit: 300
X-RateLimit-Remaining: 287
X-RateLimit-Reset: 1710510720
```

When exceeded:

```
HTTP 429 Too Many Requests
Retry-After: 32
```

---

## 15. Idempotency

Write operations that should be safe to retry must support an **idempotency key**.

```
Idempotency-Key: <client-generated-uuid>
```

| Endpoint type | Idempotency key | Behavior |
|---|---|---|
| File upload (`POST /pipeline/parse`) | Recommended | Server deduplicates by file hash + account_id anyway; idempotency key provides an extra safety net |
| Approve proposals | Recommended | Repeated approval of same `pending_id` with same key returns the original `200` from cache |
| Generic POST (create rules, etc.) | Optional | If key is provided and a response was already returned for it within 24h, cached response is returned |

**Behavior:**
- If a request with the same `Idempotency-Key` was processed within 24 hours, the server returns the original response with header `Idempotency-Replayed: true`.
- If the same key is reused with a **different** request body, the server returns `409 IDEMPOTENCY_KEY_REUSED`.

---

## 16. Response Headers

All responses include:

| Header | Value | Description |
|---|---|---|
| `X-Request-ID` | UUID | Unique identifier for the request (same as `error.request_id`) |
| `X-API-Version` | `v1` | API version that handled the request |
| `Content-Type` | `application/json` | Always present on JSON responses |
| `X-RateLimit-Limit` | integer | See §14 |
| `X-RateLimit-Remaining` | integer | See §14 |
| `X-RateLimit-Reset` | Unix timestamp | See §14 |

Async operation responses additionally include:

| Header | Value |
|---|---|
| `Location` | URL of the poll endpoint (mirrors `poll_url` in body) |

---

## 17. CORS

CORS is configured at the API gateway level:

```
Access-Control-Allow-Origin: https://app.ledger.app (production)
Access-Control-Allow-Origin: * (development)
Access-Control-Allow-Methods: GET, POST, PUT, PATCH, DELETE, OPTIONS
Access-Control-Allow-Headers: Authorization, Content-Type, Idempotency-Key, X-Request-ID
Access-Control-Max-Age: 86400
```

---

## 18. Health & Meta Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | None | Basic health check. Returns `200 { "status": "ok" }` |
| `GET` | `/health/ready` | None | Readiness check (DB connections, dependency status). Returns `200` or `503`. |
| `GET` | `/api/v1/version` | None | Returns current API version, build timestamp, git commit |

**Version response:**

```json
{
  "api_version": "v1",
  "app_version": "3.0.0",
  "build_at": "2026-03-15T00:00:00Z",
  "git_commit": "abc123f"
}
```

---

## 19. Bulk Endpoints

When operating on multiple records in a single request:

### 19.1 Request

```json
POST /api/v1/proposals/bulk-approve
{
  "ids": ["uuid1", "uuid2", "uuid3"]
}
```

Maximum batch size per bulk call: **200 IDs**. Exceeding returns `400 BULK_LIMIT_EXCEEDED`.

### 19.2 Partial Success Response

If any items in a bulk operation fail while others succeed, return `207 Multi-Status`:

```json
{
  "results": [
    { "id": "uuid1", "status": 200, "message": "approved" },
    { "id": "uuid2", "status": 409, "error": { "code": "ALREADY_APPROVED", "message": "Already approved." } },
    { "id": "uuid3", "status": 200, "message": "approved" }
  ],
  "summary": {
    "total": 3,
    "succeeded": 2,
    "failed": 1
  }
}
```

If **all** items fail, return `400`. If **all** items succeed, return `200` (not `207`).

---

## 20. Deprecation Policy

When an endpoint is deprecated:

1. Add `Deprecation: true` and `Sunset: <date>` response headers at least **3 months** before removal.
2. Add `deprecated: true` to the endpoint in the OpenAPI spec.
3. Document the replacement endpoint in the `description` field.

```
Deprecation: true
Sunset: Sat, 15 Jun 2026 00:00:00 GMT
Link: </api/v2/proposals>; rel="successor-version"
```

---

## 21. OpenAPI Tags Reference

All sub-module endpoints are tagged consistently for grouping in generated documentation:

| Tag | Modules |
|---|---|
| `Accounts` | SM-A |
| `Imports` | SM-B |
| `Parser` | SM-C |
| `LLM` | SM-D |
| `Normalization` | SM-E |
| `Deduplication` | SM-F |
| `Categorization` | SM-G |
| `Scoring` | SM-H |
| `Proposals` | SM-I |
| `SmartProcessing` | SM-J |
| `Pipeline` | SM-K |
| `Meta` | Health, version |

---

## 22. Query Parameter Reference Card

Quick reference for code generation. These parameters are recognized on all applicable list endpoints.

| Parameter | Type | Section |
|---|---|---|
| `page` | integer | §6 Pagination |
| `limit` | integer | §6 Pagination |
| `sort` | string (`field:asc\|desc,...`) | §7 Sorting |
| `q` | string (min 2 chars) | §9 Search |
| `fields` | string (comma-separated) | §10 Field Selection |
| `{field}` | equality filter | §8.1 Filtering |
| `{field}__gte` | range filter | §8.2 Filtering |
| `{field}__lte` | range filter | §8.2 Filtering |
| `{field}__gt` | range filter | §8.2 Filtering |
| `{field}__lt` | range filter | §8.2 Filtering |
| `{field}__exists` | boolean | §8.5 Filtering |
