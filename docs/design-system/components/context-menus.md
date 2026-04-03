## Context Menus (Right-Click) Overview
While the Web primarily relies on explicit inline action buttons (e.g. ellipses `...` drop-downs), native application paradigms rely heavily on native Context Menus (Right-Click menus). Because this is a desktop app translation, supporting right-click operations in standard tables is highly recommended.

## Component-Specific Tokens
| Component Token | Web Equivalent | WPF (XAML) Map | Mac (SwiftUI) Map |
| :--- | :--- | :--- | :--- |
| `menu-bg` | `bg-white shadow-xl`| N/A (Standard OS ContextMenu) | N/A (Native ContextMenu) |
| `menu-item-hover` | `hover:bg-slate-50` | `Background="{StaticResource ColorSlate50}"` | Handled actively by OS |

## Cross-Platform Usage Examples

### Web (React/Tailwind)
```jsx
// Frequently mimicked via custom Div floating near point-of-click
<div className="absolute bg-white shadow-xl rounded-lg py-2 w-48 border border-slate-100 z-50">
  <button className="w-full text-left px-4 py-2 hover:bg-slate-50 text-slate-700">Edit Scenario</button>
  <button className="w-full text-left px-4 py-2 hover:bg-rose-50 text-rose-600">Delete</button>
</div>
```

### Windows (WPF XAML)
WPF controls inherently possess a `.ContextMenu` property extending to standard OS structures. These should be hooked directly into standard view items (like DataGrid Rows).
```xml
<!-- In View: Targeting a DataGrid Row -->
<DataGrid.RowStyle>
    <Style TargetType="DataGridRow">
        <Setter Property="ContextMenu">
            <Setter.Value>
                <!-- Native Context Menu Wrapper -->
                <ContextMenu>
                    <MenuItem Header="Edit Scenario" Command="{Binding EditCommand}"/>
                    <MenuItem Header="Duplicate" Command="{Binding DuplicateCommand}"/>
                    <!-- Usually stylized via global ContextMenu styles to remove vintage 3D borders -->
                    <Separator/> 
                    <MenuItem Header="Delete" Command="{Binding DeleteCommand}" Foreground="{StaticResource ColorRose500}"/>
                </ContextMenu>
            </Setter.Value>
        </Setter>
    </Style>
</DataGrid.RowStyle>
```

### Mac (SwiftUI)
Adding right-click contextual support is natively handled via `.contextMenu`. SwiftUI delegates the precise menu visuals to macOS standard OS behavior.
```swift
struct ScenarioRow: View {
    let scenario: Scenario
    
    var body: some View {
        Text(scenario.name)
            .padding()
            .contextMenu {
                Button(action: {
                    // Edit logic
                }) {
                    Label("Edit Scenario", systemImage: "pencil")
                }
                
                Button(action: {
                    // Duplicate logic
                }) {
                    Label("Duplicate", systemImage: "doc.on.doc")
                }
                
                Divider()
                
                Button(role: .destructive, action: {
                    // Delete logic
                }) {
                    Label("Delete", systemImage: "trash")
                }
            }
    }
}
```
