# ── Ledger — API Server ───────────────────────────────────────────────────────
# Base: Debian-slim for broad package availability (OCR, PDF tooling, psycopg2)
FROM python:3.11-slim

# System dependencies:
#   ghostscript      — required by camelot-py for PDF table extraction
#   poppler-utils    — pdfinfo / pdftotext used by pdfplumber and pdf2image
#   tesseract-ocr    — OCR engine used by pytesseract
#   libglib2.0-0     — shared lib dependency for OpenCV (used by camelot)
#   libgomp1         — OpenMP runtime (OpenCV)
#   libsm6 libxext6 libxrender1 — headless X11 stubs required by OpenCV
#   libpq-dev        — C headers for psycopg2 compilation (not needed for
#                      psycopg2-binary, but harmless and may be needed later)
RUN apt-get update && apt-get install -y --no-install-recommends \
        ghostscript \
        poppler-utils \
        tesseract-ocr \
        tesseract-ocr-eng \
        tesseract-ocr-hin \
        libglib2.0-0 \
        libgomp1 \
        libsm6 \
        libxext6 \
        libxrender1 \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer is cached unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY src/ .

# Ensure the src directory is on the Python path (imports work without a package install)
ENV PYTHONPATH=/app

EXPOSE 8000

# Copy and use the entrypoint script that waits for PostgreSQL before starting
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
