from typing import Optional
from pydantic import BaseModel, Field
from common.enums import BankAccountType, LoanType

class BaseAccountSetupDTO(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=100)

class InstitutionAccountSetupDTO(BaseAccountSetupDTO):
    institution_id: int

class BankAccountSetupDTO(InstitutionAccountSetupDTO):
    account_number_masked: str = Field(..., min_length=4)
    bank_account_type: BankAccountType
    ifsc_code: Optional[str] = Field(None, pattern=r"^[A-Z]{4}0[A-Z0-9]{6}$")
    branch: Optional[str] = None

class CreditCardSetupDTO(InstitutionAccountSetupDTO):
    last_four_digits: str = Field(..., pattern=r"^\d{4}$")
    credit_limit: float = Field(..., gt=0)
    billing_cycle_day: int = Field(..., ge=1, le=28)
    interest_rate_annual: float = Field(..., ge=0)

class LoanSetupDTO(InstitutionAccountSetupDTO):
    loan_type: LoanType
    principal_amount: float = Field(..., gt=0)
    interest_rate: float = Field(..., ge=0)
    tenure_months: int = Field(..., gt=0)
    emi_amount: float = Field(..., gt=0)
    start_date: str
    linked_asset_account_id: Optional[int] = None

class BrokerageSetupDTO(InstitutionAccountSetupDTO):
    demat_id: Optional[str] = None
    default_cost_basis_method: str = Field(default="FIFO")

class FixedDepositSetupDTO(InstitutionAccountSetupDTO):
    principal_amount: float = Field(..., gt=0)
    interest_rate: float = Field(..., gt=0)
    start_date: str
    maturity_date: str
    compounding_frequency: str = Field(default="QUARTERLY")
    auto_renew: bool = False

class CashWalletSetupDTO(BaseAccountSetupDTO):
    pass


class AccountResponse(BaseModel):
    id: int = Field(..., description="COA Account ID")
    name: str
    account_type: str = Field(..., description="E.g., ASSET, LIABILITY")
    subtype: Optional[str] = Field(None, description="E.g., BANK, CREDIT_CARD")
    institution_id: Optional[int] = None
    detail: Optional[dict] = Field(None, description="Account type-specific details")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 101,
                    "name": "HDFC Savings",
                    "account_type": "ASSET",
                    "subtype": "BANK",
                    "institution_id": 1,
                    "detail": {
                        "account_number_masked": "1234",
                        "bank_account_type": "SAVINGS"
                    }
                }
            ]
        }
    }
