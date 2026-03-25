"""Test journal entry correctness for all account-type combinations.

Verifies that for every fixture in tests/fixtures/csv/journal_combos/ the
full pipeline (parse → normalize → categorize → propose) produces balanced
journal entries where the correct account type appears on the correct side.

Account-type combination matrix covered:
  Source = ASSET (bank account 1102)
    bank_income.csv            → Asset←Income      (DR bank, CR income)
    bank_expense.csv           → Asset→Expense     (CR bank, DR expense)
    bank_to_asset.csv          → Asset→Asset       (CR bank, DR investment/cash)
    bank_to_liability.csv      → Asset→Liability   (CR bank, DR CC/loan)
    bank_transfer_out.csv      → Asset→Asset       (CR bank, DR transfer clearing)
    bank_to_equity.csv         → Asset←Equity      (DR bank, CR opening equity)
    bank_all_income_types.csv  → one row per income category (salary/interest/
                                   dividend/refund/cashback/capital-gains)
    bank_all_expense_types.csv → one row per expense category (food/transport/
                                   shopping/healthcare/utilities/housing/emi/
                                   insurance/education/entertainment)

  Source = LIABILITY (credit card 2100, via --account-type CREDIT_CARD)
    cc_to_expense.csv          → Liability→Expense (CR CC, DR expense)
    cc_to_income.csv           → Liability←Income  (DR CC, CR income/cashback)
    cc_bill_payment.csv        → Liability←Transfer(DR CC, CR transfer clearing)
    cc_all_expense_types.csv   → one row per CC expense type (food/transport/
                                   shopping/healthcare/utilities/entertainment/
                                   education/insurance)

  all_combinations_bank.csv — comprehensive bank fixture with all 6 bank combos
"""

from __future__ import annotations

import pathlib
import uuid
from decimal import Decimal

import pytest

pytest.importorskip("pandas")

from core.models.enums import SourceType                                        # noqa: E402
from core.models.source_map import get_source_account                           # noqa: E402
from modules.parser.chain import ExtractionChain                                # noqa: E402
from modules.parser.parsers.generic_csv import GenericCsvParser                 # noqa: E402
from services.normalize_service import NormalizeService                         # noqa: E402
from services.categorize_service import CategorizeService                       # noqa: E402
from services.proposal_service import ProposalService, ProposedJournalEntry    # noqa: E402
from services.smart_service import SmartProcessor, SmartProcessingOptions      # noqa: E402

_CSV_COMBOS = pathlib.Path(__file__).parent / "fixtures" / "csv" / "journal_combos"

# ── Income account codes (4xxx) ─────────────────────────────────────────────
_INCOME_CODES = {str(c) for c in range(4000, 5000)}
# ── Expense account codes (5xxx) ─────────────────────────────────────────────
_EXPENSE_CODES = {str(c) for c in range(5000, 6000)}
# ── Asset account codes (1xxx) ───────────────────────────────────────────────
_ASSET_CODES = {str(c) for c in range(1000, 2000)}
# ── Liability / transfer codes (2xxx) ────────────────────────────────────────
_LIABILITY_CODES = {str(c) for c in range(2000, 3000)}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read(filename: str) -> bytes:
    return (_CSV_COMBOS / filename).read_bytes()


def _run_smart(
    filename: str,
    account_type_override: str | None = None,
    source_type: SourceType = SourceType.HDFC_BANK_CSV,
) -> SmartProcessingOptions:
    """Parse fixture → full SmartProcessor pipeline → return result."""
    batch_id = str(uuid.uuid4())
    raw = ExtractionChain(GenericCsvParser(), batch_id, _read(filename)).run()
    assert raw.rows, f"No rows parsed from {filename}"

    src_info = get_source_account(source_type, account_type_override)
    opts = SmartProcessingOptions(
        use_llm=False,
        bank_account_id=src_info.account_code,
        source_account_code=src_info.account_code,
        source_account_name=src_info.account_name,
        source_account_class=src_info.account_class,
        account_id="TEST-ACC",
    )
    return SmartProcessor().process_batch(
        user_id="test-user", batch_id=batch_id, raw_rows=raw.rows, options=opts
    )


def _proposals(filename: str, **kwargs) -> list[ProposedJournalEntry]:
    result = _run_smart(filename, **kwargs)
    assert result.proposals is not None
    return result.proposals.proposals


def _assert_balanced(proposals: list[ProposedJournalEntry]) -> None:
    for p in proposals:
        dr = sum(l.debit  for l in p.lines)
        cr = sum(l.credit for l in p.lines)
        assert dr == cr, (
            f"Unbalanced entry for '{p.narration}': DR={dr} CR={cr}\n"
            f"Lines: {p.lines}"
        )


def _source_lines(proposals: list[ProposedJournalEntry], source_code: str):
    """All journal lines where account_code == source_code."""
    return [l for p in proposals for l in p.lines if l.account_code == source_code]


def _counterpart_lines(proposals: list[ProposedJournalEntry], source_code: str):
    """All journal lines where account_code != source_code."""
    return [l for p in proposals for l in p.lines if l.account_code != source_code]


def _counterpart_code_for(
    proposals: list[ProposedJournalEntry],
    narr_key: str,
    source_code: str,
) -> str | None:
    """Return the counterpart account_code for the first proposal whose
    narration contains *narr_key* (case-insensitive).
    """
    for p in proposals:
        if narr_key.lower() in p.narration.lower():
            cparts = [l for l in p.lines if l.account_code != source_code]
            return cparts[0].account_code if cparts else None
    return None


# ---------------------------------------------------------------------------
# Tests: source_map module
# ---------------------------------------------------------------------------

class TestSourceMap:
    """Unit tests for get_source_account()."""

    @pytest.mark.parametrize("st,expected_code", [
        (SourceType.HDFC_BANK,      "1102"),
        (SourceType.HDFC_BANK_CSV,  "1102"),
        (SourceType.SBI_BANK,       "1102"),
        (SourceType.ICICI_BANK_CSV, "1102"),
        (SourceType.CAS_CAMS,       "1200"),
        (SourceType.CAS_KFINTECH,   "1200"),
        (SourceType.ZERODHA_TRADEBOOK,    "1220"),
        (SourceType.ZERODHA_HOLDINGS,     "1220"),
        (SourceType.ZERODHA_CAPITAL_GAINS,"1220"),
        (SourceType.UNKNOWN,        "1102"),
        (SourceType.GENERIC_CSV,    "1102"),
    ])
    def test_source_type_to_code(self, st: SourceType, expected_code: str):
        info = get_source_account(st)
        assert info.account_code == expected_code

    @pytest.mark.parametrize("st", [
        SourceType.HDFC_BANK, SourceType.SBI_BANK_CSV, SourceType.ICICI_BANK,
        SourceType.CAS_CAMS, SourceType.ZERODHA_TRADEBOOK, SourceType.UNKNOWN,
    ])
    def test_all_sources_are_asset(self, st: SourceType):
        info = get_source_account(st)
        assert info.account_class == "ASSET"
        assert info.is_debit_normal is True

    def test_credit_card_override(self):
        info = get_source_account(SourceType.HDFC_BANK_CSV, account_type_override="CREDIT_CARD")
        assert info.account_code == "2100"
        assert info.account_class == "LIABILITY"
        assert info.is_debit_normal is False

    def test_cc_alias(self):
        info = get_source_account(account_type_override="CC")
        assert info.account_code == "2100"

    def test_bank_override(self):
        info = get_source_account(account_type_override="BANK")
        assert info.account_code == "1102"
        assert info.account_class == "ASSET"

    def test_unknown_override_falls_through_to_source_type(self):
        """Unknown override key → fall through to source_type lookup."""
        info = get_source_account(SourceType.CAS_CAMS, account_type_override="NONEXISTENT")
        assert info.account_code == "1200"

    def test_string_source_type(self):
        """String values should work the same as enum values."""
        info = get_source_account("HDFC_BANK_CSV")
        assert info.account_code == "1102"

    def test_invalid_string_returns_default(self):
        info = get_source_account("NOT_A_REAL_SOURCE_TYPE")
        assert info.account_code == "1102"   # default

    def test_none_returns_default(self):
        info = get_source_account(None)
        assert info.account_code == "1102"


# ---------------------------------------------------------------------------
# Tests: Fixture files existence
# ---------------------------------------------------------------------------

class TestFixtureFilesExist:
    @pytest.mark.parametrize("name", [
        "bank_income.csv",
        "bank_expense.csv",
        "bank_to_asset.csv",
        "bank_to_liability.csv",
        "bank_to_equity.csv",
        "bank_transfer_out.csv",
        "cc_to_expense.csv",
        "cc_to_income.csv",
        "cc_bill_payment.csv",
        "all_combinations_bank.csv",
    ])
    def test_fixture_exists(self, name: str):
        p = _CSV_COMBOS / name
        assert p.is_file(), f"Missing fixture: {p}"
        assert p.stat().st_size > 0


# ---------------------------------------------------------------------------
# Tests: Bank account (ASSET source = 1102) combinations
# ---------------------------------------------------------------------------

class TestBankSourceJournals:
    """All journals produced when source = Savings Account (Asset 1102)."""

    SOURCE = "1102"

    def test_bank_income_all_balanced(self):
        props = _proposals("bank_income.csv")
        assert props
        _assert_balanced(props)

    def test_bank_income_source_is_debited(self):
        """Income credited to bank → bank (Asset) is DR (increases)."""
        props = _proposals("bank_income.csv")
        src_lines = _source_lines(props, self.SOURCE)
        # Every income row: bank is DR
        assert all(l.debit > 0 and l.credit == 0 for l in src_lines), (
            "Bank account should be DEBITED on income rows (asset increases)"
        )

    def test_bank_income_counterpart_is_income_account(self):
        """Counterpart of salary/interest/refund rows must be an income account."""
        props = _proposals("bank_income.csv")
        cpart = _counterpart_lines(props, self.SOURCE)
        codes = {l.account_code for l in cpart}
        assert codes <= _INCOME_CODES | _LIABILITY_CODES, (
            f"Expected income account codes, got: {codes}"
        )

    def test_bank_expense_all_balanced(self):
        props = _proposals("bank_expense.csv")
        assert props
        _assert_balanced(props)

    def test_bank_expense_source_is_credited(self):
        """Expense deducted from bank → bank (Asset) is CR (decreases)."""
        props = _proposals("bank_expense.csv")
        src_lines = _source_lines(props, self.SOURCE)
        assert all(l.credit > 0 and l.debit == 0 for l in src_lines), (
            "Bank account should be CREDITED on expense rows (asset decreases)"
        )

    def test_bank_expense_counterpart_is_expense_account(self):
        """Counterpart of food/rent/utility rows must be in expense range.

        Some rows (e.g. mobile recharges) may be classified as TRANSFER → 2999,
        so liability/clearing codes are also acceptable counterparts.
        """
        props = _proposals("bank_expense.csv")
        cpart = _counterpart_lines(props, self.SOURCE)
        codes = {l.account_code for l in cpart}
        # Allow asset codes (cash withdrawals → 1101) and liability/clearing (transfers → 2999)
        assert codes <= _EXPENSE_CODES | _ASSET_CODES | _LIABILITY_CODES, (
            f"Unexpected counterpart codes for bank expense fixture: {codes}"
        )

    def test_bank_to_asset_all_balanced(self):
        """Investment / ATM / FD rows must be balanced."""
        props = _proposals("bank_to_asset.csv")
        assert props
        _assert_balanced(props)

    def test_bank_to_asset_produces_asset_counterpart(self):
        """SIP / FD / ATM → counterpart must be another Asset or clearing account."""
        props = _proposals("bank_to_asset.csv")
        cpart = _counterpart_lines(props, self.SOURCE)
        codes = {l.account_code for l in cpart}
        assert codes <= _ASSET_CODES | _LIABILITY_CODES | _EXPENSE_CODES, (
            f"Unexpected counterpart codes: {codes}"
        )

    def test_bank_to_liability_all_balanced(self):
        """CC bill payment / loan EMI rows must be balanced."""
        props = _proposals("bank_to_liability.csv")
        assert props
        _assert_balanced(props)

    def test_bank_to_equity_produces_bank_debit(self):
        """Opening balance row → bank is DR (asset increases, equity is CR)."""
        props = _proposals("bank_to_equity.csv")
        assert props
        _assert_balanced(props)
        src_lines = _source_lines(props, self.SOURCE)
        assert any(l.debit > 0 for l in src_lines)

    def test_bank_transfer_all_balanced(self):
        props = _proposals("bank_transfer_out.csv")
        assert props
        _assert_balanced(props)

    def test_bank_transfer_uses_clearing_account(self):
        """Transfer rows must route through Transfer Clearing (2999)."""
        props = _proposals("bank_transfer_out.csv")
        cpart = _counterpart_lines(props, self.SOURCE)
        codes = {l.account_code for l in cpart}
        assert "2999" in codes, (
            f"Expected Transfer Clearing 2999 for transfer rows. Got: {codes}"
        )

    def test_all_combinations_bank_balanced(self):
        """Comprehensive fixture — every row must be balanced."""
        props = _proposals("all_combinations_bank.csv")
        assert props
        _assert_balanced(props)

    def test_all_combinations_bank_has_income_and_expense(self):
        """Mixed fixture must yield both income and expense counterpart accounts."""
        props = _proposals("all_combinations_bank.csv")
        cpart = _counterpart_lines(props, self.SOURCE)
        codes = {l.account_code for l in cpart}
        income_present  = bool(codes & _INCOME_CODES)
        expense_present = bool(codes & _EXPENSE_CODES)
        assert income_present,  "Expected at least one income account in mixed fixture"
        assert expense_present, "Expected at least one expense account in mixed fixture"


# ---------------------------------------------------------------------------
# Tests: Credit Card account (LIABILITY source = 2100) combinations
# ---------------------------------------------------------------------------

class TestCreditCardSourceJournals:
    """All journals produced when source = Credit Card (Liability 2100)."""

    SOURCE = "2100"
    OVERRIDE = "CREDIT_CARD"

    def test_cc_expense_all_balanced(self):
        props = _proposals("cc_to_expense.csv", account_type_override=self.OVERRIDE)
        assert props
        _assert_balanced(props)

    def test_cc_expense_source_is_credited(self):
        """CC purchase → CC Payable (Liability) is CR (liability increases)."""
        props = _proposals("cc_to_expense.csv", account_type_override=self.OVERRIDE)
        src_lines = _source_lines(props, self.SOURCE)
        assert src_lines, "Expected CC source (2100) lines in cc_to_expense"
        assert all(l.credit > 0 and l.debit == 0 for l in src_lines), (
            "CC Payable should be CREDITED on CC purchase (liability increases)"
        )

    def test_cc_expense_counterpart_is_expense(self):
        """Counterpart of CC purchases must be expense accounts."""
        props = _proposals("cc_to_expense.csv", account_type_override=self.OVERRIDE)
        cpart = _counterpart_lines(props, self.SOURCE)
        codes = {l.account_code for l in cpart}
        assert codes <= _EXPENSE_CODES | _LIABILITY_CODES, (
            f"Expected expense codes for CC purchases, got: {codes}"
        )

    def test_cc_income_all_balanced(self):
        """CC refund / cashback rows must be balanced."""
        props = _proposals("cc_to_income.csv", account_type_override=self.OVERRIDE)
        assert props
        _assert_balanced(props)

    def test_cc_income_source_is_debited(self):
        """CC refund/cashback → CC Payable (Liability) is DR (liability decreases)."""
        props = _proposals("cc_to_income.csv", account_type_override=self.OVERRIDE)
        src_lines = _source_lines(props, self.SOURCE)
        assert src_lines, "Expected CC source (2100) lines in cc_to_income"
        assert all(l.debit > 0 and l.credit == 0 for l in src_lines), (
            "CC Payable should be DEBITED on refund/cashback (liability decreases)"
        )

    def test_cc_income_counterpart_is_income(self):
        """Counterpart of CC cashback/refund must be income accounts."""
        props = _proposals("cc_to_income.csv", account_type_override=self.OVERRIDE)
        cpart = _counterpart_lines(props, self.SOURCE)
        codes = {l.account_code for l in cpart}
        assert codes <= _INCOME_CODES | _LIABILITY_CODES, (
            f"Expected income codes for CC refunds/cashback, got: {codes}"
        )

    def test_cc_payment_all_balanced(self):
        """CC bill payment rows must be balanced."""
        props = _proposals("cc_bill_payment.csv", account_type_override=self.OVERRIDE)
        assert props
        _assert_balanced(props)

    def test_cc_payment_source_is_debited(self):
        """CC bill payment → CC Payable (Liability) is DR (liability decreases)."""
        props = _proposals("cc_bill_payment.csv", account_type_override=self.OVERRIDE)
        src_lines = _source_lines(props, self.SOURCE)
        assert src_lines, "Expected CC source (2100) lines in cc_bill_payment"
        assert all(l.debit > 0 and l.credit == 0 for l in src_lines), (
            "CC Payable should be DEBITED when bill is paid (liability decreases)"
        )


# ---------------------------------------------------------------------------
# Tests: Bank income — exact counterpart CoA code per income sub-type
# ---------------------------------------------------------------------------

class TestBankIncomeByCategoryCode:
    """Each income sub-type must post to the correct CoA account.

    Table (from core.models.coa_categories.CATEGORY_TO_ACCOUNT):
      INCOME_SALARY        -> 4100
      INCOME_INTEREST      -> 4200
      INCOME_DIVIDEND      -> 4300
      INCOME_CAPITAL_GAINS -> 4400
      INCOME_REFUND        -> 4900
      INCOME_CASHBACK      -> 4900
    """

    _FILE = "bank_all_income_types.csv"
    _SRC  = "1102"

    def test_all_rows_balanced(self):
        props = _proposals(self._FILE)
        assert len(props) == 13, f"Expected 13 proposals, got {len(props)}"
        _assert_balanced(props)

    def test_bank_is_dr_for_every_income_row(self):
        """Income arriving in bank -> Asset INCREASES -> bank is DR."""
        props = _proposals(self._FILE)
        src = _source_lines(props, self._SRC)
        assert src, "No source (1102) lines found"
        assert all(l.debit > 0 and l.credit == 0 for l in src), (
            "Bank (Asset) must be DEBITED for every income row"
        )

    @pytest.mark.parametrize("narr_key,expected_code", [
        # INCOME_SALARY → 4100
        ("salary",        "4100"),
        ("payroll",       "4100"),
        # INCOME_INTEREST → 4200
        ("savings int",   "4200"),
        ("quarterly int", "4200"),
        # INCOME_DIVIDEND → 4300
        ("dividend pay",  "4300"),
        ("div pay",       "4300"),
        # INCOME_CAPITAL_GAINS → 4400
        ("stcg",          "4400"),
        ("capital gain",  "4400"),
        # INCOME_REFUND → 4900
        ("refund",        "4900"),
        ("reversal",      "4900"),
        # INCOME_CASHBACK → 4900
        ("cashback reward", "4900"),
        ("cash back amazon", "4900"),
    ])
    def test_counterpart_code(self, narr_key: str, expected_code: str):
        """Counterpart account must match the expected CoA code."""
        props = _proposals(self._FILE)
        code  = _counterpart_code_for(props, narr_key, self._SRC)
        assert code is not None, (
            f"No proposal narration containing '{narr_key}'"
        )
        assert code == expected_code, (
            f"'{narr_key}' row: expected counterpart {expected_code}, got {code}"
        )


# ---------------------------------------------------------------------------
# Tests: Bank expense — exact counterpart CoA code per expense sub-type
# ---------------------------------------------------------------------------

class TestBankExpenseByCategoryCode:
    """Each expense sub-type must post to the correct CoA account.

    Table (from core.models.coa_categories.CATEGORY_TO_ACCOUNT):
      EXPENSE_FOOD          -> 5100
      EXPENSE_TRANSPORT     -> 5200
      EXPENSE_SHOPPING      -> 5700
      EXPENSE_HEALTHCARE    -> 5500
      EXPENSE_UTILITIES     -> 5400
      EXPENSE_HOUSING       -> 5300
      EXPENSE_EMI           -> 5300  (same bucket as housing for now)
      EXPENSE_INSURANCE     -> 5900
      EXPENSE_EDUCATION     -> 5600
      EXPENSE_ENTERTAINMENT -> 5800
    """

    _FILE = "bank_all_expense_types.csv"
    _SRC  = "1102"

    def test_all_rows_balanced(self):
        props = _proposals(self._FILE)
        assert len(props) == 23, f"Expected 23 proposals, got {len(props)}"
        _assert_balanced(props)

    def test_bank_is_cr_for_every_expense_row(self):
        """Money leaves bank for expense -> Asset DECREASES -> bank is CR."""
        props = _proposals(self._FILE)
        src = _source_lines(props, self._SRC)
        assert src, "No source (1102) lines found"
        assert all(l.credit > 0 and l.debit == 0 for l in src), (
            "Bank (Asset) must be CREDITED for every expense row"
        )

    @pytest.mark.parametrize("narr_key,expected_code", [
        # EXPENSE_FOOD → 5100
        ("zomato",        "5100"),
        ("swiggy",        "5100"),
        # EXPENSE_TRANSPORT → 5200
        ("uber taxi",     "5200"),
        ("ola ride",      "5200"),
        ("indigo airline","5200"),
        # EXPENSE_SHOPPING → 5700
        ("amazon india",  "5700"),
        ("flipkart sale", "5700"),
        ("myntra fashion","5700"),
        # EXPENSE_HEALTHCARE → 5500
        ("apollo pharmacy","5500"),
        ("medplus",       "5500"),
        # EXPENSE_UTILITIES → 5400
        ("bescom",        "5400"),
        ("jio broadband", "5400"),
        ("airtel postpaid","5400"),
        # EXPENSE_HOUSING → 5300
        ("house rent",    "5300"),
        # EXPENSE_EMI → 5300
        ("home loan emi", "5300"),
        ("car loan emi",  "5300"),
        # EXPENSE_INSURANCE → 5900
        ("lic insurance", "5900"),
        # EXPENSE_EDUCATION → 5600
        ("coursera",      "5600"),
        ("udemy",         "5600"),
        # EXPENSE_ENTERTAINMENT → 5800
        ("netflix",       "5800"),
        ("spotify music", "5800"),
        ("prime video",   "5800"),
    ])
    def test_counterpart_code(self, narr_key: str, expected_code: str):
        """Counterpart account must match the expected CoA code."""
        props = _proposals(self._FILE)
        code  = _counterpart_code_for(props, narr_key, self._SRC)
        assert code is not None, (
            f"No proposal narration containing '{narr_key}'"
        )
        assert code == expected_code, (
            f"'{narr_key}' row: expected counterpart {expected_code}, got {code}"
        )

    def test_counterpart_is_dr_for_every_expense_row(self):
        """Expense account on counterpart must be DR (Expense INCREASES = DR)."""
        props = _proposals(self._FILE)
        cpart = _counterpart_lines(props, self._SRC)
        assert all(l.debit > 0 and l.credit == 0 for l in cpart), (
            "Counterpart (Expense) must be DEBITED on every expense row"
        )


# ---------------------------------------------------------------------------
# Tests: Credit Card expense — exact counterpart CoA code per CC expense type
# ---------------------------------------------------------------------------

class TestCCExpenseByCategoryCode:
    """CC purchases must use the same CoA codes as bank expenses and post correctly:
      CC Payable (Liability) is CR (liability increases) on every purchase.
      Counterpart Expense account is DR (expense increases).
    """

    _FILE     = "cc_all_expense_types.csv"
    _SRC      = "2100"
    _OVERRIDE = "CREDIT_CARD"

    def test_all_rows_balanced(self):
        props = _proposals(self._FILE, account_type_override=self._OVERRIDE)
        assert len(props) == 21, f"Expected 21 proposals, got {len(props)}"
        _assert_balanced(props)

    def test_cc_is_cr_for_every_purchase(self):
        """CC purchase -> Liability INCREASES -> CC Payable is CR."""
        props = _proposals(self._FILE, account_type_override=self._OVERRIDE)
        src = _source_lines(props, self._SRC)
        assert src, "No source (2100) lines found"
        assert all(l.credit > 0 and l.debit == 0 for l in src), (
            "CC Payable (Liability) must be CREDITED on every purchase row"
        )

    def test_counterpart_is_dr_for_every_purchase(self):
        """Expense counterpart must be DR (Expense INCREASES = DR)."""
        props = _proposals(self._FILE, account_type_override=self._OVERRIDE)
        cpart = _counterpart_lines(props, self._SRC)
        assert all(l.debit > 0 and l.credit == 0 for l in cpart), (
            "Counterpart (Expense) must be DEBITED on every CC purchase row"
        )

    @pytest.mark.parametrize("narr_key,expected_code", [
        # EXPENSE_FOOD → 5100
        ("swiggy food",      "5100"),
        ("zomato restaurant","5100"),
        ("cafe coffee",      "5100"),
        # EXPENSE_TRANSPORT → 5200
        ("irctc train",      "5200"),
        ("indigo flight",    "5200"),
        ("ola ride",         "5200"),
        # EXPENSE_SHOPPING → 5700
        ("amazon india",     "5700"),
        ("flipkart shopping","5700"),
        ("myntra fashion",   "5700"),
        # EXPENSE_HEALTHCARE → 5500
        ("apollo pharmacy", "5500"),
        ("hospital consultation", "5500"),
        # EXPENSE_UTILITIES → 5400
        ("jio broadband",   "5400"),
        ("airtel mobile",   "5400"),
        ("bescom electricity","5400"),
        # EXPENSE_ENTERTAINMENT → 5800
        ("netflix",          "5800"),
        ("spotify music",    "5800"),
        # EXPENSE_EDUCATION → 5600
        ("coursera",         "5600"),
        ("udemy course",     "5600"),
        # EXPENSE_INSURANCE → 5900
        ("lic insurance",    "5900"),
        ("term plan insurance", "5900"),
    ])
    def test_counterpart_code(self, narr_key: str, expected_code: str):
        """Counterpart account must match the expected CoA code."""
        props = _proposals(self._FILE, account_type_override=self._OVERRIDE)
        code  = _counterpart_code_for(props, narr_key, self._SRC)
        assert code is not None, (
            f"No proposal narration containing '{narr_key}'"
        )
        assert code == expected_code, (
            f"'{narr_key}' CC row: expected counterpart {expected_code}, got {code}"
        )


# ---------------------------------------------------------------------------
# Tests: Proposal balance invariant (parametrized over all fixtures)
# ---------------------------------------------------------------------------

_ALL_BANK_FIXTURES = [
    "bank_income.csv",
    "bank_expense.csv",
    "bank_to_asset.csv",
    "bank_to_liability.csv",
    "bank_to_equity.csv",
    "bank_transfer_out.csv",
    "bank_all_income_types.csv",
    "bank_all_expense_types.csv",
    "all_combinations_bank.csv",
]

_ALL_CC_FIXTURES = [
    "cc_to_expense.csv",
    "cc_to_income.csv",
    "cc_bill_payment.csv",
    "cc_all_expense_types.csv",
]


@pytest.mark.parametrize("filename", _ALL_BANK_FIXTURES)
def test_bank_fixture_all_entries_balanced(filename: str):
    """All journal entries produced from bank fixtures must be balanced."""
    props = _proposals(filename)
    assert props, f"No proposals generated for {filename}"
    _assert_balanced(props)


@pytest.mark.parametrize("filename", _ALL_CC_FIXTURES)
def test_cc_fixture_all_entries_balanced(filename: str):
    """All journal entries produced from CC fixtures must be balanced."""
    props = _proposals(filename, account_type_override="CREDIT_CARD")
    assert props, f"No proposals generated for {filename}"
    _assert_balanced(props)


@pytest.mark.parametrize("filename", _ALL_BANK_FIXTURES + _ALL_CC_FIXTURES)
def test_no_zero_amount_proposals(filename: str):
    """Every journal line must have a non-zero amount on exactly one side."""
    override = "CREDIT_CARD" if "cc_" in filename else None
    props_list = _proposals(filename, account_type_override=override)
    for proposal in props_list:
        for line in proposal.lines:
            assert (line.debit > 0) != (line.credit > 0), (
                f"Line for '{proposal.narration}' must have exactly one of debit/credit > 0: {line}"
            )
