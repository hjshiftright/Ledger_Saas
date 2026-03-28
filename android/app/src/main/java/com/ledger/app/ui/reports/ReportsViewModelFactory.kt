package com.ledger.app.ui.reports

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import com.ledger.app.data.api.LedgerApiService

class ReportsViewModelFactory(private val api: LedgerApiService) : ViewModelProvider.Factory {
    override fun <T : ViewModel> create(modelClass: Class<T>): T {
        @Suppress("UNCHECKED_CAST")
        return ReportsViewModel(api) as T
    }
}
