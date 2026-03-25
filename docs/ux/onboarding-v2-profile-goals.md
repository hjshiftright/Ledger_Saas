# Ledger Onboarding V2 — Profile, Goals, Assets

**Version:** 2.0  
**Date:** March 20, 2026  
**Design Philosophy:** Profile-first, goal-driven onboarding

---

## Design Principles

1. **Start with identity, not accounts** — Understand WHO the user is before asking WHAT they have
2. **Goals before balances** — Connect aspirations to reality upfront
3. **Context-aware defaults** — Location, life stage, and profile shape everything
4. **Progressive disclosure** — Essential path is simple, depth is optional

---

## Flow Overview

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│  Screen 1          Screen 2            Screen 3               │
│  ─────────         ─────────            ─────────              │
│                                                                │
│  Profile &     →   Financial       →    Assets &              │
│  Context           Goals                Liabilities            │
│                                                                │
│  • Profile type    • Retirement         • Bank accounts        │
│  • Location        • Education          • Investments          │
│  • Life stage      • Marriage           • Property             │
│                    • Home purchase      • Loans                │
│                    • Car purchase       • Credit cards         │
│                    • Holidays                                  │
│                                                                │
└────────────────────────────────────────────────────────────────┘
                           ↓
                    Dashboard Ready
```

**Estimated completion time:** 10-15 minutes

---

## Screen 1: Profile & Context

### Purpose
Establish user identity and context that drives all downstream recommendations, expense benchmarks, and financial planning calculations.

### Visual Design

**Layout:**
- Full-screen centered card (max-width: 700px)
- Large, welcoming heading: "Let's get to know you"
- Subtext: "This helps us personalize your financial plan"
- Progress indicator: "Step 1 of 3"
- Clean, spacious form with one question flowing into the next

---

### Section 1.1: Basic Information

**Question: "What should we call you?"**
- Single text input field
- Placeholder: "Your name"
- Auto-focus on load
- Min: 2 chars, Max: 50 chars
- Validation: Required

**Question: "When were you born?"**
- Date picker (dropdown for month, year; number input for day)
- OR: Age input with conversion
- Calculates: Current age, retirement age estimate (60), planning horizon
- Validation: Age between 18-80
- Why we ask: "Your age shapes retirement planning and goal timelines"

---

### Section 1.2: Profile Type ⭐ (Most Important)

**Question: "Which profile best describes you?"**

Displayed as large, visual cards (3 columns on desktop, stack on mobile)

#### Profile Option 1: **Salaried Employee** 💼

**Visual:**
- Icon: Briefcase or office building
- Card color: Blue gradient
- Badge: "Most Popular"

**Description:**
"You earn a regular salary, have standard deductions (EPF, taxes), and want to manage investments and loans."

**Pre-selected defaults when chosen:**
- Income sources: Monthly salary
- Standard deductions: EPF, Professional Tax, Income Tax (TDS)
- Typical accounts: 
  - Bank accounts (1-2)
  - EPF account
  - Credit cards
  - Possible home/car loan
- Expense categories: Rent/EMI, Groceries, Utilities, Transport, Entertainment
- Tax regime: New vs. Old (will ask later)

**Contextual help:** "Perfect for professionals in IT, banking, consulting, government jobs, etc."

---

#### Profile Option 2: **Business Owner** 🏪

**Visual:**
- Icon: Storefront or shop
- Card color: Green gradient
- Badge: "Self-employed"

**Description:**
"You run a business, have variable income, and need to track business expenses, GST, and investments."

**Pre-selected defaults when chosen:**
- Income sources: Business revenue, Multiple income streams
- Standard deductions: GST, Business expenses, Professional fees
- Typical accounts:
  - Multiple bank accounts (personal + business)
  - GST account
  - Accounts receivable/payable
  - Business loans
  - Personal investments
- Expense categories: Business expenses, Inventory, Salary payments, Rent, Utilities
- Tax: Business income tax, GST filings

**Contextual help:** "For entrepreneurs, shop owners, contractors, and self-employed professionals"

---

#### Profile Option 3: **Early Investor** 📈

**Visual:**
- Icon: Growth chart or seed growing
- Card color: Purple gradient
- Badge: "Wealth Builder"

**Description:**
"You're focused on growing wealth through investments. You actively track stocks, mutual funds, and other assets."

**Pre-selected defaults when chosen:**
- Income sources: Salary/Business + Investment income
- Focus: Investment tracking and portfolio management
- Typical accounts:
  - Bank accounts
  - Demat/Trading account
  - Multiple mutual funds
  - Gold/Commodities
  - Real estate
- Expense categories: Minimal (they don't need detailed expense tracking)
- Tax: Capital gains tracking, LTCG/STCG

**Contextual help:** "For those building wealth through markets, real estate, and strategic investing"

---

**Interaction:**
- Single selection (radio behavior)
- Click to select
- Selected card: Elevated shadow, bold border, checkmark icon
- On selection: Brief animation + "Great! I'll set up accounts for [Profile Type]"

**Can change later?** Yes, but will reset Chart of Accounts defaults

---

### Section 1.3: Location Context

**Question: "Which city do you live in?"**

**Why this matters:**
- Cost of living varies dramatically (Mumbai vs. Jaipur)
- Rent/housing costs 3-5x different
- Expense benchmarks adjusted
- Tax implications (HRA for salaried)
- Lifestyle expense suggestions

**UI Component:**
- Searchable dropdown with autocomplete
- Top 50 Indian cities shown first:
  - Tier 1: Mumbai, Delhi, Bangalore, Hyderabad, Chennai, Kolkata, Pune, Ahmedabad
  - Tier 2: Jaipur, Lucknow, Kochi, Indore, Bhopal, Coimbatore, Nagpur, Visakhapatnam
  - Tier 3+: Option to type any city

**Data structure:**
```json
{
  "city": "Bangalore",
  "tier": 1,
  "col_index": 1.8,  // Cost of Living Index (Mumbai = 2.0, small town = 1.0)
  "avg_rent_1bhk": 18000,
  "avg_rent_2bhk": 30000
}
```

**Display on selection:**
"Got it! Expenses in Bangalore are typically higher. I'll adjust benchmarks accordingly."

---

### Section 1.4: Life Stage (Optional but helpful)

**Question: "Tell us about your family situation"**

**Options (checkboxes - multi-select allowed):**
- [ ] Single
- [ ] Married
- [ ] Have children (if yes, ask count: 0-5)
- [ ] Supporting parents
- [ ] Planning to buy a home
- [ ] Have dependents

**Why this matters:**
- Children → Education goals auto-suggested
- Married → Joint accounts, spouse tracking
- Parents → Healthcare, support expenses
- Buying home → Home loan tracking

**Can skip:** Yes, with "Skip for now" link

---

### Section 1.5: Financial Comfort (Optional)

**Question: "What's your approximate monthly take-home income?"**

**UI:** Slider with ranges (reduces friction vs. exact number)

**Ranges:**
- Under ₹25k
- ₹25k - ₹50k
- ₹50k - ₹75k
- ₹75k - ₹1L
- ₹1L - ₹2L
- ₹2L - ₹5L
- ₹5L - ₹10L
- Above ₹10L

**Why ask:**
- Sets realistic goal amounts
- Adjusts expense category suggestions
- Helps with SIP recommendations

**Privacy note:** "This stays private and is only used for personalized recommendations"

**Can skip:** Yes, but impacts goal calculations

---

### Bottom of Screen 1

**Call to Action:**
- Large button: "Continue to Goals →"
- Secondary link: "Save and finish later"

**Data captured at this point:**
```json
{
  "profile": {
    "name": "Rajesh Kumar",
    "age": 32,
    "date_of_birth": "1994-03-15",
    "profile_type": "salaried_employee",
    "city": "Bangalore",
    "city_tier": 1,
    "col_index": 1.8,
    "life_stage": {
      "marital_status": "married",
      "children_count": 1,
      "supporting_parents": true
    },
    "monthly_income_range": "1L-2L"
  }
}
```

---

## Screen 2: Financial Goals

### Purpose
Capture aspirations BEFORE asking about current finances. This creates motivation and context for tracking.

### Visual Design

**Layout:**
- Full-screen centered card
- Heading: "What are you working towards?"
- Subtext: "Select the goals that matter to you. We'll help you plan for them."
- Progress indicator: "Step 2 of 3"

**Grid of goal cards** (2 columns on desktop, 1 on mobile)

---

### Goal Template Structure

Each goal card contains:
- **Icon** - Large, colorful icon representing the goal
- **Goal name** - Clear, aspirational label
- **One-liner** - Brief description
- **Quick facts** - Pre-calculated estimates based on profile
- **Selection state** - Checkbox or toggle
- **Expand option** - Click to see/edit details

---

### Goal 1: 🏝️ Retirement

**Card content:**
- **Icon:** Beach sunset or rocking chair
- **Title:** "Comfortable Retirement"
- **Description:** "Financial freedom at 60"
- **Auto-calculated preview:**
  - Based on current age: 32
  - Retirement age: 60 (28 years away)
  - Required corpus: ₹2.5 Cr (assuming ₹50k/month expenses, inflated)
  - Current savings needed per month: ₹15,000

**Expandable details (if clicked):**
- Retirement age: Adjustable slider (55-70)
- Expected monthly expenses in retirement: Input or slider
- Life expectancy assumption: 85 years
- Inflation assumption: 6%
- Return assumption: 12% (pre-retirement), 8% (post-retirement)
- Calculation shown: 25x annual expenses, inflation-adjusted

**Status indicator:**
- If income data provided: "You need to save ₹15k/month"
- If no income: "We'll calculate this once you add your finances"

---

### Goal 2: 🎓 Children's Education

**Conditional display:** Only shown if user indicated they have children OR are planning for children

**Card content:**
- **Icon:** Graduation cap
- **Title:** "Children's Education"
- **Description:** "College fund for your kids"
- **Auto-calculated preview:**
  - If 1 child, age 5: College in 13 years
  - Estimated cost: ₹25L (undergrad), ₹50L (abroad)
  - Monthly SIP required: ₹12,000

**Expandable details:**
- Number of children: Input (1-5)
- Current age of each child: Input
- Type of education:
  - [ ] Engineering/Medical (India) - ₹15-25L
  - [ ] Undergraduate abroad - ₹50L-1Cr
  - [ ] Private school + coaching - ₹5-8L
  - [ ] Custom amount
- Inflation: 8% (education inflation higher)

---

### Goal 3: 💍 Children's Marriage

**Conditional display:** Only if user has children or plans to

**Card content:**
- **Icon:** Wedding rings or celebration
- **Title:** "Children's Marriage"
- **Description:** "Wedding & starting fund"
- **Auto-calculated preview:**
  - If 1 child, age 5: Marriage in ~23 years
  - Estimated wedding cost: ₹25L (metro city wedding)
  - Monthly SIP required: ₹5,000

**Expandable details:**
- Number of children: Input
- Age at marriage assumption: 26-28
- Wedding budget tiers:
  - Simple: ₹5-10L
  - Traditional: ₹15-25L
  - Grand: ₹30-50L+
  - Custom amount
- Location: Metro vs. Tier 2 (affects cost)

---

### Goal 4: 🏖️ Dream Holidays

**Card content:**
- **Icon:** Airplane or palm tree
- **Title:** "Dream Vacations"
- **Description:** "International trips & experiences"
- **Auto-calculated preview:**
  - Annual vacation budget: ₹2L
  - Special trip in 3 years: ₹5L (e.g., Europe)
  - Monthly saving: ₹8,000

**Expandable details:**
- Frequency: Annual, bi-annual, every 3 years
- Type:
  - Domestic premium (₹50k-1L)
  - International budget (₹1-2L)
  - International premium (₹3-5L)
  - Dream destination (₹5-10L+)
- Special upcoming trip: Yes/No, when, budget
- Recurring annual vacation fund: Yes/No, amount

---

### Goal 5: 🏠 Purchase of Home

**Card content:**
- **Icon:** House
- **Title:** "Buy Your Dream Home"
- **Description:** "First home or upgrade"
- **Auto-calculated preview:**
  - Target: 1BHK in Bangalore (₹60L)
  - Down payment (20%): ₹12L
  - Timeline: 3-5 years
  - Monthly savings needed: ₹25,000

**Expandable details:**
- Already own a home? Yes/No
- If No (First home):
  - City: [Use profile city]
  - Property type: 1BHK/2BHK/3BHK
  - Approximate value: Based on city + type
  - Timeline: 2/3/5/7/10 years
  - Down payment %: 20-30%
- If Yes (Upgrade):
  - Current home value
  - Target home value
  - Timeline
- Loan planning: Yes/No (affects calculation)

**City-specific defaults:**
```
Mumbai: 1BHK = ₹80L, 2BHK = ₹1.5Cr
Bangalore: 1BHK = ₹60L, 2BHK = ₹1Cr
Pune: 1BHK = ₹50L, 2BHK = ₹80L
Tier 2 cities: 1BHK = ₹30L, 2BHK = ₹50L
```

---

### Goal 6: 🚗 Purchase of Dream Car

**Card content:**
- **Icon:** Car or sports car
- **Title:** "Dream Car"
- **Description:** "Upgrade or first car"
- **Auto-calculated preview:**
  - Target: Mid-range sedan (₹15L)
  - Down payment: ₹3L
  - Timeline: 2 years
  - Monthly savings: ₹10,000

**Expandable details:**
- Car segment:
  - Entry hatchback: ₹6-8L
  - Mid-segment sedan: ₹12-18L
  - Premium sedan: ₹25-40L
  - Luxury: ₹50L+
  - Custom amount
- Timeline: 1-5 years
- Buying approach:
  - [ ] Full payment (save entire amount)
  - [ ] Loan (save down payment only - 20-30%)
- Trade-in existing car? Yes/No, value

---

### Additional Goals (Shown as "+ Add More")

User can optionally add:
- 📱 **Tech/Gadgets Fund** - Phones, laptops every 2-3 years
- 🏥 **Health Emergency Fund** - 6 months expenses (auto-calculated)
- 💳 **Debt Freedom** - Pay off all loans by X date
- 🎯 **Financial Independence** - FIRE goals
- 🎨 **Custom Goal** - Name your own goal

---

### Goal Selection Interaction

**Multi-select:**
- Users can select multiple goals
- Each selected goal shows a checkmark
- Unselected goals are slightly dimmed
- No minimum required (can skip all)

**Smart suggestions:**
- Based on age + life stage:
  - Age < 30 & Single → Suggest: Retirement, Home, Car
  - Age 30-40 & Married with kids → Suggest: Education, Retirement, Home
  - Age > 50 → Suggest: Retirement (priority), Healthcare

**Bottom of screen:**
- Summary: "You've selected 4 goals. Total monthly savings needed: ₹48,000"
- If monthly savings > income: Warning "This is ambitious! We'll help prioritize on next screen"
- Button: "Continue to Assets & Liabilities →"
- Link: "Skip goals for now"

---

## Screen 3: Assets & Liabilities

### Purpose
Capture current financial position to calculate Net Worth and goal feasibility.

### Visual Design

**Layout:**
- Split screen (on desktop)
- Left side: Assets (green theme)
- Right side: Liabilities (red theme)
- Heading: "Let's map your current finances"
- Subtext: "This gives you your starting Net Worth"
- Progress: "Step 3 of 3"

---

### Section 3.1: Assets (Left Panel)

**Heading:** "What do you own?" 💰

#### Asset Category 1: 🏦 Bank Accounts

**Interface:** Quick-add buttons + manual entry

**Quick-add bank buttons (based on profile type):**
- If Salaried: HDFC, SBI, ICICI, Axis, Kotak (most popular for salaried)
- If Business: HDFC, ICICI, Axis, Yes Bank (business-friendly)
- "⊕ Add another bank"

**On clicking a bank:**
- Shows input card:
  - Bank name (pre-filled)
  - Account type: Savings / Current / Salary
  - Current balance: ₹_______
  - Account nickname (optional): "Emergency Fund", "Salary Account"
- "Save" adds to list
- Can add multiple accounts from same bank

**Display added accounts:**
```
✓ HDFC Salary Account          ₹1,25,000
✓ SBI Savings                  ₹45,000
✓ ICICI Current (Business)     ₹2,30,000
                              ──────────
  Total in Banks:              ₹4,00,000
```

---

#### Asset Category 2: 💼 Investments

**Shown as expandable sections:**

**2A: Employee Provident Fund (EPF)**
- Only shown if profile = Salaried Employee
- Current EPF balance: ₹_______
- Auto-calculate: If user entered age (e.g., 32) and income, suggest typical EPF balance range

**2B: Public Provident Fund (PPF)**
- Common for salaried + business owners
- Current balance: ₹_______

**2C: Mutual Funds**
- Input options:
  - Quick: Total MF portfolio value: ₹_______
  - Detailed: Add individual funds (Groww, Kuvera, Zerodha Coin)
- Current value: ₹_______

**2D: Stocks / Demat Account**
- Especially for "Early Investor" profile
- Broker: Zerodha / Groww / ICICI Direct / Other
- Current portfolio value: ₹_______

**2E: Fixed Deposits**
- Number of FDs: 1, 2, 3+
- Total FD value: ₹_______

**2F: Gold**
- Physical gold (grams): _______ grams × ₹6,000/gm = ₹_______
- OR: Approximate value: ₹_______
- Digital gold: ₹_______
- Sovereign Gold Bonds: ₹_______

**2G: Real Estate**
- Own a property? Yes/No
- If Yes:
  - Property type: Residential / Commercial
  - Current market value: ₹_______
  - Outstanding loan? → Move to Liabilities
- Can own multiple properties

**2H: Other Assets**
- Vehicle: ₹_______
- Business value: ₹_______ (if Business Owner)
- Rental deposits: ₹_______
- Crypto: ₹_______
- Other: ₹_______

**Asset summary (sticky at bottom):**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Assets: ₹15,75,000
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

### Section 3.2: Liabilities (Right Panel)

**Heading:** "What do you owe?" 💳

#### Liability Category 1: 🏠 Home Loan

**If user selected "Purchase of Home" goal OR owns property:**
- Do you have a home loan? Yes/No
- If Yes:
  - Bank/Lender: _______
  - Original loan amount: ₹_______
  - Outstanding principal: ₹_______
  - Monthly EMI: ₹_______
  - Interest rate: _____% p.a.
  - Years remaining: _____ years
- Can have multiple home loans

---

#### Liability Category 2: 🚗 Vehicle Loan

**If user selected "Dream Car" goal OR in typical salaried profile:**
- Do you have a car/vehicle loan? Yes/No
- If Yes:
  - Vehicle: Car / Two-wheeler
  - Lender: _______
  - Outstanding amount: ₹_______
  - Monthly EMI: ₹_______
  - Years remaining: _____ years

---

#### Liability Category 3: 🎓 Education Loan

**If user age < 35 OR profile = Early Starter:**
- Do you have an education loan? Yes/No
- If Yes:
  - Lender: SBI / HDFC / Other
  - Outstanding amount: ₹_______
  - Monthly EMI: ₹_______

---

#### Liability Category 4: 💰 Personal Loan

- Any personal loans? Yes/No
- If Yes:
  - Lender: _______
  - Outstanding: ₹_______
  - Monthly EMI: ₹_______

---

#### Liability Category 5: 💳 Credit Cards

**Common for all profiles:**
- How many credit cards do you have? 0 / 1 / 2 / 3+
- For each card:
  - Bank: HDFC / SBI / ICICI / Axis / Amex / Other
  - Current outstanding balance: ₹_______
  - Credit limit (optional): ₹_______
  - Do you carry a balance? Yes/No
    - If Yes: This is debt, we'll help you clear it
    - If No: Great! Only transactional use

**Credit card debt warning:**
If outstanding > 0 and carrying balance:
"⚠️ High-interest debt detected. We recommend prioritizing this in your goals."

---

#### Liability Category 6: Other Debts

- Borrowed from family/friends: ₹_______
- Business loans (if Business Owner): ₹_______
- Other: ₹_______

**Liability summary (sticky at bottom):**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Liabilities: ₹35,00,000
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

### Net Worth Calculation (Center, Bottom)

**Large, prominent display:**

```
╔══════════════════════════════════════╗
║                                      ║
║   YOUR NET WORTH                     ║
║                                      ║
║   ₹15,75,000  -  ₹35,00,000         ║
║   (Assets)      (Liabilities)        ║
║                                      ║
║   = - ₹19,25,000                     ║
║   ═══════════════                    ║
║                                      ║
╚══════════════════════════════════════╝
```

**If negative:** 
"Don't worry! Many people start here. Your goals will help you build positive net worth."

**If positive:**
"Great start! Let's grow this with smart planning."

---

### Bottom Actions

**Primary button:** "Review My Plan →"
**Secondary link:** "Go back to edit goals"

**Data captured:**
```json
{
  "assets": {
    "banks": [
      {"name": "HDFC", "type": "salary", "balance": 125000},
      {"name": "SBI", "type": "savings", "balance": 45000}
    ],
    "investments": {
      "epf": 450000,
      "ppf": 200000,
      "mutual_funds": 300000,
      "stocks": 150000,
      "fd": 100000
    },
    "gold": 50000,
    "real_estate": 0,
    "other": 0,
    "total": 1575000
  },
  "liabilities": {
    "home_loan": {"outstanding": 3000000, "emi": 35000},
    "vehicle_loan": {"outstanding": 200000, "emi": 8000},
    "education_loan": 0,
    "personal_loan": 0,
    "credit_cards": [
      {"bank": "HDFC", "outstanding": 25000, "carrying_balance": false}
    ],
    "other": 0,
    "total": 3500000
  },
  "net_worth": -1925000
}
```

---

## Screen 4: Review & Dashboard Preview

### Purpose
Show consolidated view and generate confidence before final submission.

### Layout

**Full-screen dashboard preview**

---

### Section 4.1: Profile Summary (Top Card)

```
┌──────────────────────────────────────────────────┐
│  👤 Rajesh Kumar                                  │
│  32 years old | Salaried Employee | Bangalore    │
│                                                   │
│  Family: Married with 1 child                    │
│  Monthly Income: ₹1-2L range                     │
└──────────────────────────────────────────────────┘
```

---

### Section 4.2: Your Goals (Middle Card)

```
┌──────────────────────────────────────────────────┐
│  🎯 Your Financial Goals                          │
│                                                   │
│  1. 🏝️ Retirement (₹2.5Cr by 2052)               │
│     Status: Need ₹15k/month savings              │
│                                                   │
│  2. 🎓 Child's Education (₹25L by 2037)          │
│     Status: Need ₹12k/month savings              │
│                                                   │
│  3. 🏠 Purchase Home (₹60L down payment by 2029) │
│     Status: Need ₹25k/month savings              │
│                                                   │
│  4. 🚗 Dream Car (₹15L by 2026)                  │
│     Status: Need ₹10k/month savings              │
│                                                   │
│  💡 Total monthly savings needed: ₹62,000        │
│                                                   │
│  ⚠️ Based on income range, this is AMBITIOUS.    │
│      We'll help you prioritize in the dashboard. │
└──────────────────────────────────────────────────┘
```

---

### Section 4.3: Your Net Worth (Bottom Card)

```
┌──────────────────────────────────────────────────┐
│  💰 Your Starting Net Worth                       │
│                                                   │
│  Assets:                          ₹15,75,000     │
│  ├─ Banks                         ₹4,00,000      │
│  ├─ EPF/PPF                       ₹6,50,000      │
│  ├─ Mutual Funds                  ₹3,00,000      │
│  ├─ Stocks                        ₹1,50,000      │
│  └─ Gold                          ₹50,000        │
│                                                   │
│  Liabilities:                     ₹35,00,000     │
│  ├─ Home Loan                     ₹30,00,000     │
│  ├─ Vehicle Loan                  ₹2,00,000      │
│  └─ Credit Card                   ₹25,000        │
│                                                   │
│  ═══════════════════════════════════════════     │
│  Net Worth:            - ₹19,25,000 (NEGATIVE)   │
│                                                   │
│  📊 Asset Allocation:                             │
│  [PIE CHART: EPF 41% | MF 19% | Banks 25%...]   │
└──────────────────────────────────────────────────┘
```

---

### Section 4.4: What Happens Next

**Info panel:**

```
✓ I'll create your double-entry accounting Chart of Accounts based on your profile
✓ I'll set up tracking for all your assets and liabilities  
✓ I'll show goal progress on your dashboard
✓ I'll analyze transactions and suggest categorization
✓ I can import bank statements to auto-track expenses

You can:
• Upload bank statements to track spending
• Record transactions manually
• Adjust goals anytime
• Add/remove accounts as your life changes
```

---

### Bottom Actions

**Large primary button:**
"🚀 Launch My Dashboard"

**Secondary actions:**
- "← Edit my information"
- "Save and finish later"

---

## Backend API Requirements

### Endpoint 1: Create Profile

```
POST /api/v1/onboarding/profile

Request Body:
{
  "name": "Rajesh Kumar",
  "age": 32,
  "date_of_birth": "1994-03-15",
  "profile_type": "salaried_employee | business_owner | early_investor",
  "city": "Bangalore",
  "life_stage": {
    "marital_status": "married | single | other",
    "children_count": 1,
    "supporting_parents": true
  },
  "monthly_income_range": "1L-2L"
}

Response:
{
  "profile_id": "prof_123abc",
  "defaults_applied": {
    "chart_of_accounts_template": "salaried_india_standard",
    "income_accounts": [...],
    "expense_categories": [...],
    "suggested_accounts": [...]
  }
}
```

---

### Endpoint 2: Save Goals

```
POST /api/v1/onboarding/goals

Request Body:
{
  "profile_id": "prof_123abc",
  "goals": [
    {
      "goal_type": "retirement",
      "target_age": 60,
      "target_amount": 25000000,
      "monthly_expense_retirement": 50000,
      "priority": 1
    },
    {
      "goal_type": "child_education",
      "child_age": 5,
      "target_year": 2037,
      "target_amount": 2500000,
      "education_type": "engineering_india",
      "priority": 2
    },
    {
      "goal_type": "home_purchase",
      "target_year": 2029,
      "property_value": 6000000,
      "down_payment_amount": 1200000,
      "loan_required": true,
      "priority": 3
    }
  ]
}

Response:
{
  "goals_saved": 3,
  "monthly_savings_required": 62000,
  "feasibility_status": "ambitious | achievable | conservative",
  "recommendations": [
    "Consider extending home purchase timeline by 1 year",
    "Retirement savings are on track"
  ]
}
```

---

### Endpoint 3: Save Assets & Liabilities

```
POST /api/v1/onboarding/finances

Request Body:
{
  "profile_id": "prof_123abc",
  "assets": {
    "banks": [...],
    "investments": {...},
    "gold": 50000,
    "real_estate": 0,
    "other": 0
  },
  "liabilities": {
    "home_loan": {...},
    "vehicle_loan": {...},
    "credit_cards": [...],
    "other": 0
  }
}

Response:
{
  "net_worth": -1925000,
  "asset_allocation": {
    "epf_ppf": 41.3,
    "mutual_funds": 19.0,
    "banks": 25.4,
    "stocks": 9.5,
    "gold": 3.2
  },
  "debt_to_asset_ratio": 2.22,
  "recommendations": [
    "High debt-to-asset ratio. Focus on debt reduction.",
    "Good diversification in investments.",
    "Consider increasing emergency fund to 6 months expenses."
  ]
}
```

---

### Endpoint 4: Complete Onboarding

```
POST /api/v1/onboarding/complete

Request Body:
{
  "profile_id": "prof_123abc"
}

Response:
{
  "onboarding_complete": true,
  "user_id": "usr_789xyz",
  "accounts_created": 47,
  "chart_of_accounts_template": "salaried_india_standard",
  "dashboard_url": "/dashboard",
  "next_steps": [
    "Upload your first bank statement",
    "Set up recurring transactions",
    "Review goal progress"
  ]
}
```

---

## Mobile Responsiveness

### Screen 1: Profile & Context
- Stack all questions vertically
- Profile cards: Full-width, stack vertically
- City dropdown: Full-screen modal on mobile

### Screen 2: Goals
- Goal cards: Full-width, stack vertically
- Expandable details: Bottom sheet modal
- Summary sticky at bottom

### Screen 3: Assets & Liabilities
- No split: Stack Assets first, then Liabilities
- Each category: Accordion/expandable sections
- Net worth: Sticky bottom card

### Screen 4: Review
- All cards stack vertically
- Charts: Smaller, optimized for mobile viewport

---

## Success Metrics

**Completion Rate:**
- Target: >75% complete all 3 screens
- Measure: Drop-off at each screen

**Time to Complete:**
- Target: 10-15 minutes median
- Measure: Server-side timestamps

**Goal Selection:**
- Track: Most popular goals
- Expected: Retirement > Education > Home

**Data Quality:**
- Measure: How many skip income/asset details
- Target: <20% skip financial details

**User Satisfaction:**
- NPS survey after onboarding
- Target: NPS > 50

---

## Design Assets Required

### Icons
- Profile types: Briefcase, Storefront, Chart
- Goals: Sunset, Graduation, Ring, Plane, House, Car
- Assets/Liabilities: Bank, Investment, Gold, Property, Credit Card

### Illustrations
- Welcome screen hero image
- Empty state: "Add your first asset"
- Success state: Net worth calculated

### Colors
- Primary: Indigo (#4F46E5)
- Success/Assets: Green (#10B981)
- Warning/Liabilities: Red (#EF4444)
- Neutral: Slate (#64748B)

---

## Future Enhancements (V2.1+)

1. **AI-Assisted Profile Building**
   - Chat interface: "Tell me about yourself" → Parse and fill form
   - Voice input for hands-free onboarding

2. **Bank Connect Integration**
   - Auto-fetch balances via Account Aggregator
   - No manual entry needed

3. **Social Proof**
   - "1,234 people in Bangalore with similar profile saved ₹45k on average"
   - Benchmark against similar users

4. **Gamification**
   - Progress badges: "Profile Master", "Goal Setter"
   - Encourage completion

5. **Import from Other Apps**
   - Import from Excel/CSV
   - Connect to existing finance apps

---

**Document End**

Ready for:
- Frontend implementation (React component breakdown)
- Backend API development
- Design mockups in Figma
- User testing & iteration
