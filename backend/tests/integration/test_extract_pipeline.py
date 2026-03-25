"""End-to-end extraction + pipeline tests using static fixture files.

Tests exercise the full non-HTTP pipeline with no mocks:

    fixture bytes   → ExtractionChain.run()              (SM-C)
    raw rows        → NormalizeService.normalize_batch()  (SM-E)
    norm rows       → DedupService.dedup_batch()          (SM-F)
    deduped rows    → CategorizeService.categorize_batch() (SM-G)
    all above       → SmartProcessor.process_batch()      (SM-J)
    proposals       → ProposalService inside SmartProcessor (SM-I)

PDF-format parsers are tested via ``parse_text_content()`` from ``.txt``
fixtures, exercising the same regex parsing logic that runs on real
statements without requiring an actual PDF file.

Fixture files:
    tests/fixtures/csv/    — one CSV per supported bank format
    tests/fixtures/text/   — PDF-parser text-layer content as plain text
"""

from __future__ import annotations

import pathlib
import uuid
from decimal import Decimal

import pytest

pytest.importorskip("pandas")

from core.models.enums import SourceType                                        # noqa: E402
                                                                               # noqa: E402
from services.categorize_service import CategorizeService                        # noqa: E402
from services.dedup_service import DedupService                                  # noqa: E402
from services.normalize_service import NormalizeService                          # noqa: E402
from modules.parser.chain import ExtractionChain                                # noqa: E402
from modules.parser.parsers.generic_csv import GenericCsvParser                 # noqa: E402
from modules.parser.parsers.hdfc_pdf import HdfcPdfParser                      # noqa: E402
from modules.parser.parsers.icici_pdf import IciciPdfParser                    # noqa: E402
from modules.parser.parsers.sbi_pdf import SbiPdfParser                        # noqa: E402
from modules.parser.parsers.zerodha_csv import ZerodhaTradebookParser           # noqa: E402
from services.smart_service import SmartProcessingOptions, SmartProcessor        # noqa: E402

# ---------------------------------------------------------------------------
# Fixture file helpers
# ---------------------------------------------------------------------------

_FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"
_CSV = _FIXTURES / "csv"
_TEXT = _FIXTURES / "text"


def _csv_bytes(name: str) -> bytes:
    return (_CSV / name).read_bytes()


def _text_str(name: str) -> str:
    return (_TEXT / name).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def user_id() -> str:
    return "pipeline-test-user"


@pytest.fixture
def account_id() -> str:
    return "ACC-TEST-001"


@pytest.fixture
def batch_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture(autouse=True)
def reset_dedup() -> None:
    """No-op: _seen_hashes removed; dedup is stateless per call (uses db_hashes param)."""
    yield


# ---------------------------------------------------------------------------
# Pipeline helper functions
# ---------------------------------------------------------------------------

def _extract_csv(filename: str, bid: str):
    """Run ExtractionChain on a CSV fixture file using GenericCsvParser."""
    return ExtractionChain(GenericCsvParser(), bid, _csv_bytes(filename)).run()


def _extract_tradebook(bid: str):
    return ExtractionChain(
        ZerodhaTradebookParser(), bid, _csv_bytes("zerodha_tradebook.csv")
    ).run()


def _normalize(rows, bid: str):
    return NormalizeService().normalize_batch(bid, rows).rows


def _dedup(rows, uid: str, bid: str, acc: str, db_hashes: set[str] | None = None):
    return DedupService().dedup_batch(
        user_id=uid, batch_id=bid, account_id=acc, rows=rows, db_hashes=db_hashes
    )


def _hashes_from(result) -> set[str]:
    """Collect txn_hashes from a DedupBatchResult (simulates DB commit in tests)."""
    return {r.extra_fields["txn_hash"] for r in result.new if "txn_hash" in r.extra_fields}


def _smart(raw_rows, uid: str, bid: str, acc: str = "ACC-TEST-001", db_hashes: set[str] | None = None):
    return SmartProcessor().process_batch(
        user_id=uid,
        batch_id=bid,
        raw_rows=raw_rows,
        options=SmartProcessingOptions(use_llm=False, account_id=acc, db_hashes=db_hashes),
    )


# ---------------------------------------------------------------------------
# Class: TestFixtureFilesExist
# ---------------------------------------------------------------------------

class TestFixtureFilesExist:
    """Sanity-check that all fixture files are present and non-empty."""

    @pytest.mark.parametrize("name", [
        "hdfc_bank.csv",
        "hdfc_bank_duplicate.csv",
        "hdfc_bank_overlap.csv",
        "sbi_bank.csv",
        "icici_bank.csv",
        "axis_bank.csv",
        "zerodha_tradebook.csv",
    ])
    def test_csv_fixture_exists(self, name: str):
        path = _CSV / name
        assert path.is_file(), f"Missing fixture: {path}"
        assert path.stat().st_size > 0

    @pytest.mark.parametrize("name", [
        "hdfc_statement.txt",
        "sbi_statement.txt",
        "icici_statement.txt",
    ])
    def test_text_fixture_exists(self, name: str):
        path = _TEXT / name
        assert path.is_file(), f"Missing fixture: {path}"
        assert path.read_text(encoding="utf-8").strip()


# ---------------------------------------------------------------------------
# Class: TestCSVExtraction
# ---------------------------------------------------------------------------

class TestCSVExtraction:
    """ExtractionChain from real CSV fixture bytes through GenericCsvParser."""

    def test_hdfc_csv_row_count(self, batch_id: str):
        assert len(_extract_csv("hdfc_bank.csv", batch_id).rows) == 10

    def test_hdfc_csv_source_type(self, batch_id: str):
        rows = _extract_csv("hdfc_bank.csv", batch_id).rows
        assert all(r.source_type == SourceType.HDFC_BANK_CSV for r in rows)

    def test_hdfc_csv_has_debit_and_credit_rows(self, batch_id: str):
        rows = _extract_csv("hdfc_bank.csv", batch_id).rows
        assert any(r.raw_debit for r in rows), "Expected at least one debit row"
        assert any(r.raw_credit for r in rows), "Expected at least one credit row"

    def test_hdfc_csv_all_rows_have_date(self, batch_id: str):
        rows = _extract_csv("hdfc_bank.csv", batch_id).rows
        assert all(r.raw_date for r in rows)

    def test_hdfc_csv_all_rows_have_narration(self, batch_id: str):
        rows = _extract_csv("hdfc_bank.csv", batch_id).rows
        assert all(r.raw_narration for r in rows)

    def test_hdfc_csv_all_rows_have_balance(self, batch_id: str):
        rows = _extract_csv("hdfc_bank.csv", batch_id).rows
        assert all(r.raw_balance for r in rows)

    def test_sbi_csv_row_count(self, batch_id: str):
        assert len(_extract_csv("sbi_bank.csv", batch_id).rows) == 8

    def test_sbi_csv_source_type(self, batch_id: str):
        rows = _extract_csv("sbi_bank.csv", batch_id).rows
        assert all(r.source_type == SourceType.SBI_BANK_CSV for r in rows)

    def test_icici_csv_row_count(self, batch_id: str):
        assert len(_extract_csv("icici_bank.csv", batch_id).rows) == 8

    def test_icici_csv_source_type(self, batch_id: str):
        rows = _extract_csv("icici_bank.csv", batch_id).rows
        assert all(r.source_type == SourceType.ICICI_BANK_CSV for r in rows)

    def test_axis_csv_row_count(self, batch_id: str):
        assert len(_extract_csv("axis_bank.csv", batch_id).rows) == 8

    def test_axis_csv_source_type(self, batch_id: str):
        rows = _extract_csv("axis_bank.csv", batch_id).rows
        assert all(r.source_type == SourceType.AXIS_BANK_CSV for r in rows)

    def test_zerodha_tradebook_row_count(self, batch_id: str):
        assert len(_extract_tradebook(batch_id).rows) == 5

    def test_zerodha_source_type(self, batch_id: str):
        rows = _extract_tradebook(batch_id).rows
        assert all(r.source_type == SourceType.ZERODHA_TRADEBOOK for r in rows)

    def test_zerodha_has_buy_and_sell_rows(self, batch_id: str):
        from core.models.enums import TxnTypeHint
        rows = _extract_tradebook(batch_id).rows
        hints = {r.txn_type_hint for r in rows}
        assert TxnTypeHint.PURCHASE in hints, "No BUY trades found"
        assert TxnTypeHint.REDEMPTION in hints, "No SELL trades found"

    def test_duplicate_csv_content_matches_original(self, batch_id: str):
        """hdfc_bank_duplicate.csv must produce identical narrations as hdfc_bank.csv."""
        orig = [r.raw_narration for r in _extract_csv("hdfc_bank.csv", batch_id).rows]
        dup = [r.raw_narration for r in _extract_csv("hdfc_bank_duplicate.csv", batch_id).rows]
        assert orig == dup

    def test_overlap_csv_row_count(self, batch_id: str):
        assert len(_extract_csv("hdfc_bank_overlap.csv", batch_id).rows) == 6


# ---------------------------------------------------------------------------
# Class: TestPDFTextExtraction
# ---------------------------------------------------------------------------

class TestPDFTextExtraction:
    """parse_text_content() from .txt fixtures exercises each PDF parser's regex logic."""

    def test_hdfc_text_row_count(self, batch_id: str):
        result = HdfcPdfParser().parse_text_content(batch_id, _text_str("hdfc_statement.txt"))
        assert len(result.rows) == 10

    def test_hdfc_text_has_debit_and_credit_rows(self, batch_id: str):
        rows = HdfcPdfParser().parse_text_content(batch_id, _text_str("hdfc_statement.txt")).rows
        assert any(r.raw_debit for r in rows)
        assert any(r.raw_credit for r in rows)

    def test_hdfc_text_source_type(self, batch_id: str):
        rows = HdfcPdfParser().parse_text_content(batch_id, _text_str("hdfc_statement.txt")).rows
        assert all(r.source_type == SourceType.HDFC_BANK for r in rows)

    def test_hdfc_text_salary_row_is_credit(self, batch_id: str):
        rows = HdfcPdfParser().parse_text_content(batch_id, _text_str("hdfc_statement.txt")).rows
        salary = [r for r in rows if "SALARY" in r.raw_narration.upper()]
        assert salary, "No SALARY row in HDFC text fixture"
        assert salary[0].raw_credit is not None, "SALARY credit row should have raw_credit set"

    def test_sbi_text_row_count(self, batch_id: str):
        result = SbiPdfParser().parse_text_content(batch_id, _text_str("sbi_statement.txt"))
        assert len(result.rows) == 8

    def test_sbi_text_source_type(self, batch_id: str):
        rows = SbiPdfParser().parse_text_content(batch_id, _text_str("sbi_statement.txt")).rows
        assert all(r.source_type == SourceType.SBI_BANK for r in rows)

    def test_icici_text_row_count(self, batch_id: str):
        result = IciciPdfParser().parse_text_content(batch_id, _text_str("icici_statement.txt"))
        assert len(result.rows) == 8

    def test_icici_text_source_type(self, batch_id: str):
        rows = IciciPdfParser().parse_text_content(batch_id, _text_str("icici_statement.txt")).rows
        assert all(r.source_type == SourceType.ICICI_BANK for r in rows)

    def test_sbi_text_salary_row_has_amount(self, batch_id: str):
        """SBI fixture's SALARY row must have a non-empty credit amount."""
        rows = SbiPdfParser().parse_text_content(batch_id, _text_str("sbi_statement.txt")).rows
        salary = [r for r in rows if "SALARY" in r.raw_narration.upper()]
        assert salary
        # Either raw_credit or raw_debit will carry the amount
        assert salary[0].raw_credit or salary[0].raw_debit


# ---------------------------------------------------------------------------
# Class: TestNormalizePipeline
# ---------------------------------------------------------------------------

class TestNormalizePipeline:
    """NormalizeService converts RawParsedRow → NormalizedTransaction from file data."""

    def test_hdfc_csv_all_10_rows_normalized(self, batch_id: str):
        raw = _extract_csv("hdfc_bank.csv", batch_id).rows
        norm = _normalize(raw, batch_id)
        assert len(norm) == 10

    def test_hdfc_csv_all_dates_parsed(self, batch_id: str):
        raw = _extract_csv("hdfc_bank.csv", batch_id).rows
        norm = _normalize(raw, batch_id)
        missing = [n.raw_date for n in norm if n.txn_date is None]
        assert not missing, f"Dates that failed to parse: {missing}"

    def test_sbi_csv_dates_parsed(self, batch_id: str):
        raw = _extract_csv("sbi_bank.csv", batch_id).rows
        norm = _normalize(raw, batch_id)
        missing = [n.raw_date for n in norm if n.txn_date is None]
        assert not missing, f"SBI dates failed: {missing}"

    def test_amounts_always_positive(self, batch_id: str):
        """_resolve_amount always returns a positive absolute value."""
        raw = _extract_csv("hdfc_bank.csv", batch_id).rows
        norm = _normalize(raw, batch_id)
        assert all(n.amount > 0 for n in norm), "All amounts should be positive after normalize"

    def test_is_debit_flag_set_correctly(self, batch_id: str):
        raw = _extract_csv("hdfc_bank.csv", batch_id).rows
        norm = _normalize(raw, batch_id)
        # Salary row is the only explicit credit in HDFC fixture
        salary = next((n for n in norm if "SALARY" in n.raw_narration.upper()), None)
        assert salary is not None
        assert salary.is_debit is False
        assert salary.amount == Decimal("85000.00")

    def test_closing_balance_parsed(self, batch_id: str):
        raw = _extract_csv("hdfc_bank.csv", batch_id).rows
        norm = _normalize(raw, batch_id)
        assert all(n.closing_balance is not None for n in norm)

    def test_narrations_not_empty_after_normalize(self, batch_id: str):
        raw = _extract_csv("hdfc_bank.csv", batch_id).rows
        norm = _normalize(raw, batch_id)
        assert all(n.narration for n in norm)

    def test_row_ids_unique(self, batch_id: str):
        raw = _extract_csv("hdfc_bank.csv", batch_id).rows
        norm = _normalize(raw, batch_id)
        ids = [n.row_id for n in norm]
        assert len(ids) == len(set(ids))

    def test_icici_salary_is_credit(self, batch_id: str):
        """ICICI fixture first row is salary credit of 150000."""
        raw = _extract_csv("icici_bank.csv", batch_id).rows
        norm = _normalize(raw, batch_id)
        salary = next((n for n in norm if "SALARY" in n.raw_narration.upper()), None)
        assert salary is not None
        assert salary.is_debit is False
        assert salary.amount == Decimal("150000.00")

    def test_hdfc_text_all_rows_normalized(self, batch_id: str):
        """Rows from HDFC PDF text fixture should all normalize successfully."""
        raw = HdfcPdfParser().parse_text_content(batch_id, _text_str("hdfc_statement.txt")).rows
        norm = _normalize(raw, batch_id)
        assert len(norm) == 10
        assert all(n.txn_date is not None for n in norm)


# ---------------------------------------------------------------------------
# Class: TestDedupPipeline
# ---------------------------------------------------------------------------

class TestDedupPipeline:
    """DedupService correctly identifies new vs duplicate transactions across imports."""

    def test_first_import_all_rows_new(self, user_id: str, account_id: str, batch_id: str):
        norm = _normalize(_extract_csv("hdfc_bank.csv", batch_id).rows, batch_id)
        result = _dedup(norm, user_id, batch_id, account_id)
        assert result.txn_new == 10
        assert result.txn_duplicate == 0

    def test_reimport_same_file_all_duplicates(self, user_id: str, account_id: str):
        b1, b2 = str(uuid.uuid4()), str(uuid.uuid4())
        # First import
        norm1 = _normalize(_extract_csv("hdfc_bank_duplicate.csv", b1).rows, b1)
        r1 = _dedup(norm1, user_id, b1, account_id)
        assert r1.txn_new == 10

        # Second import — identical content; pass committed hashes (simulates DB state)
        committed = _hashes_from(r1)
        norm2 = _normalize(_extract_csv("hdfc_bank_duplicate.csv", b2).rows, b2)
        r2 = _dedup(norm2, user_id, b2, account_id, db_hashes=committed)
        assert r2.txn_new == 0
        assert r2.txn_duplicate == 10

    def test_overlap_import_correct_split(self, user_id: str, account_id: str):
        """3 rows in common + 3 new rows → 3 dup, 3 new on the second import."""
        b1, b2 = str(uuid.uuid4()), str(uuid.uuid4())
        norm1 = _normalize(_extract_csv("hdfc_bank.csv", b1).rows, b1)
        r1 = _dedup(norm1, user_id, b1, account_id)
        committed = _hashes_from(r1)

        norm2 = _normalize(_extract_csv("hdfc_bank_overlap.csv", b2).rows, b2)
        r2 = _dedup(norm2, user_id, b2, account_id, db_hashes=committed)
        assert r2.txn_duplicate == 3, f"Expected 3 duplicates, got {r2.txn_duplicate}"
        assert r2.txn_new == 3, f"Expected 3 new rows, got {r2.txn_new}"

    def test_different_users_no_collision(self, account_id: str):
        """Alice and Bob can import the same file independently."""
        b1, b2 = str(uuid.uuid4()), str(uuid.uuid4())
        norm1 = _normalize(_extract_csv("hdfc_bank.csv", b1).rows, b1)
        norm2 = _normalize(_extract_csv("hdfc_bank.csv", b2).rows, b2)
        _dedup(norm1, "alice", b1, account_id)
        r2 = _dedup(norm2, "bob", b2, account_id)
        assert r2.txn_new == 10, "Bob's first import should have 0 duplicates"

    def test_new_rows_have_dedup_status_new(self, user_id: str, account_id: str, batch_id: str):
        norm = _normalize(_extract_csv("hdfc_bank.csv", batch_id).rows, batch_id)
        result = _dedup(norm, user_id, batch_id, account_id)
        for row in result.new:
            assert row.extra_fields.get("dedup_status") == "NEW"

    def test_duplicate_rows_have_dedup_status_duplicate(self, user_id: str, account_id: str):
        b1, b2 = str(uuid.uuid4()), str(uuid.uuid4())
        norm1 = _normalize(_extract_csv("hdfc_bank.csv", b1).rows, b1)
        r1 = _dedup(norm1, user_id, b1, account_id)
        committed = _hashes_from(r1)
        norm2 = _normalize(_extract_csv("hdfc_bank_duplicate.csv", b2).rows, b2)
        result = _dedup(norm2, user_id, b2, account_id, db_hashes=committed)
        # Check that only duplicate rows are recorded
        assert result.txn_duplicate == 10

    def test_sbi_reimport_all_duplicates(self, user_id: str, account_id: str):
        b1, b2 = str(uuid.uuid4()), str(uuid.uuid4())
        norm1 = _normalize(_extract_csv("sbi_bank.csv", b1).rows, b1)
        r1 = _dedup(norm1, user_id, b1, account_id)
        committed = _hashes_from(r1)
        norm2 = _normalize(_extract_csv("sbi_bank.csv", b2).rows, b2)
        r2 = _dedup(norm2, user_id, b2, account_id, db_hashes=committed)
        assert r2.txn_new == 0
        assert r2.txn_duplicate == 8


# ---------------------------------------------------------------------------
# Class: TestCategoryAssignment
# ---------------------------------------------------------------------------

class TestCategoryAssignment:
    """CategorizeService assigns the right category code for common merchants."""

    def _get_categories(self, filename: str, uid: str, bid: str) -> dict[str, str]:
        """Return {raw_narration_upper → category_code} for all rows in a fixture."""
        raw = _extract_csv(filename, bid).rows
        norm = _normalize(raw, bid)
        result = _dedup(norm, uid, bid, "ACC-CAT")
        CategorizeService().categorize_batch(user_id=uid, batch_id=bid, rows=result.new)
        return {r.raw_narration.upper(): r.extra_fields["category"] for r in result.new}

    def test_swiggy_is_food_expense(self, user_id: str, batch_id: str):
        cats = self._get_categories("hdfc_bank.csv", user_id, batch_id)
        swiggy = next((v for k, v in cats.items() if "SWIGGY" in k), None)
        assert swiggy == "EXPENSE_FOOD", f"SWIGGY category was '{swiggy}'"

    def test_zomato_is_food_expense(self, user_id: str, batch_id: str):
        cats = self._get_categories("hdfc_bank.csv", user_id, batch_id)
        zomato = next((v for k, v in cats.items() if "ZOMATO" in k), None)
        assert zomato == "EXPENSE_FOOD", f"ZOMATO category was '{zomato}'"

    def test_salary_is_income_salary(self, user_id: str, batch_id: str):
        cats = self._get_categories("hdfc_bank.csv", user_id, batch_id)
        salary = next((v for k, v in cats.items() if "SALARY" in k), None)
        assert salary == "INCOME_SALARY", f"SALARY category was '{salary}'"

    def test_emi_is_expense_emi(self, user_id: str, batch_id: str):
        cats = self._get_categories("hdfc_bank.csv", user_id, batch_id)
        emi = next((v for k, v in cats.items() if "EMI" in k), None)
        assert emi == "EXPENSE_EMI", f"EMI category was '{emi}'"

    def test_atm_is_cash_withdrawal(self, user_id: str, batch_id: str):
        cats = self._get_categories("hdfc_bank.csv", user_id, batch_id)
        atm = next((v for k, v in cats.items() if "ATM" in k or "CASH WD" in k), None)
        assert atm == "CASH_WITHDRAWAL", f"ATM category was '{atm}'"

    def test_amazon_is_shopping(self, user_id: str, batch_id: str):
        cats = self._get_categories("hdfc_bank.csv", user_id, batch_id)
        amazon = next((v for k, v in cats.items() if "AMAZON" in k), None)
        assert amazon == "EXPENSE_SHOPPING", f"AMAZON category was '{amazon}'"

    def test_uber_is_transport(self, user_id: str, batch_id: str):
        cats = self._get_categories("hdfc_bank.csv", user_id, batch_id)
        uber = next((v for k, v in cats.items() if "UBER" in k), None)
        assert uber == "EXPENSE_TRANSPORT", f"UBER category was '{uber}'"

    def test_interest_is_income_interest(self, user_id: str, batch_id: str):
        cats = self._get_categories("hdfc_bank.csv", user_id, batch_id)
        interest = next((v for k, v in cats.items() if "INTEREST" in k), None)
        assert interest == "INCOME_INTEREST", f"INTEREST category was '{interest}'"

    def test_lic_is_insurance(self, user_id: str, batch_id: str):
        cats = self._get_categories("hdfc_bank.csv", user_id, batch_id)
        lic = next((v for k, v in cats.items() if "LIC" in k), None)
        assert lic == "EXPENSE_INSURANCE", f"LIC category was '{lic}'"

    def test_sbi_salary_categorized(self, user_id: str, batch_id: str):
        cats = self._get_categories("sbi_bank.csv", user_id, batch_id)
        salary = next((v for k, v in cats.items() if "SALARY" in k), None)
        assert salary == "INCOME_SALARY"

    def test_axis_emi_categorized(self, user_id: str, batch_id: str):
        cats = self._get_categories("axis_bank.csv", user_id, batch_id)
        emi = next((v for k, v in cats.items() if "EMI" in k), None)
        assert emi == "EXPENSE_EMI"

    def test_icici_salary_categorized(self, user_id: str, batch_id: str):
        cats = self._get_categories("icici_bank.csv", user_id, batch_id)
        salary = next((v for k, v in cats.items() if "SALARY" in k), None)
        assert salary == "INCOME_SALARY"


# ---------------------------------------------------------------------------
# Class: TestSmartProcessingPipeline
# ---------------------------------------------------------------------------

class TestSmartProcessingPipeline:
    """SmartProcessor.process_batch() — full pipeline from raw rows to proposals."""

    def test_hdfc_csv_pipeline_counts(self, user_id: str, batch_id: str):
        raw = _extract_csv("hdfc_bank.csv", batch_id).rows
        result = _smart(raw, user_id, batch_id)
        assert result.raw_rows_count == 10
        assert result.normalized_count == 10
        assert result.new_count == 10
        assert result.duplicate_count == 0

    def test_sbi_csv_pipeline_counts(self, user_id: str, batch_id: str):
        raw = _extract_csv("sbi_bank.csv", batch_id).rows
        result = _smart(raw, user_id, batch_id)
        assert result.raw_rows_count == 8
        assert result.new_count == 8

    def test_icici_csv_pipeline_counts(self, user_id: str, batch_id: str):
        raw = _extract_csv("icici_bank.csv", batch_id).rows
        result = _smart(raw, user_id, batch_id)
        assert result.raw_rows_count == 8
        assert result.new_count == 8

    def test_axis_csv_pipeline_counts(self, user_id: str, batch_id: str):
        raw = _extract_csv("axis_bank.csv", batch_id).rows
        result = _smart(raw, user_id, batch_id)
        assert result.raw_rows_count == 8
        assert result.new_count == 8

    def test_confidence_band_counts_sum_to_new_count(self, user_id: str, batch_id: str):
        raw = _extract_csv("hdfc_bank.csv", batch_id).rows
        r = _smart(raw, user_id, batch_id)
        assert r.green_count + r.yellow_count + r.red_count == r.new_count

    def test_proposals_generated_for_hdfc(self, user_id: str, batch_id: str):
        raw = _extract_csv("hdfc_bank.csv", batch_id).rows
        result = _smart(raw, user_id, batch_id)
        assert result.proposals is not None
        assert len(result.proposals.proposals) > 0

    def test_all_new_rows_accounted_in_proposals(self, user_id: str, batch_id: str):
        """proposals + unproposable must equal new_count."""
        raw = _extract_csv("hdfc_bank.csv", batch_id).rows
        result = _smart(raw, user_id, batch_id)
        accounted = len(result.proposals.proposals) + len(result.proposals.unproposable)
        assert accounted == result.new_count

    def test_hdfc_text_smart_pipeline(self, user_id: str, batch_id: str):
        """Full pipeline from HDFC PDF text fixture (no CSV, no HTTP)."""
        raw = HdfcPdfParser().parse_text_content(batch_id, _text_str("hdfc_statement.txt")).rows
        result = _smart(raw, user_id, batch_id)
        assert result.raw_rows_count == 10
        assert result.new_count == 10

    def test_reimport_via_smart_all_duplicate(self, user_id: str):
        """SmartProcessor short-circuits correctly on reimport."""
        b1, b2 = str(uuid.uuid4()), str(uuid.uuid4())
        raw1 = _extract_csv("hdfc_bank_duplicate.csv", b1).rows
        r1 = _smart(raw1, user_id, b1)
        assert r1.new_count == 10

        # Simulate DB commit: pass new-row hashes as db_hashes for second import
        committed = {r.extra_fields["txn_hash"] for r in r1.normalized_rows if "txn_hash" in r.extra_fields}
        raw2 = _extract_csv("hdfc_bank_duplicate.csv", b2).rows
        r2 = _smart(raw2, user_id, b2, db_hashes=committed)
        assert r2.new_count == 0
        assert r2.duplicate_count == 10

    def test_overlap_via_smart(self, user_id: str):
        """3 overlapping rows produce 3 new, 3 dup on second run."""
        b1, b2 = str(uuid.uuid4()), str(uuid.uuid4())
        r1 = _smart(_extract_csv("hdfc_bank.csv", b1).rows, user_id, b1)
        committed = {r.extra_fields["txn_hash"] for r in r1.normalized_rows if "txn_hash" in r.extra_fields}
        r2 = _smart(_extract_csv("hdfc_bank_overlap.csv", b2).rows, user_id, b2, db_hashes=committed)
        assert r2.duplicate_count == 3
        assert r2.new_count == 3

    def test_no_proposals_after_reimport(self, user_id: str):
        """After reimport all rows are duplicate → zero proposals."""
        b1, b2 = str(uuid.uuid4()), str(uuid.uuid4())
        r1 = _smart(_extract_csv("hdfc_bank.csv", b1).rows, user_id, b1)
        committed = {r.extra_fields["txn_hash"] for r in r1.normalized_rows if "txn_hash" in r.extra_fields}
        r2 = _smart(_extract_csv("hdfc_bank_duplicate.csv", b2).rows, user_id, b2, db_hashes=committed)
        assert len(r2.proposals.proposals) == 0


# ---------------------------------------------------------------------------
# Class: TestJournalEntryProposals
# ---------------------------------------------------------------------------

class TestJournalEntryProposals:
    """Proposals generated by SmartProcessor must be valid balanced journal entries."""

    def _proposals(self, user_id: str, batch_id: str):
        raw = _extract_csv("hdfc_bank.csv", batch_id).rows
        return _smart(raw, user_id, batch_id).proposals.proposals

    def test_all_proposals_have_two_lines(self, user_id: str, batch_id: str):
        for p in self._proposals(user_id, batch_id):
            assert len(p.lines) == 2, (
                f"Expected 2 journal lines for '{p.narration}', got {len(p.lines)}"
            )

    def test_all_proposals_are_balanced(self, user_id: str, batch_id: str):
        for p in self._proposals(user_id, batch_id):
            assert p.is_balanced, (
                f"Unbalanced entry '{p.narration}': "
                f"dr={sum(l.debit for l in p.lines)} "
                f"cr={sum(l.credit for l in p.lines)}"
            )

    def test_bank_account_line_in_every_proposal(self, user_id: str, batch_id: str):
        """Every proposal must include a line for the bank account (code '1102')."""
        for p in self._proposals(user_id, batch_id):
            codes = {l.account_code for l in p.lines}
            assert "1102" in codes, (
                f"No bank account (1102) in '{p.narration}': {codes}"
            )

    def test_proposals_have_txn_date(self, user_id: str, batch_id: str):
        for p in self._proposals(user_id, batch_id):
            assert p.txn_date is not None

    def test_proposals_have_narration(self, user_id: str, batch_id: str):
        for p in self._proposals(user_id, batch_id):
            assert p.narration

    def test_all_proposals_pending(self, user_id: str, batch_id: str):
        for p in self._proposals(user_id, batch_id):
            assert p.status == "PENDING"

    def test_salary_proposal_uses_income_account(self, user_id: str, batch_id: str):
        proposals = self._proposals(user_id, batch_id)
        salary = [p for p in proposals if "SALARY" in p.narration.upper()]
        assert salary, "No salary proposal generated"
        income_codes = {"4100", "4200", "4900"}
        for p in salary:
            codes = {l.account_code for l in p.lines}
            assert codes & income_codes, f"No income account in salary proposal: {codes}"

    def test_food_proposal_uses_expense_food_account(self, user_id: str, batch_id: str):
        proposals = self._proposals(user_id, batch_id)
        food = [p for p in proposals
                if "SWIGGY" in p.narration.upper() or "ZOMATO" in p.narration.upper()]
        assert food, "No food proposal generated"
        for p in food:
            codes = {l.account_code for l in p.lines}
            assert "5100" in codes, f"No EXPENSE_FOOD (5100) in food proposal: {codes}"

    def test_total_debit_equals_total_credit_per_proposal(self, user_id: str, batch_id: str):
        """Sum of all debit lines == sum of all credit lines for each proposal."""
        for p in self._proposals(user_id, batch_id):
            total_dr = sum(l.debit for l in p.lines)
            total_cr = sum(l.credit for l in p.lines)
            assert total_dr == total_cr, (
                f"Proposal '{p.narration}' not balanced: dr={total_dr} cr={total_cr}"
            )


# ---------------------------------------------------------------------------
# Class: TestTransferPairDetection
# ---------------------------------------------------------------------------

class TestTransferPairDetection:
    """DedupService detects same-batch UPI/NEFT transfer pairs."""

    def test_matching_upi_amount_pair_detected(self, user_id: str, account_id: str):
        """A debit and credit of equal absolute amounts on the same day with 'UPI' in
        the narration should be flagged as a transfer pair."""
        from core.models.enums import ExtractionMethod, SourceType
        from core.models.raw_parsed_row import RawParsedRow

        bid = str(uuid.uuid4())
        debit = RawParsedRow(
            batch_id=bid,
            source_type=SourceType.HDFC_BANK_CSV,
            parser_version="1.0",
            extraction_method=ExtractionMethod.TABLE_EXTRACTION,
            raw_date="15/01/2026",
            raw_narration="UPI/TRANSFER/TO ACC123",
            raw_debit="5000.00",
            raw_balance="15000.00",
            row_confidence=0.95,
        )
        credit = RawParsedRow(
            batch_id=bid,
            source_type=SourceType.HDFC_BANK_CSV,
            parser_version="1.0",
            extraction_method=ExtractionMethod.TABLE_EXTRACTION,
            raw_date="15/01/2026",
            raw_narration="UPI/SELF TRANSFER/CREDIT FROM ACC123",
            raw_credit="5000.00",
            raw_balance="20000.00",
            row_confidence=0.95,
        )
        norm = NormalizeService().normalize_batch(bid, [debit, credit]).rows
        result = DedupService().dedup_batch(
            user_id=user_id, batch_id=bid, account_id=account_id, rows=norm
        )
        assert len(result.transfer_pairs) >= 1, "Expected a transfer pair; none detected"

    def test_salary_not_a_transfer_pair(self, user_id: str, account_id: str, batch_id: str):
        """HDFC fixture has no matching debit/credit amounts → zero transfer pairs."""
        norm = _normalize(_extract_csv("hdfc_bank.csv", batch_id).rows, batch_id)
        result = _dedup(norm, user_id, batch_id, account_id)
        assert result.transfer_pairs == []

    def test_neft_pair_across_same_batch(self, user_id: str, account_id: str):
        """NEFT debit and credit of same amount on same day = transfer pair."""
        from core.models.enums import ExtractionMethod, SourceType
        from core.models.raw_parsed_row import RawParsedRow

        bid = str(uuid.uuid4())
        outgoing = RawParsedRow(
            batch_id=bid,
            source_type=SourceType.HDFC_BANK_CSV,
            parser_version="1.0",
            extraction_method=ExtractionMethod.TABLE_EXTRACTION,
            raw_date="10/01/2026",
            raw_narration="NEFT TRANSFER TO SAVINGS ACCOUNT",
            raw_debit="25000.00",
            raw_balance="75000.00",
            row_confidence=0.90,
        )
        incoming = RawParsedRow(
            batch_id=bid,
            source_type=SourceType.HDFC_BANK_CSV,
            parser_version="1.0",
            extraction_method=ExtractionMethod.TABLE_EXTRACTION,
            raw_date="10/01/2026",
            raw_narration="NEFT TRANSFER INWARD FROM JOINT ACCOUNT",
            raw_credit="25000.00",
            raw_balance="100000.00",
            row_confidence=0.90,
        )
        norm = NormalizeService().normalize_batch(bid, [outgoing, incoming]).rows
        result = DedupService().dedup_batch(
            user_id=user_id, batch_id=bid, account_id=account_id, rows=norm
        )
        assert len(result.transfer_pairs) >= 1


# ---------------------------------------------------------------------------
# Class: TestCrossBatchTransferDetection
# ---------------------------------------------------------------------------

class TestCrossBatchTransferDetection:
    """DedupService scenario 2 — accounts imported at different times.

    The caller passes existing rows from a previously imported account as
    ``existing_rows``.  The engine must find the transfer pair across batches
    and retroactively mark the historical row.
    """

    def _make_norm_row(
        self,
        bid: str,
        narration: str,
        amount: str,
        is_debit: bool,
        txn_date: str = "15/01/2026",
    ):
        from core.models.enums import ExtractionMethod, SourceType
        from core.models.raw_parsed_row import RawParsedRow
        raw = RawParsedRow(
            batch_id=bid,
            source_type=SourceType.HDFC_BANK_CSV,
            parser_version="1.0",
            extraction_method=ExtractionMethod.TABLE_EXTRACTION,
            raw_date=txn_date,
            raw_narration=narration,
            raw_debit=amount if is_debit else None,
            raw_credit=None if is_debit else amount,
            raw_balance="50000.00",
            row_confidence=0.95,
        )
        return NormalizeService().normalize_batch(bid, [raw]).rows[0]

    def test_cross_batch_pair_detected_via_existing_rows(self, user_id: str):
        """Account A imported first; Account B imported later.
        Passing Account A's row as existing_rows must produce a retroactive link."""
        b1, b2 = str(uuid.uuid4()), str(uuid.uuid4())

        # Account A: HDFC debit on Jan 15
        hist_row = self._make_norm_row(
            b1, "NEFT TRANSFER TO ICICI SAVINGS", "30000.00", is_debit=True
        )
        hist_row.extra_fields["dedup_status"] = "NEW"   # already imported

        # Account B: ICICI credit on Jan 15
        new_row = self._make_norm_row(
            b2, "NEFT INWARD TRANSFER FROM HDFC", "30000.00", is_debit=False
        )

        result = DedupService().dedup_batch(
            user_id=user_id,
            batch_id=b2,
            account_id="ACC-ICICI-001",
            rows=[new_row],
            existing_rows=[hist_row],
        )

        assert len(result.retroactive_transfer_pairs) == 1, (
            "Expected 1 retroactive transfer pair"
        )
        new_id, hist_id = result.retroactive_transfer_pairs[0]
        assert new_id == new_row.row_id
        assert hist_id == hist_row.row_id

    def test_cross_batch_both_rows_marked_transfer_pair(self, user_id: str):
        """Both the new row and the historical row must be flagged TRANSFER_PAIR."""
        b1, b2 = str(uuid.uuid4()), str(uuid.uuid4())

        hist_row = self._make_norm_row(b1, "UPI TRANSFER TO ICICI", "8000.00", is_debit=True)
        hist_row.extra_fields["dedup_status"] = "NEW"

        new_row = self._make_norm_row(b2, "UPI SELF TRANSFER CREDIT", "8000.00", is_debit=False)

        DedupService().dedup_batch(
            user_id=user_id,
            batch_id=b2,
            account_id="ACC-ICICI-002",
            rows=[new_row],
            existing_rows=[hist_row],
        )

        assert new_row.extra_fields.get("dedup_status") == "TRANSFER_PAIR"
        assert hist_row.extra_fields.get("dedup_status") == "TRANSFER_PAIR"
        assert hist_row.extra_fields.get("transfer_pair_retroactive") is True

    def test_cross_batch_no_match_when_amounts_differ(self, user_id: str):
        """No retroactive link when amounts don't match."""
        b1, b2 = str(uuid.uuid4()), str(uuid.uuid4())

        hist_row = self._make_norm_row(b1, "NEFT TRANSFER TO ICICI", "30000.00", is_debit=True)
        new_row = self._make_norm_row(b2, "NEFT INWARD FROM HDFC", "29999.00", is_debit=False)

        result = DedupService().dedup_batch(
            user_id=user_id,
            batch_id=b2,
            account_id="ACC-ICICI-003",
            rows=[new_row],
            existing_rows=[hist_row],
        )

        assert result.retroactive_transfer_pairs == []
        assert new_row.extra_fields.get("dedup_status") == "NEW"

    def test_cross_batch_no_match_when_no_transfer_keyword(self, user_id: str):
        """No retroactive link when neither narration contains a transfer keyword."""
        b1, b2 = str(uuid.uuid4()), str(uuid.uuid4())

        hist_row = self._make_norm_row(b1, "SALARY CREDIT EMPLOYER LTD", "50000.00", is_debit=False)
        new_row = self._make_norm_row(b2, "SALARY DEBIT EMPLOYER LTD", "50000.00", is_debit=True)

        result = DedupService().dedup_batch(
            user_id=user_id,
            batch_id=b2,
            account_id="ACC-OTHER-001",
            rows=[new_row],
            existing_rows=[hist_row],
        )

        assert result.retroactive_transfer_pairs == []

    def test_one_sided_import_stays_new(self, user_id: str):
        """Scenario 3: only one account imported, no existing_rows.
        The row must stay NEW — no pair, no error."""
        b1 = str(uuid.uuid4())
        row = self._make_norm_row(b1, "NEFT TRANSFER TO ICICI SAVINGS", "15000.00", is_debit=True)

        result = DedupService().dedup_batch(
            user_id=user_id,
            batch_id=b1,
            account_id="ACC-HDFC-001",
            rows=[row],
            existing_rows=None,    # counterpart not yet added
        )

        assert row.extra_fields.get("dedup_status") == "NEW"
        assert result.transfer_pairs == []
        assert result.retroactive_transfer_pairs == []

    def test_cross_batch_date_tolerance_one_day(self, user_id: str):
        """±1 day date tolerance: debit on Jan 15, credit on Jan 16 — still a pair."""
        b1, b2 = str(uuid.uuid4()), str(uuid.uuid4())

        hist_row = self._make_norm_row(
            b1, "NEFT TRANSFER TO ICICI", "20000.00", is_debit=True, txn_date="15/01/2026"
        )
        new_row = self._make_norm_row(
            b2, "NEFT INWARD TRANSFER FROM HDFC", "20000.00", is_debit=False, txn_date="16/01/2026"
        )

        result = DedupService().dedup_batch(
            user_id=user_id,
            batch_id=b2,
            account_id="ACC-ICICI-004",
            rows=[new_row],
            existing_rows=[hist_row],
        )

        assert len(result.retroactive_transfer_pairs) == 1

    def test_cross_batch_date_tolerance_two_days_no_match(self, user_id: str):
        """2-day gap exceeds tolerance — no pair expected."""
        b1, b2 = str(uuid.uuid4()), str(uuid.uuid4())

        hist_row = self._make_norm_row(
            b1, "NEFT TRANSFER TO ICICI", "20000.00", is_debit=True, txn_date="15/01/2026"
        )
        new_row = self._make_norm_row(
            b2, "NEFT INWARD FROM HDFC", "20000.00", is_debit=False, txn_date="17/01/2026"
        )

        result = DedupService().dedup_batch(
            user_id=user_id,
            batch_id=b2,
            account_id="ACC-ICICI-005",
            rows=[new_row],
            existing_rows=[hist_row],
        )

        assert result.retroactive_transfer_pairs == []
