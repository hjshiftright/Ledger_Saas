## Tech Debt Report
The codebase exhibits significant technical debt regarding hardcoded color values. While Tailwind CSS provides a robust theme palette, components frequently bypass it by using arbitrary value utilities (e.g., `bg-[#2C4A70]`). 

Below is an inventory of notable deviations that must be consolidated into the Tier 2 (Semantic Aliases) token structure.

### Hardcoded `#2C4A70` (Cobalt Blue)
This is acting as the primary brand/action color but is manually declared in dozens of places.
- `WealthDashboard.jsx` - Appears in roughly 40+ variations (`bg-[#2C4A70]/5`, `text-[#2C4A70]`, `border-[#2C4A70]`). Used for chart lines, active states, buttons, badges, and textual highlights.
- `ReportsPage.jsx` - Used in subtext: `className="mt-2 text-xs text-[#2C4A70]"` and chart paths.
- `OnboardingV4.jsx` - Found constantly in secondary buttons: `bg-indigo-50 text-[#2C4A70]`.
- Various Dashboards - Used as main chart hex colors: `stroke="#2C4A70"`.

### Hardcoded Chart / Status Colors
Chart implementations (Recharts) rely purely on hex codes rather than CSS variables mapped to Tailwind.
- `#22c55e` (Emerald 500) - Used for 'Cash & Bank' categories, 'great' status indicators, Income bars/lines.
- `#f43f5e` (Rose 500) / `#ef4444` (Red 500) - Used for Expenses, 'low'/'negative' status, Real Estate.
- `#f59e0b` (Amber 500) - Used for Provident Funds and warning/mediocre states.
- `#6366f1` / `#8b5cf6` / `#a855f7` (Indigo / Violet / Purple tailwind values) - Hardcoded into SVG gradients in the WealthDashboard instead of deriving from classes.
- Target: `<stop offset="5%" stopColor="#6366f1" />`

### Non-Standard Spacing / Sizing
- `index.css`: `.custom-scrollbar::-webkit-scrollbar { width: 6px; }` (Uses explicit px rather than standard token space).
- Inline height overrides: `width={70}`, `height={28}` on charts and graphical hero items.

### Recommendation
All hardcoded hex colors should be replaced. 
1. Define `cobalt: { 500: '#2C4A70' }` inside `tailwind.config.js`.
2. Convert all Recharts graph colors into CSS custom properties injected via a theme provider or mapped to CSS variables like `var(--color-status-success)` to ensure dark mode compatibility.
