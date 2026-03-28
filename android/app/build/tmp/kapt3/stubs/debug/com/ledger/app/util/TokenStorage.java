package com.ledger.app.util;

@kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000 \n\u0002\u0018\u0002\n\u0002\u0010\u0000\n\u0000\n\u0002\u0010\u0002\n\u0000\n\u0002\u0010\u000e\n\u0002\b\u0004\n\u0002\u0010\b\n\u0002\b\u0002\bf\u0018\u00002\u00020\u0001J\b\u0010\u0002\u001a\u00020\u0003H&J\n\u0010\u0004\u001a\u0004\u0018\u00010\u0005H&J\u0010\u0010\u0006\u001a\u00020\u00032\u0006\u0010\u0007\u001a\u00020\u0005H&J \u0010\b\u001a\u00020\u00032\u0006\u0010\u0007\u001a\u00020\u00052\u0006\u0010\t\u001a\u00020\n2\u0006\u0010\u000b\u001a\u00020\u0005H&\u00a8\u0006\f"}, d2 = {"Lcom/ledger/app/util/TokenStorage;", "", "clearToken", "", "getToken", "", "savePreToken", "token", "saveToken", "userId", "", "tenantId", "app_debug"})
public abstract interface TokenStorage {
    
    @org.jetbrains.annotations.Nullable()
    public abstract java.lang.String getToken();
    
    public abstract void savePreToken(@org.jetbrains.annotations.NotNull()
    java.lang.String token);
    
    public abstract void saveToken(@org.jetbrains.annotations.NotNull()
    java.lang.String token, int userId, @org.jetbrains.annotations.NotNull()
    java.lang.String tenantId);
    
    public abstract void clearToken();
}