-if class com.ledger.app.data.models.LoginRequest
-keepnames class com.ledger.app.data.models.LoginRequest
-if class com.ledger.app.data.models.LoginRequest
-keep class com.ledger.app.data.models.LoginRequestJsonAdapter {
    public <init>(com.squareup.moshi.Moshi);
}
