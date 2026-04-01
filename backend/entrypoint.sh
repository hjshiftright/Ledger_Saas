#!/bin/sh
set -e

# Wait until PgBouncer (and through it, PostgreSQL) is accepting connections
# before starting the API server.
#
# Connection flow this script verifies:
#   entrypoint health check → PgBouncer :6432 → PostgreSQL :5432
#
# DATABASE_URL uses the postgresql+asyncpg:// scheme (for SQLAlchemy async engine).
# psycopg2 requires the plain postgresql:// scheme, so we strip the driver prefix
# before passing it to the health check.

if echo "$DATABASE_URL" | grep -q "^postgresql"; then
    # Derive a sync URL for psycopg2 by removing the +asyncpg driver suffix
    SYNC_URL=$(echo "$DATABASE_URL" | sed 's|postgresql+asyncpg://|postgresql://|')

    echo "Waiting for PgBouncer at $(echo "$SYNC_URL" | sed 's|//.*@|//<credentials>@|') ..."
    until python - <<EOF
import sys, os
try:
    import psycopg2
    psycopg2.connect("$SYNC_URL").close()
    sys.exit(0)
except Exception as e:
    print(f"  not ready: {e}")
    sys.exit(1)
EOF
    do
        sleep 2
    done
    echo "PgBouncer is ready."
fi

exec uvicorn main:app --host 0.0.0.0 --port 8000
