package com.ledger.app.ui.transactions;

@kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000J\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0010\b\n\u0000\n\u0002\u0010!\n\u0002\u0018\u0002\n\u0000\n\u0002\u0010\u000e\n\u0002\b\u0005\n\u0002\u0010\u000b\n\u0002\b\u0006\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0002\u0010 \n\u0002\b\u0003\n\u0002\u0010\u0002\n\u0002\b\b\u0018\u00002\u00020\u0001B\r\u0012\u0006\u0010\u0002\u001a\u00020\u0003\u00a2\u0006\u0002\u0010\u0004J\u0016\u0010\u001d\u001a\u00020\u001e2\u0006\u0010\u001f\u001a\u00020\u000b2\u0006\u0010 \u001a\u00020\u000bJ\u000e\u0010!\u001a\u00020\u001eH\u0082@\u00a2\u0006\u0002\u0010\"J\u0006\u0010#\u001a\u00020\u001eJ\u000e\u0010$\u001a\u00020\u001eH\u0082@\u00a2\u0006\u0002\u0010\"J\u0006\u0010%\u001a\u00020\u001eR\u000e\u0010\u0005\u001a\u00020\u0006X\u0082D\u00a2\u0006\u0002\n\u0000R\u0014\u0010\u0007\u001a\b\u0012\u0004\u0012\u00020\t0\bX\u0082\u0004\u00a2\u0006\u0002\n\u0000R\u000e\u0010\u0002\u001a\u00020\u0003X\u0082\u0004\u00a2\u0006\u0002\n\u0000R\u0010\u0010\n\u001a\u0004\u0018\u00010\u000bX\u0082\u000e\u00a2\u0006\u0002\n\u0000R\u001e\u0010\r\u001a\u00020\u00062\u0006\u0010\f\u001a\u00020\u0006@BX\u0086\u000e\u00a2\u0006\b\n\u0000\u001a\u0004\b\u000e\u0010\u000fR\u0010\u0010\u0010\u001a\u0004\u0018\u00010\u000bX\u0082\u000e\u00a2\u0006\u0002\n\u0000R\u001e\u0010\u0012\u001a\u00020\u00112\u0006\u0010\f\u001a\u00020\u0011@BX\u0086\u000e\u00a2\u0006\b\n\u0000\u001a\u0004\b\u0013\u0010\u0014R\u001e\u0010\u0015\u001a\u00020\u00062\u0006\u0010\f\u001a\u00020\u0006@BX\u0086\u000e\u00a2\u0006\b\n\u0000\u001a\u0004\b\u0016\u0010\u000fR#\u0010\u0017\u001a\u0014\u0012\u0010\u0012\u000e\u0012\n\u0012\b\u0012\u0004\u0012\u00020\t0\u001a0\u00190\u0018\u00a2\u0006\b\n\u0000\u001a\u0004\b\u001b\u0010\u001c\u00a8\u0006&"}, d2 = {"Lcom/ledger/app/ui/transactions/TransactionsViewModel;", "Landroidx/lifecycle/ViewModel;", "api", "Lcom/ledger/app/data/api/LedgerApiService;", "(Lcom/ledger/app/data/api/LedgerApiService;)V", "PAGE_SIZE", "", "_allTransactions", "", "Lcom/ledger/app/data/models/TransactionOut;", "currentFromDate", "", "<set-?>", "currentOffset", "getCurrentOffset", "()I", "currentToDate", "", "hasMorePages", "getHasMorePages", "()Z", "totalCount", "getTotalCount", "transactionState", "Landroidx/lifecycle/MutableLiveData;", "Lcom/ledger/app/util/UiState;", "", "getTransactionState", "()Landroidx/lifecycle/MutableLiveData;", "filterByDate", "", "fromDate", "toDate", "loadCount", "(Lkotlin/coroutines/Continuation;)Ljava/lang/Object;", "loadMore", "loadPage", "loadTransactions", "app_debug"})
public final class TransactionsViewModel extends androidx.lifecycle.ViewModel {
    @org.jetbrains.annotations.NotNull()
    private final com.ledger.app.data.api.LedgerApiService api = null;
    @org.jetbrains.annotations.NotNull()
    private final androidx.lifecycle.MutableLiveData<com.ledger.app.util.UiState<java.util.List<com.ledger.app.data.models.TransactionOut>>> transactionState = null;
    private int currentOffset = 0;
    private boolean hasMorePages = true;
    private int totalCount = 0;
    @org.jetbrains.annotations.NotNull()
    private final java.util.List<com.ledger.app.data.models.TransactionOut> _allTransactions = null;
    private final int PAGE_SIZE = 20;
    @org.jetbrains.annotations.Nullable()
    private java.lang.String currentFromDate;
    @org.jetbrains.annotations.Nullable()
    private java.lang.String currentToDate;
    
    public TransactionsViewModel(@org.jetbrains.annotations.NotNull()
    com.ledger.app.data.api.LedgerApiService api) {
        super();
    }
    
    @org.jetbrains.annotations.NotNull()
    public final androidx.lifecycle.MutableLiveData<com.ledger.app.util.UiState<java.util.List<com.ledger.app.data.models.TransactionOut>>> getTransactionState() {
        return null;
    }
    
    public final int getCurrentOffset() {
        return 0;
    }
    
    public final boolean getHasMorePages() {
        return false;
    }
    
    public final int getTotalCount() {
        return 0;
    }
    
    public final void loadTransactions() {
    }
    
    public final void loadMore() {
    }
    
    public final void filterByDate(@org.jetbrains.annotations.NotNull()
    java.lang.String fromDate, @org.jetbrains.annotations.NotNull()
    java.lang.String toDate) {
    }
    
    private final java.lang.Object loadPage(kotlin.coroutines.Continuation<? super kotlin.Unit> $completion) {
        return null;
    }
    
    private final java.lang.Object loadCount(kotlin.coroutines.Continuation<? super kotlin.Unit> $completion) {
        return null;
    }
}