package com.ledger.app.data.models

import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class DashboardSummary(
    val net_worth: String,
    val total_assets: String? = null,
    val total_liabilities: String? = null,
    val period_income: String,
    val period_expenses: String,
    val net_income: String,
    val savings_rate: Double?,
    val as_of: String? = null,
    val from_date: String? = null,
    val to_date: String? = null
)

@JsonClass(generateAdapter = true)
data class MonthlyTrend(
    val month: String,
    val income: String,
    val expense: String
)

@JsonClass(generateAdapter = true)
data class ExpenseCategory(
    val category: String,
    val amount: String,
    val percentage: Double
)

@JsonClass(generateAdapter = true)
data class BalanceSheetNode(
    val account_id: String? = null,
    val name: String,
    val code: String? = null,
    val balance: String,
    val children: List<BalanceSheetNode>? = null
)

@JsonClass(generateAdapter = true)
data class HealthResponse(
    val status: String,
    val version: String? = null,
    val env: String? = null
)
