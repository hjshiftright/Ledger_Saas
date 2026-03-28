package com.ledger.app.ui.reports

import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ledger.app.data.api.LedgerApiService
import com.ledger.app.data.models.DashboardSummary
import com.ledger.app.data.models.ExpenseCategory
import com.ledger.app.data.models.MonthlyTrend
import com.ledger.app.util.UiState
import kotlinx.coroutines.launch
import java.io.IOException
import java.time.LocalDate
import java.time.format.DateTimeFormatter

class ReportsViewModel(private val api: LedgerApiService) : ViewModel() {

    val summaryState = MutableLiveData<UiState<DashboardSummary>>()
    val trendState = MutableLiveData<UiState<List<MonthlyTrend>>>()
    val categoriesState = MutableLiveData<UiState<List<ExpenseCategory>>>()
    val balanceSheetState = MutableLiveData<UiState<Map<String, Any>>>()

    private var currentFromDate: String? = null
    private var currentToDate: String? = null

    fun loadReports() {
        viewModelScope.launch {
            launch { loadSummary() }
            launch { loadTrend() }
            launch { loadCategories() }
            launch { loadBalanceSheet() }
        }
    }

    fun setPeriod(period: String) {
        val (fromDate, toDate) = calculateDateRange(period)
        currentFromDate = fromDate
        currentToDate = toDate
        loadReports()
    }

    fun setCustomPeriod(fromDate: String, toDate: String) {
        currentFromDate = fromDate
        currentToDate = toDate
        loadReports()
    }

    private fun calculateDateRange(period: String): Pair<String, String> {
        val today = LocalDate.now()
        val fmt = DateTimeFormatter.ofPattern("yyyy-MM-dd")
        return when (period) {
            "THIS_MONTH" -> {
                val start = today.withDayOfMonth(1)
                val end = today.withDayOfMonth(today.lengthOfMonth())
                Pair(start.format(fmt), end.format(fmt))
            }
            "LAST_MONTH" -> {
                val lastMonth = today.minusMonths(1)
                val start = lastMonth.withDayOfMonth(1)
                val end = lastMonth.withDayOfMonth(lastMonth.lengthOfMonth())
                Pair(start.format(fmt), end.format(fmt))
            }
            "THIS_QUARTER" -> {
                val quarterMonth = ((today.monthValue - 1) / 3) * 3 + 1
                val start = LocalDate.of(today.year, quarterMonth, 1)
                val end = start.plusMonths(2).withDayOfMonth(
                    start.plusMonths(2).lengthOfMonth()
                )
                Pair(start.format(fmt), end.format(fmt))
            }
            "THIS_YEAR" -> {
                val start = LocalDate.of(today.year, 1, 1)
                val end = LocalDate.of(today.year, 12, 31)
                Pair(start.format(fmt), end.format(fmt))
            }
            else -> Pair(
                today.withDayOfMonth(1).format(fmt),
                today.withDayOfMonth(today.lengthOfMonth()).format(fmt)
            )
        }
    }

    private suspend fun loadSummary() {
        try {
            val response = api.getDashboardSummary(currentFromDate, currentToDate)
            summaryState.postValue(
                if (response.isSuccessful) UiState.Success(response.body()!!)
                else UiState.Error("Failed to load summary: ${response.code()}")
            )
        } catch (e: IOException) {
            summaryState.postValue(UiState.Error("Network error. Please check your connection."))
        } catch (e: Exception) {
            summaryState.postValue(UiState.Error("Error: ${e.message}"))
        }
    }

    private suspend fun loadTrend() {
        try {
            val response = api.getMonthlyTrend(currentFromDate, currentToDate)
            trendState.postValue(
                if (response.isSuccessful) UiState.Success(response.body()!!)
                else UiState.Error("Failed to load trend: ${response.code()}")
            )
        } catch (e: IOException) {
            trendState.postValue(UiState.Error("Network error. Please check your connection."))
        } catch (e: Exception) {
            trendState.postValue(UiState.Error("Error: ${e.message}"))
        }
    }

    private suspend fun loadCategories() {
        try {
            val response = api.getExpenseCategories(currentFromDate, currentToDate)
            if (response.isSuccessful) {
                val sorted = response.body()!!
                    .sortedByDescending { it.amount.toDoubleOrNull() ?: 0.0 }
                categoriesState.postValue(UiState.Success(sorted))
            } else {
                categoriesState.postValue(UiState.Error("Failed to load categories: ${response.code()}"))
            }
        } catch (e: IOException) {
            categoriesState.postValue(UiState.Error("Network error. Please check your connection."))
        } catch (e: Exception) {
            categoriesState.postValue(UiState.Error("Error: ${e.message}"))
        }
    }

    private suspend fun loadBalanceSheet() {
        try {
            val response = api.getBalanceSheet(currentFromDate, currentToDate)
            balanceSheetState.postValue(
                if (response.isSuccessful) UiState.Success(response.body()!!)
                else UiState.Error("Failed to load balance sheet: ${response.code()}")
            )
        } catch (e: IOException) {
            balanceSheetState.postValue(UiState.Error("Network error. Please check your connection."))
        } catch (e: Exception) {
            balanceSheetState.postValue(UiState.Error("Error: ${e.message}"))
        }
    }
}
