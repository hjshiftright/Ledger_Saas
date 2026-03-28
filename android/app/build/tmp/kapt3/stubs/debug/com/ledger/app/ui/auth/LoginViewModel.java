package com.ledger.app.ui.auth;

@kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000B\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0002\b\u0003\n\u0002\u0010\u000b\n\u0002\b\u0003\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0010\u0002\n\u0000\n\u0002\u0010\u000e\n\u0002\b\u0006\u0018\u00002\u00020\u0001B\r\u0012\u0006\u0010\u0002\u001a\u00020\u0003\u00a2\u0006\u0002\u0010\u0004J\u0016\u0010\u0013\u001a\u00020\u00142\u0006\u0010\u0015\u001a\u00020\u00162\u0006\u0010\u0017\u001a\u00020\u0016J\u0012\u0010\u0018\u001a\u00020\u00162\b\u0010\u0019\u001a\u0004\u0018\u00010\u0016H\u0002J\u000e\u0010\u001a\u001a\u00020\u00142\u0006\u0010\u001b\u001a\u00020\u0016R\u0010\u0010\u0005\u001a\u0004\u0018\u00010\u0006X\u0082\u000e\u00a2\u0006\u0002\n\u0000R\u000e\u0010\u0002\u001a\u00020\u0003X\u0082\u0004\u00a2\u0006\u0002\n\u0000R\u001d\u0010\u0007\u001a\u000e\u0012\n\u0012\b\u0012\u0004\u0012\u00020\u00060\t0\b\u00a2\u0006\b\n\u0000\u001a\u0004\b\n\u0010\u000bR\u0011\u0010\f\u001a\u00020\r8F\u00a2\u0006\u0006\u001a\u0004\b\u000e\u0010\u000fR\u001d\u0010\u0010\u001a\u000e\u0012\n\u0012\b\u0012\u0004\u0012\u00020\u00110\t0\b\u00a2\u0006\b\n\u0000\u001a\u0004\b\u0012\u0010\u000b\u00a8\u0006\u001c"}, d2 = {"Lcom/ledger/app/ui/auth/LoginViewModel;", "Landroidx/lifecycle/ViewModel;", "api", "Lcom/ledger/app/data/api/LedgerApiService;", "(Lcom/ledger/app/data/api/LedgerApiService;)V", "_authResponse", "Lcom/ledger/app/data/models/AuthListResponse;", "loginState", "Landroidx/lifecycle/MutableLiveData;", "Lcom/ledger/app/util/UiState;", "getLoginState", "()Landroidx/lifecycle/MutableLiveData;", "shouldAutoSelectTenant", "", "getShouldAutoSelectTenant", "()Z", "tenantState", "Lcom/ledger/app/data/models/TokenResponse;", "getTenantState", "login", "", "email", "", "password", "parseErrorBody", "errorBody", "selectTenant", "tenantId", "app_debug"})
public final class LoginViewModel extends androidx.lifecycle.ViewModel {
    @org.jetbrains.annotations.NotNull()
    private final com.ledger.app.data.api.LedgerApiService api = null;
    @org.jetbrains.annotations.NotNull()
    private final androidx.lifecycle.MutableLiveData<com.ledger.app.util.UiState<com.ledger.app.data.models.AuthListResponse>> loginState = null;
    @org.jetbrains.annotations.NotNull()
    private final androidx.lifecycle.MutableLiveData<com.ledger.app.util.UiState<com.ledger.app.data.models.TokenResponse>> tenantState = null;
    @org.jetbrains.annotations.Nullable()
    private com.ledger.app.data.models.AuthListResponse _authResponse;
    
    public LoginViewModel(@org.jetbrains.annotations.NotNull()
    com.ledger.app.data.api.LedgerApiService api) {
        super();
    }
    
    @org.jetbrains.annotations.NotNull()
    public final androidx.lifecycle.MutableLiveData<com.ledger.app.util.UiState<com.ledger.app.data.models.AuthListResponse>> getLoginState() {
        return null;
    }
    
    @org.jetbrains.annotations.NotNull()
    public final androidx.lifecycle.MutableLiveData<com.ledger.app.util.UiState<com.ledger.app.data.models.TokenResponse>> getTenantState() {
        return null;
    }
    
    public final boolean getShouldAutoSelectTenant() {
        return false;
    }
    
    public final void login(@org.jetbrains.annotations.NotNull()
    java.lang.String email, @org.jetbrains.annotations.NotNull()
    java.lang.String password) {
    }
    
    public final void selectTenant(@org.jetbrains.annotations.NotNull()
    java.lang.String tenantId) {
    }
    
    private final java.lang.String parseErrorBody(java.lang.String errorBody) {
        return null;
    }
}