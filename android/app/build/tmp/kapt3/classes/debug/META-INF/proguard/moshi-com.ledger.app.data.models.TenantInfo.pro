-if class com.ledger.app.data.models.TenantInfo
-keepnames class com.ledger.app.data.models.TenantInfo
-if class com.ledger.app.data.models.TenantInfo
-keep class com.ledger.app.data.models.TenantInfoJsonAdapter {
    public <init>(com.squareup.moshi.Moshi);
}
