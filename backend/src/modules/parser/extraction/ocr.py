"""OCR extraction — renders PDF pages to images and runs Tesseract.

Used as the third fallback for scanned / image-only PDFs.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# Optional imports — graceful degradation
try:
    import pytesseract  # type: ignore[import-untyped]
    from PIL import Image  # type: ignore[import-untyped]
    import io as _io
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logger.debug("pytesseract / Pillow not installed — OCR extraction unavailable.")


class OCRExtractor:
    """Renders each PDF page to an image and runs Tesseract OCR.

    Supported languages: English + Hindi ('eng+hin').
    Falls back to 'eng' only if 'hin' language pack is not installed.
    """

    DEFAULT_DPI: int = 200
    _NOISE_PATTERN = re.compile(r"[^\x20-\x7E\u0900-\u097F\n]")  # Keep ASCII + Devanagari

    def __init__(self, dpi: int = DEFAULT_DPI) -> None:
        self.dpi = dpi

    def extract_pages(self, file_bytes: bytes) -> list[str]:
        """OCR every page and return text per page.

        Returns an empty list if Tesseract is not available or rendering fails.
        """
        if not TESSERACT_AVAILABLE:
            logger.warning("OCRExtractor: pytesseract not available.")
            return []

        try:
            from core.utils.pdf_utils import render_all_pages_to_png
            png_pages = render_all_pages_to_png(file_bytes, dpi=self.dpi)
        except ImportError as exc:
            logger.warning("OCRExtractor: PyMuPDF not available for rendering: %s", exc)
            return []
        except Exception as exc:  # noqa: BLE001
            logger.warning("OCRExtractor: page rendering failed: %s", exc)
            return []

        results: list[str] = []
        lang = self._available_lang()
        for i, png_bytes in enumerate(png_pages):
            try:
                img = Image.open(_io.BytesIO(png_bytes))
                text: str = pytesseract.image_to_string(img, lang=lang, config="--psm 6")
                text = self._clean_ocr_output(text)
                results.append(text)
            except Exception as exc:  # noqa: BLE001
                exc_str = str(exc)
                # Tesseract binary missing — log once and stop trying all pages
                if "tesseract is not installed" in exc_str.lower() or "not found" in exc_str.lower():
                    logger.warning(
                        "OCRExtractor: tesseract binary not installed or not in PATH "
                        "(skipping remaining pages). "
                        "Install from https://github.com/UB-Mannheim/tesseract/wiki"
                    )
                    return []
                logger.warning("OCRExtractor: page %d failed: %s", i, exc)
                results.append("")

        return results

    def extract_combined(self, file_bytes: bytes) -> str:
        """Return OCR text from all pages joined with newlines."""
        return "\n".join(self.extract_pages(file_bytes))

    # ── Private ───────────────────────────────────────────────────────────────

    @staticmethod
    def _available_lang() -> str:
        try:
            langs = pytesseract.get_languages()
            return "eng+hin" if "hin" in langs else "eng"
        except Exception:  # noqa: BLE001
            return "eng"

    def _clean_ocr_output(self, text: str) -> str:
        """Remove common OCR noise characters while preserving Devanagari."""
        text = self._NOISE_PATTERN.sub("", text)
        # Collapse multiple spaces to single space
        text = re.sub(r"  +", " ", text)
        return text.strip()
