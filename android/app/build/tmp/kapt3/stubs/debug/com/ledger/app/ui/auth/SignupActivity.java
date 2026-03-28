package com.ledger.app.ui.auth;

@kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000>\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0000\n\u0002\u0010 \n\u0002\u0010\u000e\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0010\u0002\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0002\b\u0007\n\u0002\u0010\u000b\n\u0000\u0018\u00002\u00020\u0001B\u0005\u00a2\u0006\u0002\u0010\u0002J\u0010\u0010\n\u001a\u00020\u000b2\u0006\u0010\f\u001a\u00020\rH\u0002J\u0012\u0010\u000e\u001a\u00020\u000b2\b\u0010\u000f\u001a\u0004\u0018\u00010\u0010H\u0014J\b\u0010\u0011\u001a\u00020\u000bH\u0002J\b\u0010\u0012\u001a\u00020\u000bH\u0002J\b\u0010\u0013\u001a\u00020\u000bH\u0002J\u0010\u0010\u0014\u001a\u00020\u000b2\u0006\u0010\u0015\u001a\u00020\u0007H\u0002J\u0010\u0010\u0016\u001a\u00020\u000b2\u0006\u0010\u0017\u001a\u00020\u0018H\u0002R\u000e\u0010\u0003\u001a\u00020\u0004X\u0082.\u00a2\u0006\u0002\n\u0000R\u0014\u0010\u0005\u001a\b\u0012\u0004\u0012\u00020\u00070\u0006X\u0082\u0004\u00a2\u0006\u0002\n\u0000R\u000e\u0010\b\u001a\u00020\tX\u0082.\u00a2\u0006\u0002\n\u0000\u00a8\u0006\u0019"}, d2 = {"Lcom/ledger/app/ui/auth/SignupActivity;", "Landroidx/appcompat/app/AppCompatActivity;", "()V", "binding", "Lcom/ledger/app/databinding/ActivitySignupBinding;", "entityTypes", "", "", "viewModel", "Lcom/ledger/app/ui/auth/SignupViewModel;", "handleSignupSuccess", "", "authResponse", "Lcom/ledger/app/data/models/AuthListResponse;", "onCreate", "savedInstanceState", "Landroid/os/Bundle;", "setupClickListeners", "setupEntityTypeDropdown", "setupObservers", "showError", "message", "showLoading", "loading", "", "app_debug"})
public final class SignupActivity extends androidx.appcompat.app.AppCompatActivity {
    private com.ledger.app.databinding.ActivitySignupBinding binding;
    private com.ledger.app.ui.auth.SignupViewModel viewModel;
    @org.jetbrains.annotations.NotNull()
    private final java.util.List<java.lang.String> entityTypes = null;
    
    public SignupActivity() {
        super();
    }
    
    @java.lang.Override()
    protected void onCreate(@org.jetbrains.annotations.Nullable()
    android.os.Bundle savedInstanceState) {
    }
    
    private final void setupEntityTypeDropdown() {
    }
    
    private final void setupObservers() {
    }
    
    private final void setupClickListeners() {
    }
    
    private final void handleSignupSuccess(com.ledger.app.data.models.AuthListResponse authResponse) {
    }
    
    private final void showLoading(boolean loading) {
    }
    
    private final void showError(java.lang.String message) {
    }
}