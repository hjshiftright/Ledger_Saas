import pytest
from onboarding.networth.service import NetWorthService
from onboarding.account.schemas import BankAccountSetupDTO, CreditCardSetupDTO
from onboarding.account.service import AccountSetupService
from onboarding.opening_balance.schemas import OpeningBalanceDTO
from onboarding.opening_balance.service import OpeningBalanceService
from onboarding.coa.service import COASetupService
from common.enums import BankAccountType
from repositories.sqla_account_repo import AccountRepository
from repositories.sqla_institution_repo import SqlAlchemyInstitutionRepository
from repositories.sqla_account_detail_repo import SqlAlchemyAccountDetailRepository
from repositories.sqla_transaction_repo import TransactionRepository
from repositories.sqla_snapshot_repo import SqlAlchemySnapshotRepository

async def test_compute_net_worth(session):
    acc_repo = AccountRepository(session)
    inst_repo = SqlAlchemyInstitutionRepository(session)
    det_repo = SqlAlchemyAccountDetailRepository(session)
    tx_repo = TransactionRepository(session)
    snap_repo = SqlAlchemySnapshotRepository(session)

    coa_sys = COASetupService(acc_repo)
    await coa_sys.create_default_coa()

    await inst_repo.create({"name": "Test Bank", "institution_type": "BANK"})
    acc_sys = AccountSetupService(acc_repo, inst_repo, det_repo)
    bank_acc = await acc_sys.add_bank_account(BankAccountSetupDTO(
        institution_id=1, display_name="Checking", account_number_masked="1234", bank_account_type=BankAccountType.SAVINGS
    ))
    cc_acc = await acc_sys.add_credit_card(CreditCardSetupDTO(
        institution_id=1, display_name="CC", last_four_digits="4444", credit_limit=10000, billing_cycle_day=1, interest_rate_annual=15.0
    ))

    ob_sys = OpeningBalanceService(tx_repo, acc_repo)
    await ob_sys.set_opening_balance(OpeningBalanceDTO(
        account_id=bank_acc["coa"].id, balance_amount=15000.0, balance_date="2026-04-01"
    ))
    await ob_sys.set_opening_balance(OpeningBalanceDTO(
        account_id=cc_acc["coa"].id, balance_amount=2500.0, balance_date="2026-04-01"
    ))

    nw_sys = NetWorthService(snap_repo, acc_repo, tx_repo)
    res = await nw_sys.compute_initial_net_worth("2026-04-01")

    assert res.total_assets == 15000.0
    assert res.total_liabilities == 2500.0
    assert res.net_worth == 12500.0
    assert res.breakdown["liquid_assets"] == 15000.0
    assert res.breakdown["short_term_liabilities"] == 2500.0
