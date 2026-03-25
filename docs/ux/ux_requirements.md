# Ledger — UX Requirements Document

**Version:** 1.0  
**Date:** March 17, 2026  
**Status:** Draft for Review  

> **Scope:** This document defines the UX requirements for the Ledger onboarding experience — a 4-stage wizard that transforms a first-time user into an informed, confident wealth tracker. This work is **separate** from the existing frontend in `/frontend/` and will not modify any existing code.

---

## 1. Design Context

### 1.1 The Problem

Most personal finance tools fall into two camps:
- **Oversimplified budgeting apps** (Mint, YNAB) that lack true accounting rigor
- **Accounting software** (Tally, GnuCash) that overwhelm users with jargon

Ledger sits in between — powered by a real double-entry engine but presenting itself as a friendly wealth manager. The onboarding UX is the moment where this balance is established. If the user feels confused or overwhelmed, they will never return.

### 1.2 Target Users (From PRD)

| Persona | Profile | Key Need | Onboarding Behavior |
|---------|---------|----------|---------------------|
| **Riya** | 29, IT professional, Bangalore | "Am I on track?" | Will accept defaults, wants speed |
| **Suresh** | 45, textile business, Surat | Consolidated family view | Will customize heavily, needs detail |
| **Ananya** | 23, just started working | Hand-holding and education | Needs explanation at every step |

### 1.3 Constraints

- **No modification** to the existing `/frontend/` codebase
- New UX prototypes will live in `/docs/ux/` as self-contained HTML files
- Must work against the existing backend REST APIs
- India-first design (₹, Indian numbering, FY April–March)
- AI assistant integration is a core feature, not an afterthought

---

## 2. User Journey Map

The onboarding journey has **4 stages** mapped to distinct emotional states:

```
Stage 1: IDENTITY          Stage 2: STRUCTURE          Stage 3: AMBITION          Stage 4: CLARITY
"Who am I?"                "What do I own/owe?"        "Where am I going?"        "Where do I stand?"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Profile + Persona          Chart of Accounts           Financial Goals            Net Asset Dashboard
                           (Assets, Liabilities,       (Retirement, Education,    (Balance Sheet,
                            Income, Expenses)           Purchase, Freedom)         Net Worth, Goals)

Emotion: Curious           Emotion: "This knows me"    Emotion: Motivated         Emotion: Empowered
Duration: 2–3 min          Duration: 3–5 min           Duration: 3–5 min          Duration: 1–2 min
```

### User Journey Steps

1. **Welcome & Identity** → User provides name, age, and basic details. Selects a lifestyle persona from visual cards. Optionally uses AI assistant to build profile via conversation.

2. **Chart of Accounts** → Based on persona, a default set of accounts is pre-created. User reviews and customizes assets (banks, investments, gold, property), liabilities (loans, credit cards), income sources, and expense categories. Enters opening balances.

3. **Financial Goals** → User defines life goals from pre-built templates (retirement, education, holidays, purchases, freedom). Each goal has a detailed configuration wizard with smart defaults. AI assistant can help fill in goals conversationally.

4. **Net Asset Dashboard** → Summary dashboard showing complete financial picture: net worth, asset allocation, goal funding status, and actionable insights.

---

## 3. Persona System Requirements

### 3.1 Persona Cards

The system must offer **at least 7 lifestyle personas** that influence default account creation and goal suggestions:

| # | Persona | Icon Concept | Target User | Default Accounts Emphasis |
|---|---------|-------------|-------------|--------------------------|
| 1 | **The Salaried Professional** | Briefcase | IT/corporate employees | Bank accounts, EPF/PPF, mutual funds, credit cards, EMIs |
| 2 | **The Business Owner** | Storefront | Small/medium business owners | Multiple bank accounts, business income, tax accounts, receivables |
| 3 | **The Household Manager** | Home + family | Primary family finance manager | Joint accounts, childcare expenses, education funds, insurance |
| 4 | **The Early Starter** | Seedling/graduation cap | Fresh graduates, first job | Basic bank account, first credit card, starter SIPs |
| 5 | **The Investor** | Chart/trend lines | Active investors, traders | Brokerage accounts, mutual funds, stocks, gold, FDs |
| 6 | **The Freelancer** | Laptop + coffee | Consultants, gig workers | Multiple income sources, GST tracking, business expenses |
| 7 | **The Retiree / Pre-retiree** | Sunset/palm tree | Planning retirement or already retired | Pension, FDs, rental income, healthcare expenses |

**Optional additional personas:**
- **The NRI** — Foreign income, dual-currency tracking, NRE/NRO accounts
- **The Student** — Education loans, part-time income, minimal expenses

### 3.2 Persona Behavior

- Each persona pre-selects a specific set of Chart of Accounts defaults
- Each persona pre-configures relevant goals (e.g., Salaried → Retirement + Emergency Fund)
- Each persona sets estimated income/expense ranges for intelligent defaults
- User can select **multiple personas** (e.g., "Salaried Professional" + "Investor")
- All personas are presented as visual cards with icon, title, 1-line description, and key financial assumptions

### 3.3 AI-Assisted Profile Creation

As an alternative to manual persona selection:
- User can click "Tell me about yourself" to launch AI assistant
- AI asks conversational questions about lifestyle, income, family, financial habits
- AI maps the conversation to one or more personas and pre-fills the profile
- User reviews and confirms the AI-suggested profile before proceeding

---

## 4. Chart of Accounts Requirements

### 4.1 Pre-Creation Based on Persona

The system must pre-create accounts based on selected persona(s). The user sees these as **selectable cards** organized by category.

**Asset Categories (shown as cards):**
| Category | Card Visual | Default for Personas |
|----------|------------|---------------------|
| Bank Accounts | Bank building icon | All personas |
| Cash | Cash/wallet icon | All personas |
| Fixed Deposits | Lock/vault icon | Salaried, Business, Retiree |
| Gold | Gold bar icon | Household, Investor, Retiree |
| Vehicles | Car icon | Salaried, Business, Household |
| Real Estate | House icon | Business, Household, Investor |
| Stock Investments | Chart icon | Investor, Salaried |
| Mutual Funds | Pie chart icon | Salaried, Investor, Early Starter |
| EPF/PPF/NPS | Government shield icon | Salaried |
| Insurance | Umbrella icon | Salaried, Household |

**Liability Categories:**
| Category | Card Visual | Default for Personas |
|----------|------------|---------------------|
| Home Loan | House + ₹ icon | Salaried, Household |
| Vehicle Loan | Car + ₹ icon | Salaried, Business |
| Personal Loan | Handshake icon | All (deselected by default) |
| Education Loan | Book + ₹ icon | Early Starter |
| Credit Cards | Card icon | All personas |
| Business Loan | Building + ₹ icon | Business, Freelancer |

**Income & Expense accounts** follow similar pattern with persona-based defaults.

### 4.2 Account Detail Entry

For each selected account category, the user can:
- Add specific instances (e.g., "HDFC Savings Account", "SBI Home Loan")
- Enter account details (institution, account number masked, type)
- Set opening balances inline
- See running totals for total assets, total liabilities, and net worth

### 4.3 Smart Defaults & Minimal Clicks

- Pre-selected cards are visually distinguished (highlighted border, checkmark)
- User can deselect cards they don't need
- Additional cards can be added with a single click
- Each card expands to show detail entry only when selected
- "Quick setup" option: accept all defaults and just enter balances

### 4.4 AI-Assisted Chart of Accounts

- AI can suggest accounts based on conversation: "I have 2 bank accounts — HDFC and SBI, a home loan, and some mutual funds"
- AI pre-creates the appropriate accounts and asks for confirmation
- AI can help estimate opening balances: "I think I have around 3 lakhs in my HDFC account"

---

## 5. Financial Goals Requirements

### 5.1 Goal Types

The system must support the following goal types as selectable cards:

| Goal | Icon | Key Inputs | Calculation |
|------|------|-----------|-------------|
| **Retirement** | Sunset | Monthly spend, retire age, last-till age, inflation, asset allocation | Future corpus = monthly spend × 12 × years × inflation factor |
| **Education** | Book/graduation cap | Child age, education type (Medical/Ivy League/Masters), country, duration | Inflation-adjusted education costs |
| **Holidays** | Airplane/palm | Frequency, type (India/Abroad), budget tier (Luxury/Comfortable/Budget), duration | Recurring annual cost projection |
| **Purchase** | Shopping bag/house | Target item, current cost, target date | Inflation-adjusted target amount |
| **Freedom** | Bird/wings | Duration (1-2 years), lifestyle cost, purpose (sabbatical/business/learning) | Living cost × duration with buffer |
| **Emergency Fund** | Shield | Months of cover (default: 6), monthly expenses | Monthly expenses × months |
| **Debt Freedom** | Broken chain | Current debts, interest rates, monthly payments | Payoff timeline calculator |

### 5.2 Goal Configuration Wizard

Each goal card, when selected, expands into a detailed configuration panel:

**Example — Retirement Goal:**
```
┌─────────────────────────────────────────────────────┐
│  🌅 RETIREMENT GOAL                                  │
│                                                       │
│  I spend     [₹ 1,00,000  ▾] every month            │
│                                                       │
│  I plan to retire when I'm  [ 60 ] years old         │
│                                                       │
│  My savings should last till I'm  [ 90 ] years old   │
│                                                       │
│  Asset allocation before retiring:                    │
│  ┌──────────────────────────────────────────────┐    │
│  │ Safe │ Conservative │ Regular │ Grow │ All-in │    │
│  └──────────────────────────────────────────────┘    │
│                                                       │
│  Asset allocation in retirement:                      │
│  ┌──────────────────────────────────────────────┐    │
│  │ Safe │ Conservative │ Regular │ Grow │ All-in │    │
│  └──────────────────────────────────────────────┘    │
│                                                       │
│  I expect inflation to be  [ 5 ]%                    │
│                                                       │
│  ───────────────────────────────────────────────────  │
│  Required Corpus:  ₹4.82 Cr                          │
│  Monthly SIP needed:  ₹32,450                        │
│  Probability of success:  78%                        │
└─────────────────────────────────────────────────────┘
```

### 5.3 Asset Allocation Presets

| Preset | Equity % | Debt % | Typical Use |
|--------|---------|--------|-------------|
| Safe | 20% | 80% | Near-term goals, retirees |
| Conservative | 35% | 65% | 3-5 year goals |
| Regular | 50% | 50% | Balanced approach |
| Grow | 70% | 30% | 7+ year goals |
| All-in | 90% | 10% | Very long-term, high risk tolerance |
| Custom | User-defined | User-defined | Advanced users |

### 5.4 AI-Assisted Goal Planning

- AI suggests goals based on persona and profile data
- AI can fill in goal parameters from conversation: "I want to retire at 55 and travel the world"
- AI provides reality checks: "Your current savings rate can support retirement at 60, but retiring at 55 would require increasing your SIP by ₹15,000/month"
- AI explains calculations in plain language

---

## 6. Net Asset Dashboard Requirements

### 6.1 Dashboard Components

The final stage dashboard must include:

1. **Net Worth Summary Card** — Total assets, total liabilities, net worth with color coding
2. **Asset Allocation Pie Chart** — Breakdown by asset type (cash, equity, debt, gold, real estate)
3. **Goal Funding Status** — Progress bars for each goal with on-track/behind/ahead indicators
4. **Monthly Cash Flow Preview** — Income vs. expenses vs. SIP commitments
5. **Financial Health Pulse** — A composite score or RAG indicator
6. **Key Insights** — AI-generated 2-3 actionable suggestions

### 6.2 Interactive Elements

- Clicking on any section drills down to detail view
- Net worth card shows trend indicator (even for Day 1, it shows "starting point")
- Goal progress bars are clickable to show the goal detail
- Dashboard adapts to the accounts and goals actually created during onboarding

---

## 7. AI Assistant Requirements

### 7.1 Presence

The AI assistant must be available at **every stage** of onboarding:
- Stage 1: Build profile through conversation
- Stage 2: Configure accounts through conversation
- Stage 3: Set up goals through conversation
- Stage 4: Explain dashboard and provide insights

### 7.2 Interaction Modes

Two interaction modes for the AI:

1. **Sidebar Panel** — Always-visible sidebar with contextual AI guidance (read-only tips + interactive chat)
2. **Full Conversation Mode** — Dedicated chat interface where user can describe their situation and AI builds the configuration

### 7.3 AI Behavior Rules

- AI must never use accounting jargon ("debit", "credit", "chart of accounts")
- AI must use Indian financial context (₹, lakhs, crores, FY April-March)
- AI must be able to suggest and auto-fill form fields based on conversation
- AI must provide a summary of what it understood before committing changes
- AI must be dismissible — user can always switch to manual mode

---

## 8. Global UX Requirements

### 8.1 Progress Tracking

- Visual progress indicator showing all 4 stages
- User can navigate back to any completed stage
- Data from completed stages is preserved
- Each stage shows estimated time remaining

### 8.2 Responsive Design

- Desktop-first but fully responsive down to 375px mobile
- Cards stack to single column on mobile
- Bottom navigation bar on mobile
- Sticky summary elements on mobile

### 8.3 Accessibility

- All interactive elements keyboard-navigable
- Color is never the only indicator (always paired with icon or text)
- Minimum contrast ratio 4.5:1
- Screen reader compatible with ARIA labels

### 8.4 Animation & Transitions

- Stage transitions: horizontal slide (250ms ease-out)
- Card selection: subtle scale + border change (150ms)
- Number updates: counting animation (300ms)
- Form appearance: fade-in from bottom (200ms)
- Loading states: skeleton screens, not spinners

### 8.5 Data Persistence

- All onboarding state saved locally (localStorage or sessionStorage)
- User can close browser and resume where they left off
- "Reset and start over" option available in settings/gear menu

---

## 9. Non-Functional Requirements

| Requirement | Target |
|------------|--------|
| Total onboarding time (defaults) | ≤ 5 minutes |
| Total onboarding time (full customization) | ≤ 15 minutes |
| Page load time | < 2 seconds |
| Animation frame rate | 60fps |
| Mobile viewport support | 375px – 1440px |
| Browser support | Chrome 90+, Firefox 90+, Safari 15+, Edge 90+ |
| Accessibility | WCAG 2.1 AA |

---

*This document serves as the foundational requirements for all UX design options. See `ux_prd.md` for product-specific requirements and `ux_detailed_requirements.md` for screen-by-screen specifications and the three distinct UX design options.*
