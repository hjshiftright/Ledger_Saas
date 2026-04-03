"""Shared pytest fixtures for all test modules."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from core.models.enums import ExtractionMethod, SourceType, TxnTypeHint
from core.models.import_batch import ImportBatch
from core.models.raw_parsed_row import ParseMetadata, ParseResult, RawParsedRow
from core.models.column_mapping import ColumnMapping


# ── Store: disable disk persistence for all tests ────────────────────────────
# Keeps dedup hash state and categorize rules fully in-memory so tests never
# read stale data from a previous run's on-disk files.

@pytest.fixture(autouse=True, scope="session")
def _disable_store_persistence():
    """Turn off JSON-file persistence for the entire test session."""
    from modules.store import configure_persistence
    configure_persistence(False)


# ── Batch IDs ─────────────────────────────────────────────────────────────────

@pytest.fixture
def batch_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def user_id() -> str:
    return "user-test-001"


@pytest.fixture
def account_id() -> str:
    return "account-test-001"


# ── ImportBatch ───────────────────────────────────────────────────────────────

@pytest.fixture
def hdfc_import_batch(batch_id: str, user_id: str, account_id: str) -> ImportBatch:
    from core.models.enums import BatchStatus, FileFormat

    return ImportBatch(
        batch_id=batch_id,
        user_id=user_id,
        account_id=account_id,
        filename="HDFC_Jan2026.pdf",
        file_hash="abc123",
        source_type=SourceType.HDFC_BANK,
        format=FileFormat.PDF,
    )


# ── RawParsedRow ──────────────────────────────────────────────────────────────

@pytest.fixture
def sample_raw_row(batch_id: str) -> RawParsedRow:
    return RawParsedRow(
        batch_id=batch_id,
        source_type=SourceType.HDFC_BANK,
        parser_version="1.2",
        extraction_method=ExtractionMethod.TEXT_LAYER,
        raw_date="01/01/2026",
        raw_narration="UPI/147896325478/SWIGGY/payment",
        raw_debit="450.00",
        raw_credit=None,
        raw_balance="19,550.00",
        raw_reference="147896325478",
        txn_type_hint=TxnTypeHint.UPI,
        row_confidence=0.95,
        row_number=1,
    )


@pytest.fixture
def sample_rows(batch_id: str) -> list[RawParsedRow]:
    """Three rows: one debit, one credit, one ATM withdrawal."""
    return [
        RawParsedRow(
            batch_id=batch_id,
            source_type=SourceType.HDFC_BANK,
            parser_version="1.2",
            extraction_method=ExtractionMethod.TEXT_LAYER,
            raw_date="01/01/2026",
            raw_narration="UPI/147896325478/SWIGGY/payment",
            raw_debit="450.00",
            raw_balance="19,550.00",
            txn_type_hint=TxnTypeHint.UPI,
            row_confidence=0.95,
            row_number=1,
        ),
        RawParsedRow(
            batch_id=batch_id,
            source_type=SourceType.HDFC_BANK,
            parser_version="1.2",
            extraction_method=ExtractionMethod.TEXT_LAYER,
            raw_date="02/01/2026",
            raw_narration="NEFT CR/SALARY/EMPLOYER",
            raw_credit="50000.00",
            raw_balance="69,550.00",
            txn_type_hint=TxnTypeHint.NEFT,
            row_confidence=0.95,
            row_number=2,
        ),
        RawParsedRow(
            batch_id=batch_id,
            source_type=SourceType.HDFC_BANK,
            parser_version="1.2",
            extraction_method=ExtractionMethod.TEXT_LAYER,
            raw_date="05/01/2026",
            raw_narration="ATM/BOM/00123 CASH WD",
            raw_debit="5000.00",
            raw_balance="64,550.00",
            txn_type_hint=TxnTypeHint.ATM_WITHDRAWAL,
            row_confidence=0.95,
            row_number=3,
        ),
    ]


# ── HDFC sample text ──────────────────────────────────────────────────────────

@pytest.fixture
def hdfc_sample_text() -> str:
    """Simulated HDFC Bank PDF text-layer content."""
    return """\
HDFC Bank Account Statement
Account Number: 50100****1234
Period: 01/01/2026 to 31/01/2026

Opening Balance 20,000.00

Date              Narration                       Chq/Ref No.        Value Dt    Withdrawal Amt (Dr)  Deposit Amt (Cr)  Closing Balance
01/01/2026        UPI/147896325478/SWIGGY/pay     147896325478       01/01/2026  450.00                                 19,550.00
02/01/2026        NEFT CR/20260201/SALARY         NEFT20260201       02/01/2026                        50,000.00        69,550.00
05/01/2026        ATM/BOM/00123 CASH WD           ATM00123           05/01/2026  5,000.00                               64,550.00
10/01/2026        IMPS/98765432100/PHONEPE        IMPS98765          10/01/2026  1,200.00                               63,350.00
15/01/2026        NEFT CR/20260115/INTEREST       NEFT20260115       15/01/2026                        350.00           63,700.00

Closing Balance 63,700.00
"""


# ── HDFC CSV sample ───────────────────────────────────────────────────────────

@pytest.fixture
def hdfc_csv_content() -> bytes:
    """Simulated HDFC Bank CSV export bytes."""
    csv = (
        "Date,Narration,Chq./Ref.No.,Value Dt,Withdrawal Amt (Dr),Deposit Amt (Cr),Closing Balance\n"
        "01/01/2026,UPI/147896325478/SWIGGY/payment,147896325478,01/01/2026,450.00,,19550.00\n"
        "02/01/2026,NEFT CR/SALARY/EMPLOYER,NEFT20260201,02/01/2026,,50000.00,69550.00\n"
        "05/01/2026,ATM CASH WITHDRAWAL,ATM00123,05/01/2026,5000.00,,64550.00\n"
    )
    return csv.encode("utf-8")


# ── Generic CSV sample ────────────────────────────────────────────────────────

@pytest.fixture
def generic_csv_content() -> bytes:
    """Generic CSV with non-standard headers."""
    csv = (
        "Trans Date,Details,Debit,Credit,Bal\n"
        "01/01/2026,Swiggy Food Order,450.00,,19550.00\n"
        "02/01/2026,Salary Credit,,50000.00,69550.00\n"
    )
    return csv.encode("utf-8")


@pytest.fixture
def generic_column_mapping(user_id: str) -> ColumnMapping:
    """A user-confirmed ColumnMapping for the generic CSV fixture."""
    return ColumnMapping(
        user_id=user_id,
        format_fingerprint="generic_test_v1",
        mapping_label="Test Generic CSV",
        date_column="Trans Date",
        narration_column="Details",
        debit_column="Debit",
        credit_column="Credit",
        balance_column="Bal",
        date_format="%d/%m/%Y",
    )


# ── CAS sample text ───────────────────────────────────────────────────────────

@pytest.fixture
def cas_sample_text() -> str:
    """Simulated CAMS CAS PDF text content (condensed)."""
    return """\
Consolidated Account Statement
CAMS
Investor: John Doe  PAN: ABCDE1234F
Period: 01-Jan-2026 to 31-Jan-2026

Folio No: 12345678  HDFC Mutual Fund

Scheme: HDFC Top 100 Fund - Direct Growth (ISIN: INF179KB01BD)

Date          Transaction         Amount (₹)  Units     Price       Unit Balance
01-Jan-2026   Purchase-SIP        5000.00     18.345    272.5400    118.345
15-Jan-2026   Redemption          10000.00    35.200    284.0900    83.145

Folio No: 87654321  Axis Mutual Fund

Scheme: Axis Bluechip Fund - Direct Growth (ISIN: INF846K01EW2)

Date          Transaction         Amount (₹)  Units     Price       Unit Balance
05-Jan-2026   SIP                 2000.00     10.512    190.2500    50.512
"""

# ── PostgreSQL Testcontainers Setup ──────────────────────────────────────────

import asyncio
from typing import AsyncGenerator
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession, async_sessionmaker
from testcontainers.postgres import PostgresContainer
from db.models.base import Base

@pytest_asyncio.fixture(scope="session")
async def postgres_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Provides a session-scoped async SQLAlchemy engine connected to Testcontainers."""
    with PostgresContainer("postgres:16-alpine", driver="asyncpg") as postgres:
        # Get connection URL and replace protocol for asyncpg
        url = postgres.get_connection_url().replace("postgresql+psycopg2", "postgresql+asyncpg")
        
        engine = create_async_engine(
            url,
            pool_size=5,
            max_overflow=10,
        )
        
        
        # Ensure all models are loaded into Base.metadata before creating tables
        from db.models import users, accounts, transactions, tenants, securities, recurring, goals, budgets, imports, tax, categories
        
        # Create all tables explicitly for tests without running full alembic logic
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
            # Apply RLS infrastructure for tests
            from sqlalchemy import text
            await conn.execute(text("CREATE ROLE app_service LOGIN PASSWORD 'test' NOSUPERUSER NOCREATEDB NOCREATEROLE"))
            await conn.execute(text("GRANT USAGE ON SCHEMA public TO app_service"))
            await conn.execute(text("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_service"))
            await conn.execute(text("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_service"))
            
            # current_tenant_id function
            await conn.execute(text('''
                CREATE OR REPLACE FUNCTION current_tenant_id() RETURNS UUID
                LANGUAGE sql STABLE SECURITY DEFINER AS $$
                    SELECT NULLIF(current_setting('app.tenant_id', TRUE), '')::UUID;
                $$;
            '''))
            
            # Enable RLS on all tenant-scoped tables
            tenant_tables = [
                # Core financials
                "transactions", "transaction_lines", "transaction_charges", "attachments",
                # Accounts
                "accounts", "financial_institutions", "bank_accounts", "fixed_deposits",
                "credit_cards", "loans", "brokerage_accounts",
                # System / settings
                "llm_providers", "app_settings", "audit_log", "notifications",
                # Import pipeline
                "import_batches",
                # Reporting / snapshots
                "monthly_snapshots", "net_worth_history", "saved_reports",
                # Categories & rules
                "payees", "tags", "transaction_tags", "user_category_rules",
                # Budgets
                "budgets", "budget_items",
                # Goals
                "goals", "goal_milestones", "goal_contributions", "goal_account_mappings",
                # Securities
                "fo_positions", "holdings_summary",
                # Recurring
                "recurring_transactions", "recurring_transaction_lines",
                # Tax
                "tax_lots", "tax_lot_disposals", "tax_section_mappings",
            ]
            for table in tenant_tables:
                await conn.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
                await conn.execute(text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))
                await conn.execute(text(f'''
                    CREATE POLICY tenant_isolation ON {table}
                        AS PERMISSIVE FOR ALL TO app_service
                        USING (tenant_id = current_tenant_id())
                        WITH CHECK (tenant_id = current_tenant_id())
                '''))
            
        yield engine
        
        await engine.dispose()

@pytest_asyncio.fixture(scope="function")
async def db_session(postgres_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Provides a function-scoped async session. Rolls back changes after each test."""
    SessionFactory = async_sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=postgres_engine,
        expire_on_commit=False,
    )

    async with SessionFactory() as session:
        # We can implement a nested transaction or rely on explicit TRUNCATE
        # Given RLS context and nested transaction behavior in asyncpg,
        # a savepoint or simplest approach is yielded session and test handles it,
        # or we just let it roll back.
        await session.begin_nested()

        yield session

        await session.rollback()


# ── Transaction propagation fixtures ─────────────────────────────────────────
# Used by tests/unit/test_tx_propagation_unit.py and
# tests/integration/test_tx_propagation_integration.py

@pytest_asyncio.fixture
async def tx_session_factory(postgres_engine: AsyncEngine):
    """Async session factory matching production config for propagation tests.

    autoflush=False and expire_on_commit=False mirror the production
    SessionFactory so test behavior matches production behavior exactly.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker as _asm
    return _asm(
        bind=postgres_engine,
        autoflush=False,
        expire_on_commit=False,
        class_=AsyncSession,
    )


@pytest_asyncio.fixture(autouse=True)
async def reset_active_tx():
    """Reset _active_tx ContextVar before every test.

    pytest-asyncio runs each test in the same event loop task by default, so a
    ContextVar value set in one test leaks into the next unless explicitly
    cleared.  This fixture prevents that contamination.
    """
    from db.transaction import _active_tx
    token = _active_tx.set(None)
    yield
    _active_tx.reset(token)


TX_TEST_TENANT_ID = "00000000-0000-0000-0000-000000000099"
TX_TEST_USER_ID = "99"

