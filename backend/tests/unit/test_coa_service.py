import pytest
from onboarding.coa.service import COASetupService
from repositories.sqla_account_repo import AccountRepository
from common.exceptions import BusinessRuleError, NotFoundError, SystemAccountError, ValidationError

@pytest.fixture
def account_repo(session):
    return AccountRepository(session)

@pytest.fixture
def coa_service(account_repo):
    return COASetupService(account_repo)

def test_create_default_coa_populates_repository(coa_service):
    accounts = coa_service.create_default_coa()
    assert len(accounts) > 5
    assert coa_service.is_coa_ready()

def test_get_coa_tree_returns_hierarchy(coa_service):
    coa_service.create_default_coa()
    tree_resp = coa_service.get_coa_tree()
    root_names = {node.name for node in tree_resp.items}
    assert {"Assets", "Liabilities", "Equity", "Income", "Expenses"}.issubset(root_names)

def test_rename_account_updates_name(coa_service):
    accounts = coa_service.create_default_coa()
    target = next(a for a in accounts if not a.is_system)
    
    updated = coa_service.rename_account(target.id, "Newly Renamed")
    assert updated.name == "Newly Renamed"

def test_rename_system_account_fails(coa_service):
    accounts = coa_service.create_default_coa()
    target = next(a for a in accounts if a.is_system)
    
    with pytest.raises(SystemAccountError):
        coa_service.rename_account(target.id, "Hacked System Account")

def test_add_custom_category(coa_service):
    accounts = coa_service.create_default_coa()
    expenses = next(a for a in accounts if a.name == "Expenses")
    
    new_cat = coa_service.add_custom_category(expenses.id, "Pet Care")
    assert new_cat.name == "Pet Care"
    assert new_cat.parent_id == expenses.id
    assert new_cat.type == "EXPENSE"
