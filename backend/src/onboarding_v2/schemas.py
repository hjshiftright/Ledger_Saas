"""
Onboarding V2 - Pydantic Schemas

Request/Response schemas for API validation
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from enum import Enum


# ===== ENUMS =====

class ProfileTypeSchema(str, Enum):
    """User profile types"""
    SALARIED_EMPLOYEE = "salaried_employee"
    BUSINESS_OWNER = "business_owner"
    EARLY_INVESTOR = "early_investor"


class GoalTypeSchema(str, Enum):
    """Financial goal types"""
    RETIREMENT = "retirement"
    CHILD_EDUCATION = "child_education"
    CHILD_MARRIAGE = "child_marriage"
    DREAM_HOLIDAYS = "dream_holidays"
    HOME_PURCHASE = "home_purchase"
    DREAM_CAR = "dream_car"
    EMERGENCY_FUND = "emergency_fund"
    DEBT_FREEDOM = "debt_freedom"
    CUSTOM = "custom"


class AssetTypeSchema(str, Enum):
    """Asset types"""
    BANK_ACCOUNT = "bank_account"
    EPF = "epf"
    PPF = "ppf"
    MUTUAL_FUND = "mutual_fund"
    STOCKS = "stocks"
    FIXED_DEPOSIT = "fd"
    GOLD = "gold"
    REAL_ESTATE = "real_estate"
    VEHICLE = "vehicle"
    CRYPTO = "crypto"
    OTHER = "other"


class LiabilityTypeSchema(str, Enum):
    """Liability types"""
    HOME_LOAN = "home_loan"
    VEHICLE_LOAN = "vehicle_loan"
    EDUCATION_LOAN = "education_loan"
    PERSONAL_LOAN = "personal_loan"
    CREDIT_CARD = "credit_card"
    BUSINESS_LOAN = "business_loan"
    OTHER = "other"


# ===== PROFILE SCHEMAS =====

class ProfileCreateRequest(BaseModel):
    """Request to create/update profile"""
    name: str = Field(..., min_length=2, max_length=100)
    age: int = Field(..., ge=18, le=80)
    date_of_birth: Optional[date] = None
    profile_type: ProfileTypeSchema
    city: str = Field(..., min_length=1, max_length=100)
    marital_status: Optional[str] = None
    children_count: int = Field(default=0, ge=0, le=10)
    supporting_parents: bool = False
    monthly_income_range: Optional[str] = None


class ProfileResponse(BaseModel):
    """Profile response"""
    profile_id: str
    user_id: str
    profile: Dict[str, Any]
    defaults_applied: Optional[Dict[str, Any]] = None
    onboarding_step: int
    
    class Config:
        from_attributes = True


# ===== GOAL SCHEMAS =====

class GoalCreateRequest(BaseModel):
    """Single goal create request"""
    goal_type: GoalTypeSchema
    target_age: Optional[int] = None
    target_amount: int  # in rupees
    target_year: Optional[int] = None
    years_to_goal: int
    monthly_saving_required: int  # in rupees
    priority: int = Field(default=5, ge=1, le=10)
    details: Dict[str, Any] = Field(default_factory=dict)


class GoalsCreateRequest(BaseModel):
    """Request to save multiple goals"""
    goals: List[GoalCreateRequest]


class GoalResponse(BaseModel):
    """Single goal response"""
    goal_id: str
    goal_type: str
    goal_name: str
    target_amount: int
    monthly_saving_required: int
    priority: int
    years_to_goal: int
    
    class Config:
        from_attributes = True


class GoalsSummaryResponse(BaseModel):
    """Goals summary response"""
    goals_saved: int
    goal_ids: List[str]
    summary: Dict[str, Any]
    onboarding_step: int


class GoalsListResponse(BaseModel):
    """List of goals response"""
    goals: List[GoalResponse]
    total_monthly_required: int


# ===== ASSET SCHEMAS =====

class AssetCreateRequest(BaseModel):
    """Single asset create request"""
    asset_type: AssetTypeSchema
    asset_name: str = Field(..., min_length=1, max_length=200)
    institution_name: Optional[str] = None
    current_value: int  # in rupees
    details: Dict[str, Any] = Field(default_factory=dict)
    is_liquid: bool = True
    is_productive: bool = False


class AssetsCreateRequest(BaseModel):
    """Request to save multiple assets"""
    assets: List[AssetCreateRequest]


class AssetResponse(BaseModel):
    """Single asset response"""
    asset_id: str
    asset_type: str
    asset_name: str
    current_value: int
    
    class Config:
        from_attributes = True


class AssetsResponse(BaseModel):
    """Assets save response"""
    assets_saved: int
    asset_ids: List[str]
    total_asset_value: int
    asset_allocation: Dict[str, Any]
    onboarding_step: int


# ===== LIABILITY SCHEMAS =====

class LiabilityCreateRequest(BaseModel):
    """Single liability create request"""
    liability_type: LiabilityTypeSchema
    liability_name: str = Field(..., min_length=1, max_length=200)
    lender_name: str = Field(..., min_length=1, max_length=200)
    original_amount: int  # in rupees
    outstanding_principal: int  # in rupees
    monthly_emi: int  # in rupees
    interest_rate: float = Field(..., ge=0, le=100)
    years_remaining: Optional[int] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class LiabilitiesCreateRequest(BaseModel):
    """Request to save multiple liabilities"""
    liabilities: List[LiabilityCreateRequest]


class LiabilityResponse(BaseModel):
    """Single liability response"""
    liability_id: str
    liability_type: str
    liability_name: str
    outstanding_principal: int
    monthly_emi: int
    
    class Config:
        from_attributes = True


class LiabilitiesResponse(BaseModel):
    """Liabilities save response"""
    liabilities_saved: int
    liability_ids: List[str]
    total_liability_value: int
    total_monthly_emi: int
    liability_analysis: Dict[str, Any]
    onboarding_step: int


# ===== NET WORTH SCHEMAS =====

class NetWorthResponse(BaseModel):
    """Net worth calculation response"""
    total_assets: int
    total_liabilities: int
    net_worth: int
    net_worth_formatted: str
    asset_breakdown: Dict[str, int]
    liability_breakdown: Dict[str, int]
    ratios: Dict[str, float]
    status: Dict[str, Any]


# ===== COMPLETE ONBOARDING SCHEMAS =====

class OnboardingCompleteRequest(BaseModel):
    """Complete onboarding request"""
    pass  # No body needed, uses authenticated user


class OnboardingCompleteResponse(BaseModel):
    """Onboarding complete response"""
    onboarding_completed: bool
    user_id: str
    profile_id: str
    summary: Dict[str, Any]
    chart_of_accounts: Dict[str, Any]
    next_steps: List[Dict[str, str]]
    dashboard_url: str
    onboarded_at: datetime


# ===== RESUME ONBOARDING SCHEMAS =====

class OnboardingResumeResponse(BaseModel):
    """Resume onboarding response"""
    onboarding_step: int
    completed_steps: List[int]
    profile: Optional[Dict[str, Any]] = None
    goals: List[GoalResponse]
    assets: List[AssetResponse]
    liabilities: List[LiabilityResponse]
    can_resume: bool
    last_updated: datetime


# ===== CITY DATA SCHEMAS =====

class CityDataResponse(BaseModel):
    """Single city data response"""
    name: str
    tier: int
    col_index: float
    avg_rent_1bhk: Optional[int]
    avg_rent_2bhk: Optional[int]
    state: str
    
    class Config:
        from_attributes = True


class CitiesListResponse(BaseModel):
    """List of cities response"""
    cities: List[CityDataResponse]
    total: int


# ===== ERROR SCHEMAS =====

class ErrorDetail(BaseModel):
    """Error detail"""
    field: str
    message: str


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: Dict[str, Any]
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Profile data validation failed",
                    "details": [
                        {"field": "age", "message": "Age must be between 18 and 80"}
                    ],
                    "timestamp": "2024-03-20T10:30:00Z"
                }
            }
        }
