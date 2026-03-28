package com.ledger.app.ui.dashboard

import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ledger.app.data.api.LedgerApiService
import com.ledger.app.data.models.DashboardSummary
import com.ledger.app.data.models.GoalOut
import com.ledger.app.data.models.TransactionOut
import com.ledger.app.util.UiState
import kotlinx.coroutines.launch
import java.io.IOException

class DashboardViewModel(private val api: LedgerApiService) : ViewModel() {

    val summaryState = MutableLiveData<UiState<DashboardSummary>>()
    val goalsState = MutableLiveData<UiState<List<GoalOut>>>()
    val transactionsState = MutableLiveData<UiState<List<TransactionOut>>>()

    fun loadDashboard() {
        summaryState.value = UiState.Loading
        goalsState.value = UiState.Loading
        transactionsState.value = UiState.Loading

        viewModelScope.launch {
            launch { loadSummary() }
            launch { loadGoals() }
            launch { loadRecentTransactions() }
        }
    }

    private suspend fun loadSummary() {
        try {
            val response = api.getDashboardSummary()
            summaryState.postValue(
                if (response.isSuccessful) UiState.Success(response.body()!!)
                else UiState.Error("Failed to load summary: ${response.code()}")
            )
        } catch (e: IOException) {
            summaryState.postValue(UiState.Error("Network error. Please check your connection."))
        } catch (e: Exception) {
            summaryState.postValue(UiState.Error("Error loading summary: ${e.message}"))
        }
    }

    private suspend fun loadGoals() {
        try {
            val response = api.getGoals()
            goalsState.postValue(
                if (response.isSuccessful) UiState.Success(response.body()!!)
                else UiState.Error("Failed to load goals: ${response.code()}")
            )
        } catch (e: IOException) {
            goalsState.postValue(UiState.Error("Network error. Please check your connection."))
        } catch (e: Exception) {
            goalsState.postValue(UiState.Error("Error loading goals: ${e.message}"))
        }
    }

    private suspend fun loadRecentTransactions() {
        try {
            val response = api.getTransactions(limit = 10)
            transactionsState.postValue(
                if (response.isSuccessful) UiState.Success(response.body()!!)
                else UiState.Error("Failed to load transactions: ${response.code()}")
            )
        } catch (e: IOException) {
            transactionsState.postValue(UiState.Error("Network error. Please check your connection."))
        } catch (e: Exception) {
            transactionsState.postValue(UiState.Error("Error loading transactions: ${e.message}"))
        }
    }

    fun refresh() {
        loadDashboard()
    }
}
