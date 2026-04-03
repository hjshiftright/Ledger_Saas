## Card Component Overview
Cards act as the primary container element. They heavily utilize a `glass-card` styling offering a modern translucency alongside robust backdrop blur. 

## Component-Specific Tokens
| Component Token | Web Equivalent | WPF (XAML) Map | Mac (SwiftUI) Map |
| :--- | :--- | :--- | :--- |
| `card-glass-bg` | `bg-white/70` | `Background="#B3FFFFFF"` | `.background(.regularMaterial)` |
| `card-glass-border`| `border-white/40` | `BorderBrush="#66FFFFFF"` | `.stroke(Color.white.opacity(0.4))` |
| `card-shadow` | `shadow-slate-200/50`| `Effect="{StaticResource ShadowLarge}"` | `.shadow(color: .black.opacity(0.05), radius: 15)` |
| `card-radius` | `rounded-xl` | `CornerRadius="{StaticResource RadiusCard}"` | `.cornerRadius(12)` |
| `card-padding` | `p-4` or `p-6` | `Padding="16" or "24"` | `.padding(16)` |

## Cross-Platform Usage Examples

### Web (React/Tailwind)
```jsx
<div className="glass-card rounded-2xl p-6">
  <h2 className="text-xl font-bold font-display">Card Title</h2>
</div>
```

### Windows (WPF XAML)
Because full glassmorphism (with background blurring) is complex out of the box in WPF, cards rely heavily on the alpha backgrounds and border layering. Third-party packages like ModernWpf can be used to unlock native Windows Mica materials if deep blurring is desired.
```xml
<!-- Standard Fallback Style in ResourceDictionary -->
<Style x:Key="GlassCardStyle" TargetType="Border">
    <Setter Property="Background" Value="#B3FFFFFF"/> <!-- White 70% -->
    <Setter Property="BorderBrush" Value="#66FFFFFF"/> <!-- White 40% -->
    <Setter Property="BorderThickness" Value="1"/>
    <Setter Property="CornerRadius" Value="{StaticResource RadiusCard}"/>
    <Setter Property="Padding" Value="24"/>
    <Setter Property="Effect" Value="{StaticResource ShadowLarge}"/>
</Style>

<!-- In View -->
<Border Style="{StaticResource GlassCardStyle}">
    <TextBlock Style="{StaticResource TypographyH2}" Text="Card Title"/>
</Border>
```

### Mac (SwiftUI)
SwiftUI handles glassmorphism universally out of the box using Materials.
```swift
struct GlassCardModifier: ViewModifier {
    func body(content: Content) -> some View {
        content
            .padding(24)
            .background(.regularMaterial)
            .cornerRadius(12)
            .overlay(
                RoundedRectangle(cornerRadius: 12)
                    .stroke(Color.white.opacity(0.4), lineWidth: 1)
            )
            .shadow(color: Color.black.opacity(0.05), radius: 15, x: 0, y: 5)
    }
}

extension View {
    func glassCard() -> some View {
        modifier(GlassCardModifier())
    }
}

// In View
VStack(alignment: .leading) {
    Text("Card Title").font(.Semantic.h2)
}
.glassCard()
```
