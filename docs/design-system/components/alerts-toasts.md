## Alerts & Toasts Overview
For feedback that doesn't require interrupting the workflow via a modal—like an "Import Successful" status, or a warning saying "Current savings rate falls short"—Alerts (in-page banners) and Toasts (floating non-blocking popups) are standard.

## Component-Specific Tokens
| Component Token | Web Equivalent | WPF (XAML) Map | Mac (SwiftUI) Map |
| :--- | :--- | :--- | :--- |
| `alert-warning-bg`| `bg-amber-50` | `Background="#E6F59E0B"` | `.background(Theme.Colors.amber50)` |
| `alert-warning-border`| `border-amber-200` | `BorderBrush="{StaticResource ColorAmber200}"`| `.stroke(Theme.Colors.amber200)` |
| `toast-shadow` | `shadow-lg` | `Effect="{StaticResource ShadowLarge}"` | `.shadow(radius: 10)` |

## Cross-Platform Usage Examples

### Web (React/Tailwind)
```jsx
// In-Page Warning Alert
<div className="flex bg-amber-50 border border-amber-200 p-4 rounded-xl items-start gap-3">
  <WarningIcon className="w-5 h-5 text-amber-500 shrink-0" />
  <div className="text-sm text-amber-800">
    <p className="font-bold">Shortfall Detected</p>
    <p>Your projected horizon may not cover inflation under this model.</p>
  </div>
</div>
```

### Windows (WPF XAML)
In WPF, an inline alert behaves identically to any block element. For floating Toasts, third-party libraries (or dedicated Adorner layering) are frequently used, but a simple Border suffices for static banners.
```xml
<Style x:Key="WarningAlertBorder" TargetType="Border">
    <Setter Property="Background" Value="#FDF6E3"/> <!-- Amber 50 approx -->
    <Setter Property="BorderBrush" Value="#FDE68A"/> <!-- Amber 200 approx -->
    <Setter Property="BorderThickness" Value="1"/>
    <Setter Property="CornerRadius" Value="{StaticResource RadiusCard}"/>
    <Setter Property="Padding" Value="16"/>
</Style>

<!-- In View -->
<Border Style="{StaticResource WarningAlertBorder}">
    <StackPanel Orientation="Horizontal">
        <Path Fill="{StaticResource ColorAmber500}" Data="..." Width="20" Height="20" Margin="0,0,12,0"/>
        <StackPanel>
            <TextBlock Text="Shortfall Detected" FontWeight="Bold" Foreground="#92400E"/>
            <TextBlock Text="Your projected horizon may not cover inflation." Foreground="#B45309"/>
        </StackPanel>
    </StackPanel>
</Border>
```

### Mac (SwiftUI)
Inline alerts in SwiftUI are straightforward stacks. For Toasts on Mac, custom overlays injected into `.overlay(alignment: .bottom)` are used.
```swift
struct WarningAlert: View {
    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: "exclamationmark.triangle.fill")
                .foregroundColor(Theme.Colors.amber500)
                .frame(width: 20, height: 20)
            
            VStack(alignment: .leading, spacing: 4) {
                Text("Shortfall Detected")
                    .font(.Semantic.bodySm.weight(.bold))
                Text("Your projected horizon may not cover inflation under this model.")
                    .font(.Semantic.bodySm)
            }
            .foregroundColor(Theme.Colors.slate900) // Or dedicated deep amber scale
        }
        .padding(16)
        .background(Color(hex: "#FDF6E3")) // Deep alias map for amber-50
        .cornerRadius(12)
        .overlay(RoundedRectangle(cornerRadius: 12).stroke(Color(hex: "#FDE68A")))
    }
}
```
