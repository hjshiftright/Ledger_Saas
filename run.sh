#!/bin/bash
set -e

echo "=============================================="
echo "       Starting Ledger Application"
echo "=============================================="

# ─────────────────────────────────────────────────────────────────────────────
# PostgreSQL connection settings
# ─────────────────────────────────────────────────────────────────────────────
PG_USER=ledger
PG_PASS=ledger_secret
PG_DB=ledger
PG_HOST=127.0.0.1
PG_PORT=5432
export DATABASE_URL="postgresql://${PG_USER}:${PG_PASS}@${PG_HOST}:${PG_PORT}/${PG_DB}"

# ─────────────────────────────────────────────────────────────────────────────
# Start PostgreSQL via Docker (only the db service from docker-compose.yml).
# Set SKIP_DOCKER_PG=1 to skip this if you already have PostgreSQL running.
# ─────────────────────────────────────────────────────────────────────────────
if [ "${SKIP_DOCKER_PG}" != "1" ]; then
    if ! command -v docker &> /dev/null; then
        echo "[ERROR] Docker was not found. Install Docker or set SKIP_DOCKER_PG=1"
        echo "        and ensure PostgreSQL is already running on ${PG_HOST}:${PG_PORT}."
        exit 1
    fi

    echo "[INFO] Starting PostgreSQL container..."
    docker compose up -d db
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
# Wait for PostgreSQL to accept connections (up to ~60 s)
# ─────────────────────────────────────────────────────────────────────────────
echo "[INFO] Waiting for PostgreSQL at ${PG_HOST}:${PG_PORT}..."
PG_TRIES=0
until python -c "
import psycopg2, os, sys
try:
    psycopg2.connect(os.environ['DATABASE_URL']).close()
    sys.exit(0)
except Exception as e:
    print(f'  not ready: {e}')
    sys.exit(1)" 2>/dev/null; do
    PG_TRIES=$((PG_TRIES + 1))
    if [ "$PG_TRIES" -ge 30 ]; then
        echo "[ERROR] PostgreSQL did not become ready after 60 seconds."
        echo "        Check Docker is running: docker compose logs db"
        exit 1
    fi
    sleep 2
done
echo "[INFO] PostgreSQL is ready."

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
echo "[INFO] Database : PostgreSQL at ${PG_HOST}:${PG_PORT}/${PG_DB}"
echo "[INFO] App URL  : http://127.0.0.1:8000/"
echo "=============================================="
python backend/src/main.py
