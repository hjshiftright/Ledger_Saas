This is a great architectural question. The Python ecosystem doesn't have a single monolithic equivalent to Spring Boot/Spring Data, but there are composable libraries that, together, give you the same capabilities — and in some cases, a framework that bakes the repository pattern in natively.

## The Landscape: Spring Concepts → Python Equivalents

| Spring Concept | Python Equivalent |
|---|---|
| Spring Data JPA Repositories | Manual Repository pattern on SQLAlchemy, **or** Litestar's built-in `SQLAlchemyRepository` |
| `@Transactional` | SQLAlchemy `Session` + context managers / decorators |
| HikariCP (connection pool) | SQLAlchemy's built-in `QueuePool` (production-grade) |
| Spring IoC / `@Autowired` | FastAPI `Depends()`, or the `dependency-injector` library |
| `@Service` layer | Plain Python classes, wired via DI |
| Spring Boot auto-config | FastAPI/Litestar app lifespan events |

---

## Option 1: FastAPI + SQLAlchemy + Manual Repository Pattern (Most Common)

This is the dominant approach in the Python ecosystem. You build the repository layer yourself, but SQLAlchemy gives you all the primitives.

### Database Engine & Session Factory (connection pooling + transaction management)

```python
# db/engine.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

engine = create_engine(
    "sqlite:///ledger.db",
    pool_size=5,              # connection pool
    max_overflow=10,
    pool_pre_ping=True,       # health-check connections
    echo=False,
)

SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_session():
    """FastAPI dependency — one session per request, auto-commit/rollback."""
    session = SessionFactory()
    try:
        yield session
        session.commit()       # auto-commit if no exception
    except Exception:
        session.rollback()     # auto-rollback on error
        raise
    finally:
        session.close()
```

### ORM Model

```python
# db/models.py
from sqlalchemy import String, Integer, Numeric, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.engine import Base
from datetime import datetime
from decimal import Decimal


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    account_type: Mapped[str] = mapped_column(String(20))  # asset, liability, etc.
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    entries: Mapped[list["JournalEntry"]] = relationship(back_populates="account")
```

### Generic Base Repository (comparable to `JpaRepository<T, ID>`)

```python
# db/repositories/base.py
from typing import TypeVar, Generic, Type, Sequence
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from db.engine import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """Generic repository providing standard CRUD operations.
    
    Comparable to Spring Data's CrudRepository / JpaRepository.
    """

    def __init__(self, model: Type[T], session: Session):
        self.model = model
        self.session = session

    def get_by_id(self, entity_id: int) -> T | None:
        return self.session.get(self.model, entity_id)

    def get_by_id_or_raise(self, entity_id: int) -> T:
        entity = self.get_by_id(entity_id)
        if entity is None:
            raise EntityNotFoundError(self.model.__name__, entity_id)
        return entity

    def list_all(self) -> Sequence[T]:
        stmt = select(self.model)
        return self.session.scalars(stmt).all()

    def list_paginated(self, offset: int = 0, limit: int = 50) -> Sequence[T]:
        stmt = select(self.model).offset(offset).limit(limit)
        return self.session.scalars(stmt).all()

    def count(self) -> int:
        stmt = select(func.count()).select_from(self.model)
        return self.session.scalar(stmt) or 0

    def create(self, entity: T) -> T:
        self.session.add(entity)
        self.session.flush()  # assigns ID without committing txn
        return entity

    def create_many(self, entities: list[T]) -> list[T]:
        self.session.add_all(entities)
        self.session.flush()
        return entities

    def update(self, entity: T) -> T:
        entity = self.session.merge(entity)
        self.session.flush()
        return entity

    def delete(self, entity: T) -> None:
        self.session.delete(entity)
        self.session.flush()

    def delete_by_id(self, entity_id: int) -> None:
        entity = self.get_by_id_or_raise(entity_id)
        self.delete(entity)


class EntityNotFoundError(Exception):
    def __init__(self, entity_name: str, entity_id: int):
        self.entity_name = entity_name
        self.entity_id = entity_id
        super().__init__(f"{entity_name} with id {entity_id} not found")
```

### Domain-Specific Repository (comparable to your custom `@Repository` interfaces)

```python
# db/repositories/account_repository.py
from sqlalchemy import select
from sqlalchemy.orm import Session
from db.models import Account
from db.repositories.base import BaseRepository


class AccountRepository(BaseRepository[Account]):

    def __init__(self, session: Session):
        super().__init__(Account, session)

    def find_by_code(self, code: str) -> Account | None:
        stmt = select(Account).where(Account.code == code)
        return self.session.scalar(stmt)

    def find_by_type(self, account_type: str) -> list[Account]:
        stmt = (
            select(Account)
            .where(Account.account_type == account_type)
            .where(Account.is_active.is_(True))
            .order_by(Account.code)
        )
        return list(self.session.scalars(stmt).all())

    def find_active(self) -> list[Account]:
        stmt = (
            select(Account)
            .where(Account.is_active.is_(True))
            .order_by(Account.account_type, Account.code)
        )
        return list(self.session.scalars(stmt).all())

    def exists_by_code(self, code: str) -> bool:
        stmt = select(Account.id).where(Account.code == code)
        return self.session.scalar(stmt) is not None
```

### Service Layer (comparable to `@Service`)

```python
# services/account_service.py
from sqlalchemy.orm import Session
from db.repositories.account_repository import AccountRepository
from db.models import Account
from schemas.account import AccountCreate, AccountUpdate


class AccountService:
    """Business logic layer — sits between API and repository.
    
    The session (and therefore the transaction boundary) is owned 
    by the FastAPI dependency. The service operates within that 
    transaction. Comparable to a Spring @Service with @Transactional.
    """

    def __init__(self, session: Session):
        self.repo = AccountRepository(session)
        self.session = session

    def create_account(self, data: AccountCreate) -> Account:
        if self.repo.exists_by_code(data.code):
            raise ValueError(f"Account code '{data.code}' already exists")

        account = Account(
            code=data.code,
            name=data.name,
            account_type=data.account_type,
            currency=data.currency,
        )
        return self.repo.create(account)

    def get_accounts_by_type(self, account_type: str) -> list[Account]:
        valid_types = {"asset", "liability", "income", "expense", "equity"}
        if account_type not in valid_types:
            raise ValueError(f"Invalid account type: {account_type}")
        return self.repo.find_by_type(account_type)

    def deactivate_account(self, account_id: int) -> Account:
        account = self.repo.get_by_id_or_raise(account_id)
        # Business rule: don't deactivate if account has unreconciled entries
        account.is_active = False
        return self.repo.update(account)
```

### FastAPI Route Layer (comparable to `@RestController`)

```python
# api/routes/accounts.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.engine import get_session
from services.account_service import AccountService
from schemas.account import AccountCreate, AccountResponse

router = APIRouter(prefix="/api/v1/accounts", tags=["accounts"])


def get_account_service(session: Session = Depends(get_session)) -> AccountService:
    """Dependency injection — comparable to Spring's @Autowired."""
    return AccountService(session)


@router.post("/", response_model=AccountResponse, status_code=201)
def create_account(
    data: AccountCreate,
    service: AccountService = Depends(get_account_service),
):
    return service.create_account(data)


@router.get("/by-type/{account_type}", response_model=list[AccountResponse])
def list_by_type(
    account_type: str,
    service: AccountService = Depends(get_account_service),
):
    return service.get_accounts_by_type(account_type)
```

### Transaction Flow

```
HTTP Request
  → FastAPI route
    → Depends(get_session) opens Session + begins transaction
      → Depends(get_account_service) creates service with that session
        → service calls repository methods
        → repository calls session.flush() (writes to DB, no commit yet)
      ← service returns
    ← if no exception: session.commit()
    ← if exception: session.rollback()
  ← response sent
```

This gives you the same guarantee as Spring's `@Transactional` — one transaction per request, automatic rollback on failure.

---

## Option 2: Litestar — The Most Spring-Like Framework in Python

If you want something that **ships with** a built-in repository pattern rather than building it yourself, **Litestar** (formerly Starlite) is the closest thing to Spring Data in the Python ecosystem. It has an official `litestar.contrib.sqlalchemy` module with production-ready repository and service base classes.

```python
# Using Litestar's built-in repository
from litestar.contrib.sqlalchemy.repository import SQLAlchemySyncRepository
from db.models import Account


class AccountRepository(SQLAlchemySyncRepository[Account]):
    """All standard CRUD methods are inherited automatically.
    
    Provides: get, list, create, update, upsert, delete,
    list_and_count (pagination), exists, count, and filter operations.
    """
    model_type = Account

    # Add only your custom queries
    async def find_by_type(self, account_type: str) -> list[Account]:
        return await self.list(Account.account_type == account_type)
```

Litestar also provides a `SQLAlchemySyncRepository` for non-async usage, built-in pagination DTOs, and a service layer base class. It handles session lifecycle and transaction management through its dependency injection system, very similar to how Spring manages the `EntityManager`.

---

## Option 3: The `dependency-injector` Library for Full IoC

If you want Spring-style IoC containers — where you define all your wiring in one place — the `dependency-injector` library gives you exactly that:

```python
# containers.py
from dependency_injector import containers, providers
from db.engine import SessionFactory
from db.repositories.account_repository import AccountRepository
from services.account_service import AccountService


class Container(containers.DeclarativeContainer):
    """Comparable to a Spring @Configuration class."""

    session = providers.Resource(get_session)  # scoped per request

    account_repository = providers.Factory(
        AccountRepository,
        session=session,
    )

    account_service = providers.Factory(
        AccountService,
        session=session,
    )
```

This integrates with FastAPI via `@inject` decorators.

---

## My Recommendation for Your Ledger Project

Given that you're building a personal finance ledger (not a massive enterprise system), I'd suggest **FastAPI + SQLAlchemy + manual repository pattern** (Option 1) for these reasons:

**It's the right level of structure.** You get clean separation (Route → Service → Repository → Session), transaction management, and connection pooling without pulling in a heavyweight framework. The manual repository pattern in Python is roughly 50-60 lines for the base class — unlike Java, you don't need a framework to avoid boilerplate.

**SQLAlchemy's session IS your transaction manager.** The `get_session` dependency gives you the exact same semantics as `@Transactional(propagation = REQUIRED)` — one transaction per request, automatic rollback on failure, and you can nest service calls without worrying about transaction boundaries because they all share the same session.

**Connection pooling is built into SQLAlchemy.** For SQLite specifically you'll want `StaticPool` (single connection) or `NullPool`, but if you later migrate to PostgreSQL, switching to `QueuePool` with `pool_size=5` is a one-line change.

**Folder structure** that mirrors a Spring Boot project:

```
ledger/
├── api/
│   ├── routes/
│   │   ├── accounts.py          # @RestController equivalent
│   │   ├── transactions.py
│   │   └── reports.py
│   ├── schemas/                  # Pydantic DTOs (request/response)
│   │   ├── account.py
│   │   └── transaction.py
│   └── dependencies.py          # Shared FastAPI Depends() functions
├── services/                     # @Service equivalent
│   ├── account_service.py
│   ├── transaction_service.py
│   └── import_service.py
├── db/
│   ├── engine.py                # DataSource + SessionFactory
│   ├── models.py                # @Entity equivalents
│   └── repositories/            # @Repository equivalent
│       ├── base.py              # Generic CrudRepository
│       ├── account_repository.py
│       └── transaction_repository.py
├── core/
│   ├── config.py                # application.properties equivalent
│   └── exceptions.py
└── main.py                      # @SpringBootApplication
```

This gives you the clean layered architecture you're looking for — REST controllers never touch the database directly, services encapsulate business logic, repositories encapsulate queries, and transaction boundaries are managed declaratively through the session lifecycle.