-if class com.ledger.app.data.models.TokenResponse
-keepnames class com.ledger.app.data.models.TokenResponse
-if class com.ledger.app.data.models.TokenResponse
-keep class com.ledger.app.data.models.TokenResponseJsonAdapter {
    public <init>(com.squareup.moshi.Moshi);
}
