import pytest
from onboarding.institution.schemas import InstitutionCreateDTO
from onboarding.institution.service import InstitutionService
from repositories.sqla_institution_repo import SqlAlchemyInstitutionRepository
from common.enums import InstitutionType
from common.exceptions import DuplicateError, NotFoundError, ValidationError

@pytest.fixture
def repo(session):
    return SqlAlchemyInstitutionRepository(session)

@pytest.fixture
def service(repo):
    return InstitutionService(repo)

def test_add_institution_creates_successfully(service):
    request = InstitutionCreateDTO(
        name="State Bank of India",
        institution_type=InstitutionType.BANK,
        website_url="https://sbi.co.in"
    )
    
    resp = service.add_institution(request)
    assert resp.name == "State Bank of India"
    assert resp.institution_type == InstitutionType.BANK

def test_add_duplicate_institution_fails(service):
    request = InstitutionCreateDTO(
        name="HDFC",
        institution_type=InstitutionType.BANK
    )
    
    service.add_institution(request)
    
    with pytest.raises(DuplicateError):
        service.add_institution(request)

def test_update_institution_works(service):
    # setup
    request = InstitutionCreateDTO(
        name="Zerodha",
        institution_type=InstitutionType.BROKERAGE
    )
    created = service.add_institution(request)
    
    # modify
    request.website_url = "https://zerodha.com"
    updated = service.update_institution(created.id, request)
    
    assert updated.website_url == "https://zerodha.com"
