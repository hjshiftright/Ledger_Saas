import pytest
from onboarding.opening_balance.schemas import OpeningBalanceDTO, BulkOpeningBalanceDTO
from onboarding.opening_balance.service import OpeningBalanceService
from onboarding.coa.service import COASetupService
from repositories.sqla_account_repo import AccountRepository
from repositories.sqla_transaction_repo import TransactionRepository

@pytest.fixture
def ob_service(session):
    acc_repo = AccountRepository(session)
    tx_repo = TransactionRepository(session)

    coa = COASetupService(acc_repo)
    coa.create_default_coa()

    return OpeningBalanceService(tx_repo, acc_repo), acc_repo, tx_repo

def test_set_opening_balance_asset(ob_service):
    service, acc_repo, tx_repo = ob_service
    tree = acc_repo.get_tree()
    asset_acc = next(n for n in tree if n.code == "1201")

    dto = OpeningBalanceDTO(
        account_id=asset_acc.id,
        balance_amount=50000.0,
        balance_date="2026-04-01"
    )

    res = service.set_opening_balance(dto, user_id=1)

    assert res is not None
    assert len(res.lines) == 2
    line_types = {l.line_type for l in res.lines}
    assert "DEBIT" in line_types
    assert "CREDIT" in line_types

def test_set_ob_zero_returns_none(ob_service):
    service, acc_repo, tx_repo = ob_service
    tree = acc_repo.get_tree()
    any_acc = tree[0]
    dto = OpeningBalanceDTO(
        account_id=any_acc.id,
        balance_amount=0.0,
        balance_date="2026-04-01"
    )
    res = service.set_opening_balance(dto, user_id=1)
    assert res is None

