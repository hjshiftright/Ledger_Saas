## Button Component Overview
Buttons feature gradients, aggressive border radius (`2xl` or `full`), hover shadows, and active scaling. 

## Component-Specific Tokens
| Component Token | Web Equivalent | WPF (XAML) Map | Mac (SwiftUI) Map |
| :--- | :--- | :--- | :--- |
| `button-primary-bg` | `bg-[#2C4A70]` | `Background="{StaticResource ActionPrimaryBrush}"` | `.background(Theme.Colors.actionPrimary)` |
| `button-primary-text` | `text-white` | `Foreground="White"` | `.foregroundColor(.white)` |
| `button-radius-primary`| `rounded-2xl` | `CornerRadius="{StaticResource RadiusButton}"` | `.cornerRadius(16)` |
| `button-padding-y`| `py-3` | `Padding="0,12"` | `.padding(.vertical, 12)` |
| `button-padding-x`| `px-6` | `Padding="24,0"` | `.padding(.horizontal, 24)` |

## Cross-Platform Usage Examples

### Web (React/Tailwind)
```jsx
<button className="px-6 py-3 rounded-2xl bg-[#2C4A70] text-white font-bold transition-all hover:bg-slate-700 hover:shadow-lg">
  Continue
</button>
```

### Windows (WPF XAML)
Define standard Button styles within your `App.xaml` or standard `ResourceDictionary`.
```xml
<!-- In Resource Dictionary -->
<Style x:Key="ButtonPremium" TargetType="Button">
    <Setter Property="Background" Value="{StaticResource ActionPrimaryBrush}"/>
    <Setter Property="Foreground" Value="White"/>
    <Setter Property="Padding" Value="24,12"/>
    <Setter Property="BorderThickness" Value="0"/>
    <Setter Property="Cursor" Value="Hand"/>
    <Setter Property="Template">
        <Setter.Value>
            <ControlTemplate TargetType="Button">
                <Border Background="{TemplateBinding Background}" 
                        CornerRadius="{StaticResource RadiusButton}"
                        Padding="{TemplateBinding Padding}">
                    <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center"/>
                </Border>
                <!-- Add VisualState triggers for Hover shadow injections -->
            </ControlTemplate>
        </Setter.Value>
    </Setter>
</Style>

<!-- In View -->
<Button Style="{StaticResource ButtonPremium}" Content="Continue"/>
```

### Mac (SwiftUI)
Construct a custom ButtonStyle for SwiftUI to handle identical pressed scales and layouts natively.
```swift
struct PremiumButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.Semantic.body.bold())
            .foregroundColor(.white)
            .padding(.horizontal, 24)
            .padding(.vertical, 12)
            .background(Theme.Colors.actionPrimary)
            .cornerRadius(16)
            .shadow(color: configuration.isPressed ? .clear : .black.opacity(0.1), radius: 5, y: 2)
            .scaleEffect(configuration.isPressed ? 0.95 : 1)
            .animation(Motion.hover, value: configuration.isPressed)
    }
}

// In View
Button("Continue") {
    // Action
}
.buttonStyle(PremiumButtonStyle())
```
