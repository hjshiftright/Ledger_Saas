## Typography Overview
The application utilizes a dual-font architecture. `Plus Jakarta Sans` is applied globally to the body for high legibility in data-dense interfaces, while `Outfit` is reserved for display headers (H1-H4) to provide a modern, geometric aesthetic.

## Primitive Tokens
| Token Name | CSS | WPF (XAML) | Mac (SwiftUI) |
| :--- | :--- | :--- | :--- |
| `font-family-body` | `'Plus Jakarta Sans'` | `FontFamily="Plus Jakarta Sans"` | `.font(.custom("Plus Jakarta Sans", size: ...))` |
| `font-family-title` | `'Outfit'` | `FontFamily="Outfit"` | `.font(.custom("Outfit", size: ...))` |
| `font-weight-regular` | `400` | `FontWeight="Normal"` | `weight: .regular` |
| `font-weight-medium` | `500` | `FontWeight="Medium"` | `weight: .medium` |
| `font-weight-semibold`| `600` | `FontWeight="SemiBold"` | `weight: .semibold` |
| `font-weight-bold` | `700` | `FontWeight="Bold"` | `weight: .bold` |

## Semantic Mappings (Aliases)
| Semantic Token | Styling (Size / Weight / Family) | Web Example |
| :--- | :--- | :--- |
| `typography-h1` | 36px (2.25rem) / Bold / Display | `text-4xl font-bold font-display` |
| `typography-h2` | 24px (1.5rem) / Bold / Display | `text-2xl font-bold font-display` |
| `typography-body` | 16px (1rem) / Regular / Sans | `text-base` |
| `typography-body-sm` | 14px (0.875rem) / Regular / Sans | `text-sm` |
| `typography-caption` | 12px (0.75rem) / SemiBold / Sans| `text-xs font-semibold` |

## Platform Implementations

### WPF XAML Usage (`App.xaml` ResourceDictionary)
Define default text styles that apply across TextBlock elements globally, mapping explicitly to local bundled font files if necessary. 
```xml
<ResourceDictionary>
    <!-- FontFamily Primitives -->
    <!-- Assuming fonts are included in Fonts/ folder as Embedded Resources -->
    <FontFamily x:Key="FontBody">pack://application:,,,/Fonts/#Plus Jakarta Sans</FontFamily>
    <FontFamily x:Key="FontDisplay">pack://application:,,,/Fonts/#Outfit</FontFamily>

    <!-- Semantic Styles -->
    <Style x:Key="TypographyH1" TargetType="TextBlock">
        <Setter Property="FontFamily" Value="{StaticResource FontDisplay}"/>
        <Setter Property="FontSize" Value="36"/>
        <Setter Property="FontWeight" Value="Bold"/>
    </Style>

    <Style x:Key="TypographyBody" TargetType="TextBlock">
        <Setter Property="FontFamily" Value="{StaticResource FontBody}"/>
        <Setter Property="FontSize" Value="16"/>
        <Setter Property="FontWeight" Value="Normal"/>
    </Style>
</ResourceDictionary>
```
**Example Usage:** `<TextBlock Style="{StaticResource TypographyH1}">Title</TextBlock>`

### Mac SwiftUI Usage (`Theme.swift`)
Create custom ViewModifiers or extensions on View/Font to map the semantic tokens securely.
```swift
import SwiftUI

extension Font {
    struct Semantic {
        static var h1: Font {
            .custom("Outfit-Bold", size: 36)
        }
        
        static var body: Font {
            .custom("PlusJakartaSans-Regular", size: 16)
        }

        static var caption: Font {
            .custom("PlusJakartaSans-SemiBold", size: 12)
        }
    }
}
```
**Example Usage:** `Text("Dashboard").font(.Semantic.h1)`
