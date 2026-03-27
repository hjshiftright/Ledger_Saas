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

async def test_add_institution_creates_successfully(service):
    request = InstitutionCreateDTO(
        name="State Bank of India",
        institution_type=InstitutionType.BANK,
        website_url="https://sbi.co.in"
    )

    resp = await service.add_institution(request)
    assert resp.name == "State Bank of India"
    assert resp.institution_type == InstitutionType.BANK

async def test_add_duplicate_institution_fails(service):
    request = InstitutionCreateDTO(
        name="HDFC",
        institution_type=InstitutionType.BANK
    )

    await service.add_institution(request)

    with pytest.raises(DuplicateError):
        await service.add_institution(request)

async def test_update_institution_works(service):
    request = InstitutionCreateDTO(
        name="Zerodha",
        institution_type=InstitutionType.BROKERAGE
    )
    created = await service.add_institution(request)

    request.website_url = "https://zerodha.com"
    updated = await service.update_institution(created.id, request)

    assert updated.website_url == "https://zerodha.com"
