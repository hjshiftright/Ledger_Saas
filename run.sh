#!/bin/bash
set -e

echo "=============================================="
echo "       Starting Ledger Application"
echo "=============================================="

# ─────────────────────────────────────────────────────────────────────────────
# Connection settings
#
# Connection flow (local dev):
#   Python backend (localhost) → PgBouncer (Docker :6432) → PostgreSQL (Docker :5432)
#
# DATABASE_URL      : asyncpg URL pointing to PgBouncer (:6432)
# ADMIN_DATABASE_URL: asyncpg URL pointing directly to PostgreSQL (:5432) — DDL / migrations
# PG_SYNC_URL       : plain psycopg2 URL used only for the readiness health check below
# ─────────────────────────────────────────────────────────────────────────────
PG_USER=ledger
PG_PASS=ledger_secret
PG_DB=ledger
PG_HOST=127.0.0.1
PG_PORT=5432        # PostgreSQL direct (admin engine + readiness check)
PGB_PORT=6432       # PgBouncer (app engine)

export DATABASE_URL="postgresql+asyncpg://${PG_USER}:${PG_PASS}@${PG_HOST}:${PGB_PORT}/${PG_DB}"
export ADMIN_DATABASE_URL="postgresql+asyncpg://${PG_USER}:${PG_PASS}@${PG_HOST}:${PG_PORT}/${PG_DB}"
PG_SYNC_URL="postgresql://${PG_USER}:${PG_PASS}@${PG_HOST}:${PGB_PORT}/${PG_DB}"

# ─────────────────────────────────────────────────────────────────────────────
# Start PostgreSQL + PgBouncer via Docker Compose.
# Set SKIP_DOCKER_PG=1 to skip this step if both are already running externally.
# ─────────────────────────────────────────────────────────────────────────────
if [ "${SKIP_DOCKER_PG}" != "1" ]; then
    if ! command -v docker &> /dev/null; then
        echo "[ERROR] Docker was not found. Install Docker or set SKIP_DOCKER_PG=1"
        echo "        and ensure PostgreSQL and PgBouncer are already running."
        exit 1
    fi

    echo "[INFO] Starting PostgreSQL and PgBouncer containers..."
    docker compose up -d db pgbouncer

    echo "[INFO] Waiting for PgBouncer container to become healthy..."
    PGB_HEALTH_TRIES=0
    until [ "$(docker compose ps pgbouncer --format json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0].get('Health','') if isinstance(d,list) else d.get('Health',''))" 2>/dev/null)" = "healthy" ]; do
        PGB_HEALTH_TRIES=$((PGB_HEALTH_TRIES + 1))
        if [ "$PGB_HEALTH_TRIES" -ge 30 ]; then
            echo "[WARN] Could not confirm pgbouncer health via docker compose — proceeding anyway."
            break
        fi
        sleep 2
    done
fi

# ─────────────────────────────────────────────────────────────────────────────
# Locate Python
# ─────────────────────────────────────────────────────────────────────────────
if command -v python3 &> /dev/null; then
    PYTHON_EXE="python3"
elif command -v python &> /dev/null; then
    PYTHON_EXE="python"
else
    echo "[ERROR] Python was not found. Install Python 3.11+ and add it to PATH."
    exit 1
fi

# Create virtual environment if missing
if [ ! -f ".venv/bin/activate" ]; then
    echo "[INFO] Creating virtual environment..."
    rm -rf .venv
    if ! $PYTHON_EXE -m venv .venv; then
        echo "[ERROR] Failed to create virtual environment."
        echo "        On Debian/Ubuntu: sudo apt install python3-venv"
        exit 1
    fi
fi

echo "[INFO] Activating virtual environment..."
source .venv/bin/activate

echo "[INFO] Updating pip..."
python -m pip install --upgrade pip >/dev/null 2>&1

echo "[INFO] Installing requirements..."
if ! pip install -r requirements.txt; then
    echo "[ERROR] Failed to install requirements."
    exit 1
fi

# ─────────────────────────────────────────────────────────────────────────────
# Wait for PgBouncer to accept connections (up to ~60 s)
# Connects via PgBouncer (:6432) using psycopg2 with the sync URL.
# ─────────────────────────────────────────────────────────────────────────────
echo "[INFO] Waiting for PgBouncer at ${PG_HOST}:${PGB_PORT}..."
PGB_TRIES=0
until python -c "
import psycopg2, sys
try:
    psycopg2.connect('${PG_SYNC_URL}').close()
    sys.exit(0)
except Exception as e:
    print(f'  not ready: {e}')
    sys.exit(1)" 2>/dev/null; do
    PGB_TRIES=$((PGB_TRIES + 1))
    if [ "$PGB_TRIES" -ge 30 ]; then
        echo "[ERROR] PgBouncer did not become ready after 60 seconds."
        echo "        Check: docker compose logs pgbouncer"
        echo "        Check: docker compose logs db"
        exit 1
    fi
    sleep 2
done
echo "[INFO] PgBouncer is ready."

# ─────────────────────────────────────────────────────────────────────────────
# Build the frontend
# ─────────────────────────────────────────────────────────────────────────────
echo "[INFO] Setting up frontend..."
if ! command -v node &> /dev/null; then
    echo "[ERROR] Node.js is not installed or not in PATH."
    exit 1
fi

cd frontend

if [ ! -d "node_modules" ]; then
    echo "[INFO] Installing frontend dependencies..."
    if ! npm install; then
        echo "[ERROR] Failed to install frontend dependencies."
        exit 1
    fi
fi

echo "[INFO] Building frontend..."
if ! npm run build; then
    echo "[ERROR] Failed to build frontend."
    exit 1
fi
cd ..

# ─────────────────────────────────────────────────────────────────────────────
# Launch the API server
# ─────────────────────────────────────────────────────────────────────────────
export PYTHONPATH="$(pwd)/backend/src:${PYTHONPATH}"

echo "=============================================="
echo "[INFO] Launching Ledger API server..."
echo "[INFO] App engine   : PgBouncer at ${PG_HOST}:${PGB_PORT} (pooled)"
echo "[INFO] Admin engine : PostgreSQL at ${PG_HOST}:${PG_PORT} (direct)"
echo "[INFO] App URL      : http://127.0.0.1:8000/"
echo "=============================================="
python backend/src/main.py
