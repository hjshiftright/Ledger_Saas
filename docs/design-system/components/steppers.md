## Wizards & Steppers Overview
The application handles bulk configuration (e.g. initial onboarding) via Wizard interfaces. Navigating multi-page setups requires Steppers indicating "Step 2 of 4", linking horizontal steps linearly with active/inactive states.

## Component-Specific Tokens
| Component Token | Web Equivalent | WPF (XAML) Map | Mac (SwiftUI) Map |
| :--- | :--- | :--- | :--- |
| `step-active-bg` | `bg-[#2C4A70]` | `Background="{StaticResource ActionPrimaryBrush}"`| `.background(Theme.Colors.actionPrimary)` |
| `step-inactive-bg`| `bg-slate-200` | `Background="{StaticResource ColorSlate200}"`| `.background(Theme.Colors.slate200)` |
| `step-connector` | `h-1 bg-slate-200` | `Height="4" Background="{StaticResource ColorSlate200}"`| `Frame(height: 4).background(Theme.Colors.slate200)`|

## Cross-Platform Usage Examples

### Web (React/Tailwind)
```jsx
<div className="flex items-center w-full max-w-sm mx-auto mb-8">
  <div className="w-8 h-8 rounded-full bg-[#2C4A70] text-white flex items-center justify-center font-bold">1</div>
  <div className="flex-1 h-1 bg-[#2C4A70]"></div>
  <div className="w-8 h-8 rounded-full border-2 border-[#2C4A70] text-[#2C4A70] bg-white flex items-center justify-center font-bold">2</div>
  <div className="flex-1 h-1 bg-slate-200"></div>
  <div className="w-8 h-8 rounded-full bg-slate-200 text-slate-500 flex items-center justify-center font-bold">3</div>
</div>
```

### Windows (WPF XAML)
Because WPF lacks a default Stepper module natively, combining standard Grids with dynamic visual state properties executes the sequence robustly.
```xml
<!-- In View Wrapper -->
<Grid>
    <Grid.ColumnDefinitions>
        <ColumnDefinition Width="Auto"/>
        <ColumnDefinition Width="*"/>
        <ColumnDefinition Width="Auto"/>
    </Grid.ColumnDefinitions>
    
    <!-- Active Step 1 -->
    <Border Grid.Column="0" Width="32" Height="32" CornerRadius="16" Background="{StaticResource ActionPrimaryBrush}">
        <TextBlock Text="1" Foreground="White" VerticalAlignment="Center" HorizontalAlignment="Center" FontWeight="Bold"/>
    </Border>
    
    <!-- Active Connector -->
    <Border Grid.Column="1" Height="4" Background="{StaticResource ActionPrimaryBrush}" VerticalAlignment="Center"/>
    
    <!-- Current Step 2 -->
    <Border Grid.Column="2" Width="32" Height="32" CornerRadius="16" Background="White" BorderBrush="{StaticResource ActionPrimaryBrush}" BorderThickness="2">
        <TextBlock Text="2" Foreground="{StaticResource ActionPrimaryBrush}" VerticalAlignment="Center" HorizontalAlignment="Center" FontWeight="Bold"/>
    </Border>
</Grid>
```

### Mac (SwiftUI)
SwiftUI handles uniform layouts perfectly via `HStack`.
```swift
struct StepperView: View {
    let currentStep: Int
    
    var body: some View {
        HStack(spacing: 0) {
            // Step 1: Active
            Circle()
                .fill(currentStep >= 1 ? Theme.Colors.actionPrimary : Theme.Colors.slate200)
                .frame(width: 32, height: 32)
                .overlay(Text("1").foregroundColor(.white).font(.headline))
                
            // Connector
            Rectangle()
                .fill(currentStep >= 2 ? Theme.Colors.actionPrimary : Theme.Colors.slate200)
                .frame(height: 4)
                
            // Step 2: Inactive mapped conditionally...
        }
        .padding(.horizontal)
    }
}
```
