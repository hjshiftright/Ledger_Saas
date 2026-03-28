package com.ledger.app.data.models

import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class TransactionOut(
    val id: Int,
    val transaction_date: String,
    val description: String,
    val transaction_type: String,
    val status: String,
    val is_void: Boolean = false,
    val reference_number: String? = null,
    val lines: List<TransactionLine> = emptyList()
)

@JsonClass(generateAdapter = true)
data class TransactionLine(
    val id: Int = 0,
    val account_code: String,
    val account_name: String,
    val line_type: String,
    val amount: String,
    val description: String? = null
)

@JsonClass(generateAdapter = true)
data class TransactionCountResponse(
    val count: Int
)
