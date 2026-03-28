package com.ledger.app.util;

@kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u00006\n\u0002\u0018\u0002\n\u0002\u0010\u0000\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0002\b\u0005\n\u0002\u0010\u0002\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0010\u000e\n\u0000\n\u0002\u0010\u000b\n\u0002\b\u0004\n\u0002\u0010\b\n\u0002\b\u0002\b\u00c6\u0002\u0018\u00002\u00020\u0001B\u0007\b\u0002\u00a2\u0006\u0002\u0010\u0002J\u0012\u0010\t\u001a\u00020\n2\n\b\u0002\u0010\u000b\u001a\u0004\u0018\u00010\fJ\b\u0010\r\u001a\u0004\u0018\u00010\u000eJ\u0006\u0010\u000f\u001a\u00020\u0010J\u000e\u0010\u0011\u001a\u00020\n2\u0006\u0010\u0012\u001a\u00020\u000eJ*\u0010\u0013\u001a\u00020\n2\n\b\u0002\u0010\u000b\u001a\u0004\u0018\u00010\f2\u0006\u0010\u0012\u001a\u00020\u000e2\u0006\u0010\u0014\u001a\u00020\u00152\u0006\u0010\u0016\u001a\u00020\u000eR\u001c\u0010\u0003\u001a\u0004\u0018\u00010\u0004X\u0086\u000e\u00a2\u0006\u000e\n\u0000\u001a\u0004\b\u0005\u0010\u0006\"\u0004\b\u0007\u0010\b\u00a8\u0006\u0017"}, d2 = {"Lcom/ledger/app/util/TokenManager;", "", "()V", "storage", "Lcom/ledger/app/util/TokenStorage;", "getStorage", "()Lcom/ledger/app/util/TokenStorage;", "setStorage", "(Lcom/ledger/app/util/TokenStorage;)V", "clearToken", "", "context", "Landroid/content/Context;", "getToken", "", "isLoggedIn", "", "savePreToken", "token", "saveToken", "userId", "", "tenantId", "app_debug"})
public final class TokenManager {
    @org.jetbrains.annotations.Nullable()
    private static com.ledger.app.util.TokenStorage storage;
    @org.jetbrains.annotations.NotNull()
    public static final com.ledger.app.util.TokenManager INSTANCE = null;
    
    private TokenManager() {
        super();
    }
    
    @org.jetbrains.annotations.Nullable()
    public final com.ledger.app.util.TokenStorage getStorage() {
        return null;
    }
    
    public final void setStorage(@org.jetbrains.annotations.Nullable()
    com.ledger.app.util.TokenStorage p0) {
    }
    
    @org.jetbrains.annotations.Nullable()
    public final java.lang.String getToken() {
        return null;
    }
    
    public final void savePreToken(@org.jetbrains.annotations.NotNull()
    java.lang.String token) {
    }
    
    public final void saveToken(@org.jetbrains.annotations.Nullable()
    android.content.Context context, @org.jetbrains.annotations.NotNull()
    java.lang.String token, int userId, @org.jetbrains.annotations.NotNull()
    java.lang.String tenantId) {
    }
    
    public final void clearToken(@org.jetbrains.annotations.Nullable()
    android.content.Context context) {
    }
    
    public final boolean isLoggedIn() {
        return false;
    }
}