from pydantic import BaseModel, Field
from common.enums import Currency, TaxRegime


class ProfileSetupRequest(BaseModel):
    display_name: str = Field(
        ..., min_length=1, max_length=100,
        description="User's display name"
    )
    base_currency: Currency = Field(
        default=Currency.INR,
        description="Primary currency for all transactions"
    )
    financial_year_start_month: int = Field(
        default=4,
        ge=1, le=12,
        description="Month number when FY starts (4=April for India)"
    )
    tax_regime: TaxRegime = Field(
        default=TaxRegime.NEW,
        description="Indian income tax regime"
    )
    date_format: str = Field(
        default="DD/MM/YYYY",
        pattern=r"^(DD/MM/YYYY|MM/DD/YYYY|YYYY-MM-DD)$"
    )
    number_format: str = Field(
        default="INDIAN",
        pattern=r"^(INDIAN|INTERNATIONAL)$",
        description="INDIAN=12,34,567.89  INTERNATIONAL=1,234,567.89"
    )
    age: int | None = Field(None, ge=1, le=120)
    monthly_income: float | None = Field(None, ge=0)
    monthly_expenses: float | None = Field(None, ge=0)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "display_name": "Jane Doe",
                    "base_currency": "INR",
                    "financial_year_start_month": 4,
                    "tax_regime": "NEW",
                    "date_format": "DD/MM/YYYY",
                    "number_format": "INDIAN",
                }
            ]
        }
    }


class ProfileUpdatePartialRequest(BaseModel):
    display_name: str | None = Field(None, min_length=1, max_length=100)
    base_currency: Currency | None = None
    financial_year_start_month: int | None = Field(None, ge=1, le=12)
    tax_regime: TaxRegime | None = None
    date_format: str | None = Field(None, pattern=r"^(DD/MM/YYYY|MM/DD/YYYY|YYYY-MM-DD)$")
    number_format: str | None = Field(None, pattern=r"^(INDIAN|INTERNATIONAL)$")
    age: int | None = Field(None, ge=1, le=120)
    monthly_income: float | None = Field(None, ge=0)
    monthly_expenses: float | None = Field(None, ge=0)

class ProfileResponse(BaseModel):
    id: int | None = None
    display_name: str
    base_currency: Currency
    financial_year_start_month: int
    tax_regime: TaxRegime
    date_format: str
    number_format: str
    age: int | None = None
    monthly_income: float | None = None
    monthly_expenses: float | None = None


class ProfileStatusResponse(BaseModel):
    """Whether the user profile setup is complete."""
    complete: bool = Field(..., description="True if all profile fields are configured")

