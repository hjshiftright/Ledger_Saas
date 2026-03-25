"""Tests for all four Zerodha CSV parsers — parse_dataframe() pure functions
and multi-sheet Tax P&L v2 sheet parsers.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

pytest.importorskip("pandas")
import pandas as pd  # noqa: E402 (after importorskip guard)

from core.models.enums import SourceType, TxnTypeHint
from modules.parser.parsers.zerodha_csv import (
    ZerodhaHoldingsParser,
    ZerodhaTradebookParser,
    ZerodhaTaxPnlParser,
    ZerodhaCapitalGainsParser,
)


@pytest.fixture
def batch_id() -> str:
    return str(uuid.uuid4())


# ── ZerodhaHoldingsParser ─────────────────────────────────────────────────────

class TestHoldingsParser:
    def _make_df(self, rows: list[dict]) -> pd.DataFrame:
        return pd.DataFrame(rows)

    def test_basic_row_extraction(self, batch_id):
        df = self._make_df([
            {"Instrument": "INFY", "ISIN": "INE009A01021", "Qty.": "100",
             "Avg. cost": "1500.50", "Cur. val": "160000.00"},
            {"Instrument": "RELIANCE", "ISIN": "INE002A01018", "Qty.": "50",
             "Avg. cost": "2400.00", "Cur. val": "130000.00"},
        ])
        rows, errors = ZerodhaHoldingsParser.parse_dataframe(batch_id, df)
        assert len(rows) == 2
        assert errors == []

    def test_source_type(self, batch_id):
        df = self._make_df([
            {"Instrument": "TCS", "ISIN": "INE467B01029", "Qty.": "10",
             "Avg. cost": "3500.00", "Cur. val": "38000.00"},
        ])
        rows, _ = ZerodhaHoldingsParser.parse_dataframe(batch_id, df)
        assert rows[0].source_type == SourceType.ZERODHA_HOLDINGS

    def test_isin_stored(self, batch_id):
        df = self._make_df([
            {"Instrument": "HDFC", "ISIN": "INE001A01036", "Qty.": "20",
             "Avg. cost": "1600.00", "Cur. val": "35000.00"},
        ])
        rows, _ = ZerodhaHoldingsParser.parse_dataframe(batch_id, df)
        assert rows[0].fund_isin == "INE001A01036"

    def test_narration_is_instrument(self, batch_id):
        df = self._make_df([
            {"Instrument": "WIPRO", "ISIN": "INE075A01022", "Qty.": "30",
             "Avg. cost": "450.00", "Cur. val": "14500.00"},
        ])
        rows, _ = ZerodhaHoldingsParser.parse_dataframe(batch_id, df)
        assert "WIPRO" in rows[0].raw_narration

    def test_missing_instrument_skipped(self, batch_id):
        df = self._make_df([
            {"Instrument": "", "ISIN": "INE000X00000", "Qty.": "10",
             "Avg. cost": "100.00", "Cur. val": "1000.00"},
        ])
        rows, errors = ZerodhaHoldingsParser.parse_dataframe(batch_id, df)
        assert len(rows) == 0
        assert len(errors) == 1

    def test_row_numbers_sequential(self, batch_id):
        df = self._make_df([
            {"Instrument": f"STOCK{i}", "ISIN": f"IN{i:012d}", "Qty.": "10",
             "Avg. cost": "100.00", "Cur. val": "1050.00"}
            for i in range(1, 4)
        ])
        rows, _ = ZerodhaHoldingsParser.parse_dataframe(batch_id, df)
        for i, row in enumerate(rows, start=1):
            assert row.row_number == i

    def test_batch_id_propagated(self, batch_id):
        df = self._make_df([
            {"Instrument": "INFY", "ISIN": "INE009A01021", "Qty.": "5",
             "Avg. cost": "1500.00", "Cur. val": "8000.00"},
        ])
        rows, _ = ZerodhaHoldingsParser.parse_dataframe(batch_id, df)
        assert rows[0].batch_id == batch_id


# ── ZerodhaTradebookParser ────────────────────────────────────────────────────

class TestTradebookParser:
    def _make_df(self, rows: list[dict]) -> pd.DataFrame:
        return pd.DataFrame(rows)

    def test_buy_row(self, batch_id):
        df = self._make_df([
            {"symbol": "INFY", "isin": "INE009A01021", "trade_date": "2026-01-10",
             "trade_type": "BUY", "quantity": "100", "price": "1500.00", "trade_value": "150000.00"},
        ])
        rows, errors = ZerodhaTradebookParser.parse_dataframe(batch_id, df)
        assert len(rows) == 1
        row = rows[0]
        assert row.txn_type_hint == TxnTypeHint.PURCHASE
        assert row.raw_credit == "150000.00"   # BUY → credit (outflow)
        assert errors == []

    def test_sell_row(self, batch_id):
        df = self._make_df([
            {"symbol": "TCS", "isin": "INE467B01029", "trade_date": "2026-01-15",
             "trade_type": "SELL", "quantity": "50", "price": "3500.00", "trade_value": "175000.00"},
        ])
        rows, errors = ZerodhaTradebookParser.parse_dataframe(batch_id, df)
        assert len(rows) == 1
        row = rows[0]
        assert row.txn_type_hint == TxnTypeHint.REDEMPTION
        assert row.raw_debit == "175000.00"    # SELL → debit (inflow)

    def test_source_type(self, batch_id):
        df = self._make_df([
            {"symbol": "WIPRO", "isin": "INE075A01022", "trade_date": "2026-02-01",
             "trade_type": "BUY", "quantity": "10", "price": "450.00", "trade_value": "4500.00"},
        ])
        rows, _ = ZerodhaTradebookParser.parse_dataframe(batch_id, df)
        assert rows[0].source_type == SourceType.ZERODHA_TRADEBOOK

    def test_missing_trade_date_skipped(self, batch_id):
        df = self._make_df([
            {"symbol": "X", "isin": "INE000X00000", "trade_date": "",
             "trade_type": "BUY", "quantity": "1", "price": "100.00", "trade_value": "100.00"},
        ])
        rows, errors = ZerodhaTradebookParser.parse_dataframe(batch_id, df)
        assert len(rows) == 0
        assert len(errors) == 1

    def test_multiple_rows(self, batch_id):
        df = self._make_df([
            {"symbol": f"STOCK{i}", "isin": f"IN{i:012d}", "trade_date": "2026-01-0" + str(i),
             "trade_type": "BUY", "quantity": "10", "price": "100.00", "trade_value": "1000.00"}
            for i in range(1, 5)
        ])
        rows, _ = ZerodhaTradebookParser.parse_dataframe(batch_id, df)
        assert len(rows) == 4


# ── ZerodhaTaxPnlParser ───────────────────────────────────────────────────────

class TestTaxPnlParser:
    def _make_df(self, rows: list[dict]) -> pd.DataFrame:
        return pd.DataFrame(rows)

    def test_basic_row(self, batch_id):
        df = self._make_df([
            {"symbol": "INFY", "isin": "INE009A01021",
             "buy_date": "2025-06-01", "sell_date": "2026-01-10",
             "quantity": "100", "buy_price": "1200.00", "sell_price": "1500.00",
             "pnl": "30000.00"},
        ])
        rows, errors = ZerodhaTaxPnlParser.parse_dataframe(batch_id, df)
        assert len(rows) == 1
        assert errors == []

    def test_source_type(self, batch_id):
        df = self._make_df([
            {"symbol": "TCS", "isin": "INE467B01029",
             "buy_date": "2025-01-01", "sell_date": "2026-01-01",
             "quantity": "10", "buy_price": "3000.00", "sell_price": "3500.00",
             "pnl": "5000.00"},
        ])
        rows, _ = ZerodhaTaxPnlParser.parse_dataframe(batch_id, df)
        assert rows[0].source_type == SourceType.ZERODHA_TAX_PNL

    def test_missing_sell_date_skipped(self, batch_id):
        df = self._make_df([
            {"symbol": "X", "isin": "INE000X00000",
             "buy_date": "2025-01-01", "sell_date": "",
             "quantity": "1", "buy_price": "100.00", "sell_price": "110.00",
             "pnl": "10.00"},
        ])
        rows, errors = ZerodhaTaxPnlParser.parse_dataframe(batch_id, df)
        assert len(rows) == 0

    def test_isin_stored(self, batch_id):
        df = self._make_df([
            {"symbol": "WIPRO", "isin": "INE075A01022",
             "buy_date": "2025-03-01", "sell_date": "2026-01-15",
             "quantity": "20", "buy_price": "400.00", "sell_price": "500.00",
             "pnl": "2000.00"},
        ])
        rows, _ = ZerodhaTaxPnlParser.parse_dataframe(batch_id, df)
        assert rows[0].fund_isin == "INE075A01022"


# ── ZerodhaCapitalGainsParser ─────────────────────────────────────────────────

class TestCapitalGainsParser:
    def _make_df(self, rows: list[dict]) -> pd.DataFrame:
        return pd.DataFrame(rows)

    def test_basic_row(self, batch_id):
        df = self._make_df([
            {"symbol": "INFY", "isin": "INE009A01021",
             "buy_date": "2024-01-01", "sell_date": "2026-01-01",
             "quantity": "100", "buy_value": "120000.00", "sell_value": "150000.00",
             "gain": "30000.00"},
        ])
        rows, errors = ZerodhaCapitalGainsParser.parse_dataframe(batch_id, df)
        assert len(rows) == 1
        assert errors == []

    def test_source_type(self, batch_id):
        df = self._make_df([
            {"symbol": "RELIANCE", "isin": "INE002A01018",
             "buy_date": "2024-06-01", "sell_date": "2026-01-01",
             "quantity": "50", "buy_value": "100000.00", "sell_value": "120000.00",
             "gain": "20000.00"},
        ])
        rows, _ = ZerodhaCapitalGainsParser.parse_dataframe(batch_id, df)
        assert rows[0].source_type == SourceType.ZERODHA_CAPITAL_GAINS

    def test_missing_sell_date_skipped(self, batch_id):
        df = self._make_df([
            {"symbol": "X", "isin": "INE000X00000",
             "buy_date": "2024-01-01", "sell_date": "",
             "quantity": "1", "buy_value": "100.00", "sell_value": "110.00",
             "gain": "10.00"},
        ])
        rows, errors = ZerodhaCapitalGainsParser.parse_dataframe(batch_id, df)
        assert len(rows) == 0

    def test_gain_row_narration(self, batch_id):
        df = self._make_df([
            {"symbol": "HDFC", "isin": "INE001A01036",
             "buy_date": "2024-03-01", "sell_date": "2026-01-01",
             "quantity": "25", "buy_value": "40000.00", "sell_value": "50000.00",
             "gain": "10000.00"},
        ])
        rows, _ = ZerodhaCapitalGainsParser.parse_dataframe(batch_id, df)
        assert "HDFC" in rows[0].raw_narration


# ── ZerodhaTaxPnlParser — multi-sheet v2 ─────────────────────────────────────

def _make_raw_df(rows: list[list]) -> pd.DataFrame:
    """Build a raw (no-header) DataFrame like ExcelFile.parse(header=None)."""
    return pd.DataFrame(rows, dtype=str)


class TestTaxPnlMultiSheet:
    """Tests for the v2 multi-sheet Tax P&L sheet parsers."""

    # ── _find_header_row & _make_df_from_header_row ──────────────────────────

    def test_find_header_row_basic(self):
        df = _make_raw_df([
            ["Preamble", None, None],
            ["Client ID", "XYZ", None],
            ["Symbol", "ISIN", "Entry Date", "Exit Date", "Quantity"],
            ["INFY", "INE009A01021", "2025-01-01", "2026-01-10", "100"],
        ])
        ri = ZerodhaTaxPnlParser._find_header_row(df, {"symbol", "isin", "entry date", "exit date"})
        assert ri == 2

    def test_find_header_row_missing_returns_none(self):
        df = _make_raw_df([
            ["Preamble", None, None],
            ["Client ID", "XYZ", None],
        ])
        ri = ZerodhaTaxPnlParser._find_header_row(df, {"symbol", "isin", "exit date"})
        assert ri is None

    # ── _parse_tradewise ──────────────────────────────────────────────────────

    def _make_tradewise_df(self, data_rows: list[list]) -> pd.DataFrame:
        """Build raw df with preamble + header + data for the tradewise sheet."""
        preamble = [
            ["Client ID", "XYZ123", None, None, None, None, None, None],
            ["Client Name", "Test User", None, None, None, None, None, None],
        ]
        header = [["Symbol", "ISIN", "Entry Date", "Exit Date", "Quantity",
                   "Buy Value", "Sell Value", "Profit"]]
        return _make_raw_df(preamble + header + data_rows)

    def test_tradewise_basic_row(self, batch_id):
        df = self._make_tradewise_df([
            ["INFY", "INE009A01021", "2025-06-01", "2026-01-10", "100",
             "120000", "150000", "30000"],
        ])
        rows, errors = ZerodhaTaxPnlParser._parse_tradewise(batch_id, df, "Tradewise Exits")
        assert len(rows) == 1
        assert errors == []
        row = rows[0]
        assert row.source_type == SourceType.ZERODHA_TAX_PNL_TRADEWISE
        assert row.txn_type_hint == TxnTypeHint.REDEMPTION
        assert row.raw_date == "2026-01-10"
        assert "INFY" in row.raw_narration
        assert row.fund_isin == "INE009A01021"

    def test_tradewise_skips_repeat_header_rows(self, batch_id):
        """Sub-section repeat header rows (Symbol == 'Symbol') must be silently skipped."""
        df = self._make_tradewise_df([
            # Sub-section title
            ["Equity - Short Term", None, None, None, None, None, None, None],
            # Repeat of column header row within sub-section
            ["Symbol", "ISIN", "Entry Date", "Exit Date", "Quantity",
             "Buy Value", "Sell Value", "Profit"],
            # Actual data
            ["TCS", "INE467B01029", "2025-03-01", "2026-01-20", "50",
             "170000", "195000", "25000"],
        ])
        rows, errors = ZerodhaTaxPnlParser._parse_tradewise(batch_id, df, "Tradewise Exits")
        assert len(rows) == 1
        assert rows[0].raw_narration.startswith("SELL TCS")

    def test_tradewise_multiple_subsections(self, batch_id):
        """Multiple sub-sections (Short Term + Long Term) each with repeat headers."""
        df = self._make_tradewise_df([
            ["Equity - Short Term", None, None, None, None, None, None, None],
            ["Symbol", "ISIN", "Entry Date", "Exit Date", "Quantity", "Buy Value", "Sell Value", "Profit"],
            ["INFY", "INE009A01021", "2025-06-01", "2026-01-10", "100", "120000", "150000", "30000"],
            ["Equity - Long Term", None, None, None, None, None, None, None],
            ["Symbol", "ISIN", "Entry Date", "Exit Date", "Quantity", "Buy Value", "Sell Value", "Profit"],
            ["WIPRO", "INE075A01022", "2022-01-01", "2026-02-01", "200", "80000", "110000", "30000"],
        ])
        rows, errors = ZerodhaTaxPnlParser._parse_tradewise(batch_id, df, "Tradewise Exits")
        assert len(rows) == 2
        symbols = {r.fund_isin for r in rows}
        assert "INE009A01021" in symbols
        assert "INE075A01022" in symbols

    def test_tradewise_empty_section_produces_no_rows(self, batch_id):
        """An empty sub-section (title + repeat header but no data) → zero rows."""
        df = self._make_tradewise_df([
            ["Equity - Intraday", None, None, None, None, None, None, None],
            ["Symbol", "ISIN", "Entry Date", "Exit Date", "Quantity", "Buy Value", "Sell Value", "Profit"],
        ])
        rows, errors = ZerodhaTaxPnlParser._parse_tradewise(batch_id, df, "Tradewise Exits")
        assert rows == []
        assert errors == []

    def test_tradewise_profit_in_extra_fields(self, batch_id):
        df = self._make_tradewise_df([
            ["HDFC", "INE001A01036", "2025-01-01", "2026-01-01", "10",
             "16000", "20000", "4000"],
        ])
        rows, _ = ZerodhaTaxPnlParser._parse_tradewise(batch_id, df, "Tradewise Exits")
        assert rows[0].extra_fields["profit"] == "4000"

    # ── _parse_dividends ──────────────────────────────────────────────────────

    def _make_dividend_df(self, data_rows: list[list]) -> pd.DataFrame:
        preamble = [
            ["Client ID", "XYZ123", None, None, None, None],
        ]
        header = [["Symbol", "ISIN", "Ex-date", "Quantity", "Dividend Per Share", "Net Dividend Amount"]]
        return _make_raw_df(preamble + header + data_rows)

    def test_dividends_basic_row(self, batch_id):
        df = self._make_dividend_df([
            ["INFY", "INE009A01021", "2025-08-14", "100", "10", "1000"],
        ])
        rows, errors = ZerodhaTaxPnlParser._parse_dividends(batch_id, df, "Equity Dividends")
        assert len(rows) == 1
        assert errors == []
        row = rows[0]
        assert row.txn_type_hint == TxnTypeHint.DIVIDEND_PAYOUT
        assert row.raw_date == "2025-08-14"
        assert row.raw_credit == "1000"
        assert row.fund_isin == "INE009A01021"

    def test_dividends_skips_total_row(self, batch_id):
        """'Total Dividend Amount' summary row at end must be skipped."""
        df = self._make_dividend_df([
            ["INFY", "INE009A01021", "2025-08-14", "100", "10", "1000"],
            ["Total Dividend Amount", "1000", None, None, None, None],
        ])
        rows, errors = ZerodhaTaxPnlParser._parse_dividends(batch_id, df, "Equity Dividends")
        assert len(rows) == 1

    def test_dividends_skips_repeat_header(self, batch_id):
        df = self._make_dividend_df([
            ["Symbol", "ISIN", "Ex-date", "Quantity", "Dividend Per Share", "Net Dividend Amount"],
            ["INFY", "INE009A01021", "2025-08-14", "100", "10", "1000"],
        ])
        rows, _ = ZerodhaTaxPnlParser._parse_dividends(batch_id, df, "Equity Dividends")
        assert len(rows) == 1

    def test_dividends_dedup_key_in_extra_fields(self, batch_id):
        df = self._make_dividend_df([
            ["INFY", "INE009A01021", "2025-08-14", "100", "10", "1000"],
        ])
        rows, _ = ZerodhaTaxPnlParser._parse_dividends(batch_id, df, "Equity Dividends")
        key = rows[0].extra_fields["dedup_key"]
        assert "INE009A01021" in key
        assert "2025-08-14" in key

    # ── _parse_charges ────────────────────────────────────────────────────────

    def _make_charges_df(self, data_rows: list[list]) -> pd.DataFrame:
        preamble = [
            ["Client ID", "XYZ123", None, None],
            ["Equity", None, None, None],
        ]
        header = [["Particulars", "Posting Date", "Debit", "Credit"]]
        return _make_raw_df(preamble + header + data_rows)

    def test_charges_debit_row(self, batch_id):
        df = self._make_charges_df([
            ["AMC Fee Q1", "2025-08-01", "88.5", "0"],
        ])
        rows, errors = ZerodhaTaxPnlParser._parse_charges(batch_id, df, "Other Debits and Credits")
        assert len(rows) == 1
        assert errors == []
        row = rows[0]
        assert row.raw_debit == "88.5"
        assert row.raw_credit is None  # 0 is treated as None

    def test_charges_skips_repeat_header_rows(self, batch_id):
        """Sub-section repeat header 'Particulars / Posting Date' must be skipped."""
        df = self._make_charges_df([
            ["AMC Fee", "2025-08-01", "88.5", "0"],
            ["F&O", None, None, None],           # sub-section title
            ["Particulars", "Posting Date", "Debit", "Credit"],  # repeat header
            ["F&O Charge", "2025-09-01", "50.0", "0"],
        ])
        rows, errors = ZerodhaTaxPnlParser._parse_charges(batch_id, df, "Other Debits and Credits")
        assert len(rows) == 2
        narrations = [r.raw_narration for r in rows]
        assert "AMC Fee" in narrations
        assert "F&O Charge" in narrations

    def test_charges_credit_row(self, batch_id):
        df = self._make_charges_df([
            ["Refund", "2025-11-01", "0", "100"],
        ])
        rows, _ = ZerodhaTaxPnlParser._parse_charges(batch_id, df, "Other Debits and Credits")
        assert len(rows) == 1
        assert rows[0].raw_credit == "100"
        assert rows[0].raw_debit is None

    # ── _parse_open_positions ─────────────────────────────────────────────────

    def _make_positions_df(self, data_rows: list[list]) -> pd.DataFrame:
        preamble = [
            ["Client ID", "XYZ123", None, None, None, None, None, None],
        ]
        header = [["Symbol", "Trade Date", "Exchange", "Instrument Type",
                   "Open Quantity", "Average Price", "Previous Closing Price", "Unrealized Profit"]]
        return _make_raw_df(preamble + header + data_rows)

    def test_open_positions_basic_row(self, batch_id):
        df = self._make_positions_df([
            ["NIFTY25JUN", "2025-06-15", "NFO", "FUT", "50", "24000", "24200", "10000"],
        ])
        rows, errors = ZerodhaTaxPnlParser._parse_open_positions(
            batch_id, df, "Open Positions as of 2026-03-24"
        )
        assert len(rows) == 1
        assert errors == []
        assert rows[0].extra_fields["sheet_type"] == "closing_position"

    def test_open_positions_opening_snapshot_tag(self, batch_id):
        df = self._make_positions_df([
            ["NIFTY25APR", "2025-04-01", "NFO", "FUT", "50", "22000", "22100", "5000"],
        ])
        rows, _ = ZerodhaTaxPnlParser._parse_open_positions(
            batch_id, df, "Open Positions as of 2025-04-01"
        )
        assert rows[0].extra_fields["sheet_type"] == "opening_position"

    def test_open_positions_skips_section_title_rows(self, batch_id):
        """Rows like 'Open Positions for F&O' (sub-section titles) must be skipped."""
        df = self._make_positions_df([
            ["Open Positions for F&O", None, None, None, None, None, None, None],
            ["Symbol", "Trade Date", "Exchange", "Instrument Type",
             "Open Quantity", "Average Price", "Previous Closing Price", "Unrealized Profit"],
            ["NIFTY25JUN", "2025-06-15", "NFO", "FUT", "50", "24000", "24200", "10000"],
        ])
        rows, _ = ZerodhaTaxPnlParser._parse_open_positions(
            batch_id, df, "Open Positions as of 2026-03-24"
        )
        assert len(rows) == 1
        assert rows[0].raw_narration.startswith("OPEN POSITION NIFTY25JUN")

    def test_open_positions_all_empty_returns_nothing(self, batch_id):
        """Empty sheet (only preamble + sub-section headers, no data) → zero rows."""
        df = self._make_positions_df([
            ["Open Positions for F&O", None, None, None, None, None, None, None],
            ["Symbol", "Trade Date", "Exchange", "Instrument Type",
             "Open Quantity", "Average Price", "Previous Closing Price", "Unrealized Profit"],
            ["Open Positions for Currency", None, None, None, None, None, None, None],
            ["Symbol", "Trade Date", "Exchange", "Instrument Type",
             "Open Quantity", "Average Price", "Previous Closing Price", "Unrealized Profit"],
        ])
        rows, _ = ZerodhaTaxPnlParser._parse_open_positions(
            batch_id, df, "Open Positions as of 2026-03-24"
        )
        assert rows == []

    # ── _is_multi_sheet_taxpnl ────────────────────────────────────────────────

    def test_is_multi_sheet_with_known_sheets(self):
        assert ZerodhaTaxPnlParser._is_multi_sheet_taxpnl(
            ["Tradewise Exits from 2025-04-01", "Equity Dividends", "Ledger Balances"]
        )

    def test_is_multi_sheet_false_for_plain_csv(self):
        assert not ZerodhaTaxPnlParser._is_multi_sheet_taxpnl(
            ["Sheet1"]
        )
