-if class com.ledger.app.data.models.BalanceSheetNode
-keepnames class com.ledger.app.data.models.BalanceSheetNode
-if class com.ledger.app.data.models.BalanceSheetNode
-keep class com.ledger.app.data.models.BalanceSheetNodeJsonAdapter {
    public <init>(com.squareup.moshi.Moshi);
}
-if class com.ledger.app.data.models.BalanceSheetNode
-keepnames class kotlin.jvm.internal.DefaultConstructorMarker
-if class com.ledger.app.data.models.BalanceSheetNode
-keepclassmembers class com.ledger.app.data.models.BalanceSheetNode {
    public synthetic <init>(java.lang.String,java.lang.String,java.lang.String,java.lang.String,java.util.List,int,kotlin.jvm.internal.DefaultConstructorMarker);
}
