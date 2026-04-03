## Colors Overview
The project heavily utilizes Tailwind CSS utility classes, predominantly the `slate` palette for neutral tones and structural elements. Primary brand and action colors rely on `indigo`, `purple`, and a frequently hardcoded Cobalt Blue (`#2C4A70`). Semantic roles are currently intermixed with primitive utility classes.

This system guarantees visual parity across Web, WPF (Windows), and SwiftUI (Mac).

## Primitive Tokens
| Token Name | Hex Value | CSS/Tailwind | WPF (XAML) | Mac (SwiftUI) |
| :--- | :--- | :--- | :--- | :--- |
| `color-slate-50` | `#f8fafc` | `bg-slate-50` | `<SolidColorBrush x:Key="ColorSlate50" Color="#F8FAFC"/>` | `Color(hex: "#F8FAFC")` |
| `color-slate-100` | `#f1f5f9` | `bg-slate-100` | `<SolidColorBrush x:Key="ColorSlate100" Color="#F1F5F9"/>`| `Color(hex: "#F1F5F9")` |
| `color-slate-400` | `#94a3b8` | `text-slate-400`| `<SolidColorBrush x:Key="ColorSlate400" Color="#94A3B8"/>`| `Color(hex: "#94A3B8")` |
| `color-slate-500` | `#64748b` | `text-slate-500`| `<SolidColorBrush x:Key="ColorSlate500" Color="#64748B"/>`| `Color(hex: "#64748B")` |
| `color-slate-900` | `#0f172a` | `text-slate-900`| `<SolidColorBrush x:Key="ColorSlate900" Color="#0F172A"/>`| `Color(hex: "#0F172A")` |
| `color-indigo-50` | `#eef2ff` | `bg-indigo-50` | `<SolidColorBrush x:Key="ColorIndigo50" Color="#EEF2FF"/>`| `Color(hex: "#EEF2FF")` |
| `color-indigo-100` | `#e0e7ff` | `bg-indigo-100` | `<SolidColorBrush x:Key="ColorIndigo100" Color="#E0E7FF"/>`| `Color(hex: "#E0E7FF")` |
| `color-indigo-600` | `#4f46e5` | `indigo-600` | `<SolidColorBrush x:Key="ColorIndigo600" Color="#4F46E5"/>`| `Color(hex: "#4F46E5")` |
| brand-cobalt | `#2C4A70` | `#2C4A70` | `<SolidColorBrush x:Key="ColorBrandCobalt" Color="#2C4A70"/>`| `Color(hex: "#2C4A70")` |
| `color-emerald-500` | `#22c55e` | `text-emerald-500`| `<SolidColorBrush x:Key="ColorEmerald500" Color="#22C55E"/>`| `Color(hex: "#22C55E")` |
| `color-rose-500` | `#f43f5e` | `text-rose-500` | `<SolidColorBrush x:Key="ColorRose500" Color="#F43F5E"/>` | `Color(hex: "#F43F5E")` |
| `color-amber-500` | `#f59e0b` | `text-amber-500`| `<SolidColorBrush x:Key="ColorAmber500" Color="#F59E0B"/>` | `Color(hex: "#F59E0B")` |

## Semantic Mappings (Aliases)
| Semantic Token | Mapped Primitive | Usage Context |
| :--- | :--- | :--- |
| `color-bg-base` | `color-slate-50` | Application body background |
| `color-text-primary` | `color-slate-900` | Core body text |
| `color-text-secondary` | `color-slate-500` | Muted text, labels, hints |
| `color-action-primary` | `brand-cobalt` | Primary buttons, active tabs, major icons |
| `color-status-success` | `color-emerald-500` | Positive trends, income lines, success badges |
| `color-status-danger` | `color-rose-500` | Expense lines, negative trends, destructive actions |
| `color-status-warning` | `color-amber-500` | Warnings, alerts |

## Platform Implementations

### WPF XAML Usage (`App.xaml` ResourceDictionary)
Declare aliases to map directly to primitive values so the rest of your app only depends on Semantic Brushes.
```xml
<ResourceDictionary xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
                    xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
    <!-- Primitives -->
    <SolidColorBrush x:Key="ColorSlate50" Color="#F8FAFC"/>
    <SolidColorBrush x:Key="ColorSlate900" Color="#0F172A"/>
    <SolidColorBrush x:Key="ColorBrandCobalt" Color="#2C4A70"/>

    <!-- Aliases (Semantic) -->
    <SolidColorBrush x:Key="BgBaseBrush" Color="{Binding Color, Source={StaticResource ColorSlate50}}"/>
    <SolidColorBrush x:Key="TextPrimaryBrush" Color="{Binding Color, Source={StaticResource ColorSlate900}}"/>
    <SolidColorBrush x:Key="ActionPrimaryBrush" Color="{Binding Color, Source={StaticResource ColorBrandCobalt}}"/>
</ResourceDictionary>
```
**Example Usage:** `<Border Background="{StaticResource BgBaseBrush}">...`

### Mac SwiftUI Usage (`Theme.swift`)
Create a single Theme structure to map properties easily.
```swift
import SwiftUI

extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 3: // RGB (12-bit)
            (a, r, g, b) = (255, (int >> 8) * 17, (int >> 4 & 0xF) * 17, (int & 0xF) * 17)
        case 6: // RGB (24-bit)
            (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        default:
            (a, r, g, b) = (1, 1, 1, 0)
        }
        self.init(
            .sRGB,
            red: Double(r) / 255,
            green: Double(g) / 255,
            blue:  Double(b) / 255,
            opacity: Double(a) / 255
        )
    }
}

struct Theme {
    struct Colors {
        // Primitives
        static let slate50 = Color(hex: "#F8FAFC")
        static let slate900 = Color(hex: "#0F172A")
        static let brandCobalt = Color(hex: "#2C4A70")

        // Aliases
        static let bgBase = slate50
        static let textPrimary = slate900
        static let actionPrimary = brandCobalt
    }
}
```
**Example Usage:** `.background(Theme.Colors.bgBase)`
