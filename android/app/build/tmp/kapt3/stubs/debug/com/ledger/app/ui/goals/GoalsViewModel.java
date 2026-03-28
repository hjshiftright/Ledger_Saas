package com.ledger.app.ui.goals;

@kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000^\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0010 \n\u0002\u0018\u0002\n\u0000\n\u0002\u0010\u0006\n\u0002\b\u0003\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0002\b\u0003\n\u0002\u0010\u0002\n\u0002\b\u0004\n\u0002\u0010\u000b\n\u0002\b\u0007\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0010\b\n\u0002\b\u0002\n\u0002\u0010\u000e\n\u0002\b\u0003\n\u0002\u0010$\n\u0000\u0018\u00002\u00020\u0001B\r\u0012\u0006\u0010\u0002\u001a\u00020\u0003\u00a2\u0006\u0002\u0010\u0004J\u000e\u0010\u001d\u001a\u00020\u00122\u0006\u0010\u001e\u001a\u00020\u001fJ\u000e\u0010 \u001a\u00020\u00122\u0006\u0010!\u001a\u00020\"J\u0006\u0010#\u001a\u00020\u0012J\u0012\u0010$\u001a\u00020%2\b\u0010&\u001a\u0004\u0018\u00010%H\u0002J\"\u0010\'\u001a\u00020\u00122\u0006\u0010!\u001a\u00020\"2\u0012\u0010(\u001a\u000e\u0012\u0004\u0012\u00020%\u0012\u0004\u0012\u00020%0)R\u0014\u0010\u0005\u001a\b\u0012\u0004\u0012\u00020\u00070\u0006X\u0082\u000e\u00a2\u0006\u0002\n\u0000R\u000e\u0010\u0002\u001a\u00020\u0003X\u0082\u0004\u00a2\u0006\u0002\n\u0000R\u0011\u0010\b\u001a\u00020\t8F\u00a2\u0006\u0006\u001a\u0004\b\n\u0010\u000bR\u001d\u0010\f\u001a\u000e\u0012\n\u0012\b\u0012\u0004\u0012\u00020\u00070\u000e0\r\u00a2\u0006\b\n\u0000\u001a\u0004\b\u000f\u0010\u0010R\u001d\u0010\u0011\u001a\u000e\u0012\n\u0012\b\u0012\u0004\u0012\u00020\u00120\u000e0\r\u00a2\u0006\b\n\u0000\u001a\u0004\b\u0013\u0010\u0010R#\u0010\u0014\u001a\u0014\u0012\u0010\u0012\u000e\u0012\n\u0012\b\u0012\u0004\u0012\u00020\u00070\u00060\u000e0\r\u00a2\u0006\b\n\u0000\u001a\u0004\b\u0015\u0010\u0010R\u0011\u0010\u0016\u001a\u00020\u00178F\u00a2\u0006\u0006\u001a\u0004\b\u0016\u0010\u0018R\u0011\u0010\u0019\u001a\u00020\t8F\u00a2\u0006\u0006\u001a\u0004\b\u001a\u0010\u000bR\u001d\u0010\u001b\u001a\u000e\u0012\n\u0012\b\u0012\u0004\u0012\u00020\u00070\u000e0\r\u00a2\u0006\b\n\u0000\u001a\u0004\b\u001c\u0010\u0010\u00a8\u0006*"}, d2 = {"Lcom/ledger/app/ui/goals/GoalsViewModel;", "Landroidx/lifecycle/ViewModel;", "api", "Lcom/ledger/app/data/api/LedgerApiService;", "(Lcom/ledger/app/data/api/LedgerApiService;)V", "_goals", "", "Lcom/ledger/app/data/models/GoalOut;", "averageProgress", "", "getAverageProgress", "()D", "createState", "Landroidx/lifecycle/MutableLiveData;", "Lcom/ledger/app/util/UiState;", "getCreateState", "()Landroidx/lifecycle/MutableLiveData;", "deleteState", "", "getDeleteState", "goalsState", "getGoalsState", "isEmpty", "", "()Z", "totalTargetAmount", "getTotalTargetAmount", "updateState", "getUpdateState", "createGoal", "request", "Lcom/ledger/app/data/models/GoalCreate;", "deleteGoal", "id", "", "loadGoals", "parseErrorBody", "", "errorBody", "updateGoal", "updates", "", "app_debug"})
public final class GoalsViewModel extends androidx.lifecycle.ViewModel {
    @org.jetbrains.annotations.NotNull()
    private final com.ledger.app.data.api.LedgerApiService api = null;
    @org.jetbrains.annotations.NotNull()
    private final androidx.lifecycle.MutableLiveData<com.ledger.app.util.UiState<java.util.List<com.ledger.app.data.models.GoalOut>>> goalsState = null;
    @org.jetbrains.annotations.NotNull()
    private final androidx.lifecycle.MutableLiveData<com.ledger.app.util.UiState<com.ledger.app.data.models.GoalOut>> createState = null;
    @org.jetbrains.annotations.NotNull()
    private final androidx.lifecycle.MutableLiveData<com.ledger.app.util.UiState<kotlin.Unit>> deleteState = null;
    @org.jetbrains.annotations.NotNull()
    private final androidx.lifecycle.MutableLiveData<com.ledger.app.util.UiState<com.ledger.app.data.models.GoalOut>> updateState = null;
    @org.jetbrains.annotations.NotNull()
    private java.util.List<com.ledger.app.data.models.GoalOut> _goals;
    
    public GoalsViewModel(@org.jetbrains.annotations.NotNull()
    com.ledger.app.data.api.LedgerApiService api) {
        super();
    }
    
    @org.jetbrains.annotations.NotNull()
    public final androidx.lifecycle.MutableLiveData<com.ledger.app.util.UiState<java.util.List<com.ledger.app.data.models.GoalOut>>> getGoalsState() {
        return null;
    }
    
    @org.jetbrains.annotations.NotNull()
    public final androidx.lifecycle.MutableLiveData<com.ledger.app.util.UiState<com.ledger.app.data.models.GoalOut>> getCreateState() {
        return null;
    }
    
    @org.jetbrains.annotations.NotNull()
    public final androidx.lifecycle.MutableLiveData<com.ledger.app.util.UiState<kotlin.Unit>> getDeleteState() {
        return null;
    }
    
    @org.jetbrains.annotations.NotNull()
    public final androidx.lifecycle.MutableLiveData<com.ledger.app.util.UiState<com.ledger.app.data.models.GoalOut>> getUpdateState() {
        return null;
    }
    
    public final boolean isEmpty() {
        return false;
    }
    
    public final double getTotalTargetAmount() {
        return 0.0;
    }
    
    public final double getAverageProgress() {
        return 0.0;
    }
    
    public final void loadGoals() {
    }
    
    public final void createGoal(@org.jetbrains.annotations.NotNull()
    com.ledger.app.data.models.GoalCreate request) {
    }
    
    public final void deleteGoal(int id) {
    }
    
    public final void updateGoal(int id, @org.jetbrains.annotations.NotNull()
    java.util.Map<java.lang.String, java.lang.String> updates) {
    }
    
    private final java.lang.String parseErrorBody(java.lang.String errorBody) {
        return null;
    }
}