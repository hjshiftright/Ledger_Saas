package com.ledger.app.util

import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

class TokenManagerTest {

    private lateinit var fakeStorage: FakeTokenStorage

    @Before
    fun setUp() {
        fakeStorage = FakeTokenStorage()
        TokenManager.storage = fakeStorage
    }

    @Test
    fun initially_no_token_stored() {
        assertNull(TokenManager.getToken())
        assertFalse(TokenManager.isLoggedIn())
    }

    @Test
    fun save_and_retrieve_token() {
        TokenManager.saveToken(token = "jwt_abc", userId = 1, tenantId = "tenant-uuid")
        assertEquals("jwt_abc", TokenManager.getToken())
        assertTrue(TokenManager.isLoggedIn())
    }

    @Test
    fun clear_token_removes_all() {
        TokenManager.saveToken(token = "jwt_abc", userId = 1, tenantId = "t1")
        TokenManager.clearToken()
        assertNull(TokenManager.getToken())
        assertFalse(TokenManager.isLoggedIn())
    }

    @Test
    fun overwrite_token() {
        TokenManager.saveToken(token = "old_token", userId = 1, tenantId = "t1")
        TokenManager.saveToken(token = "new_token", userId = 2, tenantId = "t2")
        assertEquals("new_token", TokenManager.getToken())
    }
}
