package com.ledger.app.util

import org.junit.Assert.*
import org.junit.Test

class CurrencyFormatterTest {

    @Test
    fun format_crores_shows_Cr_suffix() {
        assertEquals("₹2.5Cr", CurrencyFormatter.format(25_000_000.0))
    }

    @Test
    fun format_lakhs_shows_L_suffix() {
        assertEquals("₹3.5L", CurrencyFormatter.format(350_000.0))
    }

    @Test
    fun format_thousands_shows_indian_locale() {
        val result = CurrencyFormatter.format(42_500.0)
        assertTrue("Expected ₹42,500 but got $result", result.contains("42,500"))
    }

    @Test
    fun format_small_amount() {
        val result = CurrencyFormatter.format(750.0)
        assertTrue("Expected ₹750 but got $result", result.contains("750"))
    }

    @Test
    fun format_zero() {
        val result = CurrencyFormatter.format(0.0)
        assertTrue("Expected ₹0 but got $result", result.contains("0"))
    }

    @Test
    fun formatExact_shows_full_decimal() {
        val result = CurrencyFormatter.formatExact(123456.78)
        assertTrue("Expected formatted amount with 123,456 but got $result",
            result.contains("1,23,456") || result.contains("123,456"))
    }
}
