package com.ledger.app.data.api

import com.ledger.app.data.models.*
import retrofit2.Response
import retrofit2.http.*

interface LedgerApiService {

    // --- Auth ---
    @POST("api/v1/auth/login")
    suspend fun login(@Body request: LoginRequest): Response<AuthListResponse>

    @POST("api/v1/auth/signup")
    suspend fun signup(@Body request: SignupRequest): Response<AuthListResponse>

    @POST("api/v1/auth/select-tenant")
    suspend fun selectTenant(@Body request: SelectTenantRequest): Response<TokenResponse>

    @POST("api/v1/auth/logout")
    suspend fun logout(): Response<Map<String, String>>

    @GET("api/v1/auth/status")
    suspend fun authStatus(): Response<Map<String, Any>>

    // --- Reports / Dashboard ---
    @GET("api/v1/reports/summary")
    suspend fun getDashboardSummary(
        @Query("from_date") fromDate: String? = null,
        @Query("to_date") toDate: String? = null
    ): Response<DashboardSummary>

    @GET("api/v1/reports/monthly-trend")
    suspend fun getMonthlyTrend(
        @Query("from_date") fromDate: String? = null,
        @Query("to_date") toDate: String? = null,
        @Query("months") months: Int? = null
    ): Response<List<MonthlyTrend>>

    @GET("api/v1/reports/expense-categories")
    suspend fun getExpenseCategories(
        @Query("from_date") fromDate: String? = null,
        @Query("to_date") toDate: String? = null
    ): Response<List<ExpenseCategory>>

    @GET("api/v1/reports/balance-sheet")
    suspend fun getBalanceSheet(
        @Query("from_date") fromDate: String? = null,
        @Query("to_date") toDate: String? = null
    ): Response<Map<String, Any>>

    @GET("api/v1/reports/income-expense")
    suspend fun getIncomeExpense(
        @Query("from_date") fromDate: String? = null,
        @Query("to_date") toDate: String? = null
    ): Response<Map<String, Any>>

    @GET("api/v1/reports/net-worth-history")
    suspend fun getNetWorthHistory(
        @Query("months") months: Int? = null
    ): Response<List<Map<String, String>>>

    // --- Transactions ---
    @GET("api/v1/transactions")
    suspend fun getTransactions(
        @Query("limit") limit: Int = 20,
        @Query("offset") offset: Int = 0,
        @Query("from_date") fromDate: String? = null,
        @Query("to_date") toDate: String? = null
    ): Response<List<TransactionOut>>

    @GET("api/v1/transactions/count")
    suspend fun getTransactionCount(): Response<TransactionCountResponse>

    // --- Accounts ---
    @GET("api/v1/accounts")
    suspend fun getAccounts(): Response<List<AccountOut>>

    @GET("api/v1/accounts/tree")
    suspend fun getAccountsTree(): Response<List<AccountOut>>

    @GET("api/v1/accounts/{id}")
    suspend fun getAccount(@Path("id") id: String): Response<AccountOut>

    // --- Goals ---
    @GET("api/v1/goals")
    suspend fun getGoals(): Response<List<GoalOut>>

    @POST("api/v1/goals")
    suspend fun createGoal(@Body request: GoalCreate): Response<GoalOut>

    @GET("api/v1/goals/{id}")
    suspend fun getGoal(@Path("id") id: Int): Response<GoalOut>

    @PATCH("api/v1/goals/{id}")
    suspend fun updateGoal(
        @Path("id") id: Int,
        @Body updates: Map<String, String>
    ): Response<GoalOut>

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
    suspend fun healthCheck(): Response<HealthResponse>
}
