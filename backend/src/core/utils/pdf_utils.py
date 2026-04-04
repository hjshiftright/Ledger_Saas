"""PDF utility helpers shared across extraction methods.

Isolates all PDF library imports so they can be mocked in tests.
All functions take `file_bytes: bytes` — no file-system reads here.
"""

from __future__ import annotations

import hashlib
import io
import logging
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

# ── Optional imports — graceful degradation ───────────────────────────────────
try:
    import pdfplumber  # type: ignore[import-untyped]

    PDFPLUMBER_AVAILABLE = True
except ImportError:  # pragma: no cover
    PDFPLUMBER_AVAILABLE = False
    logger.warning("pdfplumber not installed — text-layer extraction unavailable.")

try:
    import fitz  # PyMuPDF  # type: ignore[import-untyped]

    PYMUPDF_AVAILABLE = True
except ImportError:  # pragma: no cover
    PYMUPDF_AVAILABLE = False
    logger.warning("PyMuPDF not installed — page rendering and encryption check unavailable.")


# ── File hashing ──────────────────────────────────────────────────────────────


def compute_file_hash(file_bytes: bytes) -> str:
    """Return the SHA-256 hex digest of raw file bytes."""
    return hashlib.sha256(file_bytes).hexdigest()


# ── Encryption ────────────────────────────────────────────────────────────────


def is_pdf_encrypted(file_bytes: bytes) -> bool:
    """Return True if the PDF requires a password to open.

    Uses PyMuPDF when available; falls back to naive byte scan.
    """
    if PYMUPDF_AVAILABLE:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        result: bool = doc.needs_pass
        doc.close()
        return result
    # Naive fallback: check for /Encrypt xref entry in file header
    return b"/Encrypt" in file_bytes[:4096]


def decrypt_pdf_bytes(file_bytes: bytes, password: str) -> bytes:
    """Decrypt an encrypted PDF and return the plain (unencrypted) bytes.

    The returned bytes are a fully in-memory copy with encryption stripped,
    safe to pass directly to pdfplumber / fitz / OCR without any password.

    Args:
        file_bytes: Raw (possibly encrypted) PDF bytes.
        password:   Owner or user password string.

    Returns:
        Unencrypted PDF bytes.

    Raises:
        ImportError: If PyMuPDF is not installed.
        ValueError:  If the password is incorrect (error code WRONG_PASSWORD)
                     or the PDF is not encrypted (error code NOT_ENCRYPTED).
    """
    if not PYMUPDF_AVAILABLE:
        raise ImportError(
            "PyMuPDF is required for PDF decryption. Install with: pip install PyMuPDF"
        )
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    try:
        if not doc.needs_pass:
            raise ValueError("NOT_ENCRYPTED")
        if not doc.authenticate(password):
            raise ValueError("WRONG_PASSWORD")
        buf = io.BytesIO()
        doc.save(buf, encryption=fitz.PDF_ENCRYPT_NONE)
        return buf.getvalue()
    finally:
        doc.close()


# ── Text extraction ───────────────────────────────────────────────────────────


def extract_text_per_page(file_bytes: bytes, max_pages: int | None = None) -> list[str]:
    """Extract embedded text from each PDF page.

    Uses pdfplumber when available; falls back to PyMuPDF so text-layer parsing
    and source detection still work when only ``PyMuPDF`` is installed.
    """
    if PDFPLUMBER_AVAILABLE:
        pages: list[str] = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for i, page in enumerate(pdf.pages):
                if max_pages is not None and i >= max_pages:
                    break
                text: str = page.extract_text() or ""
                pages.append(text)
        return pages

    if PYMUPDF_AVAILABLE:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        try:
            out: list[str] = []
            n = doc.page_count if max_pages is None else min(doc.page_count, max_pages)
            for i in range(n):
                out.append(doc[i].get_text() or "")
            return out
        finally:
            doc.close()

    raise ImportError(
        "pdfplumber or PyMuPDF is required for text-layer extraction. "
        "Install with: pip install pdfplumber  OR  pip install PyMuPDF"
    )


def extract_tables_per_page(file_bytes: bytes) -> list[list[list[str | None]]]:
    """Extract tables from each PDF page using pdfplumber (stream mode).

    Returns: list[page] → list[table] → list[row] → list[cell_value | None].
    """
    if not PDFPLUMBER_AVAILABLE:
        raise ImportError("pdfplumber is required for table extraction.")
    all_tables: list[list[list[str | None]]] = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables() or []
            all_tables.append(tables)  # type: ignore[arg-type]
    return all_tables


def get_page_count(file_bytes: bytes) -> int:
    """Return the number of pages in a PDF file."""
    if PYMUPDF_AVAILABLE:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        count: int = doc.page_count
        doc.close()
        return count
    if PDFPLUMBER_AVAILABLE:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            return len(pdf.pages)
    raise ImportError("PyMuPDF or pdfplumber is required to count PDF pages.")


# ── Page rendering (for OCR and LLM vision) ───────────────────────────────────


def render_page_to_png(file_bytes: bytes, page_number: int, dpi: int = 200) -> bytes:
    """Render a single PDF page to PNG bytes.

    Args:
        file_bytes: Raw PDF bytes.
        page_number: 0-indexed page number.
        dpi: Rendering resolution (150 = fast/draft, 200 = balanced, 300 = high quality).

    Returns:
        PNG image bytes.

    Raises:
        ImportError: If PyMuPDF is not installed.
        IndexError: If page_number is out of range.
    """
    if not PYMUPDF_AVAILABLE:
        raise ImportError(
            "PyMuPDF is required for page rendering. Install with: pip install PyMuPDF"
        )
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    try:
        if page_number >= doc.page_count:
            raise IndexError(
                f"Page {page_number} out of range (document has {doc.page_count} pages)."
            )
        page = doc[page_number]
        scale = dpi / 72.0
        matrix = fitz.Matrix(scale, scale)
        pixmap = page.get_pixmap(matrix=matrix)
        return pixmap.tobytes("png")
    finally:
        doc.close()


def render_all_pages_to_png(file_bytes: bytes, dpi: int = 200) -> list[bytes]:
    """Render every page to PNG and return as a list of PNG byte arrays."""
    count = get_page_count(file_bytes)
    return [render_page_to_png(file_bytes, i, dpi) for i in range(count)]
