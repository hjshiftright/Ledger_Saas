package com.ledger.app.data.api

import com.ledger.app.util.FakeTokenStorage
import com.ledger.app.util.TokenManager
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

class AuthInterceptorTest {

    private lateinit var mockWebServer: MockWebServer
    private lateinit var client: OkHttpClient
    private lateinit var fakeStorage: FakeTokenStorage

    @Before
    fun setUp() {
        mockWebServer = MockWebServer()
        mockWebServer.start()
        fakeStorage = com.ledger.app.util.FakeTokenStorage()
        TokenManager.storage = fakeStorage
        client = OkHttpClient.Builder()
            .addInterceptor(AuthInterceptor())
            .build()
    }

    @After
    fun tearDown() {
        mockWebServer.shutdown()
    }

    @Test
    fun adds_bearer_token_when_present() {
        fakeStorage.saveToken("abc123", 1, "tenant1")
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody("{}"))

        val request = Request.Builder()
            .url(mockWebServer.url("/test"))
            .build()
        client.newCall(request).execute()

        val recorded = mockWebServer.takeRequest()
        assertEquals("Bearer abc123", recorded.getHeader("Authorization"))
    }

    @Test
    fun no_header_when_no_token() {
        // No token saved
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody("{}"))

        val request = Request.Builder()
            .url(mockWebServer.url("/test"))
            .build()
        client.newCall(request).execute()

        val recorded = mockWebServer.takeRequest()
        assertNull(recorded.getHeader("Authorization"))
    }
}
