# Onboarding V2 API Specification

**Version:** 2.0  
**Base URL:** `/api/v1/onboarding`  
**Authentication:** Required (bearer token)  
**Date:** March 20, 2026

---

## Overview

This API supports the profile-first, goal-oriented onboarding flow with three main screens:
1. Profile & Context
2. Financial Goals  
3. Assets & Liabilities

---

## Data Models

### ProfileType Enum
```python
class ProfileType(str, Enum):
    SALARIED_EMPLOYEE = "salaried_employee"
    BUSINESS_OWNER = "business_owner"
    EARLY_INVESTOR = "early_investor"
```

### OnboardingProfile Schema
```python
class OnboardingProfile(BaseModel):
    user_id: str
    name: str = Field(..., min_length=2, max_length=100)
    age: int = Field(..., ge=18, le=80)
    date_of_birth: Optional[date] = None
    profile_type: ProfileType
    city: str
    city_tier: int = Field(default=3, ge=1, le=3)
    col_index: float = Field(default=1.0)  # Cost of Living Index
    
    # Life stage
    marital_status: Optional[str] = Field(default=None)  # single, married, divorced
    children_count: int = Field(default=0, ge=0, le=10)
    supporting_parents: bool = Field(default=False)
    
    # Financial context
    monthly_income_range: Optional[str] = None  # e.g., "1l_2l"
    monthly_income_min: Optional[int] = None  # Calculated from range
    monthly_income_max: Optional[int] = None
    
    # Metadata
    created_at: datetime
    updated_at: datetime
    onboarding_completed: bool = False
    onboarding_step: int = 1  # Current step (1-4)
```

### FinancialGoal Schema
```python
class GoalType(str, Enum):
    RETIREMENT = "retirement"
    CHILD_EDUCATION = "child_education"
    CHILD_MARRIAGE = "child_marriage"
    DREAM_HOLIDAYS = "dream_holidays"
    HOME_PURCHASE = "home_purchase"
    DREAM_CAR = "dream_car"
    EMERGENCY_FUND = "emergency_fund"
    DEBT_FREEDOM = "debt_freedom"
    CUSTOM = "custom"

class FinancialGoal(BaseModel):
    goal_id: str  # UUID
    user_id: str
    goal_type: GoalType
    goal_name: str
    
    # Target details
    target_amount: int
    target_year: Optional[int] = None
    target_age: Optional[int] = None
    years_to_goal: int
    
    # Calculation parameters
    monthly_saving_required: int
    current_savings: int = 0
    inflation_rate: float = 0.06
    return_rate: float = 0.12
    
    # Priority
    priority: int = Field(default=5, ge=1, le=10)  # 1=highest
    is_active: bool = True
    
    # Goal-specific details (JSON)
    details: dict = Field(default_factory=dict)
    # Examples:
    # - retirement: {monthly_expense: 50000, life_expectancy: 85}
    # - education: {child_age: 5, education_type: "engineering_india"}
    # - home: {city: "Bangalore", property_type: "2bhk", down_payment_pct: 20}
    
    created_at: datetime
    updated_at: datetime
```

### Asset Schema
```python
class AssetType(str, Enum):
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

class Asset(BaseModel):
    asset_id: str  # UUID
    user_id: str
    asset_type: AssetType
    asset_name: str  # e.g., "HDFC Salary Account"
    
    # Institution details
    institution_name: Optional[str] = None  # e.g., "HDFC Bank"
    account_number: Optional[str] = None
    
    # Valuation
    current_value: int  # in paise (₹100 = 10000 paise)
    purchase_value: Optional[int] = None
    valuation_date: date
    
    # Additional details (JSON)
    details: dict = Field(default_factory=dict)
    # Examples:
    # - bank: {account_type: "savings", ifsc: "HDFC0001234"}
    # - mf: {folio_number: "12345", fund_name: "HDFC Top 100"}
    # - property: {address: "...", sqft: 1200}
    
    is_liquid: bool = True  # Can be easily converted to cash
    is_productive: bool = False  # Generates income/returns
    
    created_at: datetime
    updated_at: datetime
```

### Liability Schema
```python
class LiabilityType(str, Enum):
    HOME_LOAN = "home_loan"
    VEHICLE_LOAN = "vehicle_loan"
    EDUCATION_LOAN = "education_loan"
    PERSONAL_LOAN = "personal_loan"
    CREDIT_CARD = "credit_card"
    BUSINESS_LOAN = "business_loan"
    OTHER = "other"

class Liability(BaseModel):
    liability_id: str  # UUID
    user_id: str
    liability_type: LiabilityType
    liability_name: str  # e.g., "HDFC Home Loan"
    
    # Institution
    lender_name: str  # e.g., "HDFC Bank"
    
    # Loan details
    original_amount: int  # in paise
    outstanding_principal: int
    monthly_emi: int
    interest_rate: float  # Annual percentage
    
    # Timeline
    loan_start_date: Optional[date] = None
    loan_end_date: Optional[date] = None
    years_remaining: Optional[int] = None
    
    # Additional details (JSON)
    details: dict = Field(default_factory=dict)
    # Examples:
    # - home_loan: {property_value: 6000000, disbursement_date: "2020-01-01"}
    # - credit_card: {credit_limit: 200000, carrying_balance: true}
    
    is_high_interest: bool = False  # >15% APR
    
    created_at: datetime
    updated_at: datetime
```

---

## Endpoints

### 1. Create/Update Profile

**Endpoint:** `POST /api/v1/onboarding/profile`

**Description:** Create or update user profile during onboarding

**Request Body:**
```json
{
  "name": "Rajesh Kumar",
  "age": 32,
  "date_of_birth": "1994-03-15",
  "profile_type": "salaried_employee",
  "city": "Bangalore",
  "marital_status": "married",
  "children_count": 1,
  "supporting_parents": true,
  "monthly_income_range": "1l_2l"
}
```

**Response:** `200 OK`
```json
{
  "profile_id": "prof_a1b2c3d4",
  "user_id": "usr_12345",
  "profile": {
    "name": "Rajesh Kumar",
    "age": 32,
    "profile_type": "salaried_employee",
    "city": "Bangalore",
    "city_tier": 1,
    "col_index": 1.8,
    "children_count": 1,
    "monthly_income_min": 100000,
    "monthly_income_max": 200000
  },
  "defaults_applied": {
    "chart_of_accounts_template": "salaried_india_standard",
    "suggested_accounts": [
      {"type": "BANK_ACCOUNT", "name": "Primary Savings"},
      {"type": "EPF", "name": "Employee Provident Fund"},
      {"type": "PPF", "name": "Public Provident Fund"}
    ],
    "expense_categories": [
      "Rent/EMI", "Groceries", "Transport", "Utilities", "Entertainment"
    ]
  },
  "onboarding_step": 1
}
```

**Errors:**
- `400 Bad Request` - Invalid data
- `401 Unauthorized` - Not authenticated
- `422 Unprocessable Entity` - Validation errors

---

### 2. Get Profile

**Endpoint:** `GET /api/v1/onboarding/profile`

**Description:** Retrieve current onboarding profile

**Response:** `200 OK`
```json
{
  "profile_id": "prof_a1b2c3d4",
  "name": "Rajesh Kumar",
  "age": 32,
  "profile_type": "salaried_employee",
  "city": "Bangalore",
  "onboarding_completed": false,
  "onboarding_step": 2
}
```

---

### 3. Save Financial Goals

**Endpoint:** `POST /api/v1/onboarding/goals`

**Description:** Save selected financial goals with calculations

**Request Body:**
```json
{
  "goals": [
    {
      "goal_type": "retirement",
      "target_age": 60,
      "target_amount": 25000000,
      "target_year": 2052,
      "years_to_goal": 28,
      "monthly_saving_required": 15000,
      "priority": 1,
      "details": {
        "monthly_expense_retirement": 50000,
        "life_expectancy": 85,
        "inflation_rate": 0.06,
        "return_rate_pre": 0.12,
        "return_rate_post": 0.08
      }
    },
    {
      "goal_type": "child_education",
      "target_amount": 2500000,
      "target_year": 2037,
      "years_to_goal": 13,
      "monthly_saving_required": 12000,
      "priority": 2,
      "details": {
        "child_age": 5,
        "child_current_age": 5,
        "education_type": "engineering_india",
        "college_age": 18,
        "inflation_rate": 0.08
      }
    },
    {
      "goal_type": "home_purchase",
      "target_amount": 1200000,
      "target_year": 2029,
      "years_to_goal": 5,
      "monthly_saving_required": 25000,
      "priority": 3,
      "details": {
        "property_value": 6000000,
        "down_payment_pct": 20,
        "loan_required": true,
        "city": "Bangalore",
        "property_type": "2bhk"
      }
    }
  ]
}
```

**Response:** `201 Created`
```json
{
  "goals_saved": 3,
  "goal_ids": [
    "goal_abc123",
    "goal_def456",
    "goal_ghi789"
  ],
  "summary": {
    "total_monthly_savings_required": 52000,
    "total_target_amount": 28700000,
    "feasibility": {
      "status": "ambitious",
      "feasibility_score": 65,
      "monthly_income_min": 100000,
      "savings_rate_required": 0.52,
      "message": "You'd need to save 52% of minimum income. Consider prioritizing or extending timelines."
    },
    "recommendations": [
      "Retirement savings are on track",
      "Consider extending home purchase by 1-2 years to reduce monthly burden",
      "Education goal is achievable with current savings rate"
    ]
  },
  "onboarding_step": 2
}
```

**Calculation Logic:**
```python
def calculate_goal_feasibility(goals: List[FinancialGoal], monthly_income_min: int) -> dict:
    """
    Calculate if goals are achievable based on income
    """
    total_monthly_required = sum(g.monthly_saving_required for g in goals)
    savings_rate = total_monthly_required / monthly_income_min if monthly_income_min else 0
    
    if savings_rate > 0.7:
        status = "unrealistic"
        score = 30
    elif savings_rate > 0.5:
        status = "ambitious"
        score = 60
    elif savings_rate > 0.3:
        status = "achievable"
        score = 85
    else:
        status = "conservative"
        score = 95
    
    return {
        "status": status,
        "feasibility_score": score,
        "savings_rate_required": savings_rate,
        "monthly_income_min": monthly_income_min
    }
```

---

### 4. Get Goals

**Endpoint:** `GET /api/v1/onboarding/goals`

**Description:** Retrieve all saved goals for user

**Response:** `200 OK`
```json
{
  "goals": [
    {
      "goal_id": "goal_abc123",
      "goal_type": "retirement",
      "goal_name": "Comfortable Retirement",
      "target_amount": 25000000,
      "monthly_saving_required": 15000,
      "priority": 1
    }
  ],
  "total_monthly_required": 52000
}
```

---

### 5. Save Assets

**Endpoint:** `POST /api/v1/onboarding/assets`

**Description:** Add user assets

**Request Body:**
```json
{
  "assets": [
    {
      "asset_type": "bank_account",
      "asset_name": "HDFC Salary Account",
      "institution_name": "HDFC Bank",
      "current_value": 12500000,
      "details": {
        "account_type": "salary",
        "account_number": "****1234"
      },
      "is_liquid": true
    },
    {
      "asset_type": "epf",
      "asset_name": "Employee Provident Fund",
      "current_value": 45000000,
      "is_liquid": false,
      "is_productive": true
    },
    {
      "asset_type": "mutual_fund",
      "asset_name": "Mutual Fund Portfolio",
      "current_value": 30000000,
      "details": {
        "platform": "Groww"
      },
      "is_liquid": true,
      "is_productive": true
    }
  ]
}
```

**Response:** `201 Created`
```json
{
  "assets_saved": 3,
  "asset_ids": ["ast_123", "ast_456", "ast_789"],
  "total_asset_value": 87500000,
  "asset_allocation": {
    "liquid_assets": 42500000,
    "liquid_percentage": 48.6,
    "productive_assets": 75000000,
    "productive_percentage": 85.7
  },
  "onboarding_step": 3
}
```

---

### 6. Save Liabilities

**Endpoint:** `POST /api/v1/onboarding/liabilities`

**Description:** Add user liabilities

**Request Body:**
```json
{
  "liabilities": [
    {
      "liability_type": "home_loan",
      "liability_name": "HDFC Home Loan",
      "lender_name": "HDFC Bank",
      "original_amount": 350000000,
      "outstanding_principal": 300000000,
      "monthly_emi": 3500000,
      "interest_rate": 8.5,
      "years_remaining": 15,
      "details": {
        "property_value": 600000000,
        "loan_start_date": "2020-01-01"
      }
    },
    {
      "liability_type": "vehicle_loan",
      "liability_name": "Car Loan",
      "lender_name": "ICICI Bank",
      "original_amount": 50000000,
      "outstanding_principal": 20000000,
      "monthly_emi": 800000,
      "interest_rate": 9.0,
      "years_remaining": 2
    },
    {
      "liability_type": "credit_card",
      "liability_name": "HDFC Credit Card",
      "lender_name": "HDFC Bank",
      "outstanding_principal": 2500000,
      "monthly_emi": 0,
      "interest_rate": 42.0,
      "details": {
        "credit_limit": 20000000,
        "carrying_balance": false
      },
      "is_high_interest": true
    }
  ]
}
```

**Response:** `201 Created`
```json
{
  "liabilities_saved": 3,
  "liability_ids": ["lib_123", "lib_456", "lib_789"],
  "total_liability_value": 322500000,
  "total_monthly_emi": 4300000,
  "liability_analysis": {
    "total_liabilities": 322500000,
    "high_interest_debt": 2500000,
    "monthly_emi_burden": 4300000,
    "debt_to_income_ratio": 0.36,
    "recommendations": [
      "High credit card utilization detected",
      "Consider debt consolidation for loans above 12% APR",
      "EMI burden is manageable at 36% of income"
    ]
  },
  "onboarding_step": 3
}
```

---

### 7. Calculate Net Worth

**Endpoint:** `GET /api/v1/onboarding/net-worth`

**Description:** Calculate current net worth from assets and liabilities

**Response:** `200 OK`
```json
{
  "total_assets": 87500000,
  "total_liabilities": 322500000,
  "net_worth": -235000000,
  "net_worth_formatted": "-₹23,50,000",
  "asset_breakdown": {
    "banks": 12500000,
    "epf_ppf": 45000000,
    "mutual_funds": 30000000,
    "stocks": 0,
    "gold": 0,
    "real_estate": 0
  },
  "liability_breakdown": {
    "home_loan": 300000000,
    "vehicle_loan": 20000000,
    "credit_cards": 2500000,
    "other": 0
  },
  "ratios": {
    "debt_to_asset_ratio": 3.69,
    "liquid_asset_ratio": 0.486,
    "savings_rate": 0.40
  },
  "status": {
    "is_positive": false,
    "message": "Your liabilities exceed assets. Focus on debt reduction and increasing savings.",
    "recommendations": [
      "Emergency fund: Build 6 months expenses (₹3L)",
      "High-priority: Reduce high-interest debt",
      "Continue EPF contributions for long-term growth"
    ]
  }
}
```

---

### 8. Complete Onboarding

**Endpoint:** `POST /api/v1/onboarding/complete`

**Description:** Finalize onboarding and create Chart of Accounts

**Response:** `200 OK`
```json
{
  "onboarding_completed": true,
  "user_id": "usr_12345",
  "profile_id": "prof_a1b2c3d4",
  "summary": {
    "net_worth": -235000000,
    "total_goals": 3,
    "monthly_savings_required": 52000,
    "accounts_created": 47
  },
  "chart_of_accounts": {
    "template": "salaried_india_standard",
    "accounts_created": 47,
    "categories": {
      "assets": 25,
      "liabilities": 8,
      "income": 6,
      "expenses": 8
    }
  },
  "next_steps": [
    {
      "action": "upload_statement",
      "title": "Upload your first bank statement",
      "url": "/import/upload"
    },
    {
      "action": "set_recurring",
      "title": "Set up recurring transactions",
      "url": "/transactions/recurring"
    },
    {
      "action": "view_goals",
      "title": "Review goal progress",
      "url": "/goals"
    }
  ],
  "dashboard_url": "/dashboard",
  "onboarded_at": "2024-03-20T10:30:00Z"
}
```

**Side Effects:**
- Creates full Chart of Accounts based on profile type
- Links assets to ledger accounts
- Links liabilities to ledger accounts
- Creates goal tracking records
- Marks user onboarding as complete
- Triggers welcome email

---

### 9. Resume Onboarding

**Endpoint:** `GET /api/v1/onboarding/resume`

**Description:** Get current onboarding state to resume

**Response:** `200 OK`
```json
{
  "onboarding_step": 2,
  "completed_steps": [1],
  "profile": {
    "name": "Rajesh Kumar",
    "age": 32,
    "profile_type": "salaried_employee",
    "city": "Bangalore"
  },
  "goals": [],
  "assets": [],
  "liabilities": [],
  "can_resume": true,
  "last_updated": "2024-03-20T09:15:00Z"
}
```

---

### 10. Get City Data

**Endpoint:** `GET /api/v1/onboarding/cities`

**Description:** Get list of cities with cost of living data

**Query Parameters:**
- `search` (optional): Filter cities by name
- `limit` (optional): Number of results (default: 50)

**Response:** `200 OK`
```json
{
  "cities": [
    {
      "name": "Bangalore",
      "tier": 1,
      "col_index": 1.8,
      "avg_rent_1bhk": 18000,
      "avg_rent_2bhk": 30000,
      "state": "Karnataka"
    },
    {
      "name": "Mumbai",
      "tier": 1,
      "col_index": 2.0,
      "avg_rent_1bhk": 35000,
      "avg_rent_2bhk": 60000,
      "state": "Maharashtra"
    }
  ],
  "total": 50
}
```

---

## Business Logic

### Goal Calculation Algorithms

#### 1. Retirement Corpus Calculation
```python
def calculate_retirement_corpus(
    current_age: int,
    retirement_age: int,
    monthly_expense: int,
    inflation_rate: float = 0.06,
    return_rate_pre: float = 0.12,
    return_rate_post: float = 0.08,
    life_expectancy: int = 85
) -> dict:
    """
    Calculate retirement corpus using 25x rule with inflation
    """
    years_to_retirement = retirement_age - current_age
    years_in_retirement = life_expectancy - retirement_age
    
    # Inflate monthly expenses to retirement
    future_monthly_expense = monthly_expense * ((1 + inflation_rate) ** years_to_retirement)
    annual_expense_at_retirement = future_monthly_expense * 12
    
    # 25x rule: corpus = 25 * annual expenses
    required_corpus = annual_expense_at_retirement * 25
    
    # Calculate monthly SIP needed
    # FV = P × [((1 + r)^n - 1) / r] × (1 + r)
    r = return_rate_pre / 12  # Monthly return
    n = years_to_retirement * 12  # Months
    
    monthly_sip = required_corpus / (((1 + r) ** n - 1) / r * (1 + r))
    
    return {
        "required_corpus": int(required_corpus),
        "monthly_sip": int(monthly_sip),
        "future_monthly_expense": int(future_monthly_expense),
        "years_to_retirement": years_to_retirement,
        "years_in_retirement": years_in_retirement
    }
```

#### 2. Education Goal Calculation
```python
def calculate_education_corpus(
    child_current_age: int,
    college_age: int,
    current_cost: int,
    inflation_rate: float = 0.08,
    return_rate: float = 0.12
) -> dict:
    """
    Calculate education corpus with education inflation
    """
    years_to_college = college_age - child_current_age
    
    # Inflate education cost
    future_cost = current_cost * ((1 + inflation_rate) ** years_to_college)
    
    # Calculate monthly SIP
    r = return_rate / 12
    n = years_to_college * 12
    monthly_sip = future_cost / (((1 + r) ** n - 1) / r * (1 + r))
    
    return {
        "future_cost": int(future_cost),
        "monthly_sip": int(monthly_sip),
        "years_to_save": years_to_college
    }
```

#### 3. Home Purchase Calculation
```python
def calculate_home_down_payment(
    property_value: int,
    down_payment_pct: float,
    years_to_save: int,
    return_rate: float = 0.08,
    price_appreciation: float = 0.05
) -> dict:
    """
    Calculate down payment savings with property appreciation
    """
    # Inflate property value
    future_property_value = property_value * ((1 + price_appreciation) ** years_to_save)
    down_payment_required = future_property_value * down_payment_pct
    
    # Calculate monthly SIP
    r = return_rate / 12
    n = years_to_save * 12
    monthly_sip = down_payment_required / (((1 + r) ** n - 1) / r * (1 + r))
    
    loan_amount = future_property_value - down_payment_required
    monthly_emi = calculate_emi(loan_amount, 0.085, 20)  # 8.5% for 20 years
    
    return {
        "future_property_value": int(future_property_value),
        "down_payment_required": int(down_payment_required),
        "monthly_sip": int(monthly_sip),
        "loan_amount": int(loan_amount),
        "estimated_emi": int(monthly_emi)
    }

def calculate_emi(principal: int, annual_rate: float, years: int) -> int:
    """Calculate EMI for a loan"""
    r = annual_rate / 12
    n = years * 12
    emi = principal * r * ((1 + r) ** n) / (((1 + r) ** n) - 1)
    return int(emi)
```

---

## Error Handling

### Standard Error Response
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Profile data validation failed",
    "details": [
      {
        "field": "age",
        "message": "Age must be between 18 and 80"
      }
    ],
    "timestamp": "2024-03-20T10:30:00Z"
  }
}
```

### Error Codes
- `VALIDATION_ERROR` - Input validation failed
- `PROFILE_NOT_FOUND` - Profile doesn't exist
- `ONBOARDING_INCOMPLETE` - Cannot complete, missing data
- `GOAL_CALCULATION_ERROR` - Goal calculation failed
- `DUPLICATE_ENTRY` - Resource already exists
- `UNAUTHORIZED` - Not authenticated
- `FORBIDDEN` - Not authorized

---

## Rate Limiting

- **General endpoints**: 100 requests/minute
- **Calculation endpoints**: 200 requests/minute
- **Profile updates**: 50 requests/minute

---

## Testing

### Sample Test Cases

```python
def test_create_profile():
    data = {
        "name": "Test User",
        "age": 30,
        "profile_type": "salaried_employee",
        "city": "Bangalore"
    }
    response = client.post("/api/v1/onboarding/profile", json=data)
    assert response.status_code == 200
    assert response.json()["profile"]["city_tier"] == 1

def test_calculate_retirement_goal():
    goal_data = {
        "goals": [{
            "goal_type": "retirement",
            "target_age": 60,
            "monthly_expense_retirement": 50000
        }]
    }
    response = client.post("/api/v1/onboarding/goals", json=goal_data)
    assert response.status_code == 201
    assert "monthly_saving_required" in response.json()["goals"][0]

def test_net_worth_calculation():
    # Add assets
    client.post("/api/v1/onboarding/assets", json={"assets": [...]})
    # Add liabilities
    client.post("/api/v1/onboarding/liabilities", json={"liabilities": [...]})
    # Get net worth
    response = client.get("/api/v1/onboarding/net-worth")
    assert response.status_code == 200
    assert "net_worth" in response.json()
```

---

## Implementation Priority

### Phase 1 (MVP):
1. Profile creation (Endpoint 1, 2)
2. Goal saving (Endpoint 3, 4)
3. Asset/Liability saving (Endpoint 5, 6)
4. Net worth calculation (Endpoint 7)
5. Complete onboarding (Endpoint 8)

### Phase 2 (Enhanced):
6. Resume onboarding (Endpoint 9)
7. City data API (Endpoint 10)
8. Goal calculation refinements
9. Advanced analytics

### Phase 3 (Future):
10. Bank auto-connect
11. AI-powered recommendations
12. Social benchmarking

---

**Document End**

Ready for backend implementation alongside frontend component.
