-if class com.ledger.app.data.models.GoalOut
-keepnames class com.ledger.app.data.models.GoalOut
-if class com.ledger.app.data.models.GoalOut
-keep class com.ledger.app.data.models.GoalOutJsonAdapter {
    public <init>(com.squareup.moshi.Moshi);
}
-if class com.ledger.app.data.models.GoalOut
-keepnames class kotlin.jvm.internal.DefaultConstructorMarker
-if class com.ledger.app.data.models.GoalOut
-keepclassmembers class com.ledger.app.data.models.GoalOut {
    public synthetic <init>(int,java.lang.String,java.lang.String,java.lang.String,java.lang.String,java.lang.String,java.lang.String,boolean,java.lang.String,double,java.lang.String,java.lang.String,int,kotlin.jvm.internal.DefaultConstructorMarker);
}
