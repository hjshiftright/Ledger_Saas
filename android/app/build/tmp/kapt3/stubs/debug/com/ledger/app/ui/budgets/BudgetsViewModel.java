package com.ledger.app.ui.budgets;

@kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000P\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0010 \n\u0002\u0018\u0002\n\u0000\n\u0002\u0010\b\n\u0002\b\u0003\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0002\b\u0005\n\u0002\u0010\u0002\n\u0002\b\u0002\n\u0002\u0010\u000b\n\u0002\b\u0004\n\u0002\u0010\u0006\n\u0002\b\u0004\n\u0002\u0018\u0002\n\u0002\b\u0004\u0018\u00002\u00020\u0001B\r\u0012\u0006\u0010\u0002\u001a\u00020\u0003\u00a2\u0006\u0002\u0010\u0004J\u000e\u0010\u001f\u001a\u00020\u00142\u0006\u0010 \u001a\u00020!J\u000e\u0010\"\u001a\u00020\u00142\u0006\u0010#\u001a\u00020\tJ\u0006\u0010$\u001a\u00020\u0014R\u0014\u0010\u0005\u001a\b\u0012\u0004\u0012\u00020\u00070\u0006X\u0082\u000e\u00a2\u0006\u0002\n\u0000R\u0011\u0010\b\u001a\u00020\t8F\u00a2\u0006\u0006\u001a\u0004\b\n\u0010\u000bR\u000e\u0010\u0002\u001a\u00020\u0003X\u0082\u0004\u00a2\u0006\u0002\n\u0000R#\u0010\f\u001a\u0014\u0012\u0010\u0012\u000e\u0012\n\u0012\b\u0012\u0004\u0012\u00020\u00070\u00060\u000e0\r\u00a2\u0006\b\n\u0000\u001a\u0004\b\u000f\u0010\u0010R\u001d\u0010\u0011\u001a\u000e\u0012\n\u0012\b\u0012\u0004\u0012\u00020\u00070\u000e0\r\u00a2\u0006\b\n\u0000\u001a\u0004\b\u0012\u0010\u0010R\u001d\u0010\u0013\u001a\u000e\u0012\n\u0012\b\u0012\u0004\u0012\u00020\u00140\u000e0\r\u00a2\u0006\b\n\u0000\u001a\u0004\b\u0015\u0010\u0010R\u0011\u0010\u0016\u001a\u00020\u00178F\u00a2\u0006\u0006\u001a\u0004\b\u0016\u0010\u0018R\u0011\u0010\u0019\u001a\u00020\t8F\u00a2\u0006\u0006\u001a\u0004\b\u001a\u0010\u000bR\u0011\u0010\u001b\u001a\u00020\u001c8F\u00a2\u0006\u0006\u001a\u0004\b\u001d\u0010\u001e\u00a8\u0006%"}, d2 = {"Lcom/ledger/app/ui/budgets/BudgetsViewModel;", "Landroidx/lifecycle/ViewModel;", "api", "Lcom/ledger/app/data/api/LedgerApiService;", "(Lcom/ledger/app/data/api/LedgerApiService;)V", "_budgets", "", "Lcom/ledger/app/data/models/BudgetOut;", "activeBudgetCount", "", "getActiveBudgetCount", "()I", "budgetsState", "Landroidx/lifecycle/MutableLiveData;", "Lcom/ledger/app/util/UiState;", "getBudgetsState", "()Landroidx/lifecycle/MutableLiveData;", "createState", "getCreateState", "deleteState", "", "getDeleteState", "isEmpty", "", "()Z", "totalLineItems", "getTotalLineItems", "totalPlannedAmount", "", "getTotalPlannedAmount", "()D", "createBudget", "request", "Lcom/ledger/app/data/models/BudgetCreate;", "deleteBudget", "id", "loadBudgets", "app_debug"})
public final class BudgetsViewModel extends androidx.lifecycle.ViewModel {
    @org.jetbrains.annotations.NotNull()
    private final com.ledger.app.data.api.LedgerApiService api = null;
    @org.jetbrains.annotations.NotNull()
    private final androidx.lifecycle.MutableLiveData<com.ledger.app.util.UiState<java.util.List<com.ledger.app.data.models.BudgetOut>>> budgetsState = null;
    @org.jetbrains.annotations.NotNull()
    private final androidx.lifecycle.MutableLiveData<com.ledger.app.util.UiState<com.ledger.app.data.models.BudgetOut>> createState = null;
    @org.jetbrains.annotations.NotNull()
    private final androidx.lifecycle.MutableLiveData<com.ledger.app.util.UiState<kotlin.Unit>> deleteState = null;
    @org.jetbrains.annotations.NotNull()
    private java.util.List<com.ledger.app.data.models.BudgetOut> _budgets;
    
    public BudgetsViewModel(@org.jetbrains.annotations.NotNull()
    com.ledger.app.data.api.LedgerApiService api) {
        super();
    }
    
    @org.jetbrains.annotations.NotNull()
    public final androidx.lifecycle.MutableLiveData<com.ledger.app.util.UiState<java.util.List<com.ledger.app.data.models.BudgetOut>>> getBudgetsState() {
        return null;
    }
    
    @org.jetbrains.annotations.NotNull()
    public final androidx.lifecycle.MutableLiveData<com.ledger.app.util.UiState<com.ledger.app.data.models.BudgetOut>> getCreateState() {
        return null;
    }
    
    @org.jetbrains.annotations.NotNull()
    public final androidx.lifecycle.MutableLiveData<com.ledger.app.util.UiState<kotlin.Unit>> getDeleteState() {
        return null;
    }
    
    public final boolean isEmpty() {
        return false;
    }
    
    public final int getActiveBudgetCount() {
        return 0;
    }
    
    public final double getTotalPlannedAmount() {
        return 0.0;
    }
    
    public final int getTotalLineItems() {
        return 0;
    }
    
    public final void loadBudgets() {
    }
    
    public final void createBudget(@org.jetbrains.annotations.NotNull()
    com.ledger.app.data.models.BudgetCreate request) {
    }
    
    public final void deleteBudget(int id) {
    }
}