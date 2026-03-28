package com.ledger.app.util

class FakeTokenStorage : TokenStorage {
    private var token: String? = null
    private var userId: Int = 0
    private var tenantId: String = ""

    override fun getToken(): String? = token

    override fun saveToken(token: String, userId: Int, tenantId: String) {
        this.token = token
        this.userId = userId
        this.tenantId = tenantId
    }

    override fun clearToken() {
        token = null
        userId = 0
        tenantId = ""
    }
}
