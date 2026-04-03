## Input Component Overview
Inputs feature robust, solid padding, rounded borders, and heavily visible ring focuses. 

## Component-Specific Tokens
| Component Token | Web Equivalent | WPF (XAML) Map | Mac (SwiftUI) Map |
| :--- | :--- | :--- | :--- |
| `input-bg` | `bg-white` | `Background="White"` | `.background(Color.white)` |
| `input-border` | `border-slate-200` | `BorderBrush="{StaticResource ColorSlate200}"`| `.overlay(RoundedRectangle... stroke)` |
| `input-radius` | `rounded-lg` | `CornerRadius="8"` | `.cornerRadius(8)` |
| `input-padding` | `px-4 py-3` | `Padding="16,12"` | `.padding(.horizontal, 16).padding(.vertical, 12)` |

## Cross-Platform Usage Examples

### Web (React/Tailwind)
```jsx
<input 
  type="text" 
  className="w-full px-4 py-3 rounded-lg border border-slate-200 focus:border-[#2C4A70] focus:ring-2 focus:ring-[#2C4A70]/20 outline-none bg-white"
  placeholder="Enter value"
/>
```

### Windows (WPF XAML)
Building a standard textbox style ensures identical border focus interactions.
```xml
<Style x:Key="PremiumTextBox" TargetType="TextBox">
    <Setter Property="Background" Value="White"/>
    <Setter Property="BorderBrush" Value="{StaticResource ColorSlate200}"/>
    <Setter Property="BorderThickness" Value="1"/>
    <Setter Property="Padding" Value="16,12"/>
    <Setter Property="VerticalContentAlignment" Value="Center"/>
    <Setter Property="Template">
        <Setter.Value>
            <ControlTemplate TargetType="TextBox">
                <Border Background="{TemplateBinding Background}" 
                        BorderBrush="{TemplateBinding BorderBrush}" 
                        BorderThickness="{TemplateBinding BorderThickness}" 
                        CornerRadius="8"
                        x:Name="border">
                    <ScrollViewer x:Name="PART_ContentHost" Margin="0"/>
                </Border>
                <ControlTemplate.Triggers>
                    <Trigger Property="IsFocused" Value="True">
                        <Setter TargetName="border" Property="BorderBrush" Value="{StaticResource ActionPrimaryBrush}"/>
                        <!-- Simulating Ring -->
                        <Setter TargetName="border" Property="BorderThickness" Value="2"/> 
                    </Trigger>
                </ControlTemplate.Triggers>
            </ControlTemplate>
        </Setter.Value>
    </Setter>
</Style>

<!-- In View -->
<TextBox Style="{StaticResource PremiumTextBox}" Tag="Enter value"/>
```

### Mac (SwiftUI)
SwiftUI handles standard input fields but generally requires custom TextFieldStyle modifiers to replicate Web behaviors accurately.
```swift
struct PremiumTextFieldStyle: TextFieldStyle {
    @FocusState private var isFocused: Bool

    func _body(configuration: TextField<Self._Label>) -> some View {
        configuration
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
            .background(Color.white)
            .cornerRadius(8)
            .overlay(
                RoundedRectangle(cornerRadius: 8)
                    .stroke(isFocused ? Theme.Colors.actionPrimary : Theme.Colors.slate200, lineWidth: isFocused ? 2 : 1)
            )
            .focused($isFocused)
            .animation(Motion.hover, value: isFocused)
    }
}

// In View
TextField("Enter value", text: $value)
    .textFieldStyle(PremiumTextFieldStyle())
```
