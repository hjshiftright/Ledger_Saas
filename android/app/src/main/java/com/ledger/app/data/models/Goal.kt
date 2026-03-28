package com.ledger.app.data.models

import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class GoalOut(
    val id: Int,
    val name: String,
    val goal_type: String,
    val target_amount: String,
    val current_amount: String,
    val target_date: String? = null,
    val currency_code: String = "INR",
    val is_active: Boolean = true,
    val notes: String? = null,
    val progress_pct: Double,
    val sip_amount: String? = null,
    val expected_return_rate: String? = null
)

@JsonClass(generateAdapter = true)
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
