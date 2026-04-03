## Data Tables Overview
When generating an Amortization schedule or 20-year net-worth forecast, tables are mandatory for reading row-based breakdowns. They must maintain row legibility via consistent striping padding, and sticky headers.

## Component-Specific Tokens
| Component Token | Web Equivalent | WPF (XAML) Map | Mac (SwiftUI) Map |
| :--- | :--- | :--- | :--- |
| `table-header-bg` | `bg-[#2C4A70]/5` | `Background="#0C2C4A70"` | `.background(Theme.Colors.actionPrimary.opacity(0.05))` |
| `table-header-text`| `text-[#2C4A70]` | `Foreground="{StaticResource ActionPrimaryBrush}"`| `.foregroundColor(Theme.Colors.actionPrimary)` |
| `table-row-border` | `border-slate-100`| `BorderBrush="{StaticResource ColorSlate100}"`| `Divider()` / `.background(Theme.Colors.slate100)` |
| `table-cell-pad` | `px-4 py-3` | `Padding="16,12"` | `.padding(.horizontal, 16).padding(.vertical, 12)` |

## Cross-Platform Usage Examples

### Web (React/Tailwind)
```jsx
<div className="w-full overflow-x-auto rounded-xl border border-slate-200">
  <table className="w-full text-left text-sm text-slate-900">
    <thead className="bg-[#2C4A70]/5 text-[#2C4A70] text-xs font-bold uppercase tracking-wider">
      <tr>
        <th className="px-4 py-3">Year</th>
        <th className="px-4 py-3 text-right">Net Worth</th>
      </tr>
    </thead>
    <tbody className="divide-y divide-slate-100">
      <tr className="hover:bg-slate-50 transition-colors">
        <td className="px-4 py-3 font-medium">1</td>
        <td className="px-4 py-3 text-right text-emerald-600 font-bold">₹10L</td>
      </tr>
    </tbody>
  </table>
</div>
```

### Windows (WPF XAML)
The WPF `DataGrid` is exceptionally powerful but demands strict templating to eliminate the default grey borders and behaviors to match web parity.
```xml
<Style x:Key="ForecastingDataGrid" TargetType="DataGrid">
    <Setter Property="Background" Value="White"/>
    <Setter Property="BorderBrush" Value="{StaticResource ColorSlate200}"/>
    <Setter Property="BorderThickness" Value="1"/>
    <Setter Property="RowBackground" Value="White"/>
    <Setter Property="AlternatingRowBackground" Value="{StaticResource ColorSlate50}"/>
    <Setter Property="GridLinesVisibility" Value="Horizontal"/>
    <Setter Property="HorizontalGridLinesBrush" Value="{StaticResource ColorSlate100}"/>
    <!-- Note: Further DataGridColumnHeader styling is required for the #0C2C4A70 header background -->
</Style>

<!-- In View -->
<DataGrid Style="{StaticResource ForecastingDataGrid}" AutoGenerateColumns="False" ItemsSource="{Binding ForecastRows}">
    <DataGrid.Columns>
        <DataGridTextColumn Header="Year" Binding="{Binding Year}"/>
        <DataGridTextColumn Header="Net Worth" Binding="{Binding NetWorth}" ElementStyle="{StaticResource RightAlignedEmeraldText}"/>
    </DataGrid.Columns>
</DataGrid>
```

### Mac (SwiftUI)
SwiftUI introduced the native `Table` component in macOS 12+ which beautifully mimics native OS behaviors while allowing interior cell customizations.
```swift
struct ForecastRow: Identifiable {
    let id = UUID()
    let year: String
    let netWorth: String
}

struct ForecastingTable: View {
    let rows: [ForecastRow]
    
    var body: some View {
        Table(rows) {
            TableColumn("Year", value: \.year) { row in
                Text(row.year).font(.Semantic.body.weight(.medium))
            }
            TableColumn("Net Worth", value: \.netWorth) { row in
                Text(row.netWorth)
                    .font(.Semantic.body.bold())
                    .foregroundColor(Theme.Colors.emerald500)
            }
        }
    }
}
```
