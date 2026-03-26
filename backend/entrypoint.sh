#!/bin/sh
set -e

# Wait until PostgreSQL is accepting connections before starting the API server.
# Falls back immediately if DATABASE_URL is not a PostgreSQL URL (e.g. SQLite for local dev).

if echo "$DATABASE_URL" | grep -q "^postgresql"; then
    echo "Waiting for PostgreSQL at $DATABASE_URL ..."
    until python - <<'EOF'
import sys, os
try:
    import psycopg2
    psycopg2.connect(os.environ["DATABASE_URL"]).close()
    sys.exit(0)
except Exception as e:
    print(f"  not ready: {e}")
    sys.exit(1)
EOF
    do
        sleep 2
    done
    echo "PostgreSQL is ready."
fi

exec uvicorn main:app --host 0.0.0.0 --port 8000
