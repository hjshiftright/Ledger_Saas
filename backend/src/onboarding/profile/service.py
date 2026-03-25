from typing import Optional, List
from repositories.protocols import ProfileRepository
from common.events import event_bus
from common.exceptions import NotFoundError, ValidationError, DuplicateError
from .schemas import ProfileSetupRequest, ProfileResponse


class ProfileService:
    def __init__(self, profile_repo: ProfileRepository):
        self._profiles = profile_repo

    def setup_profile(self, dto: ProfileSetupRequest, user_id: int, profile_id: Optional[int] = None) -> ProfileResponse:
        if not dto.display_name.strip():
            raise ValidationError("Display name cannot be empty")

        data = {
            "display_name": dto.display_name,
            "base_currency": dto.base_currency.value,
            "financial_year_start_month": dto.financial_year_start_month,
            "tax_regime": dto.tax_regime.value,
            "date_format": dto.date_format,
            "number_format": dto.number_format,
            "age": dto.age,
            "monthly_income": dto.monthly_income,
            "monthly_expenses": dto.monthly_expenses,
            "user_id": user_id,
        }

        if profile_id:
            profile = self._profiles.update(profile_id, data)
            if not profile:
                raise NotFoundError("Profile", str(profile_id))
            event_bus.publish("profile.updated", {"id": profile.id, "display_name": profile.display_name})
        else:
            existing = self._profiles.get_by_name(dto.display_name)
            if existing:
                raise DuplicateError("Profile", dto.display_name)
            profile = self._profiles.create(data)
            event_bus.publish("profile.created", {"id": profile.id, "display_name": profile.display_name})

        return self._to_response(profile)

    def get_profile(self, profile_id: int) -> ProfileResponse:
        profile = self._profiles.get(profile_id)
        if not profile:
            raise NotFoundError("Profile", str(profile_id))
        return self._to_response(profile)

    def list_profiles(
        self,
        limit: int = 10,
        offset: int = 0,
        sort_by: str = "id",
        sort_desc: bool = False,
        filters: dict = None,
    ) -> List[ProfileResponse]:
        profiles = self._profiles.list(limit, offset, sort_by, sort_desc, filters)
        return [self._to_response(p) for p in profiles]

    def count_profiles(self, filters: dict = None) -> int:
        return self._profiles.count(filters)

    def delete_profile(self, profile_id: int) -> None:
        if not self._profiles.delete(profile_id):
            raise NotFoundError("Profile", str(profile_id))
        event_bus.publish("profile.deleted", {"id": profile_id})

    def is_profile_complete(self, profile_id: int) -> bool:
        return self._profiles.get(profile_id) is not None

    def _to_response(self, profile) -> ProfileResponse:
        return ProfileResponse(
            id=profile.id,
            display_name=profile.display_name,
            base_currency=profile.base_currency,
            financial_year_start_month=profile.financial_year_start_month,
            tax_regime=profile.tax_regime,
            date_format=profile.date_format,
            number_format=profile.number_format,
            age=profile.age,
            monthly_income=profile.monthly_income,
            monthly_expenses=profile.monthly_expenses,
        )

