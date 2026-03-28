package com.ledger.app.ui.transactions

import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ledger.app.data.api.LedgerApiService
import com.ledger.app.data.models.TransactionOut
import com.ledger.app.util.UiState
import kotlinx.coroutines.launch
import java.io.IOException

class TransactionsViewModel(private val api: LedgerApiService) : ViewModel() {

    val transactionState = MutableLiveData<UiState<List<TransactionOut>>>()
    var currentOffset: Int = 0
        private set
    var hasMorePages: Boolean = true
        private set
    var totalCount: Int = 0
        private set

    private val _allTransactions = mutableListOf<TransactionOut>()
    private val PAGE_SIZE = 20

    private var currentFromDate: String? = null
    private var currentToDate: String? = null

    fun loadTransactions() {
        currentOffset = 0
        hasMorePages = true
        _allTransactions.clear()
        transactionState.value = UiState.Loading

        viewModelScope.launch {
            loadPage()
            loadCount()
        }
    }

    fun loadMore() {
        if (!hasMorePages) return
        viewModelScope.launch {
            loadPage()
        }
    }

    fun filterByDate(fromDate: String, toDate: String) {
        currentFromDate = fromDate
        currentToDate = toDate
        loadTransactions()
    }

    private suspend fun loadPage() {
        try {
            val response = api.getTransactions(
                limit = PAGE_SIZE,
                offset = currentOffset,
                fromDate = currentFromDate,
                toDate = currentToDate
            )
            if (response.isSuccessful) {
                val newItems = response.body()!!
                if (newItems.isEmpty()) {
                    hasMorePages = false
                } else {
                    _allTransactions.addAll(newItems)
                    currentOffset += newItems.size
                    if (newItems.size < PAGE_SIZE) hasMorePages = false
                }
                transactionState.postValue(UiState.Success(_allTransactions.toList()))
            } else {
                transactionState.postValue(UiState.Error("Failed to load transactions: ${response.code()}"))
            }
        } catch (e: IOException) {
            transactionState.postValue(UiState.Error("Network error. Please check your connection."))
        } catch (e: Exception) {
            transactionState.postValue(UiState.Error("Error loading transactions: ${e.message}"))
        }
    }

    private suspend fun loadCount() {
        try {
            val response = api.getTransactionCount()
            if (response.isSuccessful) {
                totalCount = response.body()!!.count
            }
        } catch (e: Exception) {
            // Non-critical, ignore count failure
        }
    }
}
