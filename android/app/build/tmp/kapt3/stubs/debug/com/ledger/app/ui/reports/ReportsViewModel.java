package com.ledger.app.ui.reports;

@kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000V\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0002\u0010$\n\u0002\u0010\u000e\n\u0002\u0010\u0000\n\u0002\b\u0003\n\u0002\u0010 \n\u0002\u0018\u0002\n\u0002\b\u0004\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0010\u0002\n\u0002\b\n\u0018\u00002\u00020\u0001B\r\u0012\u0006\u0010\u0002\u001a\u00020\u0003\u00a2\u0006\u0002\u0010\u0004J\u001c\u0010\u0019\u001a\u000e\u0012\u0004\u0012\u00020\t\u0012\u0004\u0012\u00020\t0\u001a2\u0006\u0010\u001b\u001a\u00020\tH\u0002J\u000e\u0010\u001c\u001a\u00020\u001dH\u0082@\u00a2\u0006\u0002\u0010\u001eJ\u000e\u0010\u001f\u001a\u00020\u001dH\u0082@\u00a2\u0006\u0002\u0010\u001eJ\u0006\u0010 \u001a\u00020\u001dJ\u000e\u0010!\u001a\u00020\u001dH\u0082@\u00a2\u0006\u0002\u0010\u001eJ\u000e\u0010\"\u001a\u00020\u001dH\u0082@\u00a2\u0006\u0002\u0010\u001eJ\u0016\u0010#\u001a\u00020\u001d2\u0006\u0010$\u001a\u00020\t2\u0006\u0010%\u001a\u00020\tJ\u000e\u0010&\u001a\u00020\u001d2\u0006\u0010\u001b\u001a\u00020\tR\u000e\u0010\u0002\u001a\u00020\u0003X\u0082\u0004\u00a2\u0006\u0002\n\u0000R)\u0010\u0005\u001a\u001a\u0012\u0016\u0012\u0014\u0012\u0010\u0012\u000e\u0012\u0004\u0012\u00020\t\u0012\u0004\u0012\u00020\n0\b0\u00070\u0006\u00a2\u0006\b\n\u0000\u001a\u0004\b\u000b\u0010\fR#\u0010\r\u001a\u0014\u0012\u0010\u0012\u000e\u0012\n\u0012\b\u0012\u0004\u0012\u00020\u000f0\u000e0\u00070\u0006\u00a2\u0006\b\n\u0000\u001a\u0004\b\u0010\u0010\fR\u0010\u0010\u0011\u001a\u0004\u0018\u00010\tX\u0082\u000e\u00a2\u0006\u0002\n\u0000R\u0010\u0010\u0012\u001a\u0004\u0018\u00010\tX\u0082\u000e\u00a2\u0006\u0002\n\u0000R\u001d\u0010\u0013\u001a\u000e\u0012\n\u0012\b\u0012\u0004\u0012\u00020\u00140\u00070\u0006\u00a2\u0006\b\n\u0000\u001a\u0004\b\u0015\u0010\fR#\u0010\u0016\u001a\u0014\u0012\u0010\u0012\u000e\u0012\n\u0012\b\u0012\u0004\u0012\u00020\u00170\u000e0\u00070\u0006\u00a2\u0006\b\n\u0000\u001a\u0004\b\u0018\u0010\f\u00a8\u0006\'"}, d2 = {"Lcom/ledger/app/ui/reports/ReportsViewModel;", "Landroidx/lifecycle/ViewModel;", "api", "Lcom/ledger/app/data/api/LedgerApiService;", "(Lcom/ledger/app/data/api/LedgerApiService;)V", "balanceSheetState", "Landroidx/lifecycle/MutableLiveData;", "Lcom/ledger/app/util/UiState;", "", "", "", "getBalanceSheetState", "()Landroidx/lifecycle/MutableLiveData;", "categoriesState", "", "Lcom/ledger/app/data/models/ExpenseCategory;", "getCategoriesState", "currentFromDate", "currentToDate", "summaryState", "Lcom/ledger/app/data/models/DashboardSummary;", "getSummaryState", "trendState", "Lcom/ledger/app/data/models/MonthlyTrend;", "getTrendState", "calculateDateRange", "Lkotlin/Pair;", "period", "loadBalanceSheet", "", "(Lkotlin/coroutines/Continuation;)Ljava/lang/Object;", "loadCategories", "loadReports", "loadSummary", "loadTrend", "setCustomPeriod", "fromDate", "toDate", "setPeriod", "app_debug"})
public final class ReportsViewModel extends androidx.lifecycle.ViewModel {
    @org.jetbrains.annotations.NotNull()
    private final com.ledger.app.data.api.LedgerApiService api = null;
    @org.jetbrains.annotations.NotNull()
    private final androidx.lifecycle.MutableLiveData<com.ledger.app.util.UiState<com.ledger.app.data.models.DashboardSummary>> summaryState = null;
    @org.jetbrains.annotations.NotNull()
    private final androidx.lifecycle.MutableLiveData<com.ledger.app.util.UiState<java.util.List<com.ledger.app.data.models.MonthlyTrend>>> trendState = null;
    @org.jetbrains.annotations.NotNull()
    private final androidx.lifecycle.MutableLiveData<com.ledger.app.util.UiState<java.util.List<com.ledger.app.data.models.ExpenseCategory>>> categoriesState = null;
    @org.jetbrains.annotations.NotNull()
    private final androidx.lifecycle.MutableLiveData<com.ledger.app.util.UiState<java.util.Map<java.lang.String, java.lang.Object>>> balanceSheetState = null;
    @org.jetbrains.annotations.Nullable()
    private java.lang.String currentFromDate;
    @org.jetbrains.annotations.Nullable()
    private java.lang.String currentToDate;
    
    public ReportsViewModel(@org.jetbrains.annotations.NotNull()
    com.ledger.app.data.api.LedgerApiService api) {
        super();
    }
    
    @org.jetbrains.annotations.NotNull()
    public final androidx.lifecycle.MutableLiveData<com.ledger.app.util.UiState<com.ledger.app.data.models.DashboardSummary>> getSummaryState() {
        return null;
    }
    
    @org.jetbrains.annotations.NotNull()
    public final androidx.lifecycle.MutableLiveData<com.ledger.app.util.UiState<java.util.List<com.ledger.app.data.models.MonthlyTrend>>> getTrendState() {
        return null;
    }
    
    @org.jetbrains.annotations.NotNull()
    public final androidx.lifecycle.MutableLiveData<com.ledger.app.util.UiState<java.util.List<com.ledger.app.data.models.ExpenseCategory>>> getCategoriesState() {
        return null;
    }
    
    @org.jetbrains.annotations.NotNull()
    public final androidx.lifecycle.MutableLiveData<com.ledger.app.util.UiState<java.util.Map<java.lang.String, java.lang.Object>>> getBalanceSheetState() {
        return null;
    }
    
    public final void loadReports() {
    }
    
    public final void setPeriod(@org.jetbrains.annotations.NotNull()
    java.lang.String period) {
    }
    
    public final void setCustomPeriod(@org.jetbrains.annotations.NotNull()
    java.lang.String fromDate, @org.jetbrains.annotations.NotNull()
    java.lang.String toDate) {
    }
    
    private final kotlin.Pair<java.lang.String, java.lang.String> calculateDateRange(java.lang.String period) {
        return null;
    }
    
    private final java.lang.Object loadSummary(kotlin.coroutines.Continuation<? super kotlin.Unit> $completion) {
        return null;
    }
    
    private final java.lang.Object loadTrend(kotlin.coroutines.Continuation<? super kotlin.Unit> $completion) {
        return null;
    }
    
    private final java.lang.Object loadCategories(kotlin.coroutines.Continuation<? super kotlin.Unit> $completion) {
        return null;
    }
    
    private final java.lang.Object loadBalanceSheet(kotlin.coroutines.Continuation<? super kotlin.Unit> $completion) {
        return null;
    }
}