package com.ledger.app.ui.budgets

import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ledger.app.data.api.LedgerApiService
import com.ledger.app.data.models.BudgetCreate
import com.ledger.app.data.models.BudgetOut
import com.ledger.app.util.UiState
import kotlinx.coroutines.launch
import java.io.IOException

class BudgetsViewModel(private val api: LedgerApiService) : ViewModel() {

    val budgetsState = MutableLiveData<UiState<List<BudgetOut>>>()
    val createState = MutableLiveData<UiState<BudgetOut>>()
    val deleteState = MutableLiveData<UiState<Unit>>()

    private var _budgets: List<BudgetOut> = emptyList()

    val isEmpty: Boolean
        get() = _budgets.isEmpty()

    val activeBudgetCount: Int
        get() = _budgets.count { it.is_active }

    val totalPlannedAmount: Double
        get() = _budgets.flatMap { it.items }.sumOf { it.planned_amount.toDoubleOrNull() ?: 0.0 }

    val totalLineItems: Int
        get() = _budgets.sumOf { it.items.size }

    fun loadBudgets() {
        budgetsState.value = UiState.Loading
        viewModelScope.launch {
            try {
                val response = api.getBudgets()
                if (response.isSuccessful) {
                    _budgets = response.body()!!
                    budgetsState.value = UiState.Success(_budgets)
                } else {
                    budgetsState.value = UiState.Error("Failed to load budgets: ${response.code()}")
                }
            } catch (e: IOException) {
                budgetsState.value = UiState.Error("Network error. Please check your connection.")
            } catch (e: Exception) {
                budgetsState.value = UiState.Error("Error: ${e.message}")
            }
        }
    }

    fun createBudget(request: BudgetCreate) {
        createState.value = UiState.Loading
        viewModelScope.launch {
            try {
                val response = api.createBudget(request)
                if (response.isSuccessful) {
                    createState.value = UiState.Success(response.body()!!)
                    loadBudgets()
                } else {
                    val errorMsg = response.errorBody()?.string() ?: "Failed to create budget"
                    createState.value = UiState.Error(errorMsg)
                }
            } catch (e: IOException) {
                createState.value = UiState.Error("Network error. Please check your connection.")
            } catch (e: Exception) {
                createState.value = UiState.Error("Error: ${e.message}")
            }
        }
    }

    fun deleteBudget(id: Int) {
        deleteState.value = UiState.Loading
        viewModelScope.launch {
            try {
                val response = api.deleteBudget(id)
                if (response.isSuccessful || response.code() == 204) {
                    deleteState.value = UiState.Success(Unit)
                    loadBudgets()
                } else {
                    deleteState.value = UiState.Error("Failed to delete budget: ${response.code()}")
                }
            } catch (e: IOException) {
                deleteState.value = UiState.Error("Network error. Please check your connection.")
            } catch (e: Exception) {
                deleteState.value = UiState.Error("Error: ${e.message}")
            }
        }
    }
}
