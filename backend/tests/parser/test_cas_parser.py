"""Tests for CasCamsParser.parse_text_content() — pure function, no I/O."""

from __future__ import annotations

import uuid

import pytest

from core.models.enums import ExtractionMethod, SourceType, TxnTypeHint
from modules.parser.parsers.cas_cams import CasParser, CasKfintechParser


@pytest.fixture
def parser() -> CasParser:
    return CasParser()


@pytest.fixture
def batch_id() -> str:
    return str(uuid.uuid4())


# ── Text fixtures ─────────────────────────────────────────────────────────────
# CAS format: DD-Mon-YYYY | TxnType | Amount | Units | Price | Unit Balance

CAS_SINGLE_PURCHASE = """\
CAS Statement
Name: John Doe  PAN: ABCDE1234F
Period: 01/01/2026 - 31/01/2026

Folio No: 1234567890 / HDFC Mutual Fund
Scheme: HDFC Top 100 Fund - Direct Growth (ISIN: INF179KB01BD)
Opening Balance: 100.000 Units @ 250.00 = 25,000.00

01-Jan-2026 Purchase-SIP 5,000.00 18.345 272.5400 118.345

"""

CAS_SINGLE_REDEMPTION = """\
CAS Statement
Folio No: 1234567890 / HDFC Mutual Fund
Scheme: HDFC Top 100 Fund - Direct Growth (ISIN: INF179KB01BD)
Opening Balance: 118.345 Units @ 280.00 = 33,136.60

15-Jan-2026 Redemption 10,000.00 35.200 284.0900 83.145

"""

CAS_MULTI_SCHEME = """\
CAS Statement
Name: Jane Doe  PAN: XYZAB5678G
Period: 01/01/2026 - 31/03/2026

Folio No: 1111111111 / ICICI Prudential
Scheme: ICICI Pru Bluechip Fund - Direct Growth (ISIN: INF109K01Z16)
Opening Balance: 200.000 Units @ 60.00 = 12,000.00

05-Jan-2026 Purchase-SIP 3,000.00 48.387 62.0000 248.387
15-Feb-2026 Redemption 5,000.00 78.740 63.5000 169.647

Folio No: 2222222222 / SBI Mutual Fund
Scheme: SBI Large & Midcap Fund - Direct Growth (ISIN: INF200K01RJ0)
Opening Balance: 150.000 Units @ 100.00 = 15,000.00

01-Mar-2026 Purchase-SIP 5,000.00 48.077 104.0000 198.077
20-Mar-2026 SIP 4,000.00 37.313 107.2000 235.390

"""

CAS_WITH_DIVIDEND = """\
CAS Statement
Folio No: 3333333333 / Axis Mutual Fund
Scheme: Axis Long Term Equity Fund - Regular Growth (ISIN: INF846K01EW2)
Opening Balance: 500.000 Units @ 50.00 = 25,000.00

10-Jan-2026 Purchase-SIP 5,000.00 96.899 51.6000 596.899
25-Jan-2026 Dividend Payout 1,500.00 0.000 0.0000 596.899
28-Jan-2026 Redemption 20,000.00 376.647 53.1000 220.252

"""

CAS_EMPTY = "CAS Statement\n\nNo transactions found for the selected period."

CAS_SLASH_DATE = """\
CAS Statement
Folio No: 9999999999 / Test Fund
Scheme: Test Scheme (ISIN: INF000T00001)
Opening Balance: 50.000 Units @ 100.00 = 5,000.00

01/01/2026 Purchase 2,000.00 19.608 102.0000 69.608

"""


# ── Row extraction ────────────────────────────────────────────────────────────

class TestRowExtraction:
    def test_single_purchase(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, CAS_SINGLE_PURCHASE)
        assert len(result.rows) == 1
        row = result.rows[0]
        assert row.raw_date is not None
        assert row.raw_narration is not None

    def test_single_redemption(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, CAS_SINGLE_REDEMPTION)
        assert len(result.rows) == 1

    def test_multiple_schemes_multiple_rows(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, CAS_MULTI_SCHEME)
        assert len(result.rows) == 4

    def test_dividend_row_included(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, CAS_WITH_DIVIDEND)
        assert len(result.rows) == 3

    def test_empty_text_zero_rows(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, CAS_EMPTY)
        assert len(result.rows) == 0

    def test_slash_date_accepted(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, CAS_SLASH_DATE)
        assert len(result.rows) == 1

    def test_source_type(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, CAS_SINGLE_PURCHASE)
        assert all(r.source_type == SourceType.CAS_CAMS for r in result.rows)

    def test_batch_id_propagated(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, CAS_SINGLE_PURCHASE)
        assert all(r.batch_id == batch_id for r in result.rows)

    def test_row_numbers_sequential(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, CAS_MULTI_SCHEME)
        for i, row in enumerate(result.rows, start=1):
            assert row.row_number == i


# ── Transaction type mapping ──────────────────────────────────────────────────

class TestTxnTypeMapping:
    def test_purchase_sip_mapped(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, CAS_SINGLE_PURCHASE)
        assert result.rows[0].txn_type_hint in (TxnTypeHint.PURCHASE, TxnTypeHint.SIP)

    def test_redemption_mapped(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, CAS_SINGLE_REDEMPTION)
        assert result.rows[0].txn_type_hint == TxnTypeHint.REDEMPTION

    def test_dividend_mapped(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, CAS_WITH_DIVIDEND)
        div_rows = [r for r in result.rows if r.txn_type_hint == TxnTypeHint.DIVIDEND_PAYOUT]
        assert len(div_rows) >= 1


# ── Metadata ──────────────────────────────────────────────────────────────────

class TestMetadata:
    def test_confidence_positive(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, CAS_MULTI_SCHEME)
        assert result.confidence > 0.0

    def test_confidence_low_for_empty(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, CAS_EMPTY)
        assert result.confidence <= 0.15

    def test_total_rows_matches(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, CAS_WITH_DIVIDEND)
        assert result.metadata.total_rows_found == len(result.rows)

    def test_method_text_layer(self, parser, batch_id):
        result = parser.parse_text_content(batch_id, CAS_SINGLE_PURCHASE)
        assert result.method == ExtractionMethod.TEXT_LAYER


# ── KFintech variant ──────────────────────────────────────────────────────────

# KFintech uses "Folio: <number>" (no "No") instead of "Folio No: <number>"
KFINTECH_SINGLE_PURCHASE = """\
KFintech CAS Statement
Name: Priya Sharma  PAN: FGHIJ5678K

Folio: 9876543210 / Mirae Asset
Scheme: Mirae Asset Large Cap Fund - Direct Growth (ISIN: INF769K01010)
Opening Balance: 80.000 Units @ 60.00 = 4,800.00

05-Jan-2026 Purchase-SIP 3,000.00 48.387 62.0000 128.387

"""

KFINTECH_MULTI_TXN = """\
KFintech CAS Statement

Folio: 1122334455 / Kotak Mutual Fund
Scheme: Kotak Emerging Equity Fund - Regular Growth (ISIN: INF174K01LS2)
Opening Balance: 200.000 Units @ 40.00 = 8,000.00

10-Jan-2026 SIP 2,000.00 47.619 42.0000 247.619
20-Jan-2026 Redemption 5,000.00 113.379 44.1000 134.240

"""


class TestCasKfintechParser:
    @pytest.fixture
    def kfintech_parser(self) -> CasKfintechParser:
        return CasKfintechParser()

    def test_source_type_is_kfintech(self, kfintech_parser, batch_id):
        result = kfintech_parser.parse_text_content(batch_id, KFINTECH_SINGLE_PURCHASE)
        assert result.rows, "Expected at least one row from KFintech CAS"
        assert all(r.source_type == SourceType.CAS_KFINTECH for r in result.rows)

    def test_parses_folio_without_no(self, kfintech_parser, batch_id):
        """KFintech 'Folio: <n>' (no 'No') must still be parsed correctly."""
        result = kfintech_parser.parse_text_content(batch_id, KFINTECH_SINGLE_PURCHASE)
        assert len(result.rows) == 1

    def test_multi_txn(self, kfintech_parser, batch_id):
        result = kfintech_parser.parse_text_content(batch_id, KFINTECH_MULTI_TXN)
        assert len(result.rows) == 2

    def test_purchase_debit_set(self, kfintech_parser, batch_id):
        result = kfintech_parser.parse_text_content(batch_id, KFINTECH_SINGLE_PURCHASE)
        row = result.rows[0]
        assert row.raw_debit is not None
        assert row.raw_credit is None

    def test_redemption_credit_set(self, kfintech_parser, batch_id):
        result = kfintech_parser.parse_text_content(batch_id, KFINTECH_MULTI_TXN)
        redemption = result.rows[1]
        assert redemption.raw_credit is not None

    def test_batch_id_propagated(self, kfintech_parser, batch_id):
        result = kfintech_parser.parse_text_content(batch_id, KFINTECH_MULTI_TXN)
        assert all(r.batch_id == batch_id for r in result.rows)

    def test_confidence_positive(self, kfintech_parser, batch_id):
        result = kfintech_parser.parse_text_content(batch_id, KFINTECH_MULTI_TXN)
        assert result.confidence > 0.0

    def test_cams_parser_source_type_unchanged(self, batch_id):
        """CasParser (CAMS variant) rows must still be CAS_CAMS."""
        cams = CasParser()
        result = cams.parse_text_content(batch_id, CAS_SINGLE_PURCHASE)
        assert all(r.source_type == SourceType.CAS_CAMS for r in result.rows)
