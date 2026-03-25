# Onboarding Code Generation Specification

This document serves as the exact, step-by-step specification for generating code for the PFMS Onboarding Module. It is structured to allow an AI coding assistant to implement the system sequentially, maintaining architectural boundaries (API -> Service -> Repository Protocol).

## Global Architectural Rules for Code Generation
1. **Four-Layer Architecture:** Code must enforce strict separation. Routers call Services, Services call Repositories via dependency-injected Protocols.
2. **DTOs / Pydantic v2:** All inputs and outputs must be strongly typed Pydantic models with clear validation rules.
3. **Double-Entry Constraint:** Opening balances must generate balanced debits/credits. Do not modify account balances directly. Let `AccountRepository/TransactionRepository` handle aggregation.
4. **Test-Driven:** Implement `tests/unit/test_<module>_service.py` using in-memory stubs before implementing endpoints. 
5. **No Database Coupling:** Use `Protocol` classes for all data access in the `pfms/repositories/protocols.py` file.

---

## Module 1: Profile Creation
**Directory:** `src/pfms/onboarding/profile/`

**1. Schemas (`schemas.py`):**
- Create `ProfileSetupRequest`: `display_name` (str, 1-100 chars), `base_currency` (`Currency` enum, default INR), `financial_year_start_month` (1-12, default 4), `tax_regime` (`TaxRegime` enum, default NEW), `date_format` (regex pattern), `number_format` (INDIAN or INTERNATIONAL).
- Create `ProfileResponse`.

**2. Repository Requirements:**
- In `repositories/protocols.py`, define `SettingsRepository` protocol: `get()`, `set()`, `get_bulk()`, `delete()`, `exists()`.
- Implement `InMemorySettingsRepository` in `repositories/inmemory/settings_repo.py`.

**3. Service (`service.py`):**
- Implement `ProfileService` injecting `SettingsRepository`.
- Methods:
  - `setup_profile(dto: ProfileSetupRequest) -> ProfileResponse`: Persist fields as `profile.display_name`, etc. Emit `profile.created` or `profile.updated`.
  - `get_profile() -> Optional[ProfileResponse]`: Aggregate `profile.*` keys. Raise `NotFoundError` if absent.
  - `is_profile_complete() -> bool`: Validate presence of necessary setting keys.

**4. API Router (`router.py`):**
- `POST /`: Calls `setup_profile`.
- `GET /`: Calls `get_profile`.
- `GET /status`: Calls `is_profile_complete`, returns `{"complete": bool}`.

---

## Module 2: Chart of Accounts (COA) Setup
**Directory:** `src/pfms/onboarding/coa/`

**1. Schemas (`schemas.py`) & Data (`default_tree.py`):**
- Create `AccountNodeResponse`, `COATreeResponse`, `RenameAccountRequest`, `AddCategoryRequest`.
- In `default_tree.py`, define `DEFAULT_COA` as a Python dictionary establishing root nodes (Assets, Liabilities, Income, Expense, Equity) and standard Indian financial categories (Bank Accounts, Cash, EPF, PPF, FDs, etc.).

**2. Repository Requirements:**
- Add `AccountRepository` protocol. Needs `create()`, `get()`, `get_tree()`, `has_transactions()`, `update()`.

**3. Service (`service.py`):**
- Implement `COASetupService` injecting `AccountRepository`.
- Methods:
  - `create_default_coa()`: Parses `DEFAULT_COA` and walks the tree to execute `repo.create()` and set parent IDs.
  - `get_coa_tree()`: Fetches the hierarchical view.
  - `rename_account(account_id, new_name)`: Updates name. Block renaming of `is_system=True` accounts.
  - `add_custom_category(parent_id, name)`: Validates parent exists and inherits `type` + `normal_balance`. Auto-generates next available account code.
  - `deactivate_category(account_id)`: Marks inactive if no transactions exist and it is not a system account.
  - `is_coa_ready() -> bool`: Returns True if root accounts exist.

**4. API Router (`router.py`):**
- `POST /initialize`: `create_default_coa`.
- `GET /tree`: `get_coa_tree`.
- `PATCH /accounts/{id}`: `rename_account`.
- `POST /accounts`: `add_custom_category`.
- `DELETE /accounts/{id}`: `deactivate_category`.
- `GET /status`: `is_coa_ready`.

---

## Module 3: Institution Registration
**Directory:** `src/pfms/onboarding/institution/`

**1. Schemas (`schemas.py`):**
- `InstitutionCreateDTO`: `name`, `type` (`InstitutionType` enum), `website_url`, `notes`.
- `InstitutionResponse`.

**2. Repository Requirements:**
- Add `InstitutionRepository` protocol. `create()`, `get()`, `list()`, `update()`, check for duplicate names.

**3. Service (`service.py`):**
- Implement `InstitutionService`.
- Methods: `add_institution` (raise `DuplicateError` on duplicate name), `get_institution`, `list_institutions`, `update_institution`.

**4. Seed Data (`seed_data.py`):**
- Static array of Indian institutions: "SBI", "HDFC", "ICICI", "Zerodha", "Groww", etc.

**5. API Router (`router.py`):**
- Standard CRUD endpoints on `/`.

---

## Module 4: Account Setup
**Directory:** `src/pfms/onboarding/account/`

*This module provides leaf node accounts connecting to institutions.*

**1. Schemas (`schemas.py`):**
- Define separate setup DTOs: `BankAccountSetupDTO`, `CreditCardSetupDTO`, `LoanSetupDTO`, `BrokerageSetupDTO`, `FixedDepositSetupDTO`.
- Ensure robust validation (e.g., IFSC regex `^[A-Z]{4}0[A-Z0-9]{6}$`, limits > 0, tenure > 0).

**2. Service (`service.py`):**
- Base Logic: Resolve COA parent -> generate internal account code -> create node -> build and attach a detail record (e.g. `bank_accounts` table equivalent) -> emit `account.created`.
- Implement per-type methods:
  - `add_bank_account()`: Targets COA `1100`. Validates IFSC and bank type.
  - `add_credit_card()`: Targets COA `2200` (Liability). Checks billing cycle.
  - `add_loan()`: Targets COA `2300` (Liability). Handles principal, rate, EMI.
  - `add_brokerage_account()`: Targets COA `1500`.
  - `add_fixed_deposit()`: Targets COA `1600`.
  - `add_cash_wallet()`: Targets COA `1200`. Needs no institution link.

**3. API Router (`router.py`):**
- Endpoints like `POST /bank`, `POST /credit-card`, `POST /loan`, etc.

---

## Module 5: Opening Balances
**Directory:** `src/pfms/onboarding/opening_balance/`

**1. Schemas (`schemas.py`):**
- `OpeningBalanceDTO`: `account_id`, `balance_amount`, `balance_date`, `notes`.

**2. Repository Requirements:**
- Add `TransactionRepository` protocol (`create_transaction()`, `get_opening_balance_for_account()`, `void_transaction()`).

**3. Service (`service.py`):**
- Implement `OpeningBalanceService`.
- Methods:
  - `set_opening_balance(dto)`: 
      - Finds base account. Base account `type` dictates debit/credit.
      - Asset > 0: Debit Asset Account, Credit `Equity -> Opening Balances`.
      - Liability > 0: Debit `Equity -> Opening Balances`, Credit Liability Account.
  - Duplicate check: If an opening balance already exists for the `account_id`, void old, create new.
  - `set_opening_balances_bulk(entries)`: Atomically execute multiple balances.

**4. API Router (`router.py`):**
- `POST /`: Set a single balance.
- `POST /bulk`: Set bulk balances.

---

## Module 6: Goal Planner
**Directory:** `src/pfms/onboarding/goal/`

**1. Schemas (`schemas.py`):**
- `GoalCreateDTO`: `name`, `target_amount`, `target_date`, `start_date`, `priority`.
- `GoalMilestoneCreateDTO`.

**2. Service (`service.py` & `calculators.py`):**
- Implement `GoalSetupService`.
- Methods: 
  - `create_goal()`.
  - `link_accounts_to_goal()`: Maps specific asset accounts to the goal (validates they are leaf accounts).
  - `add_milestone()`.
- Calculators (`calculators.py`): Math formula `calculate_required_monthly_contribution(goal)` using simple annuity rules.
- `get_goal_summary()`: Return aggregated metrics.

**3. API Router (`router.py`):**
- CRUD goals, associate accounts, get aggregate summary.

---

## Module 7: Budget Setup
**Directory:** `src/pfms/onboarding/budget/`

**1. Schemas (`schemas.py`):**
- `BudgetCreateDTO`: `name`, `period_type`, `start_date`, `end_date`, list of `LineItemDTO` (expense/income `account_id`, `budgeted_amount`).

**2. Service (`service.py`):**
- Methods:
  - `create_budget()`: Validates `start_date` < `end_date` and verifies `account_id` references valid EXPENSE/INCOME objects in COA.
  - `generate_budget_template()`: Iterates over all active leaf EXPENSE nodes in the COA and generates a pre-filled `BudgetCreateDTO` returning all values mapped as 0.0.

**3. API Router (`router.py`):**
- `POST /`: Create the budget.
- `GET /template`: Returns the auto-generated boilerplate.

---

## Module 8: Recurring Templates
**Directory:** `src/pfms/onboarding/recurring/`

**1. Schemas (`schemas.py`):**
- `RecurringTransactionCreateDTO`: `template_type`, `frequency`, `amount`, `from_account_id`, `to_account_id`, `start_date`.

**2. Service (`service.py`):**
- Methods:
  - `create_template()`: Compute `next_occurrence_date` from `start_date` and `frequency`. Save to repository.
  - `setup_sip()`: Convenience implementation mapping mutual fund to brokerage account, auto set as `SIP_PURCHASE` + `MONTHLY`.
  - `setup_emi()`: Convenience mapping debit bank account to credit loan account, auto set as `EMI_PAYMENT`.

**3. API Router (`router.py`):**
- `POST /`, `POST /sip`, `POST /emi`, `GET /`.

---

## Module 9: Net Worth Creation
**Directory:** `src/pfms/onboarding/networth/`

**1. Service (`service.py`):**
- Implement `NetWorthService`.
- Methods:
  - `compute_initial_net_worth(as_of: date)`: Request all active balances. Total Assets - Total Liabilities. Sort into Liquid, Investment, Property, Short-Term Debt, Long-Term Debt.
  - Save snapshot to `SnapshotRepository`.
  - `get_net_worth_summary()`: Returns display DTO suitable for UI.

**2. API Router (`router.py`):**
- `POST /compute`: Calculate and persist.
- `GET /summary`: Returns snapshot data.

---

## Module 10: Onboarding Orchestrator
**Directory:** `src/pfms/onboarding/orchestrator/`

**1. Service (`service.py`):**
- State machine based on enums `OnboardingStep` and `OnboardingStepStatus`.
- Core definitions: Mandatory vs Skippable steps logic. State persisted to JSON payload in `SettingsRepository` (`onboarding.state`).
- Methods: 
  - `start_step(step)`, `complete_step(step)`, `skip_step(step)`. Enforces linear completion rules (Step N requires Step N-1).
  - `complete_onboarding()`: Validates all mandatory steps are complete -> flags app as onboarded.
  - `get_next_step()`: Identifies the first PENDING/IN_PROGRESS step for resume capabilities.

**2. API Router (`router.py`):**
- `POST /step/{step}/start`
- `POST /step/{step}/complete`
- `POST /step/{step}/skip`
- `POST /complete`
- `GET /next-step`
