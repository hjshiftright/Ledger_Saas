# Ledger Android App - Technical Specification

**Version**: 1.1
**Date**: 2026-03-28
**Status**: Draft
**Methodology**: Test-Driven Development (TDD)

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [TDD Methodology & Implementation Order](#2-tdd-methodology--implementation-order)
3. [Project Structure](#3-project-structure)
4. [Tech Stack](#4-tech-stack)
5. [Architecture](#5-architecture)
6. [Network & API Configuration](#6-network--api-configuration)
7. [Authentication Flow](#7-authentication-flow)
8. [API Endpoints Reference](#8-api-endpoints-reference)
9. [Screen Specifications](#9-screen-specifications)
10. [UI Design System](#10-ui-design-system)
11. [Data Models (Kotlin)](#11-data-models-kotlin)
12. [Navigation](#12-navigation)
13. [Error Handling](#13-error-handling)
14. [Test Specifications](#14-test-specifications)
15. [Build, Run & Test](#15-build-run--test)
16. [Future Considerations](#16-future-considerations)
17. [Impact on Existing Code](#17-impact-on-existing-code)

---

## 1. Project Overview

### What
A native Android app called **Ledger** that provides a mobile interface to the existing Ledger personal finance platform. The app mirrors the web frontend's design (colors, layout, flow) while delivering a native Android experience.

### Why
Provide mobile access to the Ledger platform so users can view their financial data (dashboard, transactions, reports, goals, budgets) on the go.

### Constraints
- The app connects to the same FastAPI backend that serves the web frontend.
- Development and testing happen on the Android Emulator (same laptop as the API server).
- The API will eventually move to the cloud; the base URL must be easily configurable.
- No changes to the existing backend or frontend code.

---

## 2. TDD Methodology & Implementation Order

### 2.1 TDD Cycle

Every feature follows the **Red-Green-Refactor** cycle strictly:

```
┌─────────────────────────────────────────────────────────┐
│  1. RED    — Write a failing test first                 │
│  2. GREEN  — Write the minimum code to make it pass     │
│  3. REFACTOR — Clean up while keeping tests green       │
│  4. REPEAT — Next test case                             │
└─────────────────────────────────────────────────────────┘
```

**Rule**: No production code is written without a failing test that demands it.

### 2.2 Implementation Order (Build Phases)

The app is built in **7 phases**, each following TDD. Every phase produces a set of passing tests before moving to the next.

```
Phase 1: Foundation (Data Models + Utilities)
    │     Write tests for: models, CurrencyFormatter, TokenManager
    │     Then implement: data classes, utility objects
    │
Phase 2: Network Layer (API + Retrofit)
    │     Write tests for: API responses, AuthInterceptor, error parsing
    │     Then implement: LedgerApiService, RetrofitClient, AuthInterceptor
    │
Phase 3: Auth ViewModels
    │     Write tests for: LoginViewModel, SignupViewModel state machines
    │     Then implement: ViewModels
    │
Phase 4: Core ViewModels (Dashboard, Transactions)
    │     Write tests for: DashboardViewModel, TransactionsViewModel
    │     Then implement: ViewModels
    │
Phase 5: Feature ViewModels (Reports, Goals, Budgets)
    │     Write tests for: ReportsViewModel, GoalsViewModel, BudgetsViewModel
    │     Then implement: ViewModels
    │
Phase 6: UI / Fragments (Layouts + Wiring)
    │     Write tests for: Fragment rendering, navigation, click handlers
    │     Then implement: XML layouts, Fragments, Adapters, Activities
    │
Phase 7: Integration Tests (End-to-End)
          Write tests for: full auth flow, full CRUD flows
          Then verify: all flows work against MockWebServer
```

### 2.3 Phase 1 — Foundation Tests (Write First)

These tests are written **before any production code** exists. They define the contracts.

#### 1a. Data Model Tests

```
Test File: CurrencyFormatterTest.kt
─────────────────────────────────────
TEST: format_crores_shows_Cr_suffix
  Given: amount = 25_000_000.0
  Then:  CurrencyFormatter.format(amount) == "₹2.5Cr"

TEST: format_lakhs_shows_L_suffix
  Given: amount = 350_000.0
  Then:  CurrencyFormatter.format(amount) == "₹3.5L"

TEST: format_thousands_shows_indian_locale
  Given: amount = 42_500.0
  Then:  CurrencyFormatter.format(amount) == "₹42,500"

TEST: format_small_amount
  Given: amount = 750.0
  Then:  CurrencyFormatter.format(amount) == "₹750"

TEST: format_zero
  Given: amount = 0.0
  Then:  CurrencyFormatter.format(amount) == "₹0"

TEST: formatExact_shows_full_decimal
  Given: amount = 1_23_456.78
  Then:  CurrencyFormatter.formatExact(amount) == "₹1,23,456.78"
```

```
Test File: TokenManagerTest.kt
──────────────────────────────
TEST: initially_no_token_stored
  Then:  TokenManager.getToken() == null
  Then:  TokenManager.isLoggedIn() == false

TEST: save_and_retrieve_token
  Given: saveToken(context, "jwt_abc", 1, "tenant-uuid")
  Then:  TokenManager.getToken() == "jwt_abc"
  Then:  TokenManager.isLoggedIn() == true

TEST: clear_token_removes_all
  Given: saveToken(...), then clearToken(context)
  Then:  TokenManager.getToken() == null
  Then:  TokenManager.isLoggedIn() == false

TEST: overwrite_token
  Given: saveToken(ctx, "old_token", 1, "t1"), then saveToken(ctx, "new_token", 2, "t2")
  Then:  TokenManager.getToken() == "new_token"
```

```
Test File: DataModelTest.kt
───────────────────────────
TEST: login_request_serializes_correctly
  Given: LoginRequest("user@test.com", "pass123")
  Then:  JSON has fields "email" and "password"

TEST: auth_response_deserializes_with_tenants
  Given: JSON {"user_id":1,"email":"a@b.com","tenants":[{"tenant_id":"uuid","name":"Home","entity_type":"PERSONAL","role":"OWNER"}],"message":"ok"}
  Then:  AuthListResponse.tenants.size == 1
  Then:  AuthListResponse.tenants[0].role == "OWNER"

TEST: goal_out_deserializes_progress
  Given: JSON with progress_pct: 65.5
  Then:  GoalOut.progress_pct == 65.5

TEST: transaction_out_deserializes_lines
  Given: JSON with 2 lines (DEBIT + CREDIT)
  Then:  TransactionOut.lines.size == 2
  Then:  lines[0].line_type == "DEBIT"

TEST: dashboard_summary_handles_null_savings_rate
  Given: JSON with savings_rate: null
  Then:  DashboardSummary.savings_rate == null (no crash)

TEST: budget_create_serializes_items
  Given: BudgetCreate with 3 items
  Then:  JSON "items" array has 3 elements
```

#### 1b. Utility Tests

```
Test File: UiStateTest.kt
─────────────────────────
TEST: loading_state_is_distinct
  Given: state = UiState.Loading
  Then:  state is UiState.Loading == true

TEST: success_state_carries_data
  Given: state = UiState.Success(listOf("a","b"))
  Then:  (state as UiState.Success).data == listOf("a","b")

TEST: error_state_carries_message
  Given: state = UiState.Error("Network failed")
  Then:  (state as UiState.Error).message == "Network failed"
```

### 2.4 Phase 2 — Network Layer Tests (Write First)

Uses **MockWebServer** to simulate backend responses without hitting the real API.

```
Test File: LedgerApiServiceTest.kt
───────────────────────────────────
Setup: MockWebServer started, Retrofit pointed to mockWebServer.url("/")

TEST: login_sends_correct_request
  Given: Enqueue 200 response with AuthListResponse JSON
  When:  api.login(LoginRequest("a@b.com", "pwd"))
  Then:  Recorded request path == "/api/v1/auth/login"
  Then:  Recorded request method == "POST"
  Then:  Recorded body contains "email" and "password"

TEST: login_success_parses_response
  Given: Enqueue 200 with {"user_id":1,"email":"a@b.com","tenants":[...],"message":"ok"}
  When:  response = api.login(...)
  Then:  response.isSuccessful == true
  Then:  response.body().user_id == 1
  Then:  response.body().tenants.isNotEmpty()

TEST: login_failure_returns_401
  Given: Enqueue 401 with {"detail":"Invalid credentials"}
  When:  response = api.login(...)
  Then:  response.code() == 401
  Then:  response.isSuccessful == false

TEST: select_tenant_returns_jwt
  Given: Enqueue 200 with TokenResponse JSON
  When:  response = api.selectTenant(SelectTenantRequest("uuid"))
  Then:  response.body().access_token == "jwt_token_here"

TEST: get_dashboard_summary_success
  Given: Enqueue 200 with DashboardSummary JSON
  When:  response = api.getDashboardSummary()
  Then:  response.body().net_worth == "1500000.00"

TEST: get_transactions_with_pagination
  Given: Enqueue 200 with list of 20 transactions
  When:  response = api.getTransactions(limit=20, offset=0)
  Then:  Recorded request has query params limit=20&offset=0
  Then:  response.body().size == 20

TEST: get_transactions_with_date_filter
  Given: Enqueue 200 response
  When:  api.getTransactions(fromDate="2026-01-01", toDate="2026-03-31")
  Then:  Recorded URL contains "from_date=2026-01-01&to_date=2026-03-31"

TEST: get_goals_returns_list
  Given: Enqueue 200 with 3 goals JSON
  When:  response = api.getGoals()
  Then:  response.body().size == 3

TEST: create_goal_sends_body
  Given: Enqueue 201 with GoalOut JSON
  When:  api.createGoal(GoalCreate(name="Trip", goal_type="HOLIDAY", target_amount="100000"))
  Then:  Recorded body has "name", "goal_type", "target_amount"

TEST: delete_goal_sends_delete_method
  Given: Enqueue 204
  When:  api.deleteGoal(5)
  Then:  Recorded request path == "/api/v1/goals/5"
  Then:  Recorded request method == "DELETE"

TEST: get_budgets_returns_list
  Given: Enqueue 200 with budget list JSON
  When:  response = api.getBudgets()
  Then:  response.body().isNotEmpty()

TEST: health_check_success
  Given: Enqueue 200 with {"status":"ok","version":"3.0"}
  When:  response = api.healthCheck()
  Then:  response.isSuccessful == true

TEST: server_error_returns_500
  Given: Enqueue 500 with {"detail":"Internal server error"}
  When:  response = api.getDashboardSummary()
  Then:  response.code() == 500

TEST: network_timeout_throws_exception
  Given: MockWebServer with no response (or delayed beyond 30s)
  When:  api.getGoals()
  Then:  Throws SocketTimeoutException
```

```
Test File: AuthInterceptorTest.kt
──────────────────────────────────
TEST: adds_bearer_token_when_present
  Given: TokenManager has token "abc123"
  When:  Interceptor processes a request
  Then:  Request header "Authorization" == "Bearer abc123"

TEST: no_header_when_no_token
  Given: TokenManager has no token
  When:  Interceptor processes a request
  Then:  Request has no "Authorization" header
```

### 2.5 Phase 3 — Auth ViewModel Tests (Write First)

```
Test File: LoginViewModelTest.kt
─────────────────────────────────
Setup: Mock LedgerApiService, InstantTaskExecutorRule for LiveData

TEST: initial_state_is_idle
  Then:  viewModel.loginState.value == null (or UiState idle)

TEST: login_sets_loading_state
  Given: Mock api.login() returns slowly
  When:  viewModel.login("a@b.com", "pwd")
  Then:  viewModel.loginState.value is UiState.Loading

TEST: login_success_emits_tenant_list
  Given: Mock api.login() returns AuthListResponse with 2 tenants
  When:  viewModel.login("a@b.com", "pwd")
  Then:  viewModel.loginState.value is UiState.Success
  Then:  (value as Success).data.tenants.size == 2

TEST: login_failure_emits_error
  Given: Mock api.login() returns 401
  When:  viewModel.login("a@b.com", "wrong")
  Then:  viewModel.loginState.value is UiState.Error
  Then:  (value as Error).message contains "Invalid"

TEST: login_network_error_emits_error
  Given: Mock api.login() throws IOException
  When:  viewModel.login(...)
  Then:  viewModel.loginState.value is UiState.Error
  Then:  message contains "network" or "connection"

TEST: empty_email_emits_validation_error
  When:  viewModel.login("", "pwd")
  Then:  viewModel.loginState.value is UiState.Error
  Then:  message contains "email"

TEST: empty_password_emits_validation_error
  When:  viewModel.login("a@b.com", "")
  Then:  viewModel.loginState.value is UiState.Error
  Then:  message contains "password"

TEST: select_tenant_stores_token
  Given: Mock api.selectTenant() returns TokenResponse(access_token="jwt")
  When:  viewModel.selectTenant("tenant-uuid")
  Then:  TokenManager.getToken() == "jwt"
  Then:  viewModel.tenantState.value is UiState.Success

TEST: select_tenant_failure_emits_error
  Given: Mock api.selectTenant() returns 403
  When:  viewModel.selectTenant("bad-uuid")
  Then:  viewModel.tenantState.value is UiState.Error

TEST: single_tenant_auto_selects
  Given: Mock api.login() returns AuthListResponse with 1 tenant
  When:  viewModel.login("a@b.com", "pwd")
  Then:  viewModel.shouldAutoSelectTenant == true
```

```
Test File: SignupViewModelTest.kt
─────────────────────────────────
TEST: signup_success_emits_tenant_list
  Given: Mock api.signup() returns AuthListResponse
  When:  viewModel.signup("a@b.com", "pwd", "John", "PERSONAL")
  Then:  viewModel.signupState.value is UiState.Success

TEST: signup_duplicate_email_emits_error
  Given: Mock api.signup() returns 400 "Email already registered"
  When:  viewModel.signup("existing@b.com", ...)
  Then:  viewModel.signupState.value is UiState.Error

TEST: signup_validates_required_fields
  When:  viewModel.signup("", "", "", "")
  Then:  viewModel.signupState.value is UiState.Error
```

### 2.6 Phase 4 — Core ViewModel Tests (Write First)

```
Test File: DashboardViewModelTest.kt
─────────────────────────────────────
TEST: load_dashboard_sets_loading_then_success
  Given: Mock returns DashboardSummary, goals list, transactions list
  When:  viewModel.loadDashboard()
  Then:  summaryState transitions Loading → Success
  Then:  goalsState transitions Loading → Success
  Then:  transactionsState transitions Loading → Success

TEST: dashboard_summary_maps_net_worth
  Given: Mock returns DashboardSummary(net_worth="2500000.00")
  When:  viewModel.loadDashboard()
  Then:  (summaryState as Success).data.net_worth == "2500000.00"

TEST: dashboard_handles_partial_failure
  Given: Mock summary returns 200, goals returns 500
  When:  viewModel.loadDashboard()
  Then:  summaryState is Success
  Then:  goalsState is Error

TEST: dashboard_handles_total_failure
  Given: All three API calls throw IOException
  When:  viewModel.loadDashboard()
  Then:  All three states are Error with network message

TEST: refresh_reloads_all_data
  Given: Already loaded once (Success state)
  When:  viewModel.refresh()
  Then:  States transition Loading → Success again (fresh data)
```

```
Test File: TransactionsViewModelTest.kt
────────────────────────────────────────
TEST: load_transactions_first_page
  Given: Mock returns 20 transactions
  When:  viewModel.loadTransactions()
  Then:  state is Success with 20 items
  Then:  viewModel.currentOffset == 20

TEST: load_more_appends_to_list
  Given: First page loaded (20 items)
  Given: Mock returns 20 more transactions
  When:  viewModel.loadMore()
  Then:  state is Success with 40 items
  Then:  viewModel.currentOffset == 40

TEST: load_more_with_no_results_sets_end_reached
  Given: First page loaded
  Given: Mock returns empty list
  When:  viewModel.loadMore()
  Then:  viewModel.hasMorePages == false

TEST: filter_by_date_resets_and_reloads
  Given: Already loaded transactions
  When:  viewModel.filterByDate("2026-01-01", "2026-03-31")
  Then:  viewModel.currentOffset == 0 (reset)
  Then:  State is Success with filtered results
  Then:  API called with from_date and to_date params

TEST: load_transactions_failure
  Given: Mock returns 500
  When:  viewModel.loadTransactions()
  Then:  state is Error

TEST: transaction_count_loaded
  Given: Mock getTransactionCount returns {"count": 150}
  When:  viewModel.loadTransactions()
  Then:  viewModel.totalCount == 150
```

### 2.7 Phase 5 — Feature ViewModel Tests (Write First)

```
Test File: GoalsViewModelTest.kt
─────────────────────────────────
TEST: load_goals_success
  Given: Mock returns 3 goals
  When:  viewModel.loadGoals()
  Then:  state is Success with 3 items

TEST: load_goals_empty
  Given: Mock returns empty list
  When:  viewModel.loadGoals()
  Then:  state is Success with 0 items
  Then:  viewModel.isEmpty == true

TEST: create_goal_success
  Given: Mock createGoal returns GoalOut(id=1, name="Trip")
  When:  viewModel.createGoal(GoalCreate(...))
  Then:  createState is Success
  Then:  goals list refreshed (loadGoals called again)

TEST: create_goal_validation_error
  Given: Mock returns 400 "name is required"
  When:  viewModel.createGoal(GoalCreate(name="", ...))
  Then:  createState is Error

TEST: delete_goal_success
  Given: Mock deleteGoal returns 204
  When:  viewModel.deleteGoal(5)
  Then:  deleteState is Success
  Then:  goals list refreshed

TEST: delete_goal_failure
  Given: Mock returns 404
  When:  viewModel.deleteGoal(999)
  Then:  deleteState is Error

TEST: update_goal_success
  Given: Mock returns updated GoalOut
  When:  viewModel.updateGoal(1, mapOf("current_amount" to "200000"))
  Then:  updateState is Success

TEST: computed_summary_values
  Given: Mock returns 3 goals with target_amounts [500000, 300000, 200000] and progress [50, 75, 25]
  When:  viewModel.loadGoals()
  Then:  viewModel.totalTargetAmount == 1_000_000
  Then:  viewModel.averageProgress == 50.0
```

```
Test File: BudgetsViewModelTest.kt
───────────────────────────────────
TEST: load_budgets_success
  Given: Mock returns 2 budgets
  When:  viewModel.loadBudgets()
  Then:  state is Success with 2 items

TEST: load_budgets_empty
  Given: Mock returns empty list
  When:  viewModel.loadBudgets()
  Then:  state is Success, viewModel.isEmpty == true

TEST: create_budget_success
  Given: Mock returns BudgetOut
  When:  viewModel.createBudget(BudgetCreate(...))
  Then:  createState is Success

TEST: delete_budget_success
  Given: Mock returns 204
  When:  viewModel.deleteBudget(3)
  Then:  deleteState is Success
  Then:  budgets list refreshed

TEST: computed_summary_values
  Given: 2 budgets with 3 and 2 items, planned amounts [10000, 20000, 5000] and [15000, 8000]
  When:  viewModel.loadBudgets()
  Then:  viewModel.activeBudgetCount == 2
  Then:  viewModel.totalPlannedAmount == 58_000
  Then:  viewModel.totalLineItems == 5
```

```
Test File: ReportsViewModelTest.kt
───────────────────────────────────
TEST: load_reports_fetches_all_sections
  Given: Mock returns valid responses for summary, trend, categories, balance sheet
  When:  viewModel.loadReports()
  Then:  summaryState is Success
  Then:  trendState is Success
  Then:  categoriesState is Success
  Then:  balanceSheetState is Success

TEST: change_period_reloads_with_dates
  When:  viewModel.setPeriod("THIS_QUARTER")
  Then:  API called with correct from_date/to_date for current quarter
  Then:  All states refreshed

TEST: custom_period_uses_exact_dates
  When:  viewModel.setCustomPeriod("2026-01-01", "2026-03-31")
  Then:  API called with from_date=2026-01-01, to_date=2026-03-31

TEST: partial_failure_shows_available_data
  Given: Summary returns 200, trend returns 500
  When:  viewModel.loadReports()
  Then:  summaryState is Success
  Then:  trendState is Error (with message)

TEST: expense_categories_sorted_by_amount
  Given: Mock returns categories [A=500, B=1000, C=250]
  When:  viewModel.loadReports()
  Then:  categories order is [B=1000, A=500, C=250]
```

### 2.8 Phase 6 — UI Tests (Write First)

Uses **Espresso** for instrumented tests and **MockWebServer** for backend simulation.

```
Test File: LoginActivityTest.kt (androidTest)
──────────────────────────────────────────────
TEST: login_screen_displays_all_elements
  Then:  "Ledger" title is displayed
  Then:  Email input is displayed
  Then:  Password input is displayed
  Then:  Login button is displayed
  Then:  "Create Account" link is displayed

TEST: login_button_disabled_with_empty_fields
  When:  Email and password are empty
  Then:  Login button click shows validation error

TEST: login_shows_loading_indicator
  Given: MockWebServer enqueues delayed response
  When:  Enter email + password, click Login
  Then:  Loading indicator is displayed

TEST: login_success_navigates_to_main
  Given: MockWebServer enqueues login success + select-tenant success (single tenant)
  When:  Enter email + password, click Login
  Then:  MainActivity is launched (Dashboard visible)

TEST: login_failure_shows_error_banner
  Given: MockWebServer enqueues 401
  When:  Enter email + password, click Login
  Then:  Error banner with "Invalid credentials" is displayed

TEST: create_account_link_navigates_to_signup
  When:  Click "Create Account"
  Then:  SignupActivity is launched
```

```
Test File: DashboardFragmentTest.kt (androidTest)
──────────────────────────────────────────────────
TEST: dashboard_shows_net_worth
  Given: MockWebServer returns summary with net_worth = "2500000"
  When:  DashboardFragment is launched
  Then:  "₹25.0L" is displayed

TEST: dashboard_shows_income_expense_cards
  Given: MockWebServer returns summary
  When:  DashboardFragment is launched
  Then:  Income card is displayed with formatted amount
  Then:  Expense card is displayed with formatted amount

TEST: dashboard_shows_goals_section
  Given: MockWebServer returns 2 goals
  When:  DashboardFragment is launched
  Then:  2 goal cards are displayed with names and progress bars

TEST: dashboard_shows_recent_transactions
  Given: MockWebServer returns 5 transactions
  When:  DashboardFragment is launched
  Then:  5 transaction rows are displayed

TEST: dashboard_shows_error_on_failure
  Given: MockWebServer returns 500
  When:  DashboardFragment is launched
  Then:  Error view with retry button is displayed

TEST: dashboard_retry_reloads_data
  Given: First request fails (500), second succeeds (200)
  When:  DashboardFragment launched, click Retry
  Then:  Data is displayed successfully
```

```
Test File: TransactionsFragmentTest.kt (androidTest)
─────────────────────────────────────────────────────
TEST: transactions_list_renders_items
  Given: MockWebServer returns 10 transactions
  When:  TransactionsFragment launched
  Then:  RecyclerView has 10 items

TEST: transaction_item_shows_description_and_amount
  Given: Transaction with description="Salary" and CREDIT line amount="50000"
  When:  Fragment launched
  Then:  "Salary" text is displayed
  Then:  Amount text is displayed in green

TEST: scroll_to_bottom_triggers_load_more
  Given: MockWebServer returns 20 items, then 10 more
  When:  Scroll to bottom of list
  Then:  RecyclerView has 30 items total

TEST: empty_transactions_shows_empty_state
  Given: MockWebServer returns empty list
  When:  Fragment launched
  Then:  "No transactions" empty state is displayed
```

```
Test File: GoalsFragmentTest.kt (androidTest)
──────────────────────────────────────────────
TEST: goals_list_renders_cards
  Given: MockWebServer returns 3 goals
  When:  GoalsFragment launched
  Then:  3 goal cards are displayed

TEST: goal_card_shows_progress_bar
  Given: Goal with progress_pct = 65.0
  When:  Fragment launched
  Then:  Progress bar is visible at ~65%

TEST: create_goal_button_opens_form
  When:  Click "+ New Goal" button
  Then:  Goal creation form is displayed

TEST: empty_goals_shows_cta
  Given: MockWebServer returns empty list
  When:  Fragment launched
  Then:  "No goals yet" and CTA button are displayed
```

```
Test File: NavigationTest.kt (androidTest)
──────────────────────────────────────────
TEST: bottom_nav_switches_tabs
  Given: MainActivity launched
  When:  Click "Transactions" tab
  Then:  TransactionsFragment is displayed
  When:  Click "Reports" tab
  Then:  ReportsFragment is displayed
  When:  Click "Dashboard" tab
  Then:  DashboardFragment is displayed

TEST: back_button_from_tab_exits_app
  Given: On Dashboard tab
  When:  Press back button
  Then:  App finishes (or confirms exit)

TEST: deep_nav_back_returns_to_parent
  Given: On More > Budgets
  When:  Press back
  Then:  More menu is displayed
```

### 2.9 Phase 7 — Integration Tests (Write First)

End-to-end flows using MockWebServer, testing full sequences.

```
Test File: AuthFlowIntegrationTest.kt (androidTest)
─────────────────────────────────────────────────────
TEST: full_signup_to_dashboard_flow
  Given: MockWebServer enqueues: signup 200, select-tenant 200, summary 200, goals 200, transactions 200
  When:  Launch app → SignupActivity
  When:  Fill form → click Sign Up
  Then:  TenantPicker shown (or auto-selected)
  Then:  Dashboard displayed with data

TEST: full_login_with_tenant_picker_flow
  Given: MockWebServer enqueues: login 200 (2 tenants), select-tenant 200, dashboard data
  When:  Launch app → LoginActivity
  When:  Fill form → click Login
  Then:  TenantPicker shown with 2 tenants
  When:  Tap first tenant
  Then:  Dashboard displayed

TEST: logout_clears_state_and_returns_to_login
  Given: User is logged in, on Dashboard
  When:  Navigate to More > Settings > Logout
  Then:  LoginActivity is displayed
  Then:  TokenManager.isLoggedIn() == false
  Then:  Navigating back does NOT return to Dashboard

TEST: expired_token_redirects_to_login
  Given: User is logged in
  Given: MockWebServer returns 401 for next API call
  When:  Dashboard tries to load
  Then:  User is redirected to LoginActivity
```

```
Test File: GoalsCrudIntegrationTest.kt (androidTest)
─────────────────────────────────────────────────────
TEST: create_view_delete_goal_flow
  Given: Logged in, on Goals tab
  Given: MockWebServer enqueues: empty goals, create 201, goals with 1 item, delete 204, empty goals
  Step 1: Empty state displayed
  Step 2: Click "+ New Goal" → fill form → save
  Step 3: Goal appears in list
  Step 4: Long-press goal → confirm delete
  Step 5: Empty state displayed again
```

### 2.10 TDD Rules for Developers

| Rule | Description |
|------|-------------|
| **No code without a test** | Every function, ViewModel method, and UI behavior must have a test written before the implementation |
| **One test at a time** | Write one failing test, make it pass, then move to the next. Do not batch. |
| **Minimal implementation** | Write only enough code to make the current failing test pass. No speculative code. |
| **Tests must be fast** | Unit tests (Phase 1-5) must run in < 5 seconds total. Use mocks, not real network. |
| **Tests must be independent** | Each test sets up its own state. No test depends on another test's output. |
| **Refactor only when green** | Only refactor (extract methods, rename, reorganize) when all tests pass. |
| **Test names describe behavior** | Use format: `action_condition_expectedResult` (e.g., `login_invalidPassword_emitsError`) |
| **Mock at the boundary** | Mock the API service interface, not internals. ViewModels are tested with mock API responses. |

---

## 3. Project Structure

All Android code lives in a **new top-level folder**: `android/`

```
Ledger_Android/
├── backend/          # Existing - DO NOT MODIFY
├── frontend/         # Existing - DO NOT MODIFY
├── docs/             # Existing
├── android/          # NEW - Android app
│   ├── app/
│   │   ├── src/
│   │   │   ├── main/
│   │   │   │   ├── java/com/ledger/app/
│   │   │   │   │   ├── LedgerApplication.kt
│   │   │   │   │   ├── config/
│   │   │   │   │   │   └── AppConfig.kt
│   │   │   │   │   ├── data/
│   │   │   │   │   │   ├── api/
│   │   │   │   │   │   │   ├── LedgerApiService.kt
│   │   │   │   │   │   │   ├── AuthInterceptor.kt
│   │   │   │   │   │   │   └── RetrofitClient.kt
│   │   │   │   │   │   └── models/
│   │   │   │   │   │       ├── Auth.kt
│   │   │   │   │   │       ├── Account.kt
│   │   │   │   │   │       ├── Transaction.kt
│   │   │   │   │   │       ├── Report.kt
│   │   │   │   │   │       ├── Goal.kt
│   │   │   │   │   │       ├── Budget.kt
│   │   │   │   │   │       └── Import.kt
│   │   │   │   │   ├── ui/
│   │   │   │   │   │   ├── auth/
│   │   │   │   │   │   │   ├── LoginActivity.kt
│   │   │   │   │   │   │   ├── SignupActivity.kt
│   │   │   │   │   │   │   └── TenantPickerActivity.kt
│   │   │   │   │   │   ├── main/
│   │   │   │   │   │   │   └── MainActivity.kt
│   │   │   │   │   │   ├── dashboard/
│   │   │   │   │   │   │   ├── DashboardFragment.kt
│   │   │   │   │   │   │   └── DashboardViewModel.kt
│   │   │   │   │   │   ├── transactions/
│   │   │   │   │   │   │   ├── TransactionsFragment.kt
│   │   │   │   │   │   │   ├── TransactionsViewModel.kt
│   │   │   │   │   │   │   └── TransactionAdapter.kt
│   │   │   │   │   │   ├── reports/
│   │   │   │   │   │   │   ├── ReportsFragment.kt
│   │   │   │   │   │   │   └── ReportsViewModel.kt
│   │   │   │   │   │   ├── goals/
│   │   │   │   │   │   │   ├── GoalsFragment.kt
│   │   │   │   │   │   │   ├── GoalsViewModel.kt
│   │   │   │   │   │   │   └── GoalAdapter.kt
│   │   │   │   │   │   ├── budgets/
│   │   │   │   │   │   │   ├── BudgetsFragment.kt
│   │   │   │   │   │   │   ├── BudgetsViewModel.kt
│   │   │   │   │   │   │   └── BudgetAdapter.kt
│   │   │   │   │   │   └── settings/
│   │   │   │   │   │       └── SettingsFragment.kt
│   │   │   │   │   └── util/
│   │   │   │   │       ├── CurrencyFormatter.kt
│   │   │   │   │       ├── TokenManager.kt
│   │   │   │   │       └── ViewExtensions.kt
│   │   │   │   ├── res/
│   │   │   │   │   ├── layout/
│   │   │   │   │   ├── values/
│   │   │   │   │   │   ├── colors.xml
│   │   │   │   │   │   ├── strings.xml
│   │   │   │   │   │   ├── themes.xml
│   │   │   │   │   │   └── dimens.xml
│   │   │   │   │   ├── drawable/
│   │   │   │   │   ├── menu/
│   │   │   │   │   └── navigation/
│   │   │   │   │       └── nav_graph.xml
│   │   │   │   └── AndroidManifest.xml
│   │   │   │
│   │   │   ├── test/                              # LOCAL UNIT TESTS (JVM)
│   │   │   │   └── java/com/ledger/app/
│   │   │   │       ├── data/
│   │   │   │       │   ├── models/
│   │   │   │       │   │   └── DataModelTest.kt        # Phase 1
│   │   │   │       │   └── api/
│   │   │   │       │       ├── LedgerApiServiceTest.kt  # Phase 2
│   │   │   │       │       └── AuthInterceptorTest.kt   # Phase 2
│   │   │   │       ├── ui/
│   │   │   │       │   ├── auth/
│   │   │   │       │   │   ├── LoginViewModelTest.kt    # Phase 3
│   │   │   │       │   │   └── SignupViewModelTest.kt   # Phase 3
│   │   │   │       │   ├── dashboard/
│   │   │   │       │   │   └── DashboardViewModelTest.kt # Phase 4
│   │   │   │       │   ├── transactions/
│   │   │   │       │   │   └── TransactionsViewModelTest.kt # Phase 4
│   │   │   │       │   ├── reports/
│   │   │   │       │   │   └── ReportsViewModelTest.kt  # Phase 5
│   │   │   │       │   ├── goals/
│   │   │   │       │   │   └── GoalsViewModelTest.kt    # Phase 5
│   │   │   │       │   └── budgets/
│   │   │   │       │       └── BudgetsViewModelTest.kt  # Phase 5
│   │   │   │       └── util/
│   │   │   │           ├── CurrencyFormatterTest.kt     # Phase 1
│   │   │   │           ├── TokenManagerTest.kt          # Phase 1
│   │   │   │           └── UiStateTest.kt               # Phase 1
│   │   │   │
│   │   │   └── androidTest/                       # INSTRUMENTED TESTS (Emulator)
│   │   │       └── java/com/ledger/app/
│   │   │           ├── ui/
│   │   │           │   ├── auth/
│   │   │           │   │   └── LoginActivityTest.kt     # Phase 6
│   │   │           │   ├── dashboard/
│   │   │           │   │   └── DashboardFragmentTest.kt # Phase 6
│   │   │           │   ├── transactions/
│   │   │           │   │   └── TransactionsFragmentTest.kt # Phase 6
│   │   │           │   ├── goals/
│   │   │           │   │   └── GoalsFragmentTest.kt     # Phase 6
│   │   │           │   └── NavigationTest.kt            # Phase 6
│   │   │           ├── integration/
│   │   │           │   ├── AuthFlowIntegrationTest.kt   # Phase 7
│   │   │           │   └── GoalsCrudIntegrationTest.kt  # Phase 7
│   │   │           └── TestFixtures.kt                  # Shared JSON fixtures
│   │   │
│   │   └── build.gradle.kts
│   ├── build.gradle.kts          # Project-level
│   ├── settings.gradle.kts
│   ├── gradle.properties
│   └── gradle/
│       └── wrapper/
│           ├── gradle-wrapper.jar
│           └── gradle-wrapper.properties
```

---

## 3. Tech Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Language | Kotlin | 1.9+ |
| Min SDK | 26 (Android 8.0) | |
| Target SDK | 34 (Android 14) | |
| Build System | Gradle (Kotlin DSL) | 8.x |
| HTTP Client | Retrofit 2 + OkHttp | 2.9+ |
| JSON Parsing | Moshi (or Gson) | 1.15+ |
| Architecture | MVVM | |
| Navigation | Jetpack Navigation Component | |
| UI Components | Material Design 3 (Material You) | |
| Layouts | ConstraintLayout, RecyclerView | |
| Lifecycle | ViewModel + LiveData | |
| Token Storage | EncryptedSharedPreferences | |
| Image Loading | Coil (optional, for charts/icons) | |
| Charts | MPAndroidChart | |
| **Testing** | | |
| Unit Tests | JUnit 5 + MockK | 5.10+ / 1.13+ |
| LiveData Testing | InstantTaskExecutorRule | |
| Coroutine Testing | kotlinx-coroutines-test | 1.8+ |
| API Mocking | MockWebServer (OkHttp) | 4.12+ |
| UI Tests | Espresso | 3.5+ |
| Fragment Tests | FragmentScenario (AndroidX) | |
| Test Runner | AndroidJUnitRunner | |

---

## 5. Architecture

### Pattern: MVVM (Model-View-ViewModel)

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Activity/  │────>│  ViewModel   │────>│  Repository  │────>│  Retrofit    │
│   Fragment   │<────│  (LiveData)  │<────│  (optional)  │<────│  ApiService  │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
     View              Presentation          Data Access          Network
```

- **View** (Activity/Fragment): Observes LiveData, renders UI, handles user input.
- **ViewModel**: Holds UI state, calls API, exposes LiveData to the view.
- **ApiService**: Retrofit interface defining all API calls.
- **RetrofitClient**: Singleton that builds the Retrofit instance with the configurable base URL and auth interceptor.

### Why no Repository layer initially
For the initial version, ViewModels call the Retrofit ApiService directly. This keeps the codebase small. A Repository layer can be added later when offline caching (Room) is needed.

---

## 6. Network & API Configuration

### AppConfig.kt

```kotlin
object AppConfig {
    // For Android Emulator hitting localhost:
    // The emulator maps 10.0.2.2 -> host machine's 127.0.0.1
    var BASE_URL: String = "http://10.0.2.2:8000"

    // Future cloud URL example:
    // var BASE_URL: String = "https://api.ledger.example.com"
}
```

### AndroidManifest.xml - Cleartext Traffic

```xml
<application
    android:usesCleartextTraffic="true"
    android:networkSecurityConfig="@xml/network_security_config"
    ... >
```

### network_security_config.xml

```xml
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <domain-config cleartextTrafficPermitted="true">
        <domain includeSubdomains="true">10.0.2.2</domain>
        <domain includeSubdomains="true">127.0.0.1</domain>
    </domain-config>
</network-security-config>
```

### RetrofitClient.kt

```kotlin
object RetrofitClient {
    private var retrofit: Retrofit? = null

    fun getInstance(): Retrofit {
        if (retrofit == null || retrofit!!.baseUrl().toString() != AppConfig.BASE_URL + "/") {
            val okHttpClient = OkHttpClient.Builder()
                .addInterceptor(AuthInterceptor())
                .connectTimeout(30, TimeUnit.SECONDS)
                .readTimeout(30, TimeUnit.SECONDS)
                .build()

            retrofit = Retrofit.Builder()
                .baseUrl(AppConfig.BASE_URL)
                .client(okHttpClient)
                .addConverterFactory(MoshiConverterFactory.create())
                .build()
        }
        return retrofit!!
    }

    val api: LedgerApiService
        get() = getInstance().create(LedgerApiService::class.java)
}
```

### AuthInterceptor.kt

```kotlin
class AuthInterceptor : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val token = TokenManager.getToken()
        val request = if (token != null) {
            chain.request().newBuilder()
                .addHeader("Authorization", "Bearer $token")
                .build()
        } else {
            chain.request()
        }
        return chain.proceed(request)
    }
}
```

---

## 7. Authentication Flow

The app follows the same multi-step JWT auth flow as the web frontend:

```
┌─────────────┐    ┌──────────────┐    ┌─────────────────┐    ┌──────────────┐
│ LoginActivity│───>│ POST /login  │───>│TenantPickerActivity│──>│ POST         │
│ (email, pwd) │    │ Returns      │    │ (show tenants)   │   │ /select-tenant│
│              │    │ tenant list  │    │                  │   │ Returns JWT  │
└─────────────┘    └──────────────┘    └─────────────────┘    └──────┬───────┘
                                                                      │
                                                                      v
                                                               ┌──────────────┐
                                                               │ MainActivity │
                                                               │ (Dashboard)  │
                                                               └──────────────┘
```

### Steps

1. **LoginActivity**: User enters email + password. Calls `POST /api/v1/auth/login`.
2. **Response**: Returns `user_id`, `email`, and `tenants[]` array.
3. **TenantPickerActivity**: If multiple tenants, user selects one. If single tenant, auto-select.
4. **Select Tenant**: Calls `POST /api/v1/auth/select-tenant` with `tenant_id`.
5. **JWT Stored**: The returned `access_token` is stored in `EncryptedSharedPreferences` via `TokenManager`.
6. **MainActivity launches**: All subsequent API calls include `Authorization: Bearer <token>`.

### Signup Flow
- **SignupActivity**: email, password, full_name, entity_type (spinner/dropdown).
- Calls `POST /api/v1/auth/signup`.
- On success, proceeds to tenant selection (same as login).

### Token Management

```kotlin
object TokenManager {
    private const val PREF_NAME = "ledger_auth"
    private const val KEY_TOKEN = "access_token"
    private const val KEY_USER_ID = "user_id"
    private const val KEY_TENANT_ID = "tenant_id"

    fun saveToken(context: Context, token: String, userId: Int, tenantId: String) { ... }
    fun getToken(): String? { ... }
    fun clearToken(context: Context) { ... }
    fun isLoggedIn(): Boolean = getToken() != null
}
```

---

## 8. API Endpoints Reference

### Base Path: `/api/v1`

All endpoints require `Authorization: Bearer <JWT>` header unless noted.

### 8.1 Auth (No auth header required)

| Method | Path | Description | Request Body | Response |
|--------|------|-------------|-------------|----------|
| GET | `/auth/status` | Check if users exist | - | `{has_users, user_count}` |
| POST | `/auth/signup` | Register user + tenant | `{email, password, full_name, entity_type}` | `{user_id, email, tenants[], message}` |
| POST | `/auth/login` | Authenticate | `{email, password}` | `{user_id, email, tenants[], message}` |
| POST | `/auth/select-tenant` | Get scoped JWT | `{tenant_id}` | `{access_token, token_type, user_id, tenant_id, role}` |
| POST | `/auth/logout` | Logout (stateless) | - | `{message}` |

### 8.2 Dashboard / Reports

| Method | Path | Description | Response |
|--------|------|-------------|----------|
| GET | `/reports/summary` | Dashboard KPIs | `{net_worth, total_income, total_expense, savings_rate, ...}` |
| GET | `/reports/income-expense` | Income & expense statement | `{income_items[], expense_items[], totals}` |
| GET | `/reports/balance-sheet` | Balance sheet tree | `{assets{}, liabilities{}, equity{}}` |
| GET | `/reports/net-worth-history` | Monthly net worth trend | `[{month, net_worth}]` |
| GET | `/reports/monthly-trend` | Income vs expense by month | `[{month, income, expense}]` |
| GET | `/reports/expense-categories` | Category breakdown | `[{category, amount, percentage}]` |
| GET | `/reports/accounts-list` | All leaf accounts | `[{account_id, name, code, balance}]` |
| GET | `/reports/account-statement/{id}` | Per-account ledger | `{account, transactions[], running_balance}` |

Query params for reports: `from_date`, `to_date`, `months` (for trends).

### 8.3 Transactions

| Method | Path | Description | Query Params |
|--------|------|-------------|-------------|
| GET | `/transactions` | Paginated list | `limit`, `offset`, `from_date`, `to_date` |
| GET | `/transactions/count` | Total count | - |

Response shape for each transaction:
```json
{
  "id": 1,
  "transaction_date": "2026-01-15",
  "description": "Salary Credit",
  "transaction_type": "BANK_TRANSFER",
  "status": "CONFIRMED",
  "reference_number": "REF123",
  "lines": [
    {"account_code": "1100", "account_name": "SBI Savings", "line_type": "DEBIT", "amount": "50000.00"},
    {"account_code": "4100", "account_name": "Salary Income", "line_type": "CREDIT", "amount": "50000.00"}
  ]
}
```

### 8.4 Accounts

| Method | Path | Description |
|--------|------|-------------|
| GET | `/accounts` | List accounts (flat) |
| GET | `/accounts/tree` | CoA hierarchy |
| GET | `/accounts/{id}` | Single account |
| GET | `/accounts/{id}/balance` | Account balance |

### 8.5 Goals

| Method | Path | Description |
|--------|------|-------------|
| GET | `/goals` | List goals with progress % |
| POST | `/goals` | Create goal |
| GET | `/goals/{id}` | Single goal |
| PATCH | `/goals/{id}` | Update goal |
| DELETE | `/goals/{id}` | Delete goal |

Goal object:
```json
{
  "id": 1,
  "name": "Emergency Fund",
  "goal_type": "EMERGENCY_FUND",
  "target_amount": "500000.00",
  "current_amount": "125000.00",
  "target_date": "2027-12-31",
  "sip_amount": "10000.00",
  "expected_return_rate": "7.5",
  "is_active": true,
  "progress_pct": 25.0
}
```

### 8.6 Budgets

| Method | Path | Description |
|--------|------|-------------|
| GET | `/budgets` | List budgets |
| POST | `/budgets` | Create budget with items |
| GET | `/budgets/{id}` | Single budget |
| DELETE | `/budgets/{id}` | Deactivate budget |

### 8.7 Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Server status (no auth) |

---

## 9. Screen Specifications

### 9.1Login Screen

**Layout**: Centered card on gradient background.

**Elements**:
- App logo/title "Ledger" at top (indigo-700, bold, large)
- Subtitle text ("Personal Finance Manager")
- Email input field (TextInputLayout with outlined style)
- Password input field (with toggle visibility)
- "Login" button (full-width, indigo-600 background, white text, rounded)
- "Create Account" text link below
- Error banner (amber-50 background, amber-600 border) for failed attempts

**Behavior**:
- On submit: show loading spinner on button, disable inputs
- On success: navigate to TenantPicker or directly to MainActivity (if single tenant)
- On error: show error banner with message from API

### 9.2Signup Screen

**Layout**: Similar to Login.

**Elements**:
- Full name input
- Email input
- Password input
- Entity type dropdown (PERSONAL, SOLE_PROPRIETOR, etc.)
- "Sign Up" button
- "Already have an account? Login" link

### 9.3Tenant Picker Screen

**Layout**: Simple list screen.

**Elements**:
- Header: "Select Account"
- RecyclerView of tenant cards (name, entity_type, role badge)
- Each card is tappable

**Behavior**:
- On tap: call `/auth/select-tenant`, store JWT, navigate to MainActivity
- If only one tenant: auto-select and skip this screen

### 9.4Dashboard Screen (Main Tab)

Mirrors the web `PersonalDashboard`. This is the default tab after login.

**Sections (top to bottom)**:

1. **Welcome Header**
   - "Welcome back" text (slate-500, small)
   - Net worth value (large, bold, indigo-700 if positive, rose-600 if negative)
   - Formatted as `₹12.5L` or `₹1.2Cr`

2. **Quick Stats Row** (horizontal scroll or 3-column grid)
   - Total Income card (emerald icon, emerald-700 value)
   - Total Expense card (rose icon, rose-700 value)
   - Savings Rate card (indigo icon, percentage)
   - Each: white card, rounded-xl, shadow-sm, icon in colored circle

3. **Goals Summary** (horizontal scroll of cards)
   - Each goal card: colored background, progress bar, name, current/target amounts
   - Goal type determines color (see Section 9)

4. **Recent Transactions** (last 5-10)
   - Each row: date, description, amount (green for credit, red for debit)
   - "View All" link at bottom

**API Calls**:
- `GET /reports/summary` - for net worth, income, expense, savings rate
- `GET /goals` - for goals summary
- `GET /transactions?limit=10` - for recent transactions

### 9.5Transactions Screen

**Layout**: Full-screen list with filter header.

**Header**:
- "Transactions" title
- Date range filter (from/to date pickers)
- Transaction count badge

**List** (RecyclerView):
- Each item:
  - Left: date (dd MMM) in a circle/badge
  - Center: description (bold), account names below (small, slate-500)
  - Right: amount with sign indicator (green/red dot or text color)
  - Status badge (CONFIRMED = green, PENDING = amber, VOID = slate)

**Pagination**:
- Load more on scroll (infinite scroll or "Load More" button)
- Uses `limit` and `offset` query params

**API Calls**:
- `GET /transactions?limit=20&offset=0`
- `GET /transactions/count`

### 9.6Reports Screen

Mirrors the web `ReportsPage`.

**Period Selector** (horizontal chip group):
- This Month / Last Month / This Quarter / This Year / Custom
- Active chip: indigo-600 background, white text

**Sections (scrollable)**:

1. **KPI Cards** (2x2 grid)
   - Net Worth (slate card)
   - Total Income (emerald card)
   - Total Expenses (rose card)
   - Savings Rate (indigo card)

2. **Monthly Trend** (bar chart)
   - Income bars (emerald) vs Expense bars (rose) grouped by month
   - X-axis: month labels
   - Uses MPAndroidChart grouped bar chart

3. **Expense Categories** (horizontal bar chart or list)
   - Category name, amount, percentage bar
   - Sorted by amount descending

4. **Balance Sheet Summary** (expandable tree)
   - Assets section (expandable)
   - Liabilities section (expandable)
   - Equity section (expandable)
   - Indented hierarchy matching web's tree view

**API Calls**:
- `GET /reports/summary`
- `GET /reports/monthly-trend`
- `GET /reports/expense-categories`
- `GET /reports/balance-sheet`
- `GET /reports/income-expense`

### 9.7Goals Screen

Mirrors the web `GoalsPage`.

**Header**:
- "Goals" title with target icon
- "+ New Goal" button (indigo-600)

**Summary Strip** (3 metrics):
- Total Goals count
- Total Target amount
- Average Progress percentage

**Goals List** (RecyclerView, 1 column):
- Each card:
  - Goal name (bold)
  - Goal type badge (colored pill)
  - Progress bar (green >= 75%, indigo >= 40%, amber < 40%)
  - Progress percentage text
  - Current / Target amounts
  - Target date (if set)
  - Tap to expand or view detail

**Empty State**:
- Centered icon + "No goals yet" + "Create your first financial goal" + CTA button

**Create Goal** (bottom sheet or new screen):
- Name input
- Goal type dropdown (EMERGENCY_FUND, RETIREMENT, HOME, EDUCATION, etc.)
- Target amount input (currency)
- Current amount input
- Target date picker
- SIP amount input
- Expected return rate input
- Save button

**API Calls**:
- `GET /goals`
- `POST /goals` (create)
- `PATCH /goals/{id}` (update)
- `DELETE /goals/{id}` (delete with confirmation dialog)

### 9.8Budgets Screen

Mirrors the web `BudgetsPage`.

**Header**:
- "Budgets" title
- "+ New Budget" button (emerald-600)

**Summary Strip** (3 metrics):
- Active Budgets count
- Total Planned amount
- Total Line Items count

**Budget Cards** (RecyclerView):
- Each card:
  - Budget name (bold)
  - Period type badge (MONTHLY / QUARTERLY / ANNUAL)
  - Date range (start - end)
  - Overall progress bar
  - Expandable section showing individual line items:
    - Account/category name
    - Planned amount
    - Mini progress bar

**Create Budget** (new screen or bottom sheet):
- Name input
- Period type selector (MONTHLY, QUARTERLY, ANNUAL, CUSTOM)
- Start date picker
- End date picker (optional)
- Line items section:
  - Account dropdown + Amount input
  - "Add Item" button
- Save button

**API Calls**:
- `GET /budgets`
- `POST /budgets`
- `DELETE /budgets/{id}`

### 9.9Settings Screen

**Sections**:

1. **Server Configuration**
   - Base URL text field (pre-filled with current `AppConfig.BASE_URL`)
   - "Test Connection" button (calls `GET /health`)
   - Connection status indicator (green check / red X)

2. **Account Info**
   - Logged-in email (read-only)
   - Current tenant name and role
   - "Switch Tenant" option (navigates to TenantPicker)

3. **Actions**
   - "Logout" button (clears token, navigates to Login)

---

## 10. UI Design System

### 10.1 Color Palette

Mapped from the web frontend's Tailwind theme:

```xml
<!-- colors.xml -->

<!-- Primary -->
<color name="indigo_50">#EEF2FF</color>
<color name="indigo_100">#E0E7FF</color>
<color name="indigo_500">#6366F1</color>
<color name="indigo_600">#4F46E5</color>
<color name="indigo_700">#4338CA</color>

<!-- Secondary -->
<color name="purple_500">#A855F7</color>
<color name="purple_600">#9333EA</color>

<!-- Success -->
<color name="emerald_50">#ECFDF5</color>
<color name="emerald_100">#D1FAE5</color>
<color name="emerald_500">#10B981</color>
<color name="emerald_600">#059669</color>
<color name="emerald_700">#047857</color>

<!-- Danger -->
<color name="rose_50">#FFF1F2</color>
<color name="rose_100">#FFE4E6</color>
<color name="rose_500">#F43F5E</color>
<color name="rose_600">#E11D48</color>

<!-- Warning -->
<color name="amber_50">#FFFBEB</color>
<color name="amber_100">#FEF3C7</color>
<color name="amber_500">#F59E0B</color>
<color name="amber_600">#D97706</color>

<!-- Info -->
<color name="cyan_500">#06B6D4</color>

<!-- Neutrals (Slate) -->
<color name="slate_50">#F8FAFC</color>
<color name="slate_100">#F1F5F9</color>
<color name="slate_200">#E2E8F0</color>
<color name="slate_300">#CBD5E1</color>
<color name="slate_400">#94A3B8</color>
<color name="slate_500">#64748B</color>
<color name="slate_600">#475569</color>
<color name="slate_700">#334155</color>
<color name="slate_800">#1E293B</color>
<color name="slate_900">#0F172A</color>

<!-- Backgrounds -->
<color name="background_primary">#F8FAFC</color>
<color name="surface_card">#FFFFFF</color>

<!-- Goal Type Colors -->
<color name="goal_retirement">#F59E0B</color>
<color name="goal_emergency">#EF4444</color>
<color name="goal_home">#10B981</color>
<color name="goal_education">#3B82F6</color>
<color name="goal_vehicle">#6366F1</color>
<color name="goal_vacation">#06B6D4</color>
<color name="goal_wedding">#EC4899</color>
<color name="goal_others">#64748B</color>
```

### 10.2 Typography

| Style | Font | Size (sp) | Weight | Color |
|-------|------|-----------|--------|-------|
| H1 / Page Title | Outfit | 24 | Bold (700) | slate_900 |
| H2 / Section Title | Outfit | 18 | Bold (700) | slate_800 |
| H3 / Card Title | Outfit | 16 | SemiBold (600) | slate_800 |
| Body | Plus Jakarta Sans | 14 | Regular (400) | slate_700 |
| Body Small | Plus Jakarta Sans | 12 | Regular (400) | slate_500 |
| Caption | Plus Jakarta Sans | 10 | Medium (500) | slate_400 |
| Label | Plus Jakarta Sans | 12 | SemiBold (600) | slate_600 |
| Large Number | Outfit | 28 | Bold (700) | varies |
| Badge | Plus Jakarta Sans | 10 | SemiBold (600) | varies |

Fonts imported via Google Fonts in `res/font/`.

### 10.3 Spacing & Dimensions

```xml
<!-- dimens.xml -->
<dimen name="page_padding">16dp</dimen>
<dimen name="card_padding">16dp</dimen>
<dimen name="card_padding_small">12dp</dimen>
<dimen name="section_gap">20dp</dimen>
<dimen name="item_gap">12dp</dimen>
<dimen name="card_radius">16dp</dimen>
<dimen name="card_radius_small">12dp</dimen>
<dimen name="button_radius">12dp</dimen>
<dimen name="badge_radius">100dp</dimen>
<dimen name="card_elevation">2dp</dimen>
<dimen name="icon_size_small">16dp</dimen>
<dimen name="icon_size_medium">24dp</dimen>
<dimen name="icon_size_large">36dp</dimen>
<dimen name="progress_bar_height">8dp</dimen>
<dimen name="progress_bar_height_small">6dp</dimen>
```

### 10.4 Card Style

```xml
<!-- Reusable card style -->
<style name="LedgerCard">
    <item name="android:background">@drawable/bg_card</item>
    <item name="android:padding">@dimen/card_padding</item>
    <item name="android:elevation">@dimen/card_elevation</item>
</style>
```

`bg_card` drawable: white fill, `card_radius` corners, `slate_100` stroke (1dp).

### 10.5 Button Styles

| Variant | Background | Text Color | Radius |
|---------|-----------|------------|--------|
| Primary | indigo_600 | white | 12dp |
| Primary Hover/Press | indigo_700 | white | 12dp |
| Secondary | transparent, slate_200 border | slate_700 | 12dp |
| Success | emerald_600 | white | 12dp |
| Danger | rose_500 | white | 12dp |
| Disabled | indigo_600 @ 50% alpha | white @ 50% alpha | 12dp |

### 10.6 Amount Display Colors

| Condition | Text Color |
|-----------|-----------|
| Positive amount / Income / Credit | emerald_600 |
| Negative amount / Expense / Debit | rose_600 |
| Net Worth (positive) | indigo_700 |
| Net Worth (negative) | rose_600 |
| Neutral | slate_800 |

### 10.7 Progress Bar Colors

| Range | Color |
|-------|-------|
| >= 75% | emerald_500 (green) |
| >= 40% | indigo_500 |
| < 40% | amber_500 |

For budget usage (inverse - lower is better):
| Range | Color |
|-------|-------|
| < 70% | emerald_500 |
| 70-90% | amber_500 |
| >= 90% | rose_500 |

### 10.8 Currency Formatting

```kotlin
object CurrencyFormatter {
    fun format(amount: Double): String {
        return when {
            amount >= 10_000_000 -> "₹${String.format("%.1f", amount / 10_000_000)}Cr"
            amount >= 100_000 -> "₹${String.format("%.1f", amount / 100_000)}L"
            else -> "₹${NumberFormat.getNumberInstance(Locale("en", "IN")).format(amount)}"
        }
    }

    fun formatExact(amount: Double): String {
        val nf = NumberFormat.getCurrencyInstance(Locale("en", "IN"))
        nf.currency = Currency.getInstance("INR")
        return nf.format(amount)
    }
}
```

---

## 11. Data Models (Kotlin)

### Auth Models

```kotlin
data class LoginRequest(val email: String, val password: String)

data class SignupRequest(
    val email: String,
    val password: String,
    val full_name: String? = null,
    val entity_type: String = "PERSONAL"
)

data class AuthListResponse(
    val user_id: Int,
    val email: String,
    val tenants: List<TenantInfo>,
    val message: String
)

data class TenantInfo(
    val tenant_id: String,
    val name: String,
    val entity_type: String,
    val role: String
)

data class SelectTenantRequest(val tenant_id: String)

data class TokenResponse(
    val access_token: String,
    val token_type: String,
    val user_id: Int,
    val tenant_id: String,
    val role: String
)
```

### Report Models

```kotlin
data class DashboardSummary(
    val net_worth: String,          // Decimal as string
    val total_income: String,
    val total_expense: String,
    val savings_rate: Double?,
    val cash_flow: String?
)

data class MonthlyTrend(
    val month: String,
    val income: String,
    val expense: String
)

data class ExpenseCategory(
    val category: String,
    val amount: String,
    val percentage: Double
)

data class BalanceSheetNode(
    val account_id: String?,
    val name: String,
    val code: String?,
    val balance: String,
    val children: List<BalanceSheetNode>?
)
```

### Transaction Models

```kotlin
data class TransactionListResponse(
    val items: List<TransactionOut>,
    val total: Int?
)

data class TransactionOut(
    val id: Int,
    val transaction_date: String,
    val description: String,
    val transaction_type: String,
    val status: String,
    val is_void: Boolean,
    val reference_number: String?,
    val lines: List<TransactionLine>
)

data class TransactionLine(
    val id: Int,
    val account_code: String,
    val account_name: String,
    val line_type: String,       // "DEBIT" or "CREDIT"
    val amount: String,          // Decimal as string
    val description: String?
)
```

### Account Models

```kotlin
data class AccountOut(
    val account_id: String,
    val name: String,
    val code: String?,
    val description: String,
    val account_type: String,
    val sub_type: String,
    val normal_balance: String,
    val parent_id: String?,
    val depth: Int,
    val is_system: Boolean,
    val is_leaf: Boolean,
    val is_active: Boolean,
    val currency: String,
    val balance: String
)
```

### Goal Models

```kotlin
data class GoalOut(
    val id: Int,
    val name: String,
    val goal_type: String,
    val target_amount: String,
    val current_amount: String,
    val target_date: String?,
    val currency_code: String,
    val is_active: Boolean,
    val notes: String?,
    val progress_pct: Double,
    val sip_amount: String?,
    val expected_return_rate: String?
)

data class GoalCreate(
    val name: String,
    val goal_type: String,
    val target_amount: String,
    val current_amount: String? = null,
    val target_date: String? = null,
    val sip_amount: String? = null,
    val expected_return_rate: String? = null,
    val notes: String? = null
)
```

### Budget Models

```kotlin
data class BudgetOut(
    val id: Int,
    val name: String,
    val period_type: String,
    val start_date: String,
    val end_date: String?,
    val is_active: Boolean,
    val items: List<BudgetItemOut>
)

data class BudgetItemOut(
    val id: Int,
    val account_id: Int,
    val account_code: String,
    val account_name: String,
    val planned_amount: String,
    val notes: String?
)

data class BudgetCreate(
    val name: String,
    val period_type: String,
    val start_date: String,
    val end_date: String? = null,
    val items: List<BudgetItemCreate>
)

data class BudgetItemCreate(
    val account_code: String,
    val planned_amount: String,
    val notes: String? = null
)
```

---

## 12. Navigation

### Navigation Component with Bottom Navigation Bar

**Bottom Nav Tabs** (matching the web app's top tabs):

| Tab | Label | Icon | Fragment |
|-----|-------|------|----------|
| 1 | Dashboard | `ic_dashboard` (LayoutDashboard equivalent) | DashboardFragment |
| 2 | Transactions | `ic_receipt` | TransactionsFragment |
| 3 | Reports | `ic_bar_chart` | ReportsFragment |
| 4 | Goals | `ic_target` | GoalsFragment |
| 5 | More | `ic_more` | MoreFragment (Budgets, Settings) |

**Why 5 tabs instead of 7**: Android's Material Design recommends 3-5 bottom nav items. The "More" tab provides access to Budgets and Settings.

### Navigation Graph (nav_graph.xml)

```
LoginActivity ──> TenantPickerActivity ──> MainActivity
                                              │
                                              ├── DashboardFragment
                                              ├── TransactionsFragment
                                              ├── ReportsFragment
                                              ├── GoalsFragment
                                              └── MoreFragment
                                                   ├── BudgetsFragment
                                                   └── SettingsFragment
```

### Bottom Navigation Styling

- Background: white
- Active icon + label: indigo_600
- Inactive icon + label: slate_400
- Indicator (Material 3): indigo_50 pill behind active icon

---

## 13. Error Handling

### API Error Response Format

The backend returns errors as:
```json
{
    "detail": "Error message string"
}
```
or
```json
{
    "detail": [
        {"loc": ["body", "field"], "msg": "error", "type": "value_error"}
    ]
}
```

### Error Handling Strategy

| Scenario | Behavior |
|----------|----------|
| No network | Show full-screen error with retry button ("No internet connection") |
| API timeout (30s) | Show toast "Request timed out. Please try again." |
| HTTP 401 Unauthorized | Clear token, redirect to LoginActivity |
| HTTP 400 Bad Request | Show error message from `detail` field |
| HTTP 404 Not Found | Show "Data not found" message |
| HTTP 500 Server Error | Show "Something went wrong. Please try again later." |
| Empty data | Show empty state illustration + message per screen |
| JSON parse error | Log error, show generic error message |

### Loading States

Every screen that fetches data shows:
1. **Loading**: centered `ProgressBar` (circular, indigo) with "Loading..." text
2. **Success**: content rendered
3. **Error**: error card with retry button

Implemented via a sealed class:
```kotlin
sealed class UiState<out T> {
    object Loading : UiState<Nothing>()
    data class Success<T>(val data: T) : UiState<T>()
    data class Error(val message: String) : UiState<Nothing>()
}
```

---

## 14. Test Specifications

### 14.1 Test Pyramid

```
         /‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾\
        /   Integration (7)  \         ← Phase 7: End-to-end flows (Emulator)
       /─────────────────────-\
      /     UI / Espresso (16)  \      ← Phase 6: Fragment + Activity tests (Emulator)
     /───────────────────────────\
    /   ViewModel Unit Tests (42)  \   ← Phase 3-5: Business logic (JVM, fast)
   /─────────────────────────────────\
  /  Network / API Unit Tests (15)     \ ← Phase 2: MockWebServer (JVM)
 /───────────────────────────────────────\
/ Foundation Unit Tests (15)               \ ← Phase 1: Models, Formatters, Utils (JVM)
\─────────────────────────────────────────/

Total: ~95 tests
JVM (fast, no emulator): ~72 tests  — run in < 10 seconds
Emulator (instrumented):  ~23 tests — run in < 2 minutes
```

### 14.2 Test Types

| Type | Location | Runs On | Speed | What It Tests |
|------|----------|---------|-------|---------------|
| **Unit** | `src/test/` | JVM (local) | Fast (ms) | Models, formatters, ViewModels, API parsing, interceptors |
| **Instrumented** | `src/androidTest/` | Emulator/device | Slow (s) | UI rendering, navigation, click handlers, full flows |

### 14.3 Test Infrastructure

#### MockWebServer Setup (Shared)

```kotlin
// Base class for API tests
abstract class BaseApiTest {
    protected lateinit var mockWebServer: MockWebServer
    protected lateinit var api: LedgerApiService

    @Before fun setUp() {
        mockWebServer = MockWebServer()
        mockWebServer.start()
        val retrofit = Retrofit.Builder()
            .baseUrl(mockWebServer.url("/"))
            .addConverterFactory(MoshiConverterFactory.create())
            .build()
        api = retrofit.create(LedgerApiService::class.java)
    }

    @After fun tearDown() {
        mockWebServer.shutdown()
    }

    // Helper to enqueue JSON responses
    protected fun enqueue(code: Int, jsonBody: String) {
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(code)
                .setBody(jsonBody)
                .addHeader("Content-Type", "application/json")
        )
    }
}
```

#### ViewModel Test Setup (Shared)

```kotlin
// Base class for ViewModel tests
abstract class BaseViewModelTest {
    @get:Rule val instantTaskRule = InstantTaskExecutorRule()

    protected val testDispatcher = StandardTestDispatcher()

    @Before fun setUp() {
        Dispatchers.setMain(testDispatcher)
    }

    @After fun tearDown() {
        Dispatchers.resetMain()
    }

    // Helper to observe LiveData synchronously
    protected fun <T> LiveData<T>.getOrAwait(): T { ... }
}
```

#### Test Fixtures (Shared JSON)

```kotlin
// TestFixtures.kt — reusable JSON response strings
object TestFixtures {
    val LOGIN_SUCCESS = """
        {"user_id":1,"email":"test@ledger.com",
         "tenants":[{"tenant_id":"uuid-1","name":"Home","entity_type":"PERSONAL","role":"OWNER"}],
         "message":"Login successful"}
    """.trimIndent()

    val LOGIN_MULTI_TENANT = """
        {"user_id":1,"email":"test@ledger.com",
         "tenants":[
           {"tenant_id":"uuid-1","name":"Personal","entity_type":"PERSONAL","role":"OWNER"},
           {"tenant_id":"uuid-2","name":"Business","entity_type":"SOLE_PROPRIETOR","role":"ADMIN"}
         ],"message":"Login successful"}
    """.trimIndent()

    val TOKEN_RESPONSE = """
        {"access_token":"eyJhbGciOiJIUzI1NiJ9.test","token_type":"bearer",
         "user_id":1,"tenant_id":"uuid-1","role":"OWNER"}
    """.trimIndent()

    val DASHBOARD_SUMMARY = """
        {"net_worth":"2500000.00","total_income":"150000.00",
         "total_expense":"95000.00","savings_rate":36.7,"cash_flow":"55000.00"}
    """.trimIndent()

    val GOALS_LIST = """
        [{"id":1,"name":"Emergency Fund","goal_type":"EMERGENCY_FUND",
          "target_amount":"500000.00","current_amount":"250000.00",
          "target_date":"2027-12-31","currency_code":"INR","is_active":true,
          "notes":null,"progress_pct":50.0,"sip_amount":"10000.00",
          "expected_return_rate":"7.50"},
         {"id":2,"name":"Europe Trip","goal_type":"HOLIDAY",
          "target_amount":"300000.00","current_amount":"75000.00",
          "target_date":"2027-06-01","currency_code":"INR","is_active":true,
          "notes":null,"progress_pct":25.0,"sip_amount":null,
          "expected_return_rate":null}]
    """.trimIndent()

    val TRANSACTIONS_PAGE_1 = """..."""  // 20 transactions
    val TRANSACTIONS_EMPTY = "[]"
    val BUDGETS_LIST = """..."""
    val ERROR_401 = """{"detail":"Invalid credentials"}"""
    val ERROR_500 = """{"detail":"Internal server error"}"""
    val HEALTH_OK = """{"status":"ok","version":"3.0","env":"development"}"""

    // ... additional fixtures per endpoint
}
```

### 14.4 Test Coverage Targets

| Layer | Coverage Target | Measured By |
|-------|----------------|-------------|
| Data Models (serialization) | 100% | All fields serialize/deserialize correctly |
| Utility classes | 100% | All branches of CurrencyFormatter, TokenManager |
| ViewModels | 90%+ | All state transitions: Loading, Success, Error |
| API Service | 100% | Every endpoint called, request validated, response parsed |
| Auth Interceptor | 100% | Token present/absent cases |
| UI Fragments | Key paths | Elements visible, click handlers trigger correct actions |
| Integration | Happy + error paths | Full flow from login to data display |

### 14.5 Running Tests

```bash
# Phase 1-5: All local unit tests (fast, no emulator needed)
cd android/
./gradlew test

# Single test class
./gradlew test --tests "com.ledger.app.util.CurrencyFormatterTest"

# Phase 6-7: Instrumented tests (requires running emulator)
./gradlew connectedAndroidTest

# Single instrumented test class
./gradlew connectedAndroidTest -Pandroid.testInstrumentationRunnerArguments.class=com.ledger.app.ui.auth.LoginActivityTest

# All tests with coverage report
./gradlew testDebugUnitTest jacocoTestReport
```

### 14.6 Test Dependencies (build.gradle.kts)

```kotlin
dependencies {
    // --- Unit Testing (src/test/) ---
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.8.0")
    testImplementation("androidx.arch.core:core-testing:2.2.0")       // InstantTaskExecutorRule
    testImplementation("io.mockk:mockk:1.13.10")                      // Mocking
    testImplementation("com.squareup.okhttp3:mockwebserver:4.12.0")   // API mocking
    testImplementation("com.google.truth:truth:1.4.2")                // Assertions (optional)
    testImplementation("com.squareup.moshi:moshi-kotlin:1.15.0")      // JSON in tests

    // --- Instrumented Testing (src/androidTest/) ---
    androidTestImplementation("androidx.test.ext:junit:1.1.5")
    androidTestImplementation("androidx.test.espresso:espresso-core:3.5.1")
    androidTestImplementation("androidx.test.espresso:espresso-contrib:3.5.1")  // RecyclerView
    androidTestImplementation("androidx.test.espresso:espresso-intents:3.5.1")  // Intent verification
    androidTestImplementation("androidx.test:runner:1.5.2")
    androidTestImplementation("androidx.test:rules:1.5.0")
    androidTestImplementation("androidx.fragment:fragment-testing:1.6.2")        // FragmentScenario
    androidTestImplementation("com.squareup.okhttp3:mockwebserver:4.12.0")     // API mocking in UI tests
    androidTestImplementation("androidx.navigation:navigation-testing:2.7.7")   // Nav test
    androidTestImplementation("io.mockk:mockk-android:1.13.10")                // Mocking on device

    // Debug helpers for fragment testing
    debugImplementation("androidx.fragment:fragment-testing-manifest:1.6.2")
}
```

### 14.7 Acceptance Checklist (Gate for Each Phase)

Each phase is only considered **complete** when all its tests pass.

| Phase | Gate Criteria | Test Command |
|-------|--------------|--------------|
| 1 - Foundation | All 15 model/util tests GREEN | `./gradlew test --tests "*.util.*" --tests "*.models.*"` |
| 2 - Network | All 15 API tests GREEN + Phase 1 still GREEN | `./gradlew test --tests "*.api.*"` |
| 3 - Auth VM | All 13 auth VM tests GREEN + Phase 1-2 still GREEN | `./gradlew test --tests "*.auth.*"` |
| 4 - Core VM | All 11 core VM tests GREEN + Phase 1-3 still GREEN | `./gradlew test --tests "*.dashboard.*" --tests "*.transactions.*"` |
| 5 - Feature VM | All 18 feature VM tests GREEN + Phase 1-4 still GREEN | `./gradlew test --tests "*.goals.*" --tests "*.budgets.*" --tests "*.reports.*"` |
| 6 - UI | All 16 Espresso tests GREEN + Phase 1-5 still GREEN | `./gradlew connectedAndroidTest --tests "*.ui.*"` |
| 7 - Integration | All 7 integration tests GREEN + ALL prior tests GREEN | `./gradlew connectedAndroidTest --tests "*.integration.*"` |
| **SHIP** | **`./gradlew test && ./gradlew connectedAndroidTest`** passes with 0 failures | Full suite |

### 14.8 Manual Smoke Test Checklist (Post-TDD Verification)

After all automated tests pass, verify these on the emulator with the **real backend**:

| # | Test | Expected |
|---|------|----------|
| 1 | Launch app without backend running | Error screen with retry button |
| 2 | Signup with new credentials | Success, navigate to dashboard |
| 3 | Login with valid credentials | Success, navigate to dashboard |
| 4 | Login with invalid credentials | Error message displayed |
| 5 | Dashboard loads real data | Net worth, stats, goals, transactions visible |
| 6 | Transactions list scrolls and paginates | Loads more on scroll |
| 7 | Reports show charts and real data | KPIs, bar chart, categories render |
| 8 | Goals CRUD against real API | Create, view, update, delete goals |
| 9 | Budgets CRUD against real API | Create, view, delete budgets |
| 10 | Change base URL in Settings | App connects to new URL |
| 11 | Test Connection button | Shows success/failure indicator |
| 12 | Logout and re-login | Token cleared, login screen shown |
| 13 | Token expiry | Redirected to login automatically |
| 14 | Rotate device | UI adapts, data preserved via ViewModel |
| 15 | Back button behavior | Proper navigation stack |

---

## 15. Build, Run & Test

### Prerequisites
- Android Studio (latest stable)
- JDK 17
- Android SDK 34
- Android Emulator with API 34 image
- Backend running at `http://127.0.0.1:8000`

### Steps (TDD Workflow)

1. Open `android/` folder in Android Studio
2. Sync Gradle
3. **Write tests first** for the current phase (see Section 2)
4. Run tests: `./gradlew test` (should FAIL — Red)
5. Write implementation code
6. Run tests: `./gradlew test` (should PASS — Green)
7. Refactor if needed, re-run tests
8. For UI/Integration tests: start emulator + backend, then `./gradlew connectedAndroidTest`

### Running the App (Manual Testing)

1. Start backend: `cd backend && python -m uvicorn src.main:app --host 0.0.0.0 --port 8000`
2. Select emulator device in Android Studio
3. Run app (Shift+F10)

### Key Gradle Dependencies

```kotlin
// build.gradle.kts (app module)
dependencies {
    // AndroidX Core
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("androidx.appcompat:appcompat:1.6.1")
    implementation("com.google.android.material:material:1.11.0")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")

    // Navigation
    implementation("androidx.navigation:navigation-fragment-ktx:2.7.7")
    implementation("androidx.navigation:navigation-ui-ktx:2.7.7")

    // Lifecycle (ViewModel + LiveData)
    implementation("androidx.lifecycle:lifecycle-viewmodel-ktx:2.7.0")
    implementation("androidx.lifecycle:lifecycle-livedata-ktx:2.7.0")

    // Retrofit + OkHttp
    implementation("com.squareup.retrofit2:retrofit:2.9.0")
    implementation("com.squareup.retrofit2:converter-moshi:2.9.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")

    // Moshi (JSON)
    implementation("com.squareup.moshi:moshi-kotlin:1.15.0")
    kapt("com.squareup.moshi:moshi-kotlin-codegen:1.15.0")

    // Encrypted SharedPreferences
    implementation("androidx.security:security-crypto:1.1.0-alpha06")

    // Charts
    implementation("com.github.PhilJay:MPAndroidChart:v3.1.0")

    // SwipeRefreshLayout
    implementation("androidx.swiperefreshlayout:swiperefreshlayout:1.1.0")

    // --- Unit Testing (see Section 14.6 for full list) ---
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.8.0")
    testImplementation("androidx.arch.core:core-testing:2.2.0")
    testImplementation("io.mockk:mockk:1.13.10")
    testImplementation("com.squareup.okhttp3:mockwebserver:4.12.0")

    // --- Instrumented Testing ---
    androidTestImplementation("androidx.test.ext:junit:1.1.5")
    androidTestImplementation("androidx.test.espresso:espresso-core:3.5.1")
    androidTestImplementation("androidx.test.espresso:espresso-contrib:3.5.1")
    androidTestImplementation("androidx.fragment:fragment-testing:1.6.2")
    androidTestImplementation("com.squareup.okhttp3:mockwebserver:4.12.0")
    debugImplementation("androidx.fragment:fragment-testing-manifest:1.6.2")
}
```

---

## 16. Future Considerations

These are **not in scope** for v1 but the architecture should not preclude them:

| Feature | Notes |
|---------|-------|
| Cloud base URL | Change `AppConfig.BASE_URL` or add a build variant |
| Offline mode | Add Room database + Repository layer for caching |
| Push notifications | FCM integration for transaction alerts |
| Import wizard | File upload from device to `/imports/upload` |
| Chat assistant | Chat screen using `/chat` endpoint |
| Biometric login | Store token with BiometricPrompt |
| Dark mode | Define `values-night/` color resources |
| Wealth dashboard | Additional tab with asset allocation charts |

---

## 17. Impact on Existing Code

### Changes Required to Existing Files

**NONE.** The Android app is a standalone client that:
- Lives in a new `android/` directory
- Communicates with the backend via its existing REST API
- Does not modify any backend or frontend code
- Uses the same API endpoints the web frontend already uses

### .gitignore Addition

The existing `.gitignore` should have these lines added for the Android project:

```gitignore
# Android
android/.gradle/
android/build/
android/app/build/
android/local.properties
android/.idea/
android/*.iml
android/app/*.iml
android/captures/
android/.externalNativeBuild/
android/.cxx/
```

This is the **only change to an existing file** — appending Android-specific ignore patterns to `.gitignore`. No existing patterns are modified or removed.

---

## Appendix A: Retrofit API Interface

```kotlin
interface LedgerApiService {

    // --- Auth ---
    @GET("api/v1/auth/status")
    suspend fun authStatus(): Response<Map<String, Any>>

    @POST("api/v1/auth/signup")
    suspend fun signup(@Body request: SignupRequest): Response<AuthListResponse>

    @POST("api/v1/auth/login")
    suspend fun login(@Body request: LoginRequest): Response<AuthListResponse>

    @POST("api/v1/auth/select-tenant")
    suspend fun selectTenant(@Body request: SelectTenantRequest): Response<TokenResponse>

    @POST("api/v1/auth/logout")
    suspend fun logout(): Response<Map<String, String>>

    // --- Dashboard / Reports ---
    @GET("api/v1/reports/summary")
    suspend fun getDashboardSummary(
        @Query("from_date") fromDate: String? = null,
        @Query("to_date") toDate: String? = null
    ): Response<DashboardSummary>

    @GET("api/v1/reports/income-expense")
    suspend fun getIncomeExpense(
        @Query("from_date") fromDate: String? = null,
        @Query("to_date") toDate: String? = null
    ): Response<Map<String, Any>>

    @GET("api/v1/reports/balance-sheet")
    suspend fun getBalanceSheet(
        @Query("as_of") asOf: String? = null
    ): Response<Map<String, Any>>

    @GET("api/v1/reports/net-worth-history")
    suspend fun getNetWorthHistory(
        @Query("months") months: Int? = null
    ): Response<List<Map<String, Any>>>

    @GET("api/v1/reports/monthly-trend")
    suspend fun getMonthlyTrend(
        @Query("months") months: Int? = null
    ): Response<List<MonthlyTrend>>

    @GET("api/v1/reports/expense-categories")
    suspend fun getExpenseCategories(
        @Query("from_date") fromDate: String? = null,
        @Query("to_date") toDate: String? = null
    ): Response<List<ExpenseCategory>>

    // --- Transactions ---
    @GET("api/v1/transactions")
    suspend fun getTransactions(
        @Query("limit") limit: Int = 20,
        @Query("offset") offset: Int = 0,
        @Query("from_date") fromDate: String? = null,
        @Query("to_date") toDate: String? = null
    ): Response<List<TransactionOut>>

    @GET("api/v1/transactions/count")
    suspend fun getTransactionCount(): Response<Map<String, Int>>

    // --- Accounts ---
    @GET("api/v1/accounts")
    suspend fun getAccounts(): Response<List<AccountOut>>

    @GET("api/v1/accounts/tree")
    suspend fun getAccountsTree(): Response<Map<String, Any>>

    @GET("api/v1/accounts/{id}/balance")
    suspend fun getAccountBalance(@Path("id") id: String): Response<Map<String, Any>>

    // --- Goals ---
    @GET("api/v1/goals")
    suspend fun getGoals(): Response<List<GoalOut>>

    @POST("api/v1/goals")
    suspend fun createGoal(@Body request: GoalCreate): Response<GoalOut>

    @GET("api/v1/goals/{id}")
    suspend fun getGoal(@Path("id") id: Int): Response<GoalOut>

    @PATCH("api/v1/goals/{id}")
    suspend fun updateGoal(@Path("id") id: Int, @Body request: Map<String, Any>): Response<GoalOut>

    @DELETE("api/v1/goals/{id}")
    suspend fun deleteGoal(@Path("id") id: Int): Response<Unit>

    // --- Budgets ---
    @GET("api/v1/budgets")
    suspend fun getBudgets(): Response<List<BudgetOut>>

    @POST("api/v1/budgets")
    suspend fun createBudget(@Body request: BudgetCreate): Response<BudgetOut>

    @GET("api/v1/budgets/{id}")
    suspend fun getBudget(@Path("id") id: Int): Response<BudgetOut>

    @DELETE("api/v1/budgets/{id}")
    suspend fun deleteBudget(@Path("id") id: Int): Response<Unit>

    // --- Health ---
    @GET("health")
    suspend fun healthCheck(): Response<Map<String, Any>>
}
```

---

*End of Specification*
