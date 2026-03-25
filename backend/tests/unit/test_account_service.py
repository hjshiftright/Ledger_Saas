import pytest
from onboarding.account.schemas import BankAccountSetupDTO, CashWalletSetupDTO
from onboarding.account.service import AccountSetupService
from repositories.sqla_account_repo import AccountRepository
from repositories.sqla_institution_repo import SqlAlchemyInstitutionRepository
from repositories.sqla_account_detail_repo import SqlAlchemyAccountDetailRepository
from onboarding.coa.service import COASetupService
from common.enums import BankAccountType

@pytest.fixture
def service(session):
    acc = AccountRepository(session)
    inst = SqlAlchemyInstitutionRepository(session)
    det = SqlAlchemyAccountDetailRepository(session)

    coa_sys = COASetupService(acc)
    coa_sys.create_default_coa()

    inst.create({"name": "Test Bank", "institution_type": "BANK"})

    return AccountSetupService(acc, inst, det)

def test_add_bank_account(service):
    dto = BankAccountSetupDTO(
        institution_id=1,
        display_name="Primary Checking",
        account_number_masked="1234",
        bank_account_type=BankAccountType.SAVINGS
    )
    result = service.add_bank_account(dto)

    coa_node = result["coa"]
    detail = result["detail"]

    assert coa_node.name == "Primary Checking"
    assert coa_node.account_type == "ASSET"
    assert detail.institution_id == 1
    assert detail.bank_account_type == "SAVINGS"

def test_add_cash_wallet(service):
    dto = CashWalletSetupDTO(display_name="Wallet")
    result = service.add_cash_wallet(dto)

    assert result["coa"].name == "Wallet"
    assert result["detail"] is None

