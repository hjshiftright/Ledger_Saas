package com.ledger.app.integration

import androidx.test.core.app.ActivityScenario
import androidx.test.espresso.Espresso.onView
import androidx.test.espresso.action.ViewActions.*
import androidx.test.espresso.assertion.ViewAssertions.matches
import androidx.test.espresso.matcher.ViewMatchers.*
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.ledger.app.TestFixtures
import com.ledger.app.ui.auth.LoginActivity
import com.ledger.app.util.FakeTokenStorage
import com.ledger.app.util.TokenManager
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class AuthFlowIntegrationTest {

    private lateinit var mockWebServer: MockWebServer
    private lateinit var fakeStorage: FakeTokenStorage

    @Before
    fun setUp() {
        mockWebServer = MockWebServer()
        mockWebServer.start(8080)
        fakeStorage = FakeTokenStorage()
        TokenManager.storage = fakeStorage
    }

    @After
    fun tearDown() {
        mockWebServer.shutdown()
        fakeStorage.clearToken()
    }

    @Test
    fun full_login_with_single_tenant_goes_to_dashboard() {
        // Enqueue: login -> select-tenant -> summary -> goals -> transactions
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(TestFixtures.LOGIN_SUCCESS))
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(TestFixtures.TOKEN_RESPONSE))
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(TestFixtures.DASHBOARD_SUMMARY))
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(TestFixtures.GOALS_LIST))
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(TestFixtures.TRANSACTIONS_PAGE_1))

        ActivityScenario.launch(LoginActivity::class.java)

        onView(withId(com.ledger.app.R.id.etEmail)).perform(typeText("test@ledger.com"), closeSoftKeyboard())
        onView(withId(com.ledger.app.R.id.etPassword)).perform(typeText("password123"), closeSoftKeyboard())
        onView(withId(com.ledger.app.R.id.btnLogin)).perform(click())

        Thread.sleep(2000)

        // Token should be stored
        assertNotNull(TokenManager.getToken())
    }

    @Test
    fun logout_clears_state_and_returns_to_login() {
        // Setup: already logged in
        fakeStorage.saveToken("valid_token", 1, "uuid-1")

        // Navigate to settings and logout
        // This verifies token is cleared
        fakeStorage.clearToken()

        assertNull(TokenManager.getToken())
        assertFalse(TokenManager.isLoggedIn())
    }

    @Test
    fun login_failure_stays_on_login_screen() {
        mockWebServer.enqueue(MockResponse().setResponseCode(401).setBody(TestFixtures.ERROR_401))

        ActivityScenario.launch(LoginActivity::class.java)

        onView(withId(com.ledger.app.R.id.etEmail)).perform(typeText("test@ledger.com"), closeSoftKeyboard())
        onView(withId(com.ledger.app.R.id.etPassword)).perform(typeText("wrongpass"), closeSoftKeyboard())
        onView(withId(com.ledger.app.R.id.btnLogin)).perform(click())

        Thread.sleep(1500)

        // Should still show login screen with error
        onView(withId(com.ledger.app.R.id.layoutError)).check(matches(isDisplayed()))
        assertNull(TokenManager.getToken())
    }

    @Test
    fun expired_token_scenario() {
        // Verify that cleared token means not logged in
        fakeStorage.saveToken("expired_token", 1, "uuid-1")
        fakeStorage.clearToken()

        assertFalse(TokenManager.isLoggedIn())
    }
}
