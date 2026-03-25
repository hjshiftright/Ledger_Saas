

<think>The user wants me to create a work distribution plan for three developers (Hari, Raj, Kalyan) following spec-driven/contract-driven development in Python. They need to work independently but integrate later through well-defined contracts (interfaces/APIs).

Let me think about this carefully:

1. **Hari** - Onboarding experience and sub-modules
2. **Raj** - Transaction management and sub-modules
3. **Kalyan** - Database and Reports

Key challenges:
- They need to work independently
- They need contracts (interfaces) between their modules
- Python-based tech stack
- Must be integrable later


- For independent work, I'll establish a shared contracts layer using Pydantic models and abstract base classes, then have each developer work against those interfaces while building their own modules in parallel. Raj handles transaction operations—CRUD services, double-entry validation, recurring transactions, imports, and reconciliation—plus investment transactions. I'm reconsidering where goals and budgets fit: goals could belong to Hari's onboarding setup or Raj's ongoing management, while budgets seem more aligned with Raj since they're transaction-adjacent. Let me map this back to the original module design to clarify the boundaries. institution & account registration, opening balances, initial goal and budget setup, default chart of accounts customization, and recurring transaction templates. Raj handles manual transaction entry, editing through reversals, the recurring transaction engine, imports and reconciliation, investment and derivatives transactions, goal and budget tracking, plus void and reversal handling. Kalyan owns all the database models, repository layer, monthly snapshots, net worth calculations, all report types including tax reports, dashboard aggregation, and data exports.

Now I'm mapping out the contracts layer—shared interfaces, data transfer objects, and events—along with the tech stack using Python 3.11+, SQLAlchemy 2.0 with async support, Pydantic v2 for validation, Protocol classes for interfaces, SQLite storage, Alembic migrations, and pytest for testing. I'm structuring the project with a contracts directory that everyone contributes to, containing enums, DTOs for accounts, transactions, goals, budgets and reports...

Defining project structure... Now I'm mapping out the reports module structure with generators and snapshots, then moving to the integration point. I need to create a comprehensive plan covering the architecture, shared contracts, each developer's specific deliverables, interface contracts between modules, how we'll handle mocking for parallel development, the integration strategy, and a phased timeline.</think># Spec-Driven Development Plan — Work Distribution & Integration Contracts

## 1. Architecture Philosophy

The application follows a **layered hexagonal architecture** where each developer owns a vertical slice of functionality but all three agree on a shared horizontal contracts layer before writing any implementation code. The contracts layer is the single source of truth — it defines data shapes, service interfaces, repository protocols, and event signatures. Each developer codes against these contracts, uses mocks/stubs of the other modules during development, and integration becomes a matter of wiring real implementations in place of stubs.

```
┌──────────────────────────────────────────────────────────────────────┐
│                        APPLICATION SHELL                             │
│                     (Integration & Wiring)                           │
├──────────────┬──────────────────────┬────────────────────────────────┤
│    HARI      │        RAJ           │          KALYAN                │
│  Onboarding  │   Transactions       │    Database + Reports          │
│  Module      │   Module             │    Module                      │
├──────────────┴──────────────────────┴────────────────────────────────┤
│                     SHARED CONTRACTS LAYER                           │
│         (DTOs, Protocols, Enums, Events, Exceptions)                 │
├──────────────────────────────────────────────────────────────────────┤
│                     SQLite + SQLAlchemy                               │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 2. Tech Stack Decisions (Agreed Upfront)

| Concern | Choice | Rationale |
|---|---|---|
| Language | Python 3.11+ | Team preference |
| Data Access | SQLAlchemy Core 2.0 (no ORM layer) | SQL expression builder; database-portable queries with full visibility |
| Data Validation / DTOs | Pydantic v2 | Fast, strict, serialization built-in |
| Interface Contracts | `typing.Protocol` | Structural subtyping — no inheritance coupling |
| Migrations | Alembic | Standard SQLAlchemy companion |
| Testing | pytest + pytest-mock | Industry standard |
| Database | SQLite 3 (local file) | Local-first MVP |
| Dependency Injection | `dependency-injector` or manual wiring | Swap stubs for real implementations |
| UI Framework | To be decided separately | Decoupled from backend via service layer |
| Build/Package | Poetry or PDM | Modern Python dependency management |

---

## 3. Project Structure

```
finapp/
│
├── contracts/                      # SHARED — co-owned, locked after Phase 0
│   ├── __init__.py
│   ├── enums.py                    # All enumerations
│   ├── exceptions.py               # Domain exception hierarchy
│   ├── events.py                   # Cross-module event definitions
│   ├── dto/                        # Pydantic models (data shapes)
│   │   ├── __init__.py
│   │   ├── accounts.py
│   │   ├── institutions.py
│   │   ├── transactions.py
│   │   ├── investments.py
│   │   ├── goals.py
│   │   ├── budgets.py
│   │   ├── reports.py
│   │   ├── imports.py
│   │   ├── tax.py
│   │   └── common.py              # Pagination, date ranges, etc.
│   ├── protocols/                  # Interface definitions (typing.Protocol)
│   │   ├── __init__.py
│   │   ├── repositories.py        # Data access protocols
│   │   ├── onboarding.py          # Onboarding service protocols
│   │   ├── transaction_service.py # Transaction service protocols
│   │   └── report_service.py      # Report service protocols
│   └── constants.py               # Default CoA codes, config keys, etc.
│
├── database/                       # KALYAN owns
│   ├── __init__.py
│   ├── engine.py                   # SQLAlchemy engine + connection factory
│   ├── tables/                     # SQLAlchemy Core table definitions (Table/MetaData)
│   │   ├── __init__.py
│   │   ├── accounting.py          # accounts, currencies, exchange_rates
│   │   ├── institutions.py        # financial_institutions, bank_accounts, etc.
│   │   ├── transactions.py        # transactions, transaction_lines, charges
│   │   ├── investments.py         # securities, tax_lots, fo_*, holdings
│   │   ├── goals.py
│   │   ├── budgets.py
│   │   ├── imports.py
│   │   ├── tax.py
│   │   ├── system.py              # settings, audit_log, notifications, backup
│   │   └── reports.py             # snapshots, net_worth_history, saved_reports
│   ├── repositories/              # Protocol implementations
│   │   ├── __init__.py
│   │   ├── account_repo.py
│   │   ├── transaction_repo.py
│   │   ├── investment_repo.py
│   │   ├── goal_repo.py
│   │   ├── budget_repo.py
│   │   ├── import_repo.py
│   │   ├── report_repo.py
│   │   ├── settings_repo.py
│   │   └── audit_repo.py
│   ├── seeders/                    # Initial data population
│   │   ├── chart_of_accounts.py
│   │   ├── currencies.py
│   │   ├── tax_sections.py
│   │   └── app_settings.py
│   └── migrations/                 # Alembic migrations
│       ├── env.py
│       └── versions/
│
├── onboarding/                     # HARI owns
│   ├── __init__.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── onboarding_orchestrator.py
│   │   ├── profile_service.py
│   │   ├── institution_service.py
│   │   ├── account_setup_service.py
│   │   ├── opening_balance_service.py
│   │   ├── goal_setup_service.py
│   │   ├── budget_setup_service.py
│   │   └── coa_customization_service.py
│   ├── validators/
│   │   ├── account_validators.py
│   │   └── onboarding_validators.py
│   └── stubs/                      # Stubs for Raj's and Kalyan's modules
│       ├── mock_transaction_service.py
│       └── mock_repositories.py
│
├── transactions/                   # RAJ owns
│   ├── __init__.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── transaction_service.py
│   │   ├── journal_entry_builder.py
│   │   ├── double_entry_validator.py
│   │   ├── void_reversal_service.py
│   │   ├── recurring_engine.py
│   │   ├── investment_transaction_service.py
│   │   ├── fo_transaction_service.py
│   │   ├── tax_lot_manager.py
│   │   ├── import_service.py
│   │   ├── reconciliation_service.py
│   │   ├── goal_contribution_service.py
│   │   └── budget_tracking_service.py
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── csv_parser.py
│   │   ├── bank_statement_parser.py
│   │   ├── brokerage_parser.py
│   │   └── mf_cas_parser.py
│   ├── validators/
│   │   ├── transaction_validators.py
│   │   └── investment_validators.py
│   └── stubs/
│       └── mock_repositories.py
│
├── reports/                        # KALYAN owns
│   ├── __init__.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── report_orchestrator.py
│   │   ├── net_worth_service.py
│   │   ├── income_expense_report.py
│   │   ├── cash_flow_report.py
│   │   ├── balance_sheet_report.py
│   │   ├── trial_balance_report.py
│   │   ├── investment_performance_report.py
│   │   ├── capital_gains_report.py
│   │   ├── tax_summary_report.py
│   │   ├── goal_progress_report.py
│   │   ├── budget_variance_report.py
│   │   ├── fo_pnl_report.py
│   │   └── trend_analysis_service.py
│   ├── snapshot_engine/
│   │   ├── monthly_snapshot_builder.py
│   │   ├── net_worth_tracker.py
│   │   └── holdings_recomputer.py
│   └── exporters/
│       ├── pdf_exporter.py
│       ├── csv_exporter.py
│       └── excel_exporter.py
│
├── common/                         # Shared utilities (any developer can contribute)
│   ├── __init__.py
│   ├── date_utils.py               # FY calculations, Indian date helpers
│   ├── money.py                    # Rounding, formatting (₹ 1,23,456.78)
│   ├── event_bus.py                # Simple in-process event dispatcher
│   └── logger.py
│
├── tests/
│   ├── contracts/                  # Contract conformance tests
│   ├── database/                   # Kalyan's tests
│   ├── onboarding/                 # Hari's tests
│   ├── transactions/               # Raj's tests
│   ├── reports/                    # Kalyan's tests
│   └── integration/                # Post-integration tests (all three)
│
└── app.py                          # Composition root — wires everything together
```

---

## 4. Phase 0 — Contract Definition (All Three Together, ~3-4 Days)

This is the most critical phase. All three developers sit together (or collaborate synchronously) and finalize the contracts package. Nothing else begins until this is locked. The output of this phase is a merged, reviewed, tagged `contracts/` package that all three pull as their foundation.

### 4.1 Enums (`contracts/enums.py`)

Every enumeration used anywhere in the system is defined here. This is the shared vocabulary.

```python
from enum import StrEnum

class AccountType(StrEnum):
    ASSET = "ASSET"
    LIABILITY = "LIABILITY"
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
    EQUITY = "EQUITY"

class AccountSubtype(StrEnum):
    BANK = "BANK"
    CREDIT_CARD = "CREDIT_CARD"
    LOAN = "LOAN"
    BROKERAGE = "BROKERAGE"
    CASH = "CASH"
    FIXED_DEPOSIT = "FIXED_DEPOSIT"
    RECURRING_DEPOSIT = "RECURRING_DEPOSIT"
    PROVIDENT_FUND = "PROVIDENT_FUND"
    FIXED_ASSET = "FIXED_ASSET"
    RECEIVABLE = "RECEIVABLE"
    PAYABLE = "PAYABLE"
    MUTUAL_FUND = "MUTUAL_FUND"
    EQUITY_STOCK = "EQUITY_STOCK"
    ETF = "ETF"
    BOND = "BOND"
    GOLD = "GOLD"
    FO_MARGIN = "FO_MARGIN"
    SALARY = "SALARY"
    INTEREST = "INTEREST"
    DIVIDEND = "DIVIDEND"
    CAPITAL_GAIN = "CAPITAL_GAIN"
    GENERAL = "GENERAL"
    CUSTOM = "CUSTOM"

class NormalBalance(StrEnum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"

class TransactionType(StrEnum):
    EXPENSE = "EXPENSE"
    INCOME = "INCOME"
    TRANSFER = "TRANSFER"
    INVESTMENT_BUY = "INVESTMENT_BUY"
    INVESTMENT_SELL = "INVESTMENT_SELL"
    INVESTMENT_DIVIDEND = "INVESTMENT_DIVIDEND"
    INVESTMENT_BONUS = "INVESTMENT_BONUS"
    INVESTMENT_SPLIT = "INVESTMENT_SPLIT"
    SIP_PURCHASE = "SIP_PURCHASE"
    EMI_PAYMENT = "EMI_PAYMENT"
    FO_BUY = "FO_BUY"
    FO_SELL = "FO_SELL"
    FO_EXPIRY = "FO_EXPIRY"
    INTEREST_CREDIT = "INTEREST_CREDIT"
    INTEREST_DEBIT = "INTEREST_DEBIT"
    OPENING_BALANCE = "OPENING_BALANCE"
    ADJUSTMENT = "ADJUSTMENT"
    REVERSAL = "REVERSAL"
    CREDIT_CARD_PAYMENT = "CREDIT_CARD_PAYMENT"
    TAX_PAYMENT = "TAX_PAYMENT"

class TransactionStatus(StrEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    VOID = "VOID"
    RECONCILED = "RECONCILED"

class LineType(StrEnum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"

class Frequency(StrEnum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    BIWEEKLY = "BIWEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    HALF_YEARLY = "HALF_YEARLY"
    YEARLY = "YEARLY"

class GoalStatus(StrEnum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    ACHIEVED = "ACHIEVED"
    ABANDONED = "ABANDONED"

class GoalType(StrEnum):
    EMERGENCY_FUND = "EMERGENCY_FUND"
    RETIREMENT = "RETIREMENT"
    HOME_PURCHASE = "HOME_PURCHASE"
    VEHICLE = "VEHICLE"
    EDUCATION = "EDUCATION"
    WEDDING = "WEDDING"
    VACATION = "VACATION"
    DEBT_PAYOFF = "DEBT_PAYOFF"
    INVESTMENT_TARGET = "INVESTMENT_TARGET"
    CUSTOM = "CUSTOM"

class SecurityType(StrEnum):
    EQUITY = "EQUITY"
    MUTUAL_FUND = "MUTUAL_FUND"
    ETF = "ETF"
    BOND = "BOND"
    GOVT_SECURITY = "GOVT_SECURITY"
    SOVEREIGN_GOLD_BOND = "SOVEREIGN_GOLD_BOND"
    REIT = "REIT"
    INVIT = "INVIT"
    NPS_SCHEME = "NPS_SCHEME"

class CostBasisMethod(StrEnum):
    FIFO = "FIFO"
    AVERAGE = "AVERAGE"
    SPECIFIC = "SPECIFIC"

class GainType(StrEnum):
    STCG = "STCG"
    LTCG = "LTCG"

# ... all other enums following the same pattern
```

### 4.2 DTOs (`contracts/dto/`)

Pydantic models that define the shape of data flowing between modules. These are not ORM models — they carry no database awareness. They are pure data containers with validation.

```python
# contracts/dto/accounts.py
from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional
from contracts.enums import (
    AccountType, AccountSubtype, NormalBalance
)


class AccountCreateDTO(BaseModel):
    parent_id: Optional[int] = None
    code: str
    name: str
    account_type: AccountType
    account_subtype: Optional[AccountSubtype] = None
    currency_code: str = "INR"
    description: Optional[str] = None
    is_placeholder: bool = False
    is_system: bool = False

class AccountDTO(AccountCreateDTO):
    """Full account representation returned from the database."""
    id: int
    normal_balance: NormalBalance
    is_active: bool
    display_order: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class AccountTreeNodeDTO(BaseModel):
    """Hierarchical account representation for tree views."""
    account: AccountDTO
    children: list["AccountTreeNodeDTO"] = []
    computed_balance: float = 0.0

class AccountBalanceDTO(BaseModel):
    account_id: int
    account_name: str
    account_code: str
    balance: float
    balance_as_of: date


# contracts/dto/transactions.py
class TransactionLineCreateDTO(BaseModel):
    account_id: int
    line_type: LineType
    amount: float = Field(gt=0)
    description: Optional[str] = None
    security_id: Optional[int] = None
    quantity: Optional[float] = None
    price_per_unit: Optional[float] = None

class TransactionCreateDTO(BaseModel):
    transaction_date: date
    transaction_type: TransactionType
    description: str
    lines: list[TransactionLineCreateDTO] = Field(min_length=2)
    payee_id: Optional[int] = None
    reference_number: Optional[str] = None
    tag_ids: list[int] = []
    notes: Optional[str] = None

class TransactionDTO(BaseModel):
    id: int
    transaction_date: date
    transaction_number: str
    transaction_type: TransactionType
    description: str
    status: TransactionStatus
    lines: list["TransactionLineDTO"]
    tags: list["TagDTO"] = []
    payee: Optional["PayeeDTO"] = None
    charges: list["TransactionChargeDTO"] = []
    total_amount: float  # sum of debit side
    is_void: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# contracts/dto/goals.py
class GoalCreateDTO(BaseModel):
    name: str
    goal_type: GoalType
    target_amount: float = Field(gt=0)
    target_date: Optional[date] = None
    start_date: date
    priority: str = "MEDIUM"
    expected_return_rate: Optional[float] = None
    notes: Optional[str] = None
    account_mappings: list["GoalAccountMappingCreateDTO"] = []
    milestones: list["GoalMilestoneCreateDTO"] = []

class GoalDTO(BaseModel):
    id: int
    name: str
    goal_type: GoalType
    target_amount: float
    current_amount: float
    progress_percentage: float
    target_date: Optional[date]
    start_date: date
    status: GoalStatus
    milestones: list["GoalMilestoneDTO"] = []
    account_mappings: list["GoalAccountMappingDTO"] = []
    created_at: datetime

    model_config = {"from_attributes": True}

# ... similar DTOs for every entity
```

### 4.3 Repository Protocols (`contracts/protocols/repositories.py`)

These define _what_ Kalyan's database layer must provide. Hari and Raj code against these protocols. During independent development, they use in-memory stub implementations.

```python
# contracts/protocols/repositories.py
from typing import Protocol, Optional
from datetime import date

from contracts.dto.accounts import (
    AccountDTO, AccountCreateDTO, AccountBalanceDTO, AccountTreeNodeDTO
)
from contracts.dto.transactions import (
    TransactionDTO, TransactionCreateDTO
)
from contracts.dto.common import PaginatedResult, DateRange


class AccountRepository(Protocol):
    def create(self, dto: AccountCreateDTO) -> AccountDTO: ...
    def get_by_id(self, account_id: int) -> Optional[AccountDTO]: ...
    def get_by_code(self, code: str) -> Optional[AccountDTO]: ...
    def get_all_active(self) -> list[AccountDTO]: ...
    def get_tree(self) -> list[AccountTreeNodeDTO]: ...
    def get_children(self, parent_id: int) -> list[AccountDTO]: ...
    def get_by_type(self, account_type: AccountType) -> list[AccountDTO]: ...
    def get_by_subtype(self, subtype: AccountSubtype) -> list[AccountDTO]: ...
    def update(self, account_id: int, dto: AccountCreateDTO) -> AccountDTO: ...
    def deactivate(self, account_id: int) -> None: ...
    def get_balance(
        self, account_id: int, as_of: date
    ) -> AccountBalanceDTO: ...
    def has_transactions(self, account_id: int) -> bool: ...
    def get_next_code(self, parent_id: int) -> str: ...


class TransactionRepository(Protocol):
    def create(self, dto: TransactionCreateDTO) -> TransactionDTO: ...
    def get_by_id(self, txn_id: int) -> Optional[TransactionDTO]: ...
    def get_by_number(self, txn_number: str) -> Optional[TransactionDTO]: ...
    def search(
        self,
        date_range: Optional[DateRange] = None,
        account_id: Optional[int] = None,
        transaction_type: Optional[TransactionType] = None,
        payee_id: Optional[int] = None,
        tag_ids: Optional[list[int]] = None,
        status: Optional[TransactionStatus] = None,
        text_query: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> PaginatedResult[TransactionDTO]: ...
    def void_transaction(
        self, txn_id: int, reason: str
    ) -> TransactionDTO: ...
    def get_next_transaction_number(self) -> str: ...
    def get_lines_by_account(
        self, account_id: int, date_range: DateRange
    ) -> list[TransactionLineDTO]: ...


class GoalRepository(Protocol):
    def create(self, dto: GoalCreateDTO) -> GoalDTO: ...
    def get_by_id(self, goal_id: int) -> Optional[GoalDTO]: ...
    def get_all_active(self) -> list[GoalDTO]: ...
    def update(self, goal_id: int, dto: GoalCreateDTO) -> GoalDTO: ...
    def update_current_amount(
        self, goal_id: int, amount: float
    ) -> None: ...
    def add_contribution(
        self, dto: GoalContributionCreateDTO
    ) -> GoalContributionDTO: ...
    def get_contributions(
        self, goal_id: int
    ) -> list[GoalContributionDTO]: ...


class SecurityRepository(Protocol):
    def create(self, dto: SecurityCreateDTO) -> SecurityDTO: ...
    def get_by_id(self, security_id: int) -> Optional[SecurityDTO]: ...
    def get_by_isin(self, isin: str) -> Optional[SecurityDTO]: ...
    def search(self, query: str) -> list[SecurityDTO]: ...
    def upsert_price(self, dto: SecurityPriceDTO) -> None: ...
    def get_latest_price(
        self, security_id: int
    ) -> Optional[SecurityPriceDTO]: ...
    def get_price_history(
        self, security_id: int, date_range: DateRange
    ) -> list[SecurityPriceDTO]: ...


class TaxLotRepository(Protocol):
    def create(self, dto: TaxLotCreateDTO) -> TaxLotDTO: ...
    def get_open_lots(
        self, security_id: int, brokerage_account_id: int
    ) -> list[TaxLotDTO]: ...
    def reduce_lot(
        self, lot_id: int, quantity: float
    ) -> TaxLotDTO: ...
    def record_disposal(
        self, dto: TaxLotDisposalCreateDTO
    ) -> TaxLotDisposalDTO: ...
    def get_disposals_in_period(
        self, date_range: DateRange
    ) -> list[TaxLotDisposalDTO]: ...


class BudgetRepository(Protocol):
    def create(self, dto: BudgetCreateDTO) -> BudgetDTO: ...
    def get_active_for_period(
        self, as_of: date
    ) -> Optional[BudgetDTO]: ...
    def update_spent(
        self, budget_item_id: int, spent: float
    ) -> None: ...
    # ... remaining methods


class SnapshotRepository(Protocol):
    def save_monthly_snapshot(
        self, dto: MonthlySnapshotDTO
    ) -> None: ...
    def get_snapshot(
        self, account_id: int, year: int, month: int
    ) -> Optional[MonthlySnapshotDTO]: ...
    def save_net_worth(self, dto: NetWorthSnapshotDTO) -> None: ...
    def get_net_worth_history(
        self, date_range: DateRange
    ) -> list[NetWorthSnapshotDTO]: ...


class AuditRepository(Protocol):
    def log(self, dto: AuditLogCreateDTO) -> None: ...
    def get_history(
        self, entity_type: str, entity_id: int
    ) -> list[AuditLogDTO]: ...


class ImportRepository(Protocol):
    def create_profile(
        self, dto: ImportProfileCreateDTO
    ) -> ImportProfileDTO: ...
    def create_batch(
        self, dto: ImportBatchCreateDTO
    ) -> ImportBatchDTO: ...
    def update_batch_status(
        self, batch_id: int, status: str, counts: dict
    ) -> None: ...
    def check_duplicate_file(self, file_hash: str) -> bool: ...

class SettingsRepository(Protocol):
    def get(self, key: str) -> Optional[str]: ...
    def set(self, key: str, value: str) -> None: ...
    def get_by_category(self, category: str) -> dict[str, str]: ...
    def get_all(self) -> dict[str, str]: ...
```

### 4.4 Service Protocols (`contracts/protocols/`)

These define the business-logic interfaces that each module exposes to the others.

```python
# contracts/protocols/onboarding.py
class OnboardingService(Protocol):
    def get_onboarding_state(self) -> OnboardingStateDTO: ...
    def setup_profile(self, dto: ProfileSetupDTO) -> None: ...
    def add_institution(
        self, dto: InstitutionCreateDTO
    ) -> InstitutionDTO: ...
    def add_bank_account(
        self, dto: BankAccountSetupDTO
    ) -> AccountDTO: ...
    def add_credit_card(
        self, dto: CreditCardSetupDTO
    ) -> AccountDTO: ...
    def add_loan(self, dto: LoanSetupDTO) -> AccountDTO: ...
    def add_brokerage_account(
        self, dto: BrokerageSetupDTO
    ) -> AccountDTO: ...
    def set_opening_balance(
        self, dto: OpeningBalanceDTO
    ) -> TransactionDTO: ...
    def setup_initial_goal(
        self, dto: GoalCreateDTO
    ) -> GoalDTO: ...
    def setup_initial_budget(
        self, dto: BudgetCreateDTO
    ) -> BudgetDTO: ...
    def setup_recurring_transaction(
        self, dto: RecurringTransactionCreateDTO
    ) -> RecurringTransactionDTO: ...
    def complete_onboarding(self) -> None: ...
    def can_skip_step(self, step: OnboardingStep) -> bool: ...


# contracts/protocols/transaction_service.py
class TransactionService(Protocol):
    def create_transaction(
        self, dto: TransactionCreateDTO
    ) -> TransactionDTO: ...
    def void_transaction(
        self, txn_id: int, reason: str
    ) -> TransactionDTO: ...
    def create_reversal(
        self, original_txn_id: int, reason: str
    ) -> TransactionDTO: ...
    def get_transaction(
        self, txn_id: int
    ) -> Optional[TransactionDTO]: ...
    def search_transactions(
        self, filters: TransactionSearchDTO
    ) -> PaginatedResult[TransactionDTO]: ...
    def get_account_ledger(
        self, account_id: int, date_range: DateRange
    ) -> AccountLedgerDTO: ...


class InvestmentTransactionService(Protocol):
    def record_buy(
        self, dto: InvestmentBuyDTO
    ) -> TransactionDTO: ...
    def record_sell(
        self, dto: InvestmentSellDTO
    ) -> TransactionDTO: ...
    def record_dividend(
        self, dto: DividendDTO
    ) -> TransactionDTO: ...
    def record_bonus(self, dto: BonusDTO) -> TransactionDTO: ...
    def record_split(self, dto: SplitDTO) -> None: ...
    def get_holdings(
        self, brokerage_account_id: Optional[int] = None
    ) -> list[HoldingSummaryDTO]: ...
    def compute_capital_gains(
        self, date_range: DateRange
    ) -> CapitalGainsSummaryDTO: ...


class RecurringTransactionEngine(Protocol):
    def get_pending_occurrences(
        self, as_of: date
    ) -> list[PendingRecurringDTO]: ...
    def generate_transaction(
        self, recurring_id: int, occurrence_date: date
    ) -> TransactionDTO: ...
    def skip_occurrence(
        self, recurring_id: int, occurrence_date: date
    ) -> None: ...


class ImportService(Protocol):
    def import_bank_statement(
        self, file_path: str, profile_id: int,
        target_account_id: int
    ) -> ImportBatchDTO: ...
    def import_brokerage_tradebook(
        self, file_path: str, profile_id: int,
        brokerage_account_id: int
    ) -> ImportBatchDTO: ...
    def get_reconciliation_queue(
        self, batch_id: int
    ) -> list[ReconciliationRecordDTO]: ...
    def confirm_reconciliation(
        self, record_id: int, action: str,
        matched_txn_id: Optional[int] = None
    ) -> None: ...


# contracts/protocols/report_service.py
class ReportService(Protocol):
    def generate_net_worth(
        self, as_of: date
    ) -> NetWorthReportDTO: ...
    def generate_income_expense(
        self, date_range: DateRange,
        group_by: str = "CATEGORY"
    ) -> IncomeExpenseReportDTO: ...
    def generate_cash_flow(
        self, date_range: DateRange
    ) -> CashFlowReportDTO: ...
    def generate_balance_sheet(
        self, as_of: date
    ) -> BalanceSheetDTO: ...
    def generate_trial_balance(
        self, date_range: DateRange
    ) -> TrialBalanceDTO: ...
    def generate_investment_performance(
        self, date_range: Optional[DateRange] = None
    ) -> InvestmentPerformanceDTO: ...
    def generate_capital_gains_report(
        self, financial_year: str
    ) -> CapitalGainsReportDTO: ...
    def generate_tax_summary(
        self, financial_year: str
    ) -> TaxSummaryDTO: ...
    def generate_goal_progress(
        self, goal_id: Optional[int] = None
    ) -> GoalProgressReportDTO: ...
    def generate_budget_variance(
        self, budget_id: int
    ) -> BudgetVarianceReportDTO: ...
    def save_report_config(
        self, dto: SavedReportCreateDTO
    ) -> SavedReportDTO: ...


class SnapshotService(Protocol):
    def rebuild_monthly_snapshots(
        self, year: int, month: int
    ) -> None: ...
    def rebuild_all_snapshots(self) -> None: ...
    def compute_net_worth_snapshot(self, as_of: date) -> None: ...
    def recompute_holdings(self) -> None: ...
```

### 4.5 Event Contracts (`contracts/events.py`)

Cross-module communication uses a simple in-process event bus. When a transaction is created, it fires an event. The reports module listens and updates snapshots. The goals module listens and updates contribution tracking. This decoupling is what lets the three developers work independently.

```python
# contracts/events.py
from pydantic import BaseModel
from datetime import date

class TransactionCreatedEvent(BaseModel):
    transaction_id: int
    transaction_type: TransactionType
    transaction_date: date
    affected_account_ids: list[int]
    total_amount: float

class TransactionVoidedEvent(BaseModel):
    transaction_id: int
    original_date: date
    affected_account_ids: list[int]

class AccountCreatedEvent(BaseModel):
    account_id: int
    account_type: AccountType
    parent_id: int | None

class GoalContributionEvent(BaseModel):
    goal_id: int
    amount: float
    new_total: float
    target_amount: float

class BudgetThresholdEvent(BaseModel):
    budget_id: int
    budget_item_id: int
    account_id: int
    threshold_pct: float
    current_spent_pct: float

class ImportCompletedEvent(BaseModel):
    batch_id: int
    imported_count: int
    target_account_id: int

class PriceUpdatedEvent(BaseModel):
    security_id: int
    new_price: float
    price_date: date

class SnapshotRefreshRequestedEvent(BaseModel):
    account_ids: list[int]
    year: int
    month: int
```

### 4.6 Exception Hierarchy (`contracts/exceptions.py`)

```python
class AppError(Exception):
    """Base for all application errors."""
    def __init__(self, message: str, code: str = "UNKNOWN"):
        self.message = message
        self.code = code
        super().__init__(message)

class ValidationError(AppError): ...
class NotFoundError(AppError): ...
class DuplicateError(AppError): ...
class DoubleEntryImbalanceError(ValidationError): ...
class AccountHasTransactionsError(ValidationError): ...
class SystemAccountModificationError(ValidationError): ...
class VoidedTransactionError(ValidationError): ...
class InsufficientHoldingsError(ValidationError): ...
class BudgetExceededError(AppError): ...
class OnboardingIncompleteError(AppError): ...
class ImportParsingError(AppError): ...
class ReconciliationConflictError(AppError): ...
```

---

## 5. Developer-Specific Scope and Deliverables

### 5.1 KALYAN — Database Layer + Reports + Snapshots

Kalyan is the foundation. His repositories are what Hari and Raj depend on. He delivers first (stubs first, then real implementations), and his work is the most critical path item.

**Owns:**

Everything inside `database/` and `reports/`. Specifically, all 37 SQLAlchemy Core table definitions mapped to the schema document, all Alembic migration scripts including the initial migration that creates every table, all repository implementations that satisfy the Protocol contracts, all seed data scripts (default Chart of Accounts, currencies, tax sections, default app settings), the snapshot computation engine that rebuilds monthly balance snapshots and net worth history, the holdings recomputation engine that rebuilds `holdings_summary` from `tax_lots`, every report generator (net worth, income/expense, cash flow, balance sheet, trial balance, investment performance, capital gains, tax summary, goal progress, budget variance, F&O P&L, trend analysis), the report export layer (PDF, CSV, Excel), and the audit logging implementation.

**Key Deliverables and Sequence:**

Kalyan's first deliverable is the SQLAlchemy Core table definitions and initial Alembic migration. This is needed within the first two days of Phase 1 because Hari and Raj need to validate that the table schemas match their mental model of the data. His second deliverable is stub repository implementations — simple in-memory dictionaries that satisfy the Protocol interfaces, returning hard-coded or list-backed data. Hari and Raj import these stubs immediately and begin development. His third deliverable is real SQLAlchemy Core-backed repository implementations, replacing the stubs one by one. Each replacement is a drop-in swap — the Protocol interface is identical. His fourth deliverable is the seeder scripts, producing a fully initialized database with the default Chart of Accounts tree, INR currency, current FY tax sections, and default settings. His fifth deliverable is the snapshot engine. His sixth is the report generators, built one at a time, each tested independently against known data sets.

**What Kalyan Depends On:**

Kalyan depends on the finalized contracts (Phase 0) and nothing else. He has no runtime dependency on Hari's or Raj's code. His report generators query the database directly through repositories — they do not call Hari's or Raj's services.

**What Kalyan Provides to Others:**

Kalyan provides the repository implementations that Hari and Raj inject into their services. He also provides a `DatabaseBootstrapper` class that Hari's onboarding orchestrator calls to seed default data and create the initial schema.

### 5.2 HARI — Onboarding Module

Hari owns the entire first-run experience and the account/institution management screens that remain accessible after onboarding.

**Owns:**

Everything inside `onboarding/`. Specifically, the `OnboardingOrchestrator` that manages the multi-step onboarding flow and tracks which steps are completed, skipped, or pending, the profile setup service that captures the user's tax regime, financial year preference, and base currency, the institution management service that creates and updates `financial_institutions` records, the account setup services for each account type (bank account, credit card, loan, brokerage, fixed deposit) where each service creates the leaf node in the Chart of Accounts and the corresponding detail record, the opening balance service that creates the special `OPENING_BALANCE` transaction for each account pairing it against the Equity → Opening Balances account, the Chart of Accounts customization service that lets users rename add or deactivate expense and income categories, the initial goal setup service (creates goals and links them to accounts — the ongoing goal management lives with Raj), the initial budget setup service (creates the first monthly budget — ongoing budget tracking lives with Raj), the recurring transaction template setup service (creates SIP, EMI, rent, and subscription templates — the execution engine lives with Raj), and all onboarding-specific validators (account number format, IFSC validation, credit limit sanity checks, loan tenure and rate validation).

**Key Interaction Pattern with Kalyan's Layer:**

Hari's services receive repository instances through constructor injection:

```python
# onboarding/services/account_setup_service.py
from contracts.protocols.repositories import (
    AccountRepository, AuditRepository
)
from contracts.dto.accounts import AccountCreateDTO, AccountDTO
from contracts.dto.institutions import BankAccountSetupDTO
from contracts.enums import AccountType, AccountSubtype, NormalBalance
from contracts.events import AccountCreatedEvent
from common.event_bus import EventBus


class AccountSetupService:
    def __init__(
        self,
        account_repo: AccountRepository,
        bank_account_repo: BankAccountRepository,
        institution_repo: InstitutionRepository,
        audit_repo: AuditRepository,
        event_bus: EventBus,
    ):
        self._account_repo = account_repo
        self._bank_account_repo = bank_account_repo
        self._institution_repo = institution_repo
        self._audit_repo = audit_repo
        self._event_bus = event_bus

    def add_bank_account(
        self, dto: BankAccountSetupDTO
    ) -> AccountDTO:
        # 1. Determine parent account based on bank_account_type
        parent_code = self._resolve_parent_code(dto.bank_account_type)
        parent = self._account_repo.get_by_code(parent_code)

        # 2. Generate next available code under parent
        next_code = self._account_repo.get_next_code(parent.id)

        # 3. Create the CoA leaf node
        account = self._account_repo.create(AccountCreateDTO(
            parent_id=parent.id,
            code=next_code,
            name=dto.display_name,
            account_type=AccountType.ASSET,
            account_subtype=AccountSubtype.BANK,
            is_placeholder=False,
        ))

        # 4. Create the bank_accounts detail record
        self._bank_account_repo.create(BankAccountCreateDTO(
            account_id=account.id,
            institution_id=dto.institution_id,
            account_number_masked=dto.account_number_masked,
            bank_account_type=dto.bank_account_type,
            ifsc_code=dto.ifsc_code,
            # ...
        ))

        # 5. Audit log
        self._audit_repo.log(AuditLogCreateDTO(
            entity_type="ACCOUNT",
            entity_id=account.id,
            action="CREATE",
            summary=f"Bank account created: {dto.display_name}",
            source="USER",
        ))

        # 6. Fire event
        self._event_bus.publish(AccountCreatedEvent(
            account_id=account.id,
            account_type=AccountType.ASSET,
            parent_id=parent.id,
        ))

        return account
```

**How Hari Develops Independently:**

Hari writes in-memory stubs that implement the repository protocols. He creates a `stubs/mock_repositories.py` file with classes like `InMemoryAccountRepository` that store data in Python dictionaries. All his service logic runs and is testable without a real database. When Kalyan's real repositories are ready, the stub is swapped out at the composition root — Hari's service code changes zero lines.

**Key Deliverables and Sequence:**

Hari's first deliverable is the onboarding state machine — defining the step sequence, skip rules, and completion criteria. Second is the account setup services for each account type, one at a time. Third is the opening balance service with its special double-entry transaction generation. Fourth is the CoA customization service. Fifth is the initial goal and budget setup flows. Sixth is the recurring transaction template creation service.

### 5.3 RAJ — Transaction Management Module

Raj owns the core transaction engine — the most algorithmically complex part of the system. Everything related to creating, validating, voiding, importing, and processing financial transactions lives with him.

**Owns:**

Everything inside `transactions/`. Specifically, the `TransactionService` that creates and retrieves transactions with full double-entry validation, the `JournalEntryBuilder` which is a fluent builder that constructs multi-line transactions ensuring debit-credit balance before persisting, the `DoubleEntryValidator` that enforces the fundamental constraint — sum of debits equals sum of credits with at least two lines, the void and reversal service that marks transactions as void and creates compensating reversal entries, the `RecurringTransactionEngine` that scans templates, generates pending transaction instances, and advances `next_occurrence_date`, the `InvestmentTransactionService` handling buy, sell, dividend, bonus, and split with all their accounting implications, the `TaxLotManager` that creates lots on buy, depletes lots on sell using the configured cost basis method (FIFO or average or specific), computes holding period, and determines STCG vs LTCG classification, the `FOTransactionService` handling F&O position opening, closing, and expiry with margin and premium accounting, the `ImportService` and all parsers (CSV bank statement, brokerage tradebook, MF CAS), the `ReconciliationService` that matches imported records against existing transactions using date, amount, and description heuristics, the `GoalContributionService` that detects when a transaction hits a goal-linked account and auto-records a contribution, the `BudgetTrackingService` that updates budget spent amounts when expense transactions are created, and the transaction charge breakdown computation for investment trades.

**Key Interaction Pattern:**

Raj's services also receive repositories through injection and fire events for cross-cutting concerns:

```python
# transactions/services/transaction_service.py
class TransactionServiceImpl:
    def __init__(
        self,
        txn_repo: TransactionRepository,
        account_repo: AccountRepository,
        audit_repo: AuditRepository,
        event_bus: EventBus,
    ):
        self._txn_repo = txn_repo
        self._account_repo = account_repo
        self._audit_repo = audit_repo
        self._event_bus = event_bus
        self._validator = DoubleEntryValidator()

    def create_transaction(
        self, dto: TransactionCreateDTO
    ) -> TransactionDTO:
        # 1. Validate double-entry balance
        self._validator.validate(dto.lines)

        # 2. Validate all accounts exist and are active leaf nodes
        for line in dto.lines:
            account = self._account_repo.get_by_id(line.account_id)
            if account is None:
                raise NotFoundError(
                    f"Account {line.account_id} not found"
                )
            if account.is_placeholder:
                raise ValidationError(
                    f"Cannot post to placeholder account {account.name}"
                )

        # 3. Generate transaction number
        dto_with_number = dto.model_copy()
        # number assigned by repo

        # 4. Persist
        transaction = self._txn_repo.create(dto)

        # 5. Audit
        self._audit_repo.log(AuditLogCreateDTO(
            entity_type="TRANSACTION",
            entity_id=transaction.id,
            action="CREATE",
            summary=(
                f"Transaction {transaction.transaction_number}: "
                f"{transaction.description}"
            ),
            source="USER",
        ))

        # 6. Fire event — Kalyan's snapshot engine and
        #    Raj's own budget tracker listen to this
        self._event_bus.publish(TransactionCreatedEvent(
            transaction_id=transaction.id,
            transaction_type=transaction.transaction_type,
            transaction_date=transaction.transaction_date,
            affected_account_ids=[
                l.account_id for l in transaction.lines
            ],
            total_amount=sum(
                l.amount for l in transaction.lines
                if l.line_type == LineType.DEBIT
            ),
        ))

        return transaction
```

**The Tax Lot Manager — Raj's Most Complex Piece:**

```python
# transactions/services/tax_lot_manager.py
class TaxLotManager:
    def __init__(
        self,
        tax_lot_repo: TaxLotRepository,
        settings_repo: SettingsRepository,
    ):
        self._lot_repo = tax_lot_repo
        self._settings_repo = settings_repo

    def create_lot(
        self, security_id: int, brokerage_account_id: int,
        buy_transaction_id: int, date: date,
        quantity: float, cost_per_unit: float,
        total_charges: float,
    ) -> TaxLotDTO:
        acquisition_cost = (quantity * cost_per_unit) + total_charges
        return self._lot_repo.create(TaxLotCreateDTO(
            security_id=security_id,
            brokerage_account_id=brokerage_account_id,
            buy_transaction_id=buy_transaction_id,
            acquisition_date=date,
            quantity=quantity,
            cost_per_unit=cost_per_unit,
            acquisition_cost=acquisition_cost,
            remaining_quantity=quantity,
            status="OPEN",
        ))

    def dispose_lots(
        self, security_id: int, brokerage_account_id: int,
        sell_transaction_id: int, disposal_date: date,
        quantity_to_sell: float, sale_price_per_unit: float,
        total_charges: float,
    ) -> list[TaxLotDisposalDTO]:
        method = self._settings_repo.get("cost_basis_method") or "FIFO"
        open_lots = self._lot_repo.get_open_lots(
            security_id, brokerage_account_id
        )

        if method == CostBasisMethod.FIFO:
            open_lots.sort(key=lambda l: l.acquisition_date)

        remaining = quantity_to_sell
        disposals = []

        for lot in open_lots:
            if remaining <= 0:
                break
            dispose_qty = min(lot.remaining_quantity, remaining)
            proportional_cost = (
                lot.acquisition_cost
                * (dispose_qty / lot.quantity)
            )
            sale_proceeds = (
                dispose_qty * sale_price_per_unit
            ) - (total_charges * (dispose_qty / quantity_to_sell))

            holding_days = (disposal_date - lot.acquisition_date).days
            gain_type = self._classify_gain(
                security_id, holding_days
            )

            disposal = self._lot_repo.record_disposal(
                TaxLotDisposalCreateDTO(
                    tax_lot_id=lot.id,
                    sell_transaction_id=sell_transaction_id,
                    disposal_date=disposal_date,
                    quantity_disposed=dispose_qty,
                    sale_price_per_unit=sale_price_per_unit,
                    sale_proceeds=sale_proceeds,
                    cost_of_acquisition=proportional_cost,
                    realized_gain_loss=sale_proceeds - proportional_cost,
                    holding_period_days=holding_days,
                    gain_type=gain_type,
                )
            )
            disposals.append(disposal)

            self._lot_repo.reduce_lot(lot.id, dispose_qty)
            remaining -= dispose_qty

        if remaining > 0:
            raise InsufficientHoldingsError(
                f"Cannot sell {quantity_to_sell} units; "
                f"only {quantity_to_sell - remaining} available"
            )

        return disposals
```

**How Raj Develops Independently:**

Same pattern as Hari — in-memory repository stubs. Raj's `stubs/mock_repositories.py` provides dictionaries that behave like a database. His entire transaction engine, double-entry validator, tax lot manager, and recurring engine are testable without SQLite. He writes comprehensive unit tests with known scenarios (sample buy/sell sequences, EMI calculations, import parsing).

**Key Deliverables and Sequence:**

Raj's first deliverable is the `DoubleEntryValidator` and `JournalEntryBuilder` — the core primitives. Second is `TransactionService` for basic expense, income, and transfer transactions. Third is `InvestmentTransactionService` and `TaxLotManager` for buy and sell flows. Fourth is `RecurringTransactionEngine`. Fifth is the import parsers and `ImportService`. Sixth is `ReconciliationService`. Seventh is `GoalContributionService` and `BudgetTrackingService`. Eighth is F&O transaction handling.

---

## 6. The Event Bus — Cross-Module Communication

The event bus is a simple synchronous in-process pub/sub mechanism. It lives in `common/event_bus.py` and is part of the shared infrastructure.

```python
# common/event_bus.py
from typing import Callable, Type
from collections import defaultdict
from pydantic import BaseModel


class EventBus:
    def __init__(self):
        self._handlers: dict[
            Type[BaseModel], list[Callable]
        ] = defaultdict(list)

    def subscribe(
        self, event_type: Type[BaseModel], handler: Callable
    ) -> None:
        self._handlers[event_type].append(handler)

    def publish(self, event: BaseModel) -> None:
        for handler in self._handlers[type(event)]:
            handler(event)
```

**Who publishes what, and who subscribes:**

| Event | Published By | Subscribed By |
|---|---|---|
| `TransactionCreatedEvent` | Raj (TransactionService) | Kalyan (SnapshotEngine — updates monthly snapshots), Raj (BudgetTrackingService — updates spent amounts, GoalContributionService — checks if affected accounts are goal-linked) |
| `TransactionVoidedEvent` | Raj (VoidReversalService) | Kalyan (SnapshotEngine — reverses snapshot impact) |
| `AccountCreatedEvent` | Hari (AccountSetupService) | Kalyan (SnapshotEngine — initializes snapshot row for new account) |
| `PriceUpdatedEvent` | Kalyan or external price feed | Kalyan (HoldingsRecomputer — updates market values and unrealized P&L) |
| `ImportCompletedEvent` | Raj (ImportService) | Kalyan (generates notification) |
| `BudgetThresholdEvent` | Raj (BudgetTrackingService) | Kalyan (generates notification) |
| `GoalContributionEvent` | Raj (GoalContributionService) | Kalyan (generates notification, checks milestones) |

During independent development, each developer creates a local `EventBus` instance in their test setup. They publish events and verify their own handlers work correctly. They do not need the other module's handlers to be present — those are wired at integration time.

---

## 7. Stub Strategy

Each developer maintains stubs for the modules they depend on. These stubs are simple, deterministic, and live inside their own module's `stubs/` directory — they are not shared code.

```python
# onboarding/stubs/mock_repositories.py  (Hari writes this)
from contracts.protocols.repositories import AccountRepository
from contracts.dto.accounts import AccountDTO, AccountCreateDTO


class InMemoryAccountRepository:
    """Stub for Kalyan's AccountRepository.
    Hari uses this until Kalyan delivers the real implementation."""

    def __init__(self):
        self._store: dict[int, AccountDTO] = {}
        self._next_id = 1

    def create(self, dto: AccountCreateDTO) -> AccountDTO:
        account = AccountDTO(
            id=self._next_id,
            parent_id=dto.parent_id,
            code=dto.code,
            name=dto.name,
            account_type=dto.account_type,
            account_subtype=dto.account_subtype,
            currency_code=dto.currency_code,
            description=dto.description,
            is_placeholder=dto.is_placeholder,
            is_system=dto.is_system,
            normal_balance=(
                NormalBalance.DEBIT
                if dto.account_type in (
                    AccountType.ASSET, AccountType.EXPENSE
                )
                else NormalBalance.CREDIT
            ),
            is_active=True,
            display_order=0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        self._store[account.id] = account
        self._next_id += 1
        return account

    def get_by_id(self, account_id: int) -> AccountDTO | None:
        return self._store.get(account_id)

    # ... implement all Protocol methods with dict-backed logic
```

---

## 8. Composition Root — Integration Wiring

The `app.py` file is where all three developers' work comes together. This is written during integration and is the only place where concrete implementations replace stubs.

```python
# app.py — Composition Root
from database.engine import create_engine, create_session_factory
from database.repositories.account_repo import SQLAccountRepository
from database.repositories.transaction_repo import SQLTransactionRepository
# ... all repository imports

from onboarding.services.onboarding_orchestrator import OnboardingOrchestrator
from onboarding.services.account_setup_service import AccountSetupService

from transactions.services.transaction_service import TransactionServiceImpl
from transactions.services.recurring_engine import RecurringTransactionEngineImpl

from reports.services.report_orchestrator import ReportOrchestrator
from reports.snapshot_engine.monthly_snapshot_builder import MonthlySnapshotBuilder

from common.event_bus import EventBus


def bootstrap():
    # 1. Database
    engine = create_engine("sqlite:///finapp.db")
    session_factory = create_session_factory(engine)

    # 2. Repositories (Kalyan's implementations)
    account_repo = SQLAccountRepository(session_factory)
    txn_repo = SQLTransactionRepository(session_factory)
    goal_repo = SQLGoalRepository(session_factory)
    # ... all others

    # 3. Event Bus
    event_bus = EventBus()

    # 4. Kalyan's services
    snapshot_builder = MonthlySnapshotBuilder(
        snapshot_repo, txn_repo, account_repo
    )
    report_service = ReportOrchestrator(
        snapshot_repo, txn_repo, account_repo,
        goal_repo, budget_repo, tax_lot_repo
    )

    # 5. Raj's services
    txn_service = TransactionServiceImpl(
        txn_repo, account_repo, audit_repo, event_bus
    )
    investment_service = InvestmentTransactionServiceImpl(
        txn_repo, tax_lot_repo, security_repo,
        holdings_repo, account_repo, audit_repo, event_bus
    )
    recurring_engine = RecurringTransactionEngineImpl(
        recurring_repo, txn_service, event_bus
    )
    budget_tracker = BudgetTrackingServiceImpl(
        budget_repo, event_bus
    )
    goal_contributor = GoalContributionServiceImpl(
        goal_repo, goal_mapping_repo, event_bus
    )
    import_service = ImportServiceImpl(
        import_repo, txn_service, reconciliation_repo
    )

    # 6. Hari's services
    onboarding = OnboardingOrchestrator(
        account_setup=AccountSetupService(
            account_repo, bank_account_repo,
            institution_repo, audit_repo, event_bus
        ),
        # ... other setup services
        settings_repo=settings_repo,
    )

    # 7. Wire event subscriptions
    event_bus.subscribe(
        TransactionCreatedEvent, snapshot_builder.on_transaction_created
    )
    event_bus.subscribe(
        TransactionCreatedEvent, budget_tracker.on_transaction_created
    )
    event_bus.subscribe(
        TransactionCreatedEvent, goal_contributor.on_transaction_created
    )
    event_bus.subscribe(
        TransactionVoidedEvent, snapshot_builder.on_transaction_voided
    )
    event_bus.subscribe(
        AccountCreatedEvent, snapshot_builder.on_account_created
    )

    return AppContext(
        onboarding=onboarding,
        transaction_service=txn_service,
        investment_service=investment_service,
        recurring_engine=recurring_engine,
        import_service=import_service,
        report_service=report_service,
    )
```

---

## 9. Phased Delivery Plan

### Phase 0: Contract Lock (All Three — Days 1-4)

All three developers work together. The output is the complete `contracts/` package, reviewed, tested for consistency, and tagged as `v0.1-contracts` in version control. No implementation code is written. The common utilities package (`common/`) is also set up — `event_bus.py`, `date_utils.py`, `money.py`.

### Phase 1: Foundation (Days 5-14, Parallel Work Begins)

| Kalyan | Hari | Raj |
|---|---|---|
| SQLAlchemy models for all 37 tables | Onboarding state machine and step definitions | `DoubleEntryValidator` with exhaustive unit tests |
| Alembic initial migration | Profile setup service | `JournalEntryBuilder` fluent API |
| `create_engine` and session factory | Institution management service | Basic `TransactionService` (expense, income, transfer) |
| Stub repositories (in-memory, Protocol-conformant) → pushed to shared repo so Hari and Raj can replace their own stubs | Bank account setup service | Transaction search and retrieval |
| Currency and settings seeders | | |

**Gate:** At end of Phase 1, Kalyan's stub repositories are the canonical stubs that Hari and Raj both switch to, ensuring all three are developing against identical data behavior.

### Phase 2: Core Features (Days 15-28)

| Kalyan | Hari | Raj |
|---|---|---|
| Real SQLite repository implementations (account, transaction, settings, audit) — replacing stubs one by one | Credit card setup service | `InvestmentTransactionService` (buy/sell) |
| Chart of Accounts seeder (full default tree) | Loan setup service | `TaxLotManager` (FIFO and average cost) |
| Tax sections seeder | Brokerage account setup service | `TaxLotDisposal` and capital gains classification |
| Monthly snapshot builder | Fixed deposit setup service | `VoidReversalService` |
| Audit log repository | Opening balance service | Payee and tag management |
| | CoA customization service | |

### Phase 3: Advanced Features (Days 29-42)

| Kalyan | Hari | Raj |
|---|---|---|
| Real repositories for investments, goals, budgets, imports | Goal setup service | `RecurringTransactionEngine` |
| Net worth snapshot computation | Budget setup service | Import parsers (bank CSV, brokerage tradebook) |
| Holdings recomputer | Recurring transaction template setup | `ImportService` and `ReconciliationService` |
| Net worth report generator | Onboarding completion and validation | `GoalContributionService` |
| Income/expense report generator | | `BudgetTrackingService` |
| Balance sheet and trial balance | | F&O transaction service |

### Phase 4: Reports and Polish (Days 43-52)

| Kalyan | Hari | Raj |
|---|---|---|
| Investment performance report | Onboarding flow testing with real repos | MF CAS parser |
| Capital gains report | Edge case handling and re-onboarding flow | Import profile management |
| Tax summary report (80C, 80D mapping) | | Transaction charge breakdown |
| Goal progress report | | |
| Budget variance report | | |
| Trend analysis service | | |
| Export to PDF/CSV/Excel | | |

### Phase 5: Integration (Days 53-60)

All three developers work together. The `app.py` composition root is written. Event bus subscriptions are wired. End-to-end integration tests are authored — a full scenario that starts with onboarding, creates accounts, enters transactions, generates recurring entries, imports a statement, runs reconciliation, and produces all reports. Bugs found during integration are assigned to the appropriate developer based on which layer they originate in.

---

## 10. Testing Strategy

Each developer is responsible for unit tests within their module at a minimum of 80% coverage. The testing approach breaks down as follows.

**Kalyan** writes repository integration tests that run against a real SQLite in-memory database (`sqlite:///:memory:`), verifying that every repository method correctly reads and writes data. He also writes snapshot computation tests with known transaction sequences where expected monthly balances are pre-calculated, and report output tests with fixture data where expected totals are hand-verified.

**Hari** writes service unit tests using Kalyan's stub repositories, verifying that the onboarding orchestrator correctly sequences steps, that each account type is created with the correct parent and subtype, that opening balances produce valid double-entry transactions, and that validation rules reject invalid inputs.

**Raj** writes unit tests for the double-entry validator covering every edge case (imbalanced lines, single line, zero amounts, negative amounts). He tests the tax lot manager with known buy/sell sequences where expected lots, remaining quantities, and capital gains are hand-computed. He tests the recurring engine with various frequencies and date arithmetic. He tests each import parser with sample statement files.

**Integration tests** (Phase 5) are co-owned and live in `tests/integration/`. These are scenario-based end-to-end tests that exercise the full stack from service call through repository to SQLite and back.

---

## 11. Version Control and Branch Strategy

The repository uses a trunk-based branching model with short-lived feature branches.

The `main` branch is the integration branch. The `contracts` directory is protected — changes require review from all three developers. Each developer works on feature branches named with their module prefix: `hari/onboarding-state-machine`, `raj/double-entry-validator`, `kalyan/account-repository`. Branches merge to `main` once they pass their own unit tests and do not break the contract conformance tests. The contracts package has its own test suite (`tests/contracts/`) that validates DTO serialization, Protocol completeness, and enum consistency. This runs in CI on every merge to `main`.

---

## 12. Summary: Who Owns What

| Component | Owner | Depends On |
|---|---|---|
| `contracts/*` | All Three (co-owned) | Nothing |
| `common/*` | All Three (co-owned) | `contracts` |
| `database/models/*` | Kalyan | `contracts` |
| `database/repositories/*` | Kalyan | `contracts`, `database/models` |
| `database/seeders/*` | Kalyan | `contracts`, `database/models` |
| `database/migrations/*` | Kalyan | `database/models` |
| `reports/services/*` | Kalyan | `contracts`, `database/repositories` |
| `reports/snapshot_engine/*` | Kalyan | `contracts`, `database/repositories` |
| `reports/exporters/*` | Kalyan | `reports/services` |
| `onboarding/services/*` | Hari | `contracts`, repository protocols |
| `onboarding/validators/*` | Hari | `contracts` |
| `transactions/services/*` | Raj | `contracts`, repository protocols |
| `transactions/parsers/*` | Raj | `contracts` |
| `transactions/validators/*` | Raj | `contracts` |
| `app.py` | All Three (integration) | Everything |

The fundamental guarantee of this structure is that Hari never imports from `transactions/`, Raj never imports from `onboarding/`, and neither imports from `database/` or `reports/`. Everyone imports only from `contracts/` and `common/`. Kalyan's `reports/` module imports from `database/` (his own code) and `contracts/`. The only place cross-module concrete types meet is `app.py`.