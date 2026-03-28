package com.ledger.app.ui

import androidx.navigation.testing.TestNavHostController
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.ledger.app.R
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class NavigationTest {

    @Test
    fun bottom_nav_graph_has_correct_destinations() {
        val navController = TestNavHostController(ApplicationProvider.getApplicationContext())
        navController.setGraph(R.navigation.nav_graph)

        // Verify start destination
        assertEquals(R.id.dashboardFragment, navController.currentDestination?.id)
    }

    @Test
    fun navigate_to_transactions_works() {
        val navController = TestNavHostController(ApplicationProvider.getApplicationContext())
        navController.setGraph(R.navigation.nav_graph)

        navController.navigate(R.id.transactionsFragment)
        assertEquals(R.id.transactionsFragment, navController.currentDestination?.id)
    }

    @Test
    fun navigate_to_reports_works() {
        val navController = TestNavHostController(ApplicationProvider.getApplicationContext())
        navController.setGraph(R.navigation.nav_graph)

        navController.navigate(R.id.reportsFragment)
        assertEquals(R.id.reportsFragment, navController.currentDestination?.id)
    }

    @Test
    fun navigate_to_goals_works() {
        val navController = TestNavHostController(ApplicationProvider.getApplicationContext())
        navController.setGraph(R.navigation.nav_graph)

        navController.navigate(R.id.goalsFragment)
        assertEquals(R.id.goalsFragment, navController.currentDestination?.id)
    }

    @Test
    fun navigate_more_to_budgets_works() {
        val navController = TestNavHostController(ApplicationProvider.getApplicationContext())
        navController.setGraph(R.navigation.nav_graph)

        navController.navigate(R.id.moreFragment)
        navController.navigate(R.id.action_more_to_budgets)
        assertEquals(R.id.budgetsFragment, navController.currentDestination?.id)
    }

    @Test
    fun navigate_more_to_settings_works() {
        val navController = TestNavHostController(ApplicationProvider.getApplicationContext())
        navController.setGraph(R.navigation.nav_graph)

        navController.navigate(R.id.moreFragment)
        navController.navigate(R.id.action_more_to_settings)
        assertEquals(R.id.settingsFragment, navController.currentDestination?.id)
    }
}
