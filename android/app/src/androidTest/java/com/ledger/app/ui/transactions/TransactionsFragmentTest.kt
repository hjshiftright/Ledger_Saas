package com.ledger.app.ui.transactions

import androidx.fragment.app.testing.launchFragmentInContainer
import androidx.test.espresso.Espresso.onView
import androidx.test.espresso.assertion.ViewAssertions.matches
import androidx.test.espresso.matcher.ViewMatchers.*
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.ledger.app.R
import com.ledger.app.TestFixtures
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.hamcrest.Matchers.not
import org.junit.After
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class TransactionsFragmentTest {

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
    fun transactions_list_renders_items() {
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(TestFixtures.TRANSACTIONS_PAGE_1))
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(TestFixtures.TRANSACTION_COUNT))

        launchFragmentInContainer<TransactionsFragment>(themeResId = R.style.Theme_Ledger)

        Thread.sleep(1500)

        onView(withId(R.id.rvTransactions)).check(matches(isDisplayed()))
        onView(withId(R.id.layoutEmpty)).check(matches(not(isDisplayed())))
    }

    @Test
    fun transaction_item_shows_description_and_amount() {
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(TestFixtures.TRANSACTIONS_PAGE_1))
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(TestFixtures.TRANSACTION_COUNT))

        launchFragmentInContainer<TransactionsFragment>(themeResId = R.style.Theme_Ledger)

        Thread.sleep(1500)

        // The first transaction should show "Transaction 1"
        onView(withText("Transaction 1")).check(matches(isDisplayed()))
    }

    @Test
    fun empty_transactions_shows_empty_state() {
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(TestFixtures.TRANSACTIONS_EMPTY))
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody("""{"count":0}"""))

        launchFragmentInContainer<TransactionsFragment>(themeResId = R.style.Theme_Ledger)

        Thread.sleep(1500)

        onView(withId(R.id.layoutEmpty)).check(matches(isDisplayed()))
    }

    @Test
    fun scroll_to_bottom_triggers_load_more() {
        val page1 = "[" + (1..20).joinToString(",") { i ->
            """{"id":$i,"transaction_date":"2026-01-01","description":"Txn $i","transaction_type":"EXPENSE","status":"CONFIRMED","is_void":false,"lines":[]}"""
        } + "]"
        val page2 = "[" + (21..30).joinToString(",") { i ->
            """{"id":$i,"transaction_date":"2026-01-01","description":"Txn $i","transaction_type":"EXPENSE","status":"CONFIRMED","is_void":false,"lines":[]}"""
        } + "]"

        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(page1))
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody("""{"count":30}"""))
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(page2))

        launchFragmentInContainer<TransactionsFragment>(themeResId = R.style.Theme_Ledger)

        Thread.sleep(1500)

        // Scroll to bottom to trigger load more
        onView(withId(R.id.rvTransactions)).perform(
            androidx.test.espresso.contrib.RecyclerViewActions.scrollToPosition<androidx.recyclerview.widget.RecyclerView.ViewHolder>(19)
        )

        Thread.sleep(1500)

        // Should now have 30 items
        onView(withText("Txn 30")).check(matches(isDisplayed()))
    }
}
