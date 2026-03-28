package com.ledger.app.ui.dashboard

import com.ledger.app.data.api.LedgerApiService
import com.ledger.app.data.models.DashboardSummary
import com.ledger.app.data.models.GoalOut
import com.ledger.app.data.models.TransactionOut
import com.ledger.app.ui.BaseViewModelTest
import com.ledger.app.util.UiState
import io.mockk.coEvery
import io.mockk.mockk
import kotlinx.coroutines.test.runTest
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import retrofit2.Response

class DashboardViewModelTest : BaseViewModelTest() {

    private lateinit var mockApi: LedgerApiService
    private lateinit var viewModel: DashboardViewModel

    private val summary = DashboardSummary("2500000.00", "150000.00", "95000.00", 36.7, "55000.00")
    private val goals = listOf(
        GoalOut(1, "Emergency Fund", "EMERGENCY_FUND", "500000", "250000", progress_pct = 50.0)
    )
    private val transactions = listOf(
        TransactionOut(1, "2026-01-15", "Salary", "BANK_TRANSFER", "CONFIRMED")
    )

    @Before
    fun setUp() {
        mockApi = mockk()
        viewModel = DashboardViewModel(mockApi)
    }

    @Test
    fun load_dashboard_sets_loading_then_success() = runTest {
        coEvery { mockApi.getDashboardSummary(any(), any()) } returns Response.success(summary)
        coEvery { mockApi.getGoals() } returns Response.success(goals)
        coEvery { mockApi.getTransactions(any(), any(), any(), any()) } returns Response.success(transactions)

        viewModel.loadDashboard()
        testDispatcher.scheduler.advanceUntilIdle()

        assertTrue(viewModel.summaryState.value is UiState.Success)
        assertTrue(viewModel.goalsState.value is UiState.Success)
        assertTrue(viewModel.transactionsState.value is UiState.Success)
    }

    @Test
    fun dashboard_summary_maps_net_worth() = runTest {
        coEvery { mockApi.getDashboardSummary(any(), any()) } returns Response.success(summary)
        coEvery { mockApi.getGoals() } returns Response.success(emptyList())
        coEvery { mockApi.getTransactions(any(), any(), any(), any()) } returns Response.success(emptyList())

        viewModel.loadDashboard()
        testDispatcher.scheduler.advanceUntilIdle()

        val state = viewModel.summaryState.value
        assertTrue(state is UiState.Success)
        assertEquals("2500000.00", (state as UiState.Success).data.net_worth)
    }

    @Test
    fun dashboard_handles_partial_failure() = runTest {
        coEvery { mockApi.getDashboardSummary(any(), any()) } returns Response.success(summary)
        coEvery { mockApi.getGoals() } returns Response.error(500, """{"detail":"error"}""".toResponseBody())
        coEvery { mockApi.getTransactions(any(), any(), any(), any()) } returns Response.success(transactions)

        viewModel.loadDashboard()
        testDispatcher.scheduler.advanceUntilIdle()

        assertTrue(viewModel.summaryState.value is UiState.Success)
        assertTrue(viewModel.goalsState.value is UiState.Error)
    }

    @Test
    fun dashboard_handles_total_failure() = runTest {
        coEvery { mockApi.getDashboardSummary(any(), any()) } throws java.io.IOException("no network")
        coEvery { mockApi.getGoals() } throws java.io.IOException("no network")
        coEvery { mockApi.getTransactions(any(), any(), any(), any()) } throws java.io.IOException("no network")

        viewModel.loadDashboard()
        testDispatcher.scheduler.advanceUntilIdle()

        assertTrue(viewModel.summaryState.value is UiState.Error)
        assertTrue(viewModel.goalsState.value is UiState.Error)
        assertTrue(viewModel.transactionsState.value is UiState.Error)
    }

    @Test
    fun refresh_reloads_all_data() = runTest {
        coEvery { mockApi.getDashboardSummary(any(), any()) } returns Response.success(summary)
        coEvery { mockApi.getGoals() } returns Response.success(goals)
        coEvery { mockApi.getTransactions(any(), any(), any(), any()) } returns Response.success(transactions)

        viewModel.loadDashboard()
        testDispatcher.scheduler.advanceUntilIdle()
        viewModel.refresh()
        testDispatcher.scheduler.advanceUntilIdle()

        assertTrue(viewModel.summaryState.value is UiState.Success)
    }
}
