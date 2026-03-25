# Ledger — UX Detailed Requirements & Options

**Version:** 1.0  
**Date:** March 17, 2026  
**Status:** Draft for Review  

> **Scope:** This document provides screen-by-screen detailed requirements for the Ledger onboarding flow and presents **three distinct UX design options** for the team to choose from. It builds upon the foundations laid in `ux_requirements.md` and `ux_prd.md`.

---

## 1. Global Interactions & Layout Elements

### 1.1 Context Continuity
- **Progress Header:** Always visible at the top, showing the 4 stages. Active stage is bold/accent color. Completed stages are clickable to return.
- **Escape Hatch:** A "Skip for now" or "Save & Exit" button always available in the top right.
- **Save State:** Every field modification auto-saves to local storage. 

### 1.2 The AI Assistant Panel
The AI assistant is a core feature.
- **Collapsed state:** A floating action button (FAB) or minimal sidebar showing a friendly AI avatar and a greeting.
- **Expanded state:** A 350px right sidebar displaying chat history.
- **Contextual Awareness:** The AI knows exactly what screen the user is on and what fields are blank. "I see you haven't added a bank account yet. Want me to help?"

---

## 2. Screen-by-Screen Detailed Requirements

### 2.1 Screen 1: Welcome & Profile

**Objective:** Capture basic info and assign a persona.

**Layout Elements:**
1. **Headline:** "Let's personalize your ledger." (H1)
2. **Subheadline:** "Tell us a bit about yourself so we can set up the right foundation." (H2)
3. **Basic Info Form (Left/Top):**
   - First Name (Required text)
   - Last Name (Optional text)
   - Age (Number, used for retirement calculations)
4. **Persona Selector (Center/Bottom):**
   - Label: "Which of these best describes your current financial life?"
   - Grid of Persona Cards (as defined in `ux_prd.md`).
   - Cards are selectable toggle buttons. Outline gets thick accent color when selected.
   - *Micro-interaction:* Selecting a card updates a small summary box below it: *"We'll set up standard accounts for a salaried professional, including EPF and Mutual Funds."*
5. **Primary Action:** "Continue to Accounts" button (disabled until Name and 1 Persona selected).

### 2.2 Screen 2: Chart of Accounts & Opening Balances

**Objective:** Confirm assets and liabilities, and enter starting balances.

**Layout Elements:**
1. **Headline:** "Your Financial Map" (H1)
2. **Subheadline:** "We've pre-selected common accounts based on your profile. Add, remove, and enter your current balances." (H2)
3. **Net Worth Ticker (Sticky Top/Right):**
   - Shows live calculation: Assets - Liabilities.
   - Starts at ₹0. Updates immediately as balances are typed.
4. **Account Categories (Vertical Accordions or Tabs):**
   - **Assets Toggle:** Expands to show Bank Accounts, Investments, Real Estate, etc.
   - **Liabilities Toggle:** Expands to show Loans, Credit Cards.
5. **Account Entry Rows (Inside Categories):**
   - Name input (e.g., "HDFC Savings")
   - Balance input with ₹ symbol prefix.
   - Delete icon (trash can) to remove the row.
   - "+ Add another [Category]" button at the bottom of each list.
6. **Primary Action:** "Confirm & Continue" button.

### 2.3 Screen 3: Financial Goals

**Objective:** Define future targets to drive dashboard metrics.

**Layout Elements:**
1. **Headline:** "What are you saving for?" (H1)
2. **Subheadline:** "Set targets to track your progress and let Ledger calculate what you need to save." (H2)
3. **Goal Carousel / Grid:**
   - Display cards for Retirement, Education, Emergency, etc.
   - User clicks a card to enable that goal.
4. **Active Goal Configurator (Drawer or Modal):**
   - When a goal is clicked, a panel opens.
   - Example (Emergency): "Target Months of Expenses" slider (3 to 12).
   - "Current Savings Allocated" input.
   - Ledger displays: "Target Amount: ₹X", "Shortfall: ₹Y".
5. **Goal Summary List:**
   - Shows minimized rows of all active/configured goals below the carousel.
6. **Primary Action:** "Generate Dashboard" button. (Optional: "Skip Goals" text link).

### 2.4 Screen 4: The Net Asset Dashboard

**Objective:** Deliver the "Wow" moment. Provide a clear, actionable overview of their wealth.

**Layout Elements:**
1. **Header:** Personalized greeting ("Welcome to your Ledger, [Name]").
2. **Top Row (Metrics):**
   - Net Worth Card (Giant number + Asset/Liability breakdown).
   - Monthly Surplus Card (Income - Expenses).
3. **Middle Row (Visuals):**
   - Asset Allocation Donut Chart (e.g., Cash 20%, Equity 50%, Debt 30%).
   - Liquid vs. Locked Funds bar chart.
4. **Bottom Row (Actionable):**
   - Goals Progress table (progress bars for configured goals).
   - AI Insights Box: "Here are 3 things I noticed about your setup..."
5. **Primary Action:** "Go to Ledger Dashboard" (Exits onboarding, enters main app).

---

## 3. Universal Principle: The Ubiquitous AI Assistant

**AI is not a separate UX layout; it is a universal capability present in all design options.** 
Regardless of which visual path is chosen, the AI assistant must be available as a contextual helper that can:
- **Auto-fill & Suggest:** Parse user text to select personas or populate account balances.
- **Educate:** Answer questions about financial concepts (e.g., "What is a standard emergency fund size?").
- **Audit:** Act as a reviewer (e.g., "You added a home loan but no property asset. Did you miss something?").

---

## 4. Three Distinct UX Design Options

To provide the team with diverse visual and interaction models, here are three distinct UX options. Each integrates the **Universal AI Assistant** differently to match its unique vibe.

### Option A: The "Modern FinTech" Approach (Focus on Speed & Cards)

**Vibe:** Very similar to modern neo-banks (Jupiter, Fi) or investing apps (Zerodha Kite). Clean, sparse, heavily card-based.
**Color Palette:** Lots of white space, stark black text, bright accent colors (Neon Green for assets, Hot Pink for liabilities).
**Key Interaction Model:**
- **Wizard style:** One concept per screen. No scrolling.
- **Card Selection:** Users answer questions by clicking large visual cards.
- **Transitions:** Snappy horizontal slide animations.
- **AI Integration:** AI is a friendly Floating Action Button (FAB) in the corner. Clicking it opens a bottom-sheet chat where the user can say "I have accounts at HDFC and SBI", and the AI instantly maps this to select the relevant cards on the screen.
**Pros:** Extremely fast onboarding. Familiar to younger, app-native users.
**Cons:** Harder to view the "big picture" at once. Can feel overly simplistic for complex users.

### Option B: The "Narrative Journey" Approach (Focus on Storytelling)

**Vibe:** Feels like a guided journal or "Mad-Libs" style interactive article (similar to Typeform or early Wealthfront onboarding).
**Color Palette:** Warm, calming colors (Oatmeal backgrounds, Forest Green text, soft Serif fonts) to reduce financial anxiety.
**Key Interaction Model:**
- **Flowing Document:** The user fills in blanks in plain-English sentences seamlessly. 
  *(e.g., "Hi, I'm [ Name ]. I work as a [ Dropdown ] and my primary bank is [ Dropdown ]. I want to make sure I'm ready to retire by age [ 60 ].")*
- **Progressive Expansion:** Completing one block of text gracefully fades in the next paragraph of their financial "story."
- **AI Integration:** The AI acts as a "Co-Author." Users can choose to simply type a messy paragraph ("I make 10L a year, pay 20k rent, and have an HDFC account") and the AI extracts it to auto-build the structured narrative blocks instantly.
**Pros:** Exceptionally human and approachable. Eliminates all feeling of "filling out a form." 
**Cons:** Less efficient for users who just want to input numbers rapidly.

### Option C: The "Pro Dashboard" Approach (Focus on Density & Control)

**Vibe:** Feels like a lightweight version of professional software (Notion, Linear, or Bloomberg Terminal). Highly structured, data-dense.
**Color Palette:** Neutral slate greys, subtle borders, muted primary colors (Slate, Emerald, Crimson).
**Key Interaction Model:**
- **Single Page Application (SPA) feel:** Instead of a multi-step wizard, all stages (Profile, Accounts, Goals) are presented on a single, long-scrolling dashboard canvas.
- **Spreadsheet-like Entry:** Chart of Accounts is presented like a clean, inline-editable data table. Users can tab through fields quickly to enter balances rapidly.
- **AI Integration:** AI acts as a "Copilot / Auditor" in a persistent right-hand sidebar. As the user fills out the dense tables, the AI panel gives real-time suggestions: *"I see you added a Home Loan but no Real Estate asset. Shall I create a generic Property asset to balance this?"*
**Pros:** Power users, business owners, and accounting-savvy users will love the density and speed of data entry. Everything is visible at once.
**Cons:** Can be overwhelming for the "Early Starter" persona. Requires excellent visual hierarchy to prevent cognitive overload.

### Option D: Command-First Terminal (The Power Entry)
- **Target Persona**: Developers, Accountants, Speed-users.
- **Philosophy**: Efficiency over Visuals. "No-mouse" onboarding.
- **Onboarding Interface**: A minimalist command bar at the center of the screen.
- **Key Flow**: 
    1. Users type things like `name Vamsi age 30`.
    2. Suggestion engine predicts next commands (e.g., `/add-bank HDFC 500k`).
    3. Multi-currency and tax tags are handled via "flags" (e.g., `--tax=GST`).
- **Scenario Coverage**: High-speed bulk entry for users with 10+ accounts.

### Option E: Visual Topology (The Wealth Map)
- **Target Persona**: Family Offices, Trust Managers, Entrepeneurs with multiple holdings.
- **Philosophy**: Relationships over Lists. Understanding the "Flow" of money.
- **Onboarding Interface**: A node-graph canvas.
- **Key Flow**: 
    1. Drag a "Bank" icon onto the canvas.
    2. Connect it to a "Liability" (Loan) icon.
    3. View the "Net Worth" as the central hub node that grows/shrinks as connections are made.
- **Scenario Coverage**: Complex ownership structures, inter-account transfers, and visual auditing of debts.

## Universal Scenario Handling (Production-Grade Prototype)
To ensure the UX is not "just an idea", the prototypes must demonstrate:
1. **Unbalanced States**: Visual indicators when Assets != Liabilities + Equity (for double-entry logic).
2. **Error Feedback**: Inline validation for non-INR currencies or invalid fiscal years.
3. **Draft Persistence**: Simulate "Save & Resume" behavior.
4. **Contextual AI**: The AI shouldn't just talk; it should "fix" the state (e.g., "I've added a GST liability account to match your Business persona").

---

---

## 5. Phase 2: Enhanced & Fulfilling UX Options (F-J)

Following user feedback on the initial options, these 5 additional models focus on depth, scenario coverage, and production-grade interaction.

### Option F: The Bento Box Grid (Single-Screen Modular)
- **Vibe:** Modern Apple-style "Bento" layout.
- **Philosophy:** All 4 stages are visible simultaneously as modular widgets.
- **Mechanism:** Stages 1-4 are "locked" widgets. Completing Stage 1 unlocks Stage 2's widget. The grid gradually transforms from an empty state into the final Dashboard.
- **Fulfills:** The need to see the "Big Picture" while focusing on one task.

### Option G: The Conversational Canvas (Live AI-UI Hybrid)
- **Vibe:** AI Sidebar + Interactive Visualization on the right.
- **Philosophy:** The AI handles the "Entry", the Canvas handles the "State".
- **Mechanism:** As you chat with the AI, it "throws" cards (Personas, Bank accounts) onto the canvas. You can click these cards to edit details AI might have missed.
- **Fulfills:** High-friction data entry scenarios by offloading them to AI while maintaining control.

### Option H: The Glassmorphic Atomic Stepper (High-End Aesthetic)
- **Vibe:** Translucent, premium, "Glassmorphism" UI.
- **Philosophy:** Apple-style simplicity—one decision per screen.
- **Mechanism:** Extremely high-end transitions (blur, scale, fade). Instead of one large form, it's 12 atomic steps (Name? Age? Persona? Bank 1? Balance?).
- **Fulfills:** Reducing cognitive overload for complex financial setups.

### Option I: The Split-View Previewer (Pro-Transparency)
- **Vibe:** Dual-pane (VS Code style).
- **Philosophy:** Transparency into the Double-Entry system.
- **Mechanism:** Left Pane: Wizard/Form. Right Pane: Live "Financial Health" summary that reacts to every keystroke (Net Worth, Debt Ratio, etc.).
- **Fulfills:** Users who want to see exactly how an account or goal affects their overall status instantly.

### Option J: The Milestone "Quest" Flow (Gamified Progress)
- **Vibe:** Duolingo or RPG.
- **Philosophy:** Onboarding as a "Financial Quest".
- **Mechanism:** Stage 1: "The Identity", Stage 2: "Gathering Assets". Progress is measured in "Financial Fitness XP". Reaching the Dashboard is the "Grand Finale".
- **Fulfills:** Engagement for the "Early Starter" or younger personas who find finance boring/scary.

---

## 6. Recommendation for Next Steps

1. **Review and Select:** The product team should review these three distinct visual/interaction models (Cards vs. Narrative vs. Dashboard) and select the direction that best fits the target audience.
2. **Prototyping:** Based on the selected option, self-contained HTML/CSS/JS prototypes can be built in `/docs/ux/` to demonstrate the flow without touching the React frontend.
3. **User Testing:** Validate the chosen flow with target personas before implementing it in the main application.
