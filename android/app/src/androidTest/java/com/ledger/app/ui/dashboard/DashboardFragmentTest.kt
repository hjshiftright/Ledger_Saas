package com.ledger.app.ui.dashboard

import androidx.fragment.app.testing.launchFragmentInContainer
import androidx.test.espresso.Espresso.onView
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
class DashboardFragmentTest {

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
    fun dashboard_shows_income_expense_cards() {
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(TestFixtures.DASHBOARD_SUMMARY))
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(TestFixtures.GOALS_LIST))
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(TestFixtures.TRANSACTIONS_PAGE_1))

        launchFragmentInContainer<DashboardFragment>(themeResId = R.style.Theme_Ledger)

        Thread.sleep(1500)

        onView(withId(R.id.tvTotalIncome)).check(matches(isDisplayed()))
        onView(withId(R.id.tvTotalExpense)).check(matches(isDisplayed()))
    }

    @Test
    fun dashboard_shows_net_worth() {
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(TestFixtures.DASHBOARD_SUMMARY))
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(TestFixtures.GOALS_LIST))
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(TestFixtures.TRANSACTIONS_PAGE_1))

        launchFragmentInContainer<DashboardFragment>(themeResId = R.style.Theme_Ledger)

        Thread.sleep(1500)

        // Net worth should be displayed (₹25.0L for 2500000)
        onView(withId(R.id.tvNetWorth)).check(matches(isDisplayed()))
        onView(withId(R.id.tvNetWorth)).check(matches(withText("₹25.0L")))
    }

    @Test
    fun dashboard_shows_recent_transactions() {
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(TestFixtures.DASHBOARD_SUMMARY))
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody("[]"))
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(TestFixtures.TRANSACTIONS_PAGE_1))

        launchFragmentInContainer<DashboardFragment>(themeResId = R.style.Theme_Ledger)

        Thread.sleep(1500)

        onView(withId(R.id.rvRecentTransactions)).check(matches(isDisplayed()))
    }

    @Test
    fun dashboard_shows_error_on_failure() {
        mockWebServer.enqueue(MockResponse().setResponseCode(500).setBody(TestFixtures.ERROR_500))
        mockWebServer.enqueue(MockResponse().setResponseCode(500).setBody(TestFixtures.ERROR_500))
        mockWebServer.enqueue(MockResponse().setResponseCode(500).setBody(TestFixtures.ERROR_500))

        launchFragmentInContainer<DashboardFragment>(themeResId = R.style.Theme_Ledger)

        Thread.sleep(1500)

        onView(withId(R.id.layoutError)).check(matches(isDisplayed()))
        onView(withId(R.id.btnRetry)).check(matches(isDisplayed()))
    }

    @Test
    fun dashboard_retry_reloads_data() {
        // First request fails
        mockWebServer.enqueue(MockResponse().setResponseCode(500).setBody(TestFixtures.ERROR_500))
        mockWebServer.enqueue(MockResponse().setResponseCode(500).setBody(TestFixtures.ERROR_500))
        mockWebServer.enqueue(MockResponse().setResponseCode(500).setBody(TestFixtures.ERROR_500))

        // Second request succeeds
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(TestFixtures.DASHBOARD_SUMMARY))
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody("[]"))
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody("[]"))

        launchFragmentInContainer<DashboardFragment>(themeResId = R.style.Theme_Ledger)

        Thread.sleep(1500)

        // Click retry
        onView(withId(R.id.btnRetry)).perform(androidx.test.espresso.action.ViewActions.click())

        Thread.sleep(1500)

        onView(withId(R.id.tvNetWorth)).check(matches(isDisplayed()))
    }

    @Test
    fun dashboard_shows_goals_section() {
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(TestFixtures.DASHBOARD_SUMMARY))
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(TestFixtures.GOALS_LIST))
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody("[]"))

        launchFragmentInContainer<DashboardFragment>(themeResId = R.style.Theme_Ledger)

        Thread.sleep(1500)

        onView(withId(R.id.rvGoals)).check(matches(isDisplayed()))
    }
}
