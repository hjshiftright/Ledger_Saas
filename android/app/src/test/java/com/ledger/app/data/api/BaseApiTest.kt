package com.ledger.app.data.api

import com.ledger.app.data.models.*
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Before
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory

abstract class BaseApiTest {
    protected lateinit var mockWebServer: MockWebServer
    protected lateinit var api: LedgerApiService

    private val moshi = Moshi.Builder().addLast(KotlinJsonAdapterFactory()).build()

    @Before
    fun setUp() {
        mockWebServer = MockWebServer()
        mockWebServer.start()
        val retrofit = Retrofit.Builder()
            .baseUrl(mockWebServer.url("/"))
            .addConverterFactory(MoshiConverterFactory.create(moshi))
            .build()
        api = retrofit.create(LedgerApiService::class.java)
    }

    @After
    fun tearDown() {
        mockWebServer.shutdown()
    }

    protected fun enqueue(code: Int, jsonBody: String) {
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(code)
                .setBody(jsonBody)
                .addHeader("Content-Type", "application/json")
        )
    }
}
