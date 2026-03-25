# Ledger — UX Product Requirements Document (UX PRD)

**Version:** 1.0  
**Date:** March 17, 2026  
**Status:** Draft for Review  

---

## 1. Product UX Vision

> **"The first 10 minutes should make the user feel like they hired a personal CFO."**

The onboarding must achieve three things:
1. **Capture identity** — understand who the user is without making them fill forms
2. **Mirror their reality** — show them their financial life reflected back accurately
3. **Inspire action** — connect their current state to their future goals

---

## 2. Onboarding Architecture

### 2.1 Four-Stage Wizard

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  STAGE 1         STAGE 2              STAGE 3            STAGE 4            │
│  Profile &       Chart of Accounts    Financial          Net Asset          │
│  Persona         & Opening Balances   Goals              Dashboard          │
│                                                                              │
│  ┌─────────┐    ┌──────────────┐     ┌──────────────┐   ┌──────────────┐   │
│  │ Name    │    │ Assets       │     │ Retirement   │   │ Net Worth    │   │
│  │ Age     │    │  ├─ Banks    │     │ Education    │   │ Asset Alloc  │   │
│  │ Details │    │  ├─ Invest   │     │ Holidays     │   │ Goal Status  │   │
│  │         │    │  ├─ Gold     │     │ Purchase     │   │ Cash Flow    │   │
│  │ Persona │    │  └─ Property │     │ Freedom      │   │ Health Score │   │
│  │ Cards   │    │ Liabilities  │     │ Emergency    │   │ AI Insights  │   │
│  │         │    │  ├─ Loans    │     │ Debt Freedom │   │              │   │
│  │ AI Chat │    │  └─ Cards    │     │              │   │              │   │
│  │         │    │ Income       │     │ AI Chat      │   │              │   │
│  │         │    │ Expenses     │     │              │   │              │   │
│  │         │    │ Balances     │     │              │   │              │   │
│  │         │    │ AI Chat      │     │              │   │              │   │
│  └─────────┘    └──────────────┘     └──────────────┘   └──────────────┘   │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Stage Transitions

| Transition | Trigger | Validation | Fallback |
|-----------|---------|-----------|----------|
| Stage 1 → 2 | User confirms profile | Name required, persona selected | Cannot proceed without name + persona |
| Stage 2 → 3 | User confirms accounts | At least 1 asset account | Skip with warning |
| Stage 3 → 4 | User confirms goals | Optional (can skip goals) | Dashboard shows just net worth |
| Stage 4 → Main | "Launch Dashboard" click | Onboarding marked complete | N/A |

---

## 3. Stage 1: Profile & Persona — Detailed Requirements

### 3.1 Profile Form Fields

| Field | Type | Required | Default | Validation |
|-------|------|----------|---------|-----------|
| Display Name | Text input | Yes | — | 1-100 chars |
| Age | Number input | Yes | — | 18-100 |
| Occupation | Dropdown | No | — | Free text or dropdown |
| Annual Income Range | Range selector | No | — | Qualitative bands |
| Family Status | Toggle | No | Individual | Individual / Household |
| Location | Text / dropdown | No | — | City name |

### 3.2 Persona Card Design

Each persona card must contain:
- **Icon** — distinctive, memorable visual (not generic)
- **Title** — 2-4 words (e.g., "The Salaried Professional")
- **One-liner** — single sentence describing lifestyle
- **Financial snapshot** — pre-filled defaults the persona activates
- **Selection state** — highlighted border + checkmark when selected

**Card interactions:**
- Click to select/deselect (multi-select allowed)
- Hover shows expanded description
- Selected card glows with accent color
- Deselected cards have subtle opacity reduction

### 3.3 Expanded Persona List

| # | Persona ID | Display Name | Icon | One-liner | Pre-filled Defaults |
|---|-----------|-------------|------|-----------|-------------------|
| 1 | `salaried` | The Salaried Professional | 💼 Briefcase | "Fixed salary, EMIs, and SIPs — building wealth steadily." | Banks, EPF, PPF, MF, Credit Card, Home Loan |
| 2 | `business` | The Business Owner | 🏪 Storefront | "Revenue, receivables, and reinvestment — scaling your empire." | Multiple banks, Business income, GST, Loans |
| 3 | `household` | The Household Manager | 🏠 Home | "Joint finances, children's future, and family security." | Joint accounts, Education funds, Insurance |
| 4 | `starter` | The Early Starter | 🌱 Seedling | "First paycheck, first decisions — building habits that compound." | 1 bank, 1 SIP, Basic expenses |
| 5 | `investor` | The Active Investor | 📊 Chart | "Stocks, MFs, gold, and FDs — diversified and data-driven." | Brokerage, MF, Gold, FD, Capital gains |
| 6 | `freelancer` | The Freelancer | 💻 Laptop | "Multiple clients, variable income — organized chaos." | Multiple income sources, GST, Business expenses |
| 7 | `retiree` | The Retiree | 🌅 Sunset | "Pension, FDs, and peace of mind — securing the golden years." | Pension, FD, RD, Rental income, Healthcare |

### 3.4 AI Conversation Mode

When user selects "Build my profile with AI":
- Chat interface appears (replaces or overlays the form)
- AI asks 5-7 progressive questions
- After conversation, AI suggests persona + filled profile
- User confirms or modifies before proceeding

**Sample AI conversation flow:**
```
AI: "Hello! I'd love to help set up Ledger for you. 
     Let's start simple — what do you do for work?"

User: "I'm a software engineer at Infosys"

AI: "Great! That tells me a lot. Your salary likely comes 
     with EPF and potentially NPS. Do you also invest in 
     mutual funds or stocks?"

User: "Yes, I have some SIPs in Kuvera and a Zerodha account"

AI: "Perfect. One more — do you have any loans? Home loan, 
     car loan, education loan?"

User: "Just a home loan with HDFC"

AI: "Got it! Based on our chat, I'd suggest the 'Salaried 
     Professional' persona combined with 'Active Investor'. 
     I've pre-filled your accounts with: HDFC Bank, Infosys 
     salary, EPF, Kuvera MFs, Zerodha, and your HDFC Home Loan. 
     
     Does this look right? [✓ Looks good] [✏️ Let me modify]"
```

---

## 4. Stage 2: Chart of Accounts — Detailed Requirements

### 4.1 Category Card System

Accounts are presented as **category cards** organized into 4 sections:

**Section A: Assets (Green accent)**
```
┌─────────────────────────────────────────────────┐
│  💰 WHAT YOU OWN                                 │
│                                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐         │
│  │ 🏦       │ │ 💵       │ │ 📈       │         │
│  │ Bank     │ │ Cash     │ │ Stocks & │         │
│  │ Accounts │ │          │ │ Mutual   │         │
│  │  ✓ HDFC  │ │  ✓ (def) │ │ Funds    │         │
│  │  ✓ SBI   │ │          │ │  ✓ Zerod │         │
│  └──────────┘ └──────────┘ └──────────┘         │
│                                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐         │
│  │ 🔒       │ │ 🥇       │ │ 🚗       │         │
│  │ Fixed    │ │ Gold     │ │ Vehicles │         │
│  │ Deposits │ │          │ │          │         │
│  └──────────┘ └──────────┘ └──────────┘         │
│                                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐         │
│  │ 🏠       │ │ 🛡️      │ │ 📋       │         │
│  │ Real     │ │ EPF/PPF/ │ │ Insurance│         │
│  │ Estate   │ │ NPS      │ │          │         │
│  └──────────┘ └──────────┘ └──────────┘         │
└─────────────────────────────────────────────────┘
```

**Section B: Liabilities (Red accent)**  
Similar card grid for loans, credit cards, payables.

**Section C: Income (Blue accent)**  
Salary, Business income, Interest, Dividends, Rental, Freelance.

**Section D: Expenses (Amber accent)**  
Housing, Utilities, Food, Transport, Healthcare, Education, Entertainment, etc.

### 4.2 Card Expansion & Detail Entry

When a category card is selected (clicked), it expands to show:
1. **Instance list** — specific accounts within the category
2. **Add button** — to add new instances
3. **For each instance:**
   - Account name (editable)
   - Institution (dropdown of Indian banks/brokers)
   - Opening balance (₹ input)
   - Optional details (account number masked, type)

**Example — Bank Accounts card expanded:**
```
┌─────────────────────────────────────────────────────┐
│  🏦 Bank Accounts                          [▲ Less] │
│  ─────────────────────────────────────────────────── │
│                                                       │
│  ┌─────────────────────────────────────────────────┐ │
│  │ HDFC Savings Account                   ₹ 3,25,000│ │
│  │ HDFC Bank · Savings · ****4532                   │ │
│  └─────────────────────────────────────────────────┘ │
│                                                       │
│  ┌─────────────────────────────────────────────────┐ │
│  │ SBI Salary Account                     ₹ 85,000 │ │
│  │ SBI · Salary · ****7891                          │ │
│  └─────────────────────────────────────────────────┘ │
│                                                       │
│  [ + Add another bank account ]                       │
│                                                       │
│  Total Bank Balance: ₹4,10,000                       │
└─────────────────────────────────────────────────────┘
```

### 4.3 Running Totals & Net Worth Preview

A sticky bottom bar shows:
```
┌─────────────────────────────────────────────────────────────┐
│  Total Assets: ₹24,50,000  │  Liabilities: ₹18,00,000     │
│  ═══════════════════════════════════════════════════════     │
│  NET WORTH: ₹6,50,000                              ✓      │
└─────────────────────────────────────────────────────────────┘
```

### 4.4 Smart Defaults per Persona

| Persona | Pre-selected Assets | Pre-selected Liabilities |
|---------|-------------------|------------------------|
| Salaried | Bank(1), Cash, EPF, PPF, MF | Credit Card(1), Home Loan |
| Business | Bank(2), Cash, FD, Property, Receivables | Business Loan, Credit Card |
| Household | Bank(2), Cash, Gold, FD, Insurance | Home Loan, Credit Card(2) |
| Early Starter | Bank(1), Cash | Credit Card(1) |
| Investor | Bank(1), Stocks, MF, Gold, FD, NPS | — |
| Freelancer | Bank(2), Cash | Credit Card(1) |
| Retiree | Bank(1), FD, RD, PPF, Gold | — |

---

## 5. Stage 3: Financial Goals — Detailed Requirements

### 5.1 Goal Card Gallery

Goals are presented as visual cards arranged in a horizontal scrollable carousel or grid:

```
┌────────────────────────────────────────────────────────────────┐
│  🎯 PLAN YOUR FUTURE                                          │
│  Select goals that matter to you. Each one gets a custom plan. │
│                                                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐         │
│  │ 🌅       │ │ 📚       │ │ ✈️       │ │ 🛒       │         │
│  │Retirement│ │Education │ │Holidays  │ │Purchase  │         │
│  │          │ │          │ │          │ │          │         │
│  │ "What's  │ │ "Prepare │ │ "Put     │ │ "Save    │         │
│  │  your    │ │  for the │ │  those   │ │  and     │         │
│  │  number?"│ │  high    │ │  trips   │ │  invest" │         │
│  │          │ │  costs"  │ │  on auto"│ │          │         │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘         │
│                                                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                       │
│  │ 🕊️       │ │ 🛡️       │ │ ⛓️‍💥      │                       │
│  │Freedom   │ │Emergency │ │Debt      │                       │
│  │          │ │Fund      │ │Freedom   │                       │
│  │ "Build   │ │ "Your    │ │ "Break   │                       │
│  │  your    │ │  safety  │ │  free    │                       │
│  │  runway" │ │  net"    │ │  faster" │                       │
│  └──────────┘ └──────────┘ └──────────┘                       │
└────────────────────────────────────────────────────────────────┘
```

### 5.2 Goal Detail Wizards

Each goal type has a dedicated configuration panel with:

**Retirement:**
- Monthly expenses (₹) — slider or input
- Retirement age — slider (40-70)
- Savings duration — slider (till age 80-100)
- Pre-retirement asset allocation — preset selector
- Post-retirement asset allocation — preset selector
- Expected inflation — slider (3-10%)
- Output: Required corpus, monthly SIP, success probability

**Education:**
- Child's current age — input
- Education type — segmented control (Medical 5yr / US Ivy League 4yr / Masters 2yr / Other)
- Country — India / Abroad
- Current cost estimate — auto-filled based on type, editable
- Output: Inflation-adjusted future cost, monthly SIP

**Holidays:**
- Frequency — Every year / Every 2 years / One-time
- Type — India / Abroad
- Budget tier — Luxury / Comfortable / Budget
- Duration — 1 week / 2 weeks / 1 month
- From when — Next year / In 2 years
- Till age — slider (till 75, 80, etc.)
- Output: Annual cost, total commitment, monthly SIP

**Purchase:**
- What — Free text (house down payment, car, wedding, etc.)
- Target cost today — ₹ input
- When — date picker or "In X years" slider
- Output: Inflation-adjusted future cost, monthly SIP

**Freedom:**
- Purpose — Sabbatical / Start a business / Learn something new
- Duration — 6 months / 1 year / 2 years
- Monthly cost during freedom — ₹ input
- When — date picker or "In X years" slider
- Output: Total fund needed, monthly SIP

**Emergency Fund:**
- Monthly expenses — auto-filled from profile, editable
- Months of cover — slider (3-12, default 6)
- Current emergency savings — ₹ input
- Output: Target amount, gap, monthly SIP to fill gap

**Debt Freedom:**
- List of current debts (auto-populated from liabilities)
- For each: outstanding amount, interest rate, current EMI
- Strategy — Highest interest first / Smallest balance first
- Extra monthly payment available — ₹ input
- Output: Payoff timeline, interest saved, debt-free date

### 5.3 Goal Summary Panel

After configuring goals, a summary panel appears:

```
┌──────────────────────────────────────────────────────────────┐
│  📊 YOUR FINANCIAL PLAN SUMMARY                              │
│                                                                │
│  Goal                  Target         Monthly SIP   Status    │
│  ──────────────────────────────────────────────────────────── │
│  🌅 Retirement         ₹4.82 Cr       ₹32,450      On Track │
│  📚 Daughter's MBA     ₹45.6 L        ₹8,200       On Track │
│  ✈️ Europe Trip 2027   ₹3.5 L         ₹7,500       Stretch  │
│  🛡️ Emergency Fund     ₹4.2 L         ₹12,000      Behind   │
│  ──────────────────────────────────────────────────────────── │
│  Total Monthly SIP Commitment:         ₹60,150               │
│  Your Monthly Surplus:                 ₹50,000               │
│  Shortfall:                            ₹10,150  ⚠️           │
│                                                                │
│  💡 AI Suggestion: "Your Europe trip target could be reached  │
│     by switching to a 'Comfortable' budget tier, saving       │
│     ₹8,000/month. Or, consider pushing it to 2028."          │
└──────────────────────────────────────────────────────────────┘
```

---

## 6. Stage 4: Net Asset Dashboard — Detailed Requirements

### 6.1 Dashboard Layout

```
┌──────────────────────────────────────────────────────────────────┐
│  🎉 Welcome to your financial command center, {Name}!           │
│                                                                    │
│  ┌────────────────────────────────┐  ┌────────────────────────┐  │
│  │  NET WORTH                     │  │  ASSET ALLOCATION       │  │
│  │                                │  │                          │  │
│  │  ₹6,50,000                    │  │   [Pie Chart]           │  │
│  │  ▲ Starting point             │  │   Cash: 25%             │  │
│  │                                │  │   Equity: 30%           │  │
│  │  Assets:    ₹24,50,000        │  │   Debt: 35%             │  │
│  │  Liabilities: -₹18,00,000    │  │   Gold: 5%              │  │
│  │                                │  │   Real Estate: 5%       │  │
│  └────────────────────────────────┘  └────────────────────────┘  │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  GOAL FUNDING STATUS                                       │  │
│  │                                                              │  │
│  │  🌅 Retirement    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  2%    │  │
│  │  📚 Education     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  0%    │  │
│  │  🛡️ Emergency     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 35%    │  │
│  │  ✈️ Europe Trip   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  0%    │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌────────────────────────────────┐  ┌────────────────────────┐  │
│  │  MONTHLY CASH FLOW             │  │  FINANCIAL HEALTH       │  │
│  │                                │  │                          │  │
│  │  Income:    ₹1,20,000         │  │  Score: 62/100          │  │
│  │  Expenses:  -₹70,000         │  │  ████████████░░░░░░░░   │  │
│  │  SIPs:      -₹32,450         │  │                          │  │
│  │  ──────────────────           │  │  ✓ Emergency fund: 35%  │  │
│  │  Available:  ₹17,550         │  │  ✓ Savings rate: 42%    │  │
│  │                                │  │  ⚠ Debt ratio: High    │  │
│  └────────────────────────────────┘  └────────────────────────┘  │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  💡 AI INSIGHTS                                            │  │
│  │                                                              │  │
│  │  "Your net worth is ₹6.5L — a solid starting point. Your  │  │
│  │   home loan is your largest liability at ₹18L. With your   │  │
│  │   ₹50K monthly surplus, I recommend prioritizing your       │  │
│  │   emergency fund first (4 months to full), then increasing  │  │
│  │   your retirement SIP. Your savings rate of 42% is          │  │
│  │   excellent — well above the recommended 30%."              │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │               [ 🚀 Launch My Dashboard ]                    │  │
│  │                                                              │  │
│  │   📖 Quick Tour  ·  ⌨️ Shortcuts  ·  📚 Guide             │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### 6.2 Dashboard Data Sources

| Component | Data Source | Computation |
|-----------|-----------|-------------|
| Net Worth | Opening balances from Stage 2 | Sum(assets) - Sum(liabilities) |
| Asset Allocation | Account types from Stage 2 | Grouped by category |
| Goal Funding | Goals from Stage 3 + existing assets | Current vs target |
| Monthly Cash Flow | Profile income/expenses | Income - Expenses - SIPs |
| Financial Health | Composite calculation | Emergency adequacy + savings rate + debt ratio |
| AI Insights | All onboarding data | AI-generated summary |

---

## 7. Cross-Stage AI Assistant Specification

### 7.1 AI Panel Design

The AI assistant appears as either:
- **Right sidebar panel** (desktop) — 300px wide, always visible
- **Bottom sheet** (mobile) — slides up from bottom, dismissible

### 7.2 AI Context per Stage

| Stage | AI Role | Sample Prompts |
|-------|---------|---------------|
| 1 | Profile builder | "Tell me about yourself in 2-3 sentences" |
| 2 | Account advisor | "What banks and investments do you use?" |
| 3 | Goal planner | "What are your top 3 financial priorities?" |
| 4 | Insight generator | "Here's what I noticed about your finances..." |

### 7.3 AI-to-Form Binding

When AI suggests changes:
1. Suggested values appear as **highlighted previews** in the form fields
2. User can accept (click ✓) or reject (click ✗) each suggestion individually
3. Accepted values populate the actual form fields with a subtle animation
4. A "Review AI suggestions" summary shows all pending suggestions at once

---

## 8. Design System Tokens

### 8.1 Color Palette

| Token | Usage | Value |
|-------|-------|-------|
| `--color-primary` | CTA buttons, links, active states | Indigo-600 (#4F46E5) |
| `--color-asset` | Asset cards, positive values | Emerald-500 (#10B981) |
| `--color-liability` | Liability cards, negative values | Rose-500 (#F43F5E) |
| `--color-income` | Income categories | Blue-500 (#3B82F6) |
| `--color-expense` | Expense categories | Amber-500 (#F59E0B) |
| `--color-equity` | System accounts | Slate-400 (#94A3B8) |
| `--color-ai` | AI assistant elements | Violet-500 (#8B5CF6) |

### 8.2 Typography

| Element | Font | Size | Weight |
|---------|------|------|--------|
| Page title | Inter/Outfit | 36-40px | 800 (Extra Bold) |
| Section header | Inter/Outfit | 24px | 700 (Bold) |
| Card title | Inter/Outfit | 18px | 700 |
| Body text | Inter | 14-16px | 400 |
| Label | Inter | 12px | 600 |
| Caption | Inter | 11px | 500 |

### 8.3 Spacing & Layout

| Token | Value | Usage |
|-------|-------|-------|
| `--gap-card` | 16px | Between cards in grid |
| `--gap-section` | 32px | Between major sections |
| `--radius-card` | 16px | Card border radius |
| `--radius-button` | 12px | Button border radius |
| `--max-width` | 1200px | Content max width |

---

*This document defines WHAT the product must deliver. See `ux_detailed_requirements.md` for HOW each screen is built, and for the three distinct UX design approaches the team can choose from.*
