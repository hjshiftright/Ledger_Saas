"""SaaS-ification DB migration — adds user_id columns to all user-owned tables.

Run from backend/src/:
    python migrate.py

This migration is safe to run multiple times (idempotent — skips columns that
already exist). Existing rows will have user_id defaulted to 1 (the first user).
"""
from sqlalchemy import create_engine, text
from config import get_settings


def _add_column_safe(conn, table: str, column_def: str) -> None:
    """ALTER TABLE ... ADD COLUMN, skipping if the column already exists."""
    col_name = column_def.split()[0]
    try:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column_def}"))
        print(f"  + {table}.{col_name} added")
    except Exception as e:
        msg = str(e).lower()
        if "duplicate column name" in msg or "already exists" in msg:
            print(f"  . {table}.{col_name} already exists — skipped")
        else:
            print(f"  ! {table}.{col_name} error: {e}")


def migrate():
    settings = get_settings()
    engine = create_engine(settings.database_url)

    with engine.connect() as conn:
        print("\n=== Ledger SaaS migration: adding user_id columns ===\n")

        # ── profiles ───────────────────────────────────────────────────────────
        _add_column_safe(conn, "profiles",       "user_id INTEGER REFERENCES users(id)")
        # Legacy migration columns (previously added separately)
        _add_column_safe(conn, "profiles",       "age INTEGER")
        _add_column_safe(conn, "profiles",       "monthly_income FLOAT")
        _add_column_safe(conn, "profiles",       "monthly_expenses FLOAT")

        # ── goals ──────────────────────────────────────────────────────────────
        _add_column_safe(conn, "goals",          "user_id INTEGER NOT NULL DEFAULT 1 REFERENCES users(id)")

        # ── budgets ────────────────────────────────────────────────────────────
        _add_column_safe(conn, "budgets",        "user_id INTEGER NOT NULL DEFAULT 1 REFERENCES users(id)")

        # ── accounts ───────────────────────────────────────────────────────────
        _add_column_safe(conn, "accounts",       "user_id INTEGER REFERENCES users(id)")

        # ── import_batches ─────────────────────────────────────────────────────
        _add_column_safe(conn, "import_batches", "user_id INTEGER NOT NULL DEFAULT 1 REFERENCES users(id)")

        # ── transactions ───────────────────────────────────────────────────────
        _add_column_safe(conn, "transactions",   "user_id INTEGER NOT NULL DEFAULT 1 REFERENCES users(id)")

        # ── audit_log ──────────────────────────────────────────────────────────
        _add_column_safe(conn, "audit_log",      "user_id INTEGER REFERENCES users(id)")

        # ── notifications ──────────────────────────────────────────────────────
        _add_column_safe(conn, "notifications",  "user_id INTEGER REFERENCES users(id)")

        conn.commit()

    print("\nMigration complete. All user_id columns are in place.\n")


if __name__ == "__main__":
    migrate()
