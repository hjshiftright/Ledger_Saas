# Progressive Onboarding Blueprint for a Privacy-First Finance Tracker

## 1. Purpose and Audience

This document is a **product+UX blueprint** for designing and implementing a progressive onboarding experience in a **privacy-first, desktop finance tracker**.
It is written for:

- **Product owners** — to align on flows, scope, and prioritisation.
- **UX designers** — to translate into wireframes, micro-copy, and interaction patterns.
- **Engineers** — to implement wizard logic, navigation, state management, and data models.

The onboarding covers seven stages:

1. Basic Profiling
2. Financial Mapping (assets and liabilities)
3. Goal Setting
4. Initial Value (first real dashboard)
5. Cash Flow Discovery
6. Budgeting
7. Split Expenses Tracking

The experience combines a wizard/Netflix-style selector for structure, natural-language inputs for flexibility, and a calm, advisor-like tone with clear "why we ask" explanations to build trust.

---

## 2. Global Design Principles

### 2.1 Progressive, Multi-Session Onboarding

Never require users to complete all seven stages in one sitting. Break onboarding into **micro-flows** (2–4 minutes each) that can be completed in any order after the initial basics. Use the dashboard as the hub: show which parts are done and which are available (e.g., "Cash Flow: not set up yet — takes 2 minutes").

### 2.2 Advisor-Like, Plain-English Tone

Pretend the app is a calm financial advisor sitting next to the user. Use simple headers: "What you own" instead of "Assets — Balance Sheet"; "What you owe (loans and dues)" instead of "Liabilities"; "Where your money usually goes" instead of "Expense allocation." Avoid slang, jokes, and emojis; keep it professional but friendly.

### 2.3 Natural-Language Forms, Not Chatbots

Each step uses **one focused question + free-text area + structured summary** — not a back-and-forth chat. Users should always see exactly how their text was interpreted and be able to edit it.

### 2.4 Explain "Why We Ask" and "What You Get"

For every sensitive field or mini-flow, add a "Why we ask" or "What you get from this" line. Example: "We use this to estimate your starting net worth and show how close you are to your goals." This approach has been shown to reduce drop-off in fintech onboarding flows.

### 2.5 Visible Payoff After Each Step

Every stage should **change something visible on screen**: net worth number updates after financial mapping; a goals progress ring appears after goal setting; a budget donut appears after budgeting. This is the "gamification" — framed as professional, useful feedback rather than badges or points.

### 2.6 Privacy-First, Desktop-Only

All parsing and logic must run locally. Make this explicit throughout: "Processed on this device. We never upload your data." Offer local backup/export but no automatic cloud sync.

### 2.7 Graceful Incompleteness

At no point should the dashboard look empty or broken. Any section not yet set up should display a gentle, greyed-out placeholder with a short call-to-action and estimated time to complete, not a blank void.

---

## 3. Personas and Journey Overview

### 3.1 Personas

**Persona 1 — Salaried Professional.** Single or with family. Receives a regular salary, has EMIs, and some investments. Wants clarity on net worth, savings rate, and goals like buying a house or retiring early. Typical pain point: "I earn well but don't know where it all goes."

**Persona 2 — Business Owner / Self-Employed.** Mixes personal and business accounts. Income is irregular. Wants clarity on cash runway, debt, and separation of personal versus business finances. Typical pain point: "My business account and personal account are tangled together."

**Persona 3 — Homemaker / Household CFO.** Manages household spending, bills, school fees, and shared expenses. May or may not have a personal income stream. Wants visibility on monthly spending, safety buffers, and shared expense fairness. Typical pain point: "I handle all the bills but have no picture of where we stand."

**Persona 4 — Investor / Advanced User.** Has multiple investment accounts and instruments across asset classes. Wants allocation view, net worth tracking, and goal-linked investment monitoring. Typical pain point: "I track stocks in one app, mutual funds in another, and property on a spreadsheet."

### 3.2 High-Level Stage Order

**First session (minimum path — 3 to 5 minutes):**

1. Basic Profiling (mandatory, ~1 minute).
2. One of the following: Financial Mapping (light touch) OR Goal Setting (1–2 goals).
3. Initial Value dashboard (partial but real, with sample/placeholder data for incomplete sections).

**Subsequent sessions (user-driven):**

- Deeper Financial Mapping (add remaining asset classes, refine values).
- Cash Flow Discovery.
- Budgeting.
- Split Expenses Tracking.
- Additional goals or goal refinement.

### 3.3 Persona-Specific Recommended Paths

**Salaried Professional:** Basic Profiling → Financial Mapping (bank accounts + loans first) → Goal Setting (emergency fund, house) → Cash Flow → Budgeting.

**Business Owner:** Basic Profiling → Financial Mapping (separate personal vs business accounts) → Cash Flow (mark irregular income) → Goal Setting (cash runway, debt payoff) → Budgeting.

**Homemaker / Household CFO:** Basic Profiling → Goal Setting (emergency fund, education) → Cash Flow (household spending focus) → Budgeting → Split Expenses.

**Investor:** Basic Profiling → Financial Mapping (deep — all investment classes) → Goal Setting (retirement, wealth target) → Cash Flow → Budgeting.

These are suggestions surfaced by the app, not hard constraints. The user may deviate at any time.

---

## 4. Global Entry Flow

### 4.1 Welcome Screen

**Goal:** Set expectations; establish privacy and control.

**Elements:**

- Title: "Welcome to your financial cockpit."
- Two to three bullet promises: "Your data stays on this device." / "Set up in short steps, at your own pace." / "See useful insights in a few minutes."
- Primary button: "Get started."
- Secondary link: "Learn more about our privacy approach" (opens a short local help page).

**Design notes:** Keep the screen minimal and warm. No stock photos. Use a simple illustration or icon set showing a calm, organised workspace. The tone should make the user feel they are in control, not being sold to.

### 4.2 Time & Persona Triage Screen

**Goal:** Understand who they are and how much time they have today.

**Elements:**

- Question 1: "Which best describes you?" Presented as selectable chips: Salaried professional / Business owner / Homemaker / Investor / Student or other.
- Question 2: "How much time do you have right now?" Options: "Just browsing (2–3 minutes)" / "I can give around 10 minutes."
- Button: "Continue."

**Behaviour:**

- Always proceed to Basic Profiling.
- Store time preference to control pacing: "Just browsing" means the app will complete Basic Profiling then jump to a sample dashboard quickly, teasing the user to return for deeper steps. "10 minutes" means the app will suggest continuing into Financial Mapping and one goal after profiling.
- Persona selection sets the default category order and example text throughout all subsequent screens.

---

## 5. Stage 1 — Basic Profiling

### 5.1 Screen BP-1: About You

**Fields:** Preferred name; country; primary currency; persona chips (pre-filled if selected on the triage screen, editable).

**Copy:**

- Header: "First, a bit about you."
- Subcopy: "This helps us show examples and suggestions that match your life."
- Privacy line: "Stored only on this device. You can change it later in settings."

**Completion effect:** Enables persona-tailored sample dashboard templates and example text throughout all subsequent flows.

### 5.2 Screen BP-2: Household Snapshot

**Fields:** Household type — Single / Couple / Family / Other. Dependents — number plus approximate ages (e.g., "2 kids — 7 and 13"). Optional: partner's name or alias (for split expense tracking later).

**Copy:**

- Header: "Who do you manage money for?"
- Why we ask: "Knowing your household helps us suggest realistic goals like education, emergency buffers, and shared expenses."

**Completion effect:** Allows more relevant goal templates (e.g., children's education appears if dependents exist; split expenses is highlighted if couple or family). The system stores a "household profile" record used by Goals, Budgeting, and Split Expenses stages.

### 5.3 Screen BP-3: Quick Preferences (optional, shown only for "10 minutes" path)

**Fields:** Financial year start month (defaults based on country). Preferred number format (lakhs/crores vs thousands/millions). Whether they use any other finance tool today (dropdown: spreadsheet, another app, pen-and-paper, nothing).

**Copy:**

- Header: "A couple of preferences to make things feel right."
- Why we ask: "Small things like number format and financial year matter for reports."

**Completion effect:** Configures display formats globally. If the user mentions a current tool, offer an import hint later ("We noticed you use spreadsheets — you can paste values when adding accounts").

---

## 6. Stage 2 — Financial Mapping

### 6.1 Financial Mapping Hub Screen (FM-Hub)

**Goal:** Let the user choose how to describe their finances — natural language or structured selection.

**Elements:**

- Header: "Let's map what you have and what you owe."
- Subcopy: "You can describe it in your own words or pick from a list. Everything stays on this device."
- Persistent metrics bar (top or right sidebar, stays visible throughout all Financial Mapping screens):
  - "Assets captured so far: ₹0"
  - "Liabilities captured so far: ₹0"
  - "Estimated net worth: ₹0"
- Two entry buttons: "Type it in your own words" (opens NL mode) / "Pick from categories" (opens Gallery mode).
- Both modes write into the same internal data model (Asset, Liability, Institution, Amount, Owner, ApproximateFlag). The user can switch modes at any time via tabs at the top of the financial mapping section.

### 6.2 Mode A — Natural-Language Description (FM-NL)

#### Screen FM-NL-1: Free-Text Input

**Elements:**

- Header: "In your own words, what do you own and what do you owe?"
- Helper text: "Mention bank accounts, cards, loans, investments, property, gold — whatever matters."
- Placeholder example (persona-aware):
  - Salaried: "Example: Salary 1.5L/month in HDFC, 3L in SBI savings, ICICI credit card with 40K due, 15L home loan from HDFC, SIPs of 10k in mutual funds."
  - Business owner: "Example: Current account in Kotak with about 8L, personal savings 2L in SBI, business loan 20L from HDFC, one LIC policy, a commercial shop worth ~50L."
  - Homemaker: "Example: Joint savings in SBI around 5L, husband's salary account in HDFC, gold jewellery roughly 10L, car loan 3L remaining."
  - Investor: "Example: 25L in direct equity across Zerodha and Groww, 10L in mutual funds, 5L in PPF, 2L in NPS, 50L flat with 20L home loan."
- Multi-line textbox (large, at least five lines visible).
- Button: "Show my summary."
- Secondary link: "Skip for now (I'll add later)."

**Parsing behaviour (implementation notes for engineers):**

On button click, parse text locally using tokenisation, regex for amounts and institution names, dictionaries for bank names and product keywords (FD, PPF, SIP, MF, EMI, home loan, etc.), and simple classifiers for asset vs. liability vs. investment vs. property. Flag any parsed item with low confidence for user review. If parsing finds nothing useful, show a friendly message: "We couldn't pick up specific details. Want to try the category picker instead?"

#### Screen FM-NL-2: Structured Summary

**Elements:**

- Header: "Here's what we understood."
- Two panels side by side (or stacked on smaller screens):
  - **Assets panel** — each inferred asset as an editable row: Type (e.g., savings account, property, mutual funds) / Institution / Amount (marked "approximate" if inferred) / Owner (self, spouse, joint) / Actions: Edit, Delete.
  - **Liabilities panel** — each inferred loan or card similarly displayed.
- Metrics bar updates live: "Assets captured: ₹X (approx)" / "Liabilities captured: ₹Y (approx)" / "Estimated net worth: ₹Z."
- Button: "Looks good, continue."
- Secondary: "Add more" (scrolls to a new input box) / "I'll refine these later."

**Copy:** "You can correct anything that looks off. Rough numbers are perfectly okay — you can refine them anytime."

**Completion effect:** Internal asset and liability lists are created or updated. Metrics bar reflects current totals. The dashboard's Net Worth card will now show a real number.

### 6.3 Mode B — Netflix-Style Gallery (FM-Gallery)

#### Screen FM-G-1: Category Selection

**Elements:**

- Header: "What all do you own and owe today?"
- Subheader: "Pick the categories that apply to you. We'll only ask details for those."
- Two tile sections (multi-select, each tile is a large card with an icon and short description):

  **"Things you own (assets)":**
  - Bank accounts & cash — savings, salary, current, fixed deposits, cash at home.
  - Investments — mutual funds, stocks, bonds, EPF/PPF, NPS.
  - Property — house, land, commercial space.
  - Vehicles — car, two-wheeler, other.
  - Gold & jewellery.
  - Other valuables — art, collectibles, business inventory, receivables.

  **"What you owe (loans and dues)":**
  - Home loan.
  - Vehicle loan.
  - Personal loan.
  - Credit cards (outstanding balances).
  - Education loan.
  - Business loan.
  - Informal loans (from family, friends).
  - Other dues.

- Side panel (live-updating): "Categories selected: X" / Placeholder: "Assets total: –" / "Liabilities total: –."
- Button: "Continue."
- Link: "I'm not sure — let me describe it in words instead" (switches to NL mode).

#### Screen FM-G-2: Checklist & Micro-Wizards

After category selection, show a checklist of items to fill:

- Header: "Let's add a few details for each."
- Checklist items generated dynamically from selected tiles, e.g.: "☐ Add your bank and cash accounts" / "☐ Add your investments" / "☐ Add your loans and credit cards" / "☐ Add property and gold (optional)."
- Each item is clickable and opens a focused micro-wizard. Status updates on completion: "✓ Bank accounts — 3 accounts added."

**Example micro-wizard: "Add bank accounts"**

- Fields: Institution (dropdown with search, or type to add) / Account type (salary, savings, current, FD, cash) / Approximate balance / Owner (self, spouse, joint).
- Why we ask: "We use this to compute your starting net worth and see where your money sits."
- "Add another" button to add multiple accounts without leaving the screen.
- After saving: metrics bar updates, checklist item shows "Completed (N accounts added)."

**Example micro-wizard: "Add investments"**

- Sub-categories shown as tabs or accordion: Mutual Funds / Stocks / EPF-PPF-NPS / Fixed Deposits / Other.
- For each: approximate current value, institution/platform, owner.
- Why we ask: "Investment values help us track your net worth growth over time and show how your assets are distributed."

**Example micro-wizard: "Add property"**

- Fields: Property type (residential, commercial, land) / Approximate current market value / Any linked loan? (yes/no — if yes, link to a liability entry) / Owner.
- Why we ask: "Property is often the largest part of net worth. Including it gives you an accurate picture."

**Example micro-wizard: "Add loans and credit cards"**

- Fields: Loan type (auto-filled from category) / Lender / Original amount / Outstanding balance / EMI amount (optional) / Interest rate (optional).
- Why we ask: "Knowing what you owe — and how much it costs — helps us calculate true net worth and suggest pay-off strategies."

**Completion effect:** When at least one asset OR one liability is added, the user can proceed to Goals or the Initial Value dashboard. The metrics bar is now showing real totals.

### 6.4 Financial Mapping — Persona-Specific Behaviour

**Salaried Professional:** Default order is bank accounts → investments → loans → property. SIP and EPF prompts are highlighted. EMI-to-income ratio shown as a health indicator.

**Business Owner:** A toggle appears: "Is this a personal or business account?" for each entry. A separate "business" column appears in the metrics bar. Receivables and payables categories are surfaced.

**Homemaker:** Joint accounts and spouse's accounts are emphasised. Gold and jewellery category is highlighted. Language is adjusted: "household savings" rather than "your portfolio."

**Investor:** All investment sub-categories are expanded by default. Allocation pie chart starts building in the side panel as investments are added. Demat account and platform fields are surfaced.

---

## 7. Stage 3 — Goal Setting

### 7.1 Goals Entry Screen (GS-1)

**Entry conditions:** From onboarding flow after Basic Profiling or Financial Mapping, or from dashboard card: "Set one goal to give this dashboard a purpose."

**Elements:**

- Header: "What do you want your money to do for you?"
- Subcopy: "Goals help us show progress that actually matters — not random numbers."
- Goal template grid (persona-aware, shown as large selectable cards):
  - Emergency fund — "Build a safety net for unexpected events."
  - Buy a home — "Save for a down payment or plan a purchase."
  - Children's education — "Plan for school or college costs." (shown only if dependents exist)
  - Retire by a certain age — "Know your freedom number."
  - Pay off debt — "Clear your loans strategically."
  - Major purchase — "Car, vacation, renovation, or something else."
  - Custom goal — "Something specific to you." (free text)
- User selects 1–3 goals.
- Button: "Next."
- Link: "I'll think about this later."

### 7.2 Goal Detail Mini-Flows (GS-Detail)

For each selected goal, a short mini-wizard collects just enough information to initialise tracking.

**Emergency Fund:**

- Question: "How many months of expenses would make you feel safe?" Slider: 1–12 months.
- Info line: "Most planners suggest 3–6 months. You can choose what feels right for you."
- If monthly expenses are known (from Cash Flow later), auto-calculate target. Otherwise, ask for a rough monthly expense estimate or allow "I'll figure this out later."

**Buy a Home:**

- Question 1: "What price range are you considering?" Slider or preset ranges.
- Question 2: "When do you hope to buy?" Dropdown: 1–2 years / 3–5 years / 5–10 years / just exploring.
- Question 3: "How much can you put as a down payment today?" (links to assets if available).
- Info line: "We'll track your progress toward the down payment and factor in potential loan needs."

**Children's Education:**

- Question 1: "Which child is this for?" (dropdown from dependents list).
- Question 2: "Type of education?" Options: School / Undergraduate / Postgraduate / Study abroad / Other.
- Question 3: "Rough estimated cost?" Ranges or free number.
- Question 4: "When will you need this?" (auto-suggested from child's age).
- Info line: "Education costs tend to rise each year. We'll factor in a reasonable inflation estimate."

**Retire by a Certain Age:**

- Question 1: "At what age would you like to stop working for money?" Slider or number.
- Question 2: "Your current age?" (if not already captured).
- Question 3: "Rough monthly lifestyle cost in today's money?" (or "Same as current expenses").
- Info line: "We'll estimate a target corpus accounting for inflation. You can refine assumptions later."

**Pay Off Debt:**

- Show list of known loans and cards from Financial Mapping.
- Question: "Which debts would you like to focus on first?" (multi-select).
- Optional: "Any extra amount you can put toward debt each month?"
- Info line: "We'll show you the fastest path to being debt-free."

**Major Purchase:**

- Question 1: "What are you saving for?" (free text: car, vacation, renovation, etc.).
- Question 2: "Estimated cost?"
- Question 3: "By when?"
- Info line: "We'll break this down into a monthly saving target."

**Custom Goal:**

- Question 1: "Give it a name." (free text).
- Question 2: "Target amount?"
- Question 3: "Target date?"

### 7.3 Goals Summary Screen (GS-Summary)

**Elements:**

- Header: "Here are your goals."
- Goal cards, each showing: name, target amount (if set), timeframe, a placeholder progress ring (showing 0% or current allocated assets if applicable).
- Metrics bar addition: "Goals set: N."
- Button: "Continue to your dashboard."
- Link: "Add another goal" / "Edit a goal."

**Completion effect:** The dashboard's Goals section is now populated with real cards instead of placeholders. Each goal will start tracking once Cash Flow and Budgeting data become available.

---

## 8. Stage 4 — Initial Value (First Real Dashboard)

### 8.1 Dashboard Layout on First Entry

**Trigger:** The user reaches the dashboard after completing at least Basic Profiling plus some Financial Mapping OR one Goal.

**Top bar:** A warm, contextual message: "From what you've shared so far, here's your starting picture."

**Card 1 — Net Worth:** Shows total assets minus total liabilities using current inputs. Label: "Approximate — refine any value from the Assets & Loans section." Tap or click on the number to see the breakdown. If the user skipped Financial Mapping entirely, this card shows "₹–" with a CTA: "Add what you own and owe (2 minutes)."

**Card 2 — Goals Strip:** Horizontal row of goal cards, each with a name and a progress ring. If goals are set but cash flow is not, progress text says: "Tracking will start once we learn your cash flow and contributions." If goals are not set, show a single card: "Set a goal to give your dashboard a purpose (1 minute)."

**Card 3 — Cash Flow Summary (placeholder):** Greyed-out monthly income vs. expenses view with sample numbers (clearly labelled "sample data"). CTA: "Discover your cash flow (2 minutes)."

**Card 4 — Budget Overview (placeholder):** Greyed-out donut chart with sample categories. CTA: "Draft a simple budget (3 minutes)."

**Card 5 — Split Expenses (placeholder, shown only for couples/families):** Greyed-out shared expense card. CTA: "Set up shared expense tracking (2 minutes)."

**Card 6 — Next Best Steps (contextual):** Two or three recommended action cards based on what is missing and the user's persona. Examples: "Discover your cash flow (2 minutes)" / "Refine your net worth — add missing accounts" / "Set up shared expenses with your partner." Each card shows estimated time and a brief "what you'll get" line.

### 8.2 Sample Data Philosophy

For any section the user has not yet completed, the dashboard shows lightly styled sample data with a "Sample" watermark. The sample data is persona-aware (a salaried professional sees salary-like numbers; a business owner sees irregular income). This makes the dashboard look alive and gives the user a preview of what a completed setup will look like, motivating them to fill in real data.

### 8.3 Ongoing Engagement Nudges

After the initial session, the app should surface gentle reminders on subsequent launches: "Welcome back, [Name]. You've mapped your assets — want to discover your cash flow next? (2 minutes)." These nudges are dismissible and never block access to the dashboard.

---

## 9. Stage 5 — Cash Flow Discovery

### 9.1 Cash Flow Entry Hub (CF-Hub)

**Elements:**

- Header: "Let's understand how money moves each month."
- Subcopy: "This is where most people have their biggest 'aha' moment — seeing what actually comes in and goes out."
- Why we ask: "Cash flow is the engine of your financial life. Knowing it helps us show savings capacity, goal feasibility, and spending patterns."
- Options: "Quick estimate (1–2 minutes)" — recommended for first pass / "Detailed breakdown (5+ minutes)" — for users who want precision now.

### 9.2 Quick Estimate Flow (CF-Quick)

#### Screen CF-Q-1: Income

**Elements:**

- Header: "What comes in each month?"
- Natural-language input: "Describe your income sources in your own words."
- Persona-aware placeholder:
  - Salaried: "Example: Salary 1.2L after tax, wife earns about 80K, some interest from FDs."
  - Business owner: "Example: Business brings in roughly 3–5L/month but varies, rental income 25K."
  - Homemaker: "Example: Husband's salary is about 1.5L, I earn 15K from tuition classes."
  - Investor: "Example: Salary 2L, dividend income around 10K/quarter, some freelance income."
- Or structured alternative: a small form with rows — Source / Frequency (monthly, quarterly, irregular) / Amount.
- Button: "Next."

**Parsing:** Extract source names, amounts, frequency. Show structured summary for confirmation.

#### Screen CF-Q-2: Expenses (broad buckets)

**Elements:**

- Header: "Where does your money usually go?"
- Subcopy: "Don't worry about exact numbers. Rough monthly averages are perfect."
- Broad category cards (selectable, then expandable):
  - Housing — rent, EMI, maintenance, utilities.
  - Daily living — groceries, food delivery, household supplies.
  - Transport — fuel, commute, vehicle EMI, insurance.
  - Children — school fees, activities, childcare. (shown if dependents exist)
  - Health — insurance premiums, medical expenses.
  - Lifestyle — dining out, entertainment, subscriptions, shopping.
  - Debt payments — EMIs, credit card payments (pre-filled from Financial Mapping if available).
  - Savings & investments — SIPs, recurring deposits, other regular saving. (pre-filled if known)
  - Other — anything else.
- For each selected category: a single "approximate monthly amount" field.
- Natural-language alternative: "Or just describe it: 'Rent is 25K, groceries about 8K, EMIs total 15K, we spend maybe 10K eating out…'"
- Live summary at bottom or side:
  - "Total monthly income: ₹X."
  - "Total monthly expenses: ₹Y."
  - **"Monthly surplus/deficit: ₹Z."** (highlighted — this is the "aha" moment)
- Button: "Save and continue."

#### Screen CF-Q-3: Cash Flow Summary

**Elements:**

- Header: "Here's your monthly money flow."
- Visual: A simple horizontal bar or waterfall chart showing income on the left, expense categories in the middle, and surplus/deficit on the right.
- Key numbers called out: total income, total essential expenses, total lifestyle expenses, total savings/investments, surplus or gap.
- Insight line (contextual):
  - If surplus exists: "You have roughly ₹Z available each month. This could go toward your goals."
  - If deficit: "It looks like expenses may exceed income. Let's look at this more carefully in budgeting."
- Button: "Continue" / "Refine these numbers."

**Completion effect:** Dashboard Cash Flow card is now populated with real data. Goal cards can now show feasibility estimates. The monthly surplus becomes the basis for budget recommendations.

### 9.3 Detailed Breakdown Flow (CF-Detailed)

This is an extended version of the Quick Estimate, offered for users who want precision.

#### Screen CF-D-1: Income Detail

Same as CF-Q-1 but with additional fields: tax status (pre-tax / post-tax), deductions (PF, professional tax), irregular income log (bonuses, freelance months), and an annual view option showing month-by-month expected income.

#### Screen CF-D-2: Expense Detail

Each broad category from CF-Q-2 can be expanded into sub-categories. For example, "Housing" breaks into: rent or home loan EMI / maintenance or society charges / electricity / water / gas / internet and cable / property tax. Each sub-item has: amount, frequency (monthly, quarterly, annual), and whether it's fixed or variable.

#### Screen CF-D-3: Annual Irregular Expenses

- Header: "Some expenses don't happen every month."
- Prompt: "Think about insurance premiums, annual subscriptions, festival spending, vacations, school admissions."
- Calendar-style view or simple list: expense description, approximate amount, month(s) it typically occurs.
- Why we ask: "Annual expenses can surprise your monthly budget. We spread them across months so you're always prepared."

#### Screen CF-D-4: Detailed Summary

Same as CF-Q-3 but with more granularity: category-wise breakdown, fixed vs. variable split, and an annualised view that accounts for irregular expenses.

**Completion effect:** Full cash flow profile is stored. Dashboard shows detailed breakdowns. Goal feasibility estimates become more accurate.

---

## 10. Stage 6 — Budgeting

### 10.1 Budgeting Entry Hub (BG-Hub)

**Entry conditions:** Cash Flow Discovery is completed (at least quick estimate). If not, the app prompts: "To build a budget, we need to know your cash flow first. Want to do that now? (2 minutes)."

**Elements:**

- Header: "Let's give your money a plan."
- Subcopy: "A budget isn't about restriction — it's about making sure your money goes where you actually want it to."
- Why we ask: "Budgeting connects your cash flow to your goals. It shows whether your current spending supports the future you want."
- Options: "Auto-generate from my cash flow (1 minute)" — recommended / "Build from scratch (3–5 minutes)."

### 10.2 Auto-Generated Budget Flow (BG-Auto)

#### Screen BG-A-1: Proposed Budget

The system takes cash flow data and generates a starting budget using a sensible framework (e.g., a modified 50/30/20 approach adapted to the user's persona and goals).

**Elements:**

- Header: "Here's a starting budget based on what you told us."
- Subcopy: "Think of this as a first draft. Adjust anything that doesn't feel right."
- Budget view: a donut chart or bar chart with categories and amounts.
  - Essentials (housing, transport, groceries, utilities, insurance, debt payments): target % and amount.
  - Lifestyle (dining, entertainment, shopping, subscriptions): target % and amount.
  - Savings & Goals (SIPs, goal contributions, emergency fund top-up): target % and amount.
  - Buffer (unallocated): remaining amount.
- Each category row is editable: drag to adjust amount, or type a new number.
- Goal linkage: if goals are set, the "Savings & Goals" section shows which goals the savings feed into and how the budget supports them.
- Alert line (if applicable): "Your current lifestyle spending may make it hard to reach 'Buy a Home' by 2028. Adjusting by ₹5K/month could close the gap."
- Button: "Looks good — save this budget."
- Link: "I want to tweak this more."

#### Screen BG-A-2: Budget Saved Confirmation

- Header: "Your budget is set."
- Subcopy: "You can track against it from the dashboard. We'll show how actual spending compares each month."
- Quick prompt: "Want to set a reminder to review this monthly?"
- Button: "Go to dashboard."

**Completion effect:** Dashboard now shows a Budget card with the donut/bar chart, and a "this month" tracker that will update as expenses are logged. If expense tracking is not yet set up, the card shows: "Start logging expenses to see how you're doing against this budget."

### 10.3 Build from Scratch Flow (BG-Scratch)

#### Screen BG-S-1: Choose Categories

- Header: "Which spending categories matter to you?"
- Show all categories from Cash Flow with checkboxes. User can add custom categories.
- Pre-checked: categories where the user reported spending.

#### Screen BG-S-2: Set Limits

For each selected category, set a monthly budget limit. The system shows the current (estimated) spend alongside the field for reference. A running total at the bottom shows: "Budgeted so far: ₹X of ₹Y income. Remaining: ₹Z."

#### Screen BG-S-3: Allocate Surplus

- Header: "You have ₹Z left after your budget categories."
- Options: "Put it toward a goal" (select which one) / "Add to emergency fund" / "Keep as buffer" / "Split across goals."
- Visual: a mini-allocation chart showing how the surplus is distributed.

#### Screen BG-S-4: Review and Save

Same as BG-A-1 but reflecting the manually built budget. Same confirmation flow and dashboard effect.

### 10.4 Persona-Specific Budgeting Adjustments

**Salaried Professional:** Budget template emphasises EMI-to-income ratio and systematic savings (SIPs). Suggests an "investment" category separate from "savings."

**Business Owner:** Budget splits into personal and business. Warns about months where business income may dip. Suggests a "business reserve" category for lean months.

**Homemaker:** Budget focuses on household categories. Language uses "household budget" rather than "your budget." Highlights shared expenses and child-related spending.

**Investor:** Budget highlights capital allocation — how much goes to different investment buckets. Shows portfolio contribution alongside expense budget.

---

## 11. Stage 7 — Split Expenses Tracking

### 11.1 Split Expenses Entry Hub (SE-Hub)

**Entry conditions:** Shown only for users with household type "Couple" or "Family," or anyone who manually requests it. Accessible from dashboard or onboarding flow.

**Elements:**

- Header: "Let's set up shared expense tracking."
- Subcopy: "If you share costs with a partner, housemate, or family member, this helps everyone know where they stand — no awkward conversations needed."
- Why we ask: "Tracking shared expenses prevents misunderstandings and makes splitting fair and transparent."
- Button: "Set it up."
- Link: "Not relevant for me" (hides the section from dashboard).

### 11.2 Screen SE-1: Who Shares Expenses?

**Elements:**

- Header: "Who do you split expenses with?"
- Add people: name or alias and relationship (partner, housemate, parent, sibling, other). Pre-filled from household profile if available.
- Button: "Next."

### 11.3 Screen SE-2: Splitting Rules

**Elements:**

- Header: "How do you generally split things?"
- Options per person: 50-50 / By income ratio / Custom percentage / Varies by category.
- If "by income ratio": prompt for approximate income of each person (or let user set ratio directly).
- If "varies by category": show a grid of major categories (housing, groceries, dining, children, etc.) with a split percentage for each.
- Subcopy: "You can change this anytime. It's just a starting default."
- Button: "Next."

### 11.4 Screen SE-3: Shared Categories

**Elements:**

- Header: "Which expenses are shared?"
- Checklist of categories from budgeting or cash flow (pre-filled if available): Housing / Groceries / Utilities / Dining out / Children / Transport / Entertainment / Other.
- For each checked category, the default split (from SE-2) is shown and can be overridden.
- Categories not checked are treated as personal expenses.
- Button: "Save and continue."

### 11.5 Screen SE-4: Split Expenses Summary

**Elements:**

- Header: "Shared expense tracking is ready."
- Summary: who is involved, default split, shared categories.
- Visual: a simple balance bar showing "You owe ₹0 / They owe ₹0" (starting state).
- Subcopy: "As you log shared expenses, we'll keep a running balance so settlements are easy."
- Button: "Go to dashboard."

**Completion effect:** Dashboard shows a Split Expenses card with a running balance. When expenses are logged (manually or through future integrations), shared items are automatically split according to the rules. A "settle up" feature tracks payments between parties.

### 11.6 Ongoing Split Tracking (Post-Onboarding)

When logging any expense, the user sees a toggle: "Shared expense?" If toggled on, the split is applied automatically based on rules. The user can override per transaction. Monthly summary shows: total shared expenses, each person's share, net balance (who owes whom, and how much), and a "settle up" action that records a transfer.

---

## 12. Cross-Stage Data Flow and Technical Notes

### 12.1 Data Model Overview

The onboarding stages feed into a unified local data model. The core entities are as follows.

**UserProfile:** name, country, currency, persona, household type, dependents, preferences. Created in Stage 1 and referenced everywhere.

**Account:** institution, type (bank, investment, loan, card, property, etc.), balance/value, owner, linked goal (optional), approximate flag. Created in Stage 2, updated ongoing.

**Goal:** name, type, target amount, target date, linked accounts, monthly contribution target. Created in Stage 3, enriched by Stages 5 and 6.

**CashFlowProfile:** income sources (each with amount, frequency, variability) and expense categories (each with amount, frequency, fixed/variable flag). Created in Stage 5.

**Budget:** category limits, surplus allocation, linked goals, review frequency. Created in Stage 6.

**SplitRule:** participants, default split method, per-category overrides. Created in Stage 7.

**Transaction:** date, amount, category, account, shared flag, split details, notes. Created post-onboarding during regular use.

### 12.2 State Management

The app maintains an onboarding state object tracking which stages are complete, in progress, or not started. This drives the dashboard's "Next Best Steps" recommendations and the greyed-out placeholder behaviour. The state transitions are as follows.

Stage 1 (Basic Profiling) is mandatory and unlocks all other stages. Stages 2 through 7 can be completed in any order after Stage 1, though the recommended order is persona-dependent (as described in Section 3.3). Stage 4 (Initial Value dashboard) is not a separate "step" the user completes but rather the dashboard state that reflects whatever data has been entered so far. It becomes progressively richer as other stages are completed.

### 12.3 Local Processing and Privacy

All natural-language parsing is performed locally using on-device dictionaries and rule-based extraction. No text is transmitted externally. Financial data is stored in an encrypted local database. Export is available in standard formats (CSV, JSON) for user portability. No analytics telemetry is collected that includes financial data; only anonymised usage patterns (which stages are completed, time spent) may be collected if the user opts in.

### 12.4 Persona-Driven Configuration Table

The following table summarises how persona selection influences the experience across all stages.

| Aspect | Salaried | Business Owner | Homemaker | Investor |
|---|---|---|---|---|
| **FM default order** | Banks → Investments → Loans → Property | Business accounts → Personal accounts → Business loans → Personal loans | Joint accounts → Household savings → Gold → Loans | Investments (all sub-types) → Banks → Property → Loans |
| **FM highlighted categories** | EPF/PPF, SIPs | Receivables, payables, business reserve | Joint accounts, gold, household cash | Demat, multiple platforms, allocation view |
| **Goal suggestions** | Emergency fund, house, retirement | Cash runway, debt payoff, business growth | Emergency fund, education, household upgrade | Retirement corpus, wealth target, diversification |
| **Cash Flow emphasis** | Salary + deductions, EMI ratio | Irregular income handling, business vs personal | Household pooled income, variable expenses | Salary + investment income, capital gains |
| **Budget style** | 50/30/20 variant with SIP focus | Personal + business budgets | Household budget with child categories | Expense budget + capital allocation budget |
| **Split Expenses** | Couple split (if applicable) | Business vs personal split | Household member split | Less relevant (optional) |

---

## 13. Engagement and Gamification Framework

### 13.1 Philosophy

Gamification in a finance tool must feel professional and useful, not gimmicky. The core principle is: every completed step visibly improves the user's financial picture. Progress is measured in clarity and completeness, not points or badges.

### 13.2 Visible Progress Indicators

**Completion meter:** A simple progress bar on the dashboard showing "Financial setup: X of 7 steps complete." Each completed step fills a segment. This is not prominently placed but visible enough to create a gentle pull toward completion.

**Net worth tracker:** Visible from Stage 2 onward. Updates in real time as assets and liabilities are added. Seeing this number move is inherently engaging and motivates the user to add more data for accuracy.

**Goal feasibility indicators:** After Cash Flow is set up, each goal card shows whether the current surplus supports it: a green checkmark if on track, an amber indicator if tight, or a red flag if the goal needs attention. This creates a natural feedback loop.

**Budget health score:** After Budgeting is set up, a simple health indicator (e.g., "On track" / "Watch your spending" / "Over budget") provides ongoing feedback without being judgmental.

### 13.3 Micro-Celebrations

When the user completes a stage, show a brief, dignified confirmation: "Your net worth picture is now complete. Here's where you stand." Avoid confetti, animations, or language like "Awesome!" Keep the tone consistent with a financial advisor acknowledging a job well done.

### 13.4 Return Visit Nudges

On subsequent app launches, the dashboard surfaces one contextual suggestion based on what is missing. Examples: "You've set goals but haven't built a budget yet. Want to see if your current spending supports your goals? (3 minutes)" / "Your financial map is a month old. Anything changed? (1 minute to review)." These are dismissible and never block access.

---

## 14. Error Handling and Edge Cases

### 14.1 Incomplete or Inconsistent Data

If the user enters expenses that exceed income by a large margin, don't flag it as an "error." Instead, note it gently: "Your expenses seem higher than your income. This could mean some income sources are missing, or this is a temporary situation. Either way, we'll work with what you've given us."

If the user skips Financial Mapping entirely and goes to Goals, goal feasibility will be approximate. The goal card should note: "We'll give better estimates once you add your accounts."

### 14.2 Natural-Language Parsing Failures

If the parser cannot extract useful information from the user's free-text input, display: "We couldn't pick up specific details from that. Here are a few things to try:" followed by a simplified example and a link to the category picker. Never show error codes or technical messages.

### 14.3 Zero-State Handling

Every screen must have a considered zero state. No screen should ever appear empty with no guidance. Zero states should include a brief explanation of what the section does, a clear CTA to get started, and estimated time to complete.

### 14.4 Data Correction and Undo

All entered data can be edited or deleted at any time from the relevant section (Assets, Liabilities, Goals, Cash Flow, Budget, Split Rules). Changes propagate immediately: if a user deletes a large asset, net worth and goal feasibility update in real time. A simple undo option is available for accidental deletions (single-level undo, available for 30 seconds after deletion).

---

## 15. Post-Onboarding Transition

### 15.1 From Setup to Daily Use

Once all (or most) stages are complete, the dashboard transitions from "setup mode" to "tracking mode." The "Next Best Steps" card shifts from onboarding tasks to operational actions: "Log today's expenses" / "Review last week's spending" / "Monthly budget check-in due in 3 days."

### 15.2 Monthly Review Ritual

The app should encourage a monthly review cadence. At the start of each month (or a user-chosen date), surface a "Monthly Review" flow that walks through: last month's income vs. plan, expense breakdown vs. budget, goal progress, net worth change, and any split expense settlements needed. This keeps the data fresh and the user engaged long-term.

### 15.3 Ongoing Data Entry

Post-onboarding, the primary ongoing action is expense logging. This should be as frictionless as possible: a single input field that accepts natural language ("Coffee 150, groceries 800 at DMart, Uber 250") with automatic categorisation and split detection. Quick-entry shortcuts and keyboard-driven navigation support the desktop-first experience.

---

## 16. Summary of Screens and Flows

The following is a complete inventory of screens for design and engineering reference.

**Global Entry:** Welcome Screen → Time & Persona Triage.

**Stage 1 — Basic Profiling:** BP-1 (About You) → BP-2 (Household Snapshot) → BP-3 (Quick Preferences, optional).

**Stage 2 — Financial Mapping:** FM-Hub → Mode A: FM-NL-1 (Free Text) → FM-NL-2 (Summary) / Mode B: FM-G-1 (Category Selection) → FM-G-2 (Checklist + Micro-Wizards per category).

**Stage 3 — Goal Setting:** GS-1 (Goal Selection) → GS-Detail (Mini-wizard per goal) → GS-Summary.

**Stage 4 — Initial Value:** Dashboard (assembled from completed stages, placeholders for incomplete stages).

**Stage 5 — Cash Flow Discovery:** CF-Hub → Quick path: CF-Q-1 (Income) → CF-Q-2 (Expenses) → CF-Q-3 (Summary) / Detailed path: CF-D-1 (Income Detail) → CF-D-2 (Expense Detail) → CF-D-3 (Annual Irregular) → CF-D-4 (Detailed Summary).

**Stage 6 — Budgeting:** BG-Hub → Auto path: BG-A-1 (Proposed Budget) → BG-A-2 (Confirmation) / Scratch path: BG-S-1 (Choose Categories) → BG-S-2 (Set Limits) → BG-S-3 (Allocate Surplus) → BG-S-4 (Review and Save).

**Stage 7 — Split Expenses:** SE-Hub → SE-1 (Who Shares) → SE-2 (Splitting Rules) → SE-3 (Shared Categories) → SE-4 (Summary).

**Total unique screens:** approximately 28–32, depending on persona variations and micro-wizard count.

---

## 17. Appendix: Copy and Tone Guidelines

### 17.1 Voice Characteristics

The app speaks like a knowledgeable, calm financial advisor who respects the user's time and intelligence. The voice is warm but never casual, clear but never condescending, encouraging but never pushy, and honest about what it can and cannot do.

### 17.2 Structural Patterns for Copy

**Headers** should be action-oriented and plain: "Let's map what you have and what you owe" rather than "Financial Asset Discovery Module."

**Subcopy** should explain value or set expectations: "This helps us…" or "You'll see…" rather than feature descriptions.

**"Why we ask" lines** should be one sentence connecting the question to a tangible benefit: "We use this to calculate your true net worth" rather than "This field is required for system configuration."

**Button labels** should confirm the action in the user's language: "Save and continue" / "Looks good" / "I'll do this later" rather than "Submit" / "Next" / "Cancel."

### 17.3 Terminology Translation Table

| Technical Term | User-Facing Language |
|---|---|
| Assets | What you own |
| Liabilities | What you owe (loans and dues) |
| Net worth | Your financial position (what you own minus what you owe) |
| Cash flow | How money moves each month |
| Budget allocation | Your spending plan |
| Expense categorisation | Where your money goes |
| Surplus / deficit | What's left over / the gap |
| Asset allocation | How your investments are spread |
| Amortisation | How your loan gets paid down |
| Liquidity | Money you can access quickly |

---

This document should provide sufficient detail for product, design, and engineering teams to begin wireframing, prototyping, and building the progressive onboarding experience. Each section is designed to be independently referenceable — designers can work on Stage 6 without re-reading Stages 1 through 5, and engineers can implement the data model from Section 12 while UX work proceeds in parallel.