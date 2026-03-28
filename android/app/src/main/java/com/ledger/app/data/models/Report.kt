package com.ledger.app.data.models

import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class DashboardSummary(
    val net_worth: String,
    val total_income: String,
    val total_expense: String,
    val savings_rate: Double?,
    val cash_flow: String? = null
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
