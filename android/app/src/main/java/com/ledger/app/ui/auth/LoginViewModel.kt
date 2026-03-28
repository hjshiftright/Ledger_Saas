package com.ledger.app.ui.auth

import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ledger.app.data.api.LedgerApiService
import com.ledger.app.data.models.AuthListResponse
import com.ledger.app.data.models.LoginRequest
import com.ledger.app.data.models.SelectTenantRequest
import com.ledger.app.data.models.TokenResponse
import com.ledger.app.util.TokenManager
import com.ledger.app.util.UiState
import kotlinx.coroutines.launch
import java.io.IOException

class LoginViewModel(private val api: LedgerApiService) : ViewModel() {

    val loginState = MutableLiveData<UiState<AuthListResponse>>()
    val tenantState = MutableLiveData<UiState<TokenResponse>>()

    private var _authResponse: AuthListResponse? = null
    val shouldAutoSelectTenant: Boolean
        get() = _authResponse?.tenants?.size == 1

    fun login(email: String, password: String) {
        if (email.isBlank()) {
            loginState.value = UiState.Error("Email is required.")
            return
        }
        if (password.isBlank()) {
            loginState.value = UiState.Error("Password is required.")
            return
        }

        loginState.value = UiState.Loading
        viewModelScope.launch {
            try {
                val response = api.login(LoginRequest(email.trim(), password))
                if (response.isSuccessful) {
                    val body = response.body()!!
                    _authResponse = body
                    loginState.value = UiState.Success(body)
                } else {
                    val errorMsg = parseErrorBody(response.errorBody()?.string())
                    loginState.value = UiState.Error(errorMsg)
                }
            } catch (e: IOException) {
                loginState.value = UiState.Error("Network error. Please check your connection.")
            } catch (e: Exception) {
                loginState.value = UiState.Error("An error occurred: ${e.message}")
            }
        }
    }

    fun selectTenant(tenantId: String) {
        tenantState.value = UiState.Loading
        viewModelScope.launch {
            try {
                val response = api.selectTenant(SelectTenantRequest(tenantId))
                if (response.isSuccessful) {
                    val body = response.body()!!
                    TokenManager.saveToken(
                        token = body.access_token,
                        userId = body.user_id,
                        tenantId = body.tenant_id
                    )
                    tenantState.value = UiState.Success(body)
                } else {
                    val errorMsg = parseErrorBody(response.errorBody()?.string())
                    tenantState.value = UiState.Error(errorMsg)
                }
            } catch (e: IOException) {
                tenantState.value = UiState.Error("Network error. Please check your connection.")
            } catch (e: Exception) {
                tenantState.value = UiState.Error("An error occurred: ${e.message}")
            }
        }
    }

    private fun parseErrorBody(errorBody: String?): String {
        if (errorBody == null) return "An error occurred."
        return try {
            // Try to extract "detail" field from JSON
            val detail = errorBody.substringAfter("\"detail\":\"", "")
                .substringBefore("\"")
            if (detail.isNotEmpty()) detail else errorBody
        } catch (e: Exception) {
            errorBody
        }
    }
}
