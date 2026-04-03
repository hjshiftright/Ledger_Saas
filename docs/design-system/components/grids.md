## Grid Component Overview
The application utilizes grid utilities to handle layout structures for dashboards and lists, creating structured column workflows. Desktop applications traditionally handle these layouts using specialized container classes like Grid (WPF) or LazyVGrid/HStack (SwiftUI).

## Component-Specific Tokens
| Component Token | Web Equivalent | WPF (XAML) Map | Mac (SwiftUI) Map |
| :--- | :--- | :--- | :--- |
| `grid-gap` | `gap-4` or `gap-6` | `<RowDefinition Height="16"/>` | `spacing: 16` or `24` |
| `grid-cols-mobile` | `grid-cols-1` | Single column Grid/StackPanel | `VStack` |
| `grid-cols-desktop`| `md:grid-cols-3` | 3 ColumnDefinitions | `LazyVGrid(columns: [GridItem(.flexible())...])` |
| `grid-cols-sidebar`| `md:grid-cols-[280px_1fr]` | `ColumnDefinition Width="280"`, `Width="*"`| `NavigationSplitView` |

## Cross-Platform Usage Examples

### Web (React/Tailwind)
```jsx
// Dashboard Widget Grid
<div className="grid grid-cols-1 md:grid-cols-3 gap-6">
  <WidgetCard />
  <WidgetCard />
  <WidgetCard />
</div>
```

### Windows (WPF XAML)
WPF handles gridding natively through the `<Grid>` control, defining precise column structures.
```xml
<!-- Dashboard Widget Grid -->
<Grid>
    <Grid.ColumnDefinitions>
        <ColumnDefinition Width="*"/>
        <!-- Gap -->
        <ColumnDefinition Width="24"/> 
        <ColumnDefinition Width="*"/>
        <!-- Gap -->
        <ColumnDefinition Width="24"/> 
        <ColumnDefinition Width="*"/>
    </Grid.ColumnDefinitions>
    
    <local:WidgetCard Grid.Column="0"/>
    <local:WidgetCard Grid.Column="2"/>
    <local:WidgetCard Grid.Column="4"/>
</Grid>

<!-- Note: For dynamic lists, use an ItemsControl with a UniformGrid ItemsPanel -->
<ItemsControl ItemsSource="{Binding Widgets}">
    <ItemsControl.ItemsPanel>
        <ItemsPanelTemplate>
            <UniformGrid Columns="3" />
        </ItemsPanelTemplate>
    </ItemsControl.ItemsPanel>
</ItemsControl>
```

### Mac (SwiftUI)
SwiftUI handles grid layouts easily via `LazyVGrid`, which automatically wraps depending on view sizes similar to CSS Grid.
```swift
struct DashboardGrid: View {
    let columns = [
        GridItem(.flexible(), spacing: 24),
        GridItem(.flexible(), spacing: 24),
        GridItem(.flexible(), spacing: 24)
    ]

    var body: some View {
        LazyVGrid(columns: columns, spacing: 24) {
            WidgetCard()
            WidgetCard()
            WidgetCard()
        }
    }
}
```
