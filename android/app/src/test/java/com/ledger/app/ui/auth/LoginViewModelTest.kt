package com.ledger.app.ui.auth

import com.ledger.app.data.api.LedgerApiService
import com.ledger.app.data.models.AuthListResponse
import com.ledger.app.data.models.TenantInfo
import com.ledger.app.data.models.TokenResponse
import com.ledger.app.ui.BaseViewModelTest
import com.ledger.app.util.FakeTokenStorage
import com.ledger.app.util.TokenManager
import com.ledger.app.util.UiState
import io.mockk.coEvery
import io.mockk.mockk
import kotlinx.coroutines.test.runTest
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import retrofit2.Response

class LoginViewModelTest : BaseViewModelTest() {

    private lateinit var mockApi: LedgerApiService
    private lateinit var viewModel: LoginViewModel
    private lateinit var fakeStorage: FakeTokenStorage

    private val singleTenantResponse = AuthListResponse(
        user_id = 1,
        email = "a@b.com",
        tenants = listOf(TenantInfo("uuid-1", "Home", "PERSONAL", "OWNER")),
        message = "ok"
    )

    private val multiTenantResponse = AuthListResponse(
        user_id = 1,
        email = "a@b.com",
        tenants = listOf(
            TenantInfo("uuid-1", "Personal", "PERSONAL", "OWNER"),
            TenantInfo("uuid-2", "Business", "SOLE_PROPRIETOR", "ADMIN")
        ),
        message = "ok"
    )

    @Before
    fun setUp() {
        mockApi = mockk()
        viewModel = LoginViewModel(mockApi)
        fakeStorage = FakeTokenStorage()
        TokenManager.storage = fakeStorage
    }

    @Test
    fun initial_state_is_idle() {
        assertNull(viewModel.loginState.value)
    }

    @Test
    fun login_success_emits_tenant_list() = runTest {
        coEvery { mockApi.login(any()) } returns Response.success(singleTenantResponse)
        viewModel.login("a@b.com", "pwd")
        testDispatcher.scheduler.advanceUntilIdle()

        val state = viewModel.loginState.value
        assertTrue(state is UiState.Success)
        assertEquals(1, (state as UiState.Success).data.tenants.size)
    }

    @Test
    fun login_failure_emits_error() = runTest {
        val errorBody = """{"detail":"Invalid credentials"}""".toResponseBody()
        coEvery { mockApi.login(any()) } returns Response.error(401, errorBody)
        viewModel.login("a@b.com", "wrong")
        testDispatcher.scheduler.advanceUntilIdle()

        val state = viewModel.loginState.value
        assertTrue("Expected Error but got $state", state is UiState.Error)
    }

    @Test
    fun login_network_error_emits_error() = runTest {
        coEvery { mockApi.login(any()) } throws java.io.IOException("Network unreachable")
        viewModel.login("a@b.com", "pwd")
        testDispatcher.scheduler.advanceUntilIdle()

        val state = viewModel.loginState.value
        assertTrue(state is UiState.Error)
        val message = (state as UiState.Error).message.lowercase()
        assertTrue("Expected 'network' or 'connection' in message but got: $message",
            message.contains("network") || message.contains("connection"))
    }

    @Test
    fun empty_email_emits_validation_error() {
        viewModel.login("", "pwd")
        val state = viewModel.loginState.value
        assertTrue(state is UiState.Error)
        val message = (state as UiState.Error).message.lowercase()
        assertTrue("Expected 'email' in message", message.contains("email"))
    }

    @Test
    fun empty_password_emits_validation_error() {
        viewModel.login("a@b.com", "")
        val state = viewModel.loginState.value
        assertTrue(state is UiState.Error)
        val message = (state as UiState.Error).message.lowercase()
        assertTrue("Expected 'password' in message", message.contains("password"))
    }

    @Test
    fun select_tenant_stores_token() = runTest {
        val tokenResponse = TokenResponse(
            access_token = "jwt",
            token_type = "bearer",
            user_id = 1,
            tenant_id = "uuid-1",
            role = "OWNER"
        )
        coEvery { mockApi.selectTenant(any()) } returns Response.success(tokenResponse)
        viewModel.selectTenant("uuid-1")
        testDispatcher.scheduler.advanceUntilIdle()

        assertEquals("jwt", TokenManager.getToken())
        assertTrue(viewModel.tenantState.value is UiState.Success)
    }

    @Test
    fun select_tenant_failure_emits_error() = runTest {
        val errorBody = """{"detail":"Forbidden"}""".toResponseBody()
        coEvery { mockApi.selectTenant(any()) } returns Response.error(403, errorBody)
        viewModel.selectTenant("bad-uuid")
        testDispatcher.scheduler.advanceUntilIdle()

        assertTrue(viewModel.tenantState.value is UiState.Error)
    }

    @Test
    fun single_tenant_auto_selects() = runTest {
        coEvery { mockApi.login(any()) } returns Response.success(singleTenantResponse)
        viewModel.login("a@b.com", "pwd")
        testDispatcher.scheduler.advanceUntilIdle()

        assertTrue(viewModel.shouldAutoSelectTenant)
    }

    @Test
    fun multi_tenant_does_not_auto_select() = runTest {
        coEvery { mockApi.login(any()) } returns Response.success(multiTenantResponse)
        viewModel.login("a@b.com", "pwd")
        testDispatcher.scheduler.advanceUntilIdle()

        assertFalse(viewModel.shouldAutoSelectTenant)
    }
}
