package com.ledger.app.data.api;

@kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000*\n\u0002\u0018\u0002\n\u0002\u0010\u0000\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0002\b\u0003\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0010\u0002\n\u0000\b\u00c6\u0002\u0018\u00002\u00020\u0001B\u0007\b\u0002\u00a2\u0006\u0002\u0010\u0002J\u0006\u0010\f\u001a\u00020\u000bJ\u0006\u0010\r\u001a\u00020\u000eR\u0011\u0010\u0003\u001a\u00020\u00048F\u00a2\u0006\u0006\u001a\u0004\b\u0005\u0010\u0006R\u0016\u0010\u0007\u001a\n \t*\u0004\u0018\u00010\b0\bX\u0082\u0004\u00a2\u0006\u0002\n\u0000R\u0010\u0010\n\u001a\u0004\u0018\u00010\u000bX\u0082\u000e\u00a2\u0006\u0002\n\u0000\u00a8\u0006\u000f"}, d2 = {"Lcom/ledger/app/data/api/RetrofitClient;", "", "()V", "api", "Lcom/ledger/app/data/api/LedgerApiService;", "getApi", "()Lcom/ledger/app/data/api/LedgerApiService;", "moshi", "Lcom/squareup/moshi/Moshi;", "kotlin.jvm.PlatformType", "retrofit", "Lretrofit2/Retrofit;", "getInstance", "resetInstance", "", "app_debug"})
public final class RetrofitClient {
    @org.jetbrains.annotations.Nullable()
    private static retrofit2.Retrofit retrofit;
    private static final com.squareup.moshi.Moshi moshi = null;
    @org.jetbrains.annotations.NotNull()
    public static final com.ledger.app.data.api.RetrofitClient INSTANCE = null;
    
    private RetrofitClient() {
        super();
    }
    
    @org.jetbrains.annotations.NotNull()
    public final retrofit2.Retrofit getInstance() {
        return null;
    }
    
    public final void resetInstance() {
    }
    
    @org.jetbrains.annotations.NotNull()
    public final com.ledger.app.data.api.LedgerApiService getApi() {
        return null;
    }
}