"""Text layer extraction — reads embedded text from a PDF using pdfplumber."""

from __future__ import annotations

import logging
from typing import Callable

from core.utils.pdf_utils import extract_text_per_page

logger = logging.getLogger(__name__)


class TextLayerExtractor:
    """Extracts embedded text from a PDF, page by page.

    This is the fastest and most accurate extraction method, but only works
    on digitally generated PDFs (not scanned / image PDFs).

    The extractor is intentionally stateless — construct once and call
    `extract_pages()` multiple times if needed.
    """

    def extract_pages(self, file_bytes: bytes) -> list[str]:
        """Return the text content of each page as a list of strings.

        Returns an empty list if extraction fails (missing library, encrypted
        file, or zero-content PDF).

        Args:
            file_bytes: Raw PDF bytes.

        Returns:
            List of page text strings (one entry per page).
        """
        try:
            pages = extract_text_per_page(file_bytes)
            logger.debug("TextLayerExtractor: extracted %d pages", len(pages))
            return pages
        except ImportError as exc:
            logger.warning("TextLayerExtractor: pdfplumber not available: %s", exc)
            return []
        except Exception as exc:  # noqa: BLE001
            logger.warning("TextLayerExtractor: failed to extract text: %s", exc)
            return []

    def extract_combined(self, file_bytes: bytes) -> str:
        """Return all page text joined with newlines."""
        return "\n".join(self.extract_pages(file_bytes))

    def has_meaningful_text(self, file_bytes: bytes, min_chars_per_page: int = 100) -> bool:
        """Return True if the PDF has enough embedded text to be worth parsing.

        Used to decide whether to skip directly to OCR/LLM for image-only PDFs.
        """
        pages = self.extract_pages(file_bytes)
        if not pages:
            return False
        avg_chars = sum(len(p) for p in pages) / len(pages)
        return avg_chars >= min_chars_per_page
