-- Alembic RLS policies reference role app_service. Create it on first DB init only.
DO $$
BEGIN
    CREATE ROLE app_service LOGIN PASSWORD 'ledger_secret' NOSUPERUSER NOCREATEDB NOCREATEROLE;
EXCEPTION
    WHEN duplicate_object THEN NULL;
END
$$;
