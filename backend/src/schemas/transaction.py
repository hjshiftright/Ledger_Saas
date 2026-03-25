from pydantic import BaseModel
from datetime import date
from decimal import Decimal
from typing import List

class TransactionLineDTO(BaseModel):
    account_id: int
    line_type: str
    amount: Decimal

class TransactionCreateDTO(BaseModel):
    date: date
    description: str
    expense_account_id: int
    payment_account_id: int
    amount: Decimal

class TransactionResponseDTO(BaseModel):
    id: int
    transaction_date: date
    description: str

    class Config:
        from_attributes = True
