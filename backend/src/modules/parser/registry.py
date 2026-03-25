"""ParserRegistry — maps SourceType to a concrete parser instance.

Usage:
    registry = ParserRegistry.default()
    parser = registry.get(SourceType.HDFC_BANK)
    chain = ExtractionChain(parser, batch_id, file_bytes)
    result = chain.run()
"""

from __future__ import annotations

import logging
from typing import Type

from core.models.enums import SourceType
from modules.parser.base import BaseParser

logger = logging.getLogger(__name__)


class ParserRegistry:
    """Central dispatch table: SourceType → BaseParser subclass.

    Parsers are registered as *classes* (not instances) and instantiated
    lazily on first `get()` call. This keeps the registry lightweight and
    makes it easy to swap implementations in tests.
    """

    def __init__(self) -> None:
        self._registry: dict[SourceType, Type[BaseParser]] = {}
        self._instances: dict[SourceType, BaseParser] = {}

    # ── Registration ──────────────────────────────────────────────────────────

    def register(self, source_type: SourceType, parser_class: Type[BaseParser]) -> None:
        """Register a parser class for a source type.

        Args:
            source_type: The SourceType this parser handles.
            parser_class: A concrete subclass of BaseParser (not an instance).
        """
        if source_type in self._registry:
            logger.warning(
                "ParserRegistry: overwriting existing parser for %s", source_type.value
            )
        self._registry[source_type] = parser_class
        # Clear cached instance so the new class is used on next get()
        self._instances.pop(source_type, None)

    # ── Lookup ────────────────────────────────────────────────────────────────

    def get(self, source_type: SourceType) -> BaseParser | None:
        """Return the parser instance for the given SourceType.

        Returns None if no parser is registered (caller should fall back to
        LLM or return an error to the user).
        """
        if source_type not in self._registry:
            return None
        if source_type not in self._instances:
            self._instances[source_type] = self._registry[source_type]()
        return self._instances[source_type]

    def has(self, source_type: SourceType) -> bool:
        """Return True if a parser is registered for this source type."""
        return source_type in self._registry

    def registered_types(self) -> list[SourceType]:
        """Return all registered SourceTypes."""
        return list(self._registry.keys())

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def default(cls) -> "ParserRegistry":
        """Build and return the default registry with all built-in parsers.

        Imports are deferred here to avoid circular dependencies and to allow
        partial installs (e.g. no camelot) to still work.
        """
        # ── Bank PDF parsers ──────────────────────────────────────────────────
        from modules.parser.parsers.hdfc_pdf    import HdfcPdfParser
        from modules.parser.parsers.sbi_pdf     import SbiPdfParser
        from modules.parser.parsers.icici_pdf   import IciciPdfParser
        from modules.parser.parsers.axis_pdf    import AxisPdfParser
        from modules.parser.parsers.kotak_pdf   import KotakPdfParser
        from modules.parser.parsers.indusind_pdf import IndusIndPdfParser
        from modules.parser.parsers.idfc_pdf    import IdfcPdfParser
        from modules.parser.parsers.union_pdf   import UnionBankPdfParser
        from modules.parser.parsers.yes_cc_pdf   import YesCcPdfParser
        from modules.parser.parsers.icici_cc_pdf  import IciciCcPdfParser
        from modules.parser.parsers.hdfc_cc_pdf   import HdfcCcPdfParser

        # ── Mutual Fund CAS parsers ───────────────────────────────────────────
        from modules.parser.parsers.cas_cams    import CasParser, CasKfintechParser

        # ── CSV / XLS parsers ─────────────────────────────────────────────────
        from modules.parser.parsers.generic_csv import GenericCsvParser
        from modules.parser.parsers.zerodha_csv import (
            ZerodhaHoldingsParser,
            ZerodhaTradebookParser,
            ZerodhaTaxPnlParser,
            ZerodhaCapitalGainsParser,
        )

        registry = cls()

        # Bank PDFs
        registry.register(SourceType.HDFC_BANK,    HdfcPdfParser)
        registry.register(SourceType.SBI_BANK,     SbiPdfParser)
        registry.register(SourceType.ICICI_BANK,   IciciPdfParser)
        registry.register(SourceType.AXIS_BANK,    AxisPdfParser)
        registry.register(SourceType.KOTAK_BANK,   KotakPdfParser)
        registry.register(SourceType.INDUSIND_BANK, IndusIndPdfParser)
        registry.register(SourceType.IDFC_BANK,    IdfcPdfParser)
        registry.register(SourceType.UNION_BANK,   UnionBankPdfParser)
        registry.register(SourceType.YES_BANK_CC,   YesCcPdfParser)
        registry.register(SourceType.ICICI_BANK_CC,  IciciCcPdfParser)
        registry.register(SourceType.HDFC_BANK_CC,   HdfcCcPdfParser)

        # CAS (CAMS + MF Central share CasParser; KFintech gets its own variant)
        registry.register(SourceType.CAS_CAMS,       CasParser)
        registry.register(SourceType.CAS_KFINTECH,   CasKfintechParser)
        registry.register(SourceType.CAS_MF_CENTRAL, CasParser)

        # Bank CSVs — column-mapping via GenericCsvParser
        registry.register(SourceType.HDFC_BANK_CSV,  GenericCsvParser)
        registry.register(SourceType.SBI_BANK_CSV,   GenericCsvParser)
        registry.register(SourceType.ICICI_BANK_CSV, GenericCsvParser)
        registry.register(SourceType.AXIS_BANK_CSV,  GenericCsvParser)
        registry.register(SourceType.KOTAK_BANK_CSV, GenericCsvParser)
        registry.register(SourceType.IDFC_BANK_CSV,  GenericCsvParser)
        registry.register(SourceType.UNION_BANK_CSV, GenericCsvParser)

        # Zerodha — dedicated parsers
        registry.register(SourceType.ZERODHA_HOLDINGS,          ZerodhaHoldingsParser)
        registry.register(SourceType.ZERODHA_TRADEBOOK,         ZerodhaTradebookParser)
        registry.register(SourceType.ZERODHA_TAX_PNL,           ZerodhaTaxPnlParser)
        registry.register(SourceType.ZERODHA_TAX_PNL_TRADEWISE, ZerodhaTaxPnlParser)
        registry.register(SourceType.ZERODHA_TAX_PNL_DIVIDENDS, ZerodhaTaxPnlParser)
        registry.register(SourceType.ZERODHA_TAX_PNL_CHARGES,   ZerodhaTaxPnlParser)
        registry.register(SourceType.ZERODHA_OPEN_POSITIONS,    ZerodhaTaxPnlParser)
        registry.register(SourceType.ZERODHA_CAPITAL_GAINS,     ZerodhaCapitalGainsParser)

        # Generic fallback
        registry.register(SourceType.GENERIC_CSV, GenericCsvParser)
        registry.register(SourceType.GENERIC_XLS, GenericCsvParser)

        return registry
