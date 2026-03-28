-if class com.ledger.app.data.models.GoalCreate
-keepnames class com.ledger.app.data.models.GoalCreate
-if class com.ledger.app.data.models.GoalCreate
-keep class com.ledger.app.data.models.GoalCreateJsonAdapter {
    public <init>(com.squareup.moshi.Moshi);
}
-if class com.ledger.app.data.models.GoalCreate
-keepnames class kotlin.jvm.internal.DefaultConstructorMarker
-if class com.ledger.app.data.models.GoalCreate
-keepclassmembers class com.ledger.app.data.models.GoalCreate {
    public synthetic <init>(java.lang.String,java.lang.String,java.lang.String,java.lang.String,java.lang.String,java.lang.String,java.lang.String,java.lang.String,int,kotlin.jvm.internal.DefaultConstructorMarker);
}
