# Ledger — Onboarding UX Specification

## Product Introduction

Ledger is a personal and household finance application built on the principles of double-entry accounting. It gives individuals and families complete, auditable control over their financial records — without requiring accounting expertise. Ledger runs locally by default with no external services required, ensuring your financial data stays private and under your control.

The onboarding experience is the user's first interaction with Ledger. Its purpose is to transform what could be an intimidating setup process (double-entry accounting, chart of accounts, opening balances) into a guided, approachable, and even enjoyable experience. By the end of onboarding, the user should have a fully functional ledger with real accounts and balances — ready to record their first transaction.

### Design Principles for Onboarding

**Progressive disclosure.** Never show the user the full complexity of double-entry accounting upfront. Reveal concepts only when the user needs them, and always in plain language first.

**Sensible defaults with escape hatches.** Every step should have a smart default that works for 80% of users. Advanced users can customize, but no one should be forced to make decisions they don't understand yet.

**Momentum over completeness.** The onboarding should feel fast. Users can always change settings and add accounts later. The goal is to get them to a working ledger, not a perfect one.

**Trust through transparency.** Show the user what Ledger is doing with their data at every step. No hidden accounts, no mystery categories. Everything is visible and editable.

---

## Onboarding Flow Overview

The onboarding consists of seven steps, presented as a linear flow with a progress indicator. Users can navigate back to previous steps but must complete required fields before advancing. The entire flow should take 3–5 minutes for a user who accepts defaults, or 10–15 minutes for a user who customizes everything.

**Step sequence:**

Step 1 → Welcome & Value Proposition
Step 2 → Profile & Preferences
Step 3 → Choose Your Template
Step 4 → Customize Your Accounts
Step 5 → Set Opening Balances
Step 6 → Import Existing Data (Optional)
Step 7 → Review & Get Started

---

## Step 1: Welcome & Value Proposition

### Purpose
Set the emotional tone. Reassure the user that Ledger is powerful but approachable. Establish what makes it different from typical budgeting apps.

### Screen Layout

**Top section — Full-width hero area**

A clean illustration or animation showing a simple ledger book transforming into a modern digital interface. The visual language should feel warm, precise, and calm — not corporate, not playful. Think: a well-organized desk, not a cartoon piggy bank.

**Center — Headline and supporting copy**

> **Headline:** "Your finances, in perfect balance."
>
> **Subheadline:** "Ledger gives you the clarity of professional accounting tools with the simplicity of a personal finance app. Every dollar is tracked, every transaction balanced, every answer at your fingertips."

**Below — Three value pillars, displayed as a horizontal row of cards**

Each card has an icon, a short title, and one sentence of description.

Card 1 — Icon: a balanced scale
> **"Double-Entry, Zero Confusion"**
> "Every transaction is automatically balanced. You'll always know exactly where your money went — and where it came from."

Card 2 — Icon: a shield or lock
> **"Your Data, Your Device"**
> "Ledger runs locally on your machine. No cloud accounts, no data harvesting, no subscriptions. Your financial life stays private."

Card 3 — Icon: a sprouting seedling
> **"Start Simple, Grow With You"**
> "Begin with a template that fits your life. Add complexity only when you need it. Ledger adapts to you, not the other way around."

**Bottom — Primary action**

A single prominent button, center-aligned:

> **[ Get Started → ]**

Below the button, a subtle text link:

> "Already have a Ledger backup? **Restore from file**"

### Interactions
- Clicking "Get Started" transitions to Step 2 with a smooth slide-left animation.
- Clicking "Restore from file" opens a system file picker for `.ledger` or `.db` backup files, bypassing onboarding entirely if the restore succeeds.
- No back button on this step (it is the entry point).

### Visual Notes
- Background: clean white or very light warm gray.
- No navigation chrome on this screen. Full immersion.
- The progress indicator (a segmented bar showing steps 1–7) appears at the very top, with Step 1 highlighted. It is subtle — thin, not dominant.

---

## Step 2: Profile & Preferences

### Purpose
Capture the minimal information needed to configure the ledger correctly: who is using it, what currency they operate in, and their preferred date and number formats. This step also determines whether the ledger is for an individual or a household, which affects account templates in Step 3.

### Screen Layout

**Progress bar** — Step 2 of 7 highlighted.

**Section header**

> **"Let's set up your ledger."**
>
> "These basics help Ledger display your finances the way you expect. You can change any of these later in Settings."

**Form fields — Stacked vertically, single column, generous spacing**

**Field 1: Ledger Name**
- Input type: Text field
- Placeholder text: "e.g., My Finances, The Johnson Family, Household Budget"
- Default value: Empty
- Required: Yes
- Validation: 1–60 characters, no special characters except spaces, hyphens, and apostrophes
- Helper text beneath field: "This is just a label for your ledger. You can have multiple ledgers later."

**Field 2: Ledger Type**
- Input type: Segmented toggle (two options, side by side)
- Options: **"Individual"** | **"Household"**
- Default: "Individual" selected
- No helper text needed — the selection changes the visual:
  - If "Individual" is selected, a subtle single-person silhouette icon appears beside it.
  - If "Household" is selected, a multi-person silhouette appears, and a new sub-field fades in below.

**Field 2a: Household Members (conditional — visible only when "Household" is selected)**
- Input type: Tag input / chip input
- Placeholder: "Add a family member name and press Enter"
- Behavior: User types a name, presses Enter, and a styled chip/tag appears. Each chip has an × to remove. Minimum 2 members required when Household is selected.
- Helper text: "These names help you track who spent what. You can add or remove members anytime."

**Field 3: Primary Currency**
- Input type: Searchable dropdown
- Default value: Auto-detected from system locale (e.g., "USD — US Dollar" for en-US locale, "INR — Indian Rupee" for en-IN)
- List includes all ISO 4217 currencies, formatted as "CODE — Full Name"
- The selected currency's symbol is previewed: "Amounts will display as: **\$1,234.56**"
- Required: Yes
- Helper text: "This is your main currency. You can add additional currencies later for travel or foreign accounts."

**Field 4: Date Format**
- Input type: Segmented toggle (three options)
- Options: **"MM/DD/YYYY"** | **"DD/MM/YYYY"** | **"YYYY-MM-DD"**
- Default: Auto-detected from locale
- Live preview below the toggle: "Today's date: **03/14/2026**" (updates dynamically based on selection)

**Field 5: Fiscal Year Start**
- Input type: Dropdown, showing 12 months
- Default: "January"
- Helper text: "Most people use January. If you file taxes on a different cycle, choose that month."

**Bottom — Navigation buttons, right-aligned**

> **[ ← Back ]** (text button, secondary style)
> **[ Continue → ]** (primary button, filled)

### Interactions
- "Continue" is disabled (grayed out) until Ledger Name and Primary Currency are filled.
- Switching between Individual and Household animates the member input smoothly — no jarring layout jump.
- The currency preview updates instantly when the dropdown selection changes.
- "Back" returns to Step 1.

### Validation Behavior
- Inline validation appears beneath each field when the user tabs away or clicks Continue.
- Error messages are specific: "Ledger name is required" not "This field is required."
- If Household is selected with fewer than 2 members, the error reads: "Add at least two household members, or switch to Individual."

---

## Step 3: Choose Your Template

### Purpose
This is the most important step conceptually. The user selects a pre-built chart of accounts that matches their financial life. The template determines the initial set of accounts (asset, liability, income, expense, equity). The goal is to make double-entry setup feel like choosing a theme — not building an accounting system from scratch.

### Screen Layout

**Progress bar** — Step 3 of 7 highlighted.

**Section header**

> **"Pick a starting point."**
>
> "Choose the template closest to your financial life. Don't worry about getting it perfect — you can add, rename, or remove any account later."

**Template cards — Grid layout, 2 columns on desktop, 1 column on mobile**

Each card is a selectable panel with a subtle border. When selected, the border becomes the primary accent color and a checkmark appears in the top-right corner. Only one template can be selected at a time.

---

**Template Card 1: "Simple Personal"**
- Icon: A single wallet
- Recommended badge: "Most Popular" (small pill badge, top-left corner)
- Description: "For individuals tracking everyday income and expenses. Includes a checking account, savings account, credit card, and common expense categories."
- Account preview (collapsed by default, expandable via "See accounts →" link):
  - Assets: Checking Account, Savings Account, Cash on Hand
  - Liabilities: Credit Card
  - Income: Salary / Wages, Interest Income, Other Income
  - Expenses: Housing, Utilities, Groceries, Transportation, Dining Out, Entertainment, Healthcare, Insurance, Clothing, Personal Care, Subscriptions, Miscellaneous
  - Equity: Opening Balances

---

**Template Card 2: "Household"**
- Icon: A house with people
- Conditionally highlighted: If the user selected "Household" in Step 2, this card has a soft highlight background and a label: "Recommended based on your setup"
- Description: "For families and shared households. Includes joint and individual accounts, shared expense categories, and household-specific tracking like childcare and home maintenance."
- Account preview (expandable):
  - Assets: Joint Checking, Joint Savings, [Member 1] Personal Account, [Member 2] Personal Account, Cash on Hand, Emergency Fund
  - Liabilities: Mortgage / Rent Deposit, Joint Credit Card, [Member 1] Credit Card, [Member 2] Credit Card
  - Income: [Member 1] Salary, [Member 2] Salary, Interest Income, Other Income
  - Expenses: Mortgage / Rent, Utilities, Groceries, Childcare, School / Education, Transportation, Dining Out, Entertainment, Healthcare, Insurance, Home Maintenance, Subscriptions, Gifts & Donations, Miscellaneous
  - Equity: Opening Balances

---

**Template Card 3: "Freelancer / Side Hustle"**
- Icon: A laptop with a dollar sign
- Description: "For individuals with self-employment or freelance income. Separates business and personal finances, includes invoicing categories and tax-relevant expense tracking."
- Account preview (expandable):
  - Assets: Personal Checking, Business Checking, Savings, Cash, Accounts Receivable
  - Liabilities: Personal Credit Card, Business Credit Card, Tax Payable (estimated)
  - Income: Client Income, Personal Salary (if applicable), Interest, Other Income
  - Expenses: (Split into Personal and Business sub-groups) — Personal: Housing, Utilities, Groceries, Transportation, Healthcare, etc. Business: Software & Tools, Office Supplies, Professional Services, Marketing, Travel (Business), Continuing Education, Bank & Payment Fees
  - Equity: Opening Balances, Owner's Draw / Contribution

---

**Template Card 4: "Comprehensive"**
- Icon: A full ledger book
- Description: "A detailed chart of accounts for users who want thorough tracking from day one. Includes investment accounts, loan tracking, detailed expense categories, and multi-currency readiness."
- Account preview (expandable):
  - Assets: Checking, Savings, Cash, Emergency Fund, Brokerage / Investments, Retirement (401k/IRA), HSA / FSA, Accounts Receivable, Other Assets
  - Liabilities: Credit Card (Primary), Credit Card (Secondary), Mortgage, Auto Loan, Student Loans, Personal Loans, Medical Debt, Other Liabilities
  - Income: Salary, Bonus, Investment Income (Dividends, Capital Gains), Rental Income, Side Income, Tax Refunds, Gifts Received, Other
  - Expenses: Housing (Rent/Mortgage, Property Tax, Home Insurance, HOA, Maintenance, Furnishings), Utilities (Electric, Gas, Water, Internet, Phone), Food (Groceries, Dining Out, Coffee), Transportation (Gas, Auto Insurance, Maintenance, Parking, Public Transit), Health (Insurance, Doctor/Dental, Prescriptions, Gym), Financial (Bank Fees, Interest Paid, Tax Preparation), Personal (Clothing, Grooming, Education), Lifestyle (Entertainment, Subscriptions, Travel, Hobbies, Gifts Given, Charity), Children (Childcare, Activities, Supplies)
  - Equity: Opening Balances, Retained Earnings

---

**Template Card 5: "Blank Slate"**
- Icon: An empty page with a plus sign
- Description: "Start with only the essential system accounts. Build your chart of accounts from scratch. Best for experienced users who know exactly what they want."
- Account preview: Only "Opening Balances Equity" account. Everything else is empty.

---

**Below the cards — an informational callout box (light blue or light yellow background)**

> ℹ️ **"What are these accounts?"**
> "In double-entry accounting, every transaction touches two accounts — money always comes from somewhere and goes somewhere. These templates set up the 'somewhere' — the categories and accounts that organize your financial life. Think of them as labeled folders for every type of money movement."

**Bottom — Navigation**

> **[ ← Back ]** **[ Continue → ]**

### Interactions
- Clicking anywhere on a card selects it. The previously selected card deselects.
- "See accounts →" expands an accordion-style list within the card, grouped by account type (Assets, Liabilities, Income, Expenses, Equity) with each type as a bold sub-header.
- "Continue" is disabled until a template is selected.
- If the user selected "Household" in Step 2 but picks "Simple Personal" here, a gentle toast or inline note appears: "This template is designed for individuals. Your household members won't have individual accounts. Switch to Household template?" with a dismiss option.

---

## Step 4: Customize Your Accounts

### Purpose
Let the user review and modify the chart of accounts generated by their chosen template. This is where power users can rename, add, or remove accounts. Casual users can scan the list and move on.

### Screen Layout

**Progress bar** — Step 4 of 7 highlighted.

**Section header**

> **"Make it yours."**
>
> "Here are the accounts from your chosen template. Rename anything that doesn't fit, remove what you don't need, or add what's missing. You can always do this later too."

**Account list — Organized by account type, displayed as collapsible sections**

Each account type (Assets, Liabilities, Income, Expenses, Equity) is a collapsible section with a colored left-border accent (green for Assets, red for Liabilities, blue for Income, orange for Expenses, gray for Equity). Each section shows a count badge: "Assets (3)" and is expanded by default.

Within each section, accounts are listed as editable rows. Each row contains:

- A drag handle (⠿) on the left for reordering
- An editable text field showing the account name (inline editing — click to edit, looks like plain text until focused)
- An account code displayed as a subtle monospace label (auto-generated, e.g., "1001", "2001") — editable for advanced users
- A delete button (🗑 icon, appears on hover, subtle) on the right

**At the bottom of each section — an "Add Account" row**

> **[ + Add account ]** (text button, left-aligned within the section)

Clicking it inserts a new blank row in the section with the cursor focused in the name field and an auto-generated next-in-sequence account code.

**Below all sections — a summary bar (sticky to bottom on scroll)**

> "**Total: 24 accounts** across 5 categories. You can add more anytime from Settings → Chart of Accounts."

**Bottom — Navigation**

> **[ ← Back ]** **[ Continue → ]**

### Interactions
- Inline editing: clicking an account name turns it into an active text input. Pressing Enter or clicking away saves. Pressing Escape reverts.
- Deleting an account shows a brief confirmation: "Remove 'Dining Out'?" with **Remove** and **Cancel** buttons. No modal — an inline popover anchored to the row.
- System-required accounts (like "Opening Balances" under Equity) have the delete button disabled with a tooltip: "This account is required for your opening balances."
- Drag-and-drop reordering works within a section (you can reorder expense accounts but can't drag an expense account into assets).
- Adding an account focuses the new name field and scrolls it into view if needed.

### Validation
- Account names must be unique within their type. If a duplicate is entered, the field shows a red border and the message: "An account with this name already exists in [section]."
- Account names: 1–80 characters.
- At least one account must exist in Assets, Liabilities, Income, and Expenses for the ledger to be functional. If a user tries to delete the last account in a required section, the message reads: "You need at least one [type] account. Add another before removing this one."

---

## Step 5: Set Opening Balances

### Purpose
Capture the current real-world balances of the user's asset and liability accounts. This creates the first set of transactions in the ledger (each debiting/crediting the account against the Opening Balances equity account). This step makes the ledger immediately useful — the user's net worth is visible from day one.

### Screen Layout

**Progress bar** — Step 5 of 7 highlighted.

**Section header**

> **"Where do you stand today?"**
>
> "Enter the current balance of each account. Check your bank apps or latest statements — it doesn't need to be down to the penny. Accounts you leave at zero will simply start empty."

**Informational callout — collapsible, open by default on first visit**

> 💡 **"Why do opening balances matter?"**
> "These starting values let Ledger show your complete financial picture from day one. Without them, your net worth and account balances would start at zero and only reflect future transactions. You can always adjust these later if you find a more accurate number."

**Balance entry form — Organized into two visual groups**

**Group 1: "What You Have" (Assets)**
- Green header accent
- Each asset account from Step 4 is listed as a row
- Each row: Account name (left, non-editable label) → Currency symbol + numeric input field (right-aligned, formatted with commas as you type)
- Default value in each field: 0.00
- Placeholder: "0.00"

Example rows:
> Checking Account ........................ \$ [ 4,250.00 ]
> Savings Account ......................... \$ [ 12,000.00 ]
> Cash on Hand ............................ \$ [ 150.00 ]

**Group 2: "What You Owe" (Liabilities)**
- Red header accent
- Same row structure, but with a helper note above the group:
> "Enter these as positive numbers. Ledger knows they're debts."

Example rows:
> Credit Card ............................. \$ [ 1,800.00 ]
> Student Loan ............................ \$ [ 24,500.00 ]

**Below both groups — a live-calculated summary card with soft background**

> 📊 **Your Starting Net Worth**
>
> Total Assets: **\$16,400.00**
> Total Liabilities: **\$26,300.00**
> ──────────────────────
> Net Worth: **−\$9,900.00**

The net worth line is green if positive, red if negative. It updates in real time as the user types.

A reassuring note beneath the summary if the value is negative:

> "A negative net worth is completely normal — especially with student loans or a mortgage. Ledger helps you watch this number improve over time."

**Bottom — Navigation**

> **[ ← Back ]** **[ Continue → ]**
>
> Subtle text link beneath: "Skip this step — I'll add balances later"

### Interactions
- Numeric fields accept only digits, commas, and a single decimal point. Non-numeric input is silently ignored.
- Tabbing between fields moves top to bottom within a group, then to the next group.
- The net worth summary recalculates on every keystroke (debounced by 200ms to avoid flicker).
- "Skip this step" sets all balances to zero and advances to Step 6. A toast confirms: "No problem. You can set opening balances anytime from Settings."

### Validation
- No negative numbers allowed in the input fields (liabilities are stored as positive values; the system handles the sign internally).
- Maximum value: 999,999,999.99 (displays an error if exceeded: "That's a lot of money. Double-check this amount?").
- Non-required: the user can leave everything at 0.00 and still continue.

---

## Step 6: Import Existing Data (Optional)

### Purpose
Allow users to jumpstart their ledger by importing historical transactions from bank exports (CSV/OFX) or from other finance tools. This step is entirely optional — many users will skip it during onboarding and import data later.

### Screen Layout

**Progress bar** — Step 6 of 7 highlighted.

**Section header**

> **"Bring in your history."**
>
> "If you have transaction exports from your bank or another finance app, you can import them now. This is completely optional — you can always import data later."

**Three option cards — Stacked vertically, full-width**

---

**Option Card 1: "Import Bank Transactions (CSV)"**
- Icon: A spreadsheet/CSV file icon
- Description: "Most banks let you download transactions as a .csv file. Ledger will help you map the columns to the right fields."
- Action button: **[ Choose CSV File ]**
- When clicked: Opens system file picker filtered to `.csv` files. After selection, the file name appears with a checkmark, and a column-mapping preview panel slides in below (see sub-flow below).

**Option Card 2: "Import from Finance App"**
- Icon: An exchange/sync icon
- Description: "Ledger can import from OFX/QFX files exported by Quicken, GnuCash, and most banking portals."
- Action button: **[ Choose OFX/QFX File ]**
- When clicked: Same pattern as CSV, but no column mapping needed — OFX is a structured format.

**Option Card 3: "Start Fresh"**
- Icon: A sparkle/star icon
- Description: "Skip importing and start recording transactions from today. Your opening balances are already set."
- Action button: **[ Start Fresh → ]** (styled as a text link, not a button, to de-emphasize)

---

**CSV Column Mapping Sub-Flow (appears inline after CSV file selection)**

A preview table showing the first 3 rows of the CSV file. Above the table, each column has a dropdown selector with options: "Date," "Description," "Amount," "Debit," "Credit," "Category," "Reference," "Ignore this column." Ledger auto-detects common column names and pre-selects mappings where it can.

Below the preview:

> "**42 transactions found** spanning Jan 1, 2026 – Mar 10, 2026."
>
> **Target account:** [ Dropdown: select which account these transactions belong to ]
>
> **[ Import These Transactions ]** (primary button)

---

**Bottom — Navigation**

> **[ ← Back ]** **[ Continue → ]**

The "Continue" button is always enabled on this step (imports are optional).

### Interactions
- Importing shows a progress indicator: "Importing 42 transactions..." with a spinner.
- After import completes, a success message replaces the card: "✓ 42 transactions imported into Checking Account. **3 duplicates were skipped.**" with a "View Details" link.
- Users can import multiple files (e.g., one per bank account) before continuing.
- File format errors show inline: "This file doesn't appear to be a valid CSV. Make sure it's exported from your bank's transaction download page."

---

## Step 7: Review & Get Started

### Purpose
Show the user a complete summary of everything that was set up during onboarding. Build confidence that the ledger is ready. Create a moment of completion and accomplishment.

### Screen Layout

**Progress bar** — Step 7 of 7, fully filled.

**Section header — Celebratory but not over-the-top**

> **"Your ledger is ready."**
>
> "Here's a summary of what we've set up. Everything below can be changed later from Settings."

**Summary sections — Clean, read-only display cards stacked vertically**

---

**Card 1: Profile**
- Ledger name, type (Individual or Household), household members if applicable
- Primary currency, date format, fiscal year start
- A small "Edit" link in the top-right corner of the card (returns to Step 2)

---

**Card 2: Chart of Accounts**
- Template name used (e.g., "Based on: Household template")
- Account counts by type: "6 Asset accounts, 4 Liability accounts, 4 Income accounts, 14 Expense accounts, 1 Equity account"
- A small "Edit" link (returns to Step 4)

---

**Card 3: Opening Balances**
- Total Assets, Total Liabilities, Net Worth — same format as Step 5's summary
- A small "Edit" link (returns to Step 5)

---

**Card 4: Imported Data** (only shown if the user imported in Step 6)
- "42 transactions imported into Checking Account"
- "Date range: Jan 1, 2026 – Mar 10, 2026"

---

**Below the cards — a visually prominent call-to-action section**

A slightly larger card or section with a warm background color:

> 🎉 **"You're all set."**
>
> "Your first step: record a transaction. Buy a coffee, pay a bill, receive your paycheck — Ledger makes it simple."
>
> **[ Open My Ledger → ]** (large primary button, centered)

Below the button, three subtle text links in a horizontal row:

> "📖 Take a quick tour" · "⌨️ Learn keyboard shortcuts" · "📚 Read the guide"

### Interactions
- "Edit" links on each card navigate back to the corresponding step. Returning to Step 7 preserves all data.
- "Open My Ledger" completes onboarding, marks it as done (never shown again for this ledger), and navigates to the main dashboard.
- "Take a quick tour" launches an optional overlay walkthrough of the main UI (tooltips pointing to key interface elements).
- The main dashboard, upon first load after onboarding, shows a friendly empty state with a prominent "Record Your First Transaction" button.

---

## Global UX Elements

### Progress Bar Behavior
The progress bar appears at the top of every step (Steps 1–7). It is a thin horizontal segmented bar. Completed steps are filled with the primary accent color. The current step is filled and slightly pulsing or has a dot indicator. Future steps are a light gray fill. Clicking on a completed step navigates back to it (with all data preserved).

### Transition Animations
All step transitions use a horizontal slide animation — advancing slides left, going back slides right. Duration: 250ms, ease-out curve. Form content fades in after the slide completes (100ms delay, 150ms fade).

### Responsive Behavior
On screens narrower than 768px, the template cards in Step 3 stack to a single column. Form fields remain single-column throughout (no side-by-side fields on mobile). The progress bar becomes a compact step counter: "Step 3 of 7" with back/next arrows. The net worth summary card in Step 5 becomes sticky to the bottom of the viewport on mobile so the user can see it update while scrolling through account fields.

### Keyboard Navigation
All form fields and buttons are fully keyboard-accessible. Tab order follows visual order. Enter submits the current step (equivalent to clicking Continue). Escape cancels inline editing in Step 4. Focus rings are visible and use the primary accent color.

### Color Palette Guidance
The onboarding should use the application's primary palette consistently. Account types should have consistent color coding throughout the onboarding and the main application: green hues for assets (money you have), red hues for liabilities (money you owe), blue hues for income (money coming in), amber/orange hues for expenses (money going out), and neutral gray for equity (system accounts). These colors are used for accents, borders, and section headers — never for full backgrounds (which remain white or light gray for readability).

### Error and Empty States
If the application encounters an error during onboarding (e.g., file import fails, database write fails), a non-blocking toast notification appears at the bottom of the screen with the error message and a "Try Again" action. The user is never kicked out of the onboarding flow due to an error. If the user navigates directly to the app URL without completing onboarding, they are redirected to the step where they left off — onboarding state is persisted locally.

---

## Post-Onboarding: First-Run Dashboard

After onboarding completes, the user lands on the main dashboard. For a first-time user, the dashboard should not feel empty. It should show the opening balance data entered during onboarding presented as the initial financial snapshot: a net worth card, account balances list, and a prominent call-to-action to record the first transaction. An optional tooltip-based tour highlights the navigation sidebar, the "New Transaction" button, the accounts list, and the reports section.

---

*This specification is intended to provide sufficient detail for visual mockup generation in tools such as Google Canvas, Figma, or similar. Each step described above corresponds to one screen or view. Visual designers should treat each Step section as a standalone screen specification with all copy, field definitions, layout guidance, and interaction notes included.*