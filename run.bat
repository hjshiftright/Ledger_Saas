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
:: ADMIN_DATABASE_URL : asyncpg URL pointing directly to PostgreSQL (:5433 on host)
:: PG_SYNC_URL        : plain psycopg2 URL used only for the readiness health check below
:: ─────────────────────────────────────────────────────────────────────────────
set PG_USER=ledger
set PG_PASS=ledger_secret
set PG_DB=ledger
set PG_HOST=127.0.0.1
set PG_PORT=5433
set PGB_PORT=6432

set DATABASE_URL=postgresql+asyncpg://%PG_USER%:%PG_PASS%@%PG_HOST%:%PGB_PORT%/%PG_DB%
set ADMIN_DATABASE_URL=postgresql+asyncpg://%PG_USER%:%PG_PASS%@%PG_HOST%:%PG_PORT%/%PG_DB%
set PG_SYNC_URL=postgresql://%PG_USER%:%PG_PASS%@%PG_HOST%:%PGB_PORT%/%PG_DB%

:: ─────────────────────────────────────────────────────────────────────────────
:: Application settings — override here if needed
:: ─────────────────────────────────────────────────────────────────────────────
set APP_ENV=development
set APP_HOST=127.0.0.1
set APP_PORT=8000
set APP_DEBUG=false
set SECRET_KEY=change-me-before-going-to-production
set ALLOWED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000
set GOOGLE_CLIENT_ID=23208176216-hoti0t0pmsskee269dsotbtad4rds3nm.apps.googleusercontent.com

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
if exist "backend\.venv\Scripts\python.exe" (
    set PYTHON_EXE=backend\.venv\Scripts\python.exe
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
:: Create virtual environment inside backend/ if missing
if not exist "backend\.venv" (
    echo [INFO] Creating virtual environment in backend\.venv ...
    %PYTHON_EXE% -m venv backend\.venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

set PYTHON_EXE=backend\.venv\Scripts\python.exe

:venv_ready
echo [INFO] Updating pip...
"%PYTHON_EXE%" -m pip install --upgrade pip >nul 2>&1

echo [INFO] Installing backend requirements...
"%PYTHON_EXE%" -m pip install -r backend\requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install backend requirements.
    pause
    exit /b 1
)


:: ─────────────────────────────────────────────────────────────────────────────
:: Wait for PgBouncer to accept connections via :6432 (up to ~60 s)
:: ─────────────────────────────────────────────────────────────────────────────
echo [INFO] Waiting for PgBouncer at %PG_HOST%:%PGB_PORT%...
set /a PGB_TRIES=0

:pgb_wait
"%PYTHON_EXE%" -c "import psycopg2, os, sys; psycopg2.connect(os.environ['PG_SYNC_URL']).close(); sys.exit(0)" >nul 2>&1
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
:: Launch the API server  (also serves the built frontend as static files)
:: ─────────────────────────────────────────────────────────────────────────────
set PYTHONPATH=%cd%\backend\src

echo ==============================================
echo [INFO] Launching Ledger API server...
echo [INFO] App engine   : PgBouncer at %PG_HOST%:%PGB_PORT% (pooled)
echo [INFO] Admin engine : PostgreSQL at %PG_HOST%:%PG_PORT% (direct)
echo [INFO] App URL      : http://%APP_HOST%:%APP_PORT%/
echo ==============================================
"%PYTHON_EXE%" backend\src\main.py

pause
