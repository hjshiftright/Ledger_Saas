-if class com.ledger.app.data.models.MonthlyTrend
-keepnames class com.ledger.app.data.models.MonthlyTrend
-if class com.ledger.app.data.models.MonthlyTrend
-keep class com.ledger.app.data.models.MonthlyTrendJsonAdapter {
    public <init>(com.squareup.moshi.Moshi);
}
