## Feedback Skeletons & Empty States Overview
When initiating complex Monte Carlo simulations or processing cross-scenario projections, users need continuous feedback. A skeleton loader simulates the structure before the data finishes returning, preventing layout jank.

## Component-Specific Tokens
| Component Token | Web Equivalent | WPF (XAML) Map | Mac (SwiftUI) Map |
| :--- | :--- | :--- | :--- |
| `skeleton-bg` | `bg-slate-200` | `Background="{StaticResource ColorSlate200}"`| `.background(Theme.Colors.slate200)` |
| `skeleton-pulse`| `animate-pulse` | Infinite Opacity Storyboard `[0.5 -> 1.0]` | `.opacity(isPulsing ? 0.5 : 1.0)` |
| `skeleton-radius`| `rounded-xl` | `CornerRadius="12"` | `.cornerRadius(12)` |

## Cross-Platform Usage Examples

### Web (React/Tailwind)
```jsx
// Skeleton Card (Pulsing)
<div className="glass-card rounded-2xl p-6 animate-pulse">
  <div className="h-6 w-1/3 bg-slate-200 rounded mb-4"></div>
  <div className="h-32 w-full bg-slate-100 rounded-xl"></div>
</div>
```

### Windows (WPF XAML)
Because WPF does not have a native "pulse" utility class, we build an isolated animated style using `EventTrigger` for `Loaded`.
```xml
<!-- Infinite Pulse Animation Style -->
<Style x:Key="SkeletonPulseStyle" TargetType="Border">
    <Setter Property="Background" Value="{StaticResource ColorSlate200}"/>
    <Setter Property="CornerRadius" Value="4"/>
    <Style.Triggers>
        <EventTrigger RoutedEvent="Loaded">
            <BeginStoryboard>
                <Storyboard RepeatBehavior="Forever" AutoReverse="True">
                    <DoubleAnimation Storyboard.TargetProperty="Opacity" 
                                     From="1.0" To="0.5" 
                                     Duration="0:0:0.8"/>
                </Storyboard>
            </BeginStoryboard>
        </EventTrigger>
    </Style.Triggers>
</Style>

<!-- In View -->
<Border Style="{StaticResource GlassCardStyle}">
    <StackPanel>
        <!-- Title Skeleton -->
        <Border Height="24" Width="120" HorizontalAlignment="Left" Margin="0,0,0,16" Style="{StaticResource SkeletonPulseStyle}"/>
        <!-- Graph Skeleton -->
        <Border Height="128" CornerRadius="12" Style="{StaticResource SkeletonPulseStyle}"/>
    </StackPanel>
</Border>
```

### Mac (SwiftUI)
SwiftUI animations handle repetitive pulsing beautifully via `.repeatForever()`. In iOS 17/macOS 14, standard `.scenePadding()` loaders are native, but a manual custom pulsing view guarantees backward compatibility.
```swift
struct SkeletonLoader: View {
    @State private var isPulsing = false
    
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            // Title Skeleton
            RoundedRectangle(cornerRadius: 4)
                .fill(Theme.Colors.slate200)
                .frame(width: 120, height: 24)
            
            // Graph Skeleton
            RoundedRectangle(cornerRadius: 12)
                .fill(Theme.Colors.slate200)
                .frame(height: 128)
        }
        .padding(24)
        .background(Color.white)
        .cornerRadius(12)
        .opacity(isPulsing ? 0.5 : 1.0)
        .onAppear {
            withAnimation(.easeInOut(duration: 0.8).repeatForever(autoreverses: true)) {
                isPulsing = true
            }
        }
    }
}
```
