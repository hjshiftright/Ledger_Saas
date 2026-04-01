@echo off
setlocal enabledelayedexpansion

echo ==============================================
echo        Starting Ledger Application
echo ==============================================

:: ─────────────────────────────────────────────────────────────────────────────
:: Connection settings
::
:: Connection flow (local dev):
::   Python backend (localhost) → PgBouncer (Docker :6432) → PostgreSQL (Docker :5432)
::
:: DATABASE_URL       : asyncpg URL pointing to PgBouncer (:6432)
:: ADMIN_DATABASE_URL : asyncpg URL pointing directly to PostgreSQL (:5432) — DDL / migrations
:: PG_SYNC_URL        : plain psycopg2 URL used only for the readiness health check below
:: ─────────────────────────────────────────────────────────────────────────────
set PG_USER=ledger
set PG_PASS=ledger_secret
set PG_DB=ledger
set PG_HOST=127.0.0.1
set PG_PORT=5432
set PGB_PORT=6432

:: Async URL via PgBouncer — used by the main SQLAlchemy engine (asyncpg)
set DATABASE_URL=postgresql+asyncpg://%PG_USER%:%PG_PASS%@%PG_HOST%:%PGB_PORT%/%PG_DB%

:: Async URL direct to PostgreSQL — used by the admin engine and Alembic migrations
set ADMIN_DATABASE_URL=postgresql+asyncpg://%PG_USER%:%PG_PASS%@%PG_HOST%:%PG_PORT%/%PG_DB%

:: Sync URL via PgBouncer — used only by the psycopg2 readiness check below
set PG_SYNC_URL=postgresql://%PG_USER%:%PG_PASS%@%PG_HOST%:%PGB_PORT%/%PG_DB%


:: ─────────────────────────────────────────────────────────────────────────────
:: Start PostgreSQL + PgBouncer via Docker Compose
:: ─────────────────────────────────────────────────────────────────────────────
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker was not found. Install Docker Desktop and ensure it is running.
    pause
    exit /b 1
)

echo [INFO] Starting PostgreSQL and PgBouncer containers...
docker compose up -d db pgbouncer
if %errorlevel% neq 0 (
    echo [ERROR] Failed to start Docker containers.
    echo         Ensure Docker Desktop is running: docker compose logs
    pause
    exit /b 1
)


:: ─────────────────────────────────────────────────────────────────────────────
:: Locate Python
:: ─────────────────────────────────────────────────────────────────────────────
set PYTHON_EXE=python
if exist ".venv\Scripts\python.exe" (
    set PYTHON_EXE=".venv\Scripts\python.exe"
    goto :venv_ready
)

py --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_EXE=py
    goto :check_done
)

python --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_EXE=python
    goto :check_done
)

echo [ERROR] Python was not found. Install Python 3.11+ and add it to PATH.
pause
exit /b 1

:check_done
:: Create virtual environment if missing
if not exist ".venv" (
    echo [INFO] Creating virtual environment...
    %PYTHON_EXE% -m venv .venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

set PYTHON_EXE=".venv\Scripts\python.exe"

:venv_ready
echo [INFO] Activating virtual environment...
call .venv\Scripts\activate

echo [INFO] Updating pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul 2>&1

echo [INFO] Installing requirements...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install requirements.
    pause
    exit /b 1
)

:: ─────────────────────────────────────────────────────────────────────────────
:: Wait for PgBouncer to accept connections via :6432 (up to ~60 s)
:: ─────────────────────────────────────────────────────────────────────────────
echo [INFO] Waiting for PgBouncer at %PG_HOST%:%PGB_PORT%...
set /a PGB_TRIES=0

:pgb_wait
".venv\Scripts\python.exe" -c "import psycopg2, os, sys; psycopg2.connect(os.environ['PG_SYNC_URL']).close(); sys.exit(0)" >nul 2>&1
if %errorlevel% equ 0 goto :pgb_ready
set /a PGB_TRIES+=1
if %PGB_TRIES% geq 30 (
    echo [ERROR] PgBouncer at %PG_HOST%:%PGB_PORT% did not become ready after 60 seconds.
    echo         Check containers: docker compose logs pgbouncer
    echo         Check database:   docker compose logs db
    pause
    exit /b 1
)
timeout /t 2 /nobreak >nul
goto :pgb_wait

:pgb_ready
echo [INFO] PgBouncer is ready.

:: ─────────────────────────────────────────────────────────────────────────────
:: Build the frontend
:: ─────────────────────────────────────────────────────────────────────────────
echo [INFO] Setting up frontend...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js is not installed or not in PATH.
    pause
    exit /b 1
)

cd frontend
if not exist "node_modules\" (
    echo [INFO] Installing frontend dependencies...
    call npm install
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install frontend dependencies.
        cd ..
        pause
        exit /b 1
    )
)

echo [INFO] Building frontend...
call npm run build
if %errorlevel% neq 0 (
    echo [ERROR] Failed to build frontend.
    cd ..
    pause
    exit /b 1
)
cd ..

:: ─────────────────────────────────────────────────────────────────────────────
:: Launch the API server
:: ─────────────────────────────────────────────────────────────────────────────
set PYTHONPATH=%cd%\backend\src

echo ==============================================
echo [INFO] Launching Ledger API server...
echo [INFO] App engine   : PgBouncer at %PG_HOST%:%PGB_PORT% (pooled)
echo [INFO] Admin engine : PostgreSQL at %PG_HOST%:%PG_PORT% (direct)
echo [INFO] App URL      : http://127.0.0.1:8000/
echo ==============================================
".venv\Scripts\python.exe" backend\src\main.py

pause
