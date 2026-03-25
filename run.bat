@echo off
setlocal

echo ==============================================
echo        Starting Ledger Application
echo ==============================================

:: Check for python (prefer venv if it exists, otherwise check host)
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

echo [ERROR] Python was not found (checked py, python).
echo Please install Python 3.11+ and ensure it is added to your PATH.
pause
exit /b 1

:check_done
:: Set up virtual environment if it doesn't exist
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

:: Activate virtual environment
echo [INFO] Activating virtual environment...
call .venv\Scripts\activate

:: Ensure pip is up to date
echo [INFO] Updating pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul 2>&1

:: Install requirements
echo [INFO] Installing requirements...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install requirements.
    pause
    exit /b 1
)

:: Set up Frontend
echo [INFO] Setting up frontend...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js is not installed or not in PATH.
    echo Please install Node.js to build the frontend.
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

:: Add src directory to PYTHONPATH so imports work correctly
set PYTHONPATH=%cd%\backend\src

:: Start the application
echo ==============================================
echo [INFO] Launching Ledger API server...
echo [INFO] The frontend will be available at http://127.0.0.1:8000/
echo ==============================================
".venv\Scripts\python.exe" backend\src\main.py

pause
