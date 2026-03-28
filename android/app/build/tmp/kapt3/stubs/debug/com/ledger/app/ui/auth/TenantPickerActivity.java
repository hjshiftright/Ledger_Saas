package com.ledger.app.ui.auth;

@kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u00002\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0010\u0002\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0010 \n\u0002\u0018\u0002\n\u0000\u0018\u00002\u00020\u0001B\u0005\u00a2\u0006\u0002\u0010\u0002J\b\u0010\u0007\u001a\u00020\bH\u0002J\u0012\u0010\t\u001a\u00020\b2\b\u0010\n\u001a\u0004\u0018\u00010\u000bH\u0014J\u0016\u0010\f\u001a\u00020\b2\f\u0010\r\u001a\b\u0012\u0004\u0012\u00020\u000f0\u000eH\u0002R\u000e\u0010\u0003\u001a\u00020\u0004X\u0082.\u00a2\u0006\u0002\n\u0000R\u000e\u0010\u0005\u001a\u00020\u0006X\u0082.\u00a2\u0006\u0002\n\u0000\u00a8\u0006\u0010"}, d2 = {"Lcom/ledger/app/ui/auth/TenantPickerActivity;", "Landroidx/appcompat/app/AppCompatActivity;", "()V", "binding", "Lcom/ledger/app/databinding/ActivityTenantPickerBinding;", "loginViewModel", "Lcom/ledger/app/ui/auth/LoginViewModel;", "navigateToMain", "", "onCreate", "savedInstanceState", "Landroid/os/Bundle;", "setupRecyclerView", "tenants", "", "Lcom/ledger/app/data/models/TenantInfo;", "app_debug"})
public final class TenantPickerActivity extends androidx.appcompat.app.AppCompatActivity {
    private com.ledger.app.databinding.ActivityTenantPickerBinding binding;
    private com.ledger.app.ui.auth.LoginViewModel loginViewModel;
    
    public TenantPickerActivity() {
        super();
    }
    
    @java.lang.Override()
    protected void onCreate(@org.jetbrains.annotations.Nullable()
    android.os.Bundle savedInstanceState) {
    }
    
    private final void setupRecyclerView(java.util.List<com.ledger.app.data.models.TenantInfo> tenants) {
    }
    
    private final void navigateToMain() {
    }
}