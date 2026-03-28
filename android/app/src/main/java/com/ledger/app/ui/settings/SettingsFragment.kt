package com.ledger.app.ui.settings

import android.content.Intent
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import com.ledger.app.config.AppConfig
import com.ledger.app.data.api.RetrofitClient
import com.ledger.app.databinding.FragmentSettingsBinding
import com.ledger.app.ui.auth.LoginActivity
import com.ledger.app.util.TokenManager
import kotlinx.coroutines.launch

class SettingsFragment : Fragment() {

    private var _binding: FragmentSettingsBinding? = null
    private val binding get() = _binding!!

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        _binding = FragmentSettingsBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        binding.etBaseUrl.setText(AppConfig.BASE_URL)

        binding.btnTestConnection.setOnClickListener {
            val url = binding.etBaseUrl.text?.toString()?.trim() ?: ""
            if (url.isNotEmpty()) {
                AppConfig.BASE_URL = url
                RetrofitClient.resetInstance()
            }
            testConnection()
        }

        binding.btnLogout.setOnClickListener {
            TokenManager.clearToken()
            val intent = Intent(requireContext(), LoginActivity::class.java)
            intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
            startActivity(intent)
        }

        binding.btnSwitchTenant.setOnClickListener {
            android.widget.Toast.makeText(context, "Switch tenant: logout and re-login", android.widget.Toast.LENGTH_SHORT).show()
        }
    }

    private fun testConnection() {
        binding.ivConnectionStatus.visibility = View.GONE
        lifecycleScope.launch {
            try {
                val response = RetrofitClient.api.healthCheck()
                if (response.isSuccessful) {
                    android.widget.Toast.makeText(context, "Connected successfully ✓", android.widget.Toast.LENGTH_SHORT).show()
                } else {
                    android.widget.Toast.makeText(context, "Connection failed: ${response.code()}", android.widget.Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                android.widget.Toast.makeText(context, "Connection failed: ${e.message}", android.widget.Toast.LENGTH_SHORT).show()
            }
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
