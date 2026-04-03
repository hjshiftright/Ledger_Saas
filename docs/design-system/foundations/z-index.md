## Z-Index & Elevation Overview
Z-Index layering is used fundamentally on the web version to manage overlapping context menus, sticky headers, and full-screen modal overlays. Desktop clients manage layering natively either through layout order or dedicated elevation properties.

## Primitive Tokens
| Token Name | Layer Identity | Web Equivalent | WPF (XAML) Map | Mac (SwiftUI) Map |
| :--- | :--- | :--- | :--- | :--- |
| `z-index-base` | Standard content | `z-0` | `Panel.ZIndex="0"` | `.zIndex(0)` |
| `z-index-sticky` | Fixed Headers/Navs | `z-10` | `Panel.ZIndex="10"` | `.zIndex(10)` |
| `z-index-dropdown`| Select Menus/Tooltips | `z-40` | `Panel.ZIndex="40"` | `.zIndex(40)` |
| `z-index-modal` | Overlays/Dialogs | `z-50` | `Panel.ZIndex="50"` | `.zIndex(50)` |

## Cross-Platform Usage Examples

### Web (React/Tailwind)
```jsx
// Page Layout with Sticky Header and overlaid Modal
<div className="relative">
  <header className="sticky top-0 z-10 bg-white">Nav</header>
  
  <main className="z-0">Scrollable Content</main>
  
  <div className="fixed inset-0 z-50 bg-black/40">Modal Overlay</div>
</div>
```

### Windows (WPF XAML)
In WPF, elements declared *later* in the XAML tree naturally render on top. `Panel.ZIndex` forcibly overrides this rendering sequence and perfectly mimics HTML Z-binding.
```xml
<Grid>
    <!-- Renders normally -->
    <ScrollViewer Panel.ZIndex="0">
        <TextBlock Text="Scrollable Content"/>
    </ScrollViewer>
    
    <!-- Forced above content visually, simulating fixed header -->
    <Border Panel.ZIndex="10" VerticalAlignment="Top" Background="White">
        <TextBlock Text="Nav"/>
    </Border>
    
    <!-- Top-most level popup -->
    <Grid Panel.ZIndex="50" Background="#66000000">
        <TextBlock Text="Modal Overlay" Foreground="White" HorizontalAlignment="Center"/>
    </Grid>
</Grid>
```

### Mac (SwiftUI)
SwiftUI handles Z-depth explicitly using the `.zIndex()` modifier. Like WPF, things written later in a `ZStack` render on top natively, but explicitly declaring `.zIndex` helps coordinate animations.
```swift
ZStack(alignment: .top) {
    // Scrollable Content
    ScrollView {
        Text("Scrollable Content")
            .padding(.top, 60)
    }
    .zIndex(0)

    // Sticky Header
    VStack {
        Text("Nav")
            .frame(maxWidth: .infinity)
            .padding()
            .background(Color.white)
    }
    .zIndex(10)

    // Conditional Modal
    if showModal {
        Color.black.opacity(0.4)
            .ignoresSafeArea()
            .overlay(
                Text("Modal Overlay").foregroundColor(.white)
            )
            .zIndex(50) // Ensures top level hierarchy
    }
}
```
