from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, AliasChoices

class OpeningBalanceDTO(BaseModel):
    model_config = {"populate_by_name": True}

    account_id: int
    balance_amount: float = Field(
        ..., ge=0,
        validation_alias=AliasChoices("balance_amount", "amount")
    )
    balance_date: str = Field(
        ...,
        validation_alias=AliasChoices("balance_date", "as_of_date")
    )
    notes: Optional[str] = None

class BulkOpeningBalanceDTO(BaseModel):
    balances: List[OpeningBalanceDTO]

class OpeningBalanceResponse(BaseModel):
    account_id: int
    amount: float

class BulkOpeningBalanceResponse(BaseModel):
    total_processed: int
    successful_entries: List[OpeningBalanceResponse]
    failed_entries: List[Dict[str, Any]]
