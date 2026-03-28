-if class com.ledger.app.data.models.BudgetItemOut
-keepnames class com.ledger.app.data.models.BudgetItemOut
-if class com.ledger.app.data.models.BudgetItemOut
-keep class com.ledger.app.data.models.BudgetItemOutJsonAdapter {
    public <init>(com.squareup.moshi.Moshi);
}
-if class com.ledger.app.data.models.BudgetItemOut
-keepnames class kotlin.jvm.internal.DefaultConstructorMarker
-if class com.ledger.app.data.models.BudgetItemOut
-keepclassmembers class com.ledger.app.data.models.BudgetItemOut {
    public synthetic <init>(int,int,java.lang.String,java.lang.String,java.lang.String,java.lang.String,int,kotlin.jvm.internal.DefaultConstructorMarker);
}
