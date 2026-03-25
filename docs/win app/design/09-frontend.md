# Ledger Desktop — Frontend Design

**Version:** 1.0  
**Status:** Design Review

---

## 1. Overview

The frontend is a React 19 + Vite 6 + Tailwind CSS 4 application served from `wwwroot/` inside .NET's `IHost`. It runs inside a WebView2 control embedded in the WPF shell window. All backend communication happens via `fetch()` to `http://localhost:{port}` and a SignalR WebSocket connection.

The existing Ledger SaaS React app is the starting point. Several pages are adapted; new pages and components are added.

---

## 2. New and Modified Pages

### 2.1 QuickStartWizard (NEW)

**Path:** `/setup`  
**Shown when:** `GET /setup/status` returns `setupComplete: false`  
**Blocked if opened directly when setup complete:** Redirected to `/`

**Screen 1 — Folder Setup:**
```
┌──────────────────────────────────────────────────────┐
│                                                      │
│   💼 Welcome to Ledger                               │
│                                                      │
│   First, choose your LedgerDrive folder.             │
│   This is where you drop your bank statements,       │
│   PDFs, and Excel files. Ledger will watch it        │
│   and process everything automatically.              │
│                                                      │
│   LedgerDrive Location:                              │
│   [ C:\Users\Ravi\Documents\LedgerDrive ] [Browse]   │
│                                                      │
│   ℹ️  All data stays on your machine.                │
│      Nothing is ever uploaded to a server.           │
│                                                      │
│                              [Next →]                │
└──────────────────────────────────────────────────────┘
```

**Screen 2 — Profile:**
```
┌──────────────────────────────────────────────────────┐
│                                                      │
│   👤 Your Financial Profile                          │
│                                                      │
│   We use these details to automatically unlock       │
│   encrypted PDF statements.                          │
│                                                      │
│   Name *          [                    ]             │
│   Date of Birth*  [DD/MM/YYYY          ]             │
│   Mobile Number   [                    ]             │
│   PAN Number      [                    ]             │
│                                                      │
│   Currency        [INR ▼]                            │
│   Tax Regime      [New Regime ▼]                     │
│                                                      │
│   🔒 This data is stored only on this device         │
│      using Windows encryption.                       │
│                                                      │
│   [← Back]                        [Get Started →]   │
└──────────────────────────────────────────────────────┘
```

**On Submit:** `POST /setup/complete` → navigate to `/`

---

### 2.2 FilesPage (NEW)

**Path:** `/files`  
**Tab label:** Files

The central hub for tracking LedgerDrive activity. Combines real-time file status with an action center for files needing attention.

```
┌──────────────────────────────────────────────────────────────────┐
│ LedgerDrive Activity                    [Scan Now] [Open Folder] │
├──────────────────────────────────────────────────────────────────┤
│ NEEDS ATTENTION (1)                                              │
│ ┌──────────────────────────────────────────────────────────────┐ │
│ │ 🔐 union_dec_2024.pdf              Union Bank | Encrypted    │ │
│ │    Could not unlock automatically                            │ │
│ │    Password: [                           ] [Unlock]          │ │
│ └──────────────────────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────────────┤
│ PROCESSING                                                       │
│ ┌──────────────────────────────────────────────────────────────┐ │
│ │ ⏳ HDFC_Jan_2025.pdf               HDFC     | Parsing...     │ │
│ │    ████████░░░░░░░░  55%                                      │ │
│ └──────────────────────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────────────┤
│ RECENT (last 30 days)                                            │
│ ✅ HDFC_Dec_2024.pdf     HDFC    Dec 2024   117 txns   Jan 15   │
│ ✅ ICICI_Nov_2024.pdf    ICICI   Nov 2024    89 txns   Jan 12   │
│ ❌ UNION_OCT_2024.pdf    Unknown  Failed (unsupported format)   │
│ ✅ sbi_oct_2024.xlsx     SBI     Oct 2024   201 txns   Jan 10   │
└──────────────────────────────────────────────────────────────────┘
```

**SignalR integration:** Every event from `FileStatusHub` updates the relevant row in real time without full refresh.

---

### 2.3 ProposalsPage (ADAPTED from existing)

**Path:** `/proposals`  
**Tab label:** "Review & Approve"

Natural-language heading and labels replace all technical terms. Confidence badge replaced by friendly trust indicator.

```
┌───────────────────────────────────────────────────────────────────┐
│ Waiting for your approval (45)     [✅ Approve the confident ones] [Filter ▼]│
├───────────────────────────────────────────────────────────────────┤
│ Date       │ What happened            │ Amount  │ Category    │ Confidence│
│ Jan 15     │ Swiggy food order        │ ₹485    │ Food 🟢     │ Very sure │
│ Jan 15     │ Salary credited          │ ₹50,000 │ Salary 🟡  │ Fairly sure│
│ Jan 14     │ Amazon purchase          │ ₹1,299  │ Shopping 🟢 │ Very sure │
└───────────────────────────────────────────────────────────────────┘
  [✅ Approve these] [Rename or fix] [❌ Not this one]

Keys: A = approve, E = edit, R = reject, ↑↓ = move, Space = select
```

Confidence display: 🟢 Very sure (≥ 85%) | 🟡 Fairly sure (60–84%) | 🔴 Not sure (< 60%)

No raw percentages or decimal scores are shown to the user.

---

### 2.4 Dashboard — "Your Financial Picture" (REDESIGNED)

**Path:** `/`  
**Title:** "Your Financial Picture" (replaces generic "Dashboard")

The dashboard is a fully **customisable dashlet grid**. The user decides which cards to show, where to place them, and how large they should be. Layout is saved automatically.

#### Default Layout (first launch)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Your Financial Picture                     [+ Add a card] [↺ Reset]   │
├───────────────────────────┬───────────────────────────┬─────────────────────┐
│  ⚙ How much am I worth?    │   ⚙ This month so far        │   ⚙ Files activity   │
│  ₹8,24,350               │   Earned:    ₹85,000          │   ✅ 3 done           │
│  ▲ ₹34,200 vs last month  │   Spent:     ₹42,350          │   ⏳ 1 in progress   │
│  [See the full trend]     │   Saved:   + ₹42,650          │   🔐 1 needs password │
│                           │   [Full breakdown]           │   [See all files]  │
├───────────────────────────┼───────────────────────────┼─────────────────────┤
│  ⚙ Where did my money go?  │   ⚙ Waiting for approval      │   ⚙ Am I on budget?  │
│  [Donut chart by category]│   45 transactions to review  │   Food:   92%      │
│  Food 38% │ Bills 22%    │   [Review and approve them]   │   Travel: 45%      │
│  EMIs 18% │ Other 22%    │                               │   Bills: 110% ⚠   │
│  [Explore details]        │                               │   [See all]       │
└───────────────────────────┴───────────────────────────┴─────────────────────┘
```

Drag handle (⚙) on each card header allows repositioning. Resize grip on each card's bottom-right corner. X button on hover to remove the card.

#### Available Dashlets Catalogue

All dashlets available to add via "+ Add a card":

| Dashlet Key | Friendly Name | Default Size |
|---|---|---|
| `net_worth` | How much am I worth? | Medium |
| `monthly_summary` | This month so far | Medium |
| `file_activity` | Files activity | Small |
| `spending_breakdown` | Where did my money go? | Medium |
| `pending_approvals` | Waiting for approval | Small |
| `budget_status` | Am I on budget? | Small |
| `net_worth_chart` | My net worth over time | Large |
| `recent_transactions` | What I spent recently | Medium |
| `goal_progress` | Working towards my goals | Small |
| `cash_flow` | Money in vs money out | Medium |
| `tax_summary` | Tax snapshot this year | Small |
| `bank_balances` | My account balances | Small |
| `lending_summary` | Money I've lent out | Small |
| `folio_insights` | How my investments are spread | Medium |
| `emi_prepayment` | Pay off my home loan faster | Medium |
| `family_overview` | How's the family doing? | Large (v2 only) |
| `ai_insight` | What Ledger noticed | Small (requires LLM) |

#### Drag-and-Drop Implementation

```jsx
// Dashboard.jsx
import GridLayout from 'react-grid-layout';
import 'react-grid-layout/css/styles.css';

export function Dashboard() {
    const { layout, setLayout, dashlets } = useDashletStore();
    const [showPicker, setShowPicker] = useState(false);

    const onLayoutChange = (newLayout) => {
        setLayout(newLayout);   // Persists to API: PATCH /settings { dashboard_layout: JSON }
    };

    return (
        <div className="dashboard">
            <header>
                <h1>Your Financial Picture</h1>
                <button onClick={() => setShowPicker(true)}>+ Add a card</button>
                <button onClick={resetLayout}>Reset</button>
            </header>

            <GridLayout
                className="layout"
                layout={layout}
                cols={12}
                rowHeight={120}
                width={containerWidth}
                draggableHandle=".dashlet-drag-handle"
                onLayoutChange={onLayoutChange}
                compactType="vertical"      // auto-collapse empty space
                preventCollision={false}
            >
                {dashlets.map(d => (
                    <div key={d.id} data-grid={d.grid}>
                        <DashletFrame key={d.id} dashlet={d} />
                    </div>
                ))}
            </GridLayout>

            {showPicker && (
                <DashletPicker
                    activeDashlets={dashlets.map(d => d.key)}
                    onAdd={key => addDashlet(key)}
                    onClose={() => setShowPicker(false)}
                />
            )}
        </div>
    );
}
```

#### DashletFrame

```jsx
// Wraps every dashlet with drag handle, title, and remove button
function DashletFrame({ dashlet, onRemove }) {
    return (
        <div className="dashlet-frame">
            <div className="dashlet-header">
                <span className="dashlet-drag-handle">⚙</span>
                <span className="dashlet-title">{dashlet.label}</span>
                <button className="dashlet-remove" onClick={() => onRemove(dashlet.id)}
                    title="Remove this card">×</button>
            </div>
            <div className="dashlet-body">
                <dashlet.Component />
            </div>
        </div>
    );
}
```

#### Dashlet Picker Drawer

```
┌────────────────────────────────────────┐
│ Add a card to your dashboard       × │
├────────────────────────────────────────┤
│ [Search cards...              ]    │
│                                    │
│ ✔ How much am I worth?   (on)      │
│ ✔ This month so far      (on)      │
│ + My net worth over time           │
│ + What I spent recently            │
│ + Working towards my goals         │
│ + Tax snapshot this year           │
└────────────────────────────────────────┘
```

#### Layout Persistence

```javascript
// useDashletStore.js (Zustand)
const useDashletStore = create((set) => ({
    layout: DEFAULT_LAYOUT,
    dashlets: DEFAULT_DASHLETS,

    setLayout: async (newLayout) => {
        set({ layout: newLayout });
        await api.patch('/settings', {
            dashboard_layout: JSON.stringify(newLayout)
        });
    },

    addDashlet: (key) => set(state => ({
        dashlets: [...state.dashlets, DASHLET_CATALOG[key]]
    })),

    removeDashlet: (id) => set(state => ({
        dashlets: state.dashlets.filter(d => d.id !== id)
    })),

    resetLayout: async () => {
        set({ layout: DEFAULT_LAYOUT, dashlets: DEFAULT_DASHLETS });
        await api.patch('/settings', { dashboard_layout: null });
    }
}));
```

On startup: `GET /settings` returns `dashboard_layout` JSON. If null, `DEFAULT_LAYOUT` is used.

**Family View toggle (v2 — hidden in v1):**
```
[My view] [👨‍👩‍👧 Family view]   ← shown only when family_mode_enabled = true
When Family view selected: all dashlets switch to consolidated family data
```

---

### 2.5 ProfilePage (NEW)

**Path:** `/profile`  
**Tab label:** Profile (in Settings sidebar or top nav)

```
┌──────────────────────────────────────────────────────┐
│ Your Profile                          [Edit] [Save]  │
├──────────────────────────────────────────────────────┤
│ Display Name     Ravi Kumar                          │
│ Date of Birth    ****-04-15 (partial shown)          │
│ PAN Number       ABCDE****F (partial shown)          │
│ Mobile Number    9876****10 (partial shown)          │
│ Currency         INR                                 │
│ Tax Regime       New Regime (FY 2024–25)             │
├──────────────────────────────────────────────────────┤
│ 🔒 Security                                          │
│ PIN Lock:    [Enabled]    [Change PIN] [Disable PIN] │
│ Auto-Lock:   [After 5 min ▼]                         │
├──────────────────────────────────────────────────────┤
│ ℹ️  Password Cracking Hints                          │
│ Ledger uses your DOB, PAN, mobile, and name to       │
│ attempt unlocking encrypted PDF statements.          │
│ [Manage Password Hints]                              │
└──────────────────────────────────────────────────────┘
```

---

### 2.6 SettingsPage (ADAPTED)

**Path:** `/settings`

Add new settings panels:
- **LedgerDrive:** Folder location, change folder, force rescan
- **AI Assistant:** Provider, API key, model, Privacy Mode default
- **Security:** PIN enable/disable, auto-lock timeout, audit log view
- **Appearance:** Theme (Light/Dark/System), compact mode
- **About:** Version, changelog, check for updates

---

## 3. New Components

### 3.1 FileActivityRow
```jsx
// Single file status row for FilesPage
// All status values mapped to plain English before display
const STATUS_LABELS = {
    Vaulted:          'Saved safely',
    Detecting:        'Figuring out what this is…',
    PasswordRequired: 'We need your password 🔐',
    Parsing:          'Reading your statement…',
    Normalized:       'Cleaning up the numbers…',
    Deduplicating:    'Checking for duplicates…',
    Categorizing:     'Sorting into categories…',
    Proposing:        'Getting ready for your review…',
    Organized:        'Done ✓',
    Failed:           "Couldn't process this file",
    Unsupported:      "We don't support this file type yet",
    Removed:          'Removed'
};

function FileActivityRow({ file, onUnlock }) {
    const [password, setPassword] = useState('');
    const statusLabel = STATUS_LABELS[file.status] ?? file.status;
    return (
        <div className={`file-row status-${file.status.toLowerCase()}`}>
            <StatusIcon status={file.status} />
            <span className="file-name">{file.originalName}</span>
            <span className="bank-badge">{file.detectedBank}</span>
            <span className="file-status-label">{statusLabel}</span>
            {file.status === 'Parsing' && <ProgressBar pct={file.progressPct} />}
            {file.status === 'PasswordRequired' && (
                <form onSubmit={() => onUnlock(file.id, password)}>
                    <input type="password" value={password}
                        onChange={e => setPassword(e.target.value)}
                        placeholder="Enter the PDF password" />
                    <button type="submit">Unlock this file</button>
                </form>
            )}
        </div>
    );
}
```

### 3.2 ChatWidget (ADAPTED)
```jsx
function ChatWidget() {
    const [privacyMode, setPrivacyMode] = usePrivacyModeSetting();
    return (
        <div className="chat-widget">
            <div className="privacy-bar">
                <LockIcon locked={privacyMode} />
                <span>Privacy Mode: {privacyMode ? 'ON' : 'OFF'}</span>
                <Toggle checked={privacyMode} onChange={setPrivacyMode} />
            </div>
            {!privacyMode && (
                <div className="privacy-warning">
                    ⚠️ Your real financial data will be sent to the AI provider.
                </div>
            )}
            <MessageList />
            <MessageInput onSend={handleSend} />
        </div>
    );
}
```

### 3.3 PinLockScreen
```jsx
// Shown when app auto-locks. Covers entire WebView2 area.
function PinLockScreen({ onUnlock }) {
    const [pin, setPin] = useState('');
    const [error, setError] = useState(null);

    const handleSubmit = async () => {
        const res = await api.post('/settings/pin/verify', { pin });
        if (res.valid) { onUnlock(); }
        else { setError('Incorrect PIN. Try again.'); setPin(''); }
    };

    return (
        <div className="pin-lock-overlay">
            <div className="pin-box">
                <h2>🔒 Ledger is Locked</h2>
                <PinInput value={pin} onChange={setPin} length={6} />
                {error && <p className="error">{error}</p>}
                <button onClick={handleSubmit}>Unlock</button>
            </div>
        </div>
    );
}
```

### 3.4 NetWorthWidget (ADAPTED)
```jsx
// Supports memberId filter for Family View (v2)
function NetWorthWidget({ memberId = null }) {
    const { data } = useNetWorthQuery(memberId);
    return (
        <div className="net-worth-card">
            <h3>{memberId ? `${data.memberName}'s Net Worth` : 'Your Net Worth'}</h3>
            <p className="amount">₹{data.total.toLocaleString('en-IN')}</p>
            <NetWorthChart history={data.history} />
        </div>
    );
}
```

### 3.5 LendingSummaryDashlet (NEW)

Shows outstanding loans lent to or borrowed from friends/family.

```
┌─────────────────────────────────────────────┐
│ 💸 Money I've lent out             [Details] │
├─────────────────────────────────────────────┤
│ Outstanding                          ₹42,000 │
│ Overdue (2 people)                   ₹18,000 │
│ Interest earned this year             ₹2,100 │
├─────────────────────────────────────────────┤
│ Ravi Kumar    ₹15,000  Due 15 Apr   ✅ On time│
│ Priya Sharma  ₹18,000  Due Mar 1   ⚠️ Overdue │
│ Nitin         ₹ 9,000  No due date            │
│                                   [+ Record] │
└─────────────────────────────────────────────┘
```

**Data source:** `GET /lending` → `ManualLoan[]` with computed `balance_remaining`  
**Quick action:** "+ Record" opens a modal for new loan or repayment entry  
**Color coding:** red row for overdue, yellow for due within 7 days, green for on-time

### 3.6 FolioInsightsDashlet (NEW)

Surfaces portfolio concentration warnings and rebalance suggestions.

```
┌─────────────────────────────────────────────────────┐
│ 📊 How my investments are spread         [Details]  │
├─────────────────────────────────────────────────────┤
│  ⚠️  HDFC Flexicap makes up 38% of your portfolio   │
│      Consider spreading some into an index fund.    │
├─────────────────────────────────────────────────────┤
│ Equity (large-cap)   ████████████░░░  62%           │
│ Equity (mid/small)   ████░░░░░░░░░░░  18%           │
│ Debt / Liquid        ███░░░░░░░░░░░░  12%           │
│ Other                ██░░░░░░░░░░░░░   8%           │
├─────────────────────────────────────────────────────┤
│ ⚠️  Overlap alert: HDFC Top 100 + ICICI Bluechip    │
│     share ~70% of holdings — you may be doubling up │
│                                  [See suggestions]  │
└─────────────────────────────────────────────────────┘
```

**Data source:** `GET /insights/folio` — aggregates from `Assets\Investments` parsed holdings  
**Concentration threshold:** configurable, default 30%  
**Disclaimer:** always shown — "These are informational observations, not financial advice."

### 3.7 EmiPrepaymentDashlet (NEW)

Lets user see the benefit of paying extra on their home loan.

```
┌─────────────────────────────────────────────────────────────┐
│ 🏠 Pay off my home loan faster               [Edit details] │
├─────────────────────────────────────────────────────────────┤
│ HDFC Home Loan  —  ₹32L outstanding  —  8.5% p.a.          │
├───────────────────────────────┬─────────────────────────────┤
│ Current plan                  │ If I pay ₹5,000 extra/month │
│ ████████████████████░░░░░░░░  │ ████████████░░░░░░░░░░░░░░░ │
│ Done in: Feb 2042             │ Done in: Jun 2037 🎉         │
│ Total interest: ₹18.4L        │ Total interest: ₹13.2L      │
│                               │ You save: ₹5.2L             │
├───────────────────────────────┴─────────────────────────────┤
│ Extra per month:  ─○──────────────  ₹5,000  (drag to change)│
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 📢 Paying ₹5,000 extra per month saves ₹5.2L in     │   │
│  │    interest and closes your loan 4 years 8 months   │   │
│  │    earlier.                                          │   │
│  └──────────────────────────────────────────────────────┘   │
│                                     [Lump-sum calculator]   │
└─────────────────────────────────────────────────────────────┘
```

**Data source:** `GET /insights/emi/{loanId}` → `HomeLoanProfile`; calculations via `GET /insights/emi/{loanId}/prepayment?extra={amount}`  
**Slider range:** ₹0 – ₹50,000 (configurable)  
**Lump-sum tab:** separate view for one-time prepayment calculation

---

## 4. Routing

```jsx
// App.jsx
function App() {
    const { setupComplete, loading } = useSetupStatus();

    if (loading) return <SplashScreen />;
    if (!setupComplete) return <QuickStartWizard />;

    return (
        <PinGate>
            <Layout>
                <Routes>
                    <Route path="/"           element={<Dashboard />} />
                    <Route path="/files"      element={<FilesPage />} />
                    <Route path="/proposals"  element={<ProposalsPage />} />
                    <Route path="/accounts"   element={<AccountsPage />} />
                    <Route path="/reports/*"  element={<ReportsPage />} />
                    <Route path="/lending"    element={<LendingPage />} />
                    <Route path="/folio"      element={<FolioPage />} />
                    <Route path="/profile"    element={<ProfilePage />} />
                    <Route path="/settings"   element={<SettingsPage />} />
                    <Route path="/chat"       element={<ChatPage />} />
                </Routes>
            </Layout>
        </PinGate>
    );
}
```

**PinGate:** HOC that checks PIN lock status and shows `PinLockScreen` when locked. Becomes active only if PIN is enabled and auto-lock timer has fired.

---

## 5. SignalR Client Setup

```javascript
// frontend/src/hooks/useFileHub.js
import * as signalR from '@microsoft/signalr';
import { useEffect, useCallback } from 'react';
import { useFileStore } from '../stores/fileStore';

export function useFileHub() {
    const updateFile = useFileStore(s => s.updateFile);

    useEffect(() => {
        const conn = new signalR.HubConnectionBuilder()
            .withUrl('/hubs/files')
            .withAutomaticReconnect([1000, 2000, 5000, 10000])
            .configureLogging(signalR.LogLevel.Warning)
            .build();

        const events = [
            'file.vaulted', 'file.detected', 'file.parsing', 'file.parsed',
            'file.proposing', 'file.organized', 'file.failed',
            'file.pw_required', 'file.removal_pending', 'proposal.created'
        ];

        events.forEach(evt => conn.on(evt, payload => updateFile(evt, payload)));

        conn.start().catch(console.error);
        return () => conn.stop();
    }, [updateFile]);
}
```

---

## 6. State Management

Zustand stores (lightweight, no Redux):

| Store | Purpose |
|---|---|
| `fileStore` | FilesPage queue — updated by SignalR events |
| `proposalStore` | Pending proposals count (for badge) |
| `settingsStore` | App settings cache |
| `profileStore` | User profile |
| `pinStore` | PIN lock state (locked/unlocked, last activity time) |
| `dashletStore` | Dashboard layout + active dashlets list, persisted to app_settings |
| `familyStore` | (v2) Family members, active view mode |

---

## 7. API Client

```javascript
// frontend/src/api/client.js
const BASE = window.LEDGER_API_BASE ?? 'http://localhost:5000';

export const api = {
    get:    (path)        => fetch(`${BASE}${path}`).then(r => r.json()),
    post:   (path, body)  => fetch(`${BASE}${path}`, { method: 'POST',  headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) }).then(r => r.json()),
    patch:  (path, body)  => fetch(`${BASE}${path}`, { method: 'PATCH', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) }).then(r => r.json()),
    delete: (path)        => fetch(`${BASE}${path}`, { method: 'DELETE' }).then(r => r.json()),
};
```

`window.LEDGER_API_BASE` is injected by the WPF shell via `WebView2.CoreWebView2.AddHostObjectToScript` or a `script` tag injected before the SPA loads:

```csharp
// MainWindow.xaml.cs — after NavigateToString or NavigateToLocalHost
webView.CoreWebView2.AddScriptToExecuteOnDocumentCreatedAsync(
    $"window.LEDGER_API_BASE = 'http://localhost:{_backendPort}';"
);
```

---

## 9. UX Language Standards

Every user-visible string must use plain, conversational language. The guiding principle: write as if talking to a family member who has never used accounting software.

### 9.1 Navigation Labels

| Technical Name | Displayed As |
|---|---|
| Dashboard | Your Financial Picture |
| Proposals | Review & Approve |
| Accounts | My Accounts |
| Reports | Reports & Insights |
| Files | LedgerDrive Files |
| Lending | Money I've Lent |
| Folio | My Investments |
| Settings | Settings |
| Profile | My Profile |

### 9.2 Button & Action Labels

| Action | Button Text |
|---|---|
| Approve proposal | "Looks right" or "Approve" |
| Approve all high-confidence | "Approve the confident ones" |
| Reject proposal | "Not this one" |
| Submit password | "Unlock this file" |
| Remove transactions | "Yes, remove them" |
| Cancel destructive action | "No, keep them" |
| Add dashlet | "+ Add a card" |
| Reset dashboard | "Reset to default" |
| Enable PIN | "Protect with a PIN" |
| Run vault integrity check | "Check my backup files are intact" |

### 9.3 Empty States

| Screen | Empty State Message |
|---|---|
| Dashboard (no transactions) | "Drop a bank statement into your LedgerDrive folder to get started. We'll handle the rest." |
| Proposals (nothing to review) | "You're all caught up — no transactions waiting for your approval." |
| Files page (no files yet) | "Your LedgerDrive folder is empty. Drop any bank statement, PDF, or Excel file here." |
| Transactions (no results) | "No transactions found for this period." |
| Reports (no data) | "No data yet. Import some statements first and then come back here." |

### 9.4 Status Indicators

Status terms are never shown in raw form. All pipeline states map to natural-language strings via the `STATUS_LABELS` object defined in `FileActivityRow`. The confidence score (a number like `0.92`) is always rendered as a word: "Very sure", "Fairly sure", or "Not sure".

### 9.5 Confirmation Dialogs

Confirmations state the exact consequence, not just "Are you sure?":

```
// Deleting a processed file
"Removing this file will delete 117 transactions from your ledger.
 Your original file is safely backed up in the vault.
 Do you want to continue?"

[Yes, remove them]   [No, keep them]

// Clearing the vault
"This will permanently delete all 48 backed-up originals in your vault.
 This cannot be undone.
 Type CLEAR to confirm:"

[________________]   [Cancel]
```

### 9.6 Toast Messages (Natural Language)

```javascript
// toastMessages.js — all user-facing toast strings
export const TOAST = {
    fileOrganized:   (bank, period, count) =>
        `${bank} ${period} is ready — ${count} transactions waiting for your approval`,
    passwordNeeded:  (name) =>
        `We couldn't unlock "${name}". Tap here to enter the password.`,
    alreadyImported: () =>
        `You already imported this file — skipping it.`,
    parseFailed:     (name) =>
        `We had trouble reading "${name}". You can try again or skip it.`,
    duplicateWarning:(bank, period) =>
        `You already have ${bank} ${period} transactions. Import anyway?`,
    updateAvailable: (version) =>
        `Ledger ${version} is ready to install.`,
    vaultLowDisk:    (gb) =>
        `Your backup folder is using ${gb} GB. You can manage this in Settings.`,
};
```

### 9.7 Dependencies

```json
{
  "react-grid-layout": "^1.4.4"
}
```

`react-grid-layout` powers the drag-and-drop dashlet grid. It is the only new frontend dependency introduced by the dashboard customisation feature.

```
App launch
    │
    ├─ WPF MainWindow opens
    ├─ IHost.StartAsync() → Kestrel on ephemeral port
    ├─ WebView2.Navigate(http://localhost:{port})
    │
    └─ React loads → App.jsx
            │
            ├─ GET /setup/status
            │       setupComplete: false
            │
            └─ <QuickStartWizard />
                    Screen 1: Choose folder
                    Screen 2: Profile
                    POST /setup/complete
                    navigate("/")
                    │
                    └─ <Dashboard />
                            FileWatcher started ✅
                            "Drop files in LedgerDrive to begin" empty state
```
