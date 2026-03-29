"""initial_schema_with_rls

Creates the full Ledger 3.0 schema via SQLAlchemy metadata + appends the
PostgreSQL Row-Level Security (RLS) layer required for multi-tenancy.

Revision ID: dc8bdc3d7239
Revises:
Create Date: 2026-03-27 19:57:19.113476
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = 'dc8bdc3d7239'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ── Tenant-scoped tables: RLS is enabled on every one of these ────────────────
_TENANT_SCOPED_TABLES = [
    "accounts",
    "app_settings",
    "attachments",
    "bank_accounts",
    "brokerage_accounts",
    "budget_items",
    "budgets",
    "credit_cards",
    "financial_institutions",
    "fixed_deposits",
    "fo_positions",
    "goal_account_mappings",
    "goal_contributions",
    "goal_milestones",
    "goals",
    "holdings_summary",
    "import_batches",
    "llm_providers",
    "loans",
    "monthly_snapshots",
    "net_worth_history",
    "notifications",
    "payees",
    "recurring_transaction_lines",
    "recurring_transactions",
    "saved_reports",
    "tags",
    "tax_lot_disposals",
    "tax_lots",
    "tax_section_mappings",
    "transaction_charges",
    "transaction_lines",
    "transaction_tags",
    "transactions",
    "user_category_rules",
]

# Audit log needs special insert-only + select policy (no UPDATE/DELETE)
_AUDIT_LOG_TABLE = "audit_log"


def upgrade() -> None:
    # ── 1. Create all tables via SQLAlchemy metadata ──────────────────────────
    # Import all model modules so Base.metadata is fully populated.
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

    from db.models.base import Base
    from db.models import (  # noqa: F401
        users, accounts, transactions, goals, budgets,
        imports, recurring, reporting, categories, system, tax, securities,
    )
    # Import tenants model if it exists
    try:
        from db.models import tenants  # noqa: F401
    except ImportError:
        pass

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)

    # ── 2. Helper function: current_tenant_id() ───────────────────────────────
    op.execute(text("""
        CREATE OR REPLACE FUNCTION current_tenant_id() RETURNS UUID
            LANGUAGE sql STABLE SECURITY DEFINER
        AS $$
            SELECT NULLIF(current_setting('app.tenant_id', TRUE), '')::UUID;
        $$;
    """))

    # ── 3. Enable RLS on all tenant-scoped tables ─────────────────────────────
    for table in _TENANT_SCOPED_TABLES:
        op.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
        op.execute(text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))
        op.execute(text(f"""
            CREATE POLICY tenant_isolation ON {table}
                AS PERMISSIVE
                FOR ALL
                TO app_service
                USING (tenant_id = current_tenant_id())
                WITH CHECK (tenant_id = current_tenant_id())
        """))

    # ── 4. Audit log: insert + select allowed, no UPDATE/DELETE ───────────────
    op.execute(text(f"ALTER TABLE {_AUDIT_LOG_TABLE} ENABLE ROW LEVEL SECURITY"))
    op.execute(text(f"ALTER TABLE {_AUDIT_LOG_TABLE} FORCE ROW LEVEL SECURITY"))
    op.execute(text(f"""
        CREATE POLICY audit_insert ON {_AUDIT_LOG_TABLE}
            AS PERMISSIVE FOR INSERT
            TO app_service
            WITH CHECK (tenant_id = current_tenant_id())
    """))
    op.execute(text(f"""
        CREATE POLICY audit_select ON {_AUDIT_LOG_TABLE}
            AS PERMISSIVE FOR SELECT
            TO app_service
            USING (tenant_id = current_tenant_id())
    """))
    op.execute(text(f"""
        CREATE POLICY audit_no_update ON {_AUDIT_LOG_TABLE}
            AS RESTRICTIVE FOR UPDATE
            TO app_service
            USING (FALSE)
    """))
    op.execute(text(f"""
        CREATE POLICY audit_no_delete ON {_AUDIT_LOG_TABLE}
            AS RESTRICTIVE FOR DELETE
            TO app_service
            USING (FALSE)
    """))

    # ── 5. Securities: global read, no app_service writes ────────────────
    op.execute(text("ALTER TABLE securities ENABLE ROW LEVEL SECURITY"))
    op.execute(text("ALTER TABLE securities FORCE ROW LEVEL SECURITY"))
    op.execute(text("""
        CREATE POLICY global_read ON securities
            AS PERMISSIVE FOR SELECT
            TO app_service
            USING (TRUE)
    """))
    op.execute(text("""
        CREATE POLICY global_insert_block ON securities
            AS RESTRICTIVE FOR INSERT
            TO app_service
            WITH CHECK (FALSE)
    """))
    op.execute(text("""
        CREATE POLICY global_update_block ON securities
            AS RESTRICTIVE FOR UPDATE
            TO app_service
            USING (FALSE)
    """))
    op.execute(text("""
        CREATE POLICY global_delete_block ON securities
            AS RESTRICTIVE FOR DELETE
            TO app_service
            USING (FALSE)
    """))

    # ── 6. Users: RLS to prevent arbitrary mutations by app_service ───────────
    op.execute(text("ALTER TABLE users ENABLE ROW LEVEL SECURITY"))
    op.execute(text("ALTER TABLE users FORCE ROW LEVEL SECURITY"))
    op.execute(text("""
        CREATE POLICY users_select ON users
            AS PERMISSIVE FOR SELECT
            TO app_service
            USING (TRUE)
    """))
    op.execute(text("""
        CREATE POLICY users_update ON users
            AS PERMISSIVE FOR UPDATE
            TO app_service
            USING (TRUE)
    """))
    op.execute(text("""
        CREATE POLICY users_insert_block ON users
            AS RESTRICTIVE FOR INSERT
            TO app_service
            WITH CHECK (FALSE)
    """))


def downgrade() -> None:
    # Drop all RLS policies and disable RLS before dropping tables
    for table in _TENANT_SCOPED_TABLES:
        op.execute(text(f"DROP POLICY IF EXISTS tenant_isolation ON {table}"))
        op.execute(text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY"))

    for policy in ("audit_insert", "audit_select", "audit_no_update", "audit_no_delete"):
        op.execute(text(f"DROP POLICY IF EXISTS {policy} ON {_AUDIT_LOG_TABLE}"))
    op.execute(text(f"ALTER TABLE {_AUDIT_LOG_TABLE} DISABLE ROW LEVEL SECURITY"))

    op.execute(text("DROP POLICY IF EXISTS global_read ON securities"))
    op.execute(text("DROP POLICY IF EXISTS global_insert_block ON securities"))
    op.execute(text("DROP POLICY IF EXISTS global_update_block ON securities"))
    op.execute(text("DROP POLICY IF EXISTS global_delete_block ON securities"))
    op.execute(text("ALTER TABLE securities DISABLE ROW LEVEL SECURITY"))

    op.execute(text("DROP POLICY IF EXISTS users_select ON users"))
    op.execute(text("DROP POLICY IF EXISTS users_update ON users"))
    op.execute(text("DROP POLICY IF EXISTS users_insert_block ON users"))
    op.execute(text("ALTER TABLE users DISABLE ROW LEVEL SECURITY"))

    op.execute(text("DROP FUNCTION IF EXISTS current_tenant_id()"))

    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
    from db.models.base import Base
    from db.models import (  # noqa: F401
        users, accounts, transactions, goals, budgets,
        imports, recurring, reporting, categories, system, tax, securities,
    )
    try:
        from db.models import tenants  # noqa: F401
    except ImportError:
        pass
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
