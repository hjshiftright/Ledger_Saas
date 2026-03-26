@echo off
setlocal enabledelayedexpansion

echo ==============================================
echo        Starting Ledger Application
echo ==============================================

:: ─────────────────────────────────────────────────────────────────────────────
:: PostgreSQL connection settings — change these if you use a different host or
:: credentials.  The DATABASE_URL is passed to the Python process as an env var
:: so pydantic-settings picks it up automatically.
:: ─────────────────────────────────────────────────────────────────────────────
set PG_USER=ledgeradmin
set PG_PASS=ledger123
set PG_DB=ledgerdb
set PG_HOST=127.0.0.1
set PG_PORT=5432
set DATABASE_URL=postgresql://%PG_USER%:%PG_PASS%@%PG_HOST%:%PG_PORT%/%PG_DB%


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
:: Wait for PostgreSQL to accept connections (up to ~60 s)
:: ─────────────────────────────────────────────────────────────────────────────
echo [INFO] Waiting for PostgreSQL at %PG_HOST%:%PG_PORT%...
set /a PG_TRIES=0
:pg_wait
".venv\Scripts\python.exe" -c "import psycopg2, os, sys; psycopg2.connect(os.environ['DATABASE_URL']).close(); sys.exit(0)" >nul 2>&1
if %errorlevel% equ 0 goto :pg_ready
set /a PG_TRIES+=1
if %PG_TRIES% geq 30 (
    echo [ERROR] Cannot connect to PostgreSQL at %PG_HOST%:%PG_PORT%/%PG_DB%.
    echo         Verify the database is running and the credentials in this script are correct.
    pause
    exit /b 1
)
timeout /t 2 /nobreak >nul
goto :pg_wait

:pg_ready
echo [INFO] PostgreSQL is ready.

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
:: Launch the API server (serves the built frontend from /frontend/dist)
:: ─────────────────────────────────────────────────────────────────────────────
set PYTHONPATH=%cd%\backend\src

echo ==============================================
echo [INFO] Launching Ledger API server...
echo [INFO] Database : PostgreSQL at %PG_HOST%:%PG_PORT%/%PG_DB%
echo [INFO] App URL  : http://127.0.0.1:8000/
echo ==============================================
".venv\Scripts\python.exe" backend\src\main.py

pause
