# Ledger — Novice-Friendly Onboarding Wizard UX Design

**Version:** 1.0  
**Date:** March 21, 2026  
**Status:** Draft for Review  
**Design Theme:** Plain language, zero finance jargon, guided wizard with AI assistant

---

## Design Philosophy

> **"If your grandmother can fill this out, it's designed right."**

Every label, question, and placeholder must speak the language of everyday life — not accounting textbooks. The word "asset" never appears. Neither does "liability", "equity", "ledger", or "balance sheet". Instead:

| Finance Jargon | Plain Language Replacement |
|----------------|---------------------------|
| Assets | What you own |
| Liabilities | What you owe |
| Net Worth | Net Worth (Total Wealth) |
| Portfolio | Your savings & investments |
| Equity | Stocks / Shares |
| EPF / NPS | EPF / NPS |
| Mutual Fund | Mutual Fund |
| Capital | Money set aside |
| Opening Balance | Current amount |
| Goals / Financial Goals | What you're saving for |

---

## Overall Wizard Layout

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  🟢 Ledger                                                          Step 1 of 4 │
│  ─────────────────────────────────────────────────────────────────────────────  │
│                                                                                  │
│   ●━━━━━━━━━○━━━━━━━━━○━━━━━━━━━○                                               │
│   About You   What You Own   What You Owe   What I'm Saving For               │
│                                                                                  │
├──────────────────────────────────────────┬──────────────────────────────────────┤
│                                          │                                      │
│   LEFT PANEL — Main Form Area           │   RIGHT PANEL — AI Assistant         │
│   (60% width)                           │   (40% width)                        │
│                                          │                                      │
│   One focused section at a time         │   "Just talk to me"                  │
│   Large, friendly inputs                │   Conversational interface           │
│   Inline hints below each field         │   Fills form automatically           │
│   "Why do we ask?" tooltips             │   Always visible / collapsible       │
│                                          │                                      │
├──────────────────────────────────────────┴──────────────────────────────────────┤
│  [← Back]                                                   [Continue →]       │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Progress Stepper

A horizontal stepper always visible at the top, with friendly labels:

```
  ●━━━━━━━━━━━━━━━○━━━━━━━━━━━━━━━○━━━━━━━━━━━━━━━○
  About You     What You Own    What You Owe    What I'm Saving For
  (active)      (upcoming)      (upcoming)      (upcoming)
```

- Active step: filled circle + bold label
- Completed step: checkmark circle + muted label
- Upcoming step: empty circle + muted label
- Clicking a completed step goes back to it
- Mobile: steps collapse to "Step 1 of 4 — About You"

---

## AI Assistant Panel (Right Side — Persistent)

### Concept

A friendly chat panel fixed on the right side of every screen. The user can describe their situation in plain English, and the AI listens, understands, and fills the form fields on the left.

### Visual Design

```
┌──────────────────────────────────────┐
│  🤖 Your Financial Guide             │
│  ────────────────────────────────── │
│                                      │
│  ┌────────────────────────────────┐  │
│  │ 💬 Hi! I can help you fill    │  │
│  │ this out. Just tell me about  │  │
│  │ yourself in plain English and │  │
│  │ I'll handle the rest!         │  │
│  └────────────────────────────────┘  │
│                                      │
│  [User message bubble]               │
│  ┌────────────────────────────────┐  │
│  │ I'm Arjun, 32 years old,      │  │
│  │ working as a software engineer │  │
│  │ in Bangalore. I have 2 kids   │  │
│  │ and support my parents too.   │  │
│  └────────────────────────────────┘  │
│                                      │
│  [AI response with form fill preview]│
│  ┌────────────────────────────────┐  │
│  │ Got it, Arjun! I've filled in:│  │
│  │ ✅ Name: Arjun                 │  │
│  │ ✅ Age: 32                     │  │
│  │ ✅ Profile: Salaried / Tech    │  │
│  │ ✅ City: Bangalore             │  │
│  │ ✅ Kids: 2                     │  │
│  │ ✅ Supporting parents: Yes     │  │
│  │                                │  │
│  │ Looks good?                   │  │
│  │ [✓ Yes, perfect] [✏️ Tweak it]│  │
│  └────────────────────────────────┘  │
│                                      │
│  ┌────────────────────────────────┐  │
│  │ Type anything here... 🎤       │  │
│  └────────────────────────────────┘  │
│  [Send]                              │
└──────────────────────────────────────┘
```

### AI Assistant Behaviour

| Situation | AI Behaviour |
|-----------|-------------|
| User types a description | Parses and fills matching fields, shows a confirmation card |
| Ambiguous input | Asks a targeted clarifying question ("Did you mean a home loan or a personal loan?") |
| User confirms AI fill | Locks those fields with a ✅ badge; user can still click to edit |
| Field the AI can't determine | Highlights the empty field on the left with a gentle nudge ("I couldn't catch your city — can you tell me?") |
| User wants to undo AI fill | "Clear my answers for this step" button at the bottom |
| Mobile | AI panel becomes a floating chat bubble; tap to expand full-screen |

### Suggested Prompts (shown as chips when chat is empty)

- "I'm a software engineer earning ₹18L a year"
- "I have SBI and HDFC bank accounts"
- "I want to retire by 55 with ₹80,000 a month"
- "I owe ₹40 lakhs on a home loan"

---

## Screen 1 — About You

### Purpose
Understand who the person is so every recommendation, benchmark, and suggestion is personalised to their life stage.

### Heading & Subtext
- **Heading:** "Let's start with a little about you"
- **Subtext:** "This takes about 2 minutes and helps us personalise everything for you"
- **Guidance:** "Knowing your name, age, and details helps us plan your financial goals and timelines much better. Every person's journey is unique, and this helps us tailor Ledger to yours."

---

### Section 1: Your Name & Age

```
┌───────────────────────────────────────────────────────┐
│  What should we call you?                             │
│  ┌─────────────────────────────────────────────────┐  │
│  │  Arjun                                          │  │
│  └─────────────────────────────────────────────────┘  │
│  Hint: Just your first name is fine                   │
│                                                       │
│  How old are you?                                     │
│  ┌──────┐                                            │
│  │  32  │                                            │
│  └──────┘                                            │
│  Hint: Your age helps us calculate when to save by   │
└───────────────────────────────────────────────────────┘
```

**Fields:**

| Label on Screen | Field ID | Type | Validation | Hint Text |
|-----------------|----------|------|-----------|-----------|
| What should we call you? | `name` | Text | Required, 2–50 chars | Just your first name is fine |
| How old are you? | `age` | Number | 18–80 | Your age helps us plan timelines |

---

### Section 2: What Do You Do?

Displayed as large, friendly cards — not a dropdown. User taps one card. Multiple selections allowed if applicable.

```
┌──────────────────────────────────────────────────────────────────┐
│  What best describes what you do?                                │
│                                                                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐ │
│  │ 💼               │  │ 🏪               │  │ 📊             │ │
│  │ I work for a     │  │ I run my own     │  │ I invest and   │ │
│  │ company / org    │  │ business         │  │ manage money   │ │
│  │                  │  │                  │  │                │ │
│  │ Salaried         │  │ Business Owner   │  │ Investor       │ │
│  └──────────────────┘  └──────────────────┘  └────────────────┘ │
│                                                                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐ │
│  │ 💻               │  │ 🏠               │  │ 🌅             │ │
│  │ I work for       │  │ I manage the     │  │ I'm retired    │ │
│  │ myself /         │  │ home and family  │  │                │ │
│  │ freelance        │  │                  │  │                │ │
│  │ Freelancer       │  │ Homemaker        │  │ Retired        │ │
│  └──────────────────┘  └──────────────────┘  └────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

**Persona cards:**

| Card Label | Icon | Short Description | Internal ID |
|------------|------|------------------|-------------|
| Salaried | 💼 | I work for a company or organisation | `salaried` |
| Business Owner | 🏪 | I run my own business | `business` |
| Investor | 📊 | I invest and manage money | `investor` |
| Freelancer | 💻 | I work for myself / freelance | `freelancer` |
| Homemaker | 🏠 | I manage the home and family | `homemaker` |
| Retired | 🌅 | I'm retired | `retired` |

---

### Section 3: Where Are You Based?

```
┌───────────────────────────────────────────────────────┐
│  Which city do you live in?                           │
│  ┌─────────────────────────────────────────────────┐  │
│  │  Bangalore                     ▼               │  │
│  └─────────────────────────────────────────────────┘  │
│  Hint: This helps us benchmark costs in your city     │
└───────────────────────────────────────────────────────┘
```

| Label | Field ID | Type | Notes |
|-------|----------|------|-------|
| Which city do you live in? | `city` | Searchable dropdown | Top 50 Indian cities + "Other" option |

---

### Section 4: Your Family

```
┌───────────────────────────────────────────────────────┐
│  Tell us about your family                            │
│  (This helps us understand your expenses and what you're saving for)    │
│                                                       │
│  Are you married?                                     │
│  ○ Yes, married    ● Not yet / Single                │
│                                                       │
│  Do you have children?                                │
│  ○ No children                                        │
│  ● 1 child        ○ 2 children     ○ 3+ children      │
│                                                       │
│  Do you financially support your parents?             │
│  ● Yes        ○ No                                    │
│                                                       │
│  Any other dependents?                                │
│  ┌─────────────────────────────────────────────────┐  │
│  │  e.g. siblings, in-laws (optional)              │  │
│  └─────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────┘
```

| Label | Field ID | Type | Options |
|-------|----------|------|---------|
| Are you married? | `marital_status` | Toggle | Yes / No |
| Children | `num_children` | Segmented (0, 1, 2, 3+) | 0 = No children |
| Supporting parents? | `parents_support` | Toggle | Yes / No |
| Other dependents | `other_dependents` | Text (optional) | Free text |

---

### Screen 1 — Navigation

- **Back:** Not shown (first screen)
- **Continue:** "That's me — keep going →"  
- **Validation:** Name and profile type are required; age required; all others optional

---

## Screen 2 — What You Own

### Purpose
Capture everything the person has money in, in plain language. No "assets" or "balance sheet" language.

### Heading & Subtext
- **Heading:** "What do you currently have saved or invested?"
- **Subtext:** "Don't worry about exact numbers — estimates are perfectly fine"
- **Guidance:** "This shows us where your money is currently working. Understanding what you already own is the first step in building a solid foundation for your future wealth."

---

### Layout: Category Cards Grid

Each category is a tappable card. Tapping expands it to show detail entry. Cards that are already filled show a green checkmark and a summary.

```
┌────────────────────────────────────────────────────────────────────┐
│  💡 Tip: Add only what you have. Skip the rest — you can always   │
│  come back and add more later.                                     │
└────────────────────────────────────────────────────────────────────┘

┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
│  🏦               │ │  💰               │ │  📈               │
│  Bank Accounts    │ │  Cash in Hand     │ │  Stocks &         │
│                   │ │                   │ │  Shares           │
│  + Add            │ │  + Add            │ │  + Add            │
└───────────────────┘ └───────────────────┘ └───────────────────┘

┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
│  📦               │ │  🛡️              │ │  🥇               │
│  SIPs & Mutual    │ │  Retirement       │ │  Gold             │
│  Funds            │ │  Savings at Work  │ │                   │
│                   │ │  (EPF / NPS)      │ │                   │
│  + Add            │ │  + Add            │ │  + Add            │
└───────────────────┘ └───────────────────┘ └───────────────────┘

┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
│  🔒               │ │  🌍               │ │  ➕               │
│  Fixed Deposits   │ │  Foreign          │ │  Something else?  │
│  & RDs            │ │  Investments      │ │                   │
│                   │ │                   │ │                   │
│  + Add            │ │  + Add            │ │  + Add            │
└───────────────────┘ └───────────────────┘ └───────────────────┘
```

---

### Category: Bank Accounts

**Expanded view:**

```
┌─────────────────────────────────────────────────────────────────┐
│  🏦 Bank Accounts                                    [▲ Close]  │
│  ───────────────────────────────────────────────────────────── │
│                                                                │
│  Which bank and how much is sitting there right now?          │
│                                                                │
│  ┌────────────────────────────────────────────────┐           │
│  │  Account nickname   Bank name      Today's amount          │
│  │  ┌──────────────┐ ┌────────────┐ ┌────────────┐           │
│  │  │ My HDFC A/c  │ │ HDFC Bank ▼│ │ ₹ 3,25,000 │           │
│  │  └──────────────┘ └────────────┘ └────────────┘           │
│  └────────────────────────────────────────────────┘           │
│                                                                │
│  [+ Add another bank account]                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Fields per entry:**

| Label | Field | Type | Notes |
|-------|-------|------|-------|
| Account nickname | `nickname` | Text | e.g. "My HDFC Savings" |
| Bank name | `bank` | Searchable dropdown | Top Indian banks list |
| Today's amount | `balance` | Currency (₹) | Approximate is fine |

---

### Category: Cash in Hand

```
How much cash do you usually keep at home or in your wallet?
₹ [ 10,000 ]
Hint: An estimate is fine — for example ₹5,000 or ₹50,000
```

---

### Category: Stocks & Shares

```
Do you invest in individual stocks?
○ Yes    ● No

[If Yes:]
Broker / App name:   [ Zerodha ▼ ]
Approximate value:   ₹ [ 2,50,000 ]

(+ Add another broker / account)
```

---

### Category: SIPs & Mutual Funds

```
Do you have any SIPs or mutual fund investments?
● Yes    ○ No

[If Yes:]
Platform / App:      [ Groww ▼ ]
Approximate value:   ₹ [ 5,00,000 ]

Hint: This is the total current value, not what you invested originally.

(+ Add another platform)
```

---

### Category: Retirement Savings at Work (EPF / NPS)

```
Does your employer deduct PF (provident fund) from your salary?
● Yes    ○ No

[If Yes, EPF:]
Approximate EPF balance today:   ₹ [ 8,50,000 ]
Hint: Check your EPFO passbook or HR portal

Do you also have NPS (National Pension System)?
○ Yes    ● No

[If Yes, NPS:]
Approximate NPS balance:   ₹ [ 1,50,000 ]
```

---

### Category: Gold

```
Do you have any gold — jewellery, coins, or digital gold?

┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ 💍 Jewellery     │  │ 🪙 Coins / Bars  │  │ 📱 Digital Gold  │
│ ₹ [__________]  │  │ ₹ [__________]  │  │ ₹ [__________]  │
└──────────────────┘  └──────────────────┘  └──────────────────┘

Hint: Estimate based on today's gold price if you're not sure
```

---

### Category: Fixed Deposits & RDs

```
Do you have any Fixed Deposits (FDs) or Recurring Deposits (RDs)?
● Yes    ○ No

[If Yes:]
Where is it?         [ SBI ▼ ]
Type:                ○ Fixed Deposit (FD)   ● Recurring Deposit (RD)
Amount / Value:      ₹ [ 3,00,000 ]
Matures on:         [ March 2027 ] (optional)

(+ Add another FD / RD)
```

---

### Category: Foreign Investments

```
Do you have any investments or savings outside India?
○ Yes    ● No

[If Yes:]
Country / Currency:  [ US Dollar (USD) ▼ ]
Type:                [ US Stocks (e.g. ETFs) ▼ ]
Amount in ₹:         ₹ [ 4,50,000 ]
```

---

### Category: Something Else?

```
Do you have anything else we haven't asked about?
(e.g. a plot of land, a car you own, a business you own, insurance policy)

┌────────────────────────────────────────────────────────┐
│  What is it?        [ Land / Plot             ]       │
│  Approximate value  ₹ [ 25,00,000 ]                   │
└────────────────────────────────────────────────────────┘

(+ Add more)
```

---

### Screen 2 — Summary Bar

A subtle running total at the bottom of the left panel:

```
┌──────────────────────────────────────────────────────┐
│  Everything you own so far:   ₹ 45,35,000  (approx) │
└──────────────────────────────────────────────────────┘
```

### Screen 2 — Navigation

- **Back:** "← About You"
- **Continue:** "Continue to what you owe →"
- **Validation:** At least one entry recommended; shown as a gentle warning (not a blocker) — "You haven't added anything yet. That's okay — you can add it later."

---

## Screen 3 — What You Owe

### Purpose
Capture loans and credit card balances in a friendly, non-judgmental way.

### Heading & Subtext
- **Heading:** "Now let's look at what you owe"
- **Subtext:** "No judgment here — this helps us give you a complete and honest picture"
- **Guidance:** "High-interest debts can sometimes slow down your savings journey. Knowing what you owe helps us prioritize your path to becoming debt-free and reaching your goals faster."

---

### Layout: Category Cards Grid

```
┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
│  💳               │ │  🏠               │ │  🚗               │
│  Credit Cards     │ │  Home Loan        │ │  Vehicle Loan     │
│                   │ │                   │ │  (Car / Bike)     │
│  + Add            │ │  + Add            │ │  + Add            │
└───────────────────┘ └───────────────────┘ └───────────────────┘

┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
│  🎓               │ │  💸               │ │  ➕               │
│  Education Loan   │ │  Personal Loan    │ │  Any other loan   │
│                   │ │                   │ │  or money owed    │
│  + Add            │ │  + Add            │ │  + Add            │
└───────────────────┘ └───────────────────┘ └───────────────────┘
```

---

### Category: Credit Cards

```
┌─────────────────────────────────────────────────────────────┐
│  💳 Credit Cards                                [▲ Close]   │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  Which card and how much do you currently owe?             │
│  (This is your outstanding balance — what you'd pay today) │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ Card name    │  │ Bank         │  │ Amount you owe  │  │
│  │ HDFC Regalia │  │ HDFC Bank ▼  │  │ ₹ 22,500        │  │
│  └──────────────┘  └──────────────┘  └─────────────────┘  │
│                                                             │
│  [+ Add another credit card]                               │
└─────────────────────────────────────────────────────────────┘
```

| Label | Field | Type | Notes |
|-------|-------|------|-------|
| Card name | `card_name` | Text | e.g. "HDFC Regalia" |
| Bank | `bank` | Dropdown | List of card-issuing banks |
| Amount you owe right now | `outstanding` | Currency (₹) | Current outstanding balance |

---

### Category: Home Loan

```
┌─────────────────────────────────────────────────────────────┐
│  🏠 Home Loan                                   [▲ Close]   │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  Who is the loan with?                                     │
│  [ HDFC Bank ▼ ]                                           │
│                                                             │
│  How much do you still need to repay?                      │
│  ₹ [ 42,00,000 ]                                           │
│  Hint: Check your last EMI statement for "outstanding amt"  │
│                                                             │
│  Monthly EMI (payment per month):                          │
│  ₹ [ 38,500 ]                                              │
│                                                             │
│  Interest rate: [ 8.5 % ] (optional)                      │
│                                                             │
│  [+ I have another home loan]                              │
└─────────────────────────────────────────────────────────────┘
```

---

### Category: Vehicle Loan

```
What vehicle?
○ Car     ○ Two-wheeler     ○ Commercial vehicle

Lender:            [ Axis Bank ▼ ]
Amount still owed: ₹ [ 5,50,000 ]
Monthly EMI:       ₹ [ 12,500 ]
```

---

### Category: Education Loan

```
Who took this loan?
○ Myself     ○ My child     ○ Other family member

Lender:            [ SBI ▼ ]
Amount still owed: ₹ [ 8,00,000 ]
Monthly EMI:       ₹ [ 15,000 ] (optional — if repayment started)
```

---

### Category: Personal Loan

```
Lender / App:      [ Bajaj Finance ▼ ]
Amount still owed: ₹ [ 1,20,000 ]
Monthly EMI:       ₹ [ 8,500 ]

(+ Add another personal loan)
```

---

### Category: Any Other Loan or Money Owed

```
What is it?        [ Loan from a friend / relative ▼ ]
How much?          ₹ [ 50,000 ]
Notes (optional):  [ Borrowed from uncle for education ]
```

---

### Screen 3 — Running Summary

```
┌─────────────────────────────────────────────────────────────────┐
│  Total you owe:  ₹ 57,40,000       EMIs per month: ₹ 66,000    │
└─────────────────────────────────────────────────────────────────┘
```

---

### Screen 3 — Navigation

- **Back:** "← What You Own"
- **Continue:** "Continue to what you're saving for →"
- **Validation:** Optional — same gentle nudge if empty

---

## Screen 4 — What You're Saving For

### Purpose
Capture what the person is working towards — in the most human way possible.

### Heading & Subtext
- **Heading:** "What are you saving for?"
- **Subtext:** "Tell us your dreams — big or small. We'll help you get there."
- **Guidance:** "Goal-oriented investment will help you organize your wealth creation journey and adjust the investments according to the goals. It turns abstract numbers into real-life milestones you can work toward."

---

### Layout: Savings Plans Grid

Savings plans come in two flavours:
1. **Preset plans** — common things people save for, with friendly icons (shown upfront)
2. **Your own plan** — "Add your own dream" card

```
┌────────────────────────────────────────────────────────────────────┐
│  What are you saving for? Pick as many as you like.               │
└────────────────────────────────────────────────────────────────────┘

┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
│  🌅               │ │  🏥               │ │  🎓               │
│  Retire           │ │  Emergency        │ │  Kids'            │
│  Comfortably      │ │  Safety Net       │ │  Education        │
│                   │ │                   │ │                   │
│  [I'm saving for  │ │  [I'm saving for  │ │  [I'm saving for  │
│   this]           │ │   this]           │ │   this]           │
└───────────────────┘ └───────────────────┘ └───────────────────┘

┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
│  🏠               │ │  🚗               │ │  ✈️               │
│  Buy a Home       │ │  Buy a Car        │ │  Dream Vacation   │
│                   │ │                   │ │                   │
│  [I'm saving for  │ │  [I'm saving for  │ │  [I'm saving for  │
│   this]           │ │   this]           │ │   this]           │
└───────────────────┘ └───────────────────┘ └───────────────────┘

┌───────────────────┐
│  ✨               │
│  Something Else   │
│  I'm Saving For   │
│  (Add your own    │
│  dream / plan)    │
│  [Add this]       │
└───────────────────┘
```

---

### Savings Plan Detail: Retire Comfortably

When user taps "I'm saving for this", a detail panel slides in or expands inline:

```
┌─────────────────────────────────────────────────────────────────┐
│  🌅 Retire Comfortably                              [▲ Close]   │
│  ─────────────────────────────────────────────────────────────  │
│                                                                │
│  How old do you want to be when you retire?                   │
│     ┌────────┐                                                │
│     │  55    │  years old                                     │
│     └────────┘                                                │
│  (You're 32 today — that's 23 years away)                     │
│                                                                │
│  How much would you want to spend each month after retiring?  │
│     ₹ [ 80,000 ] per month                                    │
│  Hint: Think about today's expenses — it's okay to estimate   │
│                                                                │
│  How much have you already saved for retirement?              │
│  (EPF, NPS, PPF, FDs — anything you think of as retirement    │
│   money)                                                      │
│     ₹ [ 8,50,000 ] already saved                              │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  📊 Quick estimate                                       │ │
│  │  To retire at 55 with ₹80,000/month for 30 years,       │ │
│  │  you'll need roughly ₹3.2 Cr.                            │ │
│  │  You already have ₹8.5L — great start! 🎉                │ │
│  └──────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

**Fields:**

| Label | Field ID | Type | Notes |
|-------|----------|------|-------|
| Retirement age | `retirement_age` | Number (slider + input) | Default: 60 |
| Monthly expenses in retirement | `retirement_monthly_expense` | Currency (₹) | |
| Already saved for retirement | `retirement_saved` | Currency (₹) | Pre-filled from Screen 2 if EPF/NPS entered |

---

### Savings Plan Detail: Emergency Safety Net

```
┌─────────────────────────────────────────────────────────────────┐
│  🏥 Emergency Safety Net                            [▲ Close]   │
│  ─────────────────────────────────────────────────────────────  │
│                                                                │
│  An emergency fund is money you set aside for the unexpected  │
│  — job loss, medical bills, urgent repairs. Most experts      │
│  recommend 3–6 months of your monthly expenses.               │
│                                                                │
│  What are your monthly household expenses (roughly)?          │
│     ₹ [ 60,000 ] per month                                    │
│                                                                │
│  How many months of expenses do you want to keep safe?        │
│     ○ 3 months   ● 6 months   ○ 12 months                    │
│                                                                │
│  How much do you already have set aside as emergency money?   │
│     ₹ [ 1,00,000 ]                                            │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Your target: ₹ 3,60,000    You have: ₹ 1,00,000       │  │
│  │  Gap: ₹ 2,60,000 to go                                  │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

### Savings Plan Detail: Kids' Education

```
┌─────────────────────────────────────────────────────────────────┐
│  🎓 Education for Kids                              [▲ Close]   │
│  ─────────────────────────────────────────────────────────────  │
│                                                                │
│  For which child? (add multiple if needed)                    │
│  Child's name (or "Child 1"):   [ Riya ]                      │
│  Child's current age:           [ 6 ] years                   │
│                                                                │
│  When do you expect to need this money?                       │
│  (e.g. for college at age 18 → 12 years from now)             │
│     In [ 12 ] years                                           │
│                                                                │
│  How much do you think you'll need?                           │
│  (In today's value — we'll adjust for inflation)              │
│     ₹ [ 20,00,000 ]                                           │
│  Hint: Engineering/Medical college can cost ₹15–40L today    │
│                                                                │
│  How much have you already set aside for this?                │
│     ₹ [ 2,00,000 ]                                            │
│                                                                │
│  [+ Add for another child]                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

### Savings Plan Detail: Buy a Home

```
┌─────────────────────────────────────────────────────────────────┐
│  🏠 Buy a Home                                      [▲ Close]   │
│  ─────────────────────────────────────────────────────────────  │
│                                                                │
│  What's the rough budget for the home you have in mind?       │
│     ₹ [ 80,00,000 ]                                           │
│  Hint: Include registration and stamp duty costs (~10%)       │
│                                                                │
│  When do you want to buy it?                                  │
│     In [ 3 ] years   (or by year [ 2029 ])                    │
│                                                                │
│  How much have you already saved up for this?                 │
│     ₹ [ 5,00,000 ]                                            │
└─────────────────────────────────────────────────────────────────┘
```

---

### Savings Plan Detail: Buy a Car

```
┌─────────────────────────────────────────────────────────────────┐
│  🚗 Buy a Car                                       [▲ Close]   │
│  ─────────────────────────────────────────────────────────────  │
│                                                                │
│  What kind of car do you have in mind?                        │
│  ○ Hatchback (up to ₹8L)   ○ Sedan (₹8–20L)                  │
│  ● SUV (₹20–40L)           ○ Luxury (₹40L+)                  │
│                                                                │
│  Budget:        ₹ [ 25,00,000 ]                               │
│  When?          In [ 2 ] years                                │
│  Already saved: ₹ [ 3,00,000 ]                                │
└─────────────────────────────────────────────────────────────────┘
```

---

### Savings Plan Detail: Dream Vacation

```
┌─────────────────────────────────────────────────────────────────┐
│  ✈️ Dream Vacation                                  [▲ Close]   │
│  ─────────────────────────────────────────────────────────────  │
│                                                                │
│  Where do you want to go?   [ Maldives / Europe / Japan ]     │
│  Estimated cost:            ₹ [ 3,00,000 ]                    │
│  When?                      In [ 1 ] year                     │
│  Already saved:             ₹ [ 50,000 ]                      │
└─────────────────────────────────────────────────────────────────┘
```

---

### Savings Plan Detail: Something Else I'm Saving For (Custom)

```
┌─────────────────────────────────────────────────────────────────┐
│  ✨ Something Else I'm Saving For           [▲ Close]   │
│  ─────────────────────────────────────────────────────────────  │
│                                                                │
│  What are you saving for?                                     │
│  [ Starting a business / Wedding / Medical treatment / Other ]│
│                                                                │
│  How much will you need?    ₹ [ __________ ]                  │
│  When do you need it?       In [ __ ] years                   │
│  Already saved:             ₹ [ __________ ]                  │
│                                                                │
│  [+ Add another savings plan]                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### Screen 4 — Your Savings Plans Summary

Your saved plans appear as summary chips below the cards grid as they're added:

```
✅ Retire at 55 · ₹80K/mo   ✅ Emergency: 6 months   ✅ Riya's education: ₹20L in 12yr
```

---

### Screen 4 — Navigation

- **Back:** "← What You Owe"
- **Continue:** "Show me my financial picture →"
- **Validation:** Optional — at least one plan is recommended with a gentle prompt: "Telling us what you're saving for helps us guide you better. Add at least one?"

---

## Completion Screen

### Purpose
Celebrate the user completing onboarding and give them a sense of what they've built.

### Design

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│                    🎉                                       │
│                                                             │
│         You're all set, Arjun!                             │
│                                                             │
│    Here's a quick snapshot of what you just built:         │
│                                                             │
│    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│    │ 💰           │  │ 💳           │  │ 🎯           │   │
│    │ You own      │  │ You owe      │  │ Plans added  │   │
│    │ ₹ 45.3L      │  │ ₹ 57.4L      │  │ 4            │   │
│    └──────────────┘  └──────────────┘  └──────────────┘   │
│                                                             │
│    Your Net Worth today:  -₹ 12.1L                            │
│    (Don't worry — most people with active loans look       │
│    like this. Your investments grow over time!)            │
│                                                             │
│              [Open My Dashboard →]                         │
│                                                             │
│    You can update any of this later from Settings.         │
└─────────────────────────────────────────────────────────────┘
```

---

## AI Assistant — Detailed Interaction Spec

### Integration with Each Screen

| Screen | AI's Proactive Prompt | What AI Can Auto-Fill |
|--------|-----------------------|----------------------|
| Screen 1 | "Tell me about yourself!" | Name, age, profile type, city, family details |
| Screen 2 | "What money do you have saved or invested?" | All asset categories and amounts |
| Screen 3 | "Any loans or credit cards?" | All loan types, lenders, outstanding amounts, EMIs |
| Screen 4 | "What are you saving towards?" | Savings plans, amounts, timelines, already-saved amounts |

---

### Sample AI Conversations by Screen

**Screen 1:**
```
User: "I'm Priya, 28, a software engineer at TCS in Hyderabad. 
       I'm married and have no kids yet. My parents aren't 
       dependent on me."

AI fills:
  ✅ Name: Priya
  ✅ Age: 28
  ✅ Profile: Salaried
  ✅ City: Hyderabad
  ✅ Married: Yes
  ✅ Kids: 0
  ✅ Supporting parents: No
```

**Screen 2:**
```
User: "I have HDFC savings with about 2 lakhs, SBI with 50k, 
       around 3 lakh in Zerodha stocks, and my EPF should be 
       around 4 lakhs. I also have 2 SIPs in Groww for about 
       1.5 lakhs total."

AI fills:
  ✅ Bank Accounts → HDFC: ₹2,00,000
  ✅ Bank Accounts → SBI: ₹50,000
  ✅ Stocks & Shares → Zerodha: ₹3,00,000
  ✅ Retirement (EPF): ₹4,00,000
  ✅ SIPs & Mutual Funds → Groww: ₹1,50,000
```

**Screen 3:**
```
User: "I have an HDFC home loan with about 35 lakhs remaining, 
       EMI is 32,000 a month. And one credit card from ICICI 
       with 15,000 outstanding."

AI fills:
  ✅ Home Loan → HDFC: ₹35,00,000 | EMI: ₹32,000
  ✅ Credit Card → ICICI: ₹15,000
```

**Screen 4:**
```
User: "I want to retire at 58. I'd need about 70k a month 
       after retirement. I also want to save for a house 
       in 5 years — roughly 60 lakhs. And an emergency fund 
       for 6 months of my 55k monthly expenses."

AI fills:
  ✅ Retire at 58 | ₹70,000/month
  ✅ Buy a Home in 5 years | ₹60,00,000
  ✅ Emergency Fund: 6 months × ₹55,000 = ₹3,30,000
```

---

### AI Panel States

| State | Visual |
|-------|--------|
| Idle (no conversation yet) | Friendly greeting + 3–4 suggested prompt chips |
| Listening (user typing) | Subtle pulse animation on the input bar |
| Processing | "Thinking..." with a gentle loading shimmer |
| Filled fields | Green checkmarks in the chat bubble; matching fields briefly glow on the left panel |
| Partial fill | Orange badges on fields AI couldn't fill; AI explains what it's missing |
| Error / unclear | AI asks a focused follow-up question |
| Voice mode (optional) | Microphone icon in input bar; real-time transcript |

---

### AI "Why do we ask?" System

Every field section has a small ⓘ icon. Clicking it triggers an AI explanation in the right panel:

```
User clicks ⓘ next to "Supporting parents?"

AI: "When you support your parents financially, it affects 
     how much you can save and invest each month. It also 
     shapes your insurance needs and emergency fund size. 
     We'll factor this into your monthly budget automatically."
```

---

## Responsive Design Notes

### Desktop (≥1280px)
- Two-panel layout: form 60% left, AI 40% right
- All category cards in 3-column grid
- Expanded card detail appears inline

### Tablet (768–1279px)
- Two-panel layout: form 55% left, AI 45% right (collapsible)
- Category cards in 2-column grid

### Mobile (<768px)
- Single-column layout
- AI assistant as floating action button (bottom right)
- Tapping FAB opens full-screen AI chat
- Category cards as full-width rows
- Sticky "Continue" button at bottom

---

## Tone & Copy Guidelines

| Situation | ✅ Use This | ❌ Avoid This |
|-----------|------------|--------------|
| Empty state | "You haven't added anything yet — that's okay!" | "No records found" |
| Asking for amounts | "How much is in there right now?" | "Enter opening balance" |
| Validation error | "Looks like you skipped your name — we need this one!" | "Field required" |
| Completion | "You're all set!" | "Onboarding complete" |
| Loan section | "No judgment — loans are normal!" | (silence / clinical form) |
| Tip | "An estimate is perfectly fine" | "Enter exact value" |
| Progress | "Almost there — one more step!" | "3 of 4 steps completed" |

---

## Accessibility Requirements

- All inputs have visible focus rings
- Card selection uses `aria-pressed` 
- AI chat panel has `aria-live="polite"` for screen reader updates
- Each screen has a single `h1` as the main heading
- Colour is never the sole indicator of state (always paired with icon or text)
- Tab order follows visual reading order
- AI-filled fields are marked with `aria-label="Pre-filled by AI assistant — click to edit"`

---

## Data Collected: Summary Table

| Screen | Field | Field ID | Required |
|--------|-------|----------|----------|
| 1 | Name | `name` | Yes |
| 1 | Age | `age` | Yes |
| 1 | Profile type | `profile_type` | Yes |
| 1 | City | `city` | No |
| 1 | Marital status | `marital_status` | No |
| 1 | Number of children | `num_children` | No |
| 1 | Supporting parents | `parents_support` | No |
| 2 | Bank accounts (list) | `bank_accounts[]` | No |
| 2 | Cash in hand | `cash_in_hand` | No |
| 2 | Stocks / shares | `equity[]` | No |
| 2 | Mutual funds / SIPs | `mutual_funds[]` | No |
| 2 | EPF balance | `epf_balance` | No |
| 2 | NPS balance | `nps_balance` | No |
| 2 | Gold | `gold` | No |
| 2 | Fixed deposits | `fixed_deposits[]` | No |
| 2 | Foreign investments | `foreign_investments[]` | No |
| 2 | Other assets | `other_assets[]` | No |
| 3 | Credit cards | `credit_cards[]` | No |
| 3 | Home loan | `home_loans[]` | No |
| 3 | Vehicle loan | `vehicle_loans[]` | No |
| 3 | Education loan | `education_loans[]` | No |
| 3 | Personal loan | `personal_loans[]` | No |
| 3 | Other loans | `other_loans[]` | No |
| 4 | Retire comfortably | `goal_retirement` | No |
| 4 | Emergency safety net | `goal_emergency` | No |
| 4 | Kids' education | `goals_education[]` | No |
| 4 | Buy a home | `goal_home` | No |
| 4 | Buy a car | `goal_car` | No |
| 4 | Dream vacation | `goals_vacation[]` | No |
| 4 | Custom savings plans | `goals_custom[]` | No |

---

## Open Questions for Review

1. **AI backend:** Should the AI assistant use a streaming response (real-time word-by-word), or batch response? Streaming feels more alive.
2. **Voice input:** Should the microphone icon be included in the AI chat input from day 1, or deferred to v2?
3. **Skip behaviour:** Should every screen allow "I'll fill this later" or should Screen 1 (About You) be mandatory?
4. **Pre-fill from persona:** When a user selects "Salaried" in Screen 1 and the AI has identified common accounts, should Screen 2 pre-populate suggestions automatically?
5. **Progress save:** Should progress auto-save so a user can close the tab and resume? If yes, where — localStorage or server?
6. **Net worth reveal:** The completion screen shows the net picture. Should it always show even if it's negative?

---

*Document prepared for review — March 21, 2026*
