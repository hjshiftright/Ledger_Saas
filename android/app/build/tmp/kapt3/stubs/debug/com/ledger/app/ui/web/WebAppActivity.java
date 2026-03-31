package com.ledger.app.ui.web;

@kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u00006\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0000\n\u0002\u0010\u000b\n\u0000\n\u0002\u0010\u0002\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0003\n\u0002\u0010\u000e\n\u0002\b\u0002\n\u0002\u0010\b\n\u0002\b\u0002\u0018\u0000 \u00122\u00020\u0001:\u0001\u0012B\u0005\u00a2\u0006\u0002\u0010\u0002J\u0012\u0010\u0007\u001a\u00020\b2\b\u0010\t\u001a\u0004\u0018\u00010\nH\u0014J\b\u0010\u000b\u001a\u00020\bH\u0002J \u0010\f\u001a\u00020\b2\u0006\u0010\r\u001a\u00020\u000e2\u0006\u0010\u000f\u001a\u00020\u000e2\u0006\u0010\u0010\u001a\u00020\u0011H\u0002R\u000e\u0010\u0003\u001a\u00020\u0004X\u0082.\u00a2\u0006\u0002\n\u0000R\u000e\u0010\u0005\u001a\u00020\u0006X\u0082\u000e\u00a2\u0006\u0002\n\u0000\u00a8\u0006\u0013"}, d2 = {"Lcom/ledger/app/ui/web/WebAppActivity;", "Landroidx/appcompat/app/AppCompatActivity;", "()V", "binding", "Lcom/ledger/app/databinding/ActivityWebAppBinding;", "tokenInjected", "", "onCreate", "", "savedInstanceState", "Landroid/os/Bundle;", "setupBackNavigation", "setupWebView", "token", "", "email", "userId", "", "Companion", "app_debug"})
public final class WebAppActivity extends androidx.appcompat.app.AppCompatActivity {
    private com.ledger.app.databinding.ActivityWebAppBinding binding;
    private boolean tokenInjected = false;
    @org.jetbrains.annotations.NotNull()
    public static final java.lang.String EXTRA_TOKEN = "token";
    @org.jetbrains.annotations.NotNull()
    public static final java.lang.String EXTRA_EMAIL = "email";
    @org.jetbrains.annotations.NotNull()
    public static final java.lang.String EXTRA_USER_ID = "user_id";
    @org.jetbrains.annotations.NotNull()
    public static final com.ledger.app.ui.web.WebAppActivity.Companion Companion = null;
    
    public WebAppActivity() {
        super();
    }
    
    @java.lang.Override()
    protected void onCreate(@org.jetbrains.annotations.Nullable()
    android.os.Bundle savedInstanceState) {
    }
    
    private final void setupWebView(java.lang.String token, java.lang.String email, int userId) {
    }
    
    private final void setupBackNavigation() {
    }
    
    @kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000\u0014\n\u0002\u0018\u0002\n\u0002\u0010\u0000\n\u0002\b\u0002\n\u0002\u0010\u000e\n\u0002\b\u0003\b\u0086\u0003\u0018\u00002\u00020\u0001B\u0007\b\u0002\u00a2\u0006\u0002\u0010\u0002R\u000e\u0010\u0003\u001a\u00020\u0004X\u0086T\u00a2\u0006\u0002\n\u0000R\u000e\u0010\u0005\u001a\u00020\u0004X\u0086T\u00a2\u0006\u0002\n\u0000R\u000e\u0010\u0006\u001a\u00020\u0004X\u0086T\u00a2\u0006\u0002\n\u0000\u00a8\u0006\u0007"}, d2 = {"Lcom/ledger/app/ui/web/WebAppActivity$Companion;", "", "()V", "EXTRA_EMAIL", "", "EXTRA_TOKEN", "EXTRA_USER_ID", "app_debug"})
    public static final class Companion {
        
        private Companion() {
            super();
        }
    }
}