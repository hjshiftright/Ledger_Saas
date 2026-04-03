## Charts & Data Visualization Overview
The standard web app heavily leverages `Recharts` for dynamic line, area, and bar graphing (e.g. Net Worth velocity, category spending). Hardcoded semantic colors dictate visual data representation, dividing statuses like income, expenses, and specific asset categories.

## Component-Specific Tokens
| Token Category / Meaning | Hex Value | Web (Recharts) | WPF (XAML) Example | Mac (SwiftUI) Example |
| :--- | :--- | :--- | :--- | :--- |
| **Income / Success** | `#22C55E` | `<Line stroke="#22c55e">` | `Fill="{StaticResource ColorEmerald500}"`| `.foregroundStyle(Theme.Colors.emerald500)` |
| **Expenses / Negative** | `#F43F5E` | `<Area stroke="#f43f5e">` | `Fill="{StaticResource ColorRose500}"` | `.foregroundStyle(Theme.Colors.rose500)` |
| **Net Worth / Primary** | `#6366F1` | `<Area stroke="#6366f1">` | `Fill="{StaticResource ColorIndigo600}"`| `.foregroundStyle(Theme.Colors.indigo600)` |
| Chart Grid Lines | `#F1F5F9` | `<CartesianGrid stroke="#f1f5f9">`| `Stroke="{StaticResource ColorSlate100}"` | `.gridLine(stroke: Theme.Colors.slate100)` |
| Chart Axis Tezt | `#94A3B8` | `tick={{fill: '#94a3b8'}}`| `Foreground="{StaticResource ColorSlate400}"` | `.foregroundStyle(Theme.Colors.slate400)` |

## Semantic Asset Map (Pie Charts)
To ensure that pie charts across Desktop and Web always represent the same asset types identically:
- **Cash & Bank:** Emerald (`#22C55E`)
- **Equities:** Cobalt (`#2C4A70`)
- **Real Estate:** Red (`#EF4444`)
- **Provident Funds:** Amber (`#F59E0B`)

## Cross-Platform Usage Examples

### Web (React/Recharts)
```jsx
<AreaChart data={data}>
  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
  <XAxis dataKey="label" tick={{ fill: '#94a3b8' }} />
  
  <Area type="monotone" dataKey="net_worth" stroke="#6366f1" fill="url(#nwGrad)" />
  <Area type="monotone" dataKey="liabilities" stroke="#f43f5e" fill="none" strokeDasharray="4 2" />
</AreaChart>
```

### Windows (WPF XAML)
Because WPF does not include a robust first-party charting package, it is highly recommended to bridge `LiveCharts2` or `OxyPlot` and map the visual brushes appropriately through XAML logic.
```xml
<!-- Example mapping to LiveCharts2 (CartesianChart) -->
<lvc:CartesianChart Series="{Binding NetWorthSeries}">
    <!-- Ensure axis ticks map to our design system -->
    <lvc:CartesianChart.XAxes>
        <lvc:Axis LabelsPaint="{StaticResource ColorSlate400_SKPaint}" />
    </lvc:CartesianChart.XAxes>
</lvc:CartesianChart>

<!-- In ViewModel (C# bindings driving the graphics) -->
<!-- new LineSeries<double> { Stroke = new SolidColorPaint(SKColors.Parse("#6366F1")) } -->
```

### Mac (SwiftUI)
SwiftUI 4+ natively contains the highly performant `SwiftUI Charts` framework, making mapping exact equivalents incredibly native.
```swift
import Charts
import SwiftUI

struct WealthChartView: View {
    let data: [WealthPoint]

    var body: some View {
        Chart(data) { point in
            // Net Worth Area
            AreaMark(
                x: .value("Month", point.month),
                y: .value("Net Worth", point.netWorth)
            )
            .foregroundStyle(
                LinearGradient(colors: [Theme.Colors.indigo600.opacity(0.8), Theme.Colors.indigo600.opacity(0.1)], startPoint: .top, endPoint: .bottom)
            )

            // Liabilities Line (Dashed)
            LineMark(
                x: .value("Month", point.month),
                y: .value("Liabilities", point.liabilities)
            )
            .foregroundStyle(Theme.Colors.rose500)
            .lineStyle(StrokeStyle(lineWidth: 2, dash: [4, 2]))
        }
        .chartXAxis {
            AxisMarks(values: .automatic) { _ in
                AxisGridLine(stroke: StrokeStyle(lineWidth: 1, dash: [3,3])).foregroundStyle(Theme.Colors.slate100)
                AxisValueLabel().foregroundStyle(Theme.Colors.slate400)
            }
        }
    }
}
```
