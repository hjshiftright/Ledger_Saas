-if class com.ledger.app.data.models.TransactionOut
-keepnames class com.ledger.app.data.models.TransactionOut
-if class com.ledger.app.data.models.TransactionOut
-keep class com.ledger.app.data.models.TransactionOutJsonAdapter {
    public <init>(com.squareup.moshi.Moshi);
}
-if class com.ledger.app.data.models.TransactionOut
-keepnames class kotlin.jvm.internal.DefaultConstructorMarker
-if class com.ledger.app.data.models.TransactionOut
-keepclassmembers class com.ledger.app.data.models.TransactionOut {
    public synthetic <init>(int,java.lang.String,java.lang.String,java.lang.String,java.lang.String,boolean,java.lang.String,java.util.List,int,kotlin.jvm.internal.DefaultConstructorMarker);
}
