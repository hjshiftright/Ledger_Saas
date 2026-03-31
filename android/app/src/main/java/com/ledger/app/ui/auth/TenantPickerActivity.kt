package com.ledger.app.ui.auth

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.ViewModelProvider
import androidx.recyclerview.widget.LinearLayoutManager
import com.ledger.app.data.api.RetrofitClient
import com.ledger.app.data.models.AuthListResponse
import com.ledger.app.data.models.TenantInfo
import com.ledger.app.util.TokenManager
import com.ledger.app.databinding.ActivityTenantPickerBinding
import com.ledger.app.ui.web.WebAppActivity
import com.ledger.app.util.UiState
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory

class TenantPickerActivity : AppCompatActivity() {

    private lateinit var binding: ActivityTenantPickerBinding
    private lateinit var loginViewModel: LoginViewModel

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityTenantPickerBinding.inflate(layoutInflater)
        setContentView(binding.root)

        setSupportActionBar(binding.toolbar)

        loginViewModel = ViewModelProvider(
            this,
            LoginViewModelFactory(RetrofitClient.api)
        )[LoginViewModel::class.java]

        val authResponseJson = intent.getStringExtra("auth_response") ?: run {
            finish()
            return
        }

        val moshi = Moshi.Builder().addLast(KotlinJsonAdapterFactory()).build()
        val adapter = moshi.adapter(AuthListResponse::class.java)
        val authResponse = adapter.fromJson(authResponseJson) ?: run {
            finish()
            return
        }

        // Store the pre_token so AuthInterceptor sends it with the select-tenant request
        TokenManager.savePreToken(authResponse.pre_token)

        // Auto-select if single tenant
        if (authResponse.tenants.size == 1) {
            loginViewModel.selectTenant(authResponse.tenants[0].tenant_id)
        } else {
            setupRecyclerView(authResponse.tenants)
        }

        loginViewModel.tenantState.observe(this) { state ->
            if (state is UiState.Success) {
                navigateToWebApp(state.data.access_token, authResponse.email, state.data.user_id)
            }
        }
    }

    private fun setupRecyclerView(tenants: List<TenantInfo>) {
        val adapter = TenantAdapter(tenants) { tenant ->
            loginViewModel.selectTenant(tenant.tenant_id)
        }
        binding.rvTenants.layoutManager = LinearLayoutManager(this)
        binding.rvTenants.adapter = adapter
    }

    private fun navigateToWebApp(token: String, email: String, userId: Int) {
        val intent = Intent(this, WebAppActivity::class.java).apply {
            putExtra(WebAppActivity.EXTRA_TOKEN,   token)
            putExtra(WebAppActivity.EXTRA_EMAIL,   email)
            putExtra(WebAppActivity.EXTRA_USER_ID, userId)
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        }
        startActivity(intent)
    }
}
