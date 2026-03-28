-if class com.ledger.app.data.models.BudgetOut
-keepnames class com.ledger.app.data.models.BudgetOut
-if class com.ledger.app.data.models.BudgetOut
-keep class com.ledger.app.data.models.BudgetOutJsonAdapter {
    public <init>(com.squareup.moshi.Moshi);
}
-if class com.ledger.app.data.models.BudgetOut
-keepnames class kotlin.jvm.internal.DefaultConstructorMarker
-if class com.ledger.app.data.models.BudgetOut
-keepclassmembers class com.ledger.app.data.models.BudgetOut {
    public synthetic <init>(int,java.lang.String,java.lang.String,java.lang.String,java.lang.String,boolean,java.util.List,int,kotlin.jvm.internal.DefaultConstructorMarker);
}
