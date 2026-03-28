package com.ledger.app.ui.transactions

import com.ledger.app.data.api.LedgerApiService
import com.ledger.app.data.models.TransactionCountResponse
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

class TransactionsViewModelTest : BaseViewModelTest() {

    private lateinit var mockApi: LedgerApiService
    private lateinit var viewModel: TransactionsViewModel

    private fun makeTxns(count: Int) = (1..count).map { i ->
        TransactionOut(i, "2026-01-${i.toString().padStart(2,'0')}", "Txn $i", "EXPENSE", "CONFIRMED")
    }

    @Before
    fun setUp() {
        mockApi = mockk()
        viewModel = TransactionsViewModel(mockApi)
    }

    @Test
    fun load_transactions_first_page() = runTest {
        coEvery { mockApi.getTransactions(any(), any(), any(), any()) } returns Response.success(makeTxns(20))
        coEvery { mockApi.getTransactionCount() } returns Response.success(TransactionCountResponse(150))

        viewModel.loadTransactions()
        testDispatcher.scheduler.advanceUntilIdle()

        val state = viewModel.transactionState.value
        assertTrue(state is UiState.Success)
        assertEquals(20, (state as UiState.Success).data.size)
        assertEquals(20, viewModel.currentOffset)
    }

    @Test
    fun load_more_appends_to_list() = runTest {
        coEvery { mockApi.getTransactions(any(), eq(0), any(), any()) } returns Response.success(makeTxns(20))
        coEvery { mockApi.getTransactions(any(), eq(20), any(), any()) } returns Response.success(makeTxns(20))
        coEvery { mockApi.getTransactionCount() } returns Response.success(TransactionCountResponse(150))

        viewModel.loadTransactions()
        testDispatcher.scheduler.advanceUntilIdle()
        viewModel.loadMore()
        testDispatcher.scheduler.advanceUntilIdle()

        val state = viewModel.transactionState.value
        assertTrue(state is UiState.Success)
        assertEquals(40, (state as UiState.Success).data.size)
    }

    @Test
    fun load_more_with_no_results_sets_end_reached() = runTest {
        coEvery { mockApi.getTransactions(any(), eq(0), any(), any()) } returns Response.success(makeTxns(20))
        coEvery { mockApi.getTransactions(any(), eq(20), any(), any()) } returns Response.success(emptyList())
        coEvery { mockApi.getTransactionCount() } returns Response.success(TransactionCountResponse(20))

        viewModel.loadTransactions()
        testDispatcher.scheduler.advanceUntilIdle()
        viewModel.loadMore()
        testDispatcher.scheduler.advanceUntilIdle()

        assertFalse(viewModel.hasMorePages)
    }

    @Test
    fun filter_by_date_resets_and_reloads() = runTest {
        coEvery { mockApi.getTransactions(any(), any(), any(), any()) } returns Response.success(makeTxns(5))
        coEvery { mockApi.getTransactionCount() } returns Response.success(TransactionCountResponse(5))

        viewModel.filterByDate("2026-01-01", "2026-03-31")
        testDispatcher.scheduler.advanceUntilIdle()

        assertEquals(5, viewModel.currentOffset)
        assertTrue(viewModel.transactionState.value is UiState.Success)
    }

    @Test
    fun load_transactions_failure() = runTest {
        coEvery { mockApi.getTransactions(any(), any(), any(), any()) } returns Response.error(500, """{"detail":"error"}""".toResponseBody())
        coEvery { mockApi.getTransactionCount() } returns Response.success(TransactionCountResponse(0))

        viewModel.loadTransactions()
        testDispatcher.scheduler.advanceUntilIdle()

        assertTrue(viewModel.transactionState.value is UiState.Error)
    }

    @Test
    fun transaction_count_loaded() = runTest {
        coEvery { mockApi.getTransactions(any(), any(), any(), any()) } returns Response.success(makeTxns(20))
        coEvery { mockApi.getTransactionCount() } returns Response.success(TransactionCountResponse(150))

        viewModel.loadTransactions()
        testDispatcher.scheduler.advanceUntilIdle()

        assertEquals(150, viewModel.totalCount)
    }
}
