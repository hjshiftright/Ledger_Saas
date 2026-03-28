-if class com.ledger.app.data.models.TransactionLine
-keepnames class com.ledger.app.data.models.TransactionLine
-if class com.ledger.app.data.models.TransactionLine
-keep class com.ledger.app.data.models.TransactionLineJsonAdapter {
    public <init>(com.squareup.moshi.Moshi);
}
-if class com.ledger.app.data.models.TransactionLine
-keepnames class kotlin.jvm.internal.DefaultConstructorMarker
-if class com.ledger.app.data.models.TransactionLine
-keepclassmembers class com.ledger.app.data.models.TransactionLine {
    public synthetic <init>(int,java.lang.String,java.lang.String,java.lang.String,java.lang.String,java.lang.String,int,kotlin.jvm.internal.DefaultConstructorMarker);
}
