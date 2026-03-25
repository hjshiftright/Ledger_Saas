# Onboarding Module — Granular Decomposition

Let me first identify all the sub-modules within Onboarding by referring back to everything we've discussed, and then break each one into the smallest buildable, testable units.

---

## Onboarding Sub-Modules (Complete List)

Based on our conversations, onboarding encompasses these sub-modules:

1. **Profile Creation** — user identity, preferences, tax regime
2. **Chart of Accounts (COA) Setup** — default tree generation + customization
3. **Institution Registration** — adding banks, brokerages, AMCs
4. **Account Setup** — bank, credit card, loan, brokerage, FD, RD, PF, etc.
5. **Opening Balances** — initial balance entry for each account
6. **Goal Planner** — setting up financial goals with account mappings
7. **Budget Setup** — creating the first monthly/yearly budget
8. **Recurring Transaction Templates** — SIP, EMI, rent, subscriptions
9. **Net Worth Creation** — computing initial net worth from all set-up accounts
10. **Onboarding Orchestrator** — step sequencing, skip logic, completion tracking

---

## Dependency Graph Between Sub-Modules

Before decomposing, understanding what depends on what tells us the build order:

```
Profile Creation
      │
      ▼
COA Setup ─────────────────────────────────────┐
      │                                         │
      ▼                                         │
Institution Registration                        │
      │                                         │
      ▼                                         │
Account Setup                                   │
      │                                         │
      ├──────────┬──────────┬───────────┐       │
      ▼          ▼          ▼           ▼       │
Opening      Goal       Budget      Recurring   │
Balances     Planner    Setup       Templates   │
      │          │          │           │       │
      ▼          ▼          ▼           ▼       │
      └──────────┴──────────┴───────────┘       │
                      │                         │
                      ▼                         │
               Net Worth Creation ◄─────────────┘
                      │
                      ▼
            Onboarding Complete
```

Profile must come first because it determines currency and tax regime. COA must come before accounts because accounts are leaf nodes in the COA tree. Institutions must come before accounts because each account belongs to an institution. Opening balances, goals, budget, and recurring templates all depend on accounts existing but are independent of each other. Net worth comes last because it aggregates across all accounts and opening balances.

---

## Granular Decomposition — Micro-Milestones

Each item below is a single, independently buildable and testable unit. I've numbered them with a scheme: `ON-{submodule}-{sequence}`. Each one has a clear input, output, and test criteria.

---

### Sub-Module 1: Profile Creation

**ON-PROF-1: Profile DTO and Validation Rules**

Define the `ProfileSetupDTO` with all fields — user display name, base currency code, financial year start month (April for India), tax regime (old vs new), date format preference, and number format preference (Indian lakh/crore vs international). Write Pydantic validators for each field. Currency code must be a valid ISO 4217 code from a known list. Tax regime must be one of the allowed enum values. FY start month must be 1-12.

Testable by: Unit tests that pass valid profiles and verify acceptance, and pass invalid profiles (empty name, unknown currency code, invalid month) and verify rejection with correct error messages.

**ON-PROF-2: Profile Service — Save and Retrieve**

A `ProfileService` class with two methods: `setup_profile(dto: ProfileSetupDTO) -> ProfileDTO` and `get_profile() -> Optional[ProfileDTO]`. Internally calls `SettingsRepository.set()` to persist each profile field as a key-value setting (e.g., `user.display_name`, `user.base_currency`, `user.tax_regime`, `user.fy_start_month`). Retrieval reads these keys back and assembles a `ProfileDTO`.

Testable by: Using an in-memory stub `SettingsRepository` (a Python dict), call `setup_profile`, then call `get_profile` and assert all fields round-trip correctly. Test that calling `setup_profile` twice overwrites cleanly.

**ON-PROF-3: Profile Completion Check**

A method `is_profile_complete() -> bool` on `ProfileService` that checks whether all required settings keys exist and have non-empty values. This is used by the orchestrator to determine if this step can be marked done.

Testable by: Assert returns `False` on empty settings, returns `True` after `setup_profile`, returns `False` if any required key is manually deleted from the stub.

---

### Sub-Module 2: Chart of Accounts (COA) Setup

**ON-COA-1: Default COA Tree Definition (Data Only)**

A Python data structure (list of dicts or a YAML/JSON file) that defines the full default Chart of Accounts tree. This is purely static data — no database interaction. The structure encodes parent-child relationships, account codes, names, types, subtypes, normal balances, display order, and which nodes are placeholders vs leaf-ready.

Example fragment:

```python
DEFAULT_COA = [
    {
        "code": "1000", "name": "Assets",
        "type": "ASSET", "normal_balance": "DEBIT",
        "is_placeholder": True, "children": [
            {
                "code": "1100", "name": "Bank Accounts",
                "type": "ASSET", "subtype": "BANK",
                "is_placeholder": True, "children": []
            },
            {
                "code": "1200", "name": "Cash",
                "type": "ASSET", "subtype": "CASH",
                "is_placeholder": True, "children": []
            },
            # ...
        ]
    },
    # Liabilities, Income, Expense, Equity...
]
```

Testable by: Unit test that walks the tree and asserts every node has required fields, all codes are unique, all parent-child type relationships are valid (child of ASSET is ASSET), and the tree has the expected top-level nodes (Assets, Liabilities, Income, Expenses, Equity).

**ON-COA-2: COA Tree Builder — Flatten and Persist**

A `COASetupService` with method `create_default_coa() -> list[AccountDTO]`. It takes the static tree from ON-COA-1, walks it depth-first, and calls `AccountRepository.create()` for each node, setting `parent_id` based on the just-created parent. Returns the flat list of all created accounts.

Testable by: Using an in-memory `AccountRepository` stub, call `create_default_coa()`, then verify the expected number of accounts exist, parent-child relationships are correct (child's `parent_id` matches parent's `id`), and account codes match the template.

**ON-COA-3: COA Tree Retrieval**

A method `get_coa_tree() -> list[AccountTreeNodeDTO]` on `COASetupService` that calls `AccountRepository.get_tree()` and returns the hierarchical structure. This is what the UI would use to display the tree.

Testable by: After `create_default_coa()`, call `get_coa_tree()` and verify the root nodes are the five top-level types, children are nested correctly, and the depth matches expectations.

**ON-COA-4: COA Customization — Rename Account**

A method `rename_account(account_id: int, new_name: str) -> AccountDTO`. Validates that the new name is non-empty, the account exists, and persists the change. System accounts (flagged `is_system=True`) cannot be renamed.

Testable by: Create default COA, rename an expense category, verify the name changed. Try to rename a system account (like "Opening Balances Equity"), verify it raises `SystemAccountModificationError`. Try empty name, verify `ValidationError`.

**ON-COA-5: COA Customization — Add Custom Category**

A method `add_custom_category(parent_id: int, name: str) -> AccountDTO`. Creates a new leaf-capable account under the specified parent. Auto-generates the next available code under that parent. The new account inherits `account_type` and `normal_balance` from the parent.

Testable by: Add a custom category under "Expenses → Food & Dining", verify it gets the correct parent, type, auto-generated code, and appears in the tree. Try adding under a non-placeholder account and verify rejection.

**ON-COA-6: COA Customization — Deactivate Category**

A method `deactivate_category(account_id: int) -> None`. Marks an account as inactive. Cannot deactivate system accounts. Cannot deactivate an account that has transactions posted to it (calls `AccountRepository.has_transactions()`). Cannot deactivate a placeholder that has active children.

Testable by: Deactivate a leaf category with no transactions — verify success. Try deactivating a system account — verify error. Try deactivating a category with transactions — verify error. Try deactivating a placeholder with active children — verify error. Deactivate a placeholder whose all children are already inactive — verify success.

**ON-COA-7: COA Completion Check**

A method `is_coa_ready() -> bool` that verifies the COA has been created (at minimum, the five root accounts exist). Used by the orchestrator.

Testable by: Returns `False` on empty repository, returns `True` after `create_default_coa()`.

---

### Sub-Module 3: Institution Registration

**ON-INST-1: Institution DTOs and Validation**

Define `InstitutionCreateDTO` with fields: name, institution type (enum: BANK, NBFC, BROKERAGE, AMC, INSURANCE, OTHER), website URL (optional), notes (optional). Pydantic validation ensures name is non-empty, institution type is valid.

Testable by: Valid/invalid DTO construction tests.

**ON-INST-2: Institution Service — CRUD**

An `InstitutionService` with methods: `add_institution(dto) -> InstitutionDTO`, `get_institution(id) -> InstitutionDTO`, `list_institutions() -> list[InstitutionDTO]`, `update_institution(id, dto) -> InstitutionDTO`. Duplicate name check on create — if an institution with the same name already exists, raise `DuplicateError`.

Testable by: Add an institution, retrieve it, list all, update it. Try adding a duplicate name, verify error.

**ON-INST-3: Pre-Seeded Institution List (Optional Enhancement)**

A static list of common Indian banks and brokerages (SBI, HDFC, ICICI, Zerodha, Groww, etc.) that can be offered as suggestions during institution creation. This is just a data list — no service logic.

Testable by: Verify the list has entries, each with a name and type.

---

### Sub-Module 4: Account Setup

This is the largest sub-module. Each account type is its own micro-milestone because each has unique fields and validation rules.

**ON-ACCT-1: Account Setup Base Logic**

A base `AccountSetupService` with the common flow: resolve parent account in COA by subtype → generate next code → create COA leaf node → create detail record → audit log → fire event. This is the template that each specific account type follows.

Testable by: Mock test that verifies the sequence of repository calls happens in order. This is the skeleton that all subsequent account types use.

**ON-ACCT-2: Bank Account Setup**

Method `add_bank_account(dto: BankAccountSetupDTO) -> AccountDTO`. The DTO includes: institution_id, display_name, account_number_masked, bank_account_type (SAVINGS, CURRENT, SALARY), IFSC code (optional), branch (optional). Creates a leaf under "Assets → Bank Accounts" (code 1100). Also creates a `bank_accounts` detail record linking the COA account to the institution.

Validation: institution must exist, account_number_masked must be provided, IFSC (if given) must match the pattern `^[A-Z]{4}0[A-Z0-9]{6}$`.

Testable by: Add a bank account, verify COA leaf created under 1100, detail record links to correct institution. Invalid IFSC — verify rejection. Non-existent institution — verify rejection.

**ON-ACCT-3: Credit Card Setup**

Method `add_credit_card(dto: CreditCardSetupDTO) -> AccountDTO`. The DTO includes: institution_id, display_name, last_four_digits, credit_limit, billing_cycle_day (1-28), interest_rate_annual. Creates a leaf under "Liabilities → Credit Cards" (code 2200). Also creates a `credit_cards` detail record.

Validation: credit_limit > 0, billing_cycle_day between 1-28, interest_rate >= 0.

Testable by: Add a credit card, verify COA leaf is under Liabilities with CREDIT normal balance. Invalid billing day (29) — verify rejection. Zero credit limit — verify rejection.

**ON-ACCT-4: Loan Setup**

Method `add_loan(dto: LoanSetupDTO) -> AccountDTO`. The DTO includes: institution_id, display_name, loan_type (HOME, VEHICLE, PERSONAL, EDUCATION, GOLD, OTHER), principal_amount, interest_rate, tenure_months, emi_amount, start_date, linked_asset_account_id (optional, for home/vehicle loans). Creates a leaf under "Liabilities → Loans" (code 2300). Creates a `loans` detail record.

Validation: principal > 0, rate >= 0, tenure > 0, EMI > 0, start_date not in the future by more than 30 days.

Testable by: Add a home loan, verify COA leaf under Liabilities → Loans. Verify detail record has correct fields. Link to an asset account — verify the link is stored. Invalid tenure (0) — verify rejection.

**ON-ACCT-5: Brokerage/Demat Account Setup**

Method `add_brokerage_account(dto: BrokerageSetupDTO) -> AccountDTO`. The DTO includes: institution_id, display_name, demat_id (optional), default_cost_basis_method (FIFO, AVERAGE). Creates a leaf under "Assets → Investments → Brokerage Accounts" (code 1500). Creates a `brokerage_accounts` detail record.

Testable by: Add a brokerage account, verify it's under Assets → Investments. Verify cost basis method defaults to FIFO if not specified.

**ON-ACCT-6: Fixed Deposit Setup**

Method `add_fixed_deposit(dto: FixedDepositSetupDTO) -> AccountDTO`. DTO includes: institution_id, display_name, principal_amount, interest_rate, start_date, maturity_date, compounding_frequency, auto_renew flag. Creates a leaf under "Assets → Fixed Deposits" (code 1600). Creates `fixed_deposits` detail record.

Validation: maturity_date > start_date, principal > 0, rate > 0.

Testable by: Add an FD, verify COA placement and detail record. Maturity before start — verify rejection.

**ON-ACCT-7: Other Account Types (RD, PF, PPF, NPS, Insurance)**

Each follows the same pattern. These can be implemented as a batch since they share the same structure as ON-ACCT-6 with minor field variations. Each gets its own DTO, its own place in the COA tree, and its own detail record.

Testable by: Same pattern — verify COA placement, detail record creation, and field validation.

**ON-ACCT-8: Cash Wallet Account (Special Case)**

A simple method that creates a "Cash in Hand" account under "Assets → Cash" with no institution linkage and no detail record. This is the simplest account type.

Testable by: Create cash account, verify it's under Assets → Cash, no institution link needed.

---

### Sub-Module 5: Opening Balances

**ON-OB-1: Opening Balance DTO and Validation**

Define `OpeningBalanceDTO` with fields: account_id, balance_amount, balance_date, and notes (optional). Validation: account must exist, balance_date must be provided, amount can be zero (for accounts with no starting balance) but not negative for asset accounts.

Testable by: Valid/invalid DTO tests.

**ON-OB-2: Opening Balance Transaction Generator**

An `OpeningBalanceService` with method `set_opening_balance(dto: OpeningBalanceDTO) -> TransactionDTO`. This creates a double-entry transaction of type `OPENING_BALANCE`:

For an asset account with positive balance, the entry is debit the asset account and credit the "Equity → Opening Balances" account. For a liability account (credit card balance, loan outstanding), the entry is debit the "Equity → Opening Balances" account and credit the liability account. The service must locate the system "Equity → Opening Balances" account automatically.

Testable by: Set opening balance for a bank account (\₹50,000), verify a transaction is created with two lines, debit side = credit side = 50,000, the asset account is debited, the equity account is credited. Set opening balance for a credit card (\₹15,000 outstanding), verify the liability is credited and equity is debited. Set opening balance of 0 — verify no transaction is created (or a zero transaction, depending on design decision — document the choice).

**ON-OB-3: Opening Balance — Prevent Duplicates**

Logic to check whether an opening balance transaction already exists for a given account. If one exists, the service should either update it (void the old one and create a new one) or reject the duplicate with a clear error.

Testable by: Set opening balance for Account A, try setting it again with a different amount. Verify the old transaction is voided and a new one is created (or verify the error, depending on chosen behavior).

**ON-OB-4: Opening Balance — Bulk Entry**

A method `set_opening_balances_bulk(entries: list[OpeningBalanceDTO]) -> list[TransactionDTO]` that processes multiple opening balances in one call. Each entry generates its own transaction. If any entry fails validation, the entire batch fails (atomic behavior).

Testable by: Submit 5 opening balances, verify 5 transactions created. Submit 5 where the 3rd has invalid data, verify all 5 are rejected (nothing persisted).

---

### Sub-Module 6: Goal Planner

**ON-GOAL-1: Goal DTOs and Validation**

Define `GoalCreateDTO` with: name, goal_type (enum), target_amount, target_date (optional), start_date, priority (HIGH/MEDIUM/LOW), expected_return_rate (optional), notes. Validation: target_amount > 0, target_date (if provided) must be after start_date, name non-empty.

Testable by: Valid/invalid DTO tests.

**ON-GOAL-2: Goal Creation Service**

A `GoalSetupService` with method `create_goal(dto: GoalCreateDTO) -> GoalDTO`. Persists the goal via `GoalRepository.create()`. Sets initial `current_amount = 0`, `progress_percentage = 0`, `status = ACTIVE`.

Testable by: Create a goal, retrieve it, verify all fields including computed defaults.

**ON-GOAL-3: Goal — Account Mapping**

A method `link_accounts_to_goal(goal_id: int, account_ids: list[int]) -> None`. Links one or more accounts to a goal, meaning transactions hitting these accounts contribute to this goal. Validates that all accounts exist and are leaf accounts.

Testable by: Create a goal, link two bank accounts to it. Verify mappings are stored. Try linking a non-existent account — verify error. Try linking a placeholder account — verify error.

**ON-GOAL-4: Goal — Milestone Definition**

A method `add_milestone(goal_id: int, dto: GoalMilestoneCreateDTO) -> GoalMilestoneDTO`. Milestones are intermediate targets within a goal (e.g., "Save first ₹1 lakh" at 10% of a ₹10L goal). DTO has: name, target_amount or target_percentage, target_date (optional).

Testable by: Add 3 milestones to a goal, verify they're stored in order. Add a milestone with target_amount > goal's target_amount — verify rejection.

**ON-GOAL-5: Goal — Monthly Contribution Calculator**

A utility method `calculate_required_monthly_contribution(goal: GoalDTO) -> float` that computes how much must be saved monthly to hit the target by the target date, optionally accounting for expected returns. Formula: if no expected return, it's simply `(target - current) / months_remaining`. With expected return, use a basic future value of annuity formula.

Testable by: Goal of ₹10,00,000, starting from 0, 24 months, no return → ₹41,667/month. Same with 12% annual return → verify against hand-calculated value using annuity formula.

**ON-GOAL-6: Goal — List and Summary**

A method `get_all_goals() -> list[GoalDTO]` and `get_goal_summary() -> GoalSummaryDTO` that returns all active goals with their current progress. The summary includes total target across all goals, total saved across all goals, and overall progress percentage.

Testable by: Create 3 goals with different targets and progress, verify summary aggregation is correct.

---

### Sub-Module 7: Budget Setup

**ON-BUD-1: Budget DTOs and Validation**

Define `BudgetCreateDTO` with: name, period_type (MONTHLY or YEARLY), start_date, end_date, line items. Each line item has: account_id (must be an expense or income category from the COA), budgeted_amount, notes. Validation: start_date < end_date, at least one line item, all amounts > 0, no duplicate account_ids.

Testable by: Valid/invalid DTO tests including duplicate account check.

**ON-BUD-2: Budget Creation Service**

A `BudgetSetupService` with method `create_budget(dto: BudgetCreateDTO) -> BudgetDTO`. Persists the budget and its line items. Validates that all referenced account_ids are valid expense or income categories (not asset or liability accounts).

Testable by: Create a monthly budget with 5 expense categories, verify persistence. Try creating with an asset account_id — verify rejection.

**ON-BUD-3: Budget — Auto-Generate from COA**

A helper method `generate_budget_template() -> BudgetCreateDTO` that creates a budget template pre-populated with all active expense categories from the COA, each with budgeted_amount = 0. This gives the user a starting point to fill in amounts rather than selecting categories manually.

Testable by: After COA setup, call `generate_budget_template()`, verify it has one line item per active expense leaf category, all amounts are 0.

---

### Sub-Module 8: Recurring Transaction Templates

**ON-REC-1: Recurring Transaction DTOs and Validation**

Define `RecurringTransactionCreateDTO` with: name, template_type (SIP, EMI, RENT, SALARY_CREDIT, SUBSCRIPTION, CUSTOM), frequency (enum), start_date, end_date (optional), amount, from_account_id, to_account_id (or full transaction lines for complex templates), description template, auto_post flag (whether to auto-create transactions or just remind). Validation: amount > 0, start_date provided, if end_date then end_date > start_date, both accounts must exist.

Testable by: Valid/invalid DTO tests.

**ON-REC-2: Recurring Template Creation Service**

A `RecurringTemplateService` with method `create_template(dto: RecurringTransactionCreateDTO) -> RecurringTransactionDTO`. Computes `next_occurrence_date` based on start_date and frequency. Persists the template.

Testable by: Create a monthly SIP template starting on the 5th of next month. Verify `next_occurrence_date` is correctly computed. Create an EMI template, verify fields.

**ON-REC-3: Recurring — SIP Convenience Method**

A specialized method `setup_sip(dto: SIPSetupDTO) -> RecurringTransactionDTO` where `SIPSetupDTO` has: mutual_fund_name or security_id, sip_amount, sip_date (day of month), from_account_id (bank), to_account_id (brokerage), start_date. Internally creates the recurring template with the right transaction type (`SIP_PURCHASE`) and frequency (`MONTHLY`).

Testable by: Create a SIP for ₹5,000 on the 10th of each month from HDFC savings to Zerodha brokerage. Verify the underlying template has correct type, frequency, accounts, and amount.

**ON-REC-4: Recurring — EMI Convenience Method**

A specialized method `setup_emi(dto: EMISetupDTO) -> RecurringTransactionDTO` where the DTO links to a loan account, has EMI amount, debit account (bank), and frequency (typically MONTHLY). Creates a template with type `EMI_PAYMENT`.

Testable by: Create an EMI for ₹25,000/month debiting savings and crediting loan account. Verify template.

**ON-REC-5: Recurring — List Templates**

A method `list_templates() -> list[RecurringTransactionDTO]` returning all created templates with their next occurrence dates.

Testable by: Create 3 templates, list them, verify count and data.

---

### Sub-Module 9: Net Worth Creation

**ON-NW-1: Net Worth Computation Logic**

A `NetWorthService` with method `compute_initial_net_worth(as_of: date) -> NetWorthSnapshotDTO`. This aggregates all asset account balances (positive) and subtracts all liability account balances (positive = debt) to produce a single net worth figure. The method breaks it down by category — liquid assets (bank + cash), investments (brokerage + MF + FD), illiquid assets (property), short-term liabilities (credit cards), long-term liabilities (loans).

The computation uses `AccountRepository.get_balance()` for each active leaf account as of the given date.

Testable by: Set up 3 accounts with opening balances (Bank: ₹1,00,000, FD: ₹5,00,000, Credit Card: ₹20,000). Compute net worth → ₹5,80,000. Verify category breakdown.

**ON-NW-2: Net Worth — Persist Snapshot**

After computation, persist the snapshot using `SnapshotRepository.save_net_worth()`. This is the baseline net worth at onboarding time, which all future net worth tracking compares against.

Testable by: Compute and save net worth, retrieve it, verify amounts match.

**ON-NW-3: Net Worth — Display Summary**

A method `get_net_worth_summary(as_of: date) -> NetWorthDisplayDTO` that returns the structured data needed for a UI display: total assets, total liabilities, net worth, and the breakdown by category. This is a read-only method.

Testable by: After setting opening balances and computing net worth, call summary and verify all sections have correct totals.

---

### Sub-Module 10: Onboarding Orchestrator

**ON-ORCH-1: Step Definition and State Model**

Define the `OnboardingStep` enum (PROFILE, COA_SETUP, INSTITUTION_REGISTRATION, ACCOUNT_SETUP, OPENING_BALANCES, GOAL_PLANNING, BUDGET_SETUP, RECURRING_TEMPLATES, NET_WORTH_REVIEW) and `OnboardingStepStatus` enum (PENDING, IN_PROGRESS, COMPLETED, SKIPPED). Define `OnboardingStateDTO` containing a list of steps with their statuses and a computed overall progress percentage.

Testable by: Verify enum values, verify state DTO correctly computes progress (3 of 9 steps completed = 33%).

**ON-ORCH-2: Step Sequence and Skip Rules**

Define which steps are mandatory (PROFILE, COA_SETUP, ACCOUNT_SETUP) and which are skippable (INSTITUTION_REGISTRATION if accounts are added without institution, GOAL_PLANNING, BUDGET_SETUP, RECURRING_TEMPLATES). Define the ordering — step N cannot be started until step N-1 is completed or skipped.

Testable by: Verify that attempting to start ACCOUNT_SETUP before completing COA_SETUP raises an error. Verify that skipping GOAL_PLANNING is allowed. Verify that skipping PROFILE is not allowed.

**ON-ORCH-3: Step Transition Logic**

Methods `start_step(step: OnboardingStep)`, `complete_step(step: OnboardingStep)`, `skip_step(step: OnboardingStep)`. Each validates the transition is legal (can't complete a step that hasn't been started, can't skip a mandatory step). State is persisted via `SettingsRepository` as a JSON blob under key `onboarding.state`.

Testable by: Walk through the full happy path — start and complete each step in order. Verify state after each transition. Try illegal transitions and verify errors.

**ON-ORCH-4: Completion Detection and Finalization**

A method `complete_onboarding() -> None` that verifies all mandatory steps are completed, marks the overall onboarding as done (setting `onboarding.completed = true`), and triggers net worth computation. A method `is_onboarding_complete() -> bool` for the rest of the application to check.

Testable by: Complete all mandatory steps, call `complete_onboarding()`, verify `is_onboarding_complete()` returns `True`. Try completing with a mandatory step still pending — verify error.

**ON-ORCH-5: Resume Onboarding**

A method `get_next_step() -> OnboardingStep` that returns the first step that is still PENDING or IN_PROGRESS. This handles the case where the user closes the app mid-onboarding and returns later.

Testable by: Complete first 3 steps, call `get_next_step()`, verify it returns step 4.

---

## Build Sequence — Recommended Order

Here's how Hari should sequence these micro-milestones, grouping them into weekly sprints:

```
Week 1: Foundation
─────────────────────────────
  ON-PROF-1  Profile DTOs + validation
  ON-PROF-2  Profile service (save/retrieve)
  ON-PROF-3  Profile completion check
  ON-COA-1   Default COA tree data definition
  ON-COA-2   COA tree builder (persist default tree)
  ON-COA-3   COA tree retrieval

Week 2: COA Customization + Institutions + First Accounts
─────────────────────────────
  ON-COA-4   Rename account
  ON-COA-5   Add custom category
  ON-COA-6   Deactivate category
  ON-COA-7   COA completion check
  ON-INST-1  Institution DTOs
  ON-INST-2  Institution CRUD service
  ON-ACCT-1  Account setup base logic
  ON-ACCT-2  Bank account setup

Week 3: Remaining Account Types + Opening Balances
─────────────────────────────
  ON-ACCT-3  Credit card setup
  ON-ACCT-4  Loan setup
  ON-ACCT-5  Brokerage account setup
  ON-ACCT-6  Fixed deposit setup
  ON-ACCT-7  Other account types (batch)
  ON-ACCT-8  Cash wallet account
  ON-OB-1    Opening balance DTOs
  ON-OB-2    Opening balance transaction generator
  ON-OB-3    Duplicate prevention
  ON-OB-4    Bulk entry

Week 4: Goals, Budget, Recurring, Net Worth, Orchestrator
─────────────────────────────
  ON-GOAL-1  Goal DTOs
  ON-GOAL-2  Goal creation service
  ON-GOAL-3  Goal-account mapping
  ON-GOAL-4  Milestone definition
  ON-GOAL-5  Monthly contribution calculator
  ON-GOAL-6  Goal list and summary
  ON-BUD-1   Budget DTOs
  ON-BUD-2   Budget creation service
  ON-BUD-3   Auto-generate budget template
  ON-REC-1   Recurring DTOs
  ON-REC-2   Template creation service
  ON-REC-3   SIP convenience method
  ON-REC-4   EMI convenience method
  ON-REC-5   List templates
  ON-NW-1    Net worth computation
  ON-NW-2    Persist snapshot
  ON-NW-3    Display summary
  ON-ORCH-1  Step definitions
  ON-ORCH-2  Skip rules
  ON-ORCH-3  Step transitions
  ON-ORCH-4  Completion + finalization
  ON-ORCH-5  Resume onboarding
```

---

## Integration Checkpoints

Rather than waiting until the end, Hari integrates with Kalyan's real repositories at two checkpoints:

**Checkpoint 1 (End of Week 2):** Swap in Kalyan's real `AccountRepository`, `InstitutionRepository`, and `SettingsRepository`. Run Profile + COA + Institution + Bank Account tests against real SQLite. Fix any contract mismatches.

**Checkpoint 2 (End of Week 4):** Swap in all remaining real repositories. Run the full onboarding flow end-to-end: create profile → set up COA → add institution → add 3 accounts of different types → set opening balances → create a goal → create a budget → set up a SIP template → compute net worth. Verify the database has all expected records.

---

Shall I do the same decomposition for Raj's Transaction Management module next, or would you like to refine any of these onboarding micro-milestones first?