-if class com.ledger.app.data.models.AccountOut
-keepnames class com.ledger.app.data.models.AccountOut
-if class com.ledger.app.data.models.AccountOut
-keep class com.ledger.app.data.models.AccountOutJsonAdapter {
    public <init>(com.squareup.moshi.Moshi);
}
-if class com.ledger.app.data.models.AccountOut
-keepnames class kotlin.jvm.internal.DefaultConstructorMarker
-if class com.ledger.app.data.models.AccountOut
-keepclassmembers class com.ledger.app.data.models.AccountOut {
    public synthetic <init>(java.lang.String,java.lang.String,java.lang.String,java.lang.String,java.lang.String,java.lang.String,java.lang.String,java.lang.String,int,boolean,boolean,boolean,java.lang.String,java.lang.String,int,kotlin.jvm.internal.DefaultConstructorMarker);
}
