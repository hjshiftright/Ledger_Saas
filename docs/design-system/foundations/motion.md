## Motion Overview
Motion is handled through standard transition durations and easing keyframes. The interface relies upon quick transition states for button humors and slower "animate-in" states for page loads.

## Primitive Tokens
| Token Name | Web Equivalent | WPF (XAML) | Mac (SwiftUI) |
| :--- | :--- | :--- | :--- |
| `duration-fast` | `150ms` | `<Duration>0:0:0.15</Duration>` | `.animation(.easeInOut(duration: 0.15))` |
| `duration-normal`| `300ms` | `<Duration>0:0:0.3</Duration>` | `.animation(.easeInOut(duration: 0.3))` |
| `duration-slow` | `600ms` | `<Duration>0:0:0.6</Duration>` | `.animation(.easeInOut(duration: 0.6))` |
| `ease-standard` | `cubic-bezier(0.4, 0, 0.2, 1)` | `SineEaseInOut` | `.easeInOut` |
| `ease-out-back` | `cubic-bezier(0.16, 1, 0.3, 1)`| `BackEaseOut` | `.interactiveSpring()` |

## Semantic Mappings (Aliases)
| Semantic Token | Mapped Primitive | Usage Context |
| :--- | :--- | :--- |
| `motion-hover` | `duration-fast` / `ease-standard` | Button and link hovers |
| `motion-page-enter`| `duration-slow` / `ease-out-back` | Sliding up page content on load |
| `motion-progress` | `duration-slow` / `ease-standard` | Progress bar width fill animations |

## Platform Implementations

### WPF XAML Usage (`App.xaml` ResourceDictionary)
For WPF, animations are heavily reliant on `Storyboards` and `VisualStateGroups`.
```xml
<ResourceDictionary>
    <Duration x:Key="DurationFast">0:0:0.15</Duration>
    <Duration x:Key="DurationSlow">0:0:0.6</Duration>

    <!-- Example Storyboard using the standard fast motion token -->
    <Storyboard x:Key="HoverEnterAnimation">
        <DoubleAnimation Storyboard.TargetProperty="Opacity" 
                         To="0.8" 
                         Duration="{StaticResource DurationFast}">
            <DoubleAnimation.EasingFunction>
                <SineEase EasingMode="EaseInOut"/>
            </DoubleAnimation.EasingFunction>
        </DoubleAnimation>
    </Storyboard>
</ResourceDictionary>
```

### Mac SwiftUI Usage (`Theme.swift`)
SwiftUI handles transitions naturally through `.animation` attachments tied to state mutations.
```swift
import SwiftUI

struct Motion {
    static let hover = Animation.easeInOut(duration: 0.15)
    static let progress = Animation.easeInOut(duration: 0.6)
    static let pageEnter = Animation.spring(response: 0.6, dampingFraction: 0.7, blendDuration: 0)
}
```
**Example Usage:** 
```swift
Button("Action") {}
    .animation(Motion.hover, value: isHovered)
```
