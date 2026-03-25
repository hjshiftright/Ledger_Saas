#!/bin/bash
set -e

echo "=============================================="
echo "       Starting Ledger Application"
echo "=============================================="

# Check for python
if command -v python3 &> /dev/null; then
    PYTHON_EXE="python3"
elif command -v python &> /dev/null; then
    PYTHON_EXE="python"
else
    echo "[ERROR] Python was not found (checked python3, python)."
    echo "Please install Python 3.11+ and ensure it is added to your PATH."
    exit 1
fi

# Set up virtual environment if it doesn't exist
if [ ! -f ".venv/bin/activate" ]; then
    echo "[INFO] Creating virtual environment..."
    rm -rf .venv
    if ! $PYTHON_EXE -m venv .venv; then
        echo "[ERROR] Failed to create virtual environment."
        echo "If you are on Debian/Ubuntu, you might need to install virtulenv support:"
        echo "  sudo apt install python3-venv"
        exit 1
    fi
fi

# Activate virtual environment
echo "[INFO] Activating virtual environment..."
source .venv/bin/activate

# Ensure pip is up to date
echo "[INFO] Updating pip..."
python -m pip install --upgrade pip >/dev/null 2>&1

# Install requirements
echo "[INFO] Installing requirements..."
if ! pip install -r requirements.txt; then
    echo "[ERROR] Failed to install requirements."
    exit 1
fi

# Set up Frontend
echo "[INFO] Setting up frontend..."
if ! command -v node &> /dev/null; then
    echo "[ERROR] Node.js is not installed or not in PATH."
    echo "Please install Node.js to build the frontend."
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

# Add src directory to PYTHONPATH so imports work correctly
export PYTHONPATH="$(pwd)/backend/src:${PYTHONPATH}"

# Start the application
echo "=============================================="
echo "[INFO] Launching Ledger API server..."
echo "[INFO] The frontend will be available at http://127.0.0.1:8000/"
echo "=============================================="
python backend/src/main.py
