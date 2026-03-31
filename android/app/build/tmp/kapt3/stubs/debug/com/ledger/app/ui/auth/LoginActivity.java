package com.ledger.app.ui.auth;

@kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000B\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0000\n\u0002\u0010\u000e\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0010\u0002\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0004\n\u0002\u0010\b\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0002\b\u0006\n\u0002\u0010\u000b\n\u0000\u0018\u00002\u00020\u0001B\u0005\u00a2\u0006\u0002\u0010\u0002J\u0010\u0010\t\u001a\u00020\n2\u0006\u0010\u000b\u001a\u00020\fH\u0002J \u0010\r\u001a\u00020\n2\u0006\u0010\u000e\u001a\u00020\u00062\u0006\u0010\u000f\u001a\u00020\u00062\u0006\u0010\u0010\u001a\u00020\u0011H\u0002J\u0012\u0010\u0012\u001a\u00020\n2\b\u0010\u0013\u001a\u0004\u0018\u00010\u0014H\u0014J\b\u0010\u0015\u001a\u00020\nH\u0002J\b\u0010\u0016\u001a\u00020\nH\u0002J\u0010\u0010\u0017\u001a\u00020\n2\u0006\u0010\u0018\u001a\u00020\u0006H\u0002J\u0010\u0010\u0019\u001a\u00020\n2\u0006\u0010\u001a\u001a\u00020\u001bH\u0002R\u000e\u0010\u0003\u001a\u00020\u0004X\u0082.\u00a2\u0006\u0002\n\u0000R\u000e\u0010\u0005\u001a\u00020\u0006X\u0082\u000e\u00a2\u0006\u0002\n\u0000R\u000e\u0010\u0007\u001a\u00020\bX\u0082.\u00a2\u0006\u0002\n\u0000\u00a8\u0006\u001c"}, d2 = {"Lcom/ledger/app/ui/auth/LoginActivity;", "Landroidx/appcompat/app/AppCompatActivity;", "()V", "binding", "Lcom/ledger/app/databinding/ActivityLoginBinding;", "pendingEmail", "", "viewModel", "Lcom/ledger/app/ui/auth/LoginViewModel;", "handleLoginSuccess", "", "authResponse", "Lcom/ledger/app/data/models/AuthListResponse;", "navigateToWebApp", "token", "email", "userId", "", "onCreate", "savedInstanceState", "Landroid/os/Bundle;", "setupClickListeners", "setupObservers", "showError", "message", "showLoading", "loading", "", "app_debug"})
public final class LoginActivity extends androidx.appcompat.app.AppCompatActivity {
    private com.ledger.app.databinding.ActivityLoginBinding binding;
    private com.ledger.app.ui.auth.LoginViewModel viewModel;
    @org.jetbrains.annotations.NotNull()
    private java.lang.String pendingEmail = "";
    
    public LoginActivity() {
        super();
    }
    
    @java.lang.Override()
    protected void onCreate(@org.jetbrains.annotations.Nullable()
    android.os.Bundle savedInstanceState) {
    }
    
    private final void setupObservers() {
    }
    
    private final void setupClickListeners() {
    }
    
    private final void handleLoginSuccess(com.ledger.app.data.models.AuthListResponse authResponse) {
    }
    
    private final void navigateToWebApp(java.lang.String token, java.lang.String email, int userId) {
    }
    
    private final void showLoading(boolean loading) {
    }
    
    private final void showError(java.lang.String message) {
    }
}