package com.ledger.app.data.models

import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

class DataModelTest {

    private lateinit var moshi: Moshi

    @Before
    fun setUp() {
        moshi = Moshi.Builder().addLast(KotlinJsonAdapterFactory()).build()
    }

    @Test
    fun login_request_serializes_correctly() {
        val request = LoginRequest("user@test.com", "pass123")
        val adapter = moshi.adapter(LoginRequest::class.java)
        val json = adapter.toJson(request)
        assertTrue("JSON should contain email", json.contains("email"))
        assertTrue("JSON should contain password", json.contains("password"))
        assertTrue("JSON should contain user@test.com", json.contains("user@test.com"))
    }

    @Test
    fun auth_response_deserializes_with_tenants() {
        val json = """{"user_id":1,"email":"a@b.com","tenants":[{"tenant_id":"uuid","name":"Home","entity_type":"PERSONAL","role":"OWNER"}],"message":"ok"}"""
        val adapter = moshi.adapter(AuthListResponse::class.java)
        val response = adapter.fromJson(json)!!
        assertEquals(1, response.tenants.size)
        assertEquals("OWNER", response.tenants[0].role)
    }

    @Test
    fun goal_out_deserializes_progress() {
        val json = """{"id":1,"name":"Test","goal_type":"EMERGENCY_FUND","target_amount":"500000.00","current_amount":"100000.00","target_date":null,"currency_code":"INR","is_active":true,"notes":null,"progress_pct":65.5,"sip_amount":null,"expected_return_rate":null}"""
        val adapter = moshi.adapter(GoalOut::class.java)
        val goal = adapter.fromJson(json)!!
        assertEquals(65.5, goal.progress_pct, 0.001)
    }

    @Test
    fun transaction_out_deserializes_lines() {
        val json = """{"id":1,"transaction_date":"2026-01-15","description":"Salary","transaction_type":"BANK_TRANSFER","status":"CONFIRMED","is_void":false,"reference_number":null,"lines":[{"id":1,"account_code":"1100","account_name":"SBI Savings","line_type":"DEBIT","amount":"50000.00","description":null},{"id":2,"account_code":"4100","account_name":"Salary Income","line_type":"CREDIT","amount":"50000.00","description":null}]}"""
        val adapter = moshi.adapter(TransactionOut::class.java)
        val txn = adapter.fromJson(json)!!
        assertEquals(2, txn.lines.size)
        assertEquals("DEBIT", txn.lines[0].line_type)
    }

    @Test
    fun dashboard_summary_handles_null_savings_rate() {
        val json = """{"net_worth":"1500000.00","total_income":"100000.00","total_expense":"60000.00","savings_rate":null,"cash_flow":"40000.00"}"""
        val adapter = moshi.adapter(DashboardSummary::class.java)
        val summary = adapter.fromJson(json)!!
        assertNull(summary.savings_rate)
    }

    @Test
    fun budget_create_serializes_items() {
        val budget = BudgetCreate(
            name = "Monthly",
            period_type = "MONTHLY",
            start_date = "2026-01-01",
            items = listOf(
                BudgetItemCreate("5100", "10000"),
                BudgetItemCreate("5200", "5000"),
                BudgetItemCreate("5300", "3000")
            )
        )
        val adapter = moshi.adapter(BudgetCreate::class.java)
        val json = adapter.toJson(budget)
        assertTrue("JSON should contain items", json.contains("items"))
        // Count occurrences of "account_code" to verify 3 items
        val count = json.split("account_code").size - 1
        assertEquals(3, count)
    }
}
