# Onboarding V2 Implementation

Profile-based onboarding with financial goal calculations and net worth tracking.

## 🎯 Overview

The new onboarding system guides users through a 4-screen journey:
1. **Profile & Context**: Personal info, life stage, city
2. **Financial Goals**: Goal selection with auto-calculations  
3. **Finances**: Asset and liability entry
4. **Review & Launch**: Summary with chart of accounts

## 📦 Components Created

### Backend

#### Models (`backend/src/onboarding_v2/models.py`)
- `OnboardingProfile` - User demographics and context
- `FinancialGoal` - Goals with target amounts and monthly SIPs
- `UserAsset` - Bank accounts, investments, property
- `UserLiability` - Loans, credit cards, debts
- `CityData` - Indian cities with COL indexes

#### Service Layer (`backend/src/onboarding_v2/service.py`)
- `OnboardingService` - Orchestrates onboarding workflow
- Auto-applies defaults based on profile type
- Generates chart of accounts template
- Calculates net worth and goal feasibility

#### Calculators (`backend/src/onboarding_v2/calculators.py`)
Financial algorithms:
- `calculate_retirement_corpus()` - 25x rule with 6% inflation
- `calculate_education_corpus()` - SIP with 8% education inflation
- `calculate_home_down_payment()` - Property appreciation + SIP
- `calculate_car_down_payment()` - Car loan down payment
- `calculate_vacation_fund()` - Annual + special trip budgeting
- `calculate_emi()` - Standard EMI formula
- `calculate_goal_feasibility()` - Savings rate analysis

#### API Router (`backend/src/onboarding_v2/router.py`)
10 REST endpoints:
- `POST /api/v1/onboarding/profile` - Create profile
- `POST /api/v1/onboarding/goals` - Create goals with calculations
- `POST /api/v1/onboarding/assets` - Record assets
- `POST /api/v1/onboarding/liabilities` - Record liabilities
- `GET /api/v1/onboarding/net-worth` - Calculate net worth
- `POST /api/v1/onboarding/complete` - Complete onboarding
- `GET /api/v1/onboarding/resume` - Resume incomplete session
- `GET /api/v1/onboarding/cities` - Get supported cities

#### Schemas (`backend/src/onboarding_v2/schemas.py`)
Pydantic models for:
- Request validation (ProfileCreateRequest, GoalsCreateRequest, etc.)
- Response formatting (ProfileResponse, NetWorthResponse, etc.)
- Error handling (ErrorResponse, ErrorDetail)

### Frontend

#### Component (`frontend/src/OnboardingV2.jsx`)
Complete 4-screen React flow:
- Screen 1: Profile type cards, city dropdown, demographics
- Screen 2: Goal cards with auto-calculations, feasibility checks
- Screen 3: Asset/liability forms with real-time net worth
- Screen 4: Review summary with dashboard preview

Features:
- Framer Motion animations
- Lucide React icons
- Tailwind CSS styling
- Real-time calculations
- Form validation

## 🚀 Setup & Installation

### 1. Run Database Migration

```powershell
cd backend

# Create tables and seed city data
python -m src.migrations.onboarding_v2_migration

# To rollback (CAUTION - drops all tables!)
python -m src.migrations.onboarding_v2_migration rollback
```

### 2. Register API Router

Add to your main FastAPI app:

```python
# backend/src/main.py
from src.onboarding_v2 import router as onboarding_v2_router

app = FastAPI()
app.include_router(onboarding_v2_router)
```

### 3. Frontend Integration

The component is already created at `frontend/src/OnboardingV2.jsx`.

To use it in your app:

```javascript
import OnboardingV2 from './OnboardingV2'

function App() {
  return <OnboardingV2 />
}
```

## 📡 API Usage Examples

### Create Profile

```bash
POST /api/v1/onboarding/profile
Content-Type: application/json

{
  "name": "Rajesh Kumar",
  "age": 32,
  "profile_type": "salaried_employee",
  "city": "Bangalore",
  "marital_status": "married",
  "children_count": 1,
  "monthly_income_range": "1l_2l"
}
```

Response:
```json
{
  "profile_id": 1,
  "name": "Rajesh Kumar",
  "age": 32,
  "profile_type": "salaried_employee",
  "city": "Bangalore",
  "city_tier": 1,
  "col_index": 1.5,
  "risk_tolerance": "moderate",
  "investment_experience": "basic",
  "is_complete": false
}
```

### Create Goals with Auto-Calculations

```bash
POST /api/v1/onboarding/goals
Content-Type: application/json

{
  "profile_id": 1,
  "goals": [
    {
      "goal_type": "retirement",
      "details": {
        "monthly_expense": 50000,
        "retirement_age": 60
      }
    },
    {
      "goal_type": "child_education",
      "details": {
        "child_age": 5,
        "current_cost": 2500000
      }
    }
  ]
}
```

Response:
```json
{
  "profile_id": 1,
  "goals": [
    {
      "goal_id": 1,
      "goal_type": "retirement",
      "target_amount": 15000000,
      "monthly_saving_required": 28000,
      "years_to_goal": 28,
      "details": {
        "required_corpus": 15000000,
        "monthly_sip": 28000,
        "future_monthly_expense": 238000,
        "years_to_retirement": 28
      }
    },
    {
      "goal_id": 2,
      "goal_type": "child_education",
      "target_amount": 5400000,
      "monthly_saving_required": 22000,
      "years_to_goal": 13,
      "details": {
        "future_cost": 5400000,
        "monthly_sip": 22000,
        "years_to_save": 13
      }
    }
  ],
  "total_monthly_required": 50000,
  "feasibility": {
    "status": "achievable",
    "feasibility_score": 85,
    "savings_rate_required": 0.33,
    "message": "Saving 33% of income is challenging but achievable with discipline."
  }
}
```

### Get Net Worth

```bash
GET /api/v1/onboarding/net-worth?profile_id=1
```

Response:
```json
{
  "profile_id": 1,
  "total_assets": 1500000,
  "total_liabilities": 800000,
  "net_worth": 700000,
  "total_monthly_emi": 35000,
  "asset_breakdown": {
    "bank_account": {
      "count": 2,
      "total_value": 300000,
      "items": [...]
    },
    "epf": {
      "count": 1,
      "total_value": 500000,
      "items": [...]
    }
  },
  "liability_breakdown": {
    "home_loan": {
      "count": 1,
      "total_outstanding": 800000,
      "total_emi": 35000,
      "items": [...]
    }
  }
}
```

### Complete Onboarding

```bash
POST /api/v1/onboarding/complete?profile_id=1
```

Response:
```json
{
  "profile": {
    "profile_id": 1,
    "name": "Rajesh Kumar",
    "age": 32,
    "profile_type": "salaried_employee",
    "city": "Bangalore"
  },
  "goals_summary": {...},
  "net_worth": {...},
  "chart_of_accounts_template": [
    {
      "code": "1000",
      "name": "Assets",
      "type": "asset",
      "parent": null
    },
    {
      "code": "4100",
      "name": "Salary Income",
      "type": "income",
      "parent": "4000"
    },
    ...
  ],
  "next_steps": [
    "Review and approve proposed transactions",
    "Set up automatic imports from bank accounts",
    "Configure budget categories",
    "Enable smart categorization"
  ]
}
```

## 🧪 Testing

### Manual Testing

1. **Start Backend**:
   ```powershell
   cd backend
   uvicorn src.main:app --reload
   ```

2. **Start Frontend**:
   ```powershell
   cd frontend
   npm run dev
   ```

3. **Navigate to Onboarding**: Open http://localhost:5173 and access the onboarding flow

### API Testing

Use the provided test examples in `docs/api/onboarding-v2-api-spec.md`

## 🏗️ Architecture

```
┌─────────────────┐
│   Frontend      │
│  OnboardingV2   │
└────────┬────────┘
         │ HTTP/REST
         ▼
┌─────────────────┐
│   API Router    │
│  10 endpoints   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Service Layer   │
│ Business logic  │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌───────┐ ┌─────────┐
│Models │ │Calcs    │
│(ORM)  │ │(Math)   │
└───┬───┘ └─────────┘
    │
    ▼
┌─────────────────┐
│   Database      │
│  PostgreSQL     │
└─────────────────┘
```

## 📊 Database Schema

```sql
onboarding_profiles
├── profile_id (PK)
├── user_id (FK → users)
├── name, age, profile_type
├── city, city_tier, col_index
├── marital_status, children_count
└── monthly_income_range

financial_goals
├── goal_id (PK)
├── profile_id (FK → onboarding_profiles)
├── goal_type, target_amount_paise
├── monthly_saving_required_paise
├── years_to_goal, inflation_rate
└── details (JSONB)

user_assets
├── asset_id (PK)
├── profile_id (FK)
├── asset_type, name
├── current_value_paise
├── institution, account_number_last4
└── details (JSONB)

user_liabilities
├── liability_id (PK)
├── profile_id (FK)
├── liability_type, name
├── outstanding_amount_paise
├── monthly_emi_paise, interest_rate
└── details (JSONB)

city_data
├── city_id (PK)
├── city_name, tier
├── col_index
└── avg_1bhk_rent, avg_2bhk_rent
```

## 🔧 Configuration

### Profile Type Defaults

| Profile Type | Risk Tolerance | Investment Experience |
|--------------|----------------|----------------------|
| Salaried Employee | Moderate | Basic |
| Business Owner | High | Intermediate |
| Early Investor | Very High | Advanced |

### Calculation Defaults

| Goal Type | Default Inflation | Default Return |
|-----------|------------------|----------------|
| Retirement | 6% | 12% (pre), 8% (post) |
| Education | 8% | 12% |
| Home | 5% (appreciation) | 8% (savings) |
| Car | N/A | 8% |
| Vacation | N/A | 6% |

## 📝 Next Steps

1. ✅ Database migration - Run migration script
2. ✅ API registration - Add router to main.py
3. ⏳ Authentication - Connect to existing user auth system
4. ⏳ Integration testing - Test end-to-end flow
5. ⏳ UI/UX refinement - Based on user feedback
6. ⏳ Dashboard integration - Link to net worth dashboard

## 🐛 Troubleshooting

### Import Errors

If you see import errors in the router:
```python
# Ensure Base is imported in models.py
from ..db.base import Base
```

### Database Connection

Check database URL in `.env`:
```
DATABASE_URL=postgresql://user:pass@localhost/ledger
```

### Frontend API Connection

Update API base URL in `frontend/src/api.js`:
```javascript
const API_BASE = 'http://localhost:8000'
```

## 📚 Documentation

- [UX Specification](../../docs/ux/onboarding-v2-profile-goals.md)
- [API Specification](../../docs/api/onboarding-v2-api-spec.md)
- [Implementation Roadmap](../../docs/ux/ONBOARDING_V2_IMPLEMENTATION.md)

## 🤝 Contributing

When adding new features:
1. Update models if adding new fields
2. Add calculators for new goal types
3. Update service layer with business logic
4. Add API endpoints in router
5. Update schemas for validation
6. Document in API spec

---

**Status**: ✅ Backend Complete | ✅ Frontend Complete | ⏳ Testing Pending
