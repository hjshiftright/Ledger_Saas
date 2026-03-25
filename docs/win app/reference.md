# Ledger Desktop — Reference: Accounting, Parsers, Reports & Dashboard Suite

> **Purpose:** This document consolidates reference material from the existing Ledger 3.0 source docs into the sections relevant to the Windows Desktop implementation. Nothing here is new design — it is selected and adapted from `docs/` for use in the new repo. Implementation decisions live in the `design/` docs.

---

## 1. Double-Entry Accounting Primer (for Developers)

### 1.1 The Fundamental Equation

Every financial event touches exactly two places simultaneously. Money never appears from nowhere and never disappears — it always moves *from* one account *to* another.

```
Assets = Liabilities + Equity
```

Double-entry keeps this equation balanced by recording every transaction as a debit and a credit of equal value.

### 1.2 The Five Account Types

| # | Type | What it represents | Normal (home) side | Desktop CoA examples |
|---|------|--------------------|--------------------|----------------------|
| 1 | **Asset** | Things you own | Debit (DR) | Savings account, investments, home, cash, loans given |
| 2 | **Liability** | Things you owe | Credit (CR) | Credit card outstanding, home loan, personal loan |
| 3 | **Equity** | Net worth | Credit (CR) | Opening balance, retained surplus |
| 4 | **Income** | Money flowing to you | Credit (CR) | Salary, interest, dividends, cashback, refunds |
| 5 | **Expense** | Money flowing away | Debit (DR) | Food, rent, travel, EMI interest portion, subscriptions |

**DR = left side; CR = right side.** The home side increases the account; the opposite side decreases it.

### 1.3 Debit / Credit Derivation Rule

```
  Assets  =  Liabilities  +  Equity        (equation places Assets on LEFT)
  [LEFT]       [RIGHT]        [RIGHT]

  Income  → increases Equity → same side as Equity → CR
  Expense → decreases Equity → opposite side       → DR
```

You never need to memorise the table — you can always derive it from the equation.

### 1.4 Common Desktop Transaction Patterns

| Event | DR | CR |
|---|---|---|
| Salary credited to bank | Asset (Savings) | Income (Salary) |
| Grocery purchase (debit card) | Expense (Food) | Asset (Savings) |
| Credit card purchase | Expense (category) | Liability (Credit Card) |
| Credit card payment from bank | Liability (Credit Card) | Asset (Savings) |
| Home loan EMI paid | Liability (Home Loan) + Expense (Interest) | Asset (Savings) |
| SIP investment | Asset (Mutual Funds) | Asset (Savings) |
| Dividend received | Asset (Savings) | Income (Dividends) |
| Cash withdrawal | Asset (Cash) | Asset (Savings) |
| Money lent to a friend | Asset (Loans Given) | Asset (Savings) |
| Repayment received | Asset (Savings) | Asset (Loans Given) |

### 1.5 Chart of Accounts — Desktop Default (Indian)

```
1000  ASSETS
  1100  Current Assets
    1101  Cash in Hand
    1102  Savings Accounts
    1103  Current Accounts
    1104  Fixed Deposits (< 1 year)
    1105  Liquid Funds / Sweep FD
  1200  Investments
    1201  Stocks / Equities
    1202  Mutual Funds
    1203  ETFs
    1204  Fixed Deposits (> 1 year)
    1205  PPF
    1206  EPF
    1207  NPS
    1208  Sovereign Gold Bonds
    1209  Gold / Silver (physical)
  1300  Loans Given / Receivables
    1301  Personal Loans Given
    1302  Security Deposits
    1303  Tax Refunds Receivable
  1400  Fixed Assets
    1401  Real Estate
    1402  Vehicles

2000  LIABILITIES
  2100  Credit Cards
    2101  HDFC Regalia
    ...   (per card — seeded from onboarding)
  2200  Loans
    2201  Home Loan
    2202  Vehicle Loan
    2203  Personal Loan
    2204  Education Loan
  2300  Other Payables
    2301  Tax Payable
    2302  Bills Payable

3000  EQUITY
  3001  Opening Balance Equity
  3002  Retained Surplus

4000  INCOME
  4100  Earned Income
    4101  Salary
    4102  Bonus / Incentive
    4103  Freelance / Consulting
  4200  Investment Income
    4201  Dividends
    4202  Interest Earned
    4203  Realized Capital Gains — Short Term
    4204  Realized Capital Gains — Long Term
  4300  Other Income
    4301  Cashback / Rewards
    4302  Refunds
    4303  Rental Income

5000  EXPENSES
  5100  Housing
    5101  Rent
    5102  Maintenance / Society Charges
    5103  Home Loan Interest
  5200  Food & Dining
    5201  Groceries
    5202  Dining Out
    5203  Food Delivery
  5300  Transportation
    5301  Fuel
    5302  Vehicle Loan Interest
    5303  Cab / Auto / Metro
  5400  Utilities & Bills
    5401  Electricity
    5402  Internet
    5403  Mobile Recharge
    5404  Water / Gas
  5500  Shopping
    5501  Clothing & Accessories
    5502  Electronics
    5503  General Merchandise
  5600  Health & Insurance
    5601  Medical / Pharmacy
    5602  Health Insurance Premium
    5603  Life Insurance Premium
  5700  Education
    5701  School / College Fees
    5702  Courses / Training
  5800  Entertainment & Leisure
    5801  OTT / Subscriptions
    5802  Films / Events
    5803  Travel / Holiday
  5900  Financial Charges
    5901  Bank Charges
    5902  Credit Card Charges / Penalties
  5999  Uncategorized
```

---

## 2. Parser Reference Notes (C# Port Guide)

### 2.1 Supported Sources — Desktop v1

| Category | Sources | Formats | Parser class |
|---|---|---|---|
| Mutual Fund CAS | CAMS, KFintech, MF Central | Password-protected PDF | `CasParser` |
| Stock Broker | Zerodha Holdings, Tradebook, Tax P&L, Capital Gains | CSV, XLSX | `ZerodhaCsvParser` |
| Bank — PDF | HDFC, SBI, ICICI, Axis, Kotak, IndusInd, IDFC First | PDF | `HdfcPdfParser`, `SbiPdfParser`, etc. |
| Bank — CSV | HDFC, SBI, ICICI, Axis, Kotak, Zerodha | CSV | `HdfcCsvParser`, `SbiCsvParser`, etc. |
| Generic fallback | Any unrecognized source | CSV, XLSX | `GenericCsvParser` (shows column-mapper UI) |
| v2 scope | Credit card statements, EPFO passbook, NPS, Form 26AS | PDF | Planned |

### 2.2 Processing Pipeline (8 Stages)

```
Stage 1 — File Validation     Magic bytes check; extension vs content mismatch alert
Stage 2 — Password Attempt    CandidateList from UserProfile (see design/04-file-intelligence.md §6)
Stage 3 — Source Detection    Filename regex → PDF keyword scan → confidence score
Stage 4 — Text Extraction     PdfPig text layer → Docnet table extraction → Windows OCR → Tesseract
Stage 5 — Source-Specific     IDocumentParser implementation for the detected source
          Parser
Stage 6 — Schema              Map raw rows to NormalizedTransaction (date, amount, narration,
          Normalization        debit/credit flag, account hint, running balance if available)
Stage 7 — Deduplication       SHA-256 per row + fuzzy near-duplicate (date ±1, amount, payee)
                               + transfer-pair detection (debit A = credit B same day)
Stage 8 — Proposal Queue      POST to ProposalService → user reviews in /proposals
```

### 2.3 CAS Password Convention (Indian Banks)

```
Password format used by banks when they email CAS / statement PDFs:
  CAMS CAS:     PAN uppercase (e.g. ABCDE1234F)
  HDFC Bank:    <DOB ddmmyyyy> (e.g. 15012985)
  SBI:          <Account number last 4 digits>  OR  <DOB ddmmyyyy>
  ICICI:        <DOB ddmmyyyy>  OR  <PAN last 4 + DOB yyyy>
  Axis:         <DOB ddmmyyyy>
  Kotak:        <DOB ddmmyyyy>
  Union Bank:   <Customer ID>  (fallback to DOB)
```

This is why the candidate list is built from PAN + DOB + Name + Mobile — these are the exact values banks use.

### 2.4 NormalizedTransaction Schema (canonical output from every parser)

```csharp
public record NormalizedTransaction
{
    public DateOnly Date          { get; init; }
    public decimal  Amount        { get; init; }      // always positive
    public string   Narration     { get; init; }      // original description
    public string   CleanNarration{ get; init; }      // after common-prefix strip
    public bool     IsDebit       { get; init; }
    public decimal? RunningBalance{ get; init; }
    public string?  ReferenceNo   { get; init; }
    public string?  AccountHint   { get; init; }      // last 4 digits if available
    public string   SourceType    { get; init; }      // e.g. "HDFC_PDF"
    public decimal  RowConfidence { get; init; }      // 0.0 – 1.0
    public string   RawLine       { get; init; }      // for audit / debugging
}
```

---

## 3. Report Suite Reference

The following reports are required in the Desktop app. Each maps to API endpoints in `design/08-api-design.md`.

### 3.1 Core Financial Reports

| Report | Plain-Language Name | API endpoint | Key metrics |
|---|---|---|---|
| Balance Sheet | "What I Own & What I Owe" | `GET /reports/balance-sheet` | Total assets, total liabilities, net worth; expandable tree to account level |
| Income & Expense | "Money In vs Money Out" | `GET /reports/income-expense` | Total income, total expenses, surplus/deficit, savings rate % |
| Cash Flow | "Where Money Came From & Went" | `GET /reports/cash-flow` | Operating / investing / financing cash flows |
| Net Worth Trend | "My Net Worth Over Time" | `GET /reports/net-worth-history` | Monthly snapshots; sparkline + milestone overlay |
| Tax Summary | "Tax Picture This Year" | `GET /reports/tax-summary` | 80C utilization, LTCG/STCG, dividend income, TDS summary |
| Category Spending | "Where Did My Money Go" | `GET /reports/spending?period=...` | Category breakdown, month-on-month trend, top merchants |
| Budget vs Actual | "Am I On Budget?" | `GET /reports/budget-vs-actual` | Per-category budget remaining, over/under |
| Account Statement | "My Account History" | `GET /reports/account/{id}` | Reconstructed account ledger with running balance |

### 3.2 Investment Reports

| Report | Plain-Language Name | Key metrics |
|---|---|---|
| Portfolio Holdings | "What I'm Invested In" | Units, cost basis, current value, unrealized P&L per holding |
| Investment Returns | "How My Investments Are Doing" | XIRR, absolute return %, returns by asset class |
| Capital Gains | "My Capital Gains This Year" | STCG / LTCG split, tax-applicable amount per instrument |
| Asset Allocation | "How My Money Is Spread" | Donut chart: equity, debt, gold, real estate, cash |
| CAMS CAS Summary | "My Mutual Fund Picture" | Folio-wise holding, current NAV, XIRR, dividends declared |

### 3.3 Dashboard Refresh Frequency

| Data type | Refresh strategy |
|---|---|
| Transaction data | Updated immediately after each file is processed (SignalR push) |
| Net worth snapshot | Written to `net_worth_history` on each successful file process |
| Investment market value | Updated from the most recent parsed statement; no live price feed in v1 |
| Dashboard layout | Persisted to `app_settings.dashboard_layout` (see design/09-frontend.md §2.4) |

---

## 4. Strategic Dashboard Suite — 20 Insight Dashlets

> **Three design briefs exist for these 20 dashlets.** Brief A (`team_brief.md` / `team_brief-2.md`, both identical) captures the *advisor perspective* — user value, visualization, data logic, and tips. Brief B (`team_brief-3.md`) captures the *emotional insight-first perspective* — the "aha!" moment, hero visual, and single key action. §4.3 merges both and adds `dashlet_key` identifiers for implementation. All three are preserved here because users freely add or remove any dashlet from the picker.

> Every insight dashlet shows the footer: *"Based on your financial data in Ledger. For guidance only — not financial advice."*

---

### 4.1 Brief A — Advisor's Perspective (`team_brief.md` / `team_brief-2.md`)

*Both source files are identical. Focus: user value, visualization style, data logic / calculation, advisor tip.*

#### Phase 1 — Safety & Peace of Mind

| # | Dashboard Name | User Value | Visualization | Data Logic / Calculation | Advisor Tip |
|---|---|---|---|---|---|
| 1 | **Survival Runway** | Eliminates fear of job loss | Progress Ring + Runway Line | `Liquid Assets / Avg Monthly Expenses` | "You have 14 months of flight time. Focus on quality, not panic." |
| 2 | **Emergency Shield** | Prevents one bad day ruining a year | Shield Icon (Fill Level) | `Emergency Fund / Target (6× Expenses)` | "Your shield is at 80%. Refill with ₹5k/mo to be fully protected." |
| 3 | **Family Protection** | Ensures family continuity | Gap Chart (Overlapping Bars) | `Term Life Cover vs (Loans + Future Goals)` | "You have a ₹1Cr gap. A simple term plan fixes this for ₹1k/mo." |
| 4 | **Health Safety-Net** | Prevents medical debt | Stacked Bubble Chart | `Corp Insurance vs Personal Top-up vs Avg Surgery Cost` | "Corporate cover is thin. A ₹20L top-up is your best safety move." |

#### Phase 2 — Wealth Engine

| # | Dashboard Name | User Value | Visualization | Data Logic / Calculation | Advisor Tip |
|---|---|---|---|---|---|
| 5 | **Lazy Money Gym** | Identifies wasted potential | Character Animation (Sleep/Gym) | `Savings Balance − Monthly Buffer = Lazy Money` | "₹8L is 'sleeping' (0% real growth). Move it to an Orchard for 8% yield." |
| 6 | **Wealth Velocity** | Are you actually getting richer? | Vector Arrow (Length/Direction) | `(Net Worth Growth / Income) × 100` | "Your income is up, but wealth is flat. Lifestyle is eating your raises." |
| 7 | **Freedom Countdown** | Defines "Work-Optional" date | Digital Countdown Clock | `FIRE Number (25× Exp) / Monthly Savings Projection` | "Independence Day: Aug 2038. ₹5k extra/mo brings it to 2036." |
| 8 | **Tax Leakage** | Stops March scramble spending | Leaky Bucket Animation | `Unused 80C / 80D limits based on profile` | "Move ₹15k to ELSS now to save ₹4.5k in tax (and grow wealth)." |

#### Phase 3 — Aspirations & Dreams

| # | Dashboard Name | User Value | Visualization | Data Logic / Calculation | Advisor Tip |
|---|---|---|---|---|---|
| 9 | **Dream Home Path** | Makes ownership a plan | House Progress Filling Up | `Dedicated Savings vs Projected Downpayment` | "You are 65% there. This goal is on track for Dec 2027!" |
| 10 | **Junior Harvard** | Solves #1 parent anxiety | Stacked Books (Local/Intl) | `Savings vs Local Tuition vs Ivy League Costs` | "You've funded 3 years of local college, but only 0.5 years of Ivy League." |
| 11 | **Luxury Escape** | Removes guilt from vacations | Passport Stamp Progress | `Sinking Fund vs Trip Budget` | "This trip costs 4 months of retirement. Are you okay with that trade?" |
| 12 | **Guilt-Free Spending** | Encourages enjoying work | Green Light / Traffic Light | `Surplus after Goal SIPs and Fixed Costs` | "You have ₹12k for 'fun' this month. Spending it won't hurt any goals." |

#### Phase 4 — Modern Habits

| # | Dashboard Name | User Value | Visualization | Data Logic / Calculation | Advisor Tip |
|---|---|---|---|---|---|
| 13 | **Subscription Dustbin** | Reclaims leaked money | Bin with Dollar Signs | `Total Recurring app/service spends (Monthly × 120)` | "Canceling 3 unused apps saves you ₹4L over your working life." |
| 14 | **Inflation Ghost** | Explains rising costs | Fading Text / Ghost Effect | `Current Cost × (1 + Inflation)^Years` | "You'll need ₹1.6L in 2030 to live like you do on ₹1L today." |
| 15 | **Debt Snowball** | Clear path out of debt | Snowball Rolling Down | `Liabilities ordered by Interest Rate / APR` | "Kill the Credit Card first. It's a 42% interest emergency." |
| 16 | **Lifestyle Creep** | Detects hidden upgrades | Splitting Path Chart | `Income Trend-line vs Expense Trend-line` | "Eating out grew 4× faster than your salary. Slow down to stay on track." |

#### Phase 5 — Legacy & Wisdom

| # | Dashboard Name | User Value | Visualization | Data Logic / Calculation | Advisor Tip |
|---|---|---|---|---|---|
| 17 | **Passive Orchard** | Tracks Work-Optional status | Growing Tree with Fruits | `(Investment Income / Total Expenses) × 100` | "Your fruits just paid your Internet bill. Next target: Your Rent!" |
| 18 | **"What-If" Machine** | Life transition modeling | Parallel Timelines (A vs B) | `User input variables (sabbatical, kid, etc.)` | "A 1-year sabbatical moves your retirement back by 1.5 years. Worth it?" |
| 19 | **Philanthropy Dash** | Deliberate giving | Heart Expansion Chart | `Safe Giving Capacity / Total Surplus` | "You can give ₹5k/mo forever without affecting your family's safety." |
| 20 | **Financial Karma** | Ensures wealth readiness | Checklist / Legal Seal | `Nomination Status % across all manually entered info` | "3 accounts have no nominees. They risk being lost if you aren't here." |

---

### 4.2 Brief B — Insight-First Design (`team_brief-3.md`)

*Focus: the emotional "aha!" moment grasped in under 3 seconds, hero visual, and one key action.*

#### Phase 1 — Safety ("Can I Sleep?")

| # | Dashboard Name | The "Aha!" Moment (3-Sec) | Visual Hero | Key Action |
|---|---|---|---|---|
| 1 | **Survival Runway** | "I have enough to live for **14 months** without a paycheck." | Plane on a Runway (length = months) | Extend by 2 months this year |
| 2 | **Emergency Shield** | "My safety net is **80% full.** One major shock won't break me." | Shield Icon filling with liquid | Autopay ₹5k until 100% |
| 3 | **Family Protection** | "My family is covered for **all loans + school fees** for 10 years." | Protective Umbrella over small icons | Close the 20% 'gap' in cover |
| 4 | **Health Safety** | "A major illness won't touch my life savings." | Safety Net below a heart icon | Add a ₹20L top-up cover |

#### Phase 2 — Growth ("Is My Money Working?")

| # | Dashboard Name | The "Aha!" Moment (3-Sec) | Visual Hero | Key Action |
|---|---|---|---|---|
| 5 | **Lazy Money Auditor** | "I'm losing **₹2,500 every month** to inflation." | Money sleeping on a couch | Move 'Lazy Cash' to MF |
| 6 | **Wealth Velocity** | "For every ₹100 I earn, **₹15** is staying with me forever." | Speedometer (Net Worth vs Income) | Aim for ₹20/₹100 next month |
| 7 | **Freedom Clock** | "Work becomes optional on **Feb 2038.**" | Sunrise Progress Bar | Add ₹5k/mo to save 2 years |
| 8 | **Tax Leakage** | "I have a **₹4,500 'gift'** from the Govt waiting for me." | Gift Box (the tax to be saved) | Invest ₹15k in ELSS now |

#### Phase 3 — Aspirations ("Dreaming")

| # | Dashboard Name | The "Aha!" Moment (3-Sec) | Visual Hero | Key Action |
|---|---|---|---|---|
| 9 | **Dream Home Path** | "I'm **65% done** with my downpayment fund." | Building rising out of the ground | On track — keep the current SIP |
| 10 | **Junior Harvard** | "My kid's education is **fully funded** for the next 12 years." | Stacks of Library Books | Focused on 'International' goal |
| 11 | **Luxury Escape** | "This trip is **100% paid for** — guilt-free travel." | Suitcase filling up with stamps | Book your tickets now! |
| 12 | **Spend Zone** | "I have **₹12,400 to spend on fun** this month safely." | Green Traffic Light | Enjoy the surplus! |

#### Phase 4 — Reality ("Check-Up")

| # | Dashboard Name | The "Aha!" Moment (3-Sec) | Visual Hero | Key Action |
|---|---|---|---|---|
| 13 | **Subscription Bin** | "I'm wasting **₹4 Lakhs** over 10 years on unused apps." | Trash bin with dollar signs | Cancel 3 unused subscriptions |
| 14 | **Inflation Ghost** | "My today's ₹1 Lakh will only buy **₹70k of life** in 5 years." | Fading Bill icon | Increase SIPs by 10% annually |
| 15 | **Debt Snowball** | "I'll be **Debt-Free in 14 months.**" | Snowball rolling down | Pay ₹5k extra to Credit Card |
| 16 | **Lifestyle Creep** | "My spending is growing **faster** than my income." | Diverging arrows (Spend vs Earn) | Cut discretionary spend by 10% |

#### Phase 5 — Legacy ("Wisdom")

| # | Dashboard Name | The "Aha!" Moment (3-Sec) | Visual Hero | Key Action |
|---|---|---|---|---|
| 17 | **Passive Orchard** | "My investments paid for my **Internet and Electricity** bills." | Tree with ripened fruit | Next goal: Pay the Gas bill |
| 18 | **"What-If" Machine** | "A sabbatical will cost me **18 months** of retirement." | Two parallel paths | Decide: Time vs. Wealth |
| 19 | **Giving Dash** | "I can help **3 students** for 1 year without any impact." | Heart expanding | Commit to a local NGO |
| 20 | **Karma Check** | "My wealth is **100% ready** for my heirs." | Legal Wax Seal | Link Nominee to Axis Bank A/c |

---

### 4.3 Combined Implementation Reference

*Merges both briefs; adds `dashlet_key` identifiers used by the Zustand dashlet store (`design/09-frontend.md` §2.4).*

#### Phase 1 — Safety ("Can I Sleep Tonight?")

| # | Dashlet Key | Friendly Name | 3-Second Insight | Visual | Calculation |
|---|---|---|---|---|---|
| 1 | `survival_runway` | How long can I survive without income? | "You have **N months** of flight time." | Plane on a runway — length = months | `Liquid Assets ÷ Avg Monthly Expenses` |
| 2 | `emergency_shield` | Is my safety net full? | "Your safety net is **X% full**." | Shield icon filling with liquid | `Emergency Fund ÷ (6 × Monthly Expenses)` |
| 3 | `family_protection` | Is my family covered? | "Your family is covered for all loans + goals for N years." | Umbrella over family icons | `Term Insurance Cover vs (Outstanding Loans + Future Goal Cost)` |
| 4 | `health_safety` | Will a medical emergency drain me? | "A major illness won't touch your savings." | Safety net below a heart | `Personal Health Cover vs Avg Major Surgery Cost` |

#### Phase 2 — Wealth ("Is My Money Working?")

| # | Dashlet Key | Friendly Name | 3-Second Insight | Visual | Calculation |
|---|---|---|---|---|---|
| 5 | `lazy_money` | Am I letting money sleep? | "₹N is losing value to inflation every month." | Money sleeping on a couch | `Bank Balance − 3-Month Expense Buffer = Idle Cash` |
| 6 | `wealth_velocity` | Am I actually getting richer? | "For every ₹100 I earn, ₹N stays with me." | Speedometer arrow | `(Net Worth Change ÷ Monthly Income) × 100` |
| 7 | `freedom_clock` | When can I stop working? | "Work becomes optional in **Month YYYY**." | Sunrise progress bar | `FIRE Number (25× annual spend) ÷ Monthly Savings Rate projection` |
| 8 | `tax_leakage` | Am I losing money to tax I shouldn't? | "You have a ₹N tax-saving opportunity this year." | Gift box (the tax saved) | `Unused 80C / 80D limits from parsed income + expense data` |

#### Phase 3 — Aspirations ("What Am I Working Towards?")

| # | Dashlet Key | Friendly Name | 3-Second Insight | Visual | Calculation |
|---|---|---|---|---|---|
| 9 | `dream_home` | How close am I to my home downpayment? | "You're **X% there** on your downpayment goal." | Building rising from ground | `Dedicated Savings ÷ Target Downpayment` |
| 10 | `junior_education` | Can I fund my child's education? | "You've funded N years of college so far." | Stack of library books | `Education Goal Fund ÷ Projected College Cost (local vs international)` |
| 11 | `guilt_free_holiday` | Can I take that vacation without guilt? | "This trip is **fully funded** — go book it." | Suitcase filling with passport stamps | `Holiday Sinking Fund ÷ Trip Budget` |
| 12 | `spend_zone` | How much can I spend on fun this month? | "You have ₹N for guilt-free spending this month." | Green traffic light | `Monthly Surplus − Goal SIP commitments − Fixed Costs` |

#### Phase 4 — Reality Checks ("Am I Fooling Myself?")

| # | Dashlet Key | Friendly Name | 3-Second Insight | Visual | Calculation |
|---|---|---|---|---|---|
| 13 | `subscription_audit` | Am I paying for things I don't use? | "Unused subscriptions will cost you ₹N over 10 years." | Trash bin with money icons | `Recurring spend tagged as subscriptions × 120 months` |
| 14 | `inflation_ghost` | Is inflation eating my money? | "Your ₹1L today will only buy ₹N of life in 5 years." | Fading banknote | `Savings Balance × (1 − Inflation Rate)^Years` |
| 15 | `debt_snowball` | When will I be debt-free? | "You'll be **debt-free in N months**." | Snowball rolling downhill | `Liabilities sorted by interest rate; avalanche/snowball projection` |
| 16 | `lifestyle_creep` | Is my spending growing faster than my income? | "Your spending is growing **faster** than your income." | Two diverging arrows | `Expense growth rate (3-month trend) vs Income growth rate (3-month trend)` |

#### Phase 5 — Legacy ("The Bigger Picture")

| # | Dashlet Key | Friendly Name | 3-Second Insight | Visual | Calculation |
|---|---|---|---|---|---|
| 17 | `passive_orchard` | Are my investments paying my bills yet? | "Your investments just paid for your Internet bill." | Tree with ripening fruit | `(Monthly Investment Income ÷ Monthly Expenses) × 100` |
| 18 | `what_if_machine` | What if I take a sabbatical / change? | "A 1-year break moves your retirement back by N months." | Two parallel timelines | User inputs variables (sabbatical length, income drop %) → recalculates FIRE date |
| 19 | `giving_dash` | Can I afford to give back? | "You can support N students for a year without affecting your goals." | Heart expanding | `Safe Giving Capacity = Monthly Surplus × configurable % after all goals funded` |
| 20 | `karma_check` | Is my wealth ready for my family if I'm not there? | "X accounts have no nominees — they risk being lost." | Legal wax seal / checklist | `Nomination completeness scan across manually entered account data` |

#### Implementation Notes

- **Data availability:** Many of these (family protection, health safety, FIRE, education) require user-entered data beyond what's parsed from statements. The dashlet shows a "Complete your profile to unlock this" state when required data is missing — never shows fake numbers.
- **Disclaimer:** Every insight dashlet carries a footer: *"Based on your financial data in Ledger. For guidance only — not financial advice."*
- **Default set:** The default dashboard (before user customizes) shows dashlets: `net_worth`, `monthly_summary`, `spending_breakdown`, `pending_approvals`, `bank_balances`, `file_activity`. The 20 insight dashlets are in the picker but off by default — user adds what they want.
- **Data freshness:** Insight dashlets re-compute whenever the underlying transaction data changes (SignalR `file.organized` event triggers a dashboard refresh signal).
- **What-If Machine (18):** Requires an input form embedded in the dashlet — not just a display. Inputs: event type (sabbatical / career change / early retirement), duration, income impact %. Output: revised FIRE date + delta vs current.

---

## 5. Key Design Decisions Cross-Reference

| Topic | Where designed |
|---|---|
| Vault structure & file organization | `design/04-file-intelligence.md` §2, §4 |
| Password candidate matching | `design/04-file-intelligence.md` §6 |
| Proposal approval flow | `design/04-file-intelligence.md` §11 |
| All API endpoints | `design/08-api-design.md` |
| Dashboard drag-and-drop (react-grid-layout) | `design/09-frontend.md` §2.4 |
| Dashlet catalogue and store | `design/09-frontend.md` §2.4, §3.5–3.7 |
| UX language standards | `design/09-frontend.md` §9, `design/01-requirements.md` §1.15 |
| Lending tracker (F-093–F-099) | `design/01-requirements.md` §1.10a, `design/03-data-model.md` §7a |
| EMI prepayment insights (F-170–F-176) | `design/01-requirements.md` §1.18, `design/03-data-model.md` §7b |
| Folio / Portfolio insights (F-160–F-166) | `design/01-requirements.md` §1.17 |
| Family Mode (v2) | `design/10-family-mode.md` |
| Security & encryption | `design/05-security.md` |
| MSIX packaging | `design/11-packaging.md` |

---

## 6. UI Component Reuse Reference (`frontend/src/`)

The existing SaaS React app (`frontend/src/`) is partially reusable for the desktop UI. All listed components already use Tailwind CSS 4, lucide-react, and recharts — no additional library installs needed for the dashboard layer.

### 6.1 Component Inventory

| Component file | What it does | Key internals | Desktop reuse notes |
|---|---|---|---|
| `PersonalDashboard.jsx` | Main overview: net worth, goal cards, profile type banner, monthly savings | `PROFILE_TYPE_INFO`, `GOAL_TYPE_INFO`, `formatCurrency` (Cr/L/₹), framer-motion animations, `API.dashboard.load()` | Replace API base URL (see §6.4). Keep icons and animations as-is. |
| `NetWorthDashboard.jsx` | Editable assets / liabilities grid + FIRE projection | Asset categories: banks, realEstate, equity, foreignEquity, providentFund, fixedDeposits, bullion; `expectedNW = (age−22) × surplus × 3`; `INFLATION_RATE = 0.06` | Asset categories map to new `Assets\Banks\`, `Assets\House\`, `Assets\Investments\` vault folders. Move `INFLATION_RATE` to user-configurable setting. |
| `WealthDashboard.jsx` | recharts-based charts; shared UI atoms | AreaChart, BarChart, PieChart, LineChart; `DOMAIN_COLORS` (8 asset-class colours); `IDEAL_ALLOC` percentages; atoms: `Spinner`, `Empty`, `InsightCard`, `StatCard`; `fmt()` formatter (Cr/L/K) | `DOMAIN_COLORS` and `IDEAL_ALLOC` can seed `FolioInsightsDashlet` thresholds directly. `InsightCard`, `StatCard`, `Spinner`, `Empty` are ready to use in any new dashlet. |
| `ReportsPage.jsx` | Period-scoped reports: income/expense, cash flow, tax | `getPeriodDates(preset)` — handles `this_month`, `last_month`, `this_quarter`, `this_fy`, `last_12m`; `KpiCard` (4 colour variants); `fmt()`, `pct()` | `getPeriodDates` and `KpiCard` are standalone utilities — copy directly into desktop `utils/`. |
| `GoalsPage.jsx` | Goal CRUD + SIP projections | `GOAL_ICONS`, `PRIORITY_COLOR`, ComposedChart (Area + Line); `computeSip()` using 12% return + 5.12% step-up; `fmtCurrency()` | Reuse as a full page. Update to use `window.LEDGER_API_BASE`. |
| `BudgetsPage.jsx` | Budget management with progress bars | `COMMON_CATEGORIES` (pre-seeded CoA codes 4101–4999); `spendPct()`, `barColor()`, `thisMonthRange()`; uses inline `BASE` constant | Update inline `BASE` to `window.LEDGER_API_BASE`. CoA codes match §1.5 |
| `ChatWidget.jsx` | Floating in-app chat with typing indicator | `TypingDots`, `MarkdownText` (paragraph + bullet renderer), `formatInline()` (bold); uses `API` client | Wire `/chat` endpoint to desktop LLM service. `MarkdownText` renderer is reusable anywhere. |
| `SettingsPage.jsx` | LLM provider management (Gemini, OpenAI, Anthropic) | `PROVIDER_MODELS`, `PROVIDER_META` (label, colour, key hints); add/edit/test/delete/set-default flow; uses `API` client | Reuse for desktop AI settings. Add a section for vault path and DB encryption key (above the LLM section). |
| `ImportWizard.jsx` | Guided file import modal | Multi-step wizard: select → map columns → review → confirm | Replace with `FilesPage` for desktop (LedgerDrive drop zone). Keep the column-mapper step for `GenericCsvParser` fallback. |
| `api.js` | Central API client with typed methods | `BASE = http://127.0.0.1:8000/api/v1`; `v1Call()` wrapper; namespaced methods: `API.dashboard`, `API.accounts`, `API.goals`, `API.budgets`, `API.chat`, etc. | Change `BASE` to `window.LEDGER_API_BASE` (injected by WPF shell). All caller code stays the same. |

### 6.2 Shared Utilities to Extract

These formatter functions appear independently in multiple files. Consolidate into a single `src/utils/formatters.js` for the desktop app:

| Function | Source files | Notes |
|---|---|---|
| `formatCurrency(n)` | `PersonalDashboard.jsx` | Cr / L / ₹ with `en-IN` locale |
| `fmtCurrency(n)` | `GoalsPage.jsx` | Same logic, different name |
| `fmtAmount(n)` | `BudgetsPage.jsx` | Inline `₹` + `en-IN` locale (no Cr/L) |
| `fmt(n)` | `WealthDashboard.jsx`, `ReportsPage.jsx` | Cr / L / K with `en-IN` locale |
| `pct(n)` | `ReportsPage.jsx` | `toFixed(1) + '%'` |
| `getPeriodDates(preset)` | `ReportsPage.jsx` | Date range for period presets |
| `today()` | `GoalsPage.jsx` | `new Date().toISOString().slice(0,10)` |

### 6.3 Reusable Constants

| Constant | Source file | Desktop use |
|---|---|---|
| `DOMAIN_COLORS` | `WealthDashboard.jsx` | Asset class colours for charts and folio insights dashlet |
| `IDEAL_ALLOC` | `WealthDashboard.jsx` | Cash 10%, Equities 30%, MF 25%, FD 15%, PF 10%, Gold 5%, RE 5% — seed concentration alert thresholds in `FolioInsightsDashlet` |
| `INFLATION_RATE = 0.06` | `NetWorthDashboard.jsx` | Move to user-configurable setting (Settings → Assumptions) |
| `GV_RETURN = 0.12`, `GV_STEPUP = 0.0512` | `GoalsPage.jsx` | Expected SIP return and step-up rate — move to configurable setting |
| `COMMON_CATEGORIES` | `BudgetsPage.jsx` | Expense CoA codes — already match §1.5 CoA |
| `GOAL_ICONS`, `PRIORITY_COLOR` | `GoalsPage.jsx` | Goal type icons and priority colour classes — reuse directly |

### 6.4 API Base URL Migration

All SaaS components use `http://127.0.0.1:8000/api/v1` as the base URL, either via the shared `API` client (`api.js`) or as an inline `const BASE` declaration.

**Desktop change:** The WPF shell injects the in-process API base at startup:

```javascript
// Injected by WPF WebView2 before React loads (see design/06-shell-host.md §3)
window.LEDGER_API_BASE = 'http://127.0.0.1:{dynamicPort}/api/v1';
```

Files that need updating:

| File | Current base | Change needed |
|---|---|---|
| `api.js` | `const BASE = "http://127.0.0.1:8000/api/v1"` | `const BASE = window.LEDGER_API_BASE \|\| 'http://127.0.0.1:8000/api/v1'` |
| `BudgetsPage.jsx` | `const BASE = 'http://127.0.0.1:8000/api/v1'` | Same pattern (or refactor to use `API` client) |
| `GoalsPage.jsx` | `const BASE = 'http://127.0.0.1:8000/api/v1'` | Same pattern (or refactor to use `API` client) |

All other components already go through the shared `API` object from `api.js` — they pick up the change automatically once `api.js` is updated.

### 6.5 Libraries Already Available

No additional npm installs needed for the dashboard layer:

| Library | Used by | Purpose |
|---|---|---|
| `recharts` | `WealthDashboard.jsx`, `GoalsPage.jsx`, `ReportsPage.jsx` | All chart types (Area, Bar, Pie, Line, Composed) |
| `framer-motion` | `PersonalDashboard.jsx` | Entry animations on dashlets |
| `lucide-react` | All components | Icon set (Briefcase, TrendingUp, Target, Shield, Heart, etc.) |
| `tailwindcss` v4 | All components | Utility-first styles — already configured |

`react-grid-layout ^1.4.4` is the **only additional library** needed for the dashlet drag-and-drop grid (see `design/09-frontend.md` §2.4). It is not present in the current SaaS app.
