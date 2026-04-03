## Sliders (Range Inputs) Overview
Forecasting often relies heavily on interactive scenario building (e.g., adjusting expected inflation, savings rate, or time horizons). A horizontal slider/range component is the most effective UX method for these adjustments.

## Component-Specific Tokens
| Component Token | Web Equivalent | WPF (XAML) Map | Mac (SwiftUI) Map |
| :--- | :--- | :--- | :--- |
| `slider-track-bg`| `bg-slate-200` | `Background="{StaticResource ColorSlate200}"`| `.tint(Theme.Colors.slate200)` (inactive) |
| `slider-fill-bg` | `bg-[#2C4A70]` | `Foreground="{StaticResource ActionPrimaryBrush}"`| `.tint(Theme.Colors.actionPrimary)` |
| `slider-thumb` | `bg-white border-[#2C4A70]` | N/A (Standard WPF control styling) | Native system thumb |

## Cross-Platform Usage Examples

### Web (React/Tailwind)
```jsx
// Web browsers notoriously require custom CSS for standard `<input type="range">`
// Usually implemented via third party libraries like Radix UI or custom CSS rules
<div className="relative w-full h-2 bg-slate-200 rounded-full my-4">
  <div className="absolute top-0 left-0 h-full bg-[#2C4A70] rounded-full" style={{ width: '50%' }}></div>
  <div className="absolute top-1/2 left-1/2 w-4 h-4 bg-white border-2 border-[#2C4A70] rounded-full -translate-x-1/2 -translate-y-1/2 shadow-md cursor-pointer hover:scale-110 transition-transform"></div>
</div>
```

### Windows (WPF XAML)
WPF handles Sliders natively. Building an identical track and thumb requires a specific `ControlTemplate` overriding the WPF `Thumb`, but basic visual mapping works easily via Brushes.
```xml
<Style x:Key="PremiumSlider" TargetType="Slider">
    <Setter Property="Background" Value="{StaticResource ColorSlate200}"/>
    <Setter Property="Foreground" Value="{StaticResource ActionPrimaryBrush}"/>
    <Setter Property="IsSnapToTickEnabled" Value="True"/>
    <!-- Note: Exact visual thumb replication requires a full overridden template -->
</Style>

<!-- In View -->
<StackPanel>
    <TextBlock Text="Retirement Age" Style="{StaticResource TypographyBodySm}" Foreground="{StaticResource TextPrimaryBrush}"/>
    <Slider Style="{StaticResource PremiumSlider}" Minimum="50" Maximum="80" Value="65"/>
</StackPanel>
```

### Mac (SwiftUI)
SwiftUI offers a highly elegant Slider immediately out of the box that requires minimal skinning.
```swift
struct ForecastingSlider: View {
    @Binding var value: Double
    let label: String
    
    var body: some View {
        VStack(alignment: .leading, spacing: .Layout.gapTight) {
            Text(label).font(.Semantic.bodySm)
            Slider(value: $value, in: 50...80)
                .tint(Theme.Colors.actionPrimary) // Colors the filled track
        }
    }
}
```
