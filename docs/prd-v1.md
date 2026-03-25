# Ledger — Product Requirements Document (PRD)
### Version 0.1 | Draft for Brainstorming
### Date: March 14, 2026

---

## 1. Product Vision & Positioning

**Vision Statement:** Ledger democratizes personal wealth management by combining the rigor of double-entry accounting with the accessibility of AI — so that any Indian individual, regardless of financial literacy, can understand, track, and grow their wealth with the same clarity a chartered accountant would have.

**Target User Personas:**

**Persona 1 — Riya (The Salaried Professional):** 29, IT professional in Bangalore. Has salary account, 2 credit cards, a home loan, PPF, a Zerodha demat account, and a few mutual funds via Kuvera. She has no idea what her actual net worth is. She uses Excel sometimes but gives up. She wants to know: *"Am I on track? Can I afford that Europe trip next year?"*

**Persona 2 — Suresh (The Small Business Owner):** 45, runs a textile business in Surat. Has multiple bank accounts, fixed deposits, commercial property, gold, LIC policies, and children's education funds. He wants a consolidated view of family wealth and wants to plan for his daughter's wedding and his retirement. He finds apps like MProfit too "CA-oriented."

**Persona 3 — Ananya (The Early Investor):** 23, just started working. Has one bank account, one credit card, and just opened a Zerodha account. She wants to build good financial habits from day one. She needs hand-holding and education. She wants to know: *"How much should I save? What should I invest in?"*

**Competitive Landscape:** MProfit (desktop-heavy, CA-oriented), INDMoney (aggregator, not ledger-based), Perfios (B2B focus), Capitalmind Wealth Planner (goal planning only), Moneycontrol (tracking only, no accounting).

**Ledger's Differentiators:**
- True double-entry accounting engine under the hood, but the user never sees "debit" or "credit"
- AI-first experience — onboarding, categorization, reconciliation, querying
- User owns their AI configuration (BYOK LLM)
- Goal-based planning deeply integrated with actual financial data, not hypothetical inputs
- India-first: built for Indian financial instruments, tax regimes, and statement formats

---

## 2. Module Breakdown & Detailed Requirements

---

### MODULE 1: AI-Powered Onboarding & Account Provisioning

**Objective:** Transform a 5-minute conversational flow into a fully provisioned Chart of Accounts (CoA) tailored to the user's financial life.

**R1.1 — Conversational Onboarding Wizard**
The system presents a chat-based wizard (not a form) that asks progressive, branching questions in natural language. The conversation must feel like talking to a knowledgeable friend, not filling out a tax form. The AI must avoid jargon — it should say "Where do you keep your money?" not "List your asset accounts."

**R1.2 — Onboarding Question Framework**
The wizard must cover the following domains through conversation. Each domain should require no more than 2–3 questions unless the user's situation is complex.

- **Banking:** Which banks do you use? How many accounts (savings, current, salary)?
- **Credit:** Do you have credit cards? Which ones? Any personal loans or buy-now-pay-later?
- **Housing:** Do you own or rent? Do you have a home loan? What is the approximate current value?
- **Vehicles:** Do you own vehicles? Any vehicle loans?
- **Investments — Equity:** Do you trade stocks? Which broker (Zerodha, Groww, Angel One, etc.)?
- **Investments — Mutual Funds:** Do you invest in mutual funds? SIPs? Which platform?
- **Investments — Fixed Income:** FDs, RDs, PPF, EPF, NPS, Sukanya Samriddhi, bonds?
- **Insurance:** Life insurance (term, endowment, ULIP), health insurance, vehicle insurance?
- **Gold & Alternatives:** Physical gold, digital gold, sovereign gold bonds?
- **Real Estate (non-primary):** Any rental property or land?
- **Income Sources:** Salary, freelance/consulting, rental income, dividends, interest?
- **Regular Expenses:** Do you want to track daily expenses, or only major outflows?
- **Family:** Are you tracking finances for yourself only or for your household?
- **Tax:** Are you on the Old or New tax regime?

**R1.3 — Default Account Provisioning**
Regardless of user answers, the system must provision a baseline set of accounts that every Indian individual is likely to need. These are created silently and revealed only when relevant.

- **Default Asset Accounts:** Cash in Hand, Bank Account (generic), Fixed Deposits (generic), PPF, EPF, Gold, Mutual Funds (generic), Stocks (generic)
- **Default Liability Accounts:** Credit Card (generic), Personal Loan
- **Default Income Accounts:** Salary/Wages, Interest Income, Dividend Income, Capital Gains — Short Term, Capital Gains — Long Term, Rental Income, Gift/Other Income
- **Default Expense Accounts:** Groceries, Dining Out, Transportation/Fuel, Utilities (Electricity, Water, Gas), Mobile & Internet, Rent, EMI Payments, Insurance Premium, Medical/Healthcare, Education, Shopping/Personal, Entertainment/Subscriptions, Travel, Household Help/Domestic, Donations/Charity, Taxes Paid, Miscellaneous

**R1.4 — Custom Account Creation from Conversation**
When the user mentions specific banks, brokers, or instruments, the system must create named sub-accounts. For example, if the user says "I have accounts in HDFC and SBI," the system creates `Asset > Bank > HDFC Savings` and `Asset > Bank > SBI Savings` as children under the Bank Account parent.

**R1.5 — CoA Review & Edit Screen**
After the conversation concludes, the system presents a visual, categorized tree view of all provisioned accounts. The user can rename, delete, merge, or add accounts. The AI provides a summary: *"I've set up 34 accounts based on our conversation. Here's how your financial world looks. Feel free to adjust anything — you can always add more later."*

**R1.6 — Onboarding Completion State**
Onboarding is considered complete when the user confirms the CoA. The system then prompts the user to perform their first import or manually enter opening balances for key accounts (with AI assistance to estimate if the user is unsure).

---

### MODULE 2: Document Import, Parsing & Transaction Creation

**Objective:** Enable users to upload financial documents in PDF, CSV, and Excel formats and automatically generate accurate, categorized, double-entry journal entries.

**R2.1 — Supported Document Types (India-Specific)**

| Category | Sources | Formats |
|---|---|---|
| Bank Statements | SBI, HDFC, ICICI, Axis, Kotak, Yes, IndusInd, PNB, BOB, IDBI, Federal, and others | PDF, CSV, Excel, password-protected PDF |
| Credit Card Statements | All major issuers (HDFC, SBI Card, ICICI, Amex, Axis, RBL, IDFC First, etc.) | PDF |
| Stock Broker — Holdings | Zerodha (Console), Groww, Angel One, ICICI Direct, HDFC Securities | CSV, Excel |
| Stock Broker — P&L / Tradebook | Zerodha (tax P&L report), Groww, Angel One | CSV, Excel |
| Mutual Fund Statements | CAMS, KFintech (consolidated account statement — CAS) | PDF |
| Provident Fund | EPFO Passbook | PDF |
| NPS | CRA-NSDL statement | PDF |
| PPF | Bank-issued PPF passbook/statement | PDF |
| Insurance | LIC premium receipts, term plan statements | PDF |
| Tax Documents | Form 26AS, Annual Information Statement (AIS), Form 16 | PDF |
| UPI/Wallet | PhonePe, Google Pay, Paytm statement exports | CSV |
| Custom/Generic | Any tabular financial data | CSV, Excel |

**R2.2 — PDF Parsing Pipeline**
The system must handle both digitally generated PDFs (text-selectable) and scanned PDFs (requiring OCR). The pipeline consists of: upload → password handling (prompt user if encrypted) → text/table extraction → row-level parsing → schema normalization → AI-powered categorization → journal entry generation → human review queue.

**R2.3 — Intelligent Column Mapping**
For CSV and Excel files, the system must auto-detect column semantics (date, narration/description, debit amount, credit amount, balance) using header names and sample data patterns. If confidence is low, the system presents a drag-and-drop column mapper UI with AI suggestions highlighted.

**R2.4 — Transaction Categorization Engine**
Every imported transaction must be mapped to an account from the user's CoA. The AI categorization engine must use the transaction narration/description to infer the category. Examples of pattern recognition needed:

- `UPI/DR/407812345678/SWIGGY/...` → Expense: Dining Out
- `NEFT/CR/SALARY/INFOSYS LTD` → Income: Salary
- `EMI DEBIT HDFC HOME LOAN` → Liability: Home Loan (principal) + Expense: Interest (split)
- `ATM/CASH WDL/...` → Asset: Cash in Hand (transfer, not expense)
- `NACH/SIPICICIPRUMF` → Asset: Mutual Funds — ICICI Pru MF

The engine must learn from user corrections. If a user re-categorizes "ZOMATO" from "Miscellaneous" to "Dining Out," all future Zomato transactions must follow. This user-specific learning must be stored as categorization rules.

**R2.5 — Unique Transaction ID Generation (Deduplication)**
Every transaction must be assigned a deterministic, reproducible hash-based ID composed of: `hash(account_id + date + narration + amount + running_balance_if_available)`. When the same statement is re-imported, transactions with matching hashes are skipped. The system must present a deduplication report: *"143 transactions found. 98 are new. 45 already exist and were skipped."*

**R2.6 — Cross-Account Transfer Detection**
When money moves between two accounts (UPI, NEFT, RTGS, IMPS), both statements each contain one side of the transaction. The deduplication engine must detect and link matching pairs. Match criteria: opposite direction (one debit, one credit), equal amount, date within ±1 day, and a transfer keyword present in either the cleaned or raw narration. The system must handle three real-world scenarios:

- **Scenario 1 — Same-batch**: both account statements uploaded in one import. Both rows are matched and flagged `TRANSFER_PAIR` during the same dedup pass.
- **Scenario 2 — Cross-batch (prospective)**: one account was imported previously; the counterpart account is imported now. The engine compares incoming rows against the prior account's historical rows and retroactively links the match. The historical entry's journal entry is flagged for correction if already approved.
- **Scenario 3 — One-sided (deferred)**: only one account exists in the system. The transaction stays `NEW` and is proposed with a Suspense counterpart. When the counterpart account is imported later, Scenario 2 fires automatically. Users never need to re-import or manually reconcile — the system catches the match whenever both sides become available.

Bank-to-brokerage movements (e.g., NEFT to Zerodha followed by a stock purchase) are **not** treated as simple transfer pairs — each leg generates its own journal entry with the brokerage ledger account as intermediary.

**R2.7 — Opening Balance Handling**
When importing the first statement for any account, the system must infer or ask for the opening balance. If the statement includes a running balance column, the system can calculate the opening balance automatically. This opening balance becomes a journal entry against an "Opening Balance Equity" account.

**R2.8 — Password-Protected PDFs**
Many Indian bank statements are password-protected (often with a convention like DOB or PAN-based passwords). The system must prompt the user for the password. It must never store the PDF password — only the extracted data.

**R2.9 — Import History & Audit Trail**
Every import must be logged with: timestamp, filename, document type, number of transactions extracted, number of new transactions, number of duplicates skipped, and parsing confidence score. Users must be able to view, undo, or re-process any past import.

---

### MODULE 3: Double-Entry Accounting Engine

**Objective:** Maintain an unbreakable, auditable, double-entry ledger that is the single source of truth for all financial data in the system.

**R3.1 — The Golden Rule Enforcement**
Every transaction in the system must consist of at least two journal entry lines. The sum of all debit amounts must equal the sum of all credit amounts for every transaction. The system must reject any transaction that does not balance. There are no exceptions.

**R3.2 — Account Types & Normal Balances**

| Type | Normal Balance | Debit Increases | Credit Increases |
|---|---|---|---|
| Asset | Debit | ✓ | |
| Liability | Credit | | ✓ |
| Equity | Credit | | ✓ |
| Income/Revenue | Credit | | ✓ |
| Expense | Debit | ✓ | |

**R3.3 — Multi-Leg Transactions**
The system must support transactions with more than two legs. For example, a salary credit involves: Credit to Income: Salary (gross), Debit to Expense: TDS/Tax, Debit to Asset: EPF (employee contribution), and Debit to Asset: Bank Account (net salary). The AI should be capable of suggesting salary breakdowns if the user provides their salary structure once.

**R3.4 — Chart of Accounts Hierarchy**
Accounts must support a tree hierarchy of at least 4 levels deep. Example: `Asset > Investments > Mutual Funds > HDFC Mid-Cap Opportunities Fund`. Balances must roll up through the hierarchy. The user must be able to view balances at any level.

**R3.5 — Accounting Periods**
The system must support both calendar year and Indian financial year (April–March) views. Users must be able to select their preferred default. All reports must respect the selected period.

**R3.6 — Immutable Ledger with Corrections**
Transactions, once confirmed, must not be silently edited. Corrections must be made through reversing entries (a new transaction that negates the original) followed by a correcting entry. This preserves a complete audit trail. The UI should abstract this — the user clicks "Edit" and the system handles the reversal behind the scenes.

**R3.7 — Currency & Units**
The primary currency is INR. For stock and mutual fund holdings, the system must track both quantity (units/shares) and value. Gold must support grams and value. The system must support marking accounts as "quantity-tracked" (for investments) vs. "value-only" (for bank accounts).

**R3.8 — Market Value vs. Book Value**
For investment accounts (stocks, mutual funds, gold, real estate), the system must maintain both book value (acquisition cost) and current market value. The difference represents unrealized gains/losses. Market values should be updated via API integrations (see Module 8).

---

### MODULE 4: Financial Statements & Reports

**Objective:** Generate accurate, standard financial statements that give users a complete picture of their financial health — in both technical and simplified, AI-explained formats.

**R4.1 — Personal Balance Sheet**
A standard balance sheet showing Assets, Liabilities, and Net Worth (Equity) as of any selected date. The balance sheet must balance (Assets = Liabilities + Net Worth). It must support drill-down from category to individual accounts to individual transactions. It must show both book value and market value columns for investment assets. The AI must be able to generate a plain-English summary: *"Your net worth as of today is ₹34.2L. Your biggest asset is your HDFC Bank FD at ₹10L. Your biggest liability is your home loan at ₹28L outstanding."*

**R4.2 — Income & Expense Statement (Personal P&L)**
A statement showing all income and all expenses for a selected period, with the net surplus or deficit. It must support comparison across periods (this month vs. last month, this FY vs. last FY). It must support percentage breakdowns (e.g., "Dining Out is 12% of total expenses"). The AI must provide insights: *"Your expenses increased 18% this month, driven primarily by a ₹45,000 travel expense. Excluding that one-time expense, you're actually 3% below last month."*

**R4.3 — Cash Flow Statement**
A three-section cash flow statement: Operating (day-to-day income and expenses), Investing (mutual fund purchases, stock trades, FD creation/maturity), and Financing (loan EMIs, loan disbursements). This is the most powerful statement for understanding where money is actually flowing and must be presented with visual Sankey diagrams or waterfall charts.

**R4.4 — Net Worth Tracker**
A time-series chart showing net worth over time (monthly granularity at minimum). It must decompose net worth into asset classes (cash, equity, debt, real estate, gold, others) and show how the composition changes over time. It must show both book-value net worth and market-value net worth.

**R4.5 — Trial Balance**
A technical report showing all accounts with their debit and credit balances. This is primarily for debugging and audit purposes and can be hidden behind an "Advanced" menu. Total debits must equal total credits.

**R4.6 — Account Ledger / Statement**
For any individual account, the user must be able to view a chronological ledger showing every transaction, running balance, and linked journal entries. This is the equivalent of a passbook view.

**R4.7 — Investment Performance Report**
For investment accounts, the system must calculate and display: absolute returns, XIRR (time-weighted annualized returns considering actual cash flow dates), CAGR, unrealized gains/losses, and realized gains/losses. This must work for individual instruments and for the portfolio as a whole.

**R4.8 — Tax-Ready Reports**
Capital gains report split by Short-Term (STCG) and Long-Term (LTCG) with holding period calculations per Indian tax rules (1 year for equity, 2 years for debt funds pre-2023 rules, 3 years for real estate, etc.). Interest income summary across all FDs, savings accounts, and bonds. Dividend income summary. Rental income summary with standard deduction applied. Section 80C/80D deductions summary (PPF, ELSS, insurance premiums, etc.). These reports should help users or their CAs during ITR filing.

---

### MODULE 5: Dashboards & Insights

**Objective:** Present a visual, at-a-glance financial dashboard that tells the user "how am I doing?" within 5 seconds of opening the app.

**R5.1 — Home Dashboard**
The home screen must show: net worth (with % change from last month), this month's income vs. expense (with surplus/deficit), top 5 expense categories this month (visual breakdown), upcoming financial obligations (EMI due dates, SIP dates, insurance renewal), and a "financial health pulse" — a composite score or indicator (see R5.5).

**R5.2 — Expense Analytics Dashboard**
Category-wise expense breakdown (pie/donut chart), month-over-month expense trend (bar chart), daily expense heatmap (calendar view showing spend intensity), top merchants/payees, and category budget vs. actual (if budgets are configured — see Module 9).

**R5.3 — Investment Dashboard**
Portfolio composition (equity vs. debt vs. gold vs. real estate — pie chart), portfolio value over time (line chart), top gainers and losers (individual holdings), SIP tracker (active SIPs, total invested, current value), and asset allocation vs. target allocation (see goal planning).

**R5.4 — Liability Dashboard**
Outstanding liabilities summary, loan amortization progress (how much principal paid vs. remaining), credit card utilization, interest paid this year across all loans, and projected debt-free date.

**R5.5 — Financial Health Score**
A composite score (0–100 or a Red/Amber/Green system) calculated from: emergency fund adequacy (do they have 6 months of expenses in liquid assets?), debt-to-asset ratio, savings rate (income minus expenses as % of income), insurance coverage adequacy, investment diversification, and goal funding status. The AI must explain the score in plain language and suggest 2–3 specific actions to improve it.

**R5.6 — AI-Generated Monthly Digest**
At the end of each month (or on demand), the AI generates a natural-language financial summary. Example: *"In February 2026, you earned ₹1.85L and spent ₹1.12L, saving ₹73,000 (39% savings rate — excellent!). Your net worth grew from ₹42.1L to ₹43.8L, boosted by a ₹1.2L appreciation in your equity portfolio. Your home loan balance dropped below ₹25L for the first time. You're on track for your retirement goal but slightly behind on your emergency fund target."*

---

### MODULE 6: AI Chat Interface (Personalized Wealth Bot)

**Objective:** Allow users to ask any question about their financial data in natural language and receive accurate, contextual, and actionable answers.

**R6.1 — BYOK (Bring Your Own Key) LLM Configuration**
Users must be able to configure their preferred LLM provider and API key. Supported providers at launch: OpenAI (GPT-4o, GPT-4.1), Anthropic (Claude Sonnet, Claude Opus), Google (Gemini). The API key must be encrypted at rest using AES-256. The key must never be logged, and must only be decrypted in memory at the moment of API call. Users must be able to test their key connectivity from the settings screen. The system must track and display approximate token usage and cost.

**R6.2 — Query Capabilities**
The chatbot must be able to answer questions across these categories:

- **Balance Queries:** "What is my current net worth?" / "How much do I have in my HDFC savings account?"
- **Spending Analysis:** "How much did I spend on Swiggy last month?" / "What are my top 5 expenses this quarter?"
- **Income Analysis:** "What was my total interest income this financial year?"
- **Investment Queries:** "What is the XIRR on my mutual fund portfolio?" / "Which stocks am I holding at a loss?"
- **Comparison:** "Am I spending more on dining out this month compared to last month?"
- **Forecasting:** "At my current savings rate, how long will it take to save ₹10L?"
- **Tax:** "What is my estimated capital gains tax liability for this year?"
- **Goal-Related:** "Am I on track for my retirement goal?" / "How much more do I need to invest monthly to reach my vacation goal?"
- **Advice-Oriented:** "Should I prepay my home loan or invest in mutual funds?" / "Is my emergency fund adequate?"
- **Transaction Search:** "Show me all transactions above ₹10,000 in January" / "When was the last time I paid my LIC premium?"

**R6.3 — Tool-Calling Architecture**
The LLM must not have direct database access. Instead, the system must define a set of secure, parameterized functions (tools) that the LLM can invoke. Examples of tools: `get_account_balance(account_name, as_of_date)`, `get_transactions(account_name, date_from, date_to, min_amount, max_amount, category)`, `get_expense_summary(period, group_by)`, `get_net_worth(as_of_date)`, `get_investment_returns(account_name, return_type)`, `get_goal_progress(goal_name)`. All tool calls must be scoped to the authenticated user's data. No cross-user data access is possible.

**R6.4 — Contextual Awareness**
The chatbot must maintain conversation context within a session. If a user asks "How much did I spend on groceries?" and then follows up with "What about last month?", the system must understand the follow-up refers to groceries in the previous month.

**R6.5 — Proactive Insights**
The chatbot should not only respond to queries but also proactively surface insights when the user opens the chat. Examples: *"I noticed you have ₹3.2L sitting idle in your savings account. Your emergency fund target is ₹2L. Would you like to explore where to invest the excess ₹1.2L?"*

**R6.6 — Explainability**
When the chatbot provides a number, it must be able to show how it arrived at that number — e.g., linking to the specific transactions or the calculation methodology. Users must be able to click "Show me the details" to see underlying data.

---

### MODULE 7: Goal-Based Financial Planning

**Objective:** Help users define life goals, quantify them financially with inflation-adjusted projections, and create actionable investment plans — inspired by Capitalmind Wealth Planner but deeply integrated with the user's actual financial data.

**R7.1 — Goal Definition Wizard**
A conversational, step-by-step wizard for each goal type. Supported goal types at launch:

- **Retirement / Financial Freedom:** At what age do you want to retire? What monthly expense do you expect in retirement (today's value)? Do you expect any pension or rental income? What is your current age?
- **Child's Education:** Child's current age? Expected age at higher education? Estimated cost today? Domestic or international?
- **Child's Marriage:** Child's current age? Expected age at marriage? Estimated cost today?
- **Home Purchase:** When do you want to buy? Estimated property cost today? How much down payment? Expected home loan tenure and rate?
- **Vehicle Purchase:** When? Estimated cost today? Loan or full payment?
- **Vacation / Travel:** When? Estimated cost today?
- **Emergency Fund:** Target number of months of expenses to cover?
- **Custom Goal:** Name, target date, target amount (today's value).

**R7.2 — Inflation-Adjusted Future Value Calculation**
Every goal's target amount must be projected to the target date using configurable inflation rates. Default inflation assumptions: General inflation 6%, Education inflation 10%, Medical inflation 8%, Real estate inflation 7%. Users must be able to override these defaults.

**R7.3 — Risk Profiling & Asset Allocation**
The wizard must assess the user's risk appetite through a short questionnaire (5–7 questions about investment experience, reaction to market drops, time horizon preference, income stability). Based on the score, the system recommends an asset allocation (equity:debt ratio) for each goal. Short-term goals (less than 3 years) should skew heavily toward debt. Long-term goals (greater than 7 years) can have higher equity allocation. The user must be able to override the recommendation.

**R7.4 — SIP & Lumpsum Calculation**
For each goal, the system must calculate: the future value of the goal (inflation-adjusted), existing investments already tagged to this goal, the remaining corpus needed, the expected return rate based on the chosen asset allocation (using historical blended returns), the required monthly SIP to bridge the gap, and the required lumpsum investment alternatively. The system must support a "what-if" slider: *"What if I increase my SIP by ₹5,000?"* — showing the impact on goal achievement probability.

**R7.5 — Goal Funding from Existing Assets**
Unlike standalone calculators, Ledger's unique advantage is that it knows the user's actual financial data. The system should allow users to "tag" existing investments to goals. For example, an ELSS fund worth ₹3L can be tagged to the "Retirement" goal. The goal planner then adjusts the remaining SIP requirement accordingly.

**R7.6 — Goal Dashboard**
A visual dashboard showing all goals with: goal name and icon, target date, target amount (future value), current funded amount, funding percentage (progress bar), monthly SIP required, and on-track / behind / ahead status. A consolidated view must show total monthly SIP commitment across all goals vs. available surplus (income minus expenses minus existing SIPs).

**R7.7 — Monte Carlo Simulation (Advanced)**
For users who want deeper analysis, the system should offer a probability-based projection using Monte Carlo simulation. Instead of a single expected return, the system simulates thousands of scenarios with varying return sequences and shows: probability of achieving the goal (e.g., "78% chance of reaching your retirement corpus"), best-case and worst-case outcomes, and the SIP needed for a 90% probability of success.

---

### MODULE 8: Market Data & External Integrations

**Objective:** Keep investment valuations current and reduce manual data entry by integrating with Indian financial data sources.

**R8.1 — Mutual Fund NAV**
Daily NAV updates from AMFI (Association of Mutual Funds in India) — free, publicly available data. Auto-match imported mutual fund folios with AMFI scheme codes. Update portfolio market value daily.

**R8.2 — Stock Prices**
End-of-day stock prices from BSE/NSE. Use free APIs (BSE India, NSE India, or providers like Google Finance/Yahoo Finance). Auto-match holdings by ISIN or ticker symbol.

**R8.3 — Gold Price**
Daily gold price per gram (24K) from a reliable Indian source. Apply to gold holdings for market value computation.

**R8.4 — Fixed Deposit & Debt Instrument Rates**
Maintain a reference database of current FD rates from top 20 banks. Use for projections and opportunity cost analysis (*"Your SBI FD is earning 6.5%, but HDFC is offering 7.1% for the same tenure"*).

**R8.5 — Inflation Index**
CPI data from RBI/MOSPI for actual inflation tracking against assumed inflation in goal planning.

**R8.6 — Email-Based Auto-Import (Future Phase)**
With user consent, connect to Gmail/Outlook to automatically detect and import mutual fund transaction confirmations (from CAMS/KFintech), stock trade confirmations from brokers, bank debit/credit alerts, and credit card statements. This is a Phase 2 feature due to complexity and trust/privacy concerns.

---

### MODULE 9: Budgeting & Expense Management

**Objective:** Help users set and track spending budgets at a category level, powered by AI recommendations based on their actual spending history.

**R9.1 — AI-Suggested Budgets**
Based on 3 months of imported transaction history, the AI suggests category-level monthly budgets. Example: *"Based on your spending patterns, I suggest a monthly grocery budget of ₹12,000 and a dining out budget of ₹6,000. Your current averages are ₹11,200 and ₹7,800 respectively."*

**R9.2 — Budget Tracking**
Real-time tracking of spend vs. budget per category. Visual indicators (green/amber/red) as the user approaches limits. Push notification or in-app alert when a category exceeds 80% of budget.

**R9.3 — Manual Transaction Entry**
A quick-entry interface for cash expenses. Minimal fields: amount, category, optional note. The system auto-generates the journal entry (Debit: Expense category, Credit: Cash in Hand). Voice input support for mobile: *"Spent 250 on auto rickshaw"*.

**R9.4 — Recurring Transaction Templates**
Users can set up recurring transactions for: monthly rent, EMIs, SIPs, insurance premiums, subscriptions (Netflix, gym, etc.). These auto-generate on the scheduled date and appear in the "pending confirmation" queue.

---

### MODULE 10: Tax Planning & Optimization (India-Specific)

**Objective:** Help users understand their tax liability and identify optimization opportunities throughout the financial year, not just at filing time.

**R10.1 — Tax Regime Comparison**
Based on the user's income and deductions data already in the system, automatically compute tax liability under both Old and New regimes and recommend the optimal one.

**R10.2 — Section 80C Tracker**
Track investments qualifying under Section 80C (PPF, ELSS, EPF, life insurance premium, tuition fees, NSC, tax-saver FD) against the ₹1.5L limit. Show remaining headroom and suggest instruments.

**R10.3 — Capital Gains Tax Estimator**
Based on the investment transactions already in the system, calculate estimated STCG and LTCG tax liability. Suggest tax-loss harvesting opportunities: *"You have ₹18,000 in unrealized losses in Tata Motors. Selling and re-buying after 30 days could offset ₹18,000 of your ₹45,000 LTCG, saving you approximately ₹2,250 in tax."*

**R10.4 — Advance Tax Reminders**
For users with tax liability exceeding ₹10,000 (the advance tax threshold), the system must remind them of advance tax due dates (June 15, September 15, December 15, March 15) and estimate the installment amounts.

---

### MODULE 11: Security, Privacy & Data Ownership

**Objective:** Users are entrusting Ledger with their most sensitive financial data. Security is not a feature — it is a foundational requirement.

**R11.1 — Data Encryption**
All financial data encrypted at rest (AES-256). All data in transit over TLS 1.3. LLM API keys encrypted with a user-specific encryption key derived from their authentication credentials.

**R11.2 — Data Residency**
All data stored in Indian data centers (AWS Mumbai / GCP Mumbai). No financial data ever leaves Indian jurisdiction.

**R11.3 — Zero-Knowledge LLM Interaction**
When the user's data is sent to an external LLM API (via their BYOK key), only the minimum necessary context should be sent. Transaction narrations should be anonymized where possible. The system must clearly disclose to the user what data is being sent to the LLM. An "offline mode" option where the LLM runs locally (e.g., Ollama) should be supported for privacy-conscious users.

**R11.4 — Authentication**
Email + password with mandatory 2FA (TOTP-based, e.g., Google Authenticator). OAuth with Google/Apple as an alternative. Session timeout after 15 minutes of inactivity.

**R11.5 — Data Export & Portability**
Users must be able to export all their data at any time in standard formats (CSV, JSON, or a Ledger-specific backup format). This ensures no vendor lock-in.

**R11.6 — Data Deletion**
Users must be able to permanently delete their account and all associated data with a single action (after confirmation). Deletion must be irreversible and complete within 48 hours.

---

### MODULE 12: Adjacent & Differentiating Features

**R12.1 — Family / Household Mode**
Allow a primary user to create sub-profiles for spouse and dependents. Consolidated household balance sheet and net worth. Individual and combined views. Useful for Persona 2 (Suresh) who manages family wealth.

**R12.2 — Document Vault**
Secure storage for uploaded financial documents (insurance policies, property documents, loan agreements, tax returns). Tagged and searchable. The AI can answer questions about these documents: *"When does my term insurance policy expire?"*

**R12.3 — Financial Calendar**
A calendar view showing all upcoming financial events: SIP dates, EMI due dates, FD maturity dates, insurance renewal dates, advance tax deadlines, credit card payment due dates, and goal milestones.

**R12.4 — Net Worth Milestones & Gamification**
Celebrate milestones: *"🎉 Congratulations! Your net worth crossed ₹50L today!"* Streaks for consistent savings months. Badges for goal progress. This must be tasteful and optional — finance is serious, but positive reinforcement helps build habits.

**R12.5 — Nominee & Estate Planning Tracker**
Track nominees for each financial account/instrument. Flag accounts with missing nominees. Maintain a "financial map" document that can be shared with a trusted family member in case of emergency — a complete inventory of all assets and liabilities with account details.

**R12.6 — Loan Optimizer**
For users with multiple loans, analyze and recommend: which loan to prepay first (highest interest rate vs. smallest balance), impact of making a lumpsum prepayment on total interest and tenure, and refinancing opportunities if current rates are lower.

**R12.7 — Insurance Adequacy Calculator**
Based on the user's income, liabilities, dependents, and goals, calculate the recommended life insurance cover and health insurance cover. Compare with existing policies and flag gaps.

---

## 3. Non-Functional Requirements

**Performance:** Dashboard must load in under 2 seconds. PDF parsing must complete within 30 seconds for a standard 12-month bank statement. Chat responses must begin streaming within 3 seconds.

**Scalability:** Architecture must support 100K users in Year 1 with room to scale to 1M. Each user may have up to 50,000 transactions. Multi-tenant architecture with strict data isolation.

**Availability:** 99.9% uptime target. Graceful degradation if LLM APIs are unavailable (core accounting functions must work without AI).

**Accessibility:** WCAG 2.1 AA compliance. Support for Hindi and English at launch, with architecture to support regional languages in future.

**Platforms:** Web (responsive, desktop-first) at launch. Progressive Web App (PWA) for mobile. Native mobile apps (React Native or Flutter) in Phase 2.

---

## 4. Phased Delivery Roadmap

**Phase 1 — Foundation (Months 1–4):** Double-entry engine and database schema, AI onboarding wizard, CSV/Excel import with AI categorization, manual transaction entry, basic balance sheet and income/expense statement, account ledger views, and BYOK chat with basic query capability.

**Phase 2 — Intelligence (Months 5–8):** PDF parsing for top 10 Indian banks and credit cards, Zerodha and CAMS statement import, transaction deduplication and cross-account reconciliation, dashboards (home, expense, investment, liability), goal-based planning wizard, net worth tracker, and budgeting.

**Phase 3 — Depth (Months 9–12):** Market data integrations (NAV, stock prices, gold), investment performance reports (XIRR), tax planning module, financial health score, monthly AI digest, document vault, financial calendar, and family/household mode.

**Phase 4 — Scale (Year 2):** Support for additional brokers and statement formats, email-based auto-import, native mobile apps, Monte Carlo simulations, loan optimizer, insurance adequacy calculator, estate planning tracker, and regional language support.

---

## 5. Open Questions for Brainstorming

1. **Monetization Model:** Freemium (free for basic, paid for AI features and advanced reports)? Subscription tiers? Pay-per-AI-query? Since users bring their own LLM key, the AI cost is partially externalized — how does this affect pricing?

2. **Offline-First vs. Cloud-First:** Should Ledger offer a fully local/offline mode (like MProfit's desktop app) for privacy-conscious users, or is cloud-first acceptable with strong encryption?

3. **CA/Advisor Collaboration:** Should there be a "share with my CA" feature where users can grant read-only access to a tax advisor or financial planner? This could be a powerful distribution channel.

4. **Community & Benchmarking:** Anonymous, opt-in benchmarking — *"Your savings rate of 35% is higher than 72% of Ledger users in your income bracket."* Is this valuable or creepy?

5. **Regulatory Considerations:** Does Ledger need any SEBI or RBI registration if it provides investment suggestions? How do we stay on the right side of "information" vs. "advice"?

6. **Accounting Standard Alignment:** Should the system align with any formal personal accounting standard, or is a simplified, practical approach better for the target user?

---

This is a living document. I recommend we now deep-dive into any specific module you'd like to refine further — whether that's the database schema design, the AI prompt engineering for onboarding, the PDF parsing architecture, or the goal planning calculations. What would you like to explore next?