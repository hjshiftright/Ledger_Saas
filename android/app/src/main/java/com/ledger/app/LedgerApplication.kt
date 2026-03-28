package com.ledger.app

import android.app.Application
import com.ledger.app.util.EncryptedPrefsStorage
import com.ledger.app.util.TokenManager

class LedgerApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        TokenManager.storage = EncryptedPrefsStorage(this)
    }
}
