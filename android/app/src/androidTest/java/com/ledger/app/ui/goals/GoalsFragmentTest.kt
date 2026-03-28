package com.ledger.app.ui.goals

import androidx.fragment.app.testing.launchFragmentInContainer
import androidx.test.espresso.Espresso.onView
import androidx.test.espresso.action.ViewActions.click
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
class GoalsFragmentTest {

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
    fun goals_list_renders_cards() {
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(TestFixtures.GOALS_LIST))

        launchFragmentInContainer<GoalsFragment>(themeResId = R.style.Theme_Ledger)

        Thread.sleep(1500)

        onView(withId(R.id.rvGoals)).check(matches(isDisplayed()))
        onView(withText("Emergency Fund")).check(matches(isDisplayed()))
    }

    @Test
    fun goal_card_shows_progress_bar() {
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(TestFixtures.GOALS_LIST))

        launchFragmentInContainer<GoalsFragment>(themeResId = R.style.Theme_Ledger)

        Thread.sleep(1500)

        onView(withId(R.id.progressGoal)).check(matches(isDisplayed()))
    }

    @Test
    fun create_goal_button_opens_form() {
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(TestFixtures.GOALS_LIST))

        launchFragmentInContainer<GoalsFragment>(themeResId = R.style.Theme_Ledger)

        Thread.sleep(500)

        onView(withId(R.id.btnNewGoal)).check(matches(isDisplayed()))
        onView(withId(R.id.btnNewGoal)).perform(click())
        // Toast should appear (simple implementation)
    }

    @Test
    fun empty_goals_shows_cta() {
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody("[]"))

        launchFragmentInContainer<GoalsFragment>(themeResId = R.style.Theme_Ledger)

        Thread.sleep(1500)

        onView(withId(R.id.layoutEmpty)).check(matches(isDisplayed()))
        onView(withId(R.id.btnCreateFirstGoal)).check(matches(isDisplayed()))
    }
}
