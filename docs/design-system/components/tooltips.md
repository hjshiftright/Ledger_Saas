## Tooltips Overview
Deep finance relies heavily on assumed variables (CAGR, Inflation, Volatility) and acronyms. Tooltips are vital for progressive disclosure, keeping the dashboard clean while offering deep contextual definitions on hover/tap.

## Component-Specific Tokens
| Component Token | Web Equivalent | WPF (XAML) Map | Mac (SwiftUI) Map |
| :--- | :--- | :--- | :--- |
| `tooltip-bg` | `bg-slate-900` | `Background="{StaticResource ColorSlate900}"`| `.background(Theme.Colors.slate900)` |
| `tooltip-text` | `text-slate-50`| `Foreground="{StaticResource ColorSlate50}"` | `.foregroundColor(.white)` |
| `tooltip-radius`| `rounded-lg` | `CornerRadius="8"` | `.cornerRadius(8)` |
| `tooltip-shadow`| `shadow-lg` | `Effect="{StaticResource ShadowLarge}"` | `.shadow(radius: 10)` |

## Cross-Platform Usage Examples

### Web (React)
```jsx
// Using standard Title or custom Radix Tooltips
<div className="group relative inline-flex">
  <span className="text-slate-400 hover:text-[#2C4A70] cursor-help">CAGR?</span>
  
  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block w-48 bg-slate-900 text-slate-50 text-xs p-3 rounded-lg shadow-lg z-40">
    Compound Annual Growth Rate represents the yield over a specified time.
  </div>
</div>
```

### Windows (WPF XAML)
WPF has a native `ToolTip` property on all elements that can be fully re-stamped.
```xml
<Style TargetType="ToolTip">
    <Setter Property="Background" Value="{StaticResource ColorSlate900}" />
    <Setter Property="Foreground" Value="{StaticResource ColorSlate50}" />
    <Setter Property="Padding" Value="12,8" />
    <Setter Property="BorderThickness" Value="0" />
    <!-- Overriding template to add CornerRadius -->
    <Setter Property="Template">
        <Setter.Value>
            <ControlTemplate TargetType="ToolTip">
                <Border Background="{TemplateBinding Background}" 
                        CornerRadius="8" 
                        Padding="{TemplateBinding Padding}"
                        Effect="{StaticResource ShadowLarge}">
                    <ContentPresenter />
                </Border>
            </ControlTemplate>
        </Setter.Value>
    </Setter>
</Style>

<!-- In View -->
<TextBlock Text="CAGR?" Foreground="{StaticResource ColorSlate400}" Cursor="Help"
           ToolTip="Compound Annual Growth Rate represents the yield over a specified time."/>
```

### Mac (SwiftUI)
On macOS, tooltips are accessed natively through `.help()`. For custom popovers triggered by tap (iOS/iPad OS overlap), use `.popover()`.
```swift
// Native Mac Tooltip (On Hover)
Text("CAGR?")
    .foregroundColor(Theme.Colors.slate400)
    .help("Compound Annual Growth Rate represents the yield over a specified time.")

// Custom Styled Popover
@State private var showTooltip = false

Button("CAGR?") { showTooltip.toggle() }
    .foregroundColor(Theme.Colors.slate400)
    .popover(isPresented: $showTooltip) {
        Text("Compound Annual Growth Rate represents the yield over a specified time.")
            .font(.Semantic.caption)
            .padding(12)
            .background(Theme.Colors.slate900)
            .foregroundColor(.white)
            // Note: SwiftUI automatically handles the outer popover popout appearance
    }
```
