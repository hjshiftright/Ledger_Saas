package com.ledger.app.data.models;

@com.squareup.moshi.JsonClass(generateAdapter = true)
@kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000*\n\u0002\u0018\u0002\n\u0002\u0010\u0000\n\u0000\n\u0002\u0010\u000e\n\u0002\b\u0006\n\u0002\u0010\u0006\n\u0002\b\u001e\n\u0002\u0010\u000b\n\u0002\b\u0002\n\u0002\u0010\b\n\u0002\b\u0002\b\u0087\b\u0018\u00002\u00020\u0001Bk\u0012\u0006\u0010\u0002\u001a\u00020\u0003\u0012\n\b\u0002\u0010\u0004\u001a\u0004\u0018\u00010\u0003\u0012\n\b\u0002\u0010\u0005\u001a\u0004\u0018\u00010\u0003\u0012\u0006\u0010\u0006\u001a\u00020\u0003\u0012\u0006\u0010\u0007\u001a\u00020\u0003\u0012\u0006\u0010\b\u001a\u00020\u0003\u0012\b\u0010\t\u001a\u0004\u0018\u00010\n\u0012\n\b\u0002\u0010\u000b\u001a\u0004\u0018\u00010\u0003\u0012\n\b\u0002\u0010\f\u001a\u0004\u0018\u00010\u0003\u0012\n\b\u0002\u0010\r\u001a\u0004\u0018\u00010\u0003\u00a2\u0006\u0002\u0010\u000eJ\t\u0010\u001c\u001a\u00020\u0003H\u00c6\u0003J\u000b\u0010\u001d\u001a\u0004\u0018\u00010\u0003H\u00c6\u0003J\u000b\u0010\u001e\u001a\u0004\u0018\u00010\u0003H\u00c6\u0003J\u000b\u0010\u001f\u001a\u0004\u0018\u00010\u0003H\u00c6\u0003J\t\u0010 \u001a\u00020\u0003H\u00c6\u0003J\t\u0010!\u001a\u00020\u0003H\u00c6\u0003J\t\u0010\"\u001a\u00020\u0003H\u00c6\u0003J\u0010\u0010#\u001a\u0004\u0018\u00010\nH\u00c6\u0003\u00a2\u0006\u0002\u0010\u0017J\u000b\u0010$\u001a\u0004\u0018\u00010\u0003H\u00c6\u0003J\u000b\u0010%\u001a\u0004\u0018\u00010\u0003H\u00c6\u0003J~\u0010&\u001a\u00020\u00002\b\b\u0002\u0010\u0002\u001a\u00020\u00032\n\b\u0002\u0010\u0004\u001a\u0004\u0018\u00010\u00032\n\b\u0002\u0010\u0005\u001a\u0004\u0018\u00010\u00032\b\b\u0002\u0010\u0006\u001a\u00020\u00032\b\b\u0002\u0010\u0007\u001a\u00020\u00032\b\b\u0002\u0010\b\u001a\u00020\u00032\n\b\u0002\u0010\t\u001a\u0004\u0018\u00010\n2\n\b\u0002\u0010\u000b\u001a\u0004\u0018\u00010\u00032\n\b\u0002\u0010\f\u001a\u0004\u0018\u00010\u00032\n\b\u0002\u0010\r\u001a\u0004\u0018\u00010\u0003H\u00c6\u0001\u00a2\u0006\u0002\u0010\'J\u0013\u0010(\u001a\u00020)2\b\u0010*\u001a\u0004\u0018\u00010\u0001H\u00d6\u0003J\t\u0010+\u001a\u00020,H\u00d6\u0001J\t\u0010-\u001a\u00020\u0003H\u00d6\u0001R\u0013\u0010\u000b\u001a\u0004\u0018\u00010\u0003\u00a2\u0006\b\n\u0000\u001a\u0004\b\u000f\u0010\u0010R\u0013\u0010\f\u001a\u0004\u0018\u00010\u0003\u00a2\u0006\b\n\u0000\u001a\u0004\b\u0011\u0010\u0010R\u0011\u0010\b\u001a\u00020\u0003\u00a2\u0006\b\n\u0000\u001a\u0004\b\u0012\u0010\u0010R\u0011\u0010\u0002\u001a\u00020\u0003\u00a2\u0006\b\n\u0000\u001a\u0004\b\u0013\u0010\u0010R\u0011\u0010\u0007\u001a\u00020\u0003\u00a2\u0006\b\n\u0000\u001a\u0004\b\u0014\u0010\u0010R\u0011\u0010\u0006\u001a\u00020\u0003\u00a2\u0006\b\n\u0000\u001a\u0004\b\u0015\u0010\u0010R\u0015\u0010\t\u001a\u0004\u0018\u00010\n\u00a2\u0006\n\n\u0002\u0010\u0018\u001a\u0004\b\u0016\u0010\u0017R\u0013\u0010\r\u001a\u0004\u0018\u00010\u0003\u00a2\u0006\b\n\u0000\u001a\u0004\b\u0019\u0010\u0010R\u0013\u0010\u0004\u001a\u0004\u0018\u00010\u0003\u00a2\u0006\b\n\u0000\u001a\u0004\b\u001a\u0010\u0010R\u0013\u0010\u0005\u001a\u0004\u0018\u00010\u0003\u00a2\u0006\b\n\u0000\u001a\u0004\b\u001b\u0010\u0010\u00a8\u0006."}, d2 = {"Lcom/ledger/app/data/models/DashboardSummary;", "", "net_worth", "", "total_assets", "total_liabilities", "period_income", "period_expenses", "net_income", "savings_rate", "", "as_of", "from_date", "to_date", "(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/Double;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;)V", "getAs_of", "()Ljava/lang/String;", "getFrom_date", "getNet_income", "getNet_worth", "getPeriod_expenses", "getPeriod_income", "getSavings_rate", "()Ljava/lang/Double;", "Ljava/lang/Double;", "getTo_date", "getTotal_assets", "getTotal_liabilities", "component1", "component10", "component2", "component3", "component4", "component5", "component6", "component7", "component8", "component9", "copy", "(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/Double;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;)Lcom/ledger/app/data/models/DashboardSummary;", "equals", "", "other", "hashCode", "", "toString", "app_debug"})
public final class DashboardSummary {
    @org.jetbrains.annotations.NotNull()
    private final java.lang.String net_worth = null;
    @org.jetbrains.annotations.Nullable()
    private final java.lang.String total_assets = null;
    @org.jetbrains.annotations.Nullable()
    private final java.lang.String total_liabilities = null;
    @org.jetbrains.annotations.NotNull()
    private final java.lang.String period_income = null;
    @org.jetbrains.annotations.NotNull()
    private final java.lang.String period_expenses = null;
    @org.jetbrains.annotations.NotNull()
    private final java.lang.String net_income = null;
    @org.jetbrains.annotations.Nullable()
    private final java.lang.Double savings_rate = null;
    @org.jetbrains.annotations.Nullable()
    private final java.lang.String as_of = null;
    @org.jetbrains.annotations.Nullable()
    private final java.lang.String from_date = null;
    @org.jetbrains.annotations.Nullable()
    private final java.lang.String to_date = null;
    
    public DashboardSummary(@org.jetbrains.annotations.NotNull()
    java.lang.String net_worth, @org.jetbrains.annotations.Nullable()
    java.lang.String total_assets, @org.jetbrains.annotations.Nullable()
    java.lang.String total_liabilities, @org.jetbrains.annotations.NotNull()
    java.lang.String period_income, @org.jetbrains.annotations.NotNull()
    java.lang.String period_expenses, @org.jetbrains.annotations.NotNull()
    java.lang.String net_income, @org.jetbrains.annotations.Nullable()
    java.lang.Double savings_rate, @org.jetbrains.annotations.Nullable()
    java.lang.String as_of, @org.jetbrains.annotations.Nullable()
    java.lang.String from_date, @org.jetbrains.annotations.Nullable()
    java.lang.String to_date) {
        super();
    }
    
    @org.jetbrains.annotations.NotNull()
    public final java.lang.String getNet_worth() {
        return null;
    }
    
    @org.jetbrains.annotations.Nullable()
    public final java.lang.String getTotal_assets() {
        return null;
    }
    
    @org.jetbrains.annotations.Nullable()
    public final java.lang.String getTotal_liabilities() {
        return null;
    }
    
    @org.jetbrains.annotations.NotNull()
    public final java.lang.String getPeriod_income() {
        return null;
    }
    
    @org.jetbrains.annotations.NotNull()
    public final java.lang.String getPeriod_expenses() {
        return null;
    }
    
    @org.jetbrains.annotations.NotNull()
    public final java.lang.String getNet_income() {
        return null;
    }
    
    @org.jetbrains.annotations.Nullable()
    public final java.lang.Double getSavings_rate() {
        return null;
    }
    
    @org.jetbrains.annotations.Nullable()
    public final java.lang.String getAs_of() {
        return null;
    }
    
    @org.jetbrains.annotations.Nullable()
    public final java.lang.String getFrom_date() {
        return null;
    }
    
    @org.jetbrains.annotations.Nullable()
    public final java.lang.String getTo_date() {
        return null;
    }
    
    @org.jetbrains.annotations.NotNull()
    public final java.lang.String component1() {
        return null;
    }
    
    @org.jetbrains.annotations.Nullable()
    public final java.lang.String component10() {
        return null;
    }
    
    @org.jetbrains.annotations.Nullable()
    public final java.lang.String component2() {
        return null;
    }
    
    @org.jetbrains.annotations.Nullable()
    public final java.lang.String component3() {
        return null;
    }
    
    @org.jetbrains.annotations.NotNull()
    public final java.lang.String component4() {
        return null;
    }
    
    @org.jetbrains.annotations.NotNull()
    public final java.lang.String component5() {
        return null;
    }
    
    @org.jetbrains.annotations.NotNull()
    public final java.lang.String component6() {
        return null;
    }
    
    @org.jetbrains.annotations.Nullable()
    public final java.lang.Double component7() {
        return null;
    }
    
    @org.jetbrains.annotations.Nullable()
    public final java.lang.String component8() {
        return null;
    }
    
    @org.jetbrains.annotations.Nullable()
    public final java.lang.String component9() {
        return null;
    }
    
    @org.jetbrains.annotations.NotNull()
    public final com.ledger.app.data.models.DashboardSummary copy(@org.jetbrains.annotations.NotNull()
    java.lang.String net_worth, @org.jetbrains.annotations.Nullable()
    java.lang.String total_assets, @org.jetbrains.annotations.Nullable()
    java.lang.String total_liabilities, @org.jetbrains.annotations.NotNull()
    java.lang.String period_income, @org.jetbrains.annotations.NotNull()
    java.lang.String period_expenses, @org.jetbrains.annotations.NotNull()
    java.lang.String net_income, @org.jetbrains.annotations.Nullable()
    java.lang.Double savings_rate, @org.jetbrains.annotations.Nullable()
    java.lang.String as_of, @org.jetbrains.annotations.Nullable()
    java.lang.String from_date, @org.jetbrains.annotations.Nullable()
    java.lang.String to_date) {
        return null;
    }
    
    @java.lang.Override()
    public boolean equals(@org.jetbrains.annotations.Nullable()
    java.lang.Object other) {
        return false;
    }
    
    @java.lang.Override()
    public int hashCode() {
        return 0;
    }
    
    @java.lang.Override()
    @org.jetbrains.annotations.NotNull()
    public java.lang.String toString() {
        return null;
    }
}