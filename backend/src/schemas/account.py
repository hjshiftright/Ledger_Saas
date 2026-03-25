from pydantic import BaseModel
from typing import Optional

class AccountBase(BaseModel):
    code: str
    name: str
    account_type: str
    normal_balance: str

class AccountCreateDTO(AccountBase):
    pass

class AccountResponseDTO(AccountBase):
    id: int

    class Config:
        from_attributes = True
