from typing import Optional, List
from pydantic import BaseModel, Field
from common.enums import AccountType, NormalBalance

class AccountNodeResponse(BaseModel):
    id: int
    parent_id: Optional[int]
    code: str
    name: str
    type: AccountType
    subtype: Optional[str] = None
    normal_balance: NormalBalance
    is_placeholder: bool = False
    is_system: bool = False
    is_active: bool = True
    children: List['AccountNodeResponse'] = []

class COATreeResponse(BaseModel):
    items: List[AccountNodeResponse]

class RenameAccountRequest(BaseModel):
    new_name: str = Field(..., min_length=1, max_length=100)

class AddCategoryRequest(BaseModel):
    parent_id: int
    name: str = Field(..., min_length=1, max_length=100)

# Alias to match names in router
COANodeResponse = AccountNodeResponse
COARenameRequest = RenameAccountRequest
COACategoryAddRequest = AddCategoryRequest

class COAStatusResponse(BaseModel):
    """Whether the COA has been initialized yet."""
    ready: bool = Field(..., description="True if COA tree has been created")
