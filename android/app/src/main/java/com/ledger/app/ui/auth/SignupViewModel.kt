package com.ledger.app.ui.auth

import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ledger.app.data.api.LedgerApiService
import com.ledger.app.data.models.AuthListResponse
import com.ledger.app.data.models.SignupRequest
import com.ledger.app.util.UiState
import kotlinx.coroutines.launch
import java.io.IOException

class SignupViewModel(private val api: LedgerApiService) : ViewModel() {

    val signupState = MutableLiveData<UiState<AuthListResponse>>()

    fun signup(email: String, password: String, fullName: String, entityType: String) {
        if (email.isBlank() || password.isBlank() || fullName.isBlank() || entityType.isBlank()) {
            signupState.value = UiState.Error("All fields are required.")
            return
        }

        signupState.value = UiState.Loading
        viewModelScope.launch {
            try {
                val response = api.signup(
                    SignupRequest(
                        email = email.trim(),
                        password = password,
                        full_name = fullName.trim(),
                        entity_type = entityType
                    )
                )
                if (response.isSuccessful) {
                    signupState.value = UiState.Success(response.body()!!)
                } else {
                    val errorMsg = parseErrorBody(response.errorBody()?.string())
                    signupState.value = UiState.Error(errorMsg)
                }
            } catch (e: IOException) {
                signupState.value = UiState.Error("Network error. Please check your connection.")
            } catch (e: Exception) {
                signupState.value = UiState.Error("An error occurred: ${e.message}")
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
