import pytest
from onboarding.profile.schemas import ProfileSetupRequest
from onboarding.profile.service import ProfileService
from repositories.sqla_profile_repo import SqlAlchemyProfileRepository
from common.enums import Currency, TaxRegime
from common.exceptions import ValidationError, NotFoundError

@pytest.fixture
def profile_service(session):
    return ProfileService(SqlAlchemyProfileRepository(session))

async def test_setup_profile_with_valid_data_stores_all_fields(profile_service):
    request = ProfileSetupRequest(
        display_name="John Doe",
        base_currency=Currency.INR,
        financial_year_start_month=4,
        tax_regime=TaxRegime.NEW,
        date_format="DD/MM/YYYY",
        number_format="INDIAN"
    )

    response = await profile_service.setup_profile(request, user_id=1)

    assert response.display_name == "John Doe"
    assert response.base_currency == "INR"
    assert await profile_service.is_profile_complete(response.id) is True

async def test_get_profile_when_no_profile_raises_not_found(profile_service):
    with pytest.raises(NotFoundError):
        await profile_service.get_profile(9999)

async def test_empty_display_name_rejected(profile_service):
    request = ProfileSetupRequest(
        display_name="   ",
        base_currency=Currency.INR,
        financial_year_start_month=4,
        tax_regime=TaxRegime.NEW,
        date_format="DD/MM/YYYY",
        number_format="INDIAN"
    )
    with pytest.raises(ValidationError):
        await profile_service.setup_profile(request, user_id=1)
