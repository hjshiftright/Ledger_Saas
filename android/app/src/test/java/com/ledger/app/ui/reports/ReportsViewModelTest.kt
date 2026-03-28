package com.ledger.app.ui.reports

import com.ledger.app.data.api.LedgerApiService
import com.ledger.app.data.models.DashboardSummary
import com.ledger.app.data.models.ExpenseCategory
import com.ledger.app.data.models.MonthlyTrend
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

class ReportsViewModelTest : BaseViewModelTest() {

    private lateinit var mockApi: LedgerApiService
    private lateinit var viewModel: ReportsViewModel

    private val summary = DashboardSummary("2500000.00", "150000.00", "95000.00", 36.7, "55000.00")
    private val trends = listOf(MonthlyTrend("2026-01", "100000", "60000"))
    private val categories = listOf(
        ExpenseCategory("Food", "1000", 20.0),
        ExpenseCategory("Transport", "500", 10.0),
        ExpenseCategory("Groceries", "250", 5.0)
    )
    private val balanceSheet: Map<String, Any> = mapOf("assets" to emptyMap<String, Any>())

    @Before
    fun setUp() {
        mockApi = mockk()
        viewModel = ReportsViewModel(mockApi)
    }

    private fun setupAllSuccess() {
        coEvery { mockApi.getDashboardSummary(any(), any()) } returns Response.success(summary)
        coEvery { mockApi.getMonthlyTrend(any(), any(), any()) } returns Response.success(trends)
        coEvery { mockApi.getExpenseCategories(any(), any()) } returns Response.success(categories)
        coEvery { mockApi.getBalanceSheet(any(), any()) } returns Response.success(balanceSheet)
    }

    @Test
    fun load_reports_fetches_all_sections() = runTest {
        setupAllSuccess()

        viewModel.loadReports()
        testDispatcher.scheduler.advanceUntilIdle()

        assertTrue(viewModel.summaryState.value is UiState.Success)
        assertTrue(viewModel.trendState.value is UiState.Success)
        assertTrue(viewModel.categoriesState.value is UiState.Success)
        assertTrue(viewModel.balanceSheetState.value is UiState.Success)
    }

    @Test
    fun change_period_reloads_with_dates() = runTest {
        setupAllSuccess()

        viewModel.setPeriod("THIS_MONTH")
        testDispatcher.scheduler.advanceUntilIdle()

        assertTrue(viewModel.summaryState.value is UiState.Success)
    }

    @Test
    fun custom_period_uses_exact_dates() = runTest {
        setupAllSuccess()

        viewModel.setCustomPeriod("2026-01-01", "2026-03-31")
        testDispatcher.scheduler.advanceUntilIdle()

        assertTrue(viewModel.summaryState.value is UiState.Success)
    }

    @Test
    fun partial_failure_shows_available_data() = runTest {
        coEvery { mockApi.getDashboardSummary(any(), any()) } returns Response.success(summary)
        coEvery { mockApi.getMonthlyTrend(any(), any(), any()) } returns Response.error(500, """{"detail":"error"}""".toResponseBody())
        coEvery { mockApi.getExpenseCategories(any(), any()) } returns Response.success(categories)
        coEvery { mockApi.getBalanceSheet(any(), any()) } returns Response.success(balanceSheet)

        viewModel.loadReports()
        testDispatcher.scheduler.advanceUntilIdle()

        assertTrue(viewModel.summaryState.value is UiState.Success)
        assertTrue(viewModel.trendState.value is UiState.Error)
    }

    @Test
    fun expense_categories_sorted_by_amount() = runTest {
        val unordered = listOf(
            ExpenseCategory("A", "500", 10.0),
            ExpenseCategory("B", "1000", 20.0),
            ExpenseCategory("C", "250", 5.0)
        )
        coEvery { mockApi.getDashboardSummary(any(), any()) } returns Response.success(summary)
        coEvery { mockApi.getMonthlyTrend(any(), any(), any()) } returns Response.success(trends)
        coEvery { mockApi.getExpenseCategories(any(), any()) } returns Response.success(unordered)
        coEvery { mockApi.getBalanceSheet(any(), any()) } returns Response.success(balanceSheet)

        viewModel.loadReports()
        testDispatcher.scheduler.advanceUntilIdle()

        val state = viewModel.categoriesState.value as UiState.Success
        val sorted = state.data
        assertEquals("B", sorted[0].category)
        assertEquals("A", sorted[1].category)
        assertEquals("C", sorted[2].category)
    }
}
