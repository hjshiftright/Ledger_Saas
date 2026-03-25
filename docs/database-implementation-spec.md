# Ledger — Database Implementation Specification

## 1. Overview
This specification details the implementation guidelines for the Ledger Database Layer, executing **Approach 1: FastAPI + SQLAlchemy ORM + Manual Repository Pattern** as described in `dao.md`. By standardizing on SQLAlchemy ORM (`DeclarativeBase`), all tables defined in `db-schema.md` fully support seamless, object-oriented CRUD operations while preserving strict type safety and transaction boundaries.


## 2. Directory Structure Integration
The implementation maps directly onto the architecture described in V1:
```text
ledger/
├── db/
│   ├── engine.py             # DB Session config & Dependency
│   ├── models/               # SQLAlchemy Declarative Models
│   │   ├── base.py           # Base model definitions
│   │   ├── accounts.py       # (Accounts, FinancialInstitutions, etc.)
│   │   ├── transactions.py   # (Transactions, Lines, Charges)
│   │   └── goals.py          # (Goals, Milestones, Budgets)
│   └── repositories/         # Manual Repositories (Generic + Specific)
│       ├── base.py           # BaseRepository[T]
│       ├── account_repo.py   
│       └── transaction_repo.py
└── api/
    └── dependencies.py       # FastAPI Depend injects session/repo
```

## 3. Core Database Engine & Session Management
All database access is centralized through SQLAlchemy's Session object, bound to the request lifecycle via FastAPI's Dependency Injection.

### 3.1 Session Dependency
```python
# db/engine.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True
)
SessionFactory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

def get_session():
    """FastAPI Dependency enforcing Unit of Work pattern (1 transaction / request)."""
    session = SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

### 3.2 Unit of Work for Complex Operations
For multi-entity atomic operations (e.g., creating a Transaction with Lines, Charges, and updating account snapshots) **outside the HTTP request lifecycle**, use an explicit Unit of Work context manager:

```python
# db/unit_of_work.py
from contextlib import contextmanager
from sqlalchemy.orm import Session
from db.engine import SessionFactory

@contextmanager
def unit_of_work(existing_session: Session | None = None):
    """
    Explicit Unit of Work for multi-entity atomic operations.

    If an existing_session is provided, the caller owns the transaction —
    this context manager simply yields it without committing or closing.
    If no session is provided, a new session is created with full
    commit-on-success / rollback-on-failure semantics.

    Usage (standalone — background jobs, CLI, batch imports):
        with unit_of_work() as session:
            txn = Transaction(...)
            txn.lines.append(TransactionLine(...))
            session.add(txn)
            session.flush()
            # any exception → auto rollback of EVERYTHING
        # commit happens at __exit__ if no exception

    Usage (joining an existing session):
        with unit_of_work(existing_session=session) as uow_session:
            # uow_session IS the existing session — no new transaction
            repo = TransactionRepository(uow_session)
            repo.create_with_children(txn)
    """
    if existing_session is not None:
        # Caller owns the lifecycle — do not commit/rollback/close
        yield existing_session
        return

    session = SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

> **⚠️ Important:** Do NOT call `unit_of_work()` without passing `existing_session` from inside an HTTP request handler where `get_session()` is already active. Doing so creates a **second, independent database transaction**, which defeats atomicity.

**When to use `get_session()` vs `unit_of_work()`:**

| Scenario | Use | Why |
|----------|-----|-----|
| API endpoint (single or multi-repo CRUD) | `get_session()` via `Depends` | Session lifecycle tied to HTTP request |
| Background job / cron task | `unit_of_work()` (no args) | No HTTP context — needs its own session |
| CLI command / data migration | `unit_of_work()` (no args) | No HTTP context |
| Service helper that may be called from either context | `unit_of_work(existing_session=session)` | Re-uses caller's session if available |

### 3.3 Transaction Propagation — How It Works

Transaction propagation is the guarantee that **all database operations within a single business action share one database transaction**, so they either all succeed or all roll back together. This spec achieves propagation through **session sharing**, not annotations or decorators.

#### Core Principle: `flush()` ≠ `commit()`

Every repository method calls `session.flush()`, **never** `session.commit()`.

| Method | What it does | Transaction effect |
|--------|-------------|--------------------|
| `session.flush()` | Writes pending changes to the DB **within** the current transaction | Transaction stays **open** — changes are invisible outside this session |
| `session.commit()` | Finalises the transaction — makes all flushed changes permanent | Transaction **ends** — changes become visible to other connections |
| `session.rollback()` | Discards ALL flushed-but-uncommitted changes | Transaction **ends** — nothing was saved |

Because repositories only `flush()`, the **caller controls when the transaction commits**. For HTTP requests, `get_session()` commits once at the end. For background jobs, `unit_of_work()` commits when the `with` block exits cleanly.

#### Example 1 — Simple CRUD (Single Repository)

The simplest case: one API call → one service → one repo → one `flush()`.

```python
# Flow: POST /accounts
#
# get_session() ─── creates Session ──→ AccountService ──→ AccountRepository
#                                                              │
#                                                         session.flush()  ← writes, no commit
#                   session.commit() ← only HERE, after the route handler returns

@router.post("/accounts", response_model=AccountResponseDTO)
def create_account(
    data: AccountCreateDTO,
    service: AccountService = Depends(get_account_service)
):
    return service.create_new_account(data)  # flush() happens inside repo
    # ← get_session() calls commit() here if no exception
    # ← get_session() calls rollback() if any exception was raised
```

#### Example 2 — Multi-Repository Atomic Operation (Transaction Propagation)

A real-world scenario: creating a Transaction with journal lines **and** updating the monthly snapshot — two different repositories, one atomic operation.

```python
# services/transaction_service.py
from db.repositories.transaction_repo import TransactionRepository
from db.repositories.snapshot_repo import SnapshotRepository
from db.models.transactions import Transaction, TransactionLine
from schemas.transaction import TransactionCreateDTO
from sqlalchemy.orm import Session
from decimal import Decimal

class TransactionService:
    def __init__(self, session: Session):
        # BOTH repos receive the SAME session → same DB transaction
        self.txn_repo = TransactionRepository(session)
        self.snapshot_repo = SnapshotRepository(session)

    def record_expense(self, dto: TransactionCreateDTO) -> Transaction:
        """
        Business operation that spans two repositories.
        Both flush() calls happen inside the SAME transaction.
        If snapshot update fails, the transaction entry is also rolled back.
        """
        # Step 1: Create the journal entry (flush #1)
        txn = Transaction(
            transaction_date=dto.date,
            transaction_type="EXPENSE",
            description=dto.description,
        )
        txn.lines.append(TransactionLine(
            account_id=dto.expense_account_id,
            line_type="DEBIT",
            amount=dto.amount,
        ))
        txn.lines.append(TransactionLine(
            account_id=dto.payment_account_id,
            line_type="CREDIT",
            amount=dto.amount,
        ))
        saved_txn = self.txn_repo.create_with_children(txn)  # ← flush(), NOT commit()

        # Step 2: Update monthly snapshot (flush #2, SAME transaction)
        self.snapshot_repo.increment_month(
            account_id=dto.expense_account_id,
            year=dto.date.year,
            month=dto.date.month,
            debit_delta=dto.amount,
        )
        self.snapshot_repo.increment_month(
            account_id=dto.payment_account_id,
            year=dto.date.year,
            month=dto.date.month,
            credit_delta=dto.amount,
        )

        return saved_txn
        # ← No commit() here! get_session() commits after the route handler returns.
        # ← If ANYTHING above threw an exception, get_session() rolls back EVERYTHING.
```

```python
# api/routes/transactions.py
@router.post("/transactions/expense", response_model=TransactionResponseDTO)
def record_expense(
    data: TransactionCreateDTO,
    session: Session = Depends(get_session)
):
    service = TransactionService(session)
    return service.record_expense(data)
    # ← get_session() commit() or rollback() happens here
```

The propagation guarantee:
```text
HTTP Request
  │
  ├─ get_session() creates Session (BEGIN TRANSACTION)
  │
  ├─ TransactionService.record_expense()
  │   ├─ TransactionRepository.create_with_children()  →  flush() #1
  │   ├─ SnapshotRepository.increment_month()           →  flush() #2
  │   └─ SnapshotRepository.increment_month()           →  flush() #3
  │
  ├─ No exception? → COMMIT   (all 3 flushes become permanent together)
  └─ Exception?    → ROLLBACK (all 3 flushes are discarded together)
```

#### Example 3 — Cascade Saves (Parent-Child Entity Graph)

When creating an entity that has children defined with `cascade="all, delete-orphan"`, SQLAlchemy automatically persists the entire object graph in a single `session.add()` + `session.flush()` call.

```python
# Creating a Transaction with Lines and Charges — all saved atomically
txn = Transaction(
    transaction_date=date(2026, 3, 1),
    transaction_type="EXPENSE",
    description="Grocery shopping",
)

# Append children to the parent — no need to add them to session separately
txn.lines.append(TransactionLine(
    account_id=expense_account.id, line_type="DEBIT", amount=Decimal("2500.00")
))
txn.lines.append(TransactionLine(
    account_id=cash_account.id, line_type="CREDIT", amount=Decimal("2500.00")
))
txn.charges.append(TransactionCharge(
    charge_type="GST", amount=Decimal("125.00"), description="5% GST"
))

# ONE call saves Transaction + 2 Lines + 1 Charge
repo.create_with_children(txn)
# Internally: session.add(txn) → cascade → session.flush()
# All 4 rows are written in a single flush within the current transaction
```

#### Example 4 — Background Job with `unit_of_work()`

For operations outside the HTTP lifecycle (cron, CLI, batch import), `unit_of_work()` provides the same propagation guarantee:

```python
# jobs/monthly_snapshot_job.py
from db.unit_of_work import unit_of_work
from db.repositories.snapshot_repo import SnapshotRepository
from db.repositories.account_repo import AccountRepository

def generate_monthly_snapshots(year: int, month: int):
    """
    Background job: compute and store monthly snapshots for all accounts.
    ALL snapshots are saved atomically — partial failure = full rollback.
    """
    with unit_of_work() as session:
        account_repo = AccountRepository(session)
        snapshot_repo = SnapshotRepository(session)

        accounts = account_repo.list_paginated(offset=0, limit=10000)
        for account in accounts:
            snapshot = snapshot_repo.compute_snapshot(account.id, year, month)
            snapshot_repo.create(snapshot)   # flush() per snapshot, NO commit

    # ← unit_of_work() commits here if no exception
    # ← If ANY snapshot computation failed, NONE are saved
```

#### Summary: Transaction Propagation Rules

| Rule | Detail |
|------|--------|
| Repositories **never** call `commit()` | They only call `flush()` — the caller decides when to commit |
| Session sharing = Transaction sharing | If two repos hold the same `Session`, they are in the same DB transaction |
| `get_session()` owns the transaction for HTTP | Commits once after the route handler returns successfully |
| `unit_of_work()` owns the transaction for non-HTTP | Commits once when the `with` block exits without exception |
| Cascade saves handle parent-child graphs | `session.add(parent)` with `cascade="all, delete-orphan"` saves the entire tree |
| All-or-nothing guarantee | Any exception → `rollback()` → zero changes persisted |

---

## 4. Object-Oriented Entity Modeling (Base & Models)

To support object-oriented CRUD operations across all tables, every table from `db-schema.md` will be represented as a SQLAlchemy ORM Model extending a common `Base` class.

### 4.1 Base Model Definition
```python
# db/models/base.py
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import Numeric, Date, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func

class Base(DeclarativeBase):
    """Common ORM Base containing standard audit columns."""
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
```

> **Convention:** All models import `Decimal`, `date`, `datetime`, `Numeric(18, 4)`, `Date`, and `DateTime` from the base. Monetary amounts are always `Mapped[Decimal]` with `Numeric(18, 4)`. Dates are always `Mapped[date]` with `Date`. Timestamps are always `Mapped[datetime]` with `DateTime`.

### 4.2 Example Entity Model (Accounts Table)
```python
# db/models/accounts.py
from db.models.base import Base
from sqlalchemy import String, Integer, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

class Account(Base):
    __tablename__ = "accounts"
    
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    code: Mapped[str] = mapped_column(String, unique=True)
    name: Mapped[str] = mapped_column(String)
    account_type: Mapped[str] = mapped_column(String)
    account_subtype: Mapped[str | None] = mapped_column(String, nullable=True)
    currency_code: Mapped[str] = mapped_column(ForeignKey("currencies.code"), default="INR")
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    is_placeholder: Mapped[bool] = mapped_column(Boolean, default=False)
    normal_balance: Mapped[str] = mapped_column(String)
    display_order: Mapped[int] = mapped_column(Integer, default=0)

    # Self-referential hierarchy
    parent: Mapped["Account | None"] = relationship(
        remote_side="Account.id", back_populates="children"
    )
    children: Mapped[list["Account"]] = relationship(back_populates="parent")
```

### 4.3 User Profile Management Models (Household & Multi-Tenancy)
The PRD requires managing a primary user and sub-profiles (e.g., spouse and dependents) for consolidated household balance sheets. While the initial schema focuses on a single primary user, here is how the Profile entities map to SQLAlchemy objects to support these features:

```python
# db/models/users.py
from db.models.base import Base
from sqlalchemy import String, Integer, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

class User(Base):
    """Primary User Account (Authentication Level)"""
    __tablename__ = "users"
    
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Household Profiles associated with this login
    profiles: Mapped[list["UserProfile"]] = relationship(back_populates="user")

class UserProfile(Base):
    """Household Sub-Profiles (Spouse, Dependents, etc.)"""
    __tablename__ = "user_profiles"
    
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    profile_name: Mapped[str] = mapped_column(String)
    relationship_type: Mapped[str] = mapped_column(String) # e.g., 'Primary', 'Spouse', 'Dependent'
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    
    user: Mapped["User"] = relationship(back_populates="profiles")
```
*Note: To fully implement multi-tenancy, a `profile_id` (or `user_id`) foreign key would be added to the `Account` and `Transaction` models to partition the financial ledger by household member.*


## 5. Manual Repository Pattern

A central `BaseRepository` leverages generic typing to provide unified, object-based CRUD operations for any entity without repeating code.

### 5.1 Generic Base Repository

```python
# db/repositories/base.py
from typing import TypeVar, Generic, Type, Sequence, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from db.models.base import Base

T = TypeVar("T", bound=Base)

class BaseRepository(Generic[T]):
    """Generic repository mapping standard CRUD ops to object entities."""
    def __init__(self, model: Type[T], session: Session):
        self.model = model
        self.session = session

    def get_by_id(self, entity_id: int) -> Optional[T]:
        return self.session.get(self.model, entity_id)

    def get_by_id_or_raise(self, entity_id: int) -> T:
        entity = self.get_by_id(entity_id)
        if entity is None:
            raise ValueError(f"{self.model.__name__} with ID {entity_id} not found")
        return entity

    def count(self) -> int:
        stmt = select(func.count()).select_from(self.model)
        return self.session.scalar(stmt) or 0

    def list_paginated(self, offset: int = 0, limit: int = 100) -> Sequence[T]:
        stmt = select(self.model).offset(offset).limit(limit)
        return self.session.scalars(stmt).all()

    def create(self, entity: T) -> T:
        """Create operation using Python Objects"""
        self.session.add(entity)
        self.session.flush() # Securely assigns ID without committing txn
        return entity

    def create_many(self, entities: list[T]) -> list[T]:
        self.session.add_all(entities)
        self.session.flush()
        return entities

    def update(self, entity: T) -> T:
        """Update operation using Python Objects"""
        merged = self.session.merge(entity)
        self.session.flush()
        return merged

    def delete(self, entity: T) -> None:
        """Delete operation using Python Objects"""
        self.session.delete(entity)
        self.session.flush()

    def delete_by_id(self, entity_id: int) -> None:
        entity = self.get_by_id_or_raise(entity_id)
        self.delete(entity)
```

### 5.2 Specific Entity Repositories
Domain repositories inherit the generic logic and extend it with business queries.

```python
# db/repositories/account_repo.py
from sqlalchemy.orm import Session
from sqlalchemy import select
from db.models.accounts import Account
from db.repositories.base import BaseRepository

class AccountRepository(BaseRepository[Account]):
    def __init__(self, session: Session):
        super().__init__(Account, session)
        
    def find_by_code(self, code: str) -> Account | None:
        stmt = select(Account).where(Account.code == code)
        return self.session.scalar(stmt)
        
    def get_leaf_nodes_for_type(self, account_type: str) -> list[Account]:
        """Provides query abstraction independent of the Service layer."""
        stmt = (
            select(Account)
            .where(Account.account_type == account_type)
            .where(Account.is_placeholder.is_(False))
            .where(Account.is_active.is_(True))
        )
        return list(self.session.scalars(stmt).all())
```

## 6. Service and Routing Integration (FastAPI)
The final step bounds business logic through dependency injection. Controllers (routers) only deal with payloads (Pydantic), Services map domain rules safely inside the `get_session` context, and Repositories manipulate objects.

```python
# services/account_service.py
from db.repositories.account_repo import AccountRepository
from db.models.accounts import Account
from schemas.account import AccountCreateDTO
from sqlalchemy.orm import Session

class AccountService:
    def __init__(self, session: Session):
        self.repo = AccountRepository(session)

    def create_new_account(self, dto: AccountCreateDTO) -> Account:
        if self.repo.find_by_code(dto.code):
            raise ValueError(f"Account code {dto.code} already exists")
            
        # Object creation
        new_account = Account(
            code=dto.code,
            name=dto.name,
            account_type=dto.account_type,
            normal_balance=dto.normal_balance
        )
        
        # Object-based insertion via Repository
        return self.repo.create(new_account)
```

```python
# api/routes/accounts.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.engine import get_session
from services.account_service import AccountService
from schemas.account import AccountCreateDTO, AccountResponseDTO

router = APIRouter()

def get_account_service(session: Session = Depends(get_session)) -> AccountService:
    """Wires session dependency seamlessly."""
    return AccountService(session)

@router.post("/accounts", response_model=AccountResponseDTO)
def create_account(
    data: AccountCreateDTO,
    service: AccountService = Depends(get_account_service)
):
    return service.create_new_account(data)
```

## 7. Comprehensive Domain Models

The following sections define the exact SQLAlchemy ORM mappings for all 37 tables established in `db-schema.md`, categorized by domain. These models extend the declarative `Base` and establish relationships, ensuring that the manual repositories can seamlessly navigate the graph of objects.

### 7.1 Core Accounting Models
*Note: The `Account` model was defined in Section 4.2.*

```python
from sqlalchemy import String, Integer, Boolean, Numeric, Date, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.models.base import Base
from decimal import Decimal
from datetime import date, datetime

class Currency(Base):
    __tablename__ = "currencies"
    code: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    symbol: Mapped[str] = mapped_column(String)
    decimal_places: Mapped[int] = mapped_column(Integer, default=2)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class ExchangeRate(Base):
    __tablename__ = "exchange_rates"
    from_currency_code: Mapped[str] = mapped_column(ForeignKey("currencies.code"))
    to_currency_code: Mapped[str] = mapped_column(ForeignKey("currencies.code"))
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    rate_date: Mapped[date] = mapped_column(Date)
    source: Mapped[str | None] = mapped_column(String, nullable=True)
```

### 7.2 Financial Institutions and Accounts

```python
class FinancialInstitution(Base):
    __tablename__ = "financial_institutions"
    name: Mapped[str] = mapped_column(String)
    institution_type: Mapped[str] = mapped_column(String)
    logo_path: Mapped[str | None] = mapped_column(String, nullable=True)
    website: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships — institution owns many account-detail records
    bank_accounts: Mapped[list["BankAccount"]] = relationship(back_populates="institution")
    fixed_deposits: Mapped[list["FixedDeposit"]] = relationship(back_populates="institution")
    credit_cards: Mapped[list["CreditCard"]] = relationship(back_populates="institution")
    loans: Mapped[list["Loan"]] = relationship(back_populates="institution")
    brokerage_accounts: Mapped[list["BrokerageAccount"]] = relationship(back_populates="institution")

class BankAccount(Base):
    __tablename__ = "bank_accounts"
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), unique=True)
    institution_id: Mapped[int] = mapped_column(ForeignKey("financial_institutions.id"))
    account_number_masked: Mapped[str | None] = mapped_column(String, nullable=True)
    bank_account_type: Mapped[str] = mapped_column(String)
    ifsc_code: Mapped[str | None] = mapped_column(String, nullable=True)
    branch_name: Mapped[str | None] = mapped_column(String, nullable=True)
    nominee_name: Mapped[str | None] = mapped_column(String, nullable=True)
    opening_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    institution: Mapped["FinancialInstitution"] = relationship(back_populates="bank_accounts")
    account: Mapped["Account"] = relationship()

class FixedDeposit(Base):
    __tablename__ = "fixed_deposits"
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), unique=True)
    institution_id: Mapped[int] = mapped_column(ForeignKey("financial_institutions.id"))
    fd_number: Mapped[str | None] = mapped_column(String, nullable=True)
    deposit_type: Mapped[str] = mapped_column(String)
    principal_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    interest_rate: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    compounding_frequency: Mapped[str] = mapped_column(String, default="QUARTERLY")
    deposit_date: Mapped[date] = mapped_column(Date)
    maturity_date: Mapped[date] = mapped_column(Date)
    maturity_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=False)
    linked_bank_account_id: Mapped[int | None] = mapped_column(ForeignKey("bank_accounts.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    institution: Mapped["FinancialInstitution"] = relationship(back_populates="fixed_deposits")
    account: Mapped["Account"] = relationship()

class CreditCard(Base):
    __tablename__ = "credit_cards"
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), unique=True)
    institution_id: Mapped[int] = mapped_column(ForeignKey("financial_institutions.id"))
    card_number_masked: Mapped[str | None] = mapped_column(String, nullable=True)
    card_network: Mapped[str | None] = mapped_column(String, nullable=True)
    card_variant: Mapped[str | None] = mapped_column(String, nullable=True)
    credit_limit: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    billing_cycle_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payment_due_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    annual_fee: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    reward_program_name: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    institution: Mapped["FinancialInstitution"] = relationship(back_populates="credit_cards")
    account: Mapped["Account"] = relationship()

class Loan(Base):
    __tablename__ = "loans"
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), unique=True)
    institution_id: Mapped[int] = mapped_column(ForeignKey("financial_institutions.id"))
    loan_account_number: Mapped[str | None] = mapped_column(String, nullable=True)
    loan_type: Mapped[str] = mapped_column(String)
    principal_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    current_outstanding: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    interest_rate: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    interest_type: Mapped[str] = mapped_column(String, default="FLOATING")
    tenure_months: Mapped[int] = mapped_column(Integer)
    emi_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    disbursement_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    emi_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expected_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    linked_asset_account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    prepayment_charges_applicable: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    institution: Mapped["FinancialInstitution"] = relationship(back_populates="loans")
    account: Mapped["Account"] = relationship(foreign_keys=[account_id])

class BrokerageAccount(Base):
    __tablename__ = "brokerage_accounts"
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), unique=True)
    institution_id: Mapped[int] = mapped_column(ForeignKey("financial_institutions.id"))
    account_identifier: Mapped[str | None] = mapped_column(String, nullable=True)
    brokerage_account_type: Mapped[str] = mapped_column(String)
    depository: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    institution: Mapped["FinancialInstitution"] = relationship(back_populates="brokerage_accounts")
    account: Mapped["Account"] = relationship()
```

### 7.3 Investments & Securities

```python
class Security(Base):
    __tablename__ = "securities"
    symbol: Mapped[str | None] = mapped_column(String, nullable=True)
    isin: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String)
    security_type: Mapped[str] = mapped_column(String)
    exchange: Mapped[str | None] = mapped_column(String, nullable=True)
    sector: Mapped[str | None] = mapped_column(String, nullable=True)
    industry: Mapped[str | None] = mapped_column(String, nullable=True)
    mf_category: Mapped[str | None] = mapped_column(String, nullable=True)
    mf_amc: Mapped[str | None] = mapped_column(String, nullable=True)
    mf_plan: Mapped[str | None] = mapped_column(String, nullable=True)
    mf_option: Mapped[str | None] = mapped_column(String, nullable=True)
    face_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    lot_size: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    prices: Mapped[list["SecurityPrice"]] = relationship(
        back_populates="security", cascade="all, delete-orphan", lazy="selectin"
    )
    tax_lots: Mapped[list["TaxLot"]] = relationship(
        back_populates="security", cascade="all, delete-orphan", lazy="selectin"
    )

class SecurityPrice(Base):
    __tablename__ = "security_prices"
    security_id: Mapped[int] = mapped_column(ForeignKey("securities.id"))
    price_date: Mapped[date] = mapped_column(Date)
    close_price: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    open_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    high_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    low_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    volume: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str | None] = mapped_column(String, nullable=True)

    security: Mapped["Security"] = relationship(back_populates="prices")

class TaxLot(Base):
    __tablename__ = "tax_lots"
    security_id: Mapped[int] = mapped_column(ForeignKey("securities.id"))
    brokerage_account_id: Mapped[int] = mapped_column(ForeignKey("brokerage_accounts.id"))
    buy_transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"))
    acquisition_date: Mapped[date] = mapped_column(Date)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    cost_per_unit: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    acquisition_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    remaining_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    status: Mapped[str] = mapped_column(String, default="OPEN")

    security: Mapped["Security"] = relationship(back_populates="tax_lots")
    disposals: Mapped[list["TaxLotDisposal"]] = relationship(
        back_populates="tax_lot", cascade="all, delete-orphan", lazy="selectin"
    )

class TaxLotDisposal(Base):
    __tablename__ = "tax_lot_disposals"
    tax_lot_id: Mapped[int] = mapped_column(ForeignKey("tax_lots.id"))
    sell_transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"))
    disposal_date: Mapped[date] = mapped_column(Date)
    quantity_disposed: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    sale_price_per_unit: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    sale_proceeds: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    cost_of_acquisition: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    realized_gain_loss: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    holding_period_days: Mapped[int] = mapped_column(Integer)
    gain_type: Mapped[str] = mapped_column(String)
    grandfathering_applicable: Mapped[bool] = mapped_column(Boolean, default=False)
    grandfathered_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)

    tax_lot: Mapped["TaxLot"] = relationship(back_populates="disposals")

class FoContract(Base):
    __tablename__ = "fo_contracts"
    underlying_security_id: Mapped[int] = mapped_column(ForeignKey("securities.id"))
    contract_type: Mapped[str] = mapped_column(String)
    expiry_date: Mapped[date] = mapped_column(Date)
    strike_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    lot_size: Mapped[int] = mapped_column(Integer)
    exchange: Mapped[str] = mapped_column(String, default="NSE")
    contract_symbol: Mapped[str] = mapped_column(String, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class FoPosition(Base):
    __tablename__ = "fo_positions"
    fo_contract_id: Mapped[int] = mapped_column(ForeignKey("fo_contracts.id"))
    brokerage_account_id: Mapped[int] = mapped_column(ForeignKey("brokerage_accounts.id"))
    position_type: Mapped[str] = mapped_column(String)
    quantity_lots: Mapped[int] = mapped_column(Integer)
    quantity_units: Mapped[int] = mapped_column(Integer)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    entry_date: Mapped[date] = mapped_column(Date)
    entry_transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"))
    exit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    exit_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    exit_transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.id"), nullable=True)
    margin_blocked: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    premium_paid: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    premium_received: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    realized_pnl: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    settlement_type: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="OPEN")

class HoldingsSummary(Base):
    __tablename__ = "holdings_summary"
    security_id: Mapped[int] = mapped_column(ForeignKey("securities.id"))
    brokerage_account_id: Mapped[int] = mapped_column(ForeignKey("brokerage_accounts.id"))
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    total_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    average_cost_per_unit: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    total_invested_value: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    latest_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    latest_price_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    current_market_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    unrealized_pnl: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    unrealized_pnl_pct: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    absolute_return_pct: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    day_change: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    day_change_pct: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    last_recomputed_at: Mapped[datetime] = mapped_column(DateTime)
```

### 7.4 Transactions and Journal Entries

```python
class Transaction(Base):
    __tablename__ = "transactions"
    transaction_date: Mapped[date] = mapped_column(Date)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    transaction_number: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    transaction_type: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String)
    payee_id: Mapped[int | None] = mapped_column(ForeignKey("payees.id"), nullable=True)
    reference_number: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="CONFIRMED")
    is_void: Mapped[bool] = mapped_column(Boolean, default=False)
    void_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    voided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reversal_of_transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.id"), nullable=True)
    import_batch_id: Mapped[int | None] = mapped_column(ForeignKey("import_batches.id"), nullable=True)
    recurring_transaction_id: Mapped[int | None] = mapped_column(ForeignKey("recurring_transactions.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    
    # Cascade relationships — saving Transaction saves all children
    lines: Mapped[list["TransactionLine"]] = relationship(
        back_populates="transaction", cascade="all, delete-orphan", lazy="selectin"
    )
    charges: Mapped[list["TransactionCharge"]] = relationship(
        back_populates="transaction", cascade="all, delete-orphan", lazy="selectin"
    )
    attachments: Mapped[list["Attachment"]] = relationship(
        back_populates="transaction", cascade="all, delete-orphan", lazy="selectin"
    )

class TransactionLine(Base):
    __tablename__ = "transaction_lines"
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"))
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    line_type: Mapped[str] = mapped_column(String) # DEBIT or CREDIT
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    security_id: Mapped[int | None] = mapped_column(ForeignKey("securities.id"), nullable=True)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    price_per_unit: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    tax_lot_id: Mapped[int | None] = mapped_column(ForeignKey("tax_lots.id"), nullable=True)
    currency_code: Mapped[str] = mapped_column(String, default="INR")
    exchange_rate: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=1)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    
    transaction: Mapped["Transaction"] = relationship(back_populates="lines")

class TransactionCharge(Base):
    __tablename__ = "transaction_charges"
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"))
    charge_type: Mapped[str] = mapped_column(String)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    description: Mapped[str | None] = mapped_column(String, nullable=True)

    transaction: Mapped["Transaction"] = relationship(back_populates="charges")

class Attachment(Base):
    __tablename__ = "attachments"
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"))
    file_name: Mapped[str] = mapped_column(String)
    file_path: Mapped[str] = mapped_column(String)
    file_type: Mapped[str] = mapped_column(String)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)

    transaction: Mapped["Transaction"] = relationship(back_populates="attachments")
```

### 7.5 Categories, Tags, and Payees

```python
class Payee(Base):
    __tablename__ = "payees"
    name: Mapped[str] = mapped_column(String)
    default_account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    payee_type: Mapped[str] = mapped_column(String, default="OTHER")
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class Tag(Base):
    __tablename__ = "tags"
    name: Mapped[str] = mapped_column(String, unique=True)
    color: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class TransactionTag(Base):
    __tablename__ = "transaction_tags"
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id"), primary_key=True)
```

### 7.6 Recurring Transactions

```python
class RecurringTransaction(Base):
    __tablename__ = "recurring_transactions"
    template_name: Mapped[str] = mapped_column(String)
    transaction_type: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    payee_id: Mapped[int | None] = mapped_column(ForeignKey("payees.id"), nullable=True)
    estimated_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    is_amount_fixed: Mapped[bool] = mapped_column(Boolean, default=True)
    frequency: Mapped[str] = mapped_column(String)
    interval_value: Mapped[int] = mapped_column(Integer, default=1)
    day_of_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    day_of_week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    month_of_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_occurrence_date: Mapped[date] = mapped_column(Date)
    last_generated_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_occurrences: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completed_occurrences: Mapped[int] = mapped_column(Integer, default=0)
    auto_confirm: Mapped[bool] = mapped_column(Boolean, default=False)
    security_id: Mapped[int | None] = mapped_column(ForeignKey("securities.id"), nullable=True)
    sip_units: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    goal_id: Mapped[int | None] = mapped_column(ForeignKey("goals.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Cascade: saving recurring template saves its lines
    lines: Mapped[list["RecurringTransactionLine"]] = relationship(
        back_populates="recurring_transaction", cascade="all, delete-orphan", lazy="selectin"
    )

class RecurringTransactionLine(Base):
    __tablename__ = "recurring_transaction_lines"
    recurring_transaction_id: Mapped[int] = mapped_column(ForeignKey("recurring_transactions.id"))
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    line_type: Mapped[str] = mapped_column(String)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)

    recurring_transaction: Mapped["RecurringTransaction"] = relationship(back_populates="lines")
```

### 7.7 Goals

```python
class Goal(Base):
    __tablename__ = "goals"
    name: Mapped[str] = mapped_column(String)
    goal_type: Mapped[str] = mapped_column(String)
    target_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    current_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    start_date: Mapped[date] = mapped_column(Date)
    priority: Mapped[str] = mapped_column(String, default="MEDIUM")
    status: Mapped[str] = mapped_column(String, default="ACTIVE")
    icon: Mapped[str | None] = mapped_column(String, nullable=True)
    color: Mapped[str | None] = mapped_column(String, nullable=True)
    sip_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    expected_return_rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    achieved_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Cascade relationships
    milestones: Mapped[list["GoalMilestone"]] = relationship(
        back_populates="goal", cascade="all, delete-orphan", lazy="selectin"
    )
    contributions: Mapped[list["GoalContribution"]] = relationship(
        back_populates="goal", cascade="all, delete-orphan", lazy="selectin"
    )
    account_mappings: Mapped[list["GoalAccountMapping"]] = relationship(
        back_populates="goal", cascade="all, delete-orphan", lazy="selectin"
    )

class GoalAccountMapping(Base):
    __tablename__ = "goal_account_mappings"
    goal_id: Mapped[int] = mapped_column(ForeignKey("goals.id"))
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    allocation_percentage: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=100)

    goal: Mapped["Goal"] = relationship(back_populates="account_mappings")

class GoalMilestone(Base):
    __tablename__ = "goal_milestones"
    goal_id: Mapped[int] = mapped_column(ForeignKey("goals.id"))
    name: Mapped[str] = mapped_column(String)
    target_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    achieved_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String, default="PENDING")
    display_order: Mapped[int] = mapped_column(Integer, default=0)

    goal: Mapped["Goal"] = relationship(back_populates="milestones")

class GoalContribution(Base):
    __tablename__ = "goal_contributions"
    goal_id: Mapped[int] = mapped_column(ForeignKey("goals.id"))
    transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.id"), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    contribution_date: Mapped[date] = mapped_column(Date)
    contribution_type: Mapped[str] = mapped_column(String, default="MANUAL")
    notes: Mapped[str | None] = mapped_column(String, nullable=True)

    goal: Mapped["Goal"] = relationship(back_populates="contributions")
```

### 7.8 Budgets

```python
class Budget(Base):
    __tablename__ = "budgets"
    name: Mapped[str] = mapped_column(String)
    period_type: Mapped[str] = mapped_column(String)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    total_budgeted: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    total_spent: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)

    # Cascade: saving budget saves all items
    items: Mapped[list["BudgetItem"]] = relationship(
        back_populates="budget", cascade="all, delete-orphan", lazy="selectin"
    )

class BudgetItem(Base):
    __tablename__ = "budget_items"
    budget_id: Mapped[int] = mapped_column(ForeignKey("budgets.id"))
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    budgeted_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    spent_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    rollover_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    rollover_unused: Mapped[bool] = mapped_column(Boolean, default=False)
    alert_threshold_pct: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), default=80)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)

    budget: Mapped["Budget"] = relationship(back_populates="items")
```

### 7.9 Reporting and Snapshots

```python
class MonthlySnapshot(Base):
    __tablename__ = "monthly_snapshots"
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    snapshot_year: Mapped[int] = mapped_column(Integer)
    snapshot_month: Mapped[int] = mapped_column(Integer)
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    total_debits: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    total_credits: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    closing_balance: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    transaction_count: Mapped[int] = mapped_column(Integer, default=0)

class NetWorthHistory(Base):
    __tablename__ = "net_worth_history"
    snapshot_date: Mapped[date] = mapped_column(Date)
    total_assets: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    total_liabilities: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    net_worth: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    liquid_assets: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    investment_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)

class SavedReport(Base):
    __tablename__ = "saved_reports"
    name: Mapped[str] = mapped_column(String)
    report_type: Mapped[str] = mapped_column(String)
    parameters_json: Mapped[str] = mapped_column(String)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

### 7.10 Import and Reconciliation

```python
class ImportProfile(Base):
    __tablename__ = "import_profiles"
    name: Mapped[str] = mapped_column(String)
    institution_id: Mapped[int | None] = mapped_column(ForeignKey("financial_institutions.id"), nullable=True)
    source_type: Mapped[str] = mapped_column(String)
    file_format: Mapped[str] = mapped_column(String)
    column_mapping_json: Mapped[str | None] = mapped_column(String, nullable=True)
    date_format: Mapped[str | None] = mapped_column(String, default="DD/MM/YYYY")
    delimiter: Mapped[str | None] = mapped_column(String, default=",")
    skip_header_rows: Mapped[int | None] = mapped_column(Integer, default=1)
    skip_footer_rows: Mapped[int | None] = mapped_column(Integer, default=0)
    encoding: Mapped[str | None] = mapped_column(String, default="UTF-8")
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class ImportBatch(Base):
    __tablename__ = "import_batches"
    import_profile_id: Mapped[int | None] = mapped_column(ForeignKey("import_profiles.id"), nullable=True)
    file_name: Mapped[str] = mapped_column(String)
    file_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    source_type: Mapped[str] = mapped_column(String)
    import_started_at: Mapped[datetime] = mapped_column(DateTime)
    import_completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String, default="IN_PROGRESS")
    total_records: Mapped[int | None] = mapped_column(Integer, default=0)
    imported_count: Mapped[int | None] = mapped_column(Integer, default=0)
    duplicate_count: Mapped[int | None] = mapped_column(Integer, default=0)
    skipped_count: Mapped[int | None] = mapped_column(Integer, default=0)
    error_count: Mapped[int | None] = mapped_column(Integer, default=0)
    error_log: Mapped[str | None] = mapped_column(String, nullable=True)
    target_account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"), nullable=True)

    # Cascade: import batch owns its reconciliation records
    reconciliation_records: Mapped[list["ReconciliationRecord"]] = relationship(
        back_populates="import_batch", cascade="all, delete-orphan", lazy="selectin"
    )

class ReconciliationRecord(Base):
    __tablename__ = "reconciliation_records"
    import_batch_id: Mapped[int] = mapped_column(ForeignKey("import_batches.id"))
    external_date: Mapped[date] = mapped_column(Date)
    external_description: Mapped[str] = mapped_column(String)
    external_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    external_reference: Mapped[str | None] = mapped_column(String, nullable=True)
    external_balance: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    match_status: Mapped[str] = mapped_column(String, default="UNMATCHED")
    matched_transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.id"), nullable=True)
    created_transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.id"), nullable=True)
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    user_action: Mapped[str | None] = mapped_column(String, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    import_batch: Mapped["ImportBatch"] = relationship(back_populates="reconciliation_records")
```

### 7.11 Tax Management

```python
class TaxSection(Base):
    __tablename__ = "tax_sections"
    section_code: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    max_deduction_limit: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    applicable_regime: Mapped[str] = mapped_column(String, default="OLD")
    financial_year: Mapped[str] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Cascade
    mappings: Mapped[list["TaxSectionMapping"]] = relationship(
        back_populates="tax_section", cascade="all, delete-orphan", lazy="selectin"
    )

class TaxSectionMapping(Base):
    __tablename__ = "tax_section_mappings"
    tax_section_id: Mapped[int] = mapped_column(ForeignKey("tax_sections.id"))
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    security_id: Mapped[int | None] = mapped_column(ForeignKey("securities.id"), nullable=True)
    transaction_type: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)

    tax_section: Mapped["TaxSection"] = relationship(back_populates="mappings")
```

### 7.12 System, Configuration, and Audit

```python
class AppSetting(Base):
    __tablename__ = "app_settings"
    setting_key: Mapped[str] = mapped_column(String, unique=True)
    setting_value: Mapped[str | None] = mapped_column(String, nullable=True)
    setting_type: Mapped[str] = mapped_column(String, default="STRING")
    category: Mapped[str] = mapped_column(String, default="GENERAL")
    description: Mapped[str | None] = mapped_column(String, nullable=True)

class AuditLog(Base):
    __tablename__ = "audit_log"
    entity_type: Mapped[str] = mapped_column(String)
    entity_id: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String)
    changes_json: Mapped[str | None] = mapped_column(String, nullable=True)
    summary: Mapped[str | None] = mapped_column(String, nullable=True)
    source: Mapped[str] = mapped_column(String, default="USER")
    ip_address: Mapped[str | None] = mapped_column(String, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime)

class Notification(Base):
    __tablename__ = "notifications"
    notification_type: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    message: Mapped[str] = mapped_column(String)
    related_entity_type: Mapped[str | None] = mapped_column(String, nullable=True)
    related_entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    priority: Mapped[str] = mapped_column(String, default="MEDIUM")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    scheduled_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    action_url: Mapped[str | None] = mapped_column(String, nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class BackupHistory(Base):
    __tablename__ = "backup_history"
    backup_type: Mapped[str] = mapped_column(String)
    file_path: Mapped[str] = mapped_column(String)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    record_counts_json: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="COMPLETED")
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
```

## 5.3 TransactionRepository — Cascade-Aware Domain Repository

This repository demonstrates the cascade pattern for atomically saving a Transaction with all its children (lines, charges, attachments).

```python
# db/repositories/transaction_repo.py
from decimal import Decimal
from datetime import date
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select
from db.models.transactions import Transaction, TransactionLine
from db.repositories.base import BaseRepository

class TransactionRepository(BaseRepository[Transaction]):
    def __init__(self, session: Session):
        super().__init__(Transaction, session)

    def create_with_children(self, transaction: Transaction) -> Transaction:
        """
        Atomically persist a Transaction + all Lines/Charges/Attachments.
        Leverages SQLAlchemy cascade: session.add(parent) flushes children.
        
        Usage:
            txn = Transaction(transaction_date=date.today(), ...)
            txn.lines.append(TransactionLine(account_id=1001, line_type="DEBIT", amount=Decimal("5000")))
            txn.lines.append(TransactionLine(account_id=4110, line_type="CREDIT", amount=Decimal("5000")))
            txn.charges.append(TransactionCharge(...))  # optional
            saved = repo.create_with_children(txn)  # atomic save of parent + all children
        """
        self._validate_balanced(transaction)
        self.session.add(transaction)
        self.session.flush()
        return transaction

    def get_with_lines(self, transaction_id: int) -> Transaction | None:
        """Eager-load lines to avoid N+1 queries."""
        stmt = (
            select(Transaction)
            .options(joinedload(Transaction.lines))
            .where(Transaction.id == transaction_id)
        )
        return self.session.scalar(stmt)

    def get_by_date_range(
        self, start_date: date, end_date: date, status: str | None = None
    ) -> list[Transaction]:
        stmt = (
            select(Transaction)
            .options(joinedload(Transaction.lines))
            .where(Transaction.transaction_date.between(start_date, end_date))
        )
        if status:
            stmt = stmt.where(Transaction.status == status)
        stmt = stmt.order_by(Transaction.transaction_date.desc())
        return list(self.session.scalars(stmt).unique().all())

    @staticmethod
    def _validate_balanced(transaction: Transaction) -> None:
        """Enforce double-entry invariant before persistence."""
        if len(transaction.lines) < 2:
            raise ValueError("Transaction must have at least 2 lines (double-entry)")
        total_debit = sum(
            line.amount for line in transaction.lines if line.line_type == "DEBIT"
        )
        total_credit = sum(
            line.amount for line in transaction.lines if line.line_type == "CREDIT"
        )
        if total_debit != total_credit:
            raise ValueError(
                f"Transaction is unbalanced: debits={total_debit}, credits={total_credit}"
            )
```

---

## 8. Reporting Repository Layer

Read-only repository for reporting queries. Uses `monthly_snapshots` for performance — find the nearest snapshot and sum only the delta. This avoids scanning all transaction lines from inception.

```python
# db/repositories/reporting_repo.py
from decimal import Decimal
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, case
from db.models.transactions import TransactionLine, Transaction
from db.models.accounts import Account
from db.models.reporting import MonthlySnapshot, NetWorthHistory

class ReportingRepository:
    """Read-only repository for reporting queries. No create/update/delete."""

    def __init__(self, session: Session):
        self.session = session

    def get_account_balance_at_date(
        self, account_id: int, as_of_date: date
    ) -> Decimal:
        """
        Efficient balance calculation: snapshot + delta.
        1. Find the latest snapshot at or before as_of_date
        2. Sum transaction lines between snapshot date and as_of_date
        """
        # Step 1: Find nearest snapshot
        snapshot_stmt = (
            select(MonthlySnapshot)
            .where(MonthlySnapshot.account_id == account_id)
            .where(
                (MonthlySnapshot.snapshot_year * 100 + MonthlySnapshot.snapshot_month)
                <= (as_of_date.year * 100 + as_of_date.month)
            )
            .order_by(
                MonthlySnapshot.snapshot_year.desc(),
                MonthlySnapshot.snapshot_month.desc(),
            )
            .limit(1)
        )
        snapshot = self.session.scalar(snapshot_stmt)

        if snapshot:
            base_balance = snapshot.closing_balance
            delta_start = date(snapshot.snapshot_year, snapshot.snapshot_month, 1)
        else:
            base_balance = Decimal("0")
            delta_start = date(2000, 1, 1)  # effectively "from inception"

        # Step 2: Sum delta from snapshot end to as_of_date
        delta_stmt = (
            select(
                func.coalesce(
                    func.sum(
                        case(
                            (TransactionLine.line_type == "DEBIT", TransactionLine.amount),
                            else_=Decimal("0"),
                        )
                    ),
                    Decimal("0"),
                ).label("total_debits"),
                func.coalesce(
                    func.sum(
                        case(
                            (TransactionLine.line_type == "CREDIT", TransactionLine.amount),
                            else_=Decimal("0"),
                        )
                    ),
                    Decimal("0"),
                ).label("total_credits"),
            )
            .join(Transaction, TransactionLine.transaction_id == Transaction.id)
            .where(
                and_(
                    TransactionLine.account_id == account_id,
                    Transaction.transaction_date > delta_start,
                    Transaction.transaction_date <= as_of_date,
                    Transaction.is_void == False,
                )
            )
        )
        result = self.session.execute(delta_stmt).one()

        # Step 3: Get account type to determine normal balance direction
        account = self.session.get(Account, account_id)
        if account and account.account_type in ("ASSET", "EXPENSE"):
            return base_balance + result.total_debits - result.total_credits
        else:
            return base_balance + result.total_credits - result.total_debits

    def get_income_expense_summary(
        self, start_date: date, end_date: date
    ) -> list[dict]:
        """
        Aggregate income and expense by account for a date range.
        Returns: [{"account_id": int, "account_name": str, "account_type": str, "total": Decimal}]
        """
        stmt = (
            select(
                Account.id.label("account_id"),
                Account.name.label("account_name"),
                Account.account_type,
                func.sum(TransactionLine.amount).label("total"),
            )
            .join(TransactionLine, TransactionLine.account_id == Account.id)
            .join(Transaction, TransactionLine.transaction_id == Transaction.id)
            .where(
                and_(
                    Account.account_type.in_(["INCOME", "EXPENSE"]),
                    Transaction.transaction_date.between(start_date, end_date),
                    Transaction.is_void == False,
                )
            )
            .group_by(Account.id, Account.name, Account.account_type)
            .order_by(Account.account_type, Account.code)
        )
        rows = self.session.execute(stmt).all()
        return [
            {
                "account_id": r.account_id,
                "account_name": r.account_name,
                "account_type": r.account_type,
                "total": r.total,
            }
            for r in rows
        ]

    def get_net_worth_at_date(self, as_of_date: date) -> dict:
        """Compute net worth = total assets - total liabilities at a given date."""
        asset_accounts = self.session.scalars(
            select(Account.id).where(Account.account_type == "ASSET")
        ).all()
        liability_accounts = self.session.scalars(
            select(Account.id).where(Account.account_type == "LIABILITY")
        ).all()

        total_assets = sum(
            self.get_account_balance_at_date(aid, as_of_date) for aid in asset_accounts
        )
        total_liabilities = sum(
            self.get_account_balance_at_date(lid, as_of_date) for lid in liability_accounts
        )
        return {
            "as_of_date": as_of_date,
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "net_worth": total_assets - total_liabilities,
        }
```

---

## 9. TDD Strategy & Test Infrastructure

### 9.1 Test Directory Structure
```text
tests/
├── conftest.py              # Shared fixtures: in-memory DB, session, factories
├── unit/
│   ├── test_models.py       # Phase 1: Model creation, column types
│   ├── test_relationships.py # Phase 2: Cascade saves, eager loading
│   ├── test_base_repo.py    # Phase 3: Generic CRUD via BaseRepository
│   ├── test_account_repo.py # Phase 4: Domain-specific repository queries
│   ├── test_transaction_repo.py # Phase 5: Cascade save, balance validation
│   ├── test_unit_of_work.py # Phase 6: Atomic multi-entity operations
│   └── test_reporting_repo.py # Phase 7: Reporting queries, snapshots
└── factories.py             # Model factories for test data creation
```

### 9.2 Test Database Configuration (`conftest.py`)
```python
# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models.base import Base

@pytest.fixture(scope="session")
def engine():
    """In-memory SQLite for fast, isolated tests."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    return engine

@pytest.fixture
def session(engine):
    """Per-test session with automatic rollback — each test starts clean."""
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()
```

### 9.3 Model Factories
```python
# tests/factories.py
from datetime import date
from decimal import Decimal
from db.models.accounts import Account
from db.models.transactions import Transaction, TransactionLine

class AccountFactory:
    _counter = 0

    @classmethod
    def create(cls, session, **overrides) -> Account:
        cls._counter += 1
        defaults = {
            "code": f"ACC-{cls._counter:04d}",
            "name": f"Test Account {cls._counter}",
            "account_type": "ASSET",
            "normal_balance": "DEBIT",
        }
        defaults.update(overrides)
        account = Account(**defaults)
        session.add(account)
        session.flush()
        return account

class TransactionFactory:
    @classmethod
    def create_balanced(
        cls, session, debit_account_id: int, credit_account_id: int,
        amount: Decimal = Decimal("1000.00"), **overrides
    ) -> Transaction:
        defaults = {
            "transaction_date": date.today(),
            "transaction_type": "JOURNAL",
            "description": "Test transaction",
        }
        defaults.update(overrides)
        txn = Transaction(**defaults)
        txn.lines.append(TransactionLine(
            account_id=debit_account_id, line_type="DEBIT", amount=amount
        ))
        txn.lines.append(TransactionLine(
            account_id=credit_account_id, line_type="CREDIT", amount=amount
        ))
        session.add(txn)
        session.flush()
        return txn
```

### 9.4 Phased TDD Execution Plan

| Phase | Focus | Key Assertions |
|-------|-------|-----------------|
| 1. Models | Table creation, column types | `session.add(Account(...))` succeeds, `Numeric` columns store `Decimal` correctly |
| 2. Relationships | Cascade saves, eager loading | `session.add(txn)` also persists `txn.lines` without explicit `session.add()` on lines |
| 3. Base CRUD | `BaseRepository` generic ops | `create`, `get_by_id`, `list_paginated`, `update`, `delete` return expected objects |
| 4. Domain Repos | Entity-specific queries | `AccountRepo.find_by_code()`, `get_leaf_nodes_for_type()` return correct subsets |
| 5. Transaction Repo | Cascade save + validation | `create_with_children()` persists parent+children; unbalanced transaction raises `ValueError` |
| 6. Unit of Work | Atomic rollback | Exception in `unit_of_work()` block rolls back ALL changes; no partial state |
| 7. Reporting | Balance at date, I&E summary | `get_account_balance_at_date()` returns correct balance; snapshot optimization works |

### 9.5 Example Test: Cascade Save
```python
# tests/unit/test_transaction_repo.py
from decimal import Decimal
from datetime import date

def test_create_transaction_with_lines_cascades(session):
    """Phase 2+5: Saving parent Transaction cascades to TransactionLines."""
    from db.repositories.transaction_repo import TransactionRepository
    from db.models.transactions import Transaction, TransactionLine
    from tests.factories import AccountFactory

    # Arrange: create two accounts
    cash = AccountFactory.create(session, code="1101", account_type="ASSET")
    rent = AccountFactory.create(session, code="4110", account_type="EXPENSE")

    # Act: create transaction with lines via cascade
    repo = TransactionRepository(session)
    txn = Transaction(
        transaction_date=date(2026, 3, 1),
        transaction_type="EXPENSE",
        description="March Rent",
    )
    txn.lines.append(TransactionLine(
        account_id=rent.id, line_type="DEBIT", amount=Decimal("25000.00")
    ))
    txn.lines.append(TransactionLine(
        account_id=cash.id, line_type="CREDIT", amount=Decimal("25000.00")
    ))
    saved = repo.create_with_children(txn)

    # Assert: parent and children are persisted
    assert saved.id is not None
    assert len(saved.lines) == 2
    assert all(line.id is not None for line in saved.lines)

def test_unbalanced_transaction_raises_error(session):
    """Phase 5: Double-entry validation rejects unbalanced transactions."""
    from db.repositories.transaction_repo import TransactionRepository
    from db.models.transactions import Transaction, TransactionLine
    import pytest

    repo = TransactionRepository(session)
    txn = Transaction(
        transaction_date=date(2026, 3, 1),
        transaction_type="JOURNAL",
        description="Bad transaction",
    )
    txn.lines.append(TransactionLine(
        account_id=1, line_type="DEBIT", amount=Decimal("5000.00")
    ))
    txn.lines.append(TransactionLine(
        account_id=2, line_type="CREDIT", amount=Decimal("3000.00")
    ))
    with pytest.raises(ValueError, match="unbalanced"):
        repo.create_with_children(txn)
```

### 9.6 Example Test: Reporting
```python
# tests/unit/test_reporting_repo.py
from decimal import Decimal
from datetime import date

def test_income_expense_summary(session):
    """Phase 7: I&E summary aggregates by account type within date range."""
    from db.repositories.reporting_repo import ReportingRepository
    from tests.factories import AccountFactory, TransactionFactory

    salary = AccountFactory.create(session, code="3110", account_type="INCOME")
    rent = AccountFactory.create(session, code="4110", account_type="EXPENSE")
    cash = AccountFactory.create(session, code="1101", account_type="ASSET")

    TransactionFactory.create_balanced(
        session, debit_account_id=cash.id, credit_account_id=salary.id,
        amount=Decimal("50000"), transaction_type="INCOME",
        transaction_date=date(2026, 3, 1), description="Salary"
    )
    TransactionFactory.create_balanced(
        session, debit_account_id=rent.id, credit_account_id=cash.id,
        amount=Decimal("20000"), transaction_type="EXPENSE",
        transaction_date=date(2026, 3, 5), description="Rent"
    )

    repo = ReportingRepository(session)
    summary = repo.get_income_expense_summary(date(2026, 3, 1), date(2026, 3, 31))

    income_items = [s for s in summary if s["account_type"] == "INCOME"]
    expense_items = [s for s in summary if s["account_type"] == "EXPENSE"]
    assert len(income_items) >= 1
    assert len(expense_items) >= 1
```
