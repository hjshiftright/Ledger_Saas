-if class com.ledger.app.data.models.SignupRequest
-keepnames class com.ledger.app.data.models.SignupRequest
-if class com.ledger.app.data.models.SignupRequest
-keep class com.ledger.app.data.models.SignupRequestJsonAdapter {
    public <init>(com.squareup.moshi.Moshi);
}
-if class com.ledger.app.data.models.SignupRequest
-keepnames class kotlin.jvm.internal.DefaultConstructorMarker
-if class com.ledger.app.data.models.SignupRequest
-keepclassmembers class com.ledger.app.data.models.SignupRequest {
    public synthetic <init>(java.lang.String,java.lang.String,java.lang.String,java.lang.String,int,kotlin.jvm.internal.DefaultConstructorMarker);
}
