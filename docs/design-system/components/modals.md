## Modals Component Overview
Modals in the application are designed with a fixed, full-screen semi-transparent backdrop and a centered glassmorphic or solid white panel. Close buttons are top-right.

## Component-Specific Tokens
| Component Token | Web Equivalent | WPF (XAML) Map | Mac (SwiftUI) Map |
| :--- | :--- | :--- | :--- |
| `modal-backdrop-bg` | `bg-slate-900/40` | `Background="#660F172A"` | `Color.black.opacity(0.4)` |
| `modal-backdrop-blur`| `backdrop-blur-sm` | N/A (Standard WPF lacks backdrop blurring easily) | `.background(.ultraThinMaterial)` |
| `modal-panel-bg` | `bg-white` | `Background="White"` | `.background(Color.white)` |
| `modal-panel-radius` | `rounded-2xl` | `CornerRadius="{StaticResource RadiusCard}"` | `.cornerRadius(16)` |
| `modal-panel-shadow` | `shadow-2xl` | `Effect="{StaticResource ShadowLarge}"` | `.shadow(color: .black.opacity(0.2), radius: 30)` |
| `modal-padding` | `p-6` or `p-8` | `Padding="24" or "32"` | `.padding(24)` |

## Cross-Platform Usage Examples

### Web (React/Tailwind)
```jsx
// Modal Wrapper
<div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
  <div className="bg-white rounded-2xl shadow-2xl p-6 relative">
    <button className="absolute top-4 right-4 p-2">Close</button>
    <h2 className="text-2xl font-bold">Dialog Title</h2>
  </div>
</div>
```

### Windows (WPF XAML)
In WPF, you can use a custom overlay grid or a new `Window` without chromes to accomplish modals. Using an overlay `Grid` in your root layout works best for in-app popups.
```xml
<Grid x:Name="ModalBackdrop" Background="#660F172A" Visibility="Visible">
    <!-- Centered Modal Content -->
    <Border Background="White" 
            CornerRadius="16" 
            Padding="24" 
            HorizontalAlignment="Center" 
            VerticalAlignment="Center"
            Effect="{StaticResource ShadowLarge}">
        <Grid>
            <!-- Close Button Top Right -->
            <Button HorizontalAlignment="Right" VerticalAlignment="Top" 
                    Margin="-8,-8,0,0" Content="✕" 
                    Style="{StaticResource StandardCloseButton}"/>
            
            <StackPanel Margin="0,16,0,0">
                <TextBlock Style="{StaticResource TypographyH2}" Text="Dialog Title"/>
                <!-- Modal Body -->
            </StackPanel>
        </Grid>
    </Border>
</Grid>
```

### Mac (SwiftUI)
SwiftUI handles standard modals with `.sheet()` or `.fullScreenCover()`, but fully-custom centered modals can be created using ZStack overlays.
```swift
struct CustomModalView<Content: View>: View {
    @Binding var isPresented: Bool
    let title: String
    let content: Content

    init(isPresented: Binding<Bool>, title: String, @ViewBuilder content: () -> Content) {
        self._isPresented = isPresented
        self.title = title
        self.content = content()
    }

    var body: some View {
        ZStack {
            if isPresented {
                // Backdrop
                Color.black.opacity(0.4)
                    .ignoresSafeArea()
                    .onTapGesture { isPresented = false }
                
                // Panel
                VStack(alignment: .leading, spacing: 16) {
                    HStack {
                        Text(title).font(.Semantic.h2)
                        Spacer()
                        Button(action: { isPresented = false }) {
                            Image(systemName: "xmark")
                                .foregroundColor(Theme.Colors.slate500)
                        }
                    }
                    
                    content
                }
                .padding(24)
                .background(Color.white)
                .cornerRadius(16)
                .shadow(color: Color.black.opacity(0.15), radius: 30)
                .padding(40)
            }
        }
        .animation(.easeInOut(duration: 0.2), value: isPresented)
    }
}
```
