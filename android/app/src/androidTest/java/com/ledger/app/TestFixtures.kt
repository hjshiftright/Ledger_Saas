package com.ledger.app

object TestFixtures {
    val LOGIN_SUCCESS = """{"user_id":1,"email":"test@ledger.com","tenants":[{"tenant_id":"uuid-1","name":"Home","entity_type":"PERSONAL","role":"OWNER"}],"message":"Login successful"}"""

    val LOGIN_MULTI_TENANT = """{"user_id":1,"email":"test@ledger.com","tenants":[{"tenant_id":"uuid-1","name":"Personal","entity_type":"PERSONAL","role":"OWNER"},{"tenant_id":"uuid-2","name":"Business","entity_type":"SOLE_PROPRIETOR","role":"ADMIN"}],"message":"Login successful"}"""

    val TOKEN_RESPONSE = """{"access_token":"eyJhbGciOiJIUzI1NiJ9.test","token_type":"bearer","user_id":1,"tenant_id":"uuid-1","role":"OWNER"}"""

    val DASHBOARD_SUMMARY = """{"net_worth":"2500000.00","total_income":"150000.00","total_expense":"95000.00","savings_rate":36.7,"cash_flow":"55000.00"}"""

    val GOALS_LIST = """[{"id":1,"name":"Emergency Fund","goal_type":"EMERGENCY_FUND","target_amount":"500000.00","current_amount":"250000.00","target_date":"2027-12-31","currency_code":"INR","is_active":true,"notes":null,"progress_pct":50.0,"sip_amount":"10000.00","expected_return_rate":"7.50"},{"id":2,"name":"Europe Trip","goal_type":"HOLIDAY","target_amount":"300000.00","current_amount":"75000.00","target_date":"2027-06-01","currency_code":"INR","is_active":true,"notes":null,"progress_pct":25.0,"sip_amount":null,"expected_return_rate":null}]"""

    val TRANSACTIONS_EMPTY = "[]"

    val TRANSACTIONS_PAGE_1 = "[" + (1..10).joinToString(",") { i ->
        """{"id":$i,"transaction_date":"2026-01-${i.toString().padStart(2,'0')}","description":"Transaction $i","transaction_type":"EXPENSE","status":"CONFIRMED","is_void":false,"lines":[{"id":$i,"account_code":"5100","account_name":"Expenses","line_type":"DEBIT","amount":"1000.00","description":null}]}"""
    } + "]"

    val BUDGETS_LIST = """[{"id":1,"name":"Monthly Budget","period_type":"MONTHLY","start_date":"2026-01-01","end_date":null,"is_active":true,"items":[{"id":1,"account_id":1,"account_code":"5100","account_name":"Food","planned_amount":"10000.00","notes":null}]}]"""

    val ERROR_401 = """{"detail":"Invalid credentials"}"""
    val ERROR_500 = """{"detail":"Internal server error"}"""
    val HEALTH_OK = """{"status":"ok","version":"3.0","env":"development"}"""

    val TRANSACTION_COUNT = """{"count":150}"""
}
