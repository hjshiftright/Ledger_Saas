from pydantic import BaseModel, Field
from typing import List, Dict, Any
from ..profile.schemas import ProfileSetupRequest

class AssetItem(BaseModel):
    id: Any
    name: str
    balance: float
    lent_date: str | None = None
    interest_rate: float | None = None

class GoalItem(BaseModel):
    id: Any
    name: str
    target: float
    years: int
    current: float

class DashboardSaveRequest(BaseModel):
    name: str
    age: int
    monthly_income: float
    monthly_expenses: float
    assets: Dict[str, List[AssetItem]]
    liabilities: Dict[str, List[AssetItem]]
    goals: List[GoalItem]

class DashboardDataResponse(BaseModel):
    name: str
    age: int | None
    monthly_income: float | None
    monthly_expenses: float | None
    assets: Dict[str, List[AssetItem]]
    liabilities: Dict[str, List[AssetItem]]
    goals: List[GoalItem]
