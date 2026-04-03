## Icons Component Overview
The web application relies on `lucide-react` for consistent, lightweight vector iconography. Icons are universally sized using Tailwind utility classes and colored via standard `text-*` inheritance. 

For desktop clients, mapping these relies on finding equivalent native vector libraries or importing SVG path data.

## Component-Specific Tokens
| Component Token | Web Equivalent | WPF (XAML) Map | Mac (SwiftUI) Map |
| :--- | :--- | :--- | :--- |
| `icon-size-sm` | `w-4 h-4` (16px) | `Width="16" Height="16"` | `.frame(width: 16, height: 16)` |
| `icon-size-md` | `w-5 h-5` (20px) | `Width="20" Height="20"` | `.frame(width: 20, height: 20)` |
| `icon-size-lg` | `w-6 h-6` (24px) | `Width="24" Height="24"` | `.frame(width: 24, height: 24)` |
| `icon-color-muted` | `text-slate-400`| `Foreground="{StaticResource ColorSlate400}"`| `.foregroundColor(Theme.Colors.slate400)` |
| `icon-color-action`| `text-[#2C4A70]`| `Foreground="{StaticResource ActionPrimaryBrush}"`| `.foregroundColor(Theme.Colors.actionPrimary)` |

## Cross-Platform Usage Examples

### Web (React/Tailwind)
```jsx
import { Settings } from 'lucide-react';

<Settings className="w-5 h-5 text-slate-400" />
```

### Windows (WPF XAML)
Because embedding raw SVG paths bloats XAML files, the recommended path is utilizing `MahApps.Metro.IconPacks.Lucide`. This guarantees parity with the web's Lucide library.
```xml
<!-- Requires: xmlns:iconPacks="http://metro.mahapps.com/winfx/xaml/iconpacks" -->

<iconPacks:PackIconLucide 
    Kind="Settings" 
    Width="20" 
    Height="20" 
    Foreground="{StaticResource ColorSlate400}" 
    VerticalAlignment="Center"/>
```

*(Alternative: Path geometries)*
```xml
<Path Width="20" Height="20" Stretch="Uniform" Fill="{StaticResource ColorSlate400}" 
      Data="M12,2..."/> <!-- Insert explicit Lucide SVG data -->
```

### Mac (SwiftUI)
Apple provides the exceptionally robust `SF Symbols` framework natively. Instead of bundling third-party SVG icons, it is recommended to semantically map Lucide icons (like `Settings`) to their nearest Apple-sanctioned SF element (`gearshape.fill`).
```swift
struct IconView: View {
    // Map Lucide name logic
    let systemName: String
    
    var body: some View {
        Image(systemName: systemName)
            .resizable()
            .scaledToFit()
            .frame(width: 20, height: 20)
            .foregroundColor(Theme.Colors.slate400)
    }
}

// In View: Using SF Symbol 'gearshape.fill' for Settings
IconView(systemName: "gearshape.fill")
```
