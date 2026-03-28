-if class com.ledger.app.data.models.BudgetItemCreate
-keepnames class com.ledger.app.data.models.BudgetItemCreate
-if class com.ledger.app.data.models.BudgetItemCreate
-keep class com.ledger.app.data.models.BudgetItemCreateJsonAdapter {
    public <init>(com.squareup.moshi.Moshi);
}
-if class com.ledger.app.data.models.BudgetItemCreate
-keepnames class kotlin.jvm.internal.DefaultConstructorMarker
-if class com.ledger.app.data.models.BudgetItemCreate
-keepclassmembers class com.ledger.app.data.models.BudgetItemCreate {
    public synthetic <init>(java.lang.String,java.lang.String,java.lang.String,int,kotlin.jvm.internal.DefaultConstructorMarker);
}
