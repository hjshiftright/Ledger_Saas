## Badges Component Overview
Badges are used to indicate statuses (e.g. success, failure, tracking percentage). They almost universally feature full rounded borders (pill shape), bold miniature text, and heavily tinted backgrounds dependent on their semantic status (e.g. `bg-emerald-500/10` with `text-emerald-500`).

## Component-Specific Tokens
| Component Token | Web Equivalent | WPF (XAML) Map | Mac (SwiftUI) Map |
| :--- | :--- | :--- | :--- |
| `badge-radius` | `rounded-full` | `CornerRadius="9999"` | `.clipShape(Capsule())` |
| `badge-padding-x` | `px-2.5` | `Padding="10,0"` | `.padding(.horizontal, 10)` |
| `badge-padding-y` | `py-1` | `Padding="0,4"` | `.padding(.vertical, 4)` |
| `badge-font-size` | `text-xs` | `FontSize="12"` | `.font(.Semantic.caption)` |
| `badge-success-bg` | `bg-emerald-500/10` | `Background="#1A22C55E"` (Hex with 10% Alpha) | `.background(Theme.Colors.emerald500.opacity(0.1))` |
| `badge-info-bg` | `bg-[#2C4A70]/5` | `Background="#0C2C4A70"` (Hex with 5% Alpha)| `.background(Theme.Colors.actionPrimary.opacity(0.05))` |

## Cross-Platform Usage Examples

### Web (React/Tailwind)
```jsx
// Success Badge
<span className="bg-emerald-500/10 text-emerald-600 text-xs font-bold px-2.5 py-1 rounded-full">
  +12.5%
</span>
```

### Windows (WPF XAML)
Because WPF elements are static structures, a style targeting a `Border` encapsulation is the easiest way to replicate inline HTML tags.
```xml
<Style x:Key="BadgeSuccessStyle" TargetType="Border">
    <!-- Assuming hex #1A22C55E represents 10% opacity Emerald -->
    <Setter Property="Background" Value="#1A22C55E"/>
    <Setter Property="CornerRadius" Value="{StaticResource RadiusButton}"/>
    <Setter Property="Padding" Value="10,4"/>
</Style>

<Style x:Key="BadgeSuccessText" TargetType="TextBlock" BasedOn="{StaticResource TypographyCaption}">
    <Setter Property="Foreground" Value="{StaticResource ColorEmerald500}"/>
    <Setter Property="VerticalAlignment" Value="Center"/>
</Style>

<!-- In View -->
<Border Style="{StaticResource BadgeSuccessStyle}">
    <TextBlock Style="{StaticResource BadgeSuccessText}" Text="+12.5%"/>
</Border>
```

### Mac (SwiftUI)
Easily scalable in SwiftUI through a custom `ViewModifier` or structural view component.
```swift
struct BadgeSuccessModifier: ViewModifier {
    func body(content: Content) -> some View {
        content
            .font(.Semantic.caption)
            .foregroundColor(Theme.Colors.emerald500)
            .padding(.horizontal, 10)
            .padding(.vertical, 4)
            .background(Theme.Colors.emerald500.opacity(0.1))
            .clipShape(Capsule())
    }
}

extension View {
    func badgeSuccess() -> some View {
        modifier(BadgeSuccessModifier())
    }
}

// In View
Text("+12.5%").badgeSuccess()
```
