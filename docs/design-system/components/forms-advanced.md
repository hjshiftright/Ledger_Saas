## Advanced Forms Overview
Beyond standard text inputs, data-dense applications require ComboBoxes (Selects), Checkboxes, and Toggle Switches. These must share the same focus rings and padding behaviors as our base inputs to remain cohesive.

## Component-Specific Tokens
| Component Token | Web Equivalent | WPF (XAML) Map | Mac (SwiftUI) Map |
| :--- | :--- | :--- | :--- |
| `toggle-active-bg`| `bg-[#2C4A70]` | `Background="{StaticResource ActionPrimaryBrush}"`| `.tint(Theme.Colors.actionPrimary)` |
| `toggle-inactive-bg`| `bg-slate-200` | `Background="{StaticResource ColorSlate200}"`| N/A (Handled natively) |
| `select-border` | `border-slate-200`| `BorderBrush="{StaticResource ColorSlate200}"`| N/A (Handled natively) |
| `checkbox-radius` | `rounded` (4px) | `CornerRadius="4"` | `.cornerRadius(4)` |

## Cross-Platform Usage Examples

### Web (React/Tailwind)
```jsx
// Native Select Approach
<select className="px-4 py-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-[#2C4A70]/20 outline-none w-full bg-white">
  <option value="1">Option 1</option>
</select>
```

### Windows (WPF XAML)
WPF `ComboBox` and `<ToggleButton>` require distinct ControlTemplates. Below is a structural concept mimicking our input fields for a ComboBox.
```xml
<!-- Advanced ComboBox Styling mimicking the base Input -->
<Style x:Key="PremiumComboBox" TargetType="ComboBox">
    <Setter Property="Padding" Value="16,12"/>
    <Setter Property="Background" Value="White"/>
    <Setter Property="BorderBrush" Value="{StaticResource ColorSlate200}"/>
    <Setter Property="BorderThickness" Value="1"/>
    <!-- Note: A complete ControlTemplate is required to round corners of a ComboBox in WPF and style the DropDown popup, often using a ToggleButton as the host. -->
</Style>

<!-- Standard CheckBox styled with our colors -->
<Style x:Key="PremiumCheckBox" TargetType="CheckBox">
    <Setter Property="Background" Value="White"/>
    <Setter Property="BorderBrush" Value="{StaticResource ColorSlate200}"/>
    <!-- Focus visual state would target ActionPrimaryBrush -->
</Style>

<!-- In View -->
<ComboBox Style="{StaticResource PremiumComboBox}">
    <ComboBoxItem Content="Option 1"/>
</ComboBox>
```

### Mac (SwiftUI)
SwiftUI offers elegant native components. Providing appropriate `.pickerStyle` or `.toggleStyle` ensures desktop parity while respecting macOS human interface guidelines.
```swift
// Native Select via Picker
Picker("Select Item", selection: $selectedValue) {
    Text("Option 1").tag(1)
}
.pickerStyle(.menu) 
.padding(.horizontal, 16)
.padding(.vertical, 8)
.background(Color.white)
.cornerRadius(8)
.overlay(RoundedRectangle(cornerRadius: 8).stroke(Theme.Colors.slate200))


// Native Toggle (Switch)
Toggle("Enable Feature", isOn: $isToggled)
    .toggleStyle(.switch)
    .tint(Theme.Colors.actionPrimary) // Using our semantic action color
```
