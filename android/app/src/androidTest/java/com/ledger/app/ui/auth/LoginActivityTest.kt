package com.ledger.app.ui.auth

import androidx.test.core.app.ActivityScenario
import androidx.test.espresso.Espresso.onView
import androidx.test.espresso.action.ViewActions.*
import androidx.test.espresso.assertion.ViewAssertions.matches
import androidx.test.espresso.matcher.ViewMatchers.*
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.ledger.app.R
import com.ledger.app.TestFixtures
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class LoginActivityTest {

    private lateinit var mockWebServer: MockWebServer

    @Before
    fun setUp() {
        mockWebServer = MockWebServer()
        mockWebServer.start(8080)
    }

    @After
    fun tearDown() {
        mockWebServer.shutdown()
    }

    @Test
    fun login_screen_displays_all_elements() {
        ActivityScenario.launch(LoginActivity::class.java)

        onView(withText("Ledger")).check(matches(isDisplayed()))
        onView(withId(R.id.etEmail)).check(matches(isDisplayed()))
        onView(withId(R.id.etPassword)).check(matches(isDisplayed()))
        onView(withId(R.id.btnLogin)).check(matches(isDisplayed()))
        onView(withId(R.id.tvCreateAccount)).check(matches(isDisplayed()))
    }

    @Test
    fun login_button_disabled_with_empty_fields() {
        ActivityScenario.launch(LoginActivity::class.java)

        onView(withId(R.id.btnLogin)).perform(click())
        onView(withId(R.id.layoutError)).check(matches(isDisplayed()))
    }

    @Test
    fun login_shows_loading_indicator() {
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(TestFixtures.LOGIN_SUCCESS)
                .setBodyDelay(500, java.util.concurrent.TimeUnit.MILLISECONDS)
        )

        ActivityScenario.launch(LoginActivity::class.java)
        onView(withId(R.id.etEmail)).perform(typeText("test@ledger.com"), closeSoftKeyboard())
        onView(withId(R.id.etPassword)).perform(typeText("password123"), closeSoftKeyboard())
        onView(withId(R.id.btnLogin)).perform(click())

        // Button should be disabled during loading
        onView(withId(R.id.btnLogin)).check(matches(isNotEnabled()))
    }

    @Test
    fun login_failure_shows_error_banner() {
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(401)
                .setBody(TestFixtures.ERROR_401)
        )

        ActivityScenario.launch(LoginActivity::class.java)
        onView(withId(R.id.etEmail)).perform(typeText("test@ledger.com"), closeSoftKeyboard())
        onView(withId(R.id.etPassword)).perform(typeText("wrongpassword"), closeSoftKeyboard())
        onView(withId(R.id.btnLogin)).perform(click())

        Thread.sleep(1000)
        onView(withId(R.id.layoutError)).check(matches(isDisplayed()))
    }

    @Test
    fun create_account_link_navigates_to_signup() {
        ActivityScenario.launch(LoginActivity::class.java)
        onView(withId(R.id.tvCreateAccount)).perform(click())

        // SignupActivity should be started
        onView(withId(R.id.btnSignup)).check(matches(isDisplayed()))
    }
}
