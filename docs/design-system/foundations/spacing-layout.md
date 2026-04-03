## Spacing and Layout Overview
The project relies heavily on the strict 4px grid multiplier system to dictate all spacing and layout margins/padding configurations. This scaling ensures a perfectly aligned mathematical harmony.

## Primitive Tokens
| Token Name | Pixel Value | CSS | WPF (XAML) | Mac (SwiftUI) |
| :--- | :--- | :--- | :--- | :--- |
| `space-1` | `4` | `p-1`, `gap-1` | `<system:Double x:Key="Space1">4</system:Double>` | `CGFloat(4)` |
| `space-2` | `8` | `p-2`, `gap-2` | `<system:Double x:Key="Space2">8</system:Double>` | `CGFloat(8)` |
| `space-3` | `12` | `p-3`, `gap-3` | `<system:Double x:Key="Space3">12</system:Double>`| `CGFloat(12)` |
| `space-4` | `16` | `p-4`, `gap-4` | `<system:Double x:Key="Space4">16</system:Double>`| `CGFloat(16)` |
| `space-6` | `24` | `p-6`, `gap-6` | `<system:Double x:Key="Space6">24</system:Double>`| `CGFloat(24)` |
| `space-8` | `32` | `p-8`, `gap-8` | `<system:Double x:Key="Space8">32</system:Double>`| `CGFloat(32)` |

## Semantic Mappings (Aliases)
| Semantic Token | Value (Px) | Usage Context |
| :--- | :--- | :--- |
| `layout-page-padding`| 32 (or 16 mobile) | Outer padding for main dashboard layouts |
| `layout-card-padding`| 16 | Standard inner padding for cards and panels |
| `layout-gap-standard`| 12 | Spacing between sibling elements in a list |
| `layout-gap-tight` | 8 | Spacing for compact elements like icon and label |

## Platform Implementations

### WPF XAML Usage (`App.xaml` ResourceDictionary)
For WPF, define the `Double` primitives using the `clr-namespace:System;assembly=mscorlib` namespace, or set fixed Thickness resources.
```xml
<ResourceDictionary xmlns:system="clr-namespace:System;assembly=mscorlib">
    <!-- Primitives -->
    <system:Double x:Key="Space4">16</system:Double>
    
    <!-- Semantic Thickness (Padding/Margin) -->
    <Thickness x:Key="LayoutCardPadding">16,16,16,16</Thickness>
    <Thickness x:Key="LayoutPagePadding">32,32,32,32</Thickness>
</ResourceDictionary>
```
**Example Usage:** `<Border Padding="{StaticResource LayoutCardPadding}">...`

### Mac SwiftUI Usage (`Theme.swift`)
SwiftUI `padding` and `spacing` directly take `CGFloat` arguments. Create semantic aliases for your structural spacings.
```swift
import SwiftUI

extension CGFloat {
    struct Spacing {
        static let space4: CGFloat = 16
        static let space8: CGFloat = 32
    }
    
    struct Layout {
        static let cardPadding: CGFloat = Spacing.space4
        static let pagePadding: CGFloat = Spacing.space8
        static let gapStandard: CGFloat = 12
    }
}
```
**Example Usage:** 
```swift
VStack(spacing: .Layout.gapStandard) {
    // ...
}
.padding(.Layout.cardPadding)
```
