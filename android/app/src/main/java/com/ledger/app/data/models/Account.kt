package com.ledger.app.data.models

import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class AccountOut(
    val account_id: String,
    val name: String,
    val code: String? = null,
    val description: String = "",
    val account_type: String,
    val sub_type: String,
    val normal_balance: String,
    val parent_id: String? = null,
    val depth: Int = 0,
    val is_system: Boolean = false,
    val is_leaf: Boolean = true,
    val is_active: Boolean = true,
    val currency: String = "INR",
    val balance: String = "0.00"
)
