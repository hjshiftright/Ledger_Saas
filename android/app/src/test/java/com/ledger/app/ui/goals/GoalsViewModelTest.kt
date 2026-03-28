package com.ledger.app.ui.goals

import com.ledger.app.data.api.LedgerApiService
import com.ledger.app.data.models.GoalCreate
import com.ledger.app.data.models.GoalOut
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

class GoalsViewModelTest : BaseViewModelTest() {

    private lateinit var mockApi: LedgerApiService
    private lateinit var viewModel: GoalsViewModel

    private fun makeGoal(id: Int, name: String, target: String, progress: Double) =
        GoalOut(id, name, "EMERGENCY_FUND", target, "0", progress_pct = progress)

    @Before
    fun setUp() {
        mockApi = mockk()
        viewModel = GoalsViewModel(mockApi)
    }

    @Test
    fun load_goals_success() = runTest {
        val goals = listOf(makeGoal(1, "A", "100000", 50.0), makeGoal(2, "B", "200000", 25.0), makeGoal(3, "C", "300000", 75.0))
        coEvery { mockApi.getGoals() } returns Response.success(goals)

        viewModel.loadGoals()
        testDispatcher.scheduler.advanceUntilIdle()

        val state = viewModel.goalsState.value
        assertTrue(state is UiState.Success)
        assertEquals(3, (state as UiState.Success).data.size)
    }

    @Test
    fun load_goals_empty() = runTest {
        coEvery { mockApi.getGoals() } returns Response.success(emptyList())

        viewModel.loadGoals()
        testDispatcher.scheduler.advanceUntilIdle()

        assertTrue(viewModel.goalsState.value is UiState.Success)
        assertTrue(viewModel.isEmpty)
    }

    @Test
    fun create_goal_success() = runTest {
        val newGoal = makeGoal(1, "Trip", "100000", 0.0)
        coEvery { mockApi.createGoal(any()) } returns Response.success(newGoal)
        coEvery { mockApi.getGoals() } returns Response.success(listOf(newGoal))

        viewModel.createGoal(GoalCreate("Trip", "HOLIDAY", "100000"))
        testDispatcher.scheduler.advanceUntilIdle()

        assertTrue(viewModel.createState.value is UiState.Success)
    }

    @Test
    fun create_goal_validation_error() = runTest {
        coEvery { mockApi.createGoal(any()) } returns Response.error(400, """{"detail":"name is required"}""".toResponseBody())

        viewModel.createGoal(GoalCreate("", "HOLIDAY", "100000"))
        testDispatcher.scheduler.advanceUntilIdle()

        assertTrue(viewModel.createState.value is UiState.Error)
    }

    @Test
    fun delete_goal_success() = runTest {
        coEvery { mockApi.deleteGoal(5) } returns Response.success(Unit)
        coEvery { mockApi.getGoals() } returns Response.success(emptyList())

        viewModel.deleteGoal(5)
        testDispatcher.scheduler.advanceUntilIdle()

        assertTrue(viewModel.deleteState.value is UiState.Success)
    }

    @Test
    fun delete_goal_failure() = runTest {
        coEvery { mockApi.deleteGoal(999) } returns Response.error(404, """{"detail":"not found"}""".toResponseBody())

        viewModel.deleteGoal(999)
        testDispatcher.scheduler.advanceUntilIdle()

        assertTrue(viewModel.deleteState.value is UiState.Error)
    }

    @Test
    fun update_goal_success() = runTest {
        val updatedGoal = makeGoal(1, "Fund", "500000", 40.0)
        coEvery { mockApi.updateGoal(1, any()) } returns Response.success(updatedGoal)
        coEvery { mockApi.getGoals() } returns Response.success(listOf(updatedGoal))

        viewModel.updateGoal(1, mapOf("current_amount" to "200000"))
        testDispatcher.scheduler.advanceUntilIdle()

        assertTrue(viewModel.updateState.value is UiState.Success)
    }

    @Test
    fun computed_summary_values() = runTest {
        val goals = listOf(
            makeGoal(1, "A", "500000", 50.0),
            makeGoal(2, "B", "300000", 75.0),
            makeGoal(3, "C", "200000", 25.0)
        )
        coEvery { mockApi.getGoals() } returns Response.success(goals)

        viewModel.loadGoals()
        testDispatcher.scheduler.advanceUntilIdle()

        assertEquals(1_000_000.0, viewModel.totalTargetAmount, 0.01)
        assertEquals(50.0, viewModel.averageProgress, 0.01)
    }
}
