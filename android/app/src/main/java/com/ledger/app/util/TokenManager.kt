package com.ledger.app.util

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

interface TokenStorage {
    fun getToken(): String?
    fun savePreToken(token: String)
    fun saveToken(token: String, userId: Int, tenantId: String)
    fun clearToken()
}

class EncryptedPrefsStorage(context: Context) : TokenStorage {

    private val prefs = EncryptedSharedPreferences.create(
        context,
        "ledger_auth",
        MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build(),
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
    )

    override fun getToken(): String? = prefs.getString("access_token", null)

    override fun savePreToken(token: String) {
        prefs.edit().putString("access_token", token).apply()
    }

    override fun saveToken(token: String, userId: Int, tenantId: String) {
        prefs.edit()
            .putString("access_token", token)
            .putInt("user_id", userId)
            .putString("tenant_id", tenantId)
            .apply()
    }

    override fun clearToken() {
        prefs.edit().clear().apply()
    }
}

object TokenManager {
    var storage: TokenStorage? = null

    fun getToken(): String? = storage?.getToken()

    fun savePreToken(token: String) {
        storage?.savePreToken(token)
    }

    fun saveToken(context: Context? = null, token: String, userId: Int, tenantId: String) {
        storage?.saveToken(token, userId, tenantId)
    }

    fun clearToken(context: Context? = null) {
        storage?.clearToken()
    }

    fun isLoggedIn(): Boolean = getToken() != null
}
