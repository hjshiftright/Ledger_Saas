package com.ledger.app.ui.web

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AppCompatActivity
import com.ledger.app.config.AppConfig
import com.ledger.app.databinding.ActivityWebAppBinding
import com.ledger.app.ui.auth.LoginActivity

class WebAppActivity : AppCompatActivity() {

    private lateinit var binding: ActivityWebAppBinding

    // Two-load trick: first load establishes the origin, we inject the token,
    // then reload so React initialises with auth state already set.
    private var tokenInjected = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityWebAppBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // Hide the action bar — web app has its own navigation
        supportActionBar?.hide()

        val token  = intent.getStringExtra(EXTRA_TOKEN)  ?: ""
        val email  = intent.getStringExtra(EXTRA_EMAIL)  ?: ""
        val userId = intent.getIntExtra(EXTRA_USER_ID, 0)

        setupBackNavigation()
        setupWebView(token, email, userId)
    }

    private fun setupWebView(token: String, email: String, userId: Int) {
        binding.webView.apply {
            settings.apply {
                javaScriptEnabled   = true
                domStorageEnabled   = true   // required for localStorage / sessionStorage
                setSupportZoom(false)
                builtInZoomControls = false
                displayZoomControls = false
            }

            webViewClient = object : WebViewClient() {
                override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                    // Keep all navigation inside the WebView
                    return false
                }

                override fun onPageFinished(view: WebView, url: String) {
                    if (!tokenInjected) {
                        // First load finished: inject credentials then reload
                        tokenInjected = true
                        val js = """
                            (function(){
                                sessionStorage.setItem('ledger_auth_token', '${token.replace("'", "\\'")}');
                                sessionStorage.setItem('ledger_user_email',  '${email.replace("'", "\\'")}');
                                sessionStorage.setItem('ledger_user_id',     '$userId');
                            })();
                        """.trimIndent()
                        view.evaluateJavascript(js) {
                            view.reload()
                        }
                    } else {
                        // Second load: credentials are set — reveal the WebView
                        binding.loadingOverlay.visibility = View.GONE
                        binding.webView.visibility        = View.VISIBLE
                    }
                }
            }

            webChromeClient = object : WebChromeClient() {
                override fun onProgressChanged(view: WebView, newProgress: Int) {
                    binding.progressBar.progress = newProgress
                    binding.progressBar.visibility =
                        if (newProgress < 100) View.VISIBLE else View.GONE
                }
            }

            loadUrl("${AppConfig.BASE_URL}/")
        }
    }

    private fun setupBackNavigation() {
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                when {
                    binding.webView.canGoBack() -> binding.webView.goBack()
                    else -> {
                        // Return to login
                        val intent = Intent(this@WebAppActivity, LoginActivity::class.java)
                        intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
                        startActivity(intent)
                    }
                }
            }
        })
    }

    companion object {
        const val EXTRA_TOKEN   = "token"
        const val EXTRA_EMAIL   = "email"
        const val EXTRA_USER_ID = "user_id"
    }
}
