"""
Onboarding V2 - Database Models

Profile-first, goal-oriented onboarding models
"""
from datetime import datetime, date, UTC
from typing import Optional, Dict, Any
from enum import Enum
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Date, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.src.db.base import Base


class ProfileType(str, Enum):
    """User profile types"""
    SALARIED_EMPLOYEE = "salaried_employee"
    BUSINESS_OWNER = "business_owner"
    EARLY_INVESTOR = "early_investor"


class OnboardingProfile(Base):
    """User onboarding profile with demographic and financial context"""
    
    __tablename__ = "onboarding_profiles"
    
    # Primary key
    profile_id = Column(String(50), primary_key=True, index=True)
    user_id = Column(String(50), ForeignKey("users.user_id"), nullable=False, unique=True, index=True)
    
    # Basic Information
    name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)
    date_of_birth = Column(Date, nullable=True)
    
    # Profile Type
    profile_type = Column(String(20), nullable=False)  # ProfileType enum
    
    # Location
    city = Column(String(100), nullable=False)
    city_tier = Column(Integer, default=3)  # 1, 2, or 3
    col_index = Column(Float, default=1.0)  # Cost of Living Index
    
    # Life Stage
    marital_status = Column(String(20), nullable=True)  # single, married, divorced
    children_count = Column(Integer, default=0)
    supporting_parents = Column(Boolean, default=False)
    
    # Financial Context
    monthly_income_range = Column(String(20), nullable=True)  # e.g., "1l_2l"
    monthly_income_min = Column(Integer, nullable=True)  # Calculated from range
    monthly_income_max = Column(Integer, nullable=True)
    
    # Onboarding State
    onboarding_completed = Column(Boolean, default=False)
    onboarding_step = Column(Integer, default=1)  # Current step (1-4)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC), nullable=False)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    goals = relationship("FinancialGoal", back_populates="profile", cascade="all, delete-orphan")
    assets = relationship("UserAsset", back_populates="profile", cascade="all, delete-orphan")
    liabilities = relationship("UserLiability", back_populates="profile", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<OnboardingProfile(id={self.profile_id}, user={self.user_id}, type={self.profile_type})>"


class GoalType(str, Enum):
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


class FinancialGoal(Base):
    """User financial goals with calculations"""
    
    __tablename__ = "financial_goals"
    
    # Primary key
    goal_id = Column(String(50), primary_key=True, index=True)
    profile_id = Column(String(50), ForeignKey("onboarding_profiles.profile_id"), nullable=False, index=True)
    user_id = Column(String(50), ForeignKey("users.user_id"), nullable=False, index=True)
    
    # Goal Details
    goal_type = Column(String(30), nullable=False)  # GoalType enum
    goal_name = Column(String(200), nullable=False)
    
    # Target Details
    target_amount = Column(Integer, nullable=False)  # in paise
    target_year = Column(Integer, nullable=True)
    target_age = Column(Integer, nullable=True)
    years_to_goal = Column(Integer, nullable=False)
    
    # Calculation Parameters
    monthly_saving_required = Column(Integer, nullable=False)  # in paise
    current_savings = Column(Integer, default=0)  # in paise
    inflation_rate = Column(Float, default=0.06)
    return_rate = Column(Float, default=0.12)
    
    # Priority & Status
    priority = Column(Integer, default=5)  # 1=highest, 10=lowest
    is_active = Column(Boolean, default=True)
    
    # Goal-specific details stored as JSON
    details = Column(JSON, default={})
    # Examples:
    # - retirement: {"monthly_expense": 50000, "life_expectancy": 85}
    # - education: {"child_age": 5, "education_type": "engineering_india"}
    # - home: {"city": "Bangalore", "property_type": "2bhk", "down_payment_pct": 20}
    
    # Progress Tracking
    amount_saved = Column(Integer, default=0)  # in paise
    last_contribution = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC), nullable=False)
    
    # Relationships
    profile = relationship("OnboardingProfile", back_populates="goals")
    
    def __repr__(self):
        return f"<FinancialGoal(id={self.goal_id}, type={self.goal_type}, target=₹{self.target_amount/100})>"
    
    @property
    def target_amount_rupees(self):
        """Convert paise to rupees for display"""
        return self.target_amount / 100
    
    @property
    def monthly_saving_rupees(self):
        """Convert paise to rupees for display"""
        return self.monthly_saving_required / 100


class AssetType(str, Enum):
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


class UserAsset(Base):
    """User assets captured during onboarding"""
    
    __tablename__ = "user_assets"
    
    # Primary key
    asset_id = Column(String(50), primary_key=True, index=True)
    profile_id = Column(String(50), ForeignKey("onboarding_profiles.profile_id"), nullable=False, index=True)
    user_id = Column(String(50), ForeignKey("users.user_id"), nullable=False, index=True)
    
    # Asset Details
    asset_type = Column(String(20), nullable=False)  # AssetType enum
    asset_name = Column(String(200), nullable=False)
    
    # Institution Details
    institution_name = Column(String(200), nullable=True)
    account_number = Column(String(100), nullable=True)  # Encrypted/masked
    
    # Valuation
    current_value = Column(Integer, nullable=False)  # in paise
    purchase_value = Column(Integer, nullable=True)  # in paise
    valuation_date = Column(Date, default=date.today, nullable=False)
    
    # Additional details as JSON
    details = Column(JSON, default={})
    # Examples:
    # - bank: {"account_type": "savings", "ifsc": "HDFC0001234"}
    # - mf: {"folio_number": "12345", "fund_name": "HDFC Top 100"}
    # - property: {"address": "...", "sqft": 1200}
    
    # Asset Characteristics
    is_liquid = Column(Boolean, default=True)  # Can be easily converted to cash
    is_productive = Column(Boolean, default=False)  # Generates income/returns
    
    # Linked Ledger Account
    ledger_account_id = Column(String(50), nullable=True)  # Link to accounting system
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC), nullable=False)
    
    # Relationships
    profile = relationship("OnboardingProfile", back_populates="assets")
    
    def __repr__(self):
        return f"<UserAsset(id={self.asset_id}, type={self.asset_type}, value=₹{self.current_value/100})>"
    
    @property
    def current_value_rupees(self):
        """Convert paise to rupees for display"""
        return self.current_value / 100


class LiabilityType(str, Enum):
    """Liability types"""
    HOME_LOAN = "home_loan"
    VEHICLE_LOAN = "vehicle_loan"
    EDUCATION_LOAN = "education_loan"
    PERSONAL_LOAN = "personal_loan"
    CREDIT_CARD = "credit_card"
    BUSINESS_LOAN = "business_loan"
    OTHER = "other"


class UserLiability(Base):
    """User liabilities/debts captured during onboarding"""
    
    __tablename__ = "user_liabilities"
    
    # Primary key
    liability_id = Column(String(50), primary_key=True, index=True)
    profile_id = Column(String(50), ForeignKey("onboarding_profiles.profile_id"), nullable=False, index=True)
    user_id = Column(String(50), ForeignKey("users.user_id"), nullable=False, index=True)
    
    # Liability Details
    liability_type = Column(String(20), nullable=False)  # LiabilityType enum
    liability_name = Column(String(200), nullable=False)
    
    # Lender
    lender_name = Column(String(200), nullable=False)
    
    # Loan Details
    original_amount = Column(Integer, nullable=False)  # in paise
    outstanding_principal = Column(Integer, nullable=False)  # in paise
    monthly_emi = Column(Integer, nullable=False)  # in paise
    interest_rate = Column(Float, nullable=False)  # Annual percentage
    
    # Timeline
    loan_start_date = Column(Date, nullable=True)
    loan_end_date = Column(Date, nullable=True)
    years_remaining = Column(Integer, nullable=True)
    
    # Additional details as JSON
    details = Column(JSON, default={})
    # Examples:
    # - home_loan: {"property_value": 6000000, "disbursement_date": "2020-01-01"}
    # - credit_card: {"credit_limit": 200000, "carrying_balance": true}
    
    # Characteristics
    is_high_interest = Column(Boolean, default=False)  # >15% APR
    
    # Linked Ledger Account
    ledger_account_id = Column(String(50), nullable=True)  # Link to accounting system
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC), nullable=False)
    
    # Relationships
    profile = relationship("OnboardingProfile", back_populates="liabilities")
    
    def __repr__(self):
        return f"<UserLiability(id={self.liability_id}, type={self.liability_type}, outstanding=₹{self.outstanding_principal/100})>"
    
    @property
    def outstanding_rupees(self):
        """Convert paise to rupees for display"""
        return self.outstanding_principal / 100
    
    @property
    def monthly_emi_rupees(self):
        """Convert paise to rupees for display"""
        return self.monthly_emi / 100


class CityData(Base):
    """Indian cities with cost of living data"""
    
    __tablename__ = "city_data"
    
    # Primary key
    city_id = Column(String(50), primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    
    # Location
    state = Column(String(100), nullable=False)
    tier = Column(Integer, nullable=False)  # 1, 2, or 3
    
    # Cost of Living
    col_index = Column(Float, default=1.0)  # Relative to base (Mumbai = 2.0)
    avg_rent_1bhk = Column(Integer, nullable=True)  # in rupees
    avg_rent_2bhk = Column(Integer, nullable=True)  # in rupees
    avg_rent_3bhk = Column(Integer, nullable=True)  # in rupees
    
    # Additional data
    population = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC), nullable=False)
    
    def __repr__(self):
        return f"<CityData(name={self.name}, tier={self.tier}, col_index={self.col_index})>"
