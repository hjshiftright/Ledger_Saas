"""Table structure extraction — uses Camelot (lattice) or pdfplumber (stream)."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Optional imports — graceful degradation
try:
    import camelot  # type: ignore[import-untyped]
    CAMELOT_AVAILABLE = True
except ImportError:
    CAMELOT_AVAILABLE = False
    logger.debug("camelot-py not installed — lattice table extraction unavailable.")

try:
    from core.utils.pdf_utils import extract_tables_per_page, PDFPLUMBER_AVAILABLE
except ImportError:
    PDFPLUMBER_AVAILABLE = False


class TableExtractor:
    """Extracts tables from a PDF using Camelot (lattice mode) or pdfplumber (stream).

    Camelot is preferred for bordered/ruled tables (most bank statements).
    pdfplumber stream mode is the fallback for statement-style whitespace-delimited tables.

    Returns tables as lists of rows, where each row is a list of cell strings.
    """

    def extract_tables(
        self,
        file_bytes: bytes,
        method: str = "auto",
    ) -> list[list[list[str]]]:
        """Extract all tables from the document.

        Args:
            file_bytes: Raw PDF bytes.
            method: "lattice" (Camelot bordered), "stream" (pdfplumber), or
                    "auto" (try lattice first, fall back to stream).

        Returns:
            List of tables. Each table is a list of rows. Each row is a list
            of cell strings (empty string for empty cells).
        """
        if method in ("lattice", "auto") and CAMELOT_AVAILABLE:
            tables = self._extract_camelot(file_bytes, flavor="lattice")
            if tables:
                return tables
            if method == "auto":
                logger.debug("TableExtractor: lattice found no tables; trying stream.")

        if method in ("stream", "auto") and PDFPLUMBER_AVAILABLE:
            tables = self._extract_pdfplumber_stream(file_bytes)
            logger.info("TableExtractor: pdfplumber found %d table(s)", len(tables))
            return tables

        logger.warning(
            "TableExtractor: no extraction library available (camelot=%s, pdfplumber=%s)",
            CAMELOT_AVAILABLE,
            PDFPLUMBER_AVAILABLE,
        )
        return []

    # ── Private ───────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_camelot(file_bytes: bytes, flavor: str = "lattice") -> list[list[list[str]]]:
        """Use Camelot to extract tables. Camelot requires a file path.

        We write to a temp file because Camelot does not accept bytes directly.
        """
        import io
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        try:
            tables = camelot.read_pdf(tmp_path, pages="all", flavor=flavor)
            result: list[list[list[str]]] = []
            for table in tables:
                df = table.df
                rows = [[str(cell) for cell in row] for row in df.values.tolist()]
                result.extend([rows])
            return result
        except Exception as exc:  # noqa: BLE001
            logger.warning("Camelot extraction failed: %s", exc)
            return []
        finally:
            os.unlink(tmp_path)

    @staticmethod
    def _extract_pdfplumber_stream(file_bytes: bytes) -> list[list[list[str]]]:
        """Extract tables using pdfplumber (stream / whitespace heuristics)."""
        try:
            raw_pages = extract_tables_per_page(file_bytes)
        except Exception as exc:  # noqa: BLE001
            logger.warning("pdfplumber table extraction failed: %s", exc)
            return []

        result: list[list[list[str]]] = []
        for page_tables in raw_pages:
            for table in page_tables:
                cleaned = [
                    [str(cell) if cell is not None else "" for cell in row]
                    for row in table
                ]
                result.append(cleaned)
        return result
