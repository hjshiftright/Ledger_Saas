# Engineering Requirements Document: Onboarding Module

**Project:** Personal Finance Management System (PFMS)
**Module:** Onboarding (`pfms-onboarding`)
**Version:** 1.0
**Date:** March 14, 2026
**Status:** Draft for Review

---

## 1. Purpose and Scope

This document is the architectural and design source of truth for the Onboarding module of PFMS. It defines how every sub-module is built, tested, and integrated. All implementation work must conform to the specifications herein.

The Onboarding module handles the first-run experience: everything a user must configure before they can begin recording daily financial transactions. It produces a fully initialized system with a user profile, a Chart of Accounts, registered institutions and accounts, opening balances, optional goals and budgets, recurring templates, and a baseline net worth snapshot.

### 1.1 What This Document Covers

The nine onboarding sub-modules (Profile, COA, Institutions, Accounts, Opening Balances, Goals, Budget, Recurring Templates, Net Worth) plus the Onboarding Orchestrator. For each: API contract, data model, validation rules, service behavior, error taxonomy, and test specifications.

### 1.2 What This Document Does Not Cover

Transaction entry, reporting, portfolio tracking, and UI/UX design. These are covered in separate ERDs. The CLI client described here is for testing and demonstration only — it is not the production user interface.

---

## 2. Architecture Overview

### 2.1 Layered Architecture

The system follows a strict four-layer architecture. Each layer may only call the layer directly below it — never upward or sideways across modules except through defined events.

```
┌─────────────────────────────────────────────────────┐
│  Layer 4: Client Interfaces                         │
│  ┌──────────────┐  ┌──────────────┐                 │
│  │  REST API     │  │  CLI Client  │   (Future: UI) │
│  │  (FastAPI)    │  │  (Typer)     │                 │
│  └──────┬───────┘  └──────┬───────┘                 │
│         │                 │                          │
│         ▼                 ▼                          │
│  Layer 3: API Router / Controller                    │
│  ┌─────────────────────────────────────────┐        │
│  │  Request validation, response shaping,  │        │
│  │  HTTP status mapping, OpenAPI schemas   │        │
│  └──────────────────┬──────────────────────┘        │
│                     │                                │
│                     ▼                                │
│  Layer 2: Service Layer (Business Logic)             │
│  ┌─────────────────────────────────────────┐        │
│  │  Orchestration, validation, computation,│        │
│  │  domain rules, event emission           │        │
│  └──────────────────┬──────────────────────┘        │
│                     │                                │
│                     ▼                                │
│  Layer 1: Repository Layer (Data Access)             │
│  ┌─────────────────────────────────────────┐        │
│  │  Abstract repository interfaces,       │        │
│  │  SQLite implementations, in-memory      │        │
│  │  stubs for testing                      │        │
│  └─────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────┘
```

### 2.2 Key Architectural Decisions

**AD-1: API-First Development.** Every feature is first expressed as an OpenAPI endpoint. The Swagger UI is the primary tool for manual validation before any CLI or graphical UI is built.

**AD-2: SDK-Style Service Layer.** The service layer is designed as an importable Python SDK. Any future interface (web UI, mobile app, desktop app, chatbot) calls the same service methods. The FastAPI routes are thin wrappers around service calls.

**AD-3: Repository Abstraction.** All data access happens through abstract repository interfaces (Python `Protocol` classes). Two implementations exist for each: an in-memory stub (for unit tests) and a SQLAlchemy Core implementation (for integration tests and production). The SQLAlchemy Core implementation works with any supported engine (SQLite, PostgreSQL). Swapping database engines requires changing only the connection string.

**AD-4: TDD Mandatory.** No service method is implemented without a failing test written first. The test defines the expected behavior; the implementation makes it pass. Test coverage target: 95% line coverage for service layer, 90% for repository layer.

**AD-5: Double-Entry Integrity.** Every monetary operation — including opening balances — produces a balanced double-entry transaction. There is no method in the system that modifies an account balance directly. Balances are always derived by summing transaction lines.

**AD-6: Indian Financial Context as First-Class Concern.** The system natively supports Indian Rupee (₹), Indian numbering format (lakhs/crores), Indian Financial Year (April–March), Indian tax regimes (Old/New), and Indian financial instruments (PPF, NPS, EPF, FD, RD, SIP, etc.). Internationalization is deferred but the architecture does not preclude it.

---

## 3. Tech Stack

### 3.1 Core

| Component | Technology | Version | Rationale |
|---|---|---|---|
| Language | Python | 3.11+ | Type hints, match statements, modern async |
| API Framework | FastAPI | 0.100+ | Auto OpenAPI/Swagger, Pydantic integration, async support |
| Validation | Pydantic v2 | 2.0+ | DTO definition, input validation, serialization |
| Database | SQLite (default) | 3.40+ | Zero-config, embedded; engine configurable via SQLAlchemy connection string |
| Data Access | SQLAlchemy Core | 2.0+ | Database-agnostic SQL expression builder; query visibility without raw SQL strings |
| CLI Framework | Typer | 0.9+ | Built on Click, auto help generation, type-safe |
| Testing | pytest | 7.0+ | Fixtures, parameterization, rich plugin ecosystem |
| Test Coverage | pytest-cov | 4.0+ | Coverage reporting |
| API Testing | httpx + pytest | — | Async test client for FastAPI |
| Linting | Ruff | 0.1+ | Fast, replaces flake8+isort+black |
| Type Checking | mypy | 1.5+ | Static type analysis, strict mode |

### 3.2 Development Tools

| Tool | Purpose |
|---|---|
| Swagger UI | Interactive API testing (built into FastAPI at `/docs`) |
| ReDoc | Alternative API docs (built into FastAPI at `/redoc`) |
| SQLite Browser | Database inspection during development |
| Make / Taskfile | Task runner for common commands (`make test`, `make lint`, etc.) |

---

## 4. Project Structure

```
pfms/
├── pyproject.toml                    # Project metadata, dependencies
├── Makefile                          # Task runner
├── README.md
│
├── src/
│   └── pfms/
│       ├── __init__.py
│       ├── main.py                   # FastAPI application factory
│       ├── config.py                 # App configuration (DB path, etc.)
│       ├── dependencies.py           # Dependency injection setup
│       │
│       ├── common/                   # Shared utilities
│       │   ├── __init__.py
│       │   ├── enums.py              # All shared enumerations
│       │   ├── exceptions.py         # Exception hierarchy
│       │   ├── types.py              # Type aliases (Money, AccountCode, etc.)
│       │   ├── validators.py         # Reusable Pydantic validators
│       │   └── events.py            # Event bus (simple in-process pub/sub)
│       │
│       ├── onboarding/               # ONBOARDING MODULE
│       │   ├── __init__.py
│       │   ├── router.py            # FastAPI router aggregating all sub-routers
│       │   │
│       │   ├── profile/
│       │   │   ├── __init__.py
│       │   │   ├── schemas.py        # Pydantic DTOs (request/response)
│       │   │   ├── service.py        # Business logic
│       │   │   ├── router.py         # FastAPI endpoints
│       │   │   └── constants.py      # Supported currencies, tax regimes, etc.
│       │   │
│       │   ├── coa/
│       │   │   ├── __init__.py
│       │   │   ├── schemas.py
│       │   │   ├── service.py
│       │   │   ├── router.py
│       │   │   ├── default_tree.py   # Static default COA definition
│       │   │   └── constants.py
│       │   │
│       │   ├── institution/
│       │   │   ├── __init__.py
│       │   │   ├── schemas.py
│       │   │   ├── service.py
│       │   │   ├── router.py
│       │   │   └── seed_data.py      # Pre-seeded Indian institutions
│       │   │
│       │   ├── account/
│       │   │   ├── __init__.py
│       │   │   ├── schemas.py        # All account type DTOs
│       │   │   ├── service.py        # Account setup service
│       │   │   ├── router.py
│       │   │   ├── account_types.py  # Per-type setup logic
│       │   │   └── constants.py
│       │   │
│       │   ├── opening_balance/
│       │   │   ├── __init__.py
│       │   │   ├── schemas.py
│       │   │   ├── service.py
│       │   │   └── router.py
│       │   │
│       │   ├── goal/
│       │   │   ├── __init__.py
│       │   │   ├── schemas.py
│       │   │   ├── service.py
│       │   │   ├── router.py
│       │   │   └── calculators.py    # Contribution calculator, projections
│       │   │
│       │   ├── budget/
│       │   │   ├── __init__.py
│       │   │   ├── schemas.py
│       │   │   ├── service.py
│       │   │   └── router.py
│       │   │
│       │   ├── recurring/
│       │   │   ├── __init__.py
│       │   │   ├── schemas.py
│       │   │   ├── service.py
│       │   │   └── router.py
│       │   │
│       │   ├── networth/
│       │   │   ├── __init__.py
│       │   │   ├── schemas.py
│       │   │   ├── service.py
│       │   │   └── router.py
│       │   │
│       │   └── orchestrator/
│       │       ├── __init__.py
│       │       ├── schemas.py
│       │       ├── service.py
│       │       └── router.py
│       │
│       └── repositories/             # DATA ACCESS LAYER
│           ├── __init__.py
│           ├── protocols.py          # Abstract interfaces (Protocol classes)
│           ├── sqlalchemy/           # SQLAlchemy Core implementations
│           │   ├── __init__.py
│           │   ├── engine.py         # Engine creation and connection management
│           │   ├── tables.py         # SQLAlchemy Table definitions (MetaData)
│           │   ├── settings_repo.py
│           │   ├── account_repo.py
│           │   ├── institution_repo.py
│           │   ├── transaction_repo.py
│           │   ├── goal_repo.py
│           │   ├── budget_repo.py
│           │   └── recurring_repo.py
│           └── inmemory/             # In-memory stubs for testing
│               ├── __init__.py
│               ├── settings_repo.py
│               ├── account_repo.py
│               └── ... (mirrors sqlalchemy/)
│
├── cli/
│   └── pfms_cli/
│       ├── __init__.py
│       ├── main.py                   # Typer app entry point
│       ├── onboarding_commands.py    # CLI commands for onboarding
│       └── formatters.py            # Table/tree output formatting
│
├── tests/
│   ├── conftest.py                   # Shared fixtures
│   ├── unit/
│   │   ├── conftest.py              # In-memory repo fixtures
│   │   ├── test_profile_service.py
│   │   ├── test_coa_service.py
│   │   ├── test_institution_service.py
│   │   ├── test_account_service.py
│   │   ├── test_opening_balance_service.py
│   │   ├── test_goal_service.py
│   │   ├── test_budget_service.py
│   │   ├── test_recurring_service.py
│   │   ├── test_networth_service.py
│   │   └── test_orchestrator_service.py
│   ├── integration/
│   │   ├── conftest.py              # SQLite fixtures (temp DB per test)
│   │   ├── test_profile_api.py
│   │   ├── test_coa_api.py
│   │   ├── test_account_api.py
│   │   └── test_full_onboarding_flow.py
│   └── e2e/
│       └── test_onboarding_e2e.py   # Full API-driven end-to-end
│
└── docs/
    ├── erd.md                        # Entity relationship diagrams
    ├── api_examples.md               # Curl/httpie example calls
    └── onboarding_flow.md           # State machine diagrams
```

---

## 5. Design Principles and Patterns

### 5.1 Dependency Injection

All services receive their repository dependencies through constructor injection. FastAPI's `Depends()` mechanism wires this at the router level.

```python
# Service — no knowledge of how repos are created
class ProfileService:
    def __init__(self, settings_repo: SettingsRepository):
        self._settings = settings_repo

# Dependency provider — swappable
def get_profile_service(
    settings_repo: SettingsRepository = Depends(get_settings_repo)
) -> ProfileService:
    return ProfileService(settings_repo)

# Router — thin wrapper
@router.post("/profile", response_model=ProfileResponse)
def setup_profile(
    request: ProfileSetupRequest,
    service: ProfileService = Depends(get_profile_service)
):
    return service.setup_profile(request)
```

### 5.2 Repository Protocol (Interface)

Every repository is defined as a Python `Protocol`. This is the contract between service and data layers.

```python
from typing import Protocol, Optional

class SettingsRepository(Protocol):
    def get(self, key: str) -> Optional[str]: ...
    def set(self, key: str, value: str) -> None: ...
    def get_bulk(self, prefix: str) -> dict[str, str]: ...
    def delete(self, key: str) -> None: ...
    def exists(self, key: str) -> bool: ...
```

The in-memory implementation for testing:

```python
class InMemorySettingsRepository:
    def __init__(self):
        self._store: dict[str, str] = {}

    def get(self, key: str) -> Optional[str]:
        return self._store.get(key)

    def set(self, key: str, value: str) -> None:
        self._store[key] = value

    # ... etc
```

The SQLAlchemy Core implementation for production:

```python
from sqlalchemy import Table, MetaData, select, insert
from sqlalchemy.engine import Engine

class SQLAlchemySettingsRepository:
    def __init__(self, engine: Engine, metadata: MetaData):
        self._engine = engine
        self._settings: Table = metadata.tables["settings"]

    def get(self, key: str) -> Optional[str]:
        with self._engine.connect() as conn:
            stmt = select(self._settings.c.value).where(
                self._settings.c.key == key
            )
            row = conn.execute(stmt).fetchone()
            return row[0] if row else None
    # ... etc
```

### 5.3 Result Pattern for Error Handling

Services return structured results rather than raising exceptions for expected business rule violations. Unexpected errors (database failures) still raise exceptions.

```python
from dataclasses import dataclass
from typing import Generic, TypeVar, Union

T = TypeVar("T")

@dataclass(frozen=True)
class Success(Generic[T]):
    value: T

@dataclass(frozen=True)
class Failure:
    error_code: str
    message: str
    details: dict | None = None

ServiceResult = Union[Success[T], Failure]
```

Usage in service:

```python
def setup_profile(self, dto: ProfileSetupRequest) -> ServiceResult[ProfileResponse]:
    if not dto.display_name.strip():
        return Failure("VALIDATION_ERROR", "Display name cannot be empty")
    # ... persist ...
    return Success(ProfileResponse(...))
```

The router layer maps `Failure` to HTTP error responses:

```python
@router.post("/profile", response_model=ProfileResponse)
def setup_profile(request: ProfileSetupRequest, service=Depends(...)):
    result = service.setup_profile(request)
    match result:
        case Success(value):
            return value
        case Failure(error_code="VALIDATION_ERROR") as f:
            raise HTTPException(status_code=422, detail=f.message)
        case Failure(error_code="DUPLICATE_ERROR") as f:
            raise HTTPException(status_code=409, detail=f.message)
        case Failure() as f:
            raise HTTPException(status_code=400, detail=f.message)
```

### 5.4 Event Bus

Cross-module communication happens through a simple synchronous in-process event bus. When an account is created, the service emits an event. Other modules (like net worth or orchestrator) can subscribe.

```python
class EventBus:
    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = {}

    def subscribe(self, event_type: str, handler: Callable) -> None:
        self._subscribers.setdefault(event_type, []).append(handler)

    def publish(self, event_type: str, payload: dict) -> None:
        for handler in self._subscribers.get(event_type, []):
            handler(payload)
```

Events defined for onboarding: `profile.created`, `coa.initialized`, `institution.created`, `account.created`, `opening_balance.set`, `goal.created`, `budget.created`, `recurring_template.created`, `networth.computed`, `onboarding.completed`.

---

## 6. Common Enumerations

All enums are defined centrally in `pfms/common/enums.py` and imported everywhere.

```python
from enum import Enum

class Currency(str, Enum):
    INR = "INR"
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"

class TaxRegime(str, Enum):
    OLD = "OLD"
    NEW = "NEW"

class AccountType(str, Enum):
    ASSET = "ASSET"
    LIABILITY = "LIABILITY"
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
    EQUITY = "EQUITY"

class AccountSubType(str, Enum):
    BANK = "BANK"
    CASH = "CASH"
    CREDIT_CARD = "CREDIT_CARD"
    LOAN = "LOAN"
    BROKERAGE = "BROKERAGE"
    FIXED_DEPOSIT = "FIXED_DEPOSIT"
    RECURRING_DEPOSIT = "RECURRING_DEPOSIT"
    PPF = "PPF"
    EPF = "EPF"
    NPS = "NPS"
    INSURANCE = "INSURANCE"
    PROPERTY = "PROPERTY"
    GOLD = "GOLD"
    MUTUAL_FUND = "MUTUAL_FUND"
    EQUITY_SHARES = "EQUITY_SHARES"

class NormalBalance(str, Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"

class InstitutionType(str, Enum):
    BANK = "BANK"
    NBFC = "NBFC"
    BROKERAGE = "BROKERAGE"
    AMC = "AMC"
    INSURANCE = "INSURANCE"
    GOVERNMENT = "GOVERNMENT"     # For EPF, PPF, NPS
    OTHER = "OTHER"

class BankAccountType(str, Enum):
    SAVINGS = "SAVINGS"
    CURRENT = "CURRENT"
    SALARY = "SALARY"

class LoanType(str, Enum):
    HOME = "HOME"
    VEHICLE = "VEHICLE"
    PERSONAL = "PERSONAL"
    EDUCATION = "EDUCATION"
    GOLD = "GOLD"
    OTHER = "OTHER"

class GoalType(str, Enum):
    EMERGENCY_FUND = "EMERGENCY_FUND"
    RETIREMENT = "RETIREMENT"
    HOME_PURCHASE = "HOME_PURCHASE"
    VEHICLE_PURCHASE = "VEHICLE_PURCHASE"
    EDUCATION = "EDUCATION"
    VACATION = "VACATION"
    WEDDING = "WEDDING"
    DEBT_PAYOFF = "DEBT_PAYOFF"
    CUSTOM = "CUSTOM"

class GoalPriority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class GoalStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ACHIEVED = "ACHIEVED"
    ABANDONED = "ABANDONED"
    PAUSED = "PAUSED"

class Frequency(str, Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    BIWEEKLY = "BIWEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    HALF_YEARLY = "HALF_YEARLY"
    YEARLY = "YEARLY"

class RecurringType(str, Enum):
    SIP = "SIP"
    EMI = "EMI"
    RENT = "RENT"
    SALARY_CREDIT = "SALARY_CREDIT"
    SUBSCRIPTION = "SUBSCRIPTION"
    INSURANCE_PREMIUM = "INSURANCE_PREMIUM"
    UTILITY_BILL = "UTILITY_BILL"
    CUSTOM = "CUSTOM"

class OnboardingStep(str, Enum):
    PROFILE = "PROFILE"
    COA_SETUP = "COA_SETUP"
    INSTITUTION_SETUP = "INSTITUTION_SETUP"
    ACCOUNT_SETUP = "ACCOUNT_SETUP"
    OPENING_BALANCES = "OPENING_BALANCES"
    GOAL_PLANNING = "GOAL_PLANNING"
    BUDGET_SETUP = "BUDGET_SETUP"
    RECURRING_SETUP = "RECURRING_SETUP"
    NETWORTH_REVIEW = "NETWORTH_REVIEW"

class OnboardingStepStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"
```

---

## 7. Exception Hierarchy

```python
class PFMSError(Exception):
    """Base exception for all PFMS errors."""
    def __init__(self, message: str, error_code: str):
        self.message = message
        self.error_code = error_code
        super().__init__(message)

class ValidationError(PFMSError):
    """Input validation failure."""
    def __init__(self, message: str, field: str | None = None):
        self.field = field
        super().__init__(message, "VALIDATION_ERROR")

class NotFoundError(PFMSError):
    """Requested entity does not exist."""
    def __init__(self, entity: str, identifier: str | int):
        super().__init__(f"{entity} '{identifier}' not found", "NOT_FOUND")

class DuplicateError(PFMSError):
    """Entity with same unique key already exists."""
    def __init__(self, entity: str, key: str):
        super().__init__(f"{entity} with '{key}' already exists", "DUPLICATE")

class SystemAccountError(PFMSError):
    """Attempt to modify a system-managed account."""
    def __init__(self, account_name: str):
        super().__init__(
            f"Cannot modify system account '{account_name}'",
            "SYSTEM_ACCOUNT"
        )

class BusinessRuleError(PFMSError):
    """Domain/business rule violation."""
    def __init__(self, message: str):
        super().__init__(message, "BUSINESS_RULE")

class OnboardingSequenceError(PFMSError):
    """Onboarding steps accessed out of order."""
    def __init__(self, message: str):
        super().__init__(message, "ONBOARDING_SEQUENCE")
```

FastAPI maps these to HTTP codes via a global exception handler:

```python
@app.exception_handler(PFMSError)
async def pfms_error_handler(request: Request, exc: PFMSError):
    status_map = {
        "VALIDATION_ERROR": 422,
        "NOT_FOUND": 404,
        "DUPLICATE": 409,
        "SYSTEM_ACCOUNT": 403,
        "BUSINESS_RULE": 400,
        "ONBOARDING_SEQUENCE": 409,
    }
    return JSONResponse(
        status_code=status_map.get(exc.error_code, 400),
        content={
            "error_code": exc.error_code,
            "message": exc.message
        }
    )
```

---

## 8. Sub-Module Specifications

### 8.1 Profile Creation

**API Prefix:** `/api/v1/onboarding/profile`

**Endpoints:**

| Method | Path | Description | Request Body | Response |
|--------|------|-------------|--------------|----------|
| POST | `/` | Create or update user profile | `ProfileSetupRequest` | `201: ProfileResponse` |
| GET | `/` | Retrieve current profile | — | `200: ProfileResponse` or `404` |
| GET | `/status` | Check if profile is complete | — | `200: {"complete": bool}` |

**Request Schema — `ProfileSetupRequest`:**

```python
class ProfileSetupRequest(BaseModel):
    display_name: str = Field(
        ..., min_length=1, max_length=100,
        description="User's display name"
    )
    base_currency: Currency = Field(
        default=Currency.INR,
        description="Primary currency for all transactions"
    )
    financial_year_start_month: int = Field(
        default=4,
        ge=1, le=12,
        description="Month number when FY starts (4=April for India)"
    )
    tax_regime: TaxRegime = Field(
        default=TaxRegime.NEW,
        description="Indian income tax regime"
    )
    date_format: str = Field(
        default="DD/MM/YYYY",
        pattern=r"^(DD/MM/YYYY|MM/DD/YYYY|YYYY-MM-DD)$"
    )
    number_format: str = Field(
        default="INDIAN",
        pattern=r"^(INDIAN|INTERNATIONAL)$",
        description="INDIAN=12,34,567.89  INTERNATIONAL=1,234,567.89"
    )
```

**Response Schema — `ProfileResponse`:**

```python
class ProfileResponse(BaseModel):
    display_name: str
    base_currency: Currency
    financial_year_start_month: int
    tax_regime: TaxRegime
    date_format: str
    number_format: str
    created_at: datetime
    updated_at: datetime
```

**Service Behavior:**

The `ProfileService.setup_profile()` method persists each field as an individual setting in the `SettingsRepository` under the `profile.*` namespace (e.g., `profile.display_name`, `profile.base_currency`). This is an upsert — calling it again overwrites previous values. On first call it emits a `profile.created` event; on subsequent calls it emits `profile.updated`.

The `ProfileService.get_profile()` method reads all `profile.*` keys and assembles a `ProfileResponse`. If any required key is missing, it raises `NotFoundError`.

The `ProfileService.is_profile_complete()` method checks that all required keys exist and are non-empty. Returns a boolean.

**Test Specifications:**

```
UNIT TESTS (test_profile_service.py):
├── test_setup_profile_with_valid_data_stores_all_fields
├── test_setup_profile_with_defaults_uses_indian_defaults
├── test_get_profile_returns_stored_data
├── test_get_profile_when_no_profile_raises_not_found
├── test_setup_profile_twice_overwrites_cleanly
├── test_is_complete_returns_false_when_no_profile
├── test_is_complete_returns_true_after_setup
├── test_is_complete_returns_false_when_partial_data
├── test_empty_display_name_rejected
├── test_invalid_currency_rejected
├── test_invalid_fy_month_rejected
├── test_profile_created_event_emitted_on_first_setup
└── test_profile_updated_event_emitted_on_second_setup

INTEGRATION TESTS (test_profile_api.py):
├── test_post_profile_returns_201
├── test_get_profile_returns_200
├── test_get_profile_before_setup_returns_404
├── test_post_profile_with_invalid_data_returns_422
└── test_profile_status_endpoint
```

---

### 8.2 Chart of Accounts

**API Prefix:** `/api/v1/onboarding/coa`

**Endpoints:**

| Method | Path | Description | Request Body | Response |
|--------|------|-------------|--------------|----------|
| POST | `/initialize` | Create default COA | — | `201: COATreeResponse` |
| GET | `/tree` | Get full COA tree | — | `200: COATreeResponse` |
| GET | `/accounts/{id}` | Get single account | — | `200: AccountNodeResponse` |
| PATCH | `/accounts/{id}` | Rename an account | `RenameAccountRequest` | `200: AccountNodeResponse` |
| POST | `/accounts` | Add custom category | `AddCategoryRequest` | `201: AccountNodeResponse` |
| DELETE | `/accounts/{id}` | Deactivate a category | — | `204` |
| GET | `/status` | Check if COA is ready | — | `200: {"ready": bool}` |

**Default COA Tree Structure (India-specific):**

```
1000  Assets (ASSET, placeholder)
├── 1100  Bank Accounts (BANK, placeholder)
├── 1200  Cash (CASH, placeholder)
│   └── 1201  Cash in Hand (CASH, leaf)
├── 1300  Deposits (placeholder)
│   ├── 1310  Fixed Deposits (FIXED_DEPOSIT, placeholder)
│   ├── 1320  Recurring Deposits (RECURRING_DEPOSIT, placeholder)
│   └── 1330  PPF (PPF, placeholder)
├── 1400  Retirement (placeholder)
│   ├── 1410  EPF (EPF, placeholder)
│   └── 1420  NPS (NPS, placeholder)
├── 1500  Investments (placeholder)
│   ├── 1510  Brokerage Accounts (BROKERAGE, placeholder)
│   ├── 1520  Mutual Funds (MUTUAL_FUND, placeholder)
│   └── 1530  Gold (GOLD, placeholder)
├── 1600  Property (PROPERTY, placeholder)
├── 1700  Insurance (INSURANCE, placeholder)
├── 1800  Receivables (placeholder)
│   └── 1801  Loans Given (leaf)
└── 1900  Other Assets (placeholder)

2000  Liabilities (LIABILITY, placeholder)
├── 2100  Credit Cards (CREDIT_CARD, placeholder)
├── 2200  Loans (LOAN, placeholder)
│   ├── 2210  Home Loans (placeholder)
│   ├── 2220  Vehicle Loans (placeholder)
│   ├── 2230  Personal Loans (placeholder)
│   ├── 2240  Education Loans (placeholder)
│   └── 2250  Other Loans (placeholder)
├── 2300  Payables (placeholder)
│   └── 2301  Amounts Owed (leaf)
└── 2900  Other Liabilities (placeholder)

3000  Income (INCOME, placeholder)
├── 3100  Salary & Wages (placeholder)
│   ├── 3101  Basic Salary (leaf)
│   ├── 3102  HRA Received (leaf)
│   ├── 3103  Special Allowance (leaf)
│   └── 3104  Bonus (leaf)
├── 3200  Interest Income (placeholder)
│   ├── 3201  Bank Interest (leaf)
│   ├── 3202  FD Interest (leaf)
│   └── 3203  RD Interest (leaf)
├── 3300  Dividend Income (leaf)
├── 3400  Capital Gains (placeholder)
│   ├── 3401  Short Term Capital Gains (leaf)
│   └── 3402  Long Term Capital Gains (leaf)
├── 3500  Rental Income (leaf)
├── 3600  Freelance / Business Income (leaf)
├── 3700  Gifts Received (leaf)
└── 3900  Other Income (leaf)

4000  Expenses (EXPENSE, placeholder)
├── 4100  Housing (placeholder)
│   ├── 4101  Rent (leaf)
│   ├── 4102  Maintenance / Society Charges (leaf)
│   └── 4103  Property Tax (leaf)
├── 4200  Utilities (placeholder)
│   ├── 4201  Electricity (leaf)
│   ├── 4202  Water (leaf)
│   ├── 4203  Gas (leaf)
│   ├── 4204  Internet / Broadband (leaf)
│   └── 4205  Mobile / Phone (leaf)
├── 4300  Food & Dining (placeholder)
│   ├── 4301  Groceries (leaf)
│   ├── 4302  Restaurants / Eating Out (leaf)
│   ├── 4303  Food Delivery (leaf)
│   └── 4304  Beverages (leaf)
├── 4400  Transportation (placeholder)
│   ├── 4401  Fuel (leaf)
│   ├── 4402  Public Transport (leaf)
│   ├── 4403  Cab / Ride Hailing (leaf)
│   ├── 4404  Vehicle Maintenance (leaf)
│   └── 4405  Parking / Tolls (leaf)
├── 4500  Healthcare (placeholder)
│   ├── 4501  Doctor / Consultation (leaf)
│   ├── 4502  Medicines (leaf)
│   ├── 4503  Lab Tests (leaf)
│   └── 4504  Health Insurance Premium (leaf)
├── 4600  Insurance Premiums (placeholder)
│   ├── 4601  Life Insurance (leaf)
│   ├── 4602  Vehicle Insurance (leaf)
│   └── 4603  Other Insurance (leaf)
├── 4700  Education (placeholder)
│   ├── 4701  School / College Fees (leaf)
│   ├── 4702  Books / Courses (leaf)
│   └── 4703  Coaching / Tuition (leaf)
├── 4800  Shopping (placeholder)
│   ├── 4801  Clothing (leaf)
│   ├── 4802  Electronics (leaf)
│   ├── 4803  Home & Kitchen (leaf)
│   └── 4804  Personal Care (leaf)
├── 4900  Entertainment (placeholder)
│   ├── 4901  Streaming Subscriptions (leaf)
│   ├── 4902  Movies / Events (leaf)
│   ├── 4903  Hobbies (leaf)
│   └── 4904  Vacations / Travel (leaf)
├── 5000  Financial Charges (placeholder)
│   ├── 5001  Bank Charges / Fees (leaf)
│   ├── 5002  Credit Card Interest (leaf)
│   ├── 5003  Loan Interest (leaf)
│   ├── 5004  Brokerage / Commission (leaf)
│   └── 5005  GST / TDS Paid (leaf)
├── 5100  Taxes (placeholder)
│   ├── 5101  Income Tax (leaf)
│   ├── 5102  Advance Tax (leaf)
│   └── 5103  Tax Filing Charges (leaf)
├── 5200  Gifts & Donations (placeholder)
│   ├── 5201  Gifts Given (leaf)
│   └── 5202  Charitable Donations (leaf)
├── 5300  EMI Payments (placeholder)
│   ├── 5301  Home Loan EMI (leaf)
│   ├── 5302  Vehicle Loan EMI (leaf)
│   └── 5303  Personal Loan EMI (leaf)
├── 5400  Children (placeholder)
│   ├── 5401  School Fees (leaf)
│   ├── 5402  Activities / Classes (leaf)
│   └── 5403  Childcare (leaf)
├── 5500  Household Help (placeholder)
│   ├── 5501  Maid / Cook (leaf)
│   ├── 5502  Driver (leaf)
│   └── 5503  Other Help (leaf)
└── 5900  Miscellaneous Expenses (leaf)

6000  Equity (EQUITY, placeholder, system)
├── 6001  Opening Balances (leaf, system)
└── 6002  Retained Earnings (leaf, system)
```

**Key Design Rules:**

The COA builder walks this tree depth-first and creates one row per node in the `accounts` table. System accounts (under Equity) are flagged `is_system=True` and cannot be renamed, deactivated, or deleted. Placeholder accounts cannot have transactions posted directly — only leaf accounts can. When a user adds a custom category under a placeholder, the system auto-generates the next code (e.g., under 4300 Food & Dining, next code is 4305). When deactivating, the system checks for existing transaction lines referencing the account; if any exist, deactivation is blocked with a clear error message.

**Service Methods:**

```python
class COASetupService:
    def __init__(self, account_repo: AccountRepository, event_bus: EventBus): ...

    def initialize_default_coa(self) -> COATreeResponse:
        """Create the full default COA. Idempotent — if already created, returns existing."""

    def get_tree(self) -> COATreeResponse:
        """Return the full hierarchical COA tree."""

    def get_account(self, account_id: int) -> AccountNodeResponse:
        """Return a single account node with its children."""

    def rename_account(self, account_id: int, new_name: str) -> AccountNodeResponse:
        """Rename a non-system account."""

    def add_custom_category(
        self, parent_id: int, name: str, description: str = ""
    ) -> AccountNodeResponse:
        """Add a new leaf category under a placeholder parent."""

    def deactivate_account(self, account_id: int) -> None:
        """Mark an account inactive. Fails if system account or has transactions."""

    def is_coa_ready(self) -> bool:
        """Check if the five root accounts exist."""
```

**Test Specifications:**

```
UNIT TESTS (test_coa_service.py):
├── test_initialize_creates_all_expected_accounts
├── test_initialize_creates_correct_parent_child_relationships
├── test_initialize_is_idempotent
├── test_initialize_sets_correct_account_types
├── test_initialize_sets_correct_normal_balances
├── test_initialize_marks_system_accounts
├── test_get_tree_returns_hierarchical_structure
├── test_get_tree_root_nodes_are_five_types
├── test_rename_account_success
├── test_rename_system_account_raises_error
├── test_rename_with_empty_name_raises_error
├── test_add_custom_category_under_placeholder
├── test_add_custom_category_auto_generates_code
├── test_add_custom_category_inherits_type_from_parent
├── test_add_custom_category_under_leaf_raises_error
├── test_deactivate_leaf_with_no_transactions_succeeds
├── test_deactivate_system_account_raises_error
├── test_deactivate_account_with_transactions_raises_error
├── test_deactivate_placeholder_with_active_children_raises_error
├── test_deactivate_placeholder_with_all_inactive_children_succeeds
├── test_is_coa_ready_false_when_empty
└── test_is_coa_ready_true_after_initialize
```

---

### 8.3 Institution Registration

**API Prefix:** `/api/v1/onboarding/institutions`

**Endpoints:**

| Method | Path | Description | Request Body | Response |
|--------|------|-------------|--------------|----------|
| POST | `/` | Register institution | `InstitutionCreateRequest` | `201: InstitutionResponse` |
| GET | `/` | List all institutions | — | `200: list[InstitutionResponse]` |
| GET | `/{id}` | Get institution | — | `200: InstitutionResponse` |
| PUT | `/{id}` | Update institution | `InstitutionUpdateRequest` | `200: InstitutionResponse` |
| GET | `/suggestions` | Get pre-seeded list | — | `200: list[InstitutionSuggestion]` |

**Schemas:**

```python
class InstitutionCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    institution_type: InstitutionType
    website: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, max_length=1000)

class InstitutionResponse(BaseModel):
    id: int
    name: str
    institution_type: InstitutionType
    website: str | None
    notes: str | None
    account_count: int        # number of accounts linked
    created_at: datetime
    updated_at: datetime

class InstitutionSuggestion(BaseModel):
    name: str
    institution_type: InstitutionType
```

**Pre-Seeded Indian Institutions (in `seed_data.py`):**

Banks: SBI, HDFC Bank, ICICI Bank, Axis Bank, Kotak Mahindra Bank, Bank of Baroda, Punjab National Bank, Canara Bank, IndusInd Bank, IDFC First Bank, Yes Bank, Federal Bank, RBL Bank, AU Small Finance Bank.

NBFCs: Bajaj Finance, HDFC Ltd, Muthoot Finance.

Brokerages: Zerodha, Groww, Upstox, Angel One, ICICI Direct, HDFC Securities, Kotak Securities, Motilal Oswal, 5paisa.

AMCs: SBI MF, HDFC MF, ICICI Prudential MF, Axis MF, Kotak MF, Nippon India MF, UTI MF, DSP MF, Mirae Asset MF.

Insurance: LIC, HDFC Life, ICICI Prudential Life, SBI Life, Max Life, Star Health, Niva Bupa.

Government: EPFO, National Pension System (NPS), Post Office (PPF/NSC).

---

### 8.4 Account Setup

**API Prefix:** `/api/v1/onboarding/accounts`

**Endpoints:**

| Method | Path | Description | Request Body | Response |
|--------|------|-------------|--------------|----------|
| POST | `/bank` | Add bank account | `BankAccountRequest` | `201: AccountResponse` |
| POST | `/credit-card` | Add credit card | `CreditCardRequest` | `201: AccountResponse` |
| POST | `/loan` | Add loan | `LoanRequest` | `201: AccountResponse` |
| POST | `/brokerage` | Add brokerage/demat | `BrokerageRequest` | `201: AccountResponse` |
| POST | `/fixed-deposit` | Add FD | `FixedDepositRequest` | `201: AccountResponse` |
| POST | `/recurring-deposit` | Add RD | `RecurringDepositRequest` | `201: AccountResponse` |
| POST | `/ppf` | Add PPF | `PPFRequest` | `201: AccountResponse` |
| POST | `/epf` | Add EPF | `EPFRequest` | `201: AccountResponse` |
| POST | `/nps` | Add NPS | `NPSRequest` | `201: AccountResponse` |
| POST | `/insurance` | Add insurance policy | `InsuranceRequest` | `201: AccountResponse` |
| POST | `/cash` | Add cash wallet | `CashAccountRequest` | `201: AccountResponse` |
| GET | `/` | List all accounts | `?type=ASSET` | `200: list[AccountResponse]` |
| GET | `/{id}` | Get account details | — | `200: AccountDetailResponse` |

**Common Response Schema:**

```python
class AccountResponse(BaseModel):
    id: int
    coa_account_id: int       # Link to COA tree node
    display_name: str
    account_type: AccountType
    account_subtype: AccountSubType
    institution_id: int | None
    institution_name: str | None
    account_code: str         # e.g., "1101"
    is_active: bool
    created_at: datetime

class AccountDetailResponse(AccountResponse):
    """Includes type-specific fields."""
    detail: dict              # Type-specific fields (see below)
```

**Type-Specific Request Schemas:**

```python
class BankAccountRequest(BaseModel):
    institution_id: int
    display_name: str = Field(..., min_length=1, max_length=200)
    account_number_masked: str = Field(
        ..., max_length=20,
        description="Last 4 digits or masked format like XXXX1234"
    )
    bank_account_type: BankAccountType = BankAccountType.SAVINGS
    ifsc_code: str | None = Field(
        default=None,
        pattern=r"^[A-Z]{4}0[A-Z0-9]{6}$"
    )
    branch: str | None = None

class CreditCardRequest(BaseModel):
    institution_id: int
    display_name: str = Field(..., min_length=1, max_length=200)
    last_four_digits: str = Field(..., pattern=r"^\d{4}$")
    credit_limit: float = Field(..., gt=0)
    billing_cycle_day: int = Field(..., ge=1, le=28)
    interest_rate_annual: float = Field(default=0.0, ge=0)

class LoanRequest(BaseModel):
    institution_id: int
    display_name: str = Field(..., min_length=1, max_length=200)
    loan_type: LoanType
    principal_amount: float = Field(..., gt=0)
    interest_rate_annual: float = Field(..., ge=0)
    tenure_months: int = Field(..., gt=0)
    emi_amount: float = Field(..., gt=0)
    start_date: date
    linked_asset_account_id: int | None = None   # For home/vehicle loans

class FixedDepositRequest(BaseModel):
    institution_id: int
    display_name: str = Field(..., min_length=1, max_length=200)
    principal_amount: float = Field(..., gt=0)
    interest_rate_annual: float = Field(..., gt=0)
    start_date: date
    maturity_date: date
    compounding_frequency: Frequency = Frequency.QUARTERLY
    auto_renew: bool = False

    @field_validator("maturity_date")
    @classmethod
    def maturity_after_start(cls, v, info):
        if "start_date" in info.data and v <= info.data["start_date"]:
            raise ValueError("Maturity date must be after start date")
        return v

class PPFRequest(BaseModel):
    institution_id: int
    display_name: str = Field(default="PPF Account")
    account_number: str | None = None
    opening_date: date

class EPFRequest(BaseModel):
    institution_id: int = None   # Defaults to EPFO
    display_name: str = Field(default="EPF Account")
    uan_number: str | None = None
    employer_name: str | None = None

class BrokerageRequest(BaseModel):
    institution_id: int
    display_name: str = Field(..., min_length=1, max_length=200)
    demat_id: str | None = None
    default_cost_basis_method: str = Field(
        default="FIFO",
        pattern=r"^(FIFO|AVERAGE)$"
    )

class CashAccountRequest(BaseModel):
    display_name: str = Field(default="Cash in Hand")
```

**Service Behavior — Common Flow:**

For every account creation call, the `AccountSetupService` follows this sequence:

First, validate the DTO (Pydantic handles field-level validation; service checks cross-field and referential rules like "institution must exist"). Second, determine the parent COA node by account subtype (e.g., `BankAccountType` → COA node `1100`). Third, generate the next available account code under that parent (query existing children, find the max code, increment). Fourth, create the COA leaf node via `AccountRepository.create_account()`. Fifth, create the type-specific detail record via the appropriate detail table (e.g., `bank_account_details`). Sixth, emit an `account.created` event with the account ID and type. Seventh, return the `AccountResponse`.

**Database Tables for Account Details:**

Each account type has a detail table linked to the main `accounts` table:

```sql
-- Main COA / Accounts table (shared across all types)
CREATE TABLE accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    account_type TEXT NOT NULL,      -- ASSET, LIABILITY, etc.
    account_subtype TEXT,            -- BANK, CREDIT_CARD, etc.
    normal_balance TEXT NOT NULL,    -- DEBIT or CREDIT
    parent_id INTEGER REFERENCES accounts(id),
    is_placeholder INTEGER NOT NULL DEFAULT 0,
    is_system INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    display_order INTEGER NOT NULL DEFAULT 0,
    institution_id INTEGER REFERENCES institutions(id),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Type-specific detail tables
CREATE TABLE bank_account_details (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL UNIQUE REFERENCES accounts(id),
    account_number_masked TEXT,
    bank_account_type TEXT NOT NULL,   -- SAVINGS, CURRENT, SALARY
    ifsc_code TEXT,
    branch TEXT
);

CREATE TABLE credit_card_details (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL UNIQUE REFERENCES accounts(id),
    last_four_digits TEXT NOT NULL,
    credit_limit REAL NOT NULL,
    billing_cycle_day INTEGER NOT NULL,
    interest_rate_annual REAL NOT NULL DEFAULT 0
);

CREATE TABLE loan_details (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL UNIQUE REFERENCES accounts(id),
    loan_type TEXT NOT NULL,
    principal_amount REAL NOT NULL,
    interest_rate_annual REAL NOT NULL,
    tenure_months INTEGER NOT NULL,
    emi_amount REAL NOT NULL,
    start_date TEXT NOT NULL,
    linked_asset_account_id INTEGER REFERENCES accounts(id)
);

CREATE TABLE fixed_deposit_details (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL UNIQUE REFERENCES accounts(id),
    principal_amount REAL NOT NULL,
    interest_rate_annual REAL NOT NULL,
    start_date TEXT NOT NULL,
    maturity_date TEXT NOT NULL,
    compounding_frequency TEXT NOT NULL,
    auto_renew INTEGER NOT NULL DEFAULT 0
);

-- Similar tables for: recurring_deposit_details, ppf_details,
-- epf_details, nps_details, insurance_details, brokerage_details
```

---

### 8.5 Opening Balances

**API Prefix:** `/api/v1/onboarding/opening-balances`

**Endpoints:**

| Method | Path | Description | Request Body | Response |
|--------|------|-------------|--------------|----------|
| POST | `/` | Set single opening balance | `OpeningBalanceRequest` | `201: OpeningBalanceResponse` |
| POST | `/bulk` | Set multiple opening balances | `BulkOpeningBalanceRequest` | `201: list[OpeningBalanceResponse]` |
| GET | `/` | List all opening balances | — | `200: list[OpeningBalanceResponse]` |
| GET | `/{account_id}` | Get OB for specific account | — | `200: OpeningBalanceResponse` or `404` |

**Schemas:**

```python
class OpeningBalanceRequest(BaseModel):
    account_id: int
    balance_amount: float = Field(
        ...,
        description="Positive value. System determines debit/credit based on account type."
    )
    balance_date: date = Field(
        ...,
        description="The date as of which this balance is true"
    )
    notes: str | None = None

class BulkOpeningBalanceRequest(BaseModel):
    entries: list[OpeningBalanceRequest] = Field(..., min_length=1)

class OpeningBalanceResponse(BaseModel):
    account_id: int
    account_name: str
    balance_amount: float
    balance_date: date
    transaction_id: int     # The generated double-entry transaction
    notes: str | None
```

**Double-Entry Logic:**

For every opening balance, the system generates a transaction with exactly two lines. The system identifies the "Opening Balances Equity" account (COA code `6001`, flagged `is_system=True`).

For asset accounts (normal balance = DEBIT): the asset account is debited and the equity account is credited.

For liability accounts (normal balance = CREDIT): the equity account is debited and the liability account is credited.

For a zero balance, no transaction is created, but the system records that the opening balance step was completed for that account.

If an opening balance already exists for an account (a transaction of type `OPENING_BALANCE` referencing that account), the system voids the existing transaction (marks it `status=VOIDED`) and creates a new one. This ensures the user can correct mistakes during onboarding without orphaned transactions.

**Transaction Schema Used:**

```sql
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_date TEXT NOT NULL,
    transaction_type TEXT NOT NULL,   -- OPENING_BALANCE, STANDARD, TRANSFER, etc.
    description TEXT,
    reference TEXT,
    status TEXT NOT NULL DEFAULT 'POSTED',   -- POSTED, VOIDED
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE transaction_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id INTEGER NOT NULL REFERENCES transactions(id),
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    debit_amount REAL NOT NULL DEFAULT 0,
    credit_amount REAL NOT NULL DEFAULT 0,
    line_description TEXT,
    CONSTRAINT chk_single_side CHECK (
        (debit_amount > 0 AND credit_amount = 0) OR
        (credit_amount > 0 AND debit_amount = 0) OR
        (debit_amount = 0 AND credit_amount = 0)
    )
);
```

**Invariant enforced by service:** For every transaction, `SUM(debit_amount) = SUM(credit_amount)`. This is checked before persistence and any violation raises a `BusinessRuleError`.

---

### 8.6 Goal Planner

**API Prefix:** `/api/v1/onboarding/goals`

**Endpoints:**

| Method | Path | Description | Request Body | Response |
|--------|------|-------------|--------------|----------|
| POST | `/` | Create goal | `GoalCreateRequest` | `201: GoalResponse` |
| GET | `/` | List all goals | — | `200: list[GoalResponse]` |
| GET | `/{id}` | Get goal detail | — | `200: GoalDetailResponse` |
| PUT | `/{id}` | Update goal | `GoalUpdateRequest` | `200: GoalResponse` |
| POST | `/{id}/accounts` | Link accounts to goal | `GoalAccountLinkRequest` | `200: GoalResponse` |
| POST | `/{id}/milestones` | Add milestone | `MilestoneCreateRequest` | `201: MilestoneResponse` |
| GET | `/{id}/projection` | Calculate monthly contribution | — | `200: GoalProjectionResponse` |
| GET | `/summary` | Aggregate summary | — | `200: GoalSummaryResponse` |

**Schemas:**

```python
class GoalCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    goal_type: GoalType
    target_amount: float = Field(..., gt=0)
    target_date: date | None = None
    start_date: date = Field(default_factory=date.today)
    priority: GoalPriority = GoalPriority.MEDIUM
    expected_annual_return_rate: float = Field(
        default=0.0, ge=0, le=100,
        description="Expected annual return as percentage, e.g. 12.0 for 12%"
    )
    notes: str | None = None

    @field_validator("target_date")
    @classmethod
    def target_after_start(cls, v, info):
        if v and "start_date" in info.data and v <= info.data["start_date"]:
            raise ValueError("Target date must be after start date")
        return v

class GoalAccountLinkRequest(BaseModel):
    account_ids: list[int] = Field(..., min_length=1)

class MilestoneCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    target_amount: float = Field(..., gt=0)
    target_date: date | None = None

class GoalProjectionResponse(BaseModel):
    monthly_contribution_required: float
    months_remaining: int | None
    projected_corpus_at_target: float
    assumes_return_rate: float
```

**Contribution Calculation:**

When `expected_annual_return_rate` is 0, the formula is:

$$
\text{monthly} = \frac{\text{target} - \text{current}}{\text{months\_remaining}}
$$

When the return rate is provided (say \(r\) annual), the monthly rate is \(r_m = r / 12 / 100\). Using the future value of annuity formula solved for PMT:

$$
\text{PMT} = \frac{(\text{target} - \text{current} \times (1 + r_m)^n) \times r_m}{(1 + r_m)^n - 1}
$$

where \(n\) = months remaining. If `target_date` is not set, the projection returns `null` for `months_remaining` and `monthly_contribution_required`.

---

### 8.7 Budget Setup

**API Prefix:** `/api/v1/onboarding/budget`

**Endpoints:**

| Method | Path | Description | Request Body | Response |
|--------|------|-------------|--------------|----------|
| POST | `/` | Create budget | `BudgetCreateRequest` | `201: BudgetResponse` |
| GET | `/` | List budgets | — | `200: list[BudgetResponse]` |
| GET | `/{id}` | Get budget detail | — | `200: BudgetDetailResponse` |
| PUT | `/{id}` | Update budget | `BudgetUpdateRequest` | `200: BudgetResponse` |
| GET | `/template` | Generate budget template from COA | — | `200: BudgetTemplateResponse` |

**Schemas:**

```python
class BudgetLineItem(BaseModel):
    account_id: int
    budgeted_amount: float = Field(..., ge=0)
    notes: str | None = None

class BudgetCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    period_type: str = Field(..., pattern=r"^(MONTHLY|YEARLY)$")
    start_date: date
    end_date: date
    line_items: list[BudgetLineItem] = Field(..., min_length=1)

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, v, info):
        if "start_date" in info.data and v <= info.data["start_date"]:
            raise ValueError("End date must be after start date")
        return v

    @field_validator("line_items")
    @classmethod
    def no_duplicate_accounts(cls, v):
        ids = [item.account_id for item in v]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate account IDs in line items")
        return v

class BudgetResponse(BaseModel):
    id: int
    name: str
    period_type: str
    start_date: date
    end_date: date
    total_budgeted: float
    line_item_count: int
    created_at: datetime

class BudgetTemplateResponse(BaseModel):
    """Pre-populated template with all expense categories."""
    suggested_line_items: list[BudgetTemplateLineItem]

class BudgetTemplateLineItem(BaseModel):
    account_id: int
    account_name: str
    account_code: str
    parent_category: str       # e.g., "Food & Dining"
    suggested_amount: float    # 0.0 — user fills in
```

**Validation Rules:**

The service validates that every `account_id` in the line items is either an expense or income category (type EXPENSE or INCOME) and is a leaf account (not a placeholder). Passing an asset or liability account raises a `ValidationError`. The template generator queries all active expense leaf categories from the COA and returns them pre-populated with zero amounts.

---

### 8.8 Recurring Transaction Templates

**API Prefix:** `/api/v1/onboarding/recurring`

**Endpoints:**

| Method | Path | Description | Request Body | Response |
|--------|------|-------------|--------------|----------|
| POST | `/` | Create template | `RecurringCreateRequest` | `201: RecurringResponse` |
| POST | `/sip` | Create SIP (convenience) | `SIPSetupRequest` | `201: RecurringResponse` |
| POST | `/emi` | Create EMI (convenience) | `EMISetupRequest` | `201: RecurringResponse` |
| GET | `/` | List all templates | — | `200: list[RecurringResponse]` |
| GET | `/{id}` | Get template detail | — | `200: RecurringResponse` |
| PUT | `/{id}` | Update template | `RecurringUpdateRequest` | `200: RecurringResponse` |
| DELETE | `/{id}` | Delete template | — | `204` |

**Schemas:**

```python
class RecurringCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    recurring_type: RecurringType
    frequency: Frequency
    amount: float = Field(..., gt=0)
    from_account_id: int
    to_account_id: int
    start_date: date
    end_date: date | None = None
    day_of_occurrence: int = Field(
        ..., ge=1, le=28,
        description="Day of month (or period) when this recurs"
    )
    description_template: str = Field(
        default="",
        description="Template for transaction description, e.g. 'SIP - {fund_name}'"
    )
    auto_post: bool = Field(
        default=False,
        description="If true, system auto-creates transactions. If false, just reminds."
    )

class SIPSetupRequest(BaseModel):
    fund_name: str = Field(..., min_length=1)
    sip_amount: float = Field(..., gt=0)
    sip_day: int = Field(..., ge=1, le=28)
    from_account_id: int          # Bank account
    to_account_id: int            # Brokerage / MF account
    start_date: date
    end_date: date | None = None

class EMISetupRequest(BaseModel):
    loan_account_id: int          # The loan liability account
    emi_amount: float = Field(..., gt=0)
    debit_account_id: int         # Bank account EMI is debited from
    emi_day: int = Field(..., ge=1, le=28)
    start_date: date
    end_date: date | None = None

class RecurringResponse(BaseModel):
    id: int
    name: str
    recurring_type: RecurringType
    frequency: Frequency
    amount: float
    from_account_id: int
    from_account_name: str
    to_account_id: int
    to_account_name: str
    start_date: date
    end_date: date | None
    day_of_occurrence: int
    next_occurrence_date: date
    auto_post: bool
    created_at: datetime
```

**Next Occurrence Calculation:**

When a template is created, the service computes `next_occurrence_date` as the nearest future date matching the `day_of_occurrence` and `frequency`. For example, if today is March 14 and `sip_day` is 10 and frequency is MONTHLY, the next occurrence is April 10. This field is recalculated whenever a recurring transaction is actually posted (handled by the Transaction module, not Onboarding).

---

### 8.9 Net Worth

**API Prefix:** `/api/v1/onboarding/networth`

**Endpoints:**

| Method | Path | Description | Request Body | Response |
|--------|------|-------------|--------------|----------|
| POST | `/compute` | Compute and save snapshot | `NetWorthComputeRequest` | `201: NetWorthSnapshotResponse` |
| GET | `/latest` | Get most recent snapshot | — | `200: NetWorthSnapshotResponse` |

**Schemas:**

```python
class NetWorthComputeRequest(BaseModel):
    as_of_date: date = Field(default_factory=date.today)

class NetWorthCategoryBreakdown(BaseModel):
    category: str
    total: float
    accounts: list[NetWorthAccountLine]

class NetWorthAccountLine(BaseModel):
    account_id: int
    account_name: str
    balance: float

class NetWorthSnapshotResponse(BaseModel):
    as_of_date: date
    total_assets: float
    total_liabilities: float
    net_worth: float
    asset_breakdown: list[NetWorthCategoryBreakdown]
    liability_breakdown: list[NetWorthCategoryBreakdown]
    snapshot_id: int
    computed_at: datetime
```

**Computation Logic:**

The service iterates over all active leaf accounts. For each, it computes the balance by summing all transaction lines (debit - credit for DEBIT-normal accounts, credit - debit for CREDIT-normal accounts) as of the `as_of_date`. It groups assets into categories: Liquid (bank + cash), Deposits (FD + RD + PPF), Retirement (EPF + NPS), Investments (brokerage + MF + gold), Property, Insurance (surrender value), Other Assets. It groups liabilities into: Credit Cards, Loans (by loan type), Other Liabilities.

The snapshot is persisted in a `networth_snapshots` table:

```sql
CREATE TABLE networth_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    as_of_date TEXT NOT NULL,
    total_assets REAL NOT NULL,
    total_liabilities REAL NOT NULL,
    net_worth REAL NOT NULL,
    breakdown_json TEXT NOT NULL,    -- Full breakdown as JSON
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

---

### 8.10 Onboarding Orchestrator

**API Prefix:** `/api/v1/onboarding`

**Endpoints:**

| Method | Path | Description | Request Body | Response |
|--------|------|-------------|--------------|----------|
| GET | `/status` | Get onboarding state | — | `200: OnboardingStatusResponse` |
| POST | `/steps/{step}/start` | Mark step as in-progress | — | `200: OnboardingStatusResponse` |
| POST | `/steps/{step}/complete` | Mark step as completed | — | `200: OnboardingStatusResponse` |
| POST | `/steps/{step}/skip` | Skip an optional step | — | `200: OnboardingStatusResponse` |
| POST | `/complete` | Finalize onboarding | — | `200: OnboardingStatusResponse` |
| GET | `/next-step` | Get the next actionable step | — | `200: {"step": str, "status": str}` |

**Schemas:**

```python
class StepStatusEntry(BaseModel):
    step: OnboardingStep
    status: OnboardingStepStatus
    is_mandatory: bool
    started_at: datetime | None
    completed_at: datetime | None

class OnboardingStatusResponse(BaseModel):
    is_complete: bool
    progress_percentage: float     # 0.0 to 100.0
    current_step: OnboardingStep | None
    steps: list[StepStatusEntry]
```

**Step Rules:**

| Step | Mandatory | Can Skip | Prerequisites |
|------|-----------|----------|---------------|
| PROFILE | Yes | No | None |
| COA_SETUP | Yes | No | PROFILE |
| INSTITUTION_SETUP | No | Yes | COA_SETUP |
| ACCOUNT_SETUP | Yes | No | COA_SETUP |
| OPENING_BALANCES | No | Yes | ACCOUNT_SETUP |
| GOAL_PLANNING | No | Yes | ACCOUNT_SETUP |
| BUDGET_SETUP | No | Yes | COA_SETUP |
| RECURRING_SETUP | No | Yes | ACCOUNT_SETUP |
| NETWORTH_REVIEW | No | Yes | OPENING_BALANCES |

The orchestrator stores its state as a JSON blob in the settings repository under key `onboarding.state`. On first access, it initializes all steps to PENDING. Progress percentage is calculated as `(completed + skipped) / total * 100`.

---

## 9. Repository Contracts

Every repository is defined as a `Protocol`. Below are the key repository interfaces used by the onboarding module.

```python
class AccountRepository(Protocol):
    def create(self, account: AccountCreateDTO) -> AccountDTO: ...
    def get_by_id(self, id: int) -> AccountDTO | None: ...
    def get_by_code(self, code: str) -> AccountDTO | None: ...
    def get_children(self, parent_id: int) -> list[AccountDTO]: ...
    def get_tree(self) -> list[AccountTreeNode]: ...
    def get_leaves_by_type(self, account_type: AccountType) -> list[AccountDTO]: ...
    def get_leaves_by_subtype(self, subtype: AccountSubType) -> list[AccountDTO]: ...
    def update(self, id: int, updates: dict) -> AccountDTO: ...
    def has_transactions(self, id: int) -> bool: ...
    def get_balance(self, id: int, as_of: date) -> float: ...
    def get_max_code_under_parent(self, parent_id: int) -> str | None: ...
    def count_by_institution(self, institution_id: int) -> int: ...

class InstitutionRepository(Protocol):
    def create(self, institution: InstitutionCreateDTO) -> InstitutionDTO: ...
    def get_by_id(self, id: int) -> InstitutionDTO | None: ...
    def get_by_name(self, name: str) -> InstitutionDTO | None: ...
    def list_all(self) -> list[InstitutionDTO]: ...
    def update(self, id: int, updates: dict) -> InstitutionDTO: ...

class TransactionRepository(Protocol):
    def create(self, transaction: TransactionCreateDTO) -> TransactionDTO: ...
    def get_by_id(self, id: int) -> TransactionDTO | None: ...
    def get_by_type_and_account(
        self, tx_type: str, account_id: int
    ) -> list[TransactionDTO]: ...
    def void_transaction(self, id: int) -> None: ...

class GoalRepository(Protocol):
    def create(self, goal: GoalCreateDTO) -> GoalDTO: ...
    def get_by_id(self, id: int) -> GoalDTO | None: ...
    def list_all(self, status: GoalStatus | None = None) -> list[GoalDTO]: ...
    def update(self, id: int, updates: dict) -> GoalDTO: ...
    def link_accounts(self, goal_id: int, account_ids: list[int]) -> None: ...
    def get_linked_accounts(self, goal_id: int) -> list[int]: ...
    def create_milestone(
        self, goal_id: int, milestone: MilestoneCreateDTO
    ) -> MilestoneDTO: ...
    def get_milestones(self, goal_id: int) -> list[MilestoneDTO]: ...

class BudgetRepository(Protocol):
    def create(self, budget: BudgetCreateDTO) -> BudgetDTO: ...
    def get_by_id(self, id: int) -> BudgetDTO | None: ...
    def list_all(self) -> list[BudgetDTO]: ...
    def update(self, id: int, updates: dict) -> BudgetDTO: ...

class RecurringTemplateRepository(Protocol):
    def create(self, template: RecurringCreateDTO) -> RecurringDTO: ...
    def get_by_id(self, id: int) -> RecurringDTO | None: ...
    def list_all(self) -> list[RecurringDTO]: ...
    def update(self, id: int, updates: dict) -> RecurringDTO: ...
    def delete(self, id: int) -> None: ...

class SettingsRepository(Protocol):
    def get(self, key: str) -> str | None: ...
    def set(self, key: str, value: str) -> None: ...
    def get_bulk(self, prefix: str) -> dict[str, str]: ...
    def delete(self, key: str) -> None: ...
    def exists(self, key: str) -> bool: ...

class NetWorthSnapshotRepository(Protocol):
    def save(self, snapshot: NetWorthSnapshotCreateDTO) -> NetWorthSnapshotDTO: ...
    def get_latest(self) -> NetWorthSnapshotDTO | None: ...
    def get_by_date(self, as_of: date) -> NetWorthSnapshotDTO | None: ...
```

---

## 10. Testing Strategy

### 10.1 Test Pyramid

```
         ╱╲
        ╱ E2E ╲           2-3 tests: Full onboarding flow via API
       ╱────────╲
      ╱Integration╲       10-15 tests: API endpoints with real SQLite
     ╱──────────────╲
    ╱   Unit Tests    ╲    80+ tests: Service logic with in-memory stubs
   ╱────────────────────╲
```

### 10.2 TDD Workflow

Every feature follows this cycle: write a failing test → write the minimum code to pass → refactor → commit. Test files are created before implementation files.

### 10.3 Test Fixtures

```python
# tests/conftest.py — shared across all tests

@pytest.fixture
def event_bus():
    return EventBus()

@pytest.fixture
def settings_repo():
    return InMemorySettingsRepository()

@pytest.fixture
def account_repo():
    return InMemoryAccountRepository()

@pytest.fixture
def institution_repo():
    return InMemoryInstitutionRepository()

@pytest.fixture
def transaction_repo():
    return InMemoryTransactionRepository()

# Composite fixtures for services
@pytest.fixture
def profile_service(settings_repo, event_bus):
    return ProfileService(settings_repo, event_bus)

@pytest.fixture
def coa_service(account_repo, event_bus):
    return COASetupService(account_repo, event_bus)

# Integration test fixtures
@pytest.fixture
def test_engine(tmp_path):
    """Creates a fresh SQLAlchemy engine with SQLite for each test."""
    from sqlalchemy import create_engine
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    metadata.create_all(engine)  # Create all tables from SQLAlchemy Table definitions
    yield engine
    engine.dispose()

@pytest.fixture
def api_client(test_engine):
    """FastAPI test client with real SQLAlchemy-backed database."""
    app = create_app(engine=test_engine)
    with TestClient(app) as client:
        yield client
```

### 10.4 Test Naming Convention

```
test_{method_name}_{scenario}_{expected_result}
```

Examples: `test_setup_profile_with_valid_data_returns_success`, `test_rename_system_account_raises_system_account_error`, `test_set_opening_balance_for_asset_debits_asset_credits_equity`.

### 10.5 Integration Test: Full Onboarding Flow

```python
def test_complete_onboarding_flow(api_client):
    """End-to-end test covering every onboarding step via the API."""

    # Step 1: Create profile
    resp = api_client.post("/api/v1/onboarding/profile", json={
        "display_name": "Hari Kumar",
        "base_currency": "INR",
        "financial_year_start_month": 4,
        "tax_regime": "NEW"
    })
    assert resp.status_code == 201

    # Step 2: Initialize COA
    resp = api_client.post("/api/v1/onboarding/coa/initialize")
    assert resp.status_code == 201
    tree = resp.json()
    assert len(tree["root_nodes"]) == 5

    # Step 3: Register institution
    resp = api_client.post("/api/v1/onboarding/institutions", json={
        "name": "HDFC Bank",
        "institution_type": "BANK"
    })
    assert resp.status_code == 201
    hdfc_id = resp.json()["id"]

    # Step 4: Add bank account
    resp = api_client.post("/api/v1/onboarding/accounts/bank", json={
        "institution_id": hdfc_id,
        "display_name": "HDFC Savings",
        "account_number_masked": "XXXX5678",
        "bank_account_type": "SAVINGS"
    })
    assert resp.status_code == 201
    savings_id = resp.json()["id"]

    # Step 5: Set opening balance
    resp = api_client.post("/api/v1/onboarding/opening-balances", json={
        "account_id": savings_id,
        "balance_amount": 150000.00,
        "balance_date": "2026-03-01"
    })
    assert resp.status_code == 201
    assert resp.json()["transaction_id"] is not None

    # Step 6: Create goal
    resp = api_client.post("/api/v1/onboarding/goals", json={
        "name": "Emergency Fund",
        "goal_type": "EMERGENCY_FUND",
        "target_amount": 500000.00,
        "target_date": "2027-03-31",
        "priority": "HIGH"
    })
    assert resp.status_code == 201

    # Step 7: Compute net worth
    resp = api_client.post("/api/v1/onboarding/networth/compute", json={
        "as_of_date": "2026-03-14"
    })
    assert resp.status_code == 201
    nw = resp.json()
    assert nw["total_assets"] == 150000.00
    assert nw["total_liabilities"] == 0.0
    assert nw["net_worth"] == 150000.00

    # Final: Check onboarding status
    resp = api_client.get("/api/v1/onboarding/status")
    assert resp.status_code == 200
```

---

## 11. CLI Client

The CLI is built with Typer and serves as a demonstrable interface for testing before any graphical UI is developed. It calls the same FastAPI endpoints via `httpx`.

**Command Structure:**

```
pfms-cli onboarding profile setup --name "Hari" --currency INR --regime NEW
pfms-cli onboarding profile show
pfms-cli onboarding coa init
pfms-cli onboarding coa tree
pfms-cli onboarding coa rename --id 4301 --name "Kirana / Groceries"
pfms-cli onboarding institution add --name "HDFC Bank" --type BANK
pfms-cli onboarding institution list
pfms-cli onboarding account add-bank --institution 1 --name "HDFC Savings" --masked "XXXX5678"
pfms-cli onboarding account add-cc --institution 1 --name "HDFC Regalia" --last-four 1234 --limit 300000
pfms-cli onboarding account list
pfms-cli onboarding opening-balance set --account 5 --amount 150000 --date 2026-03-01
pfms-cli onboarding opening-balance list
pfms-cli onboarding goal create --name "Emergency Fund" --type EMERGENCY_FUND --target 500000
pfms-cli onboarding goal list
pfms-cli onboarding budget template
pfms-cli onboarding budget create --name "March 2026" --file budget_march.json
pfms-cli onboarding recurring add-sip --fund "Mirae Asset Large Cap" --amount 5000 --day 10 --from-account 5 --to-account 8
pfms-cli onboarding recurring list
pfms-cli onboarding networth compute
pfms-cli onboarding networth show
pfms-cli onboarding status
pfms-cli onboarding complete
```

**CLI Output Formatting:**

The CLI uses `rich` library tables for tabular data and tree renderers for the COA tree. Net worth is displayed as a formatted summary with category breakdowns. All monetary values are formatted according to the user's `number_format` setting (Indian: ₹1,50,000.00).

---

## 12. Database Schema — Complete for Onboarding

```sql
-- Settings (key-value store for profile and orchestrator state)
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Institutions
CREATE TABLE institutions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    institution_type TEXT NOT NULL,
    website TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Accounts (COA tree + leaf accounts)
CREATE TABLE accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    account_type TEXT NOT NULL,
    account_subtype TEXT,
    normal_balance TEXT NOT NULL,
    parent_id INTEGER REFERENCES accounts(id),
    is_placeholder INTEGER NOT NULL DEFAULT 0,
    is_system INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    display_order INTEGER NOT NULL DEFAULT 0,
    institution_id INTEGER REFERENCES institutions(id),
    description TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Type-specific detail tables (as defined in Section 8.4)
-- bank_account_details, credit_card_details, loan_details,
-- fixed_deposit_details, recurring_deposit_details,
-- ppf_details, epf_details, nps_details, insurance_details,
-- brokerage_details

-- Transactions and lines (as defined in Section 8.5)
-- transactions, transaction_lines

-- Goals
CREATE TABLE goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    goal_type TEXT NOT NULL,
    target_amount REAL NOT NULL,
    current_amount REAL NOT NULL DEFAULT 0,
    target_date TEXT,
    start_date TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'MEDIUM',
    expected_annual_return_rate REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE goal_account_mappings (
    goal_id INTEGER NOT NULL REFERENCES goals(id),
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    PRIMARY KEY (goal_id, account_id)
);

CREATE TABLE goal_milestones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    goal_id INTEGER NOT NULL REFERENCES goals(id),
    name TEXT NOT NULL,
    target_amount REAL NOT NULL,
    target_date TEXT,
    is_achieved INTEGER NOT NULL DEFAULT 0,
    achieved_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Budgets
CREATE TABLE budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    period_type TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE budget_line_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    budget_id INTEGER NOT NULL REFERENCES budgets(id),
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    budgeted_amount REAL NOT NULL,
    notes TEXT,
    UNIQUE(budget_id, account_id)
);

-- Recurring Templates
CREATE TABLE recurring_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    recurring_type TEXT NOT NULL,
    frequency TEXT NOT NULL,
    amount REAL NOT NULL,
    from_account_id INTEGER NOT NULL REFERENCES accounts(id),
    to_account_id INTEGER NOT NULL REFERENCES accounts(id),
    start_date TEXT NOT NULL,
    end_date TEXT,
    day_of_occurrence INTEGER NOT NULL,
    description_template TEXT,
    auto_post INTEGER NOT NULL DEFAULT 0,
    next_occurrence_date TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Net Worth Snapshots
CREATE TABLE networth_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    as_of_date TEXT NOT NULL,
    total_assets REAL NOT NULL,
    total_liabilities REAL NOT NULL,
    net_worth REAL NOT NULL,
    breakdown_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Indexes
CREATE INDEX idx_accounts_parent ON accounts(parent_id);
CREATE INDEX idx_accounts_type ON accounts(account_type);
CREATE INDEX idx_accounts_subtype ON accounts(account_subtype);
CREATE INDEX idx_accounts_institution ON accounts(institution_id);
CREATE INDEX idx_transaction_lines_account ON transaction_lines(account_id);
CREATE INDEX idx_transaction_lines_transaction ON transaction_lines(transaction_id);
CREATE INDEX idx_transactions_type ON transactions(transaction_type);
CREATE INDEX idx_transactions_date ON transactions(transaction_date);
CREATE INDEX idx_goals_status ON goals(status);
CREATE INDEX idx_recurring_next ON recurring_templates(next_occurrence_date);
CREATE INDEX idx_networth_date ON networth_snapshots(as_of_date);
```

---

## 13. Build Sequence and Milestones

### Phase 1 — Foundation (Week 1)

| ID | Task | Deliverable | Test Count |
|----|------|-------------|------------|
| ON-PROF-1 | Profile DTOs + validation | `profile/schemas.py` | 6 |
| ON-PROF-2 | Profile service (save/get) | `profile/service.py` | 5 |
| ON-PROF-3 | Profile completion check | Added to service | 3 |
| ON-PROF-API | Profile router | `profile/router.py` | 5 integration |
| ON-COA-1 | Default COA tree data | `coa/default_tree.py` | 4 |
| ON-COA-2 | COA builder (persist) | `coa/service.py` | 4 |
| ON-COA-3 | COA tree retrieval | Added to service | 3 |

**Milestone 1 Checkpoint:** User can create a profile and initialize a COA via Swagger UI. `make test` passes with 30+ tests green.

### Phase 2 — COA Customization + Institutions + First Accounts (Week 2)

| ID | Task | Deliverable | Test Count |
|----|------|-------------|------------|
| ON-COA-4 | Rename account | `coa/service.py` | 3 |
| ON-COA-5 | Add custom category | `coa/service.py` | 4 |
| ON-COA-6 | Deactivate category | `coa/service.py` | 5 |
| ON-COA-7 | COA completion check | `coa/service.py` | 2 |
| ON-COA-API | COA router (all endpoints) | `coa/router.py` | 6 integration |
| ON-INST-1 | Institution DTOs | `institution/schemas.py` | 3 |
| ON-INST-2 | Institution CRUD service | `institution/service.py` | 5 |
| ON-INST-API | Institution router | `institution/router.py` | 5 integration |
| ON-ACCT-1 | Account base logic | `account/service.py` | 3 |
| ON-ACCT-2 | Bank account setup | `account/account_types.py` | 5 |

**Milestone 2 Checkpoint:** User can customize COA, register institutions, and add bank accounts via Swagger. Integration test swaps in real SQLite repos and passes.

### Phase 3 — All Accounts + Opening Balances (Week 3)

| ID | Task | Deliverable | Test Count |
|----|------|-------------|------------|
| ON-ACCT-3 to 8 | Remaining account types | `account/account_types.py` | 18 |
| ON-ACCT-API | Account router | `account/router.py` | 8 integration |
| ON-OB-1 | Opening balance DTOs | `opening_balance/schemas.py` | 3 |
| ON-OB-2 | OB transaction generator | `opening_balance/service.py` | 5 |
| ON-OB-3 | Duplicate prevention | `opening_balance/service.py` | 3 |
| ON-OB-4 | Bulk entry | `opening_balance/service.py` | 3 |
| ON-OB-API | Opening balance router | `opening_balance/router.py` | 4 integration |

**Milestone 3 Checkpoint:** All account types can be created and opening balances set. Double-entry transactions verified via SQL query. Full account-to-balance flow works.

### Phase 4 — Goals, Budget, Recurring, Net Worth, Orchestrator (Week 4)

| ID | Task | Deliverable | Test Count |
|----|------|-------------|------------|
| ON-GOAL-1 to 6 | Goal planner (all) | `goal/` | 15 |
| ON-BUD-1 to 3 | Budget setup (all) | `budget/` | 8 |
| ON-REC-1 to 5 | Recurring templates (all) | `recurring/` | 10 |
| ON-NW-1 to 3 | Net worth (all) | `networth/` | 6 |
| ON-ORCH-1 to 5 | Orchestrator (all) | `orchestrator/` | 10 |
| CLI | CLI client | `cli/` | manual verification |
| E2E | Full onboarding e2e test | `tests/e2e/` | 1 comprehensive |

**Milestone 4 Checkpoint:** Complete onboarding flow works end-to-end via API and CLI. All 150+ tests pass. Coverage report ≥ 90%.

---

## 14. Quality Gates

Before any sub-module is considered complete, it must pass all of the following:

**Gate 1 — Code Quality:** `ruff check` reports zero issues. `mypy --strict` reports zero errors on the sub-module's files.

**Gate 2 — Unit Tests:** All unit tests pass. Coverage for the sub-module's service layer is ≥ 95%.

**Gate 3 — Integration Tests:** API endpoints tested with `TestClient` against a real (temp) SQLite database. All integration tests pass.

**Gate 4 — Contract Verification:** The in-memory repository stubs and SQLite implementations produce identical results for the same sequence of operations.

**Gate 5 — Swagger Validation:** All endpoints are accessible in Swagger UI. Request/response schemas render correctly. Manual smoke test of each endpoint via Swagger succeeds.

---

## 15. Open Questions and Future Considerations

**OQ-1: Multi-Currency Support.** The current design uses a single base currency per profile. Multi-currency accounts (e.g., a USD brokerage account) will need exchange rate tracking and currency conversion logic. This is deferred to Phase 2 but the `Currency` field on the profile is designed to be extensible.

**OQ-2: Data Import.** Many users will want to import bank statements (CSV/PDF) or existing data from other apps during onboarding. An import sub-module with format-specific parsers could be added as Step 10 in the orchestrator without disrupting the existing flow.

**OQ-3: Tax Section 80C Mapping.** Several account types (PPF, ELSS, NPS, insurance premiums) are eligible for tax deductions under Section 80C/80CCC/80CCD. Tagging these during onboarding for tax reporting is a natural enhancement.

**OQ-4: Account Aggregator Integration.** India's Account Aggregator framework (RBI regulated) could eventually allow automatic account discovery and balance fetching. The institution and account models are structured to accommodate this.

---

This document is the binding specification for all onboarding implementation work. Any deviation requires a documented decision with rationale added to Section 15.

Shall I proceed with the same level of detail for the Transaction Management module, or would you like to refine anything here first?