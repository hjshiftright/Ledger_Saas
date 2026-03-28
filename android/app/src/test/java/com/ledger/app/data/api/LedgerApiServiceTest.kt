package com.ledger.app.data.api

import com.ledger.app.data.models.GoalCreate
import com.ledger.app.data.models.LoginRequest
import com.ledger.app.data.models.SelectTenantRequest
import kotlinx.coroutines.runBlocking
import org.junit.Assert.*
import org.junit.Test

class LedgerApiServiceTest : BaseApiTest() {

    @Test
    fun login_sends_correct_request() = runBlocking {
        enqueue(200, """{"user_id":1,"email":"a@b.com","tenants":[{"tenant_id":"uuid","name":"Home","entity_type":"PERSONAL","role":"OWNER"}],"message":"ok"}""")
        api.login(LoginRequest("a@b.com", "pwd"))
        val request = mockWebServer.takeRequest()
        assertTrue(request.path!!.contains("/auth/login"))
        assertEquals("POST", request.method)
        val body = request.body.readUtf8()
        assertTrue(body.contains("email"))
        assertTrue(body.contains("password"))
    }

    @Test
    fun login_success_parses_response() = runBlocking {
        enqueue(200, """{"user_id":1,"email":"a@b.com","tenants":[{"tenant_id":"uuid","name":"Home","entity_type":"PERSONAL","role":"OWNER"}],"message":"ok"}""")
        val response = api.login(LoginRequest("a@b.com", "pwd"))
        assertTrue(response.isSuccessful)
        assertEquals(1, response.body()!!.user_id)
        assertTrue(response.body()!!.tenants.isNotEmpty())
    }

    @Test
    fun login_failure_returns_401() = runBlocking {
        enqueue(401, """{"detail":"Invalid credentials"}""")
        val response = api.login(LoginRequest("a@b.com", "wrong"))
        assertEquals(401, response.code())
        assertFalse(response.isSuccessful)
    }

    @Test
    fun select_tenant_returns_jwt() = runBlocking {
        enqueue(200, """{"access_token":"jwt_token_here","token_type":"bearer","user_id":1,"tenant_id":"uuid","role":"OWNER"}""")
        val response = api.selectTenant(SelectTenantRequest("uuid"))
        assertEquals("jwt_token_here", response.body()!!.access_token)
    }

    @Test
    fun get_dashboard_summary_success() = runBlocking {
        enqueue(200, """{"net_worth":"1500000.00","total_income":"100000.00","total_expense":"60000.00","savings_rate":40.0,"cash_flow":"40000.00"}""")
        val response = api.getDashboardSummary()
        assertEquals("1500000.00", response.body()!!.net_worth)
    }

    @Test
    fun get_transactions_with_pagination() = runBlocking {
        val items = (1..20).joinToString(",") { i ->
            """{"id":$i,"transaction_date":"2026-01-${i.toString().padStart(2,'0')}","description":"Txn $i","transaction_type":"EXPENSE","status":"CONFIRMED","is_void":false,"lines":[]}"""
        }
        enqueue(200, "[$items]")
        val response = api.getTransactions(limit = 20, offset = 0)
        val request = mockWebServer.takeRequest()
        assertTrue(request.path!!.contains("limit=20"))
        assertTrue(request.path!!.contains("offset=0"))
        assertEquals(20, response.body()!!.size)
    }

    @Test
    fun get_transactions_with_date_filter() = runBlocking {
        enqueue(200, "[]")
        api.getTransactions(fromDate = "2026-01-01", toDate = "2026-03-31")
        val request = mockWebServer.takeRequest()
        assertTrue(request.path!!.contains("from_date=2026-01-01"))
        assertTrue(request.path!!.contains("to_date=2026-03-31"))
    }

    @Test
    fun get_goals_returns_list() = runBlocking {
        val goalsJson = """[{"id":1,"name":"Goal 1","goal_type":"EMERGENCY_FUND","target_amount":"500000","current_amount":"100000","currency_code":"INR","is_active":true,"progress_pct":20.0},{"id":2,"name":"Goal 2","goal_type":"RETIREMENT","target_amount":"1000000","current_amount":"200000","currency_code":"INR","is_active":true,"progress_pct":20.0},{"id":3,"name":"Goal 3","goal_type":"HOME","target_amount":"2000000","current_amount":"100000","currency_code":"INR","is_active":true,"progress_pct":5.0}]"""
        enqueue(200, goalsJson)
        val response = api.getGoals()
        assertEquals(3, response.body()!!.size)
    }

    @Test
    fun create_goal_sends_body() = runBlocking {
        enqueue(201, """{"id":1,"name":"Trip","goal_type":"HOLIDAY","target_amount":"100000","current_amount":"0","currency_code":"INR","is_active":true,"progress_pct":0.0}""")
        api.createGoal(GoalCreate(name = "Trip", goal_type = "HOLIDAY", target_amount = "100000"))
        val request = mockWebServer.takeRequest()
        val body = request.body.readUtf8()
        assertTrue(body.contains("name"))
        assertTrue(body.contains("goal_type"))
        assertTrue(body.contains("target_amount"))
    }

    @Test
    fun delete_goal_sends_delete_method() = runBlocking {
        enqueue(204, "")
        api.deleteGoal(5)
        val request = mockWebServer.takeRequest()
        assertTrue(request.path!!.contains("/goals/5"))
        assertEquals("DELETE", request.method)
    }

    @Test
    fun get_budgets_returns_list() = runBlocking {
        enqueue(200, """[{"id":1,"name":"Monthly Budget","period_type":"MONTHLY","start_date":"2026-01-01","is_active":true,"items":[]}]""")
        val response = api.getBudgets()
        assertTrue(response.body()!!.isNotEmpty())
    }

    @Test
    fun health_check_success() = runBlocking {
        enqueue(200, """{"status":"ok","version":"3.0"}""")
        val response = api.healthCheck()
        assertTrue(response.isSuccessful)
    }

    @Test
    fun server_error_returns_500() = runBlocking {
        enqueue(500, """{"detail":"Internal server error"}""")
        val response = api.getDashboardSummary()
        assertEquals(500, response.code())
    }
}
