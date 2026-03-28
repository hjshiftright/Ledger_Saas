-if class com.ledger.app.data.models.HealthResponse
-keepnames class com.ledger.app.data.models.HealthResponse
-if class com.ledger.app.data.models.HealthResponse
-keep class com.ledger.app.data.models.HealthResponseJsonAdapter {
    public <init>(com.squareup.moshi.Moshi);
}
-if class com.ledger.app.data.models.HealthResponse
-keepnames class kotlin.jvm.internal.DefaultConstructorMarker
-if class com.ledger.app.data.models.HealthResponse
-keepclassmembers class com.ledger.app.data.models.HealthResponse {
    public synthetic <init>(java.lang.String,java.lang.String,java.lang.String,int,kotlin.jvm.internal.DefaultConstructorMarker);
}
