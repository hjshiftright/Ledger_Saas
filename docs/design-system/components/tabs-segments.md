## Tabs & Segments Overview
Scenario planning ("Aggressive" vs "Base" vs "Conservative") typically requires switching entire data contexts without navigating away from the dashboard. This demands Tabs (standard underline) or Segmented Controls (pill forms).

## Component-Specific Tokens
| Component Token | Web Equivalent | WPF (XAML) Map | Mac (SwiftUI) Map |
| :--- | :--- | :--- | :--- |
| `tab-bg-active` | `bg-white shadow` | `Background="White"` | `.background(Color.white)` |
| `tab-bg-inactive`| `bg-slate-100` | `Background="{StaticResource ColorSlate100}"`| `.background(Theme.Colors.slate100)` |
| `tab-text-active`| `text-[#2C4A70]`| `Foreground="{StaticResource ActionPrimaryBrush}"`| `.foregroundColor(Theme.Colors.actionPrimary)` |
| `tab-text-inactive`|`text-slate-500`| `Foreground="{StaticResource ColorSlate500}"`| `.foregroundColor(Theme.Colors.slate500)` |

## Cross-Platform Usage Examples

### Web (React/Tailwind)
```jsx
// Segmented Pill Control
<div className="flex bg-slate-100 p-1 rounded-xl">
  <button className="flex-1 py-1.5 px-4 rounded-lg bg-white shadow text-[#2C4A70] text-sm font-bold">
    Base
  </button>
  <button className="flex-1 py-1.5 px-4 rounded-lg text-slate-500 text-sm font-semibold hover:text-slate-700">
    Aggressive
  </button>
</div>
```

### Windows (WPF XAML)
Building a segmented control out of standard WPF RadioButtons allows seamless state binding.
```xml
<!-- Segmented RadioButton Style -->
<Style x:Key="SegmentRadioButton" TargetType="RadioButton">
    <Setter Property="Template">
        <Setter.Value>
            <ControlTemplate TargetType="RadioButton">
                <Border x:Name="border" Background="Transparent" CornerRadius="8" Padding="16,6">
                    <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center"/>
                </Border>
                <ControlTemplate.Triggers>
                    <!-- Active State -->
                    <Trigger Property="IsChecked" Value="True">
                        <Setter TargetName="border" Property="Background" Value="White"/>
                        <Setter TargetName="border" Property="Effect" Value="{StaticResource ShadowBase}"/>
                        <Setter Property="Foreground" Value="{StaticResource ActionPrimaryBrush}"/>
                        <Setter Property="FontWeight" Value="Bold"/>
                    </Trigger>
                    <!-- Inactive State -->
                    <Trigger Property="IsChecked" Value="False">
                        <Setter Property="Foreground" Value="{StaticResource ColorSlate500}"/>
                        <Setter Property="FontWeight" Value="SemiBold"/>
                    </Trigger>
                </ControlTemplate.Triggers>
            </ControlTemplate>
        </Setter.Value>
    </Setter>
</Style>

<!-- In View -->
<Border Background="{StaticResource ColorSlate100}" CornerRadius="12" Padding="4">
    <Grid>
        <Grid.ColumnDefinitions>
            <ColumnDefinition Width="*"/>
            <ColumnDefinition Width="*"/>
        </Grid.ColumnDefinitions>
        <RadioButton Grid.Column="0" Content="Base" IsChecked="True" Style="{StaticResource SegmentRadioButton}"/>
        <RadioButton Grid.Column="1" Content="Aggressive" Style="{StaticResource SegmentRadioButton}"/>
    </Grid>
</Border>
```

### Mac (SwiftUI)
SwiftUI handles segmented tabs flawlessly combining `.pickerStyle(.segmented)`.
```swift
enum Scenario: String, CaseIterable {
    case base = "Base"
    case aggressive = "Aggressive"
}

struct ScenarioPicker: View {
    @State private var selection: Scenario = .base
    
    var body: some View {
        Picker("Forecast Scenario", selection: $selection) {
            ForEach(Scenario.allCases, id: \.self) { scenario in
                Text(scenario.rawValue).tag(scenario)
            }
        }
        .pickerStyle(.segmented)
        .padding()
        // Note: Changing segmented picker explicit font colors requires deeper Introspection in SwiftUI or rebuilding a custom HStack pill selector like the WPF example.
    }
}
```
