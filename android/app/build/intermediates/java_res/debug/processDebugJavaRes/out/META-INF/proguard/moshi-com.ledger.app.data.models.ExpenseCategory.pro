-if class com.ledger.app.data.models.ExpenseCategory
-keepnames class com.ledger.app.data.models.ExpenseCategory
-if class com.ledger.app.data.models.ExpenseCategory
-keep class com.ledger.app.data.models.ExpenseCategoryJsonAdapter {
    public <init>(com.squareup.moshi.Moshi);
}
