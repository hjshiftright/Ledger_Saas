# Ledger — Onboarding Experience: Detailed Design Document

---

## Design Philosophy

The onboarding must accomplish two seemingly contradictory goals: collect a meaningful amount of financial data AND feel effortless. The key insight is that onboarding is not a gate before the product — **onboarding IS the product's first value delivery moment.** By the end of onboarding, the user must feel: *"I already know more about my finances than I did 20 minutes ago."*

Three design principles govern every decision in this document.

**Principle 1 — Show value before asking for effort.** Every piece of information the user provides should immediately produce a visible result — an account card appearing, a net worth number ticking up, a chart forming. The user is not "filling a form." They are building their financial portrait.

**Principle 2 — Defaults are sacred.** A user who clicks "Next" on every screen without typing anything should still end up with a functional, useful application. Defaults must be intelligent, not lazy. A 28-year-old salaried professional in Bangalore gets different defaults than a 50-year-old business owner in Jaipur.

**Principle 3 — Depth is optional, surface is mandatory.** The wizard presents the essential path. The contextual assistant (always visible in a side panel) offers depth. If a user wants to just say "I have an HDFC account with about ₹2 lakhs," that's enough. If they want to configure sub-accounts for joint accounts, salary accounts, and sweep-in FDs, the assistant helps them do that.

---

## Onboarding Flow Overview

The entire onboarding is visualized as a horizontal stepper or vertical journey map — always visible — so the user knows where they are and what lies ahead. The stages are:

```
[1. You] → [2. Your Money Map] → [3. Opening Balances] → [4. Your Net Worth] → [5. Your Goals] → [6. Your Ledger is Ready]
```

Each stage has a name, an icon, an estimated time, and can be revisited. Stage 5 (Your Goals) can be skipped and returned to later. A "Resume Later" capability is built in — the onboarding state is persisted, and the user can log out and return to exactly where they left off. The entire onboarding, if completed in one sitting, should take 15–25 minutes for a typical user.

---

## The Contextual Assistant Panel

A persistent panel occupying approximately 35% of the screen width on the right side is present throughout onboarding. This is the Contextual Assistant — a scripted, context-aware helper that provides tips, explanations, and guidance based on which step the user is on. It is not the LLM-powered AI bot (since the user has not yet configured an API key). Instead, it is a rule-based system that surfaces pre-written, relevant content at each step.

The assistant has a chat-like interface to feel conversational, but the messages are triggered by user actions rather than free-form input. The user can click on suggested questions (presented as clickable chips) to get more information. Examples of assistant behavior at various stages will be described within each stage below.

After onboarding, when the user configures their AI provider API key in Settings, this same panel transforms into the full LLM-powered conversational bot with access to all their financial data. This creates a natural upgrade moment — the user is already comfortable with the panel's location and interaction pattern, and the transition from scripted to intelligent feels like the product "coming alive."

On mobile, the assistant panel collapses into a floating help button that opens a bottom sheet when tapped.

---

## Stage 0: Account Creation

This is the pre-onboarding gate. It should be a single, clean page with minimal friction.

**Screen — Registration**

The screen presents a clean, centered card design. Fields required are: Full Name, Email Address, Password (with a strength meter — minimum 12 characters, passphrase encouraged), and Confirm Password. A single call-to-action button reads "Create My Ledger."

No CAPTCHA is shown unless abuse is detected. After submission, an email verification link is sent, but the user can proceed to Stage 1 immediately. Email verification is soft-gated — required before first data export or after 7 days, whichever comes first. This reduces onboarding abandonment caused by email verification friction.

Upon successful account creation, the user lands on the onboarding welcome screen, which displays a brief message setting expectations: *"Let's set up your financial world. This takes about 15–20 minutes, but you can pause and come back anytime. By the end, you'll know your net worth and have a plan for your goals."* A single button reads "Let's Begin →."

---

## Stage 1: You — Demographics & Financial Profile

**Purpose:** Collect personal context that shapes every default, projection, and recommendation downstream.

**Estimated time:** 3–4 minutes.

**UX Concept:** This should not feel like a form. The screen shows a stylized personal profile card (inspired by a modern ID card or passport layout) that fills in as the user provides information. Each question appears one at a time with a smooth transition animation, and the profile card updates in real-time. The contextual assistant panel shows relevant tips for each question.

---

### Question 1 — "What should we call you?"

A display name or nickname field, pre-filled from the full name entered during registration. This is the name the product uses in all personalized messages and headings. The profile card shows this name prominently.

---

### Question 2 — "When were you born?"

A date-of-birth picker. This gives us the user's current age, which is critical for retirement planning, insurance calculations, tax implications, and age-appropriate defaults. The profile card immediately shows "Age: 32" with a small life-stage indicator.

**Assistant tip:** *"Your age helps us set realistic defaults for financial goals. For example, a 28-year-old has different retirement planning horizons than a 45-year-old."*

---

### Question 3 — "Where are you based?"

A searchable dropdown of Indian cities (with the top 50 cities prioritized at the top). This is used for cost-of-living context in goal planning, HRA calculation context for salaried users, and eventually for location-based expense benchmarking. The profile card shows a small city indicator.

---

### Question 4 — "What describes your work best?"

Options presented as visual cards (not a dropdown) with illustrations: Salaried (Private Sector), Salaried (Government), Self-Employed / Freelancer, Business Owner, Retired, and Student / Not Working.

This choice fundamentally shapes the Chart of Accounts. A salaried person needs EPF and gratuity accounts. A business owner might need GST-related accounts. A retired person needs pension accounts. A student needs a simplified structure.

**Assistant tip for Salaried:** *"I'll set up EPF, professional tax, and salary-related accounts for you automatically."*
**Assistant tip for Business Owner:** *"I'll include business income, GST, and professional expense accounts in your setup."*

---

### Question 5 — "What's your approximate annual income?"

A slider with ranges rather than an exact number, to reduce friction: Under ₹5L, ₹5–10L, ₹10–20L, ₹20–50L, ₹50L–1Cr, and Above ₹1Cr.

This is used for tax regime defaults, savings rate benchmarking, insurance adequacy calculations, and goal feasibility checks.

**Assistant tip:** *"This helps us give you relevant suggestions. You don't need to be exact — pick the closest range. You can always refine this later from your actual data."*

---

### Question 6 — "Tell us about your household"

Presented as a compact sub-form within the same visual style: Marital status (Single / Married), Spouse works? (Yes / No — shown only if Married), Number of children (a stepper control, 0–6), Ages of children (shown for each child added, as a simple number input), and Number of other dependents such as elderly parents (a stepper control, 0–4).

This drives family mode setup, dependent-related goal templates (education fund, marriage fund), insurance needs assessment, and Section 80D applicability.

---

### Question 7 — "Which tax regime do you prefer?"

Options: Old Regime, New Regime, Not Sure.

If "Not Sure" is selected, the assistant provides a brief comparison: *"The New Regime has lower tax rates but fewer deductions. The Old Regime lets you claim deductions like 80C, HRA, and home loan interest. If you don't have heavy deductions, the New Regime usually works out better. We'll default to New Regime for now — you can change this anytime in Settings."*

---

### Question 8 — "What's your approximate monthly take-home income?"

A numeric input field with a pre-filled estimate based on the annual income range from Question 5 (for example, if they selected ₹10–20L, the field pre-fills with ₹1,00,000).

This specific number is important because it feeds directly into the goal planning surplus calculations in Stage 5. The annual range from Question 5 is too imprecise for that purpose.

**Assistant tip:** *"This is your in-hand salary or net monthly income after taxes. For self-employed users, this is your average monthly withdrawal or personal income from the business."*

---

### Question 9 — "What do you estimate your monthly expenses to be?"

A numeric input field. No pre-fill, but the assistant provides benchmarks based on their city and income: *"For someone in Bangalore with your income range, typical monthly expenses are ₹40,000–₹70,000. This includes rent, groceries, utilities, transport, and discretionary spending."*

This number, combined with take-home income, gives us the **monthly surplus** — the single most important number for goal feasibility calculations. The system computes and displays the surplus immediately: *"Your estimated monthly surplus is ₹35,000. This is the amount available for savings and investments."*

If the user enters expenses higher than or equal to their income, the assistant gently flags it: *"Your expenses seem to match or exceed your income, which means there's no surplus for savings. If this doesn't feel right, you might be overestimating expenses — most people do the opposite! You can adjust this later once you import bank statements for actual data."*

---

### Creative Addition — Financial Personality Mini-Assessment

Before moving to Stage 2, a quick, engaging four-question personality assessment appears. This is not a traditional risk profiling questionnaire (that comes in the goals section). This is lighter — designed to make the user feel seen and to set the tone of the experience.

**Question A:** *"When you check your bank balance, you feel..."*
Options: Anxious / Curious / Indifferent / Empowered

**Question B:** *"When it comes to tracking expenses, you..."*
Options: Track every rupee / Track big expenses only / Don't track at all / Have tried and given up

**Question C:** *"Your financial knowledge, honestly, is..."*
Options: Beginner / Know the basics / Fairly confident / Expert

**Question D:** *"What brought you to Ledger today?"*
Options: I want to know my net worth / I want to plan for a goal / I want to stop financial chaos / I'm just exploring

Based on these answers, the system assigns an internal profile tag — for example, "Motivated Beginner," "Lapsed Tracker," or "Confident Planner." This tag controls the level of jargon the contextual assistant uses, the amount of explanation provided in tooltips and insights throughout the product, the onboarding pacing (more hand-holding versus faster progression), and the initial dashboard emphasis (expense tracking focus versus investment focus versus goal focus).

The user sees a fun result card with a short message: *"You're a Curious Explorer 🧭 — You know there's a better way to manage money, you just haven't found the right tool. Ledger is built for you. Let's map out your financial world."*

This data is also genuinely useful for product analytics and personalization decisions.

---

### Stage 1 Completion

The profile card is now fully populated. The assistant congratulates: *"Great — I now know enough about you to personalize your setup. Next, let's discover all the places where your money lives."*

The profile card animates to become a small persistent element in the corner or header of subsequent stages, reminding the user of their context.

---

## Stage 2: Your Money Map — Account Discovery & Chart of Accounts Creation

**Purpose:** Discover all the user's financial accounts and create the Chart of Accounts.

**Estimated time:** 5–8 minutes.

**UX Concept — The Financial Life Map**

The screen is divided into two areas. The left 65% is a visual canvas where the user builds a map of their financial life. The right 35% remains the contextual assistant panel.

The canvas begins with the user's name or avatar in the center and four sectors radiating outward, each with a distinct color: **What You Own (Assets)** in green, **What You Owe (Liabilities)** in amber/red, **What You Earn (Income)** in blue, and **What You Spend (Expenses)** in orange.

Each sector contains clickable, illustrated cards representing sub-categories of accounts. When the user interacts with a card, it expands to collect details, and upon completion, a node appears on the canvas representing the created account. The canvas fills up as the user progresses, creating a visual "constellation" of their financial life.

---

### Sector 1: What You Own (Assets)

The system presents asset sub-categories as clickable, illustrated cards with a modern fintech aesthetic — soft gradients, recognizable icons, and clean typography.

---

**Card: Bank Accounts 🏦**

When clicked, this card expands to ask: "Which banks do you use?" The user sees a searchable grid of top Indian bank logos — SBI, HDFC, ICICI, Axis, Kotak, Yes Bank, IndusInd, IDFC First, PNB, BOB, IDBI, Federal Bank, Canara, Union Bank, and an "Other" option with a text input field. The user taps or clicks the banks they have accounts with.

For each selected bank, the system asks for an account type (Savings, Current, or Salary — presented as radio buttons) and optionally a nickname (for example, "Main Salary Account" or "Joint Account with Spouse").

Each selected bank immediately appears as a node on the canvas, connected to the Assets sector with a green line. The system creates accounts following the hierarchy `Asset > Bank > [Bank Name] [Type]`.

If the user selects multiple accounts at the same bank (for example, both a savings and a salary account at HDFC), the system supports this by showing an "Add another account at this bank" link.

**Default behavior if the user skips this card:** One generic "Bank Account" is created. This ensures the Chart of Accounts always has at least one bank account for basic functionality.

**Assistant tip:** *"Add all your bank accounts — even ones you rarely use. Forgotten accounts with small balances are still part of your net worth."*

---

**Card: Cash 💵**

A simple toggle: "Do you keep cash on hand (wallet, home safe, etc.)?" If toggled on, a "Cash in Hand" account is created.

**Default behavior:** This account is created for every user with a ₹0 opening balance, regardless of the toggle, since cash transactions are universal. If toggled off, the account exists but is marked as inactive and hidden from the default dashboard view.

---

**Card: Fixed Deposits 🏧**

"Do you have any Fixed Deposits?" If yes, the system asks: "With which banks or institutions?" The bank selector appears, pre-filtered to highlight banks already selected in the Bank Accounts card (since people most commonly hold FDs with their existing banks). For each bank selected, the system creates an FD account.

The assistant offers: *"If you have multiple FDs at the same bank, don't worry about adding each one separately now. One FD account per bank is enough to capture your total FD holdings. You can break them into individual FDs later if you want to track maturity dates."*

---

**Card: Provident Fund 🏛️**

This card is contextual. If the user selected "Salaried" in Stage 1, it appears with EPF pre-suggested.

The card asks three questions as toggles: "Do you have an EPF account?" (default Yes for salaried users, No for others), "Do you have a PPF account?" (default No), and "Do you contribute to VPF?" (default No).

For each toggled on, the corresponding account is created under `Asset > Provident Fund > [EPF/PPF/VPF]`.

**Assistant tip for EPF:** *"If you've been employed at multiple companies, you likely have one EPF account (if you transferred your UAN) or multiple (if you didn't). For now, one EPF account is fine. You can check your balance on the EPFO portal or the UMANG app."*

---

**Card: Stocks & Equities 📈**

"Do you invest in stocks?" If yes: "Which broker do you use?" A grid of broker logos is presented — Zerodha, Groww, Angel One, ICICI Direct, HDFC Securities, Upstox, 5Paisa, Motilal Oswal, Dhan, and Other. The user selects their broker(s).

For each selected broker, the system creates a demat/equity account under `Asset > Investments > Equities > [Broker Name]`.

**Assistant tip:** *"Just select your broker for now. We're not asking about individual stocks at this stage — you'll be able to import your holdings from your broker later for full detail."*

---

**Card: Mutual Funds 📊**

"Do you invest in Mutual Funds?" If yes: "Through which platform?" Options presented as cards: Direct via AMC websites, Kuvera, Coin by Zerodha, Groww, ET Money, Paytm Money, MF Central, and Other.

For each selected platform, the system creates a mutual fund account group under `Asset > Investments > Mutual Funds > [Platform Name]`. If the user selects "Direct via AMC," a single "Direct Mutual Funds" account is created.

**Assistant tip:** *"If you invest through multiple platforms, add each one. Later, you can import your CAMS or KFintech Consolidated Account Statement to automatically populate all your fund holdings regardless of platform."*

---

**Card: NPS (National Pension System) 🏦**

"Do you have an NPS account?" If yes, the system creates `Asset > NPS > Tier 1` and asks: "Do you also have a Tier 2 account?" If yes, creates `Asset > NPS > Tier 2`.

---

**Card: Gold 🪙**

"Do you own gold in any form?" Options are presented as multi-select cards: Physical Gold (jewelry, coins, bars), Sovereign Gold Bonds (SGBs), and Digital Gold (Paytm, Google Pay, PhonePe, etc.).

For each selected form, the corresponding account is created under `Asset > Gold > [Type]`.

**Assistant tip for Physical Gold:** *"For physical gold jewelry, estimate the weight of pure gold content, not the total jewelry weight. A 22-karat gold chain weighing 20 grams has about 18.3 grams of pure gold. If you're unsure, a rough guess is perfectly fine — we'll mark it as approximate."*

---

**Card: Real Estate 🏠**

This card first checks the user's housing situation: "Do you own the home you live in?" (Yes / No — I rent).

If yes, the system asks: estimated current market value, purchase price and year (useful for capital gains tracking later), and "Is there a loan on this property?" (if yes, the loan will be captured in the Liabilities sector).

The system then asks: "Do you own any other properties?" If yes, for each additional property: type (Residential, Commercial, or Land), an optional name or description (for example, "Pune Flat" or "Father's house"), estimated current market value, and whether there is a loan on it.

Each property creates an account under `Asset > Real Estate > [Property Name/Type]`.

---

**Card: Other Assets**

A catch-all section presented as a checklist of common items: Vehicles (car, bike — with a note that these depreciate), Money lent to others (personal loans given), Insurance with maturity value (LIC endowment, ULIP, money-back policies), Security deposits (rental deposit, utility deposits), and Crypto (if applicable).

Each selected item creates an appropriately typed account. For vehicles, the assistant notes: *"Vehicles lose value over time. We'll track them as depreciating assets. If you'd rather not track your car as an asset, you can skip this — many people don't."*

---

### Sector 2: What You Owe (Liabilities)

---

**Card: Home Loan 🏠**

This card is contextual. If the user indicated they own a home with a loan in the Real Estate card, this card is pre-activated and linked. If the user skipped the Real Estate card or said they don't own property, this card still appears (the user might be paying a home loan on a property they didn't think to list as an asset).

Questions: Which bank or institution is the loan from? Approximate outstanding principal (not original loan amount — the current remaining balance). EMI amount. Approximate interest rate. Remaining tenure in years.

The system creates `Liability > Loans > Home Loan > [Bank Name]` and internally links it to the corresponding real estate asset if one exists.

**Assistant tip:** *"Enter the current outstanding principal, not the original loan amount. You can find this in your latest loan statement or your bank's net banking portal under the loan section."*

---

**Card: Vehicle Loan 🚗**

Same structure as Home Loan: source institution, outstanding principal, EMI, interest rate, remaining tenure. Creates `Liability > Loans > Vehicle Loan > [Bank Name]`.

---

**Card: Personal Loan 💳**

Same structure: source, outstanding principal, EMI, rate, tenure. Creates `Liability > Loans > Personal Loan > [Source]`.

---

**Card: Education Loan 🎓**

Same structure with an additional note from the assistant: *"Education loan interest is deductible under Section 80E — no upper limit. We'll track this for your tax planning."*

---

**Card: Credit Cards 💳**

"Which credit cards do you have?" A visual grid of major issuers with logos is presented: HDFC, SBI Card, ICICI, Axis, Amex, RBL, IDFC First, Kotak, Yes Bank, IndusInd, OneCard, and Others.

For each selected issuer, the system asks: card name or nickname (optional — for example, "HDFC Regalia" or "Amazon Pay ICICI"), current outstanding balance (the amount currently owed — can be zero), and credit limit (for utilization tracking).

Each creates `Liability > Credit Card > [Issuer + Name]`.

**Default behavior:** Even if the user skips this card entirely, one generic "Credit Card" account is created. This is because many users will later want to record credit card transactions, and having the account pre-existing reduces friction.

---

**Card: Buy Now Pay Later / Other Borrowings**

A checklist: Amazon Pay Later, Simpl, LazyPay, Slice, any money borrowed from friends or family, or any other obligations. Each selected item creates a liability account.

---

### Sector 3: What You Earn (Income)

This sector is simpler than Assets and Liabilities because income accounts require less configuration.

The system presents income source toggles. Based on the occupation type selected in Stage 1, certain sources are pre-enabled:

**For Salaried users:** Salary/Wages (pre-enabled, cannot be disabled), Bonus/Incentives (pre-enabled), and Other Income (enabled).

**For Self-Employed/Business Owner:** Business Income (pre-enabled), Professional/Consulting Fees (pre-enabled), and Other Income (enabled).

**For all users, additional toggles:** Rental Income (pre-enabled if they own property beyond their primary residence), Interest Income (auto-enabled since they likely have bank accounts and FDs), Dividend Income (auto-enabled if they have stocks or mutual funds), Capital Gains (auto-enabled if they have investments — this is further split into Short-Term and Long-Term sub-accounts), and Gift Income.

For each enabled source, the system creates the corresponding income account. The user does not need to enter amounts here — amounts come from transactions recorded later.

**Assistant tip:** *"You don't need to enter any income amounts now. These accounts are just categories. Your actual income will be recorded when you start entering transactions or importing bank statements."*

---

### Sector 4: What You Spend (Expenses)

Instead of asking the user to list their expenses (most people cannot do this accurately), the system presents pre-configured expense categories with the option to customize.

A visual grid of expense category cards with icons is displayed. All are enabled by default. The user can toggle off categories that genuinely don't apply to them.

The categories are: Housing (Rent / Society Maintenance), Groceries & Household Supplies, Dining Out & Food Delivery, Transportation (Fuel, Metro, Auto, Cabs, Parking), Utilities (Electricity, Water, Gas, Internet, Mobile), Healthcare & Medical, Insurance Premiums, EMI Payments (auto-enabled if they have loans), Education & Learning, Shopping & Personal Care, Entertainment & Subscriptions, Travel & Vacations, Domestic Help & Services, Gifts & Donations, Children's Expenses (auto-enabled if they have children), Pet Expenses, Fitness & Wellness, and Miscellaneous.

The user is encouraged to leave most enabled: *"It's better to have a category and not need it than to not have one and lose tracking. You can always hide unused categories later."*

Each enabled category creates an expense account. Sub-categories can be configured later from Settings.

---

### Canvas Summary

After all four sectors are addressed, the canvas should show a populated visual map. The user sees their name in the center, surrounded by colored nodes for each account — green for assets, amber for liabilities, blue for income, and orange for expenses. The nodes are grouped by sector and connected with lines.

The assistant provides a summary: *"You've mapped out [X] accounts across your financial life. Here's your world at a glance. Now let's put actual numbers to these accounts."*

A floating "Add More" button remains available throughout the rest of onboarding and in the main application for accounts the user remembers later.

At the bottom of the canvas, the system shows a count: "[X] Asset Accounts, [Y] Liability Accounts, [Z] Income Accounts, [W] Expense Accounts."

---

## Stage 3: Opening Balances — Putting Numbers to Your Map

**Purpose:** Assign current balances to every account in the Assets and Liabilities sectors so the system can compute an initial net worth.

**Estimated time:** 5–8 minutes.

**UX Concept:** The visual map from Stage 2 transitions into a "fill in the blanks" mode. The canvas zooms in on the Asset and Liability nodes (Income and Expense accounts don't need opening balances). Each node now displays an editable value field. Nodes are color-coded by state: filled (has a balance — solid color) and empty (needs a balance — outlined with a dotted border).

The screen also has a running **Net Worth counter** in the header that updates in real-time as the user fills in balances. This is the core engagement mechanism — watching the net worth number change as they provide data makes the process feel productive rather than tedious.

---

### Interaction Flow

The system guides the user through accounts in a logical order, one category at a time. The user can either follow the guided sequence or click on any node on the canvas to jump directly to it.

**Guided Sequence:**

**Step 1 — Bank Accounts.** Each bank account is shown as a card with the bank logo, account type, and a large number input field. The user enters the current balance. As each balance is entered, the net worth counter at the top ticks upward.

**Step 2 — Cash.** If the user has a Cash in Hand account, a single input: "How much cash do you have on hand right now, roughly?" Default: ₹0.

**Step 3 — Fixed Deposits.** For each FD account, enter the current total value of FDs at that institution. An optional field for maturity date of the largest FD (this feeds the financial calendar feature later).

**Step 4 — Provident Fund.** For EPF, PPF, and VPF accounts, enter current balances. The assistant provides guidance on where to find these numbers: *"Your EPF balance is available on the EPFO member portal (member.epfindia.gov.in) or the UMANG app. Your PPF balance is in your bank's net banking under the PPF section. If you don't know the exact number, a rough estimate is fine."*

**Step 5 — Stocks & Equities.** For each brokerage account, enter the total current market value of the portfolio. The assistant notes: *"Log into your broker and check the 'Holdings' section. The total current value is usually displayed at the top. Don't worry about individual stocks — we'll get to that detail later."*

**Step 6 — Mutual Funds.** For each platform account, enter the total current value. Assistant: *"Check your fund platform's dashboard for the total portfolio value. Alternatively, check your CAMS or KFintech consolidated statement."*

**Step 7 — NPS.** Enter current value. Assistant: *"Check the NPS CRA portal (cra-nsdl.com) for your latest statement."*

**Step 8 — Gold.** For physical gold, the system asks for weight in grams and calculates value at the current gold rate (the system should have a recent gold rate — this can be a configuration or a static default that's periodically updated). For SGBs, ask for the number of units and calculate. For digital gold, enter the current value.

**Step 9 — Real Estate.** For each property, the estimated current market value (already entered in Stage 2 if the user filled it in, otherwise asked now).

**Step 10 — Other Assets.** Vehicles (estimated current resale value), money lent, insurance maturity values, deposits, crypto, etc.

**Step 11 — Liabilities.** For each loan, the outstanding principal (already captured in Stage 2 if entered, otherwise asked now). For each credit card, the current outstanding balance. For BNPL and other borrowings, current amounts owed.

---

### Handling Uncertainty

Users will not know every balance precisely. The system accommodates this with three options for each account:

**Exact amount** — the user enters a specific number. The account is marked as "Verified" internally.

**Approximate amount** — the user enters their best guess and ticks a checkbox labeled "This is approximate." The account is marked as "Estimated" and displays a ≈ symbol next to the balance in all views. The system tracks which accounts need verification and can nudge the user later.

**Skip for now** — the user clicks "I'll add this later." The account stays at ₹0 and is flagged as "Unverified" with a visual indicator (a small warning dot). It does not count toward net worth calculations but is included in the Chart of Accounts for future use.

The assistant reinforces this at the start of Stage 3: *"Don't worry about being perfectly accurate. Estimates are fine — we'll mark them so you know which accounts to verify later. Even a rough picture is better than no picture."*

---

### Double-Entry Accounting Behind the Scenes

For each opening balance entered, the system automatically creates a journal entry using the Opening Balance Equity account. This ensures the accounting equation is always balanced from the very first entry.

For an asset with a ₹2,00,000 balance:
`Debit: Asset > Bank > HDFC Savings ₹2,00,000`
`Credit: Equity > Opening Balance ₹2,00,000`

For a liability with ₹28,00,000 outstanding:
`Debit: Equity > Opening Balance ₹28,00,000`
`Credit: Liability > Home Loan ₹28,00,000`

The user never sees these journal entries during onboarding. They just see the number they typed. The accounting rigor happens silently. All opening balance entries are dated as of the onboarding date (or the user can specify "as of" a different date via an optional date picker — useful if they are entering balances from a recent statement).

---

### Stage 3 Completion

When the user has addressed all accounts (entering balances, marking as approximate, or skipping), the system shows a completion card:

*"You've filled in [X] of [Y] accounts. [Z] are marked as approximate and [W] are skipped."*

Two options: "Review My Accounts" (shows a clean table of all accounts with their balances for a final check) and "Show Me My Net Worth →" (proceeds to Stage 4).

---

## Stage 4: Your Net Worth — The First Payoff

**Purpose:** Present the user's computed financial position. This is the first tangible "deliverable" of the onboarding — the moment where the effort pays off.

**Estimated time:** 1–2 minutes (this is primarily a display stage, not an input stage).

**UX Concept:** A full-screen, animated "Financial Snapshot" that feels like an achievement. This is not the full dashboard (that comes after onboarding) — this is a focused, celebratory reveal.

---

### The Net Worth Reveal

The screen begins with the canvas from Stage 2, showing all account nodes. The view animates: asset nodes float upward, liability nodes float downward, and the two groups settle on either side of a central dividing line. The total assets number appears above, the total liabilities number appears below, and the line between them displays the Net Worth — animated from ₹0 to the calculated amount with a counting animation.

If the net worth is positive, the number is displayed in green with a brief positive message: *"Your estimated net worth is ₹34,20,000. This is everything you own minus everything you owe. It's your financial starting point — and it's only going to get more accurate from here."*

If the net worth is negative (common for people with recent large loans like home loans), the number is displayed in amber (not red — to avoid alarm) with a reassuring message: *"Your estimated net worth is -₹4,50,000. This is common when you have a recent home loan. The important thing is that you now have a clear picture, and every EMI payment improves this number. Let's build a plan."*

---

### Breakdown Display

Below the hero number, the snapshot shows three visualizations:

**Visualization 1 — Asset Composition.** A horizontal stacked bar or donut chart showing how the user's assets are distributed across categories: Cash & Bank Deposits, Fixed Income (FDs, PPF, EPF, Bonds), Equity (Stocks, Equity Mutual Funds), Real Estate, Gold, and Other. Each segment is labeled with both the amount and the percentage.

**Visualization 2 — Asset vs. Liability Scale.** A simple visual balance scale or bar comparison showing total assets on one side and total liabilities on the other, with the net worth as the difference.

**Visualization 3 — Account Summary Table.** A clean, compact table listing every account with its balance, grouped by type. Approximate balances show the ≈ indicator. Unverified accounts show "Not yet entered" in gray. This serves as a final review.

---

### Contextual Observations

The assistant panel shows 3–4 pre-computed observations based on the data. These are rule-based (not AI-generated) and drawn from a library of observation templates. Examples:

If the user has a high percentage of wealth in one category: *"[X]% of your assets are in real estate. While property is a solid long-term asset, high concentration in any one category increases risk. Diversification is something to explore."*

If they have significant idle cash in savings accounts: *"You have ₹[X] in savings accounts earning approximately 3–4% interest. If some of this is surplus beyond your emergency fund, a liquid fund or FD could earn more."*

If their liability-to-asset ratio is above 50%: *"Your liabilities are [X]% of your total assets. Reducing this ratio over time by paying down debt and growing investments is a good financial health indicator to track."*

If they have no equity exposure: *"You don't appear to have any equity investments (stocks or equity mutual funds). For long-term wealth building, especially for goals more than 5 years away, equity historically provides the best inflation-beating returns."*

These observations are intentionally light and informational, not prescriptive. They plant seeds of financial awareness that the goal planning stage will build on.

---

### Accuracy Caveat

If the user has approximate or unverified accounts, the system displays a small note: *"This net worth includes [X] estimated values and excludes [Y] accounts you haven't entered yet. You can improve accuracy anytime by updating balances or importing statements from the Import Hub."*

---

### Call to Action

Two buttons at the bottom:

**"Plan My Financial Goals →"** — proceeds to Stage 5.
**"Skip Goals for Now → Take Me to My Dashboard"** — skips to Stage 6. If the user chooses to skip, the system notes that goal planning is available anytime from the main menu.

---

## Stage 5: Your Goals — Where Do You Want to Be?

**Purpose:** Help users define, quantify, and plan for their financial life goals using the data already captured.

**Estimated time:** 5–10 minutes (depending on number of goals).

**This entire stage is optional and can be skipped.** The system makes this clear at the top: *"Setting goals helps you know if you're saving enough and investing right. But if you'd rather explore Ledger first and set goals later, you can skip this and come back anytime."*

---

### Step 1 — Setting Assumptions (One-Time, Applies to All Goals)

Before any individual goals are configured, the system asks the user to set global financial assumptions that will be used in all goal calculations. These are presented as a single compact panel with sliders and sensible defaults.

**General Inflation Rate**
Default: 6%. Adjustable range: 4–10%.
Assistant context: *"India's long-term average consumer inflation has been around 6%. This means something costing ₹1 lakh today will cost about ₹1.8 lakhs in 10 years."*

**Education Inflation Rate**
Default: 10%. Adjustable range: 6–15%.
Shown only if the user has children.
Assistant context: *"Education costs in India — especially for higher education — have risen at 10–12% per year historically, significantly faster than general inflation."*

**Expected Return from Equity (Long-Term)**
Default: 12%. Adjustable range: 8–18%.
Assistant context: *"India's Nifty 50 index has delivered approximately 12–13% CAGR over rolling 20-year periods. This is a reasonable long-term expectation for diversified equity investments."*

**Expected Return from Debt/Fixed Income**
Default: 7%. Adjustable range: 5–10%.
Assistant context: *"High-quality debt mutual funds, FDs, and government securities have typically returned 7–8% pre-tax over the long term."*

These assumptions are stored in user preferences and can be changed at any time from Settings. Any change automatically recalculates all goals.

---

### Step 2 — Risk Profiling

A short, five-question risk assessment determines the user's investor profile. Each question is presented as a visual scenario card with clear options.

**Question 1:** *"If your investments dropped 20% in value over one month, you would..."*
Options: Sell everything immediately / Sell some to cut losses / Do nothing and wait / Buy more at lower prices

**Question 2:** *"When it comes to investing, what matters more to you?"*
Options: Protecting what I have, even if it grows slowly / Growing my wealth, even if it fluctuates along the way

**Question 3:** *"How would you describe your investment experience?"*
Options: I've never invested beyond FDs and savings / I have some mutual funds or stocks / I actively manage my investments

**Question 4:** *"If you had ₹10 lakhs to invest for 10 years, which would you choose?"*
Option A: Guaranteed ₹18 lakhs at the end (approximately 6% annual return)
Option B: Most likely ₹28 lakhs, but could range from ₹18 lakhs to ₹40 lakhs (approximately 11% average return with volatility)
Option C: Most likely ₹38 lakhs, but could range from ₹12 lakhs to ₹65 lakhs (approximately 14% average return with high volatility)

**Question 5:** *"How long can you stay invested without needing this money?"*
Options: Less than 3 years / 3–5 years / 5–10 years / More than 10 years

Based on the answers, the system assigns one of four risk profiles:

**Conservative** — Recommended equity allocation: 20–30%, Expected blended return: 8–9%
**Moderate** — Recommended equity allocation: 40–60%, Expected blended return: 10–11%
**Aggressive** — Recommended equity allocation: 70–80%, Expected blended return: 12–13%
**Very Aggressive** — Recommended equity allocation: 80–100%, Expected blended return: 13–15%

The result is displayed with a visual spectrum (Conservative ← → Very Aggressive) and the user's position highlighted. The user can override this by selecting a different profile. The assistant explains: *"This is your starting profile. Each goal can have its own risk allocation based on its timeline — short-term goals should be more conservative, long-term goals can be more aggressive."*

---

### Step 3 — Goal Gallery

A visual grid of goal templates is presented as illustrated cards. Each card has an evocative illustration, a goal name, and a one-line description. The user browses and selects goals that apply to them. They can select multiple goals.

**Available Goal Templates:**

**Retirement / Financial Freedom 🏖️**
"Build a corpus that funds your expenses forever — the ultimate goal."

**Emergency Fund 🛡️**
"A safety net for life's surprises — job loss, medical emergencies, unexpected repairs."

**Child's Higher Education 🎓** (shown only if user has children)
"Fund your child's college or postgraduate education."

**Child's Marriage 💒** (shown only if user has children)
"Plan for your child's wedding celebration."

**First Home / Dream Home 🏡** (shown only if user does not own property, or labeled "Next Home" if they do)
"Save for a down payment or upgrade to your dream home."

**Dream Vehicle 🚗**
"That car or bike you've been thinking about."

**Vacation / Travel ✈️**
"Save for a meaningful trip — domestic or international."

**Wealth Milestone 💰**
"Hit a specific net worth target — ₹1 Crore, ₹5 Crore, your number."

**Debt Freedom ⛓️** (shown only if user has liabilities)
"Pay off all your loans and become completely debt-free."

**Custom Goal ✏️**
"Define your own goal with your own parameters."

---

### Step 4 — Goal Configuration

When the user selects a goal from the gallery, a focused configuration panel opens. I will detail the configuration for each major goal type.

---

#### Retirement / Financial Freedom

**Input 1 — Target Retirement Age**
A slider from the user's current age to 70. Default: 55 (for "financial freedom" framing) or 60 (for traditional retirement). The remaining years to retirement are shown prominently.

**Input 2 — Life Expectancy Assumption**
Default: 85. Adjustable from 70 to 100. This determines how many years the corpus needs to last. Assistant: *"Planning for a longer life is safer. Medical advances mean today's 30-year-olds could reasonably live into their 90s."*

**Input 3 — Monthly Expenses in Retirement (in Today's Money)**
Pre-filled with the monthly expense estimate from Stage 1. An adjustment slider from -40% to +20% is provided with context: *"Most people's expenses drop 20–30% in retirement — no commute, no work clothes, home loan typically paid off. But healthcare and leisure spending may increase."* The adjusted monthly expense in today's money is confirmed.

**Input 4 — Risk Allocation for This Goal**
Pre-filled from the global risk profile but adjustable. For retirement goals far away, the system suggests the user's full risk profile allocation. For retirement goals less than 10 years away, it suggests a more conservative allocation.

**The Calculation:**

The system computes and displays the following, updating in real-time as inputs change:

Future monthly expense at retirement = Today's expense × (1 + inflation)^years to retirement.
Annual expense at retirement = Future monthly expense × 12.
Total corpus needed = Annual expense at retirement × corpus multiplier (using a safe withdrawal rate of 4%, or 25× annual expenses, adjusted for the retirement duration and expected post-retirement returns).
Current investments the user can tag to this goal (a multi-select list of existing investment accounts from Stage 2 — the user checks which accounts are "for retirement").
Future value of tagged investments at retirement, growing at the blended expected return.
Gap = Corpus needed − Future value of tagged investments.
Monthly SIP required to fill the gap = calculated using the SIP future value formula at the blended expected return rate.

The result is presented as a visual journey chart or waterfall:

```
Today's Monthly Expense:                     ₹50,000/month
Adjusted for Retirement (-20%):              ₹40,000/month
Inflated to Retirement Age (23 yrs at 6%):   ₹1,53,000/month
Annual Expense at Retirement:                ₹18,36,000/year
Corpus Needed (25× annual expense):          ₹4,59,00,000
Investments Tagged to This Goal:             ₹12,00,000
Future Value at Retirement (at 12%):         ₹1,15,00,000
Gap:                                         ₹3,44,00,000
Monthly SIP Needed:                          ₹28,400/month (at 12% return)
```

**Interactive What-If Controls:** Sliders that let the user adjust retirement age, expense level, inflation assumption, and return expectation in real-time. As any slider moves, all numbers downstream recalculate instantly. This interactivity is critical — it makes abstract financial planning tangible.

---

#### Emergency Fund

**Input 1 — Target Months of Expenses**
Default: 6 months. Adjustable from 3 to 12. Assistant: *"6 months is the standard recommendation. If you're self-employed or have variable income, 9–12 months is safer."*

**The Calculation:**

Target amount = Monthly expenses (from Stage 1) × target months.
Current liquid assets (automatically identified: savings account balances + liquid fund balances if any).
Gap = Target − Current liquid assets.

Result: *"Your emergency fund target is ₹3,00,000 (6 months × ₹50,000). Your current liquid assets are ₹2,20,000. You need ₹80,000 more to be fully covered."*

---

#### Child's Higher Education

**Input 1 — Which child** (if multiple children, a selector)
**Input 2 — Education start age** — Default: 18. Adjustable.
**Input 3 — Estimated cost of education today** — Default varies by type. Quick presets: "Engineering in India (₹10–15L)," "MBA in India (₹15–25L)," "Engineering abroad (₹40–60L)," "MBA abroad (₹60L–1Cr)," or "Custom amount."
**Input 4 — Education inflation rate** — Pre-filled from global assumptions (10%).

**The Calculation:**

Years to goal = Education start age − child's current age.
Future cost = Today's cost × (1 + education inflation)^years.
Gap and SIP calculated same as retirement.

---

#### Child's Marriage

**Input 1 — Which child**
**Input 2 — Expected age of marriage** — Default: 27. Adjustable.
**Input 3 — Estimated cost today** — Default: ₹10,00,000 (adjustable). Assistant: *"Wedding costs vary enormously. Enter what you'd be comfortable spending in today's money."*

Calculation follows the same pattern as education.

---

#### Dream Home

**Input 1 — Target date or years from now**
**Input 2 — Estimated property cost today**
**Input 3 — Down payment percentage** — Default: 20%. Range: 10–100%.
**Input 4 — Will you take a home loan?** (Yes/No). If yes, the system calculates the loan EMI based on remaining amount, assumed interest rate (default 8.5%), and tenure (default 20 years), and shows this as a future monthly commitment.

Target savings = Property cost × down payment % (inflated to target date).

---

#### Dream Vehicle

**Input 1 — Target date or years from now**
**Input 2 — Vehicle cost today**
**Input 3 — Loan or full payment?** If loan: down payment %, interest rate, tenure.

---

#### Vacation / Travel

**Input 1 — Target date** (specific month/year)
**Input 2 — Estimated cost today**

Simple inflation adjustment to target date, SIP calculated.

---

#### Wealth Milestone

**Input 1 — Target net worth amount** (₹1 Cr, ₹5 Cr, ₹10 Cr, or custom)
**Input 2 — Target date or age**

The system calculates the required growth rate from current net worth to target, and shows whether it's achievable at the user's current savings rate and expected returns.

---

#### Debt Freedom

This goal is automatically configured based on existing liabilities.

The system shows all loans with their outstanding balances, EMIs, interest rates, and remaining tenures. It calculates the debt-free date if the user continues paying only minimum EMIs. It also shows the impact of extra payments: *"An extra ₹5,000/month toward your home loan would make you debt-free 3 years earlier and save ₹7,40,000 in interest."*

---

### Step 5 — Multi-Goal Consolidation

After all goals are configured, a consolidated view is presented. This is one of the most powerful moments in the onboarding.

**The Consolidated Table:**

A table showing all goals side by side with columns for: Goal Name, Target Date, Target Amount (Future Value), Currently Funded, Monthly SIP Needed, and Status.

**The Critical Number — Total Monthly Investment Required:**

The sum of all monthly SIP requirements across all goals is displayed prominently. Immediately below it, the user's monthly surplus (from Stage 1: take-home minus estimated expenses) is shown. The comparison is stark and clear:

If Total SIP ≤ Monthly Surplus: A green indicator and message: *"Your goals are achievable with your current surplus. You'd be investing ₹[X] of your ₹[Y] monthly surplus, leaving ₹[Z] as a buffer."*

If Total SIP > Monthly Surplus: An amber indicator and message: *"Your total investment need (₹[X]/month) exceeds your current monthly surplus (₹[Y]/month) by ₹[Z]. Here are some ways to bridge the gap:"* followed by suggested adjustments ranked by impact: extend the timeline for your largest goal by N years, reduce the target amount for discretionary goals, increase your income, or prioritize the most important goals and defer others.

**The Timeline Visualization:**

A horizontal timeline showing the user's current age on the left and their life expectancy on the right. Each goal is placed on the timeline at its target date, with the funded percentage shown as a progress bar within the goal marker. This gives the user a powerful visual of their financial life arc.

---

### Step 5 — Goal Stage Completion

The assistant panel summarizes: *"You've set [X] financial goals with a total target of ₹[Y]. Your monthly investment plan is ₹[Z]/month. This plan is [achievable / ambitious but possible / needs adjustment] based on your current situation."*

CTA: **"Launch My Ledger →"**

---

## Stage 6: Your Ledger is Ready — The Grand Entry

**Purpose:** Close the onboarding loop and transition the user into the main application with energy and momentum.

**Estimated time:** 1 minute.

**UX Concept:** A celebratory transition moment. A brief animation (a ledger book opening, a dashboard assembling itself piece by piece, or a simple elegant fade-in) leads to a personalized welcome.

---

### Welcome Summary Card

A centered card displays:

> *"Welcome to your Ledger, [Name]."*

Below, a clean summary:

**Accounts Created:** [X] accounts across [Y] categories.
**Net Worth:** ₹[Amount] (with a small note: "as of [onboarding date]").
**Goals Defined:** [X] goals (or "No goals set yet — you can add them anytime" if skipped).
**Monthly Savings Plan:** ₹[X]/month toward your goals (if goals were set).
**Accounts to Verify:** [X] accounts have approximate or missing balances.

---

### Suggested Next Steps

Below the summary, three action cards are presented:

**"Explore My Dashboard" 📊**
Primary CTA. Takes the user to the main home dashboard, which is pre-populated with their net worth widget, asset allocation chart, goal progress bars (if goals were set), and quick-action buttons for common tasks.

**"Import Bank & Investment Statements" 📥**
Secondary CTA. Takes the user to the Import Hub, where they can upload bank statements, CAMS/KFintech consolidated statements, broker holdings reports, and other financial documents. The system explains that imports will replace estimated balances with verified data, populate transaction history for expense analysis, enable automatic categorization and insights, and fill in individual stock and mutual fund holdings.

**"Configure AI Assistant" 🤖**
Takes the user to Settings > AI Configuration, where they can add their LLM provider API key. The system explains that the AI assistant enables natural language queries about their finances, intelligent transaction categorization, conversational financial insights, and the ability to ask questions like "How much did I spend on dining out last quarter?" This is the moment where the scripted contextual assistant from onboarding transforms into the full-powered AI bot.

---

### Post-Onboarding Nudge System

After the user enters the main application, a series of gentle, non-intrusive nudges guide them toward completing their financial picture:

**Day 1:** A dashboard banner: *"Your net worth is based on estimates. Import your first bank statement to see your real numbers."*

**Day 2–3:** If no AI key is configured, a subtle prompt: *"Unlock your AI financial assistant — add your API key in Settings."*

**Day 7:** If accounts still have approximate balances: *"[X] accounts still have estimated balances. Update them for a more accurate net worth."*

**Day 14:** If no goals were set: *"Ready to plan your future? Set up your first financial goal."*

These nudges are dismissable and respect the user's pace. They disappear once the corresponding action is taken.

---

## Data Model Requirements Summary

For the onboarding to populate the initial Chart of Accounts, opening balance sheet, goal planner, and dashboards, the following data must be captured and stored:

---

### User Profile

User ID (system-generated), full name, display name, email, hashed password, date of birth, current age (computed), city, occupation type, annual income range, monthly take-home income, estimated monthly expenses, computed monthly surplus, marital status, spouse works (boolean), number of children, children's ages (array), number of other dependents, tax regime preference, financial personality type (from mini-assessment), risk profile (from risk questionnaire), risk profile score (numeric), onboarding completion status, onboarding stage reached, and account creation timestamp.

---

### Chart of Accounts

Account ID (system-generated), account code (hierarchical, for example "1100.001"), account name, display name, account type (Asset, Liability, Income, Expense, Equity), account sub-type (Bank, FD, MF, Equity, Gold, Real Estate, Loan, Credit Card, etc.), parent account ID (for hierarchy — enables sub-accounts), institution name (bank, broker, AMC), institution logo reference, is quantity-tracked (boolean — true for stocks, MFs, gold), unit type (if quantity-tracked: shares, units, grams, sqft), currency (default INR), is active (boolean), is system-created (boolean — to distinguish onboarding-created accounts from user-created ones), verification status (Verified, Estimated, Unverified), created via (onboarding, manual, import), creation timestamp, and sort order (for display).

---

### Opening Balances

Balance ID, account ID, balance amount, balance date (onboarding date or user-specified "as of" date), is approximate (boolean), source (user-entered during onboarding), corresponding journal entry ID, and entry timestamp.

---

### Journal Entries (Opening)

Entry ID (system-generated), entry date (opening balance date), entry type (Opening Balance), narration (auto-generated, for example "Opening balance — HDFC Bank Savings"), is system-generated (boolean — true for onboarding entries), and list of entry legs. Each leg contains: leg ID, account ID, debit amount, credit amount, quantity (if applicable), and rate per unit (if applicable). All opening balance entries use the Equity > Opening Balance Equity account as the contra account.

---

### Goals

Goal ID (system-generated), goal type (Retirement, Emergency, Education, Marriage, Home, Vehicle, Vacation, Wealth, DebtFreedom, Custom), goal name (user-editable), goal icon, target date, target age (for age-based goals like retirement), target amount in today's money, inflation rate applicable (may override global), future value (computed), current funded amount (sum of tagged account balances), tagged account IDs (array — which investment accounts are assigned to this goal), risk profile for this goal, equity allocation percentage, debt allocation percentage, expected blended return percentage, required monthly SIP (computed), SIP start date (defaults to now), status (On Track, Behind, Ahead, Not Started), is active (boolean), creation timestamp, and last recalculated timestamp.

For the Retirement goal specifically, additional fields include: retirement age, life expectancy, monthly expense at retirement in today's money, expense adjustment percentage, safe withdrawal rate (default 4%), and computed annual expense at retirement (inflation-adjusted).

For Education and Marriage goals: linked child index and education type (domestic, international, custom).

For Debt Freedom: linked liability account IDs and extra monthly payment amount.

---

### Global Financial Assumptions

User ID, general inflation rate, education inflation rate, medical inflation rate, expected equity return, expected debt return, safe withdrawal rate for retirement, and last updated timestamp.

---

### Risk Profile Record

User ID, questionnaire version, individual question responses (array), computed profile (Conservative, Moderate, Aggressive, Very Aggressive), recommended equity allocation, recommended debt allocation, recommended blended return, assessment date, and is overridden by user (boolean).

---

### User Preferences

User ID, financial year preference (April–March or January–December), currency display format, active expense categories (array of account IDs), dashboard layout configuration (JSON — which widgets are visible and in what order), onboarding nudge states (which nudges have been shown and which dismissed), and theme preference.

---

## Initial Dashboard Population

Upon onboarding completion, the main dashboard is pre-populated with the following widgets based on available data:

**Net Worth Widget:** Displays the current net worth number prominently. Since this is day one, there is no trend line yet, but the widget is structured to show a time-series chart that will populate as the user updates balances over time. A small note reads: *"Update your balances monthly to track your net worth growth."*

**Asset Allocation Widget:** A donut chart showing the distribution of assets across categories (Cash & Bank, Fixed Income, Equity, Real Estate, Gold, Other). This is immediately populated from onboarding data.

**Liability Summary Widget:** A list of all liabilities with outstanding amounts and monthly EMI commitments. Total monthly EMI obligation is highlighted.

**Goal Progress Widget (if goals were set):** A set of progress bars or cards, one per goal, showing the goal name, target amount, currently funded percentage, monthly SIP required, and status indicator (color-coded).

**Monthly Cash Flow Widget:** Shows estimated monthly income, estimated monthly expenses, and computed surplus. Since no transactions have been imported yet, these come from the Stage 1 estimates. A note reads: *"Import your bank statements for actual spending data."*

**Quick Actions Bar:** Prominent buttons for the most important next steps: "Record a Transaction," "Import a Statement," "Update a Balance," and "Configure AI."

**Accounts to Verify Widget:** If any accounts have approximate or unverified balances, a small widget lists them with a "Verify Now" action for each.

---

## Summary of the Complete Onboarding Journey

The user's experience, from first visit to functional application, follows this arc:

They arrive at the registration page and create an account in under a minute. They enter the onboarding and are greeted with a warm welcome that sets expectations for a 15–20 minute setup. In Stage 1, they answer 9 questions and a 4-question personality assessment, taking about 3–4 minutes. Their personal profile is established and the system now knows enough to personalize every subsequent default.

In Stage 2, they spend 5–8 minutes discovering their financial accounts through an interactive visual canvas. They click on illustrated cards for each type of asset, liability, income, and expense category. Accounts appear as nodes on their Financial Life Map, and the Chart of Accounts is silently built behind the scenes.

In Stage 3, they spend 5–8 minutes putting numbers to each account. A running net worth counter gives them real-time feedback. They can enter exact amounts, approximations, or skip accounts for later. Double-entry journal entries are created automatically.

Stage 4 takes just 1–2 minutes — it is primarily a display and celebration stage. The user sees their net worth revealed with an animation, supported by an asset composition breakdown and contextual observations. This is the first moment of genuine value delivery.

If they choose to proceed, Stage 5 takes 5–10 minutes. They set global financial assumptions, complete a risk assessment, browse a goal gallery, and configure each selected goal with interactive calculations. The consolidated view shows them whether their goals are achievable within their current financial means.

Stage 6 takes under a minute — a summary of everything set up, and three clear paths forward: explore the dashboard, import statements, or configure the AI assistant.

The user exits onboarding with a functional personal finance system: a complete Chart of Accounts, an opening balance sheet, a computed net worth, an asset allocation view, optionally defined financial goals with a savings plan, and a clear understanding of what to do next.