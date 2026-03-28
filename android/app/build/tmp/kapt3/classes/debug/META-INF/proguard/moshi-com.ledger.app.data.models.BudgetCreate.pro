-if class com.ledger.app.data.models.BudgetCreate
-keepnames class com.ledger.app.data.models.BudgetCreate
-if class com.ledger.app.data.models.BudgetCreate
-keep class com.ledger.app.data.models.BudgetCreateJsonAdapter {
    public <init>(com.squareup.moshi.Moshi);
}
-if class com.ledger.app.data.models.BudgetCreate
-keepnames class kotlin.jvm.internal.DefaultConstructorMarker
-if class com.ledger.app.data.models.BudgetCreate
-keepclassmembers class com.ledger.app.data.models.BudgetCreate {
    public synthetic <init>(java.lang.String,java.lang.String,java.lang.String,java.lang.String,java.util.List,int,kotlin.jvm.internal.DefaultConstructorMarker);
}
