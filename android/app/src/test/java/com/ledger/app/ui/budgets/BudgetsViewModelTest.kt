package com.ledger.app.ui.budgets

import com.ledger.app.data.api.LedgerApiService
import com.ledger.app.data.models.BudgetCreate
import com.ledger.app.data.models.BudgetItemCreate
import com.ledger.app.data.models.BudgetItemOut
import com.ledger.app.data.models.BudgetOut
import com.ledger.app.ui.BaseViewModelTest
import com.ledger.app.util.UiState
import io.mockk.coEvery
import io.mockk.mockk
import kotlinx.coroutines.test.runTest
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import retrofit2.Response

class BudgetsViewModelTest : BaseViewModelTest() {

    private lateinit var mockApi: LedgerApiService
    private lateinit var viewModel: BudgetsViewModel

    private fun makeItem(id: Int, amount: String) = BudgetItemOut(id, id, "5$id00", "Category $id", amount, null)

    private fun makeBudget(id: Int, name: String, items: List<BudgetItemOut>) =
        BudgetOut(id, name, "MONTHLY", "2026-01-01", null, true, items)

    @Before
    fun setUp() {
        mockApi = mockk()
        viewModel = BudgetsViewModel(mockApi)
    }

    @Test
    fun load_budgets_success() = runTest {
        val budgets = listOf(makeBudget(1, "B1", emptyList()), makeBudget(2, "B2", emptyList()))
        coEvery { mockApi.getBudgets() } returns Response.success(budgets)

        viewModel.loadBudgets()
        testDispatcher.scheduler.advanceUntilIdle()

        val state = viewModel.budgetsState.value
        assertTrue(state is UiState.Success)
        assertEquals(2, (state as UiState.Success).data.size)
    }

    @Test
    fun load_budgets_empty() = runTest {
        coEvery { mockApi.getBudgets() } returns Response.success(emptyList())

        viewModel.loadBudgets()
        testDispatcher.scheduler.advanceUntilIdle()

        assertTrue(viewModel.budgetsState.value is UiState.Success)
        assertTrue(viewModel.isEmpty)
    }

    @Test
    fun create_budget_success() = runTest {
        val newBudget = makeBudget(1, "Test", emptyList())
        coEvery { mockApi.createBudget(any()) } returns Response.success(newBudget)
        coEvery { mockApi.getBudgets() } returns Response.success(listOf(newBudget))

        viewModel.createBudget(BudgetCreate("Test", "MONTHLY", "2026-01-01", items = listOf(BudgetItemCreate("5100", "10000"))))
        testDispatcher.scheduler.advanceUntilIdle()

        assertTrue(viewModel.createState.value is UiState.Success)
    }

    @Test
    fun delete_budget_success() = runTest {
        coEvery { mockApi.deleteBudget(3) } returns Response.success(Unit)
        coEvery { mockApi.getBudgets() } returns Response.success(emptyList())

        viewModel.deleteBudget(3)
        testDispatcher.scheduler.advanceUntilIdle()

        assertTrue(viewModel.deleteState.value is UiState.Success)
    }

    @Test
    fun computed_summary_values() = runTest {
        val budgets = listOf(
            makeBudget(1, "B1", listOf(makeItem(1, "10000"), makeItem(2, "20000"), makeItem(3, "5000"))),
            makeBudget(2, "B2", listOf(makeItem(4, "15000"), makeItem(5, "8000")))
        )
        coEvery { mockApi.getBudgets() } returns Response.success(budgets)

        viewModel.loadBudgets()
        testDispatcher.scheduler.advanceUntilIdle()

        assertEquals(2, viewModel.activeBudgetCount)
        assertEquals(58_000.0, viewModel.totalPlannedAmount, 0.01)
        assertEquals(5, viewModel.totalLineItems)
    }
}
