package com.ledger.app.data.models

import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class BudgetOut(
    val id: Int,
    val name: String,
    val period_type: String,
    val start_date: String,
    val end_date: String? = null,
    val is_active: Boolean = true,
    val items: List<BudgetItemOut> = emptyList()
)

@JsonClass(generateAdapter = true)
data class BudgetItemOut(
    val id: Int,
    val account_id: Int,
    val account_code: String,
    val account_name: String,
    val planned_amount: String,
    val notes: String? = null
)

@JsonClass(generateAdapter = true)
data class BudgetCreate(
    val name: String,
    val period_type: String,
    val start_date: String,
    val end_date: String? = null,
    val items: List<BudgetItemCreate>
)

@JsonClass(generateAdapter = true)
data class BudgetItemCreate(
    val account_code: String,
    val planned_amount: String,
    val notes: String? = null
)
