package com.ledger.app.util

import java.text.NumberFormat
import java.util.Currency
import java.util.Locale

object CurrencyFormatter {

    fun format(amount: Double): String {
        return when {
            amount >= 10_000_000 -> "₹${String.format("%.1f", amount / 10_000_000)}Cr"
            amount >= 100_000 -> "₹${String.format("%.1f", amount / 100_000)}L"
            else -> "₹${NumberFormat.getNumberInstance(Locale("en", "IN")).format(amount.toLong())}"
        }
    }

    fun formatExact(amount: Double): String {
        val nf = NumberFormat.getCurrencyInstance(Locale("en", "IN"))
        nf.currency = Currency.getInstance("INR")
        return nf.format(amount)
    }
}
