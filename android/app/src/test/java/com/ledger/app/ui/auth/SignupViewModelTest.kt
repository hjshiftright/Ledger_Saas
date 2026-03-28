package com.ledger.app.ui.auth

import com.ledger.app.data.api.LedgerApiService
import com.ledger.app.data.models.AuthListResponse
import com.ledger.app.data.models.TenantInfo
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

class SignupViewModelTest : BaseViewModelTest() {

    private lateinit var mockApi: LedgerApiService
    private lateinit var viewModel: SignupViewModel

    private val authResponse = AuthListResponse(
        user_id = 1,
        email = "a@b.com",
        tenants = listOf(TenantInfo("uuid-1", "Home", "PERSONAL", "OWNER")),
        message = "ok"
    )

    @Before
    fun setUp() {
        mockApi = mockk()
        viewModel = SignupViewModel(mockApi)
    }

    @Test
    fun signup_success_emits_tenant_list() = runTest {
        coEvery { mockApi.signup(any()) } returns Response.success(authResponse)
        viewModel.signup("a@b.com", "pwd", "John", "PERSONAL")
        testDispatcher.scheduler.advanceUntilIdle()

        assertTrue(viewModel.signupState.value is UiState.Success)
    }

    @Test
    fun signup_duplicate_email_emits_error() = runTest {
        val errorBody = """{"detail":"Email already registered"}""".toResponseBody()
        coEvery { mockApi.signup(any()) } returns Response.error(400, errorBody)
        viewModel.signup("existing@b.com", "pwd", "John", "PERSONAL")
        testDispatcher.scheduler.advanceUntilIdle()

        assertTrue(viewModel.signupState.value is UiState.Error)
    }

    @Test
    fun signup_validates_required_fields() {
        viewModel.signup("", "", "", "")
        assertTrue(viewModel.signupState.value is UiState.Error)
    }
}
