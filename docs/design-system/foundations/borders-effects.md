## Borders and Effects Overview
The design incorporates strong Glassmorphism elements in its card structures alongside modern, heavily-rounded borders for interactive elements. Shadows range from subtle utility drop-shadows to larger colored glows on primary buttons.

## Primitive Tokens
| Token Name | Web Equivalent | WPF (XAML) | Mac (SwiftUI) |
| :--- | :--- | :--- | :--- |
| `radius-lg` | `8px` | `CornerRadius="8"` | `.cornerRadius(8)` |
| `radius-xl` | `12px` | `CornerRadius="12"` | `.cornerRadius(12)` |
| `radius-2xl` | `16px` | `CornerRadius="16"` | `.cornerRadius(16)` |
| `radius-full`| `9999px` | `CornerRadius="9999"` | `Circle()` / `.clipShape(Capsule())` |
| `shadow-base`| `0 1px 3px 0 rgb(..., 0.1)` | `<DropShadowEffect BlurRadius="3" Opacity="0.1" />` | `.shadow(radius: 3, y: 1)` |
| `shadow-lg` | `0 10px 15px -3px rgb(...)`| `<DropShadowEffect BlurRadius="15" Direction="270" ShadowDepth="10" />` | `.shadow(color: .black.opacity(0.1), radius: 15, y: 10)` |

## Semantic Mappings (Aliases)
| Semantic Token | Rule | Usage Context |
| :--- | :--- | :--- |
| `radius-card` | `radius-xl` | Glass cards, dashboard widgets |
| `radius-button` | `radius-full` or `radius-2xl` | Primary buttons, tags |
| `effect-glass-bg` | RGBA white 70% | Background for floating cards/panels |
| `effect-glass-border`| RGBA white 30% | Subtle borders on glassmorphic elements |

## Platform Implementations

### WPF XAML Usage (`App.xaml` ResourceDictionary)
Glassmorphism is more intensive in standard WPF compared to the web, typically requiring specialized blur brushes. However, structural Border and Shadow effects translate directly.
```xml
<ResourceDictionary>
    <!-- Border Radii -->
    <CornerRadius x:Key="RadiusCard">12</CornerRadius>
    <CornerRadius x:Key="RadiusButton">9999</CornerRadius>

    <!-- Shared Drop Shadow -->
    <DropShadowEffect x:Key="ShadowLarge" 
                      BlurRadius="15" 
                      ShadowDepth="10" 
                      Direction="270" 
                      Opacity="0.1" 
                      Color="Black"/>
</ResourceDictionary>
```
**Example Usage:** `<Border CornerRadius="{StaticResource RadiusCard}" Effect="{StaticResource ShadowLarge}">...`

### Mac SwiftUI Usage (`Theme.swift`)
SwiftUI fully supports translucent materials seamlessly (`.ultraThinMaterial`), easily echoing web glassmorphism.
```swift
import SwiftUI

extension View {
    func glassCardStyle() -> some View {
        self
            .background(.regularMaterial) // Native Mac glass effect
            .cornerRadius(12)
            .overlay(
                RoundedRectangle(cornerRadius: 12)
                    .stroke(Color.white.opacity(0.3), lineWidth: 1)
            )
            .shadow(color: Color.black.opacity(0.05), radius: 15, x: 0, y: 10)
    }
}
```
**Example Usage:** `VStack { ... }.glassCardStyle()`
