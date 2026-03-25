# Strategic Dashboard Suite: Team Brief (Ledger 3.0)

This document acts as a **Product Specification** for the 20 Dashboards. Each view is designed to be self-explanatory, combining a relatable story with a clear data visualization.

---

## 🛡 Phase 1: Safety & Peace of Mind
*Goal: Remove anxiety and establish a rock-solid foundation.*

| Dashboard | User Value | Visualization Type | Data Logic / Calculation | Advisor Insight / Tip |
| :--- | :--- | :--- | :--- | :--- |
| **1. Survival Runway** | Eliminates fear of job loss. | **Progress Ring + Runway Line** | `Liquid Assets / Avg. Monthly Expenses` | "You have 14 months of flight time. Focus on quality, not panic." |
| **2. Emergency Shield** | Prevents one bad day from ruining a year. | **Shield Icon (Fill Level)** | `Current Emergency Fund / Target (6x Expenses)` | "Your shield is at 80%. refill it with ₹5k/mo to be fully protected." |
| **3. Family Protection** | Ensures family continuity. | **Gap Chart (Overlapping Bars)** | `Term Life Insurance vs. (Loans + Future Goals)` | "You have a ₹1Cr gap. A simple term plan fixes this for ₹1k/mo." |
| **4. Health Safety-Net** | Prevents medical debt. | **Stacked Bubble Chart** | `Corp Insurance vs. Personal Top-up vs. Avg Surgery Cost` | "Corporate cover is thin. A ₹20L top-up is your best safety move." |

---

## 🚀 Phase 2: Wealth Engine
*Goal: Make money work harder and track growth velocity.*

| Dashboard | User Value | Visualization Type | Data Logic / Calculation | Advisor Insight / Tip |
| :--- | :--- | :--- | :--- | :--- |
| **5. Lazy Money Gym** | Identifies wasted potential. | **Character Animation (Sleep/Gym)** | `Savings Balance - Monthly Buffer = Lazy Money` | "₹8L is 'sleeping' (0% real growth). Move it to an Orchard for 8% yield." |
| **6. Wealth Velocity** | Are you actually getting richer? | **Vector Arrow (Length/Direction)** | [(Net Worth Growth / Income) * 100](file:///c:/Users/kvamsi/sources/ledger-3.0/frontend/src/OnboardingV2.jsx#535-536) | "Your income is up, but your wealth is flat. Lifestyle is eating your raises." |
| **7. Freedom Countdown** | Defines the "Work-Optional" date. | **Digital Countdown Clock** | `FIRE Number (25x Exp) / Monthly Savings Projection` | "Independence Day: Aug 2038. ₹5k extra per month brings it to 2036." |
| **8. Tax Leakage** | Stops "Scramble Spending" in March. | **Leaky Bucket (Animation)** | `Unused 80C/80D limits based on profile` | "Move ₹15k to ELSS now to save ₹4.5k in tax (and grow your wealth)." |

---

## 🎨 Phase 3: Aspirations & Dreams
*Goal: Connect numbers to real-life big moments.*

| Dashboard | User Value | Visualization Type | Data Logic / Calculation | Advisor Insight / Tip |
| :--- | :--- | :--- | :--- | :--- |
| **9. Dream Home Path** | Makes ownership a plan. | **House Progress Filling Up** | `Dedicated Savings vs. Projected Downpayment` | "You are 65% there. This goal is on track for Dec 2027!" |
| **10. Junior Harvard** | Solves #1 parent anxiety. | **Stacked Books (Local/Intl)** | `Savings vs. (Local Tuition vs. Ivy League Costs)` | "You've funded 3 years of local college, but only 0.5 years of Ivy League." |
| **11. Luxury Escape** | Removes guilt from vacations. | **Passport Stamp Progress** | `Sinking Fund vs. Trip Budget` | "This trip costs 4 months of retirement. Are you okay with that trade?" |
| **12. Guilt-Free Spending** | Encourages enjoying work. | **Green Light / Traffic Light** | `Surplus after Goal SIPs and Fixed Costs` | "You have ₹12k for 'fun' this month. Spending it won't hurt any goals." |

---

## 🕰 Phase 4: Modern Habits
*Goal: Audit daily choices and their long-term impact.*

| Dashboard | User Value | Visualization Type | Data Logic / Calculation | Advisor Insight / Tip |
| :--- | :--- | :--- | :--- | :--- |
| **13. Subscription Dustbin** | Reclaims leaked money. | **Bin with Dollar signs** | `Total Recurring app/service spends (Monthly * 120)` | "Canceling 3 unused apps saves you ₹4L over your working life." |
| **14. Inflation Ghost** | Explains rising costs. | **Fading Text / Ghost Effect** | `Current Cost * (1 + Inflation)^Years` | "You'll need ₹1.6L in 2030 to live like you do on ₹1L today." |
| **15. Debt Snowball** | Clear path out of debt. | **Snowball Rolling Down** | `Liabilities ordered by Interest Rate / APR` | "Kill the Credit Card first. It's a 42% interest emergency." |
| **16. Lifestyle Creep** | Detects hidden upgrades. | **Splitting Path Chart** | `Income Trend-line vs. Expense Trend-line` | "Eating out grew 4x faster than your salary. Slow down to stay on track." |

---

## 🌳 Phase 5: Legacy & Wisdom
*Goal: Long-term impact and peace of mind.*

| Dashboard | User Value | Visualization Type | Data Logic / Calculation | Advisor Insight / Tip |
| :--- | :--- | :--- | :--- | :--- |
| **17. Passive Orchard** | Tracks 'Work-Optional' status. | **Growing Tree with Fruits** | [(Investment Income / Total Expenses) * 100](file:///c:/Users/kvamsi/sources/ledger-3.0/frontend/src/OnboardingV2.jsx#535-536) | "Your fruits just paid your Internet bill. Next target: Your Rent!" |
| **18. "What-If" Machine** | Life transition modeling. | **Parallel Timelines (A vs B)** | `User input variables (Sabbatical, Kid, etc.)` | "A 1-year sabbatical moves your retirement back by 1.5 years. Worth it?" |
| **19. Philanthropy Dash** | Deliberate giving. | **Heart Expansion Chart** | [(Safe Giving Capacity / Total Surplus)](file:///c:/Users/kvamsi/sources/ledger-3.0/frontend/src/OnboardingV2.jsx#535-536) | "You can give ₹5k/mo forever without affecting your family's safety." |
| **20. Financial Karma** | Ensures wealth readiness. | **Checklist / Legal Seal** | `Nomination Status % across all manually entered info` | "3 accounts have no nominees. They risk being lost if you aren't here." |
