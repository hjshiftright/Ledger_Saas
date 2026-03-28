package com.ledger.app.ui.auth

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.ArrayAdapter
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.ViewModelProvider
import com.ledger.app.data.api.RetrofitClient
import com.ledger.app.data.models.AuthListResponse
import com.ledger.app.databinding.ActivitySignupBinding
import com.ledger.app.ui.main.MainActivity
import com.ledger.app.util.UiState
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory

class SignupActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySignupBinding
    private lateinit var viewModel: SignupViewModel

    private val entityTypes = listOf(
        "PERSONAL", "SOLE_PROPRIETOR", "PARTNERSHIP", "COMPANY", "TRUST", "HUF"
    )

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySignupBinding.inflate(layoutInflater)
        setContentView(binding.root)

        viewModel = ViewModelProvider(
            this,
            SignupViewModelFactory(RetrofitClient.api)
        )[SignupViewModel::class.java]

        setupEntityTypeDropdown()
        setupObservers()
        setupClickListeners()
    }

    private fun setupEntityTypeDropdown() {
        val adapter = ArrayAdapter(this, android.R.layout.simple_dropdown_item_1line, entityTypes)
        binding.actvEntityType.setAdapter(adapter)
        binding.actvEntityType.setText(entityTypes[0], false)
    }

    private fun setupObservers() {
        viewModel.signupState.observe(this) { state ->
            when (state) {
                is UiState.Loading -> showLoading(true)
                is UiState.Success -> {
                    showLoading(false)
                    handleSignupSuccess(state.data)
                }
                is UiState.Error -> {
                    showLoading(false)
                    showError(state.message)
                }
            }
        }
    }

    private fun setupClickListeners() {
        binding.btnSignup.setOnClickListener {
            val email = binding.etEmail.text?.toString() ?: ""
            val password = binding.etPassword.text?.toString() ?: ""
            val fullName = binding.etFullName.text?.toString() ?: ""
            val entityType = binding.actvEntityType.text?.toString() ?: entityTypes[0]
            viewModel.signup(email, password, fullName, entityType)
        }

        binding.tvLogin.setOnClickListener {
            finish()
        }
    }

    private fun handleSignupSuccess(authResponse: AuthListResponse) {
        if (authResponse.tenants.size == 1) {
            // Reuse LoginViewModel behavior via a simple intent
            val moshi = Moshi.Builder().addLast(KotlinJsonAdapterFactory()).build()
            val adapter = moshi.adapter(AuthListResponse::class.java)
            val intent = Intent(this, TenantPickerActivity::class.java)
            intent.putExtra("auth_response", adapter.toJson(authResponse))
            startActivity(intent)
        } else {
            val moshi = Moshi.Builder().addLast(KotlinJsonAdapterFactory()).build()
            val adapter = moshi.adapter(AuthListResponse::class.java)
            val intent = Intent(this, TenantPickerActivity::class.java)
            intent.putExtra("auth_response", adapter.toJson(authResponse))
            startActivity(intent)
        }
    }

    private fun showLoading(loading: Boolean) {
        binding.btnSignup.isEnabled = !loading
        if (loading) binding.layoutError.visibility = View.GONE
    }

    private fun showError(message: String) {
        binding.layoutError.visibility = View.VISIBLE
        binding.tvErrorMessage.text = message
    }
}
