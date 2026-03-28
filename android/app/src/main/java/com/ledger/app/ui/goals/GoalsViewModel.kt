package com.ledger.app.ui.goals

import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ledger.app.data.api.LedgerApiService
import com.ledger.app.data.models.GoalCreate
import com.ledger.app.data.models.GoalOut
import com.ledger.app.util.UiState
import kotlinx.coroutines.launch
import java.io.IOException

class GoalsViewModel(private val api: LedgerApiService) : ViewModel() {

    val goalsState = MutableLiveData<UiState<List<GoalOut>>>()
    val createState = MutableLiveData<UiState<GoalOut>>()
    val deleteState = MutableLiveData<UiState<Unit>>()
    val updateState = MutableLiveData<UiState<GoalOut>>()

    private var _goals: List<GoalOut> = emptyList()

    val isEmpty: Boolean
        get() = _goals.isEmpty()

    val totalTargetAmount: Double
        get() = _goals.sumOf { it.target_amount.toDoubleOrNull() ?: 0.0 }

    val averageProgress: Double
        get() = if (_goals.isEmpty()) 0.0 else _goals.map { it.progress_pct }.average()

    fun loadGoals() {
        goalsState.value = UiState.Loading
        viewModelScope.launch {
            try {
                val response = api.getGoals()
                if (response.isSuccessful) {
                    _goals = response.body()!!
                    goalsState.value = UiState.Success(_goals)
                } else {
                    goalsState.value = UiState.Error("Failed to load goals: ${response.code()}")
                }
            } catch (e: IOException) {
                goalsState.value = UiState.Error("Network error. Please check your connection.")
            } catch (e: Exception) {
                goalsState.value = UiState.Error("Error: ${e.message}")
            }
        }
    }

    fun createGoal(request: GoalCreate) {
        createState.value = UiState.Loading
        viewModelScope.launch {
            try {
                val response = api.createGoal(request)
                if (response.isSuccessful) {
                    createState.value = UiState.Success(response.body()!!)
                    loadGoals()
                } else {
                    val errorMsg = parseErrorBody(response.errorBody()?.string())
                    createState.value = UiState.Error(errorMsg)
                }
            } catch (e: IOException) {
                createState.value = UiState.Error("Network error. Please check your connection.")
            } catch (e: Exception) {
                createState.value = UiState.Error("Error: ${e.message}")
            }
        }
    }

    fun deleteGoal(id: Int) {
        deleteState.value = UiState.Loading
        viewModelScope.launch {
            try {
                val response = api.deleteGoal(id)
                if (response.isSuccessful || response.code() == 204) {
                    deleteState.value = UiState.Success(Unit)
                    loadGoals()
                } else {
                    deleteState.value = UiState.Error("Failed to delete goal: ${response.code()}")
                }
            } catch (e: IOException) {
                deleteState.value = UiState.Error("Network error. Please check your connection.")
            } catch (e: Exception) {
                deleteState.value = UiState.Error("Error: ${e.message}")
            }
        }
    }

    fun updateGoal(id: Int, updates: Map<String, String>) {
        updateState.value = UiState.Loading
        viewModelScope.launch {
            try {
                val response = api.updateGoal(id, updates)
                if (response.isSuccessful) {
                    updateState.value = UiState.Success(response.body()!!)
                    loadGoals()
                } else {
                    updateState.value = UiState.Error("Failed to update goal: ${response.code()}")
                }
            } catch (e: IOException) {
                updateState.value = UiState.Error("Network error. Please check your connection.")
            } catch (e: Exception) {
                updateState.value = UiState.Error("Error: ${e.message}")
            }
        }
    }

    private fun parseErrorBody(errorBody: String?): String {
        if (errorBody == null) return "An error occurred."
        return try {
            val detail = errorBody.substringAfter("\"detail\":\"", "")
                .substringBefore("\"")
            if (detail.isNotEmpty()) detail else errorBody
        } catch (e: Exception) {
            errorBody
        }
    }
}
