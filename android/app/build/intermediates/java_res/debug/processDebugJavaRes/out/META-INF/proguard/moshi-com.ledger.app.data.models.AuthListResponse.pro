-if class com.ledger.app.data.models.AuthListResponse
-keepnames class com.ledger.app.data.models.AuthListResponse
-if class com.ledger.app.data.models.AuthListResponse
-keep class com.ledger.app.data.models.AuthListResponseJsonAdapter {
    public <init>(com.squareup.moshi.Moshi);
}
