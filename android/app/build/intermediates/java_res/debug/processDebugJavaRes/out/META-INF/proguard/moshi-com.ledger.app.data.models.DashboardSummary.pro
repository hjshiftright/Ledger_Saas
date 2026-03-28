-if class com.ledger.app.data.models.DashboardSummary
-keepnames class com.ledger.app.data.models.DashboardSummary
-if class com.ledger.app.data.models.DashboardSummary
-keep class com.ledger.app.data.models.DashboardSummaryJsonAdapter {
    public <init>(com.squareup.moshi.Moshi);
}
-if class com.ledger.app.data.models.DashboardSummary
-keepnames class kotlin.jvm.internal.DefaultConstructorMarker
-if class com.ledger.app.data.models.DashboardSummary
-keepclassmembers class com.ledger.app.data.models.DashboardSummary {
    public synthetic <init>(java.lang.String,java.lang.String,java.lang.String,java.lang.String,java.lang.String,java.lang.String,java.lang.Double,java.lang.String,java.lang.String,java.lang.String,int,kotlin.jvm.internal.DefaultConstructorMarker);
}
