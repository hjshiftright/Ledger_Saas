"""Tests for ParserRegistry — registration, lookup, and default factory."""

from __future__ import annotations

import pytest

from core.models.enums import SourceType
from modules.parser.base import BaseParser, ExtractionResult
from modules.parser.registry import ParserRegistry


# ── Minimal concrete parser for testing ──────────────────────────────────────

class _DummyParser(BaseParser):
    source_type = SourceType.HDFC_BANK
    version = "0.1"

    def extract(self, batch_id, file_bytes, method) -> ExtractionResult:
        from core.models.raw_parsed_row import ParseMetadata
        from core.models.enums import ExtractionMethod
        return ExtractionResult(rows=[], metadata=ParseMetadata(), method=method, confidence=0.0)


class _AnotherParser(BaseParser):
    source_type = SourceType.SBI_BANK
    version = "0.1"

    def extract(self, batch_id, file_bytes, method) -> ExtractionResult:
        from core.models.raw_parsed_row import ParseMetadata
        return ExtractionResult(rows=[], metadata=ParseMetadata(), method=method, confidence=0.0)


# ── Registration ──────────────────────────────────────────────────────────────

class TestRegistration:
    def test_register_and_get(self):
        registry = ParserRegistry()
        registry.register(SourceType.HDFC_BANK, _DummyParser)
        assert registry.get(SourceType.HDFC_BANK) is not None

    def test_get_returns_none_for_missing(self):
        registry = ParserRegistry()
        assert registry.get(SourceType.HDFC_BANK) is None

    def test_has_returns_true_after_register(self):
        registry = ParserRegistry()
        registry.register(SourceType.HDFC_BANK, _DummyParser)
        assert registry.has(SourceType.HDFC_BANK) is True

    def test_has_returns_false_for_missing(self):
        registry = ParserRegistry()
        assert registry.has(SourceType.UNKNOWN) is False

    def test_registered_types_lists_all(self):
        registry = ParserRegistry()
        registry.register(SourceType.HDFC_BANK, _DummyParser)
        registry.register(SourceType.SBI_BANK, _AnotherParser)
        types = registry.registered_types()
        assert SourceType.HDFC_BANK in types
        assert SourceType.SBI_BANK in types


# ── Lazy instantiation ────────────────────────────────────────────────────────

class TestLazyInstantiation:
    def test_parser_is_instantiated_on_get(self):
        registry = ParserRegistry()
        registry.register(SourceType.HDFC_BANK, _DummyParser)
        parser = registry.get(SourceType.HDFC_BANK)
        assert isinstance(parser, _DummyParser)

    def test_same_instance_returned_each_call(self):
        registry = ParserRegistry()
        registry.register(SourceType.HDFC_BANK, _DummyParser)
        p1 = registry.get(SourceType.HDFC_BANK)
        p2 = registry.get(SourceType.HDFC_BANK)
        assert p1 is p2  # Cached instance

    def test_re_register_clears_cache(self):
        registry = ParserRegistry()
        registry.register(SourceType.HDFC_BANK, _DummyParser)
        old_instance = registry.get(SourceType.HDFC_BANK)
        registry.register(SourceType.HDFC_BANK, _DummyParser)  # Re-register same class
        new_instance = registry.get(SourceType.HDFC_BANK)
        # New instance should be created after re-registration
        assert new_instance is not old_instance


# ── Default factory ───────────────────────────────────────────────────────────

class TestDefaultFactory:
    def test_default_has_hdfc(self):
        registry = ParserRegistry.default()
        assert registry.has(SourceType.HDFC_BANK)

    def test_default_has_sbi(self):
        registry = ParserRegistry.default()
        assert registry.has(SourceType.SBI_BANK)

    def test_default_has_cas_cams(self):
        registry = ParserRegistry.default()
        assert registry.has(SourceType.CAS_CAMS)

    def test_default_has_cas_kfintech(self):
        """CAS_KFINTECH should use CasKfintechParser (not the base CasParser)."""
        from modules.parser.parsers.cas_cams import CasKfintechParser
        registry = ParserRegistry.default()
        assert registry.has(SourceType.CAS_KFINTECH)
        parser = registry.get(SourceType.CAS_KFINTECH)
        assert isinstance(parser, CasKfintechParser)

    def test_default_has_generic_csv(self):
        registry = ParserRegistry.default()
        assert registry.has(SourceType.GENERIC_CSV)

    def test_default_has_hdfc_csv(self):
        registry = ParserRegistry.default()
        assert registry.has(SourceType.HDFC_BANK_CSV)

    def test_default_has_all_bank_csv_types(self):
        """All 6 bank CSV source types must be registered with GenericCsvParser."""
        from modules.parser.parsers.generic_csv import GenericCsvParser
        registry = ParserRegistry.default()
        for st in (
            SourceType.HDFC_BANK_CSV,
            SourceType.SBI_BANK_CSV,
            SourceType.ICICI_BANK_CSV,
            SourceType.AXIS_BANK_CSV,
            SourceType.KOTAK_BANK_CSV,
            SourceType.IDFC_BANK_CSV,
        ):
            assert registry.has(st), f"Missing: {st.value}"
            assert isinstance(registry.get(st), GenericCsvParser), f"{st.value} not using GenericCsvParser"

    def test_default_has_zerodha_types(self):
        registry = ParserRegistry.default()
        for st in (
            SourceType.ZERODHA_HOLDINGS,
            SourceType.ZERODHA_TRADEBOOK,
            SourceType.ZERODHA_TAX_PNL,
            SourceType.ZERODHA_CAPITAL_GAINS,
        ):
            assert registry.has(st), f"Missing: {st.value}"

    def test_unknown_not_registered(self):
        registry = ParserRegistry.default()
        assert not registry.has(SourceType.UNKNOWN)
        assert registry.get(SourceType.UNKNOWN) is None
