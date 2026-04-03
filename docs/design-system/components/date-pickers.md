## Date Pickers Overview
Financial forecasting is heavily timeline-bound. Selecting birth dates, retirement horizons, or viewing historical data ranges involves Date Pickers. The web typically pairs vanilla HTML date inputs with custom component wrappers to ensure cross-browser consistency.

## Component-Specific Tokens
| Component Token | Web Equivalent | WPF (XAML) Map | Mac (SwiftUI) Map |
| :--- | :--- | :--- | :--- |
| `date-input-bg` | `bg-white` | `Background="White"` | `.background(Color.white)` |
| `date-calendar-bg`| `bg-white shadow-xl`| `Background="White"` / `Effect="{StaticResource ShadowLarge}"`| `.background(Color.white)` / `.shadow(radius: 15)` |
| `date-selected` | `bg-[#2C4A70] text-white`| `Background="{StaticResource ActionPrimaryBrush}"`| `.accentColor(Theme.Colors.actionPrimary)` |

## Cross-Platform Usage Examples

### Web (React)
```jsx
// Native HTML5 Wrapper
<div className="relative">
  <input 
    type="date" 
    className="w-full px-4 py-3 border border-slate-200 rounded-lg text-slate-900 focus:border-[#2C4A70] outline-none" 
  />
</div>
```

### Windows (WPF XAML)
WPF contains a native `DatePicker` control. To style it appropriately to the design system, you override the primitive visual state colors to match the brand.
```xml
<!-- Native WPF Component styled roughly to match Inputs -->
<Style x:Key="PremiumDatePicker" TargetType="DatePicker">
    <Setter Property="Background" Value="White"/>
    <Setter Property="BorderBrush" Value="{StaticResource ColorSlate200}"/>
    <Setter Property="BorderThickness" Value="1"/>
    <!-- Note: Further ControlTemplate overrides are required to target the interior Calendar popup (CalendarStyle) and rounding the outer borders -->
</Style>

<!-- In View -->
<DatePicker Style="{StaticResource PremiumDatePicker}" SelectedDate="{Binding RetirementDate}" />
```

### Mac (SwiftUI)
SwiftUI handles DatePickers robustly and automatically renders native calendar flyouts. Styling is mostly limited to `.accentColor` targeting.
```swift
struct CustomDatePicker: View {
    @Binding var date: Date
    let title: String
    
    var body: some View {
        DatePicker(title, selection: $date, displayedComponents: .date)
            .datePickerStyle(.compact) // Renders the standard macOS contextual date string with a popup calendar
            .tint(Theme.Colors.actionPrimary) // Colors the calendar selections
            .padding(.horizontal, 16)
            .padding(.vertical, 8)
            .background(Color.white)
            .cornerRadius(8)
            .overlay(RoundedRectangle(cornerRadius: 8).stroke(Theme.Colors.slate200))
    }
}
```
