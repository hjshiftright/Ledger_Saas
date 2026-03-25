"""Zerodha CSV/XLSX parsers — four formats.

Handles all four Zerodha export formats:
  1. Holdings (portfolio snapshot)
  2. Tradebook (trade history — equity + F&O)
  3. Tax P&L (profit & loss statement)
  4. Capital Gains (CG report)

All are CSV/XLSX files processed with pandas.
Design: parse_dataframe() is the pure, unit-testable function.
"""

from __future__ import annotations

import hashlib
import io
import logging
import re
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING

from core.models.enums import ExtractionMethod, SourceType, TxnTypeHint
from core.models.raw_parsed_row import ParseMetadata, RawParsedRow
from core.utils.confidence import ConfidenceSignals, compute_confidence
from modules.parser.base import BaseParser, ExtractionResult

if TYPE_CHECKING:
    import pandas as pd

logger = logging.getLogger(__name__)


# ── Column header signatures ──────────────────────────────────────────────────

# Holdings: instrument, isin, qty, avg cost, prev close, cur val, p&l, net change %
HOLDINGS_REQUIRED = frozenset({"isin", "instrument", "qty", "avg. cost"})

# Tradebook: symbol, isin, trade_date, trade_type, quantity, price, trade_value
TRADEBOOK_REQUIRED = frozenset({"symbol", "isin", "trade_date", "trade_type", "quantity", "price"})

# Tax P&L: symbol, isin, buy_date, sell_date, quantity, buy_price, sell_price, p&l
TAX_PNL_REQUIRED = frozenset({"symbol", "isin", "buy_date", "sell_date", "quantity"})

# Capital Gains: symbol, isin, buy_date, sell_date, quantity, buy_value, sell_value, gain
CAPITAL_GAINS_REQUIRED = frozenset({"symbol", "isin", "buy_date", "sell_date", "gain"})


def _normalise_headers(headers: list[str]) -> set[str]:
    return {h.strip().lower() for h in headers}


def _detect_zerodha_format(headers: list[str]) -> SourceType:
    """Return the Zerodha SourceType that best matches the headers."""
    norm = _normalise_headers(headers)
    if TRADEBOOK_REQUIRED.issubset(norm):
        return SourceType.ZERODHA_TRADEBOOK
    if HOLDINGS_REQUIRED.issubset(norm):
        return SourceType.ZERODHA_HOLDINGS
    if CAPITAL_GAINS_REQUIRED.issubset(norm):
        return SourceType.ZERODHA_CAPITAL_GAINS
    if TAX_PNL_REQUIRED.issubset(norm):
        return SourceType.ZERODHA_TAX_PNL
    return SourceType.UNKNOWN


def _clean_decimal(raw: str | None) -> Decimal | None:
    if not raw or str(raw).strip().lower() in ("nan", ""):
        return None
    try:
        return Decimal(str(raw).replace(",", "").strip())
    except InvalidOperation:
        return None


# ── Holdings parser ───────────────────────────────────────────────────────────

class ZerodhaHoldingsParser(BaseParser):
    """Parses Zerodha Holdings CSV — portfolio snapshot (no date-based transactions)."""

    source_type = SourceType.ZERODHA_HOLDINGS
    version = "1.0"
    supported_formats = ["CSV", "XLSX"]

    def supported_methods(self) -> list[ExtractionMethod]:
        return [ExtractionMethod.TABLE_EXTRACTION]

    def extract(
        self,
        batch_id: str,
        file_bytes: bytes,
        method: ExtractionMethod,
        filename: str = "file.csv",
    ) -> ExtractionResult:
        try:
            import pandas as pd  # noqa: PLC0415
        except ImportError:
            return self._make_failed_result(batch_id, method, "pandas is required.")

        try:
            df = self._read_file(file_bytes, filename)
        except Exception as exc:  # noqa: BLE001
            return self._make_failed_result(batch_id, method, f"Failed to read file: {exc}")

        rows, errors = self.parse_dataframe(batch_id, df)
        return self._build_result(batch_id, rows, errors, method)

    @staticmethod
    def parse_dataframe(batch_id: str, df: "pd.DataFrame") -> tuple[list[RawParsedRow], list[str]]:
        """Convert a Zerodha Holdings DataFrame into RawParsedRow objects."""
        rows: list[RawParsedRow] = []
        errors: list[str] = []

        # Normalise column names
        df.columns = [c.strip() for c in df.columns]

        for row_num, (_, row) in enumerate(df.iterrows(), start=1):
            instrument = str(row.get("Instrument", row.get("instrument", ""))).strip()
            isin       = str(row.get("ISIN", row.get("isin", ""))).strip()

            if not instrument or instrument.lower() == "nan":
                errors.append(f"Row {row_num}: missing instrument name")
                continue

            qty_raw   = str(row.get("Qty.", row.get("Qty", row.get("qty", "")))).strip()
            avg_cost  = str(row.get("Avg. cost", row.get("avg. cost", ""))).strip()
            cur_val   = str(row.get("Cur. val", row.get("cur. val", ""))).strip()

            rows.append(RawParsedRow(
                batch_id=batch_id,
                source_type=SourceType.ZERODHA_HOLDINGS,
                parser_version="1.0",
                extraction_method=ExtractionMethod.TABLE_EXTRACTION,
                raw_date="",              # Holdings have no transaction date
                raw_narration=instrument,
                raw_quantity=qty_raw or None,
                raw_unit_price=avg_cost or None,
                raw_credit=cur_val or None,   # Current value mapped as "credit" for downstream
                fund_isin=isin or None,
                txn_type_hint=TxnTypeHint.PURCHASE,
                row_confidence=0.9,
                row_number=row_num,
            ))

        return rows, errors

    def _build_result(
        self, batch_id: str, rows: list[RawParsedRow], errors: list[str], method: ExtractionMethod
    ) -> ExtractionResult:
        signals = ConfidenceSignals(
            balance_cross_check_passed=None,
            all_rows_have_valid_date=True,   # Holdings have no date — skip this check
            all_rows_have_amount=bool(rows) and all(r.raw_credit or r.raw_unit_price for r in rows),
            row_count_positive=len(rows) > 0,
            no_row_parse_errors=len(errors) == 0,
        )
        confidence = compute_confidence(signals)
        meta = ParseMetadata(
            total_rows_found=len(rows),
            rows_with_errors=len(errors),
            overall_confidence=confidence,
            warnings=errors,
            extraction_method=method,
            parser_version=self.version,
        )
        return ExtractionResult(rows=rows, metadata=meta, method=method, confidence=confidence)

    @staticmethod
    def _read_file(file_bytes: bytes, filename: str) -> "pd.DataFrame":
        import pandas as pd  # noqa: PLC0415
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext in ("xls", "xlsx"):
            return pd.read_excel(io.BytesIO(file_bytes), dtype=str)
        try:
            return pd.read_csv(io.BytesIO(file_bytes), dtype=str)
        except UnicodeDecodeError:
            return pd.read_csv(io.BytesIO(file_bytes), dtype=str, encoding="latin-1")


# ── Tradebook parser ──────────────────────────────────────────────────────────

class ZerodhaTradebookParser(BaseParser):
    """Parses Zerodha Tradebook CSV — individual equity/F&O trade records."""

    source_type = SourceType.ZERODHA_TRADEBOOK
    version = "1.0"
    supported_formats = ["CSV", "XLSX"]

    def supported_methods(self) -> list[ExtractionMethod]:
        return [ExtractionMethod.TABLE_EXTRACTION]

    def extract(
        self,
        batch_id: str,
        file_bytes: bytes,
        method: ExtractionMethod,
        filename: str = "file.csv",
    ) -> ExtractionResult:
        try:
            import pandas as pd  # noqa: PLC0415
        except ImportError:
            return self._make_failed_result(batch_id, method, "pandas is required.")

        try:
            df = self._read_file(file_bytes, filename)
        except Exception as exc:  # noqa: BLE001
            return self._make_failed_result(batch_id, method, f"Failed to read: {exc}")

        rows, errors = self.parse_dataframe(batch_id, df)
        return self._build_result(batch_id, rows, errors, method)

    @staticmethod
    def parse_dataframe(batch_id: str, df: "pd.DataFrame") -> tuple[list[RawParsedRow], list[str]]:
        rows: list[RawParsedRow] = []
        errors: list[str] = []
        df.columns = [c.strip() for c in df.columns]

        for row_num, (_, row) in enumerate(df.iterrows(), start=1):
            trade_date = str(row.get("trade_date", row.get("Trade Date", ""))).strip()
            if not trade_date or trade_date.lower() == "nan":
                errors.append(f"Row {row_num}: missing trade_date")
                continue

            symbol      = str(row.get("symbol",      row.get("Symbol", ""))).strip()
            isin        = str(row.get("isin",         row.get("ISIN",   ""))).strip()
            trade_type  = str(row.get("trade_type",   row.get("Trade Type", ""))).strip().upper()
            quantity    = str(row.get("quantity",     row.get("Quantity", ""))).strip()
            price       = str(row.get("price",        row.get("Price", ""))).strip()
            trade_value = str(row.get("trade_value",  row.get("Trade Value", ""))).strip()

            # BUY = credit (money spent); SELL = debit (money received)
            is_buy = trade_type.startswith("B")
            raw_credit = trade_value if is_buy  and trade_value and trade_value.lower() != "nan" else None
            raw_debit  = trade_value if not is_buy and trade_value and trade_value.lower() != "nan" else None

            hint = TxnTypeHint.PURCHASE if is_buy else TxnTypeHint.REDEMPTION

            rows.append(RawParsedRow(
                batch_id=batch_id,
                source_type=SourceType.ZERODHA_TRADEBOOK,
                parser_version="1.0",
                extraction_method=ExtractionMethod.TABLE_EXTRACTION,
                raw_date=trade_date,
                raw_narration=f"{trade_type} {symbol}",
                raw_debit=raw_debit,
                raw_credit=raw_credit,
                raw_quantity=quantity or None,
                raw_unit_price=price or None,
                fund_isin=isin or None,
                txn_type_hint=hint,
                row_confidence=0.95,
                row_number=row_num,
            ))

        return rows, errors

    def _build_result(self, batch_id, rows, errors, method) -> ExtractionResult:
        signals = ConfidenceSignals(
            balance_cross_check_passed=None,
            all_rows_have_valid_date=bool(rows) and all(bool(r.raw_date.strip()) for r in rows),
            all_rows_have_amount=bool(rows) and all(r.raw_credit or r.raw_debit for r in rows),
            row_count_positive=len(rows) > 0,
            no_row_parse_errors=len(errors) == 0,
        )
        confidence = compute_confidence(signals)
        dates = [r.raw_date for r in rows if r.raw_date]
        meta = ParseMetadata(
            statement_from=dates[0] if dates else None,
            statement_to=dates[-1] if dates else None,
            total_rows_found=len(rows),
            rows_with_errors=len(errors),
            overall_confidence=confidence,
            warnings=errors,
            extraction_method=method,
            parser_version=self.version,
        )
        return ExtractionResult(rows=rows, metadata=meta, method=method, confidence=confidence)

    @staticmethod
    def _read_file(file_bytes: bytes, filename: str) -> "pd.DataFrame":
        import pandas as pd  # noqa: PLC0415
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext in ("xls", "xlsx"):
            return pd.read_excel(io.BytesIO(file_bytes), dtype=str)
        try:
            return pd.read_csv(io.BytesIO(file_bytes), dtype=str)
        except UnicodeDecodeError:
            return pd.read_csv(io.BytesIO(file_bytes), dtype=str, encoding="latin-1")


# ── Tax P&L parser ────────────────────────────────────────────────────────────

class ZerodhaTaxPnlParser(BaseParser):
    """Parses Zerodha Tax P&L XLSX — multi-sheet format (v2) or legacy CSV (v1).

    Multi-sheet routing (v2 — real Zerodha Tax P&L export):
      • Tradewise Exits  → capital gains rows     (sheet_type=tradewise_exit)
      • Equity Dividends → dividend income rows   (sheet_type=dividend)
      • Other Debits and Credits → broker charges (sheet_type=broker_charge)
      • Open Positions as of <date> → portfolio   (sheet_type=opening/closing_position)
      Aggregate-only sheets (Equity and Non Equity, Mutual Funds, F&O, …) are skipped.

    Legacy single-sheet CSV path (v1) retained for backward compatibility.
    """

    source_type = SourceType.ZERODHA_TAX_PNL
    version = "2.0"
    supported_formats = ["CSV", "XLSX"]

    # Substring → internal sheet type (checked against lowercased sheet name in order)
    _SHEET_TYPE_MAP: list[tuple[str, str]] = [
        ("tradewise exits",         "tradewise"),
        ("equity dividends",        "dividend"),
        ("other debits and credits","charges"),
        ("open positions as of",    "open_position"),
    ]

    # Sheet name substrings to silently skip (aggregate summaries)
    _SKIP_SUBSTRINGS: frozenset[str] = frozenset({
        "equity and non equity", "mutual funds", "f&o",
        "currency", "commodity", "ledger balances",
    })

    def supported_methods(self) -> list[ExtractionMethod]:
        return [ExtractionMethod.TABLE_EXTRACTION]

    # ── public entry point ────────────────────────────────────────────────────

    def extract(
        self,
        batch_id: str,
        file_bytes: bytes,
        method: ExtractionMethod,
        filename: str = "file.xlsx",
    ) -> ExtractionResult:
        try:
            import pandas as pd  # noqa: PLC0415
        except ImportError:
            return self._make_failed_result(batch_id, method, "pandas is required.")

        ext = filename.rsplit(".", 1)[-1].lower()
        if ext in ("xls", "xlsx"):
            try:
                xl = pd.ExcelFile(io.BytesIO(file_bytes))
            except Exception as exc:  # noqa: BLE001
                return self._make_failed_result(batch_id, method, f"Failed to open: {exc}")
            if self._is_multi_sheet_taxpnl(xl.sheet_names):
                return self._extract_multi_sheet(batch_id, xl, method)

        # Legacy CSV / single-sheet XLSX fallback
        try:
            df = self._read_file(file_bytes, filename)
        except Exception as exc:  # noqa: BLE001
            return self._make_failed_result(batch_id, method, f"Failed to read: {exc}")
        rows, errors = self.parse_dataframe(batch_id, df)
        return self._build_result(batch_id, rows, errors, method)

    # ── multi-sheet routing ───────────────────────────────────────────────────

    @classmethod
    def _is_multi_sheet_taxpnl(cls, sheet_names: list[str]) -> bool:
        """True when the workbook contains at least one known Zerodha Tax P&L sheet."""
        triggers = {"tradewise exits", "equity dividends", "other debits and credits"}
        lower = {s.lower() for s in sheet_names}
        return any(any(t in name for t in triggers) for name in lower)

    def _extract_multi_sheet(
        self,
        batch_id: str,
        xl: "pd.ExcelFile",
        method: ExtractionMethod,
    ) -> ExtractionResult:
        all_rows: list[RawParsedRow] = []
        all_errors: list[str] = []

        for sheet_name in xl.sheet_names:
            sheet_lower = sheet_name.lower()

            # Skip aggregate-summary sheets
            if any(skip in sheet_lower for skip in self._SKIP_SUBSTRINGS):
                continue

            # Determine sheet type
            sheet_type: str | None = None
            for pattern, stype in self._SHEET_TYPE_MAP:
                if pattern in sheet_lower:
                    sheet_type = stype
                    break
            if sheet_type is None:
                continue  # unknown sheet — skip silently

            try:
                df_raw = xl.parse(sheet_name, header=None, dtype=str)
            except Exception as exc:  # noqa: BLE001
                all_errors.append(f"[{sheet_name}] failed to read: {exc}")
                continue

            try:
                rows, errors = self._parse_sheet(batch_id, df_raw, sheet_type, sheet_name)
                all_rows.extend(rows)
                all_errors.extend(f"[{sheet_name}] {e}" for e in errors)
            except Exception as exc:  # noqa: BLE001
                all_errors.append(f"[{sheet_name}] parser error: {exc}")

        return self._build_result(batch_id, all_rows, all_errors, method)

    @classmethod
    def _parse_sheet(
        cls,
        batch_id: str,
        df_raw: "pd.DataFrame",
        sheet_type: str,
        sheet_name: str,
    ) -> tuple[list[RawParsedRow], list[str]]:
        if sheet_type == "tradewise":
            return cls._parse_tradewise(batch_id, df_raw, sheet_name)
        if sheet_type == "dividend":
            return cls._parse_dividends(batch_id, df_raw, sheet_name)
        if sheet_type == "charges":
            return cls._parse_charges(batch_id, df_raw, sheet_name)
        if sheet_type == "open_position":
            return cls._parse_open_positions(batch_id, df_raw, sheet_name)
        return [], []

    # ── sheet-level parsers ───────────────────────────────────────────────────

    @classmethod
    def _parse_tradewise(
        cls, batch_id: str, df_raw: "pd.DataFrame", sheet_name: str
    ) -> tuple[list[RawParsedRow], list[str]]:
        header_ri = cls._find_header_row(df_raw, {"symbol", "isin", "entry date", "exit date"})
        if header_ri is None:
            return [], [f"Could not find header row in sheet {sheet_name!r}"]

        df = cls._make_df_from_header_row(df_raw, header_ri)
        rows: list[RawParsedRow] = []

        for row_num, (_, row) in enumerate(df.iterrows(), start=1):
            symbol   = str(row.get("Symbol",     "")).strip()
            isin     = str(row.get("ISIN",        "")).strip()
            entry_dt = str(row.get("Entry Date",  "")).strip()
            exit_dt  = str(row.get("Exit Date",   "")).strip()
            qty      = str(row.get("Quantity",    "")).strip()
            buy_val  = str(row.get("Buy Value",   "")).strip()
            sell_val = str(row.get("Sell Value",  "")).strip()
            profit   = str(row.get("Profit",      "")).strip()

            # Skip repeat section-header rows and empty/total rows
            if symbol.lower() in ("symbol", "", "nan"):
                continue
            if exit_dt.lower() in ("exit date", "", "nan"):
                continue

            rows.append(RawParsedRow(
                batch_id=batch_id,
                source_type=SourceType.ZERODHA_TAX_PNL_TRADEWISE,
                parser_version="2.0",
                extraction_method=ExtractionMethod.TABLE_EXTRACTION,
                raw_date=exit_dt,
                raw_narration=f"SELL {symbol} (entry {entry_dt})",
                raw_debit=buy_val  if buy_val  and buy_val.lower()  != "nan" else None,
                raw_credit=sell_val if sell_val and sell_val.lower() != "nan" else None,
                raw_quantity=qty or None,
                fund_isin=isin or None,
                txn_type_hint=TxnTypeHint.REDEMPTION,
                row_confidence=0.9,
                row_number=row_num,
                extra_fields={
                    "sheet_type": "tradewise_exit",
                    "entry_date": entry_dt,
                    "profit": profit,
                    "dedup_key": f"trade:{isin}:{exit_dt}:{sell_val}",
                },
            ))

        return rows, []

    @classmethod
    def _parse_dividends(
        cls, batch_id: str, df_raw: "pd.DataFrame", sheet_name: str
    ) -> tuple[list[RawParsedRow], list[str]]:
        header_ri = cls._find_header_row(
            df_raw, {"symbol", "isin", "ex-date", "net dividend amount"}
        )
        if header_ri is None:
            return [], [f"Could not find header row in sheet {sheet_name!r}"]

        df = cls._make_df_from_header_row(df_raw, header_ri)
        rows: list[RawParsedRow] = []

        for row_num, (_, row) in enumerate(df.iterrows(), start=1):
            symbol  = str(row.get("Symbol",              "")).strip()
            isin    = str(row.get("ISIN",                "")).strip()
            ex_date = str(row.get("Ex-date",             "")).strip()
            qty     = str(row.get("Quantity",            "")).strip()
            dps     = str(row.get("Dividend Per Share",  "")).strip()
            net_amt = str(row.get("Net Dividend Amount", "")).strip()

            # Skip repeat section-header rows, total rows, and empty rows
            if symbol.lower() in ("symbol", "", "nan"):
                continue
            if ex_date.lower() in ("ex-date", "", "nan"):
                continue

            rows.append(RawParsedRow(
                batch_id=batch_id,
                source_type=SourceType.ZERODHA_TAX_PNL_DIVIDENDS,
                parser_version="2.0",
                extraction_method=ExtractionMethod.TABLE_EXTRACTION,
                raw_date=ex_date,
                raw_narration=f"DIVIDEND {symbol}",
                raw_credit=net_amt if net_amt and net_amt.lower() != "nan" else None,
                raw_quantity=qty or None,
                raw_unit_price=dps or None,
                fund_isin=isin or None,
                txn_type_hint=TxnTypeHint.DIVIDEND_PAYOUT,
                row_confidence=0.95,
                row_number=row_num,
                extra_fields={
                    "sheet_type": "dividend",
                    "dedup_key": f"div:{isin}:{ex_date}:{net_amt}",
                },
            ))

        return rows, []

    @classmethod
    def _parse_charges(
        cls, batch_id: str, df_raw: "pd.DataFrame", sheet_name: str
    ) -> tuple[list[RawParsedRow], list[str]]:
        header_ri = cls._find_header_row(df_raw, {"particulars", "posting date"})
        if header_ri is None:
            return [], [f"Could not find header row in sheet {sheet_name!r}"]

        df = cls._make_df_from_header_row(df_raw, header_ri)
        rows: list[RawParsedRow] = []

        for row_num, (_, row) in enumerate(df.iterrows(), start=1):
            particulars = str(row.get("Particulars",  "")).strip()
            posting_dt  = str(row.get("Posting Date", "")).strip()
            debit_raw   = str(row.get("Debit",        "")).strip()
            credit_raw  = str(row.get("Credit",       "")).strip()

            # Skip repeat section-header rows and empty rows
            if particulars.lower() in ("particulars", "", "nan"):
                continue
            if posting_dt.lower() in ("posting date", "", "nan"):
                continue

            debit_val  = debit_raw  if debit_raw  and debit_raw.lower()  not in ("nan", "0", "0.0", "")  else None
            credit_val = credit_raw if credit_raw and credit_raw.lower() not in ("nan", "0", "0.0", "") else None
            amount_key = debit_val or credit_val or ""

            rows.append(RawParsedRow(
                batch_id=batch_id,
                source_type=SourceType.ZERODHA_TAX_PNL_CHARGES,
                parser_version="2.0",
                extraction_method=ExtractionMethod.TABLE_EXTRACTION,
                raw_date=posting_dt,
                raw_narration=particulars,
                raw_debit=debit_val,
                raw_credit=credit_val,
                txn_type_hint=TxnTypeHint.DEBIT if debit_val else TxnTypeHint.CREDIT,
                row_confidence=0.9,
                row_number=row_num,
                extra_fields={
                    "sheet_type": "broker_charge",
                    "dedup_key": f"chg:{posting_dt}:{amount_key}:{particulars[:30]}",
                },
            ))

        return rows, []

    @classmethod
    def _parse_open_positions(
        cls, batch_id: str, df_raw: "pd.DataFrame", sheet_name: str
    ) -> tuple[list[RawParsedRow], list[str]]:
        header_ri = cls._find_header_row(df_raw, {"symbol", "trade date", "open quantity"})
        if header_ri is None:
            return [], [f"Could not find header row in sheet {sheet_name!r}"]

        df = cls._make_df_from_header_row(df_raw, header_ri)
        rows: list[RawParsedRow] = []

        # Tag whether this is opening (FY-start) or closing (current) snapshot
        # Sheet names look like "Open Positions as of 2025-04-01" / "…2026-03-24"
        position_tag = "opening_position" if "2025-04-01" in sheet_name else "closing_position"

        for row_num, (_, row) in enumerate(df.iterrows(), start=1):
            symbol    = str(row.get("Symbol",                  "")).strip()
            trade_dt  = str(row.get("Trade Date",              "")).strip()
            exchange  = str(row.get("Exchange",                "")).strip()
            inst_type = str(row.get("Instrument Type",         "")).strip()
            open_qty  = str(row.get("Open Quantity",           "")).strip()
            avg_price = str(row.get("Average Price",           "")).strip()
            unreal    = str(row.get("Unrealized Profit",       "")).strip()

            # Skip sub-section titles and repeat header rows
            if symbol.lower() in ("symbol", "", "nan"):
                continue
            if symbol.lower().startswith("open positions for"):
                continue

            rows.append(RawParsedRow(
                batch_id=batch_id,
                source_type=SourceType.ZERODHA_OPEN_POSITIONS,
                parser_version="2.0",
                extraction_method=ExtractionMethod.TABLE_EXTRACTION,
                raw_date=trade_dt if trade_dt and trade_dt.lower() != "nan" else "",
                raw_narration=f"OPEN POSITION {symbol} ({inst_type or exchange})",
                raw_quantity=open_qty or None,
                raw_unit_price=avg_price or None,
                txn_type_hint=TxnTypeHint.PURCHASE,
                row_confidence=0.85,
                row_number=row_num,
                extra_fields={
                    "sheet_type": position_tag,
                    "exchange": exchange,
                    "instrument_type": inst_type,
                    "unrealized_pnl": unreal,
                },
            ))

        return rows, []

    # ── shared helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _find_header_row(df_raw: "pd.DataFrame", keywords: set[str]) -> int | None:
        """Return the first DataFrame row index whose cells (lowercased) contain all keywords."""
        for ri, row in df_raw.iterrows():
            cells = {str(c).strip().lower() for c in row if str(c).strip() not in ("", "nan")}
            if keywords.issubset(cells):
                return int(ri)
        return None

    @staticmethod
    def _make_df_from_header_row(df_raw: "pd.DataFrame", header_ri: int) -> "pd.DataFrame":
        """Slice df_raw below header_ri and use that row as column names."""
        header = [str(c).strip() for c in df_raw.iloc[header_ri]]
        data = df_raw.iloc[header_ri + 1:].copy()
        data.columns = header
        return data.reset_index(drop=True)

    # ── legacy single-sheet path (v1 — kept for backward compat / CSV) ────────

    @staticmethod
    def parse_dataframe(batch_id: str, df: "pd.DataFrame") -> tuple[list[RawParsedRow], list[str]]:
        """Parse a flat single-sheet DataFrame with legacy column names (buy_date/sell_date/p&l)."""
        rows: list[RawParsedRow] = []
        errors: list[str] = []
        df.columns = [c.strip() for c in df.columns]

        for row_num, (_, row) in enumerate(df.iterrows(), start=1):
            sell_date = str(row.get("sell_date", row.get("Sell Date", ""))).strip()
            buy_date  = str(row.get("buy_date",  row.get("Buy Date",  ""))).strip()

            if not sell_date or sell_date.lower() == "nan":
                errors.append(f"Row {row_num}: missing sell_date")
                continue

            symbol     = str(row.get("symbol",     row.get("Symbol", ""))).strip()
            isin       = str(row.get("isin",        row.get("ISIN",   ""))).strip()
            quantity   = str(row.get("quantity",    row.get("Quantity", ""))).strip()
            buy_price  = str(row.get("buy_price",   row.get("Buy Price",  ""))).strip()
            sell_price = str(row.get("sell_price",  row.get("Sell Price", ""))).strip()
            pnl        = str(row.get("p&l",         row.get("P&L", row.get("pnl", "")))).strip()

            pnl_decimal = _clean_decimal(pnl)
            if pnl_decimal is not None:
                raw_credit = str(abs(pnl_decimal)) if pnl_decimal >= 0 else None
                raw_debit  = str(abs(pnl_decimal)) if pnl_decimal < 0  else None
            else:
                raw_credit = raw_debit = None

            rows.append(RawParsedRow(
                batch_id=batch_id,
                source_type=SourceType.ZERODHA_TAX_PNL,
                parser_version="1.0",
                extraction_method=ExtractionMethod.TABLE_EXTRACTION,
                raw_date=sell_date,
                raw_narration=f"SELL {symbol} (bought {buy_date})",
                raw_debit=raw_debit,
                raw_credit=raw_credit,
                raw_quantity=quantity or None,
                raw_unit_price=sell_price or None,
                fund_isin=isin or None,
                txn_type_hint=TxnTypeHint.REDEMPTION,
                row_confidence=0.9,
                row_number=row_num,
                extra_fields={"buy_price": buy_price, "pnl": pnl},
            ))

        return rows, errors

    def _build_result(self, batch_id, rows, errors, method) -> ExtractionResult:
        signals = ConfidenceSignals(
            balance_cross_check_passed=None,
            all_rows_have_valid_date=bool(rows) and all(bool(r.raw_date.strip()) for r in rows),
            all_rows_have_amount=bool(rows),
            row_count_positive=len(rows) > 0,
            no_row_parse_errors=len(errors) == 0,
        )
        confidence = compute_confidence(signals)
        dates = [r.raw_date for r in rows if r.raw_date]
        meta = ParseMetadata(
            statement_from=dates[0] if dates else None,
            statement_to=dates[-1] if dates else None,
            total_rows_found=len(rows),
            rows_with_errors=len(errors),
            overall_confidence=confidence,
            warnings=errors,
            extraction_method=method,
            parser_version=self.version,
        )
        return ExtractionResult(rows=rows, metadata=meta, method=method, confidence=confidence)

    @staticmethod
    def _read_file(file_bytes: bytes, filename: str) -> "pd.DataFrame":
        import pandas as pd  # noqa: PLC0415
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext in ("xls", "xlsx"):
            return pd.read_excel(io.BytesIO(file_bytes), dtype=str)
        try:
            return pd.read_csv(io.BytesIO(file_bytes), dtype=str)
        except UnicodeDecodeError:
            return pd.read_csv(io.BytesIO(file_bytes), dtype=str, encoding="latin-1")


# ── Capital Gains parser ──────────────────────────────────────────────────────

class ZerodhaCapitalGainsParser(BaseParser):
    """Parses Zerodha Capital Gains CSV — short/long term gains for tax filing."""

    source_type = SourceType.ZERODHA_CAPITAL_GAINS
    version = "1.0"
    supported_formats = ["CSV", "XLSX"]

    def supported_methods(self) -> list[ExtractionMethod]:
        return [ExtractionMethod.TABLE_EXTRACTION]

    def extract(
        self,
        batch_id: str,
        file_bytes: bytes,
        method: ExtractionMethod,
        filename: str = "file.csv",
    ) -> ExtractionResult:
        try:
            import pandas as pd  # noqa: PLC0415
        except ImportError:
            return self._make_failed_result(batch_id, method, "pandas is required.")

        try:
            df = self._read_file(file_bytes, filename)
        except Exception as exc:  # noqa: BLE001
            return self._make_failed_result(batch_id, method, f"Failed to read: {exc}")

        rows, errors = self.parse_dataframe(batch_id, df)
        return self._build_result(batch_id, rows, errors, method)

    @staticmethod
    def parse_dataframe(batch_id: str, df: "pd.DataFrame") -> tuple[list[RawParsedRow], list[str]]:
        rows: list[RawParsedRow] = []
        errors: list[str] = []
        df.columns = [c.strip() for c in df.columns]

        for row_num, (_, row) in enumerate(df.iterrows(), start=1):
            sell_date = str(row.get("sell_date", row.get("Sell Date", ""))).strip()
            buy_date  = str(row.get("buy_date",  row.get("Buy Date",  ""))).strip()

            if not sell_date or sell_date.lower() == "nan":
                errors.append(f"Row {row_num}: missing sell_date")
                continue

            symbol      = str(row.get("symbol",       row.get("Symbol", ""))).strip()
            isin        = str(row.get("isin",          row.get("ISIN",   ""))).strip()
            quantity    = str(row.get("quantity",      row.get("Quantity", ""))).strip()
            buy_value   = str(row.get("buy_value",     row.get("Buy Value",  ""))).strip()
            sell_value  = str(row.get("sell_value",    row.get("Sell Value", ""))).strip()
            gain        = str(row.get("gain",          row.get("Gain", ""))).strip()
            gain_type   = str(row.get("gain_type",     row.get("Gain Type", "STCG"))).strip()

            gain_decimal = _clean_decimal(gain)
            raw_credit = str(abs(gain_decimal)) if gain_decimal and gain_decimal >= 0 else None
            raw_debit  = str(abs(gain_decimal)) if gain_decimal and gain_decimal < 0  else None

            rows.append(RawParsedRow(
                batch_id=batch_id,
                source_type=SourceType.ZERODHA_CAPITAL_GAINS,
                parser_version="1.0",
                extraction_method=ExtractionMethod.TABLE_EXTRACTION,
                raw_date=sell_date,
                raw_narration=f"{gain_type} {symbol} (bought {buy_date})",
                raw_debit=raw_debit,
                raw_credit=raw_credit,
                raw_quantity=quantity or None,
                raw_unit_price=sell_value or None,
                fund_isin=isin or None,
                txn_type_hint=TxnTypeHint.REDEMPTION,
                row_confidence=0.9,
                row_number=row_num,
                extra_fields={"buy_value": buy_value, "gain_type": gain_type},
            ))

        return rows, errors

    def _build_result(self, batch_id, rows, errors, method) -> ExtractionResult:
        signals = ConfidenceSignals(
            balance_cross_check_passed=None,
            all_rows_have_valid_date=bool(rows) and all(bool(r.raw_date.strip()) for r in rows),
            all_rows_have_amount=bool(rows),
            row_count_positive=len(rows) > 0,
            no_row_parse_errors=len(errors) == 0,
        )
        confidence = compute_confidence(signals)
        dates = [r.raw_date for r in rows if r.raw_date]
        meta = ParseMetadata(
            statement_from=dates[0] if dates else None,
            statement_to=dates[-1] if dates else None,
            total_rows_found=len(rows),
            rows_with_errors=len(errors),
            overall_confidence=confidence,
            warnings=errors,
            extraction_method=method,
            parser_version=self.version,
        )
        return ExtractionResult(rows=rows, metadata=meta, method=method, confidence=confidence)

    @staticmethod
    def _read_file(file_bytes: bytes, filename: str) -> "pd.DataFrame":
        import pandas as pd  # noqa: PLC0415
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext in ("xls", "xlsx"):
            return pd.read_excel(io.BytesIO(file_bytes), dtype=str)
        try:
            return pd.read_csv(io.BytesIO(file_bytes), dtype=str)
        except UnicodeDecodeError:
            return pd.read_csv(io.BytesIO(file_bytes), dtype=str, encoding="latin-1")
