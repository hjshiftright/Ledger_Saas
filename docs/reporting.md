

<think>The user wants me to create a detailed design document for Module 4: Reports Manager (Dashboards & Reports). This should cover all the reporting capabilities needed for a personal finance ledger application built on double-entry bookkeeping principles.

Let me think about what reports and dashboards a comprehensive personal finance system needs:

1. **Dashboard / Home Screen** - The main landing page with key metrics
2. **Balance Sheet** - Assets, Liabilities, Net Worth at a point in time
3. **Income & Expense Statement (P&L)** - Revenue and expenses over a period
4. **Cash Flow Statement** - Where money came from and where it went


5. **Net Worth Tracker** - Historical net worth trend
6. **Investment Reports** - Portfolio performance, asset allocation, gains/losses
7. **Budget vs Actual** - If they have goals/budgets
8. **Tax Reports** - Capital gains, income summary for tax filing
9. **Goal Progress Reports** - Linked to Goal Manager
10. **Trial Balance** - For the accounting purists
11. **General Ledger** - Detailed transaction history per account
12. **Account Statements** - Reconstructed statements per account
13. **Expense Analytics** - Category-wise, merchant-wise, trend analysis
14. **Debt Reports** - Loan summaries and repayment tracking

Now I'm thinking through the broader architecture for this reporting system. I need to establish the core philosophy around personal finance reporting, design an effective dashboard as the entry point, and then detail each report type with consideration for filters, customization, export options, and interactive elements. I should also account for mobile usability and how frequently data gets refreshed and computed.</think># Ledger — Module 4: Reports Manager — Detailed Design Document

---

## Module Philosophy

The first three modules — Onboarding, Goal Manager, and Transaction Manager — are about getting data into Ledger. The Reports Manager is about getting meaning out. Data without interpretation is noise. A user who has diligently imported three months of bank statements and brokerage reports does not want to stare at a table of journal entries. They want answers to questions they carry in their heads every day: Am I spending more than I earn? Is my net worth growing? How much did my investments actually return? Can I afford that vacation? Where is all my money going?

The Reports Manager must serve two audiences simultaneously. The first is the user who opens Ledger once a day, glances at a dashboard for thirty seconds, and closes it — reassured or alerted. The second is the user who sits down on a Sunday afternoon, explores their finances deeply, drills into categories, compares quarters, and emerges with genuine insight. The module must satisfy both — the glance and the deep dive — without forcing either user through the other's workflow.

Three design principles govern this module.

**Principle 1 — Accounting rigor, human language.** Every report is grounded in proper double-entry accounting. The Balance Sheet balances. The Cash Flow Statement reconciles. The Income Statement ties to the General Ledger. But the labels, explanations, and visual design speak in plain language. A user should never need to know the word "contra" to understand their own finances. Where accounting terminology is used (and it should be, for precision), contextual tooltips explain it in one sentence.

**Principle 2 — Time is the universal axis.** Almost every financial question is a question about time. How much did I spend *this month*? What was my net worth *a year ago*? How have my investments performed *since I bought them*? Every report in the system supports flexible time selection — a specific month, a custom date range, a quarter, a financial year, trailing 12 months, year-to-date, inception-to-date. The time selector is a persistent, global control that cascades across reports when the user navigates between them, unless the user explicitly overrides it for a specific report.

**Principle 3 — Progressive disclosure, not progressive confusion.** Every report starts with the simplest, most useful view. Details are available on demand — through drill-downs, expansions, and filters — but are never forced upon the user. The Balance Sheet starts as three numbers: Total Assets, Total Liabilities, Net Worth. One click expands Assets into sub-categories. Another click expands a sub-category into individual accounts. Another click on an account shows its transaction history. The user controls the depth. The system never overwhelms.

---

## Module Structure

The Reports Manager is organized into a **Dashboard** (the home screen — a curated, at-a-glance overview) and a **Reports Library** (the full collection of detailed reports, each accessible individually). The Dashboard draws its widgets from the same data engines that power the detailed reports, ensuring perfect consistency — the number on the dashboard always matches the number in the detailed report.

---

## Part 1: The Dashboard — Home Screen

The Dashboard is the first screen the user sees when they open Ledger. It is not a report — it is a mosaic of the most important signals from across all reports, arranged to answer the user's top questions in under thirty seconds.

---

### Dashboard Layout

The Dashboard is organized into a visual hierarchy of cards arranged in a responsive grid. The layout adapts to screen size but follows a consistent information hierarchy on desktop.

---

#### Row 1 — The Headline Numbers

This row occupies the full width and presents the three most important numbers in the user's financial life.

**Net Worth Card.** The largest card, positioned on the left, occupying approximately 40% of the row width. It displays the current net worth as a large, prominent number (for example, "₹47,23,890"). Below the number, a delta indicator shows the change from the previous period: "+₹1,82,340 (+4.0%) from last month" in green, or "-₹45,000 (-0.9%) from last month" in red. A small sparkline chart beneath the delta shows the net worth trend over the last 6 months, providing instant visual context — is the trend rising, flat, or declining? Clicking this card navigates to the detailed Net Worth Report.

**Monthly Cash Flow Card.** Positioned in the center, approximately 30% of the row width. It shows the current month's income minus expenses as a single number: "+₹32,500 surplus" in green or "-₹8,200 deficit" in red. Below, two smaller sub-numbers show Total Income and Total Expenses for the month. A small horizontal bar visualizes the ratio — income as a green bar, expenses as a red bar overlaid, making it instantly visible whether the user is living within their means. Clicking navigates to the Cash Flow Statement.

**Savings Rate Card.** Positioned on the right, approximately 30% of the row width. Displays the current month's savings rate as a percentage: "38%" with a gauge or radial progress indicator. The gauge is colored in zones — red below 10%, amber between 10% and 20%, green above 20% (these thresholds are configurable). Below the gauge, a one-line contextual note: "You're saving ₹32,500 of your ₹85,000 income this month." Clicking navigates to the Income & Expense Report.

---

#### Row 2 — Where the Money Goes

This row provides expense visibility — the single most requested feature in any personal finance tool.

**Expense Breakdown Card (60% width).** A horizontal bar chart or treemap showing the current month's expenses broken down by top-level category. Each category is color-coded consistently throughout the application: Dining Out in orange, Shopping in purple, Transportation in blue, Utilities in teal, Rent/Housing in brown, and so on. The chart shows the top 7–8 categories with all remaining categories grouped into "Other." Each bar or segment shows the category name, amount, and percentage of total expenses. Hovering reveals the sub-category breakdown. Clicking a category navigates to the Expense Analytics report filtered to that category.

**Expense Trend Card (40% width).** A line chart showing total monthly expenses for the last 6 months. Each month is a data point, and the line reveals the spending trajectory. If the current month is on track to exceed the previous month (extrapolated from the current run rate), a subtle projected line extends to month-end with a dashed style. Below the chart, a single insight line: "Your spending is trending 12% higher than your 3-month average" or "Your spending this month is the lowest in the last 6 months."

---

#### Row 3 — Assets and Investments

**Asset Allocation Card (50% width).** A donut chart showing the composition of the user's total assets: Cash & Bank Deposits, Equities, Mutual Funds, Fixed Deposits, Real Estate, Gold, PPF/EPF, and Other. Each segment is labeled with the asset class name, current value, and percentage of total assets. The center of the donut shows Total Assets. This gives the user an instant read on their diversification. Clicking navigates to the Asset Allocation Report.

**Investment Performance Card (50% width).** A summary card showing the user's total investment portfolio (equities + mutual funds + other market-linked assets). Key metrics displayed: Total Invested (cost basis), Current Value, Total Returns (absolute amount), Total Returns percentage, and an XIRR figure (the true annualized return accounting for the timing of each investment). A small bar chart below shows returns by asset class — equities, mutual funds, and others — so the user can see which asset classes are performing and which are lagging. Clicking navigates to the Investment Performance Report.

---

#### Row 4 — Liabilities and Goals

**Liability Summary Card (50% width).** A stacked bar showing total liabilities broken down by type: Home Loan, Car Loan, Personal Loan, Credit Card Outstanding, Education Loan, and Other. The total liability amount is shown prominently. Below, the monthly debt service (total EMIs + minimum card payments) is shown as an amount and as a percentage of monthly income — the debt-to-income ratio. A warning appears if this ratio exceeds 40%: "Your monthly debt payments are 43% of your income. Financial advisors recommend keeping this below 40%." Clicking navigates to the Liability & Debt Report.

**Goal Progress Card (50% width).** A compact view of the user's top 3–4 financial goals (from the Goal Manager). Each goal shows its name, a progress bar (current vs. target), percentage complete, and projected completion status (on track, ahead, behind). If a goal is behind schedule, it is highlighted in amber. If critically behind, red. A "View All Goals" link navigates to the Goal Manager. This card is hidden if the user has not set up any goals, and the space is reallocated to other cards.

---

#### Row 5 — Recent Activity

**Recent Transactions Card (100% width).** A compact table showing the last 10–15 transactions across all accounts, with columns for Date, Description, Category, Account, and Amount (color-coded green for credits, red for debits). Each row is clickable and navigates to the transaction detail in the Transaction Manager. A "View All Transactions" link leads to the full transaction ledger. This card serves as a quick sanity check — the user can glance at recent activity and spot anything unexpected.

---

### Dashboard Customization

The Dashboard layout described above is the default. Users can customize it in two ways.

**Card Visibility.** Each card can be shown or hidden via a Dashboard Settings panel (gear icon in the top-right corner). A user who doesn't invest in equities can hide the Investment Performance Card. A user who has no loans can hide the Liability Summary Card. Hidden cards free up space for remaining cards to expand.

**Period Selector.** A global period selector in the Dashboard header lets the user switch the time context of all flow-based cards (expense breakdown, cash flow, savings rate, expense trend) between "This Month," "Last Month," "This Quarter," "This Financial Year," and "Last 12 Months." Stock-based cards (net worth, asset allocation, holdings) always show the current snapshot but include the delta relative to the selected period's start.

---

## Part 2: Balance Sheet

The Balance Sheet is the foundational accounting report — a snapshot of everything the user owns, everything they owe, and the difference between them, at a specific point in time. In accounting terms: Assets = Liabilities + Equity (where Equity, in personal finance, is effectively Net Worth plus the cumulative surplus/deficit from income and expenses).

---

### Report Layout

**Report Header.** Title: "Balance Sheet" with subtitle: "As at [Date]." The date defaults to today but is selectable via a date picker — the user can generate a balance sheet as at any historical date for which data exists.

**Comparison Mode.** A toggle allows the user to compare two balance sheets side-by-side: "As at [Date 1]" versus "As at [Date 2]." When comparison mode is active, a third column shows the change (absolute and percentage) for each line item. This is extraordinarily useful for tracking financial progress — comparing December 31 of the current year with December 31 of the previous year reveals the full-year financial trajectory.

---

### Section 1 — Assets

The Assets section is presented as an expandable tree structure. At the top level, it shows the total: "Total Assets: ₹52,18,400." Expanding this reveals the major asset groups.

**Current Assets** includes Cash in Hand (physical cash the user tracks), Bank Accounts (each account listed individually with its current balance — for example, HDFC Savings ₹3,42,100, ICICI Savings ₹1,28,500, SBI Current ₹85,200), and Short-Term Deposits (FDs maturing within 12 months, liquid funds).

**Investments** includes Equities (expandable to show individual stocks with quantity, average cost, current value, and unrealized P&L for each), Mutual Funds (expandable to show individual funds with units, cost, current value, and unrealized P&L), Exchange-Traded Funds, Sovereign Gold Bonds, National Pension System (NPS), Public Provident Fund (PPF), Employee Provident Fund (EPF), Fixed Deposits (maturing beyond 12 months), Bonds and Debentures, and Other Investments. For market-linked investments (equities, mutual funds, ETFs), the balance sheet shows the current market value — not the cost basis. The cost basis is shown as a secondary number in parentheses, and the unrealized gain/loss is shown as a delta. If market prices are not updated (the system does not have a live price feed at launch), the last known price from the most recent import is used, and the "as at" date for prices is displayed: "Market values as at [last import date]."

**Derivatives (Open Positions)** includes Futures positions (showing margin blocked and unrealized MTM P&L) and Options positions bought (showing premium paid as cost basis and current premium as market value). Options positions written (sold) appear under Liabilities since they represent obligations.

**Fixed Assets** includes Real Estate (property values as entered during onboarding — these are typically not updated frequently), Vehicles (depreciating assets — the system can optionally apply straight-line depreciation based on the purchase date and estimated useful life), Gold and Silver (physical holdings, valued at a user-entered rate or a rate from the last import), and Other Fixed Assets.

**Receivables** includes Loans Given to Others (if the user has lent money), Security Deposits (rental deposits, utility deposits), Tax Refunds Due (TDS receivable, advance tax refunds expected), and Other Receivables.

Each line item at every level of the tree shows the balance amount. Clicking on any account navigates to that account's ledger — the full transaction history for that account.

---

### Section 2 — Liabilities

**Secured Loans** includes Home Loan (each loan listed with outstanding principal — for example, SBI Home Loan ₹28,45,000), Vehicle Loan, and Loan Against Property / Loan Against Securities.

**Unsecured Loans** includes Personal Loan, Education Loan, and Loans from Friends/Family.

**Credit Card Liabilities** lists each credit card with its current outstanding balance: HDFC Regalia ₹42,300, SBI SimplyCLICK ₹18,700.

**Derivatives (Written Positions)** includes Options sold/written (showing the current obligation — premium received minus current buyback cost).

**Other Liabilities** includes Tax Payable (estimated tax liability, advance tax due), Unpaid Bills, and Other Payables.

Each loan shows its outstanding balance. If the loan was set up with terms during onboarding (interest rate, tenure, EMI amount), a small info icon reveals: original loan amount, interest rate, remaining tenure, and estimated payoff date.

---

### Section 3 — Net Worth (Equity)

Net Worth is calculated as Total Assets minus Total Liabilities. This section shows the net worth figure prominently, along with the components that built it: Opening Net Worth (the net worth at the start of the user's Ledger history, established during onboarding), the Cumulative Surplus/Deficit (total income minus total expenses since inception — this is the retained earnings equivalent in personal accounting), and Net Unrealized Gains/Losses on investments.

The accounting identity is displayed at the bottom of the Balance Sheet: "Assets (₹52,18,400) = Liabilities (₹29,06,000) + Net Worth (₹23,12,400) ✓." The checkmark confirms the balance sheet balances. If it doesn't (which would indicate a system bug), an error is displayed prominently.

---

### Balance Sheet — Special Considerations

**Real estate valuation.** Property values are inherently estimates. The balance sheet marks these with an asterisk and a note: "Property values are based on your estimates and are not independently verified. Last updated: [date]." The user can update property values at any time from the account settings.

**EPF/PPF valuation.** These accounts grow through contributions and interest, but the user may not have transaction-level detail for interest credits (especially EPF, where the employer handles contributions). The balance sheet shows the last known balance, and a note indicates the source: "Balance as per your last update on [date]."

**Depreciation of assets.** If the user has entered vehicles or equipment with purchase values, the system can optionally compute depreciation. This is a setting: "Apply depreciation to fixed assets? (Default: No)." If enabled, the system uses straight-line depreciation based on asset type defaults (vehicle: 15% per year, electronics: 25% per year) and adjusts the Balance Sheet value accordingly. The depreciation expense appears in the Income & Expense Statement.

---

## Part 3: Income & Expense Statement

This is the personal finance equivalent of a corporate Profit & Loss (P&L) statement. It shows all income earned and all expenses incurred over a period, with the net result being the surplus (savings) or deficit (overspend) for that period.

---

### Report Header

Title: "Income & Expense Statement" with subtitle: "For the period [Start Date] to [End Date]." The period is selectable: This Month, Last Month, This Quarter, This Financial Year (April to March), Last Financial Year, Last 12 Months, Year to Date, Custom Range.

**Comparison Mode.** The user can compare two periods side-by-side — for example, "January 2026" vs. "December 2025," or "Q3 FY26" vs. "Q3 FY25." The comparison view adds a Change column showing the absolute and percentage change for each line item.

---

### Section 1 — Income

Income is organized into categories that map to the user's Chart of Accounts income hierarchy.

**Earned Income** includes Salary/Wages (the primary income for most salaried users — showing gross salary if salary slip parsing is available, or the net credit amount from bank import), Freelance/Consulting Income, Business Income, and Bonus/Commission.

**Investment Income** includes Dividends (from equities and mutual funds), Interest Income (from bank accounts, FDs, bonds), Rental Income, Capital Gains — Short Term (realized gains from equity sales under 12 months, debt fund redemptions, etc.), Capital Gains — Long Term (realized gains from equity sales over 12 months), and Trading Income (further broken into Intraday Equity — speculative, and F&O — non-speculative, maintaining the tax-relevant distinction).

**Other Income** includes Gifts Received, Cashback and Rewards Redeemed, Insurance Claims Received, Tax Refunds Received, and Miscellaneous Income.

Each income line shows the total for the period. Clicking any line expands to show the individual transactions that compose it — for example, clicking "Dividends: ₹8,420" reveals the individual dividend credits with dates and source companies.

**Total Income** is shown as a subtotal line with emphasis.

---

### Section 2 — Expenses

Expenses are organized into a hierarchy that balances granularity with readability. The top-level categories are broad enough to be meaningful at a glance, and each is expandable for detail.

**Housing** includes Rent, Home Loan EMI — Interest Portion (the interest component of EMIs — the principal portion is not an expense, it's a liability reduction), Maintenance/Society Charges, Property Tax, Home Insurance, and Home Repairs & Improvement.

**Transportation** includes Fuel, Vehicle EMI — Interest Portion, Vehicle Insurance, Vehicle Maintenance, Cab/Ride Hailing (Uber, Ola), Public Transport, and Parking & Tolls.

**Food & Dining** includes Groceries, Dining Out & Food Delivery, and Beverages (Coffee, Tea, etc.).

**Utilities & Bills** includes Electricity, Water, Gas, Internet & Broadband, Mobile Phone, DTH/Streaming Subscriptions, and Other Utilities.

**Healthcare** includes Health Insurance Premiums, Doctor Consultations, Medicines & Pharmacy, Hospital/Lab Bills, and Dental/Vision Care.

**Insurance** (non-health, non-vehicle) includes Life Insurance Premiums, Term Insurance Premiums, and Other Insurance.

**Education** includes School/College Fees, Courses & Certifications, Books & Learning Materials, and Education Loan EMI — Interest Portion.

**Personal & Lifestyle** includes Clothing & Accessories, Personal Care & Grooming, Fitness & Gym, Entertainment (Movies, Events, etc.), Hobbies, and Gifts Given.

**Financial Charges** includes Bank Charges, Credit Card Fees & Interest, Brokerage & Trading Charges (STT, exchange charges, GST on brokerage), Demat Account Charges, Loan Processing Fees, and Late Payment Penalties.

**Taxes** includes Income Tax (advance tax, self-assessment tax — not TDS, which is captured at source), Professional Tax, and GST (for business owners).

**Investments — Losses** includes Capital Losses — Short Term, Capital Losses — Long Term, Trading Losses — Intraday (Speculative), and Trading Losses — F&O (Non-Speculative). These are separated from regular expenses because they have distinct tax treatment — capital losses can be carried forward and set off against future capital gains.

**Miscellaneous** includes Charity & Donations, Cash Withdrawals (not categorized further — the actual expense happens when cash is spent, and if the user doesn't track cash spending, ATM withdrawals appear here as a catch-all), and Other/Uncategorized.

Each expense line shows the total for the period. Clicking any line expands to show sub-categories or individual transactions. 

**Total Expenses** is shown as a subtotal line.

---

### Section 3 — Net Surplus / Deficit

**Net Surplus (Savings) = Total Income − Total Expenses.** This line is shown with visual emphasis — green if positive (surplus), red if negative (deficit). Below it, the savings rate is shown as a percentage: Savings Rate = Net Surplus / Total Income × 100.

A contextual annotation provides perspective. If the savings rate is above 30%: "Strong savings rate. You're setting aside nearly a third of your income." If between 15% and 30%: "Healthy savings rate. You're consistently saving a meaningful portion of your income." If between 0% and 15%: "Your savings are positive but modest. Reviewing discretionary spending categories could help increase this." If negative: "You spent more than you earned this period. This is sustainable short-term (using savings) but worth addressing if it's a recurring pattern."

---

### Visualization

Below the tabular statement, two chart options are available, toggleable by the user.

**Waterfall Chart.** A waterfall chart starting from Total Income, subtracting each major expense category as a descending bar, and arriving at Net Surplus. This visual makes it instantly clear which categories consume the most income.

**Trend Chart.** A multi-line chart showing Income (green line), Expenses (red line), and Surplus (blue line or shaded area between the two lines) over the last 6 or 12 months. This reveals seasonal patterns — for example, higher spending in festival months (October/November) or higher income in months with bonuses (March/September).

---

## Part 4: Cash Flow Statement

The Cash Flow Statement answers a different question than the Income & Expense Statement. While the I&E statement shows whether the user is living within their means, the Cash Flow Statement shows where the money actually moved — including non-income, non-expense movements like loan repayments, investment purchases, and inter-account transfers that don't appear on the I&E statement.

In corporate accounting, the Cash Flow Statement has three sections: Operating, Investing, and Financing. The personal finance equivalent maintains this structure but with personal-finance labels.

---

### Report Header

Title: "Cash Flow Statement" with subtitle: "For the period [Start Date] to [End Date]." Same period selector as the I&E Statement.

---

### Section 1 — Cash Flow from Daily Life (Operating Activities)

This section captures the net cash generated or consumed by the user's regular income and expenses — essentially, the same data as the I&E Statement but organized by cash movement.

**Cash Inflows** include salary received, freelance/business income received, interest received, dividends received, rental income received, tax refunds received, insurance claims received, and other income.

**Cash Outflows** include all expense categories (housing, transportation, food, utilities, healthcare, etc.), taxes paid, and insurance premiums paid.

**Net Cash from Daily Life** equals total inflows minus total outflows. This should approximately equal the Net Surplus from the I&E Statement, with differences arising from accrual adjustments (if any).

---

### Section 2 — Cash Flow from Investments (Investing Activities)

**Cash Outflows (Investments Made)** include equity purchases (buying stocks — shows total deployed in equity markets during the period), mutual fund purchases (lump sum + SIP), fixed deposit creation, PPF/NPS contributions, gold/SGB purchases, real estate purchase/down payment, and other investment purchases.

**Cash Inflows (Investment Proceeds)** include equity sales proceeds, mutual fund redemption proceeds, fixed deposit maturity proceeds, bond maturity/coupon received, and real estate sale proceeds.

**Net Cash from Investments.** This is typically negative for an accumulating investor (deploying more cash into investments than receiving back). A positive number means the user is liquidating investments — which could be planned (retirement withdrawal) or concerning (distress selling). No judgment is applied; the number speaks for itself.

---

### Section 3 — Cash Flow from Financing (Financing Activities)

**Cash Inflows** include loan disbursements received (new loans taken), credit card net borrowing increase (if the outstanding balance grew during the period — meaning the user financed spending with credit), and loans received from friends/family.

**Cash Outflows** include loan EMI payments — principal portion only (interest is already in Operating Activities), credit card bill payments (total payments made to card issuers), loan prepayments or foreclosure, and loans repaid to friends/family.

**Net Cash from Financing.** This is typically negative for a user who is repaying debt (more outflow for principal repayment than inflow from new borrowing). A positive number means the user took on more debt than they repaid — worth noting but not necessarily bad (for example, taking a home loan).

---

### Section 4 — Summary

**Net Change in Cash & Bank Balances = Net Cash from Daily Life + Net Cash from Investments + Net Cash from Financing.**

This is followed by: Opening Cash & Bank Balance (at the start of the period), the Net Change computed above, and the Closing Cash & Bank Balance (at the end of the period). The closing balance here must match the total of all cash and bank account balances on the Balance Sheet as at the period end date. If it doesn't, a reconciliation difference is shown and flagged.

The Cash Flow Statement is powerful because it reveals hidden dynamics. A user might have a positive surplus on their I&E Statement (income exceeds expenses) yet still see their bank balance decline — because they invested heavily or made large loan prepayments. Without the Cash Flow Statement, this would be confusing. With it, the full picture is clear.

---

### Visualization

**Sankey Diagram.** A Sankey (flow) diagram showing income sources on the left, flowing through the user's accounts in the center, and splitting into expenses, investments, and debt repayments on the right. The width of each flow is proportional to the amount. This is one of the most visually compelling ways to show the complete money flow.

**Stacked Bar Chart.** Monthly bars split into the three cash flow sections (Operating, Investing, Financing), with the net cash change shown as a line overlay. This reveals monthly patterns in investment activity and debt repayment.

---

## Part 5: Net Worth Report

While the Balance Sheet shows net worth at a single point in time, the Net Worth Report shows the trajectory — how net worth has evolved over time and what drove the changes.

---

### Net Worth Trend

**Primary Visualization.** An area chart showing net worth over time. The x-axis is time (monthly data points from the user's earliest data to present). The y-axis is net worth in rupees. The area under the curve is filled with a gradient — green when net worth is positive, transitioning to red if it goes negative (unlikely for most users, but possible for those with high leverage).

Above the chart, headline numbers show: Current Net Worth, Net Worth at start of the selected range, Change (absolute and percentage), and Compound Annual Growth Rate (CAGR) if the range spans more than a year.

**Decomposition Visualization.** A stacked area chart showing the composition of net worth over time — Assets stacked in positive territory and Liabilities stacked in negative territory, with Net Worth as the line between them. This reveals whether net worth growth is driven by asset appreciation, liability reduction, or both.

---

### Net Worth Attribution — What Drove the Change

For any selected period, the system computes and displays the factors that contributed to the net worth change.

**Savings Contribution.** The net surplus from income minus expenses. This is the portion of net worth growth driven by the user's active saving behavior. For most salaried individuals in their accumulation years, this is the primary driver.

**Investment Returns — Realized.** Capital gains, dividends, and interest earned on investments. This is the portion of net worth growth driven by investment performance that has been crystallized.

**Investment Returns — Unrealized.** The change in market value of investments beyond what was invested. If the user's equity portfolio appreciated by ₹1,50,000 during the period without any sales, this ₹1,50,000 is unrealized investment return. It contributed to net worth growth but hasn't been converted to cash.

**Asset Revaluation.** Changes in the estimated value of non-market assets like real estate (if the user updated their property value estimate during the period).

**Debt Reduction.** The reduction in total liabilities. If the user repaid ₹2,00,000 in loan principal, net worth grew by ₹2,00,000 from this factor alone (the asset side — bank balance — decreased, but the liability side decreased by the same amount, netting to zero; the net worth increase comes from the fact that the principal was repaid from savings, which are already captured in the Savings Contribution above). To avoid double-counting, the attribution waterfall is carefully constructed: Savings Contribution captures the full surplus, and Debt Reduction shows how much of that surplus went to reducing liabilities rather than accumulating assets. The waterfall separates the two for clarity.

**Visualization:** A waterfall chart showing: Starting Net Worth → +Savings → +Realized Investment Returns → +Unrealized Investment Returns → +Asset Revaluation → −New Debt Taken → Ending Net Worth. Each bar is colored by type, making it visually clear what drove the change.

---

### Net Worth Milestones

The report highlights milestones the user has crossed or is approaching. Examples include crossing ₹10,00,000 net worth, crossing ₹25,00,000, crossing ₹50,00,000, crossing ₹1,00,00,000 (the "crore milestone"), first month where investment income exceeded a month's expenses, and the date when the user became "debt-free" (total liabilities reached zero), if applicable.

Milestones are shown as markers on the net worth trend chart and listed in a sidebar with dates. Upcoming milestones show the projected date based on the current trajectory.

---

## Part 6: Expense Analytics

This is the deepest, most interactive report in the system — designed for the user who wants to truly understand where their money goes.

---

### Category Deep Dive

**Treemap View.** The default view is a treemap where each rectangle represents an expense category, sized by amount and colored by the category's assigned color. Larger rectangles are bigger expenses. Clicking a category zooms into its sub-categories (for example, clicking "Food & Dining" reveals "Groceries," "Dining Out," "Beverages" as sub-rectangles). Clicking a sub-category reveals individual transactions.

**Table View.** A sortable table with columns: Category, Amount, Percentage of Total, Transaction Count, Average Transaction Size, Change vs. Previous Period (in both amount and percentage). Sorting by "Change vs. Previous Period" instantly highlights categories where spending has increased or decreased significantly.

---

### Merchant Analysis

**Top Merchants.** A ranked list of the user's top 20 merchants by total spending during the selected period. Each row shows: Merchant Name, Total Spent, Transaction Count, Average Transaction, Category, and Change vs. Previous Period.

This view is often more actionable than category analysis. Knowing that "Dining Out" is ₹12,000 is useful; knowing that ₹7,400 of that went to Swiggy and ₹3,200 to Zomato is more actionable. The user might realize they're ordering delivery too frequently and can cook more.

**Merchant Trend.** Clicking on any merchant shows a monthly spending trend for that merchant, revealing patterns like increasing frequency or growing order sizes.

---

### Time-Based Patterns

**Day-of-Week Analysis.** A bar chart showing average daily spending by day of the week. Many users will see higher spending on weekends (dining out, shopping, entertainment). This pattern awareness can be valuable.

**Day-of-Month Analysis.** A bar chart showing spending by day of the month. Salary day often triggers a spending spike. This can reveal timing patterns the user may want to address.

**Monthly Comparison.** A grouped bar chart showing spending by category for each month in the selected range (for example, 6 months). Each month has a cluster of bars, one per category. This reveals seasonal patterns and anomalies.

---

### Recurring vs. Discretionary

The system classifies expenses as **Recurring** (fixed, predictable: rent, EMIs, subscriptions, insurance premiums, utility bills) or **Discretionary** (variable, choice-driven: dining out, shopping, entertainment, travel). This classification is initially determined by transaction patterns (same payee, similar amount, monthly frequency indicates recurring) and refined by user corrections.

A split view shows: Total Recurring Expenses (with a list of each recurring item, its amount, and frequency), Total Discretionary Expenses (with category breakdown), and the ratio between them: "62% of your spending is recurring, 38% is discretionary."

This is important for financial planning. Recurring expenses are the "floor" — the minimum the user must earn to sustain their lifestyle. Discretionary expenses are the lever — the variable that can be adjusted to increase savings.

---

### Anomaly Detection

The system identifies spending anomalies without AI — using simple statistical methods. For each category, the system computes the trailing 3-month average. Any category where the current month's spending exceeds the average by more than 50% is flagged as an anomaly: "Shopping spending (₹18,400) is 67% higher than your 3-month average (₹11,020)."

Similarly, unusually large individual transactions are flagged: "Your ₹45,000 transaction at [Merchant] on [Date] is significantly larger than your typical transactions."

Anomalies are shown in a dedicated "Alerts" section at the top of the Expense Analytics report.

---

## Part 7: Investment Performance Report

This report provides a comprehensive view of the user's investment portfolio — not just the current snapshot (which the Balance Sheet already shows) but the performance over time.

---

### Portfolio Overview

**Total Portfolio Value.** The current total market value of all investments. Below it: Total Amount Invested (cost basis), Total Returns (Value minus Cost), Total Returns percentage, and XIRR (the true annualized return accounting for the timing and magnitude of every cash flow — investments, withdrawals, dividends). XIRR is the gold standard for measuring investment performance because it accounts for the fact that not all money was invested at the same time. A tooltip explains XIRR in plain language: "XIRR is your true annualized return, accounting for when you invested each amount. It's more accurate than simple percentage returns for ongoing investments like SIPs."

---

### Asset Class Performance

A table showing each asset class and its performance: Asset Class, Amount Invested, Current Value, Absolute Returns, XIRR, and Allocation Percentage. Asset classes include Equities (Direct Stocks), Equity Mutual Funds, Debt Mutual Funds, Hybrid Mutual Funds, Fixed Deposits, PPF, EPF, NPS, Gold/SGB, and Others.

**Visualization.** A bubble chart where each bubble is an asset class, the x-axis is XIRR (return), the y-axis is allocation percentage, and the bubble size is the absolute value invested. This reveals at a glance which asset classes have the highest return and which have the highest allocation — and whether those align.

---

### Individual Security Performance

**Equity Holdings.** A table with one row per stock: Symbol, Quantity, Average Buy Price, Current Price, Invested Amount, Current Value, Unrealized P&L (amount and percentage), XIRR, Holding Period, and LTCG/STCG classification. Sortable by any column. Sorting by P&L percentage immediately shows the best and worst performers.

**Mutual Fund Holdings.** A table with one row per fund: Fund Name, AMC, Category (Large Cap, Mid Cap, Flexi Cap, Debt, etc.), Units, Average NAV, Current NAV, Invested Amount, Current Value, Unrealized P&L, XIRR, and SIP Active (Yes/No with monthly SIP amount if active).

For each holding, clicking reveals a detailed sub-report with transaction history (every buy and sell), NAV chart (if data is available from imports), and cost lot breakdown (showing each purchase lot with its date, quantity, cost, current value, gain/loss, and holding period — critical for tax planning, as the user can identify which lots to sell for optimal tax treatment).

---

### Realized Gains & Losses

A table showing all realized (booked) gains and losses during the selected period. Columns: Security/Fund Name, Buy Date, Sell Date, Holding Period, Buy Price, Sell Price, Quantity, Realized P&L, and Classification (STCG, LTCG, Speculative, Non-Speculative Business Income).

**Subtotals by classification:** Total STCG (for equity delivery), Total LTCG (for equity delivery), Total Speculative Income (intraday equity), Total Non-Speculative Business Income (F&O), Total MF STCG, Total MF LTCG, and Total Debt Fund Gains. These subtotals directly feed into the Tax Summary Report and help the user understand their tax liability from investments.

---

### Derivatives Performance Summary

For users who trade derivatives, a dedicated section shows the performance of their F&O activity.

**Futures Summary.** Total contracts traded, total realized P&L from futures, win rate (percentage of profitable trades), average profit per winning trade, average loss per losing trade, largest single gain, largest single loss, and total charges paid (brokerage + STT + GST).

**Options Summary.** Total contracts traded (separately for bought and written), total premium paid (for bought options), total premium received (for written options), total realized P&L, win rate, and total charges. For option buyers specifically: percentage of options that expired worthless (the "option buyer's pain metric" — most retail option buyers lose money, and this metric quantifies it).

**Monthly F&O P&L Trend.** A bar chart showing monthly net P&L from derivatives trading. This reveals whether the user's trading is consistently profitable, consistently loss-making, or volatile. A cumulative P&L line overlay shows the running total. If the cumulative line is trending downward, a note appears: "Your cumulative F&O P&L over the selected period is negative. This is common — most retail derivative traders lose money over time."

---

### Portfolio Diversification Analysis

**Current Allocation vs. Target.** If the user has set target allocations (during onboarding or in settings — for example, 60% equity, 20% debt, 10% gold, 10% cash), a comparison chart shows actual versus target. Deviations are highlighted: "Your equity allocation (72%) exceeds your target (60%). Consider rebalancing by deploying future savings into debt instruments."

**Concentration Risk.** The system flags concentration risks: if any single stock represents more than 15% of the total equity portfolio, if any single mutual fund represents more than 25% of the total MF portfolio, or if any single asset class represents more than 50% of total investments (excluding real estate, which is naturally concentrated). These are configurable thresholds, and the system explains each flag without being alarmist.

---

## Part 8: Liability & Debt Report

This report provides a comprehensive view of the user's debt situation — not just balances (which the Balance Sheet shows) but the dynamics of debt repayment and the cost of debt.

---

### Debt Summary

A summary card shows: Total Outstanding Debt (sum of all liabilities), Monthly Debt Service (total of all EMIs and minimum card payments), Debt-to-Income Ratio (monthly debt service divided by monthly income), Debt-to-Asset Ratio (total debt divided by total assets), and Interest Paid This Period (total interest expense across all loans and credit cards).

---

### Loan-by-Loan Detail

For each loan, the report shows a detailed card containing the lender name and loan type, original loan amount and disbursement date, interest rate (fixed or floating, and current rate if floating), original tenure and remaining tenure, EMI amount, total paid to date (cumulative EMIs), principal repaid to date and interest paid to date (the principal/interest split from all EMIs combined), outstanding principal, estimated payoff date (at current EMI), and prepayment impact calculator: "If you pay an additional ₹[X] per month, you will save ₹[Y] in interest and close the loan [Z] months earlier."

**Amortization Schedule.** Each loan has an expandable amortization schedule showing the month-by-month breakdown of future EMIs into principal and interest components. This is generated from the loan terms (principal, rate, tenure) using the standard reducing balance EMI formula. The schedule highlights the crossover point — the month where the principal component of the EMI exceeds the interest component for the first time.

**Loan Progress Visualization.** A stacked bar showing the original loan amount, with the "Principal Repaid" portion in green and the "Outstanding" portion in gray. The green portion grows over time, providing a visual sense of progress.

---

### Credit Card Analysis

For each credit card: outstanding balance, credit limit, utilization percentage (outstanding divided by limit — with a warning if above 30%, as high utilization can impact credit scores), last payment amount and date, minimum due for the current billing cycle, full payment due for the current billing cycle, interest charged in the current and previous billing cycles, and total interest paid since inception (if data is available from imported statements).

**Utilization Trend.** A line chart showing credit card utilization over time. Consistently high utilization (above 50%) is flagged with guidance.

**Credit Card Cost Analysis.** If the user carries a revolving balance (doesn't pay the full bill), the report calculates the effective annual cost of credit card debt, which is typically 36–42% per annum — far higher than any other form of consumer debt. The report shows this rate prominently: "Your HDFC Regalia card charges 3.5% per month (42% per annum) on outstanding balances. You paid ₹4,830 in interest over the last 3 months."

---

### Debt Freedom Projection

If the user has active debts, the report shows a projection: "At your current repayment rate, you will be completely debt-free by [Month, Year]." A timeline visualization shows each loan's projected closure date, color-coded and stacked chronologically.

For users with multiple loans, a "Debt Repayment Strategy" section shows two approaches. The **Avalanche Method** recommends paying off the highest-interest-rate debt first (mathematically optimal — minimizes total interest paid). The **Snowball Method** recommends paying off the smallest balance first (psychologically rewarding — provides quick wins). The system shows the projected total interest and debt-free date under each method, letting the user choose their preferred approach.

---

## Part 9: Tax Summary Report

This report is designed to help the user during tax filing season (typically June–July for Indian taxpayers). It aggregates all tax-relevant data from the year's transactions into a format that aligns with the Indian Income Tax Return (ITR) structure.

---

### Income Summary for Tax

**Salary Income.** Total salary received during the financial year. If salary slip parsing is available, the breakdown includes basic pay, HRA, special allowance, and other components.

**Income from House Property.** Rental income received, minus municipal taxes paid, minus 30% standard deduction (automatic under Indian tax law), minus home loan interest paid (subject to limits). Net taxable income from house property is computed.

**Income from Capital Gains.** STCG (taxed at 15% for equity, at slab rate for others), LTCG (taxed at 10% above ₹1,00,000 for equity, at 20% with indexation for others — noting that these rates may have changed with recent tax reforms). The report shows the gross gains, any available exemption, and the taxable gains for each category.

**Income from Business/Profession.** Intraday equity trading income (speculative), F&O trading income (non-speculative), freelance/consulting income, and any other business income. Relevant deductions and expenses against this income.

**Income from Other Sources.** Interest income (savings account, FD, bonds), dividend income, gifts received (above exemption limit), and any other income.

**Gross Total Income.** The sum of all heads of income.

---

### Deductions Summary (Chapter VI-A)

The report identifies and aggregates potential deductions from the user's transaction data. Under Section 80C (limit ₹1,50,000): PPF contributions, ELSS mutual fund investments, EPF contributions (employee share), life insurance premiums paid, home loan principal repaid, and tuition fees paid. Under Section 80D: health insurance premiums paid (self, family, and parents). Under Section 80TTA/80TTB: savings account interest income deduction (up to ₹10,000 for non-senior citizens under 80TTA). Under Section 24(b): home loan interest deduction. And any other detectable deductions.

The report shows the available deduction, the limit, and the utilized amount: "Section 80C: You've invested/paid ₹1,32,000 against a limit of ₹1,50,000. You can save additional tax by investing ₹18,000 more in eligible instruments before March 31."

---

### Tax Computation (Estimated)

The report estimates the user's tax liability under both the Old Tax Regime and the New Tax Regime, showing which one results in lower tax. This includes gross total income under each regime, applicable deductions under each regime (the new regime has limited deductions), taxable income, tax computed at applicable slab rates, health and education cess (4%), and total estimated tax liability.

**Old vs. New Regime Comparison.** A side-by-side comparison with the recommendation: "Based on your income and deductions, the [Old/New] Tax Regime results in lower tax by ₹[X]." A disclaimer notes that this is an estimate and the user should consult a tax professional for filing.

**TDS Already Paid.** The report aggregates TDS deducted (from salary, bank interest, and other sources) and shows the remaining tax payable or refund due: "Estimated tax liability: ₹2,45,000. TDS already deducted: ₹2,10,000. Estimated remaining tax payable: ₹35,000."

---

### Advance Tax Schedule

For users with significant non-salary income (capital gains, rental income, freelance income), the system shows the advance tax payment schedule (June 15, September 15, December 15, March 15) with the recommended installment amounts based on estimated total income.

---

## Part 10: Goal Progress Report

This report integrates with the Goal Manager and provides a financial progress view of each goal.

---

### Goal Dashboard

Each goal is shown as a card with: Goal Name, Target Amount, Current Progress (amount accumulated in tagged accounts), Progress Percentage (with a visual progress bar), Monthly Contribution (average over the last 3 months), Required Monthly Contribution (to reach the target by the deadline), Projected Completion Date (at current contribution rate), and Status (On Track in green, Slightly Behind in amber, Significantly Behind in red, Achieved in blue).

---

### Goal Detail View

Clicking on a goal reveals a detailed analysis. A projection chart shows two lines: the "Target Path" (a straight line from start to deadline showing the required accumulation trajectory) and the "Actual Path" (the actual accumulation of funds in tagged accounts over time). If the Actual Path is above the Target Path, the goal is ahead of schedule. If below, it's behind.

A contribution history table shows each contribution (SIP, lump sum, manual saving) to the goal's tagged accounts, with dates and amounts. The growth of the goal fund — both from contributions and from investment returns (if the goal fund is invested in market-linked instruments) — is shown separately, so the user can see how much of their progress is from saving and how much is from returns.

If the goal is behind schedule, the system calculates and displays the recovery action needed: "To get back on track, you need to contribute ₹[X] per month for the next [Y] months, compared to your current average of ₹[Z] per month."

---

## Part 11: General Ledger & Account Statement

These are the detailed, transaction-level reports for users who want to see every entry for a specific account.

---

### General Ledger

The General Ledger shows every journal entry in the system for a selected period, across all accounts. It is the most detailed report and is primarily useful for auditing and troubleshooting.

Columns: Entry Number (JE-2026-001234), Date, Narration, Account Name, Debit Amount, Credit Amount, and Running Balance for each account. The ledger is searchable (by narration, account name, amount) and filterable (by date range, account, entry type).

---

### Account Statement

An Account Statement shows all transactions for a single selected account. It mimics the format of a bank passbook or statement — familiar and intuitive.

The user selects an account from a dropdown (organized by the Chart of Accounts hierarchy) and a date range. The statement shows: Account Name, Statement Period, Opening Balance (at start of period), a transaction list (Date, Description/Narration, Debit, Credit, Running Balance), and Closing Balance (at end of period).

For bank accounts, this reconstructed statement can be compared against the original bank statement to verify completeness. For expense accounts, this becomes a spending log for that category. For investment accounts, this becomes a transaction history showing every buy, sell, dividend, and charge.

---

## Part 12: Trial Balance

The Trial Balance is a verification report — it confirms that the double-entry system is intact. It lists every account in the Chart of Accounts with its net debit or credit balance. The total of all debit balances must equal the total of all credit balances. If they don't, there is a system error.

The Trial Balance is not a commonly viewed report for most users, but it is essential for system integrity. It is available in the Reports Library under an "Accounting Reports" section. Power users and accounting-literate users may check it periodically.

Columns: Account Code, Account Name, Account Type (Asset/Liability/Equity/Income/Expense), Debit Balance, Credit Balance. The final row shows totals, with a green checkmark if they balance and a red warning if they don't.

---

## Part 13: Custom Reports & Report Builder

For advanced users who want reports the system doesn't provide out of the box, a Report Builder allows the creation of custom reports.

**Report Builder Interface.** The user selects the data source (which accounts or account groups to include), the time period, the grouping dimension (by category, by month, by counterparty, by transaction type), the metric (sum, count, average, minimum, maximum), filters (amount range, specific counterparties, specific tags), and the output format (table, bar chart, line chart, pie chart).

For example, a user could build a custom report showing "Monthly spending at restaurants in the last 12 months" by selecting the Dining Out expense account, grouping by month, using sum as the metric, and choosing a bar chart output. Or "All transactions above ₹50,000 in the last financial year" by selecting all accounts, filtering for amount > ₹50,000, and choosing a table output.

Custom reports can be saved and pinned to the Dashboard as additional cards.

---

## Part 14: Report Export & Sharing

All reports can be exported in multiple formats.

**PDF Export.** A formatted, print-ready PDF with the report title, date, the user's name, and the report content including charts rendered as images. Suitable for filing, sharing with a financial advisor, or printing for personal records.

**Excel Export.** The raw data underlying the report, in a structured Excel file. Suitable for users who want to do their own analysis, create custom charts, or integrate with other tools. All numerical data is exported as numbers (not formatted text), making it ready for Excel formulas and pivot tables.

**CSV Export.** Plain text export for maximum compatibility.

**Image Export.** Individual charts can be exported as PNG images for use in presentations or personal records.

Reports are generated and exported entirely on the client side (or via the user's local server). No report data passes through any external server. The export functionality works offline.

---

## Part 15: Report Scheduling & Notifications

Users can configure automated report generation on a schedule.

**Monthly Financial Summary.** On the 1st of each month, the system generates a summary of the previous month: income, expenses, savings rate, net worth change, investment returns, and key anomalies. This summary is available within the app as a notification and can optionally be exported as a PDF to a local folder.

**Quarterly Review Prompt.** At the end of each quarter, the system prompts the user to review their quarterly performance with a pre-generated quarterly report comparing the quarter's actual performance to any goals or budgets.

**Annual Financial Report.** At the end of the financial year (March 31), the system generates a comprehensive annual report covering all major areas: income and expense summary, net worth growth, investment performance, debt reduction progress, goal progress, and tax summary. This serves as the user's personal annual financial review.

---

## Part 16: Report Computation Engine — Technical Architecture

All reports are computed from the same underlying transaction and journal entry data. The computation engine sits between the raw data store and the report presentation layer.

---

### Balance Computation

Account balances at any point in time are computed by summing all debit and credit entries for the account up to (and including) the specified date, starting from the opening balance. For asset and expense accounts, the balance is the sum of debits minus the sum of credits. For liability, equity, and income accounts, the balance is the sum of credits minus the sum of debits.

**Optimization.** For performance, the system maintains pre-computed monthly closing balances for each account. To compute a balance at any date within a month, the system takes the previous month-end closing balance and applies only the transactions from the current month up to the specified date. This avoids re-summing the entire transaction history for every report.

Monthly closing balances are recomputed whenever transactions are committed, edited, or voided for the affected month and all subsequent months. This ensures that historical reports remain accurate even when past data is corrected.

---

### XIRR Computation

XIRR (Extended Internal Rate of Return) is computed using the Newton-Raphson method on the series of cash flows for the investment account. Cash flows include each investment (negative cash flow), each withdrawal/redemption (positive cash flow), and the current portfolio value as a terminal positive cash flow on the current date.

The XIRR computation is available at the individual security level, the asset class level, and the total portfolio level. Each level aggregates the cash flows of its constituents.

---

### Period Comparisons

When the user selects a comparison mode (current month vs. previous month, or this quarter vs. same quarter last year), the engine computes both periods independently and then produces the delta (absolute change and percentage change) for each line item. Zero-division scenarios (when the prior period value is zero and the current period is non-zero) are handled gracefully — the change is shown as "New" rather than an infinity percentage.

---

### Caching and Refresh

Reports are cached after first computation for the selected parameters (account, period, grouping). The cache is invalidated when new transactions are committed, existing transactions are edited or voided, accounts are created, renamed, or merged, or the user changes any configuration that affects report computation (like category mappings or depreciation settings). When the cache is invalid, the report is recomputed on next access. For frequently accessed reports (the Dashboard), background recomputation is triggered immediately after a transaction commit, so the user sees updated numbers without waiting.

---

## Part 17: Data Model Requirements for Reports

---

### Monthly Account Snapshot

Account ID, year-month, opening balance, total debits during the month, total credits during the month, closing balance, transaction count, and last computed timestamp. This table is the primary performance optimization for balance-at-date queries.

---

### Report Configuration (User-Saved Reports)

Report ID (UUID), user ID, report name, report type (Balance Sheet, I&E, Cash Flow, Custom, etc.), parameters (JSON containing period, comparison settings, filters, grouping), is pinned to dashboard (boolean), dashboard position (if pinned), last accessed timestamp, and creation timestamp.

---

### Report Schedule

Schedule ID, user ID, report type, frequency (Monthly, Quarterly, Annually), trigger day (for example, 1st of month), export format (PDF, Excel), export destination (in-app notification, local folder path), is active (boolean), last triggered timestamp, and next trigger timestamp.

---

### Milestone Record

Milestone ID, user ID, milestone type (Net Worth Threshold, Debt Free, Investment Income Exceeds Expenses, etc.), milestone value (the threshold amount or condition), date achieved, is notified (boolean, whether the user has been shown this milestone), and creation timestamp.

---

This completes the Reports Manager specification. The module transforms raw ledger data into actionable financial intelligence across every dimension that matters — spending, saving, investing, borrowing, and tax planning. The implementation can be phased: Phase 1 delivers the Dashboard, Balance Sheet, Income & Expense Statement, and Expense Analytics. Phase 2 adds Net Worth Report, Investment Performance, Cash Flow Statement, and Account Statements. Phase 3 adds Tax Summary, Liability Analysis, Goal Progress integration, Custom Report Builder, and Report Scheduling.