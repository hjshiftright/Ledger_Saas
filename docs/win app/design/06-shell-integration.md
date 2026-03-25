# Ledger Desktop — Windows Shell Integration

**Version:** 1.0  
**Status:** Design Review

---

## 1. Overview

Shell integration makes LedgerDrive feel like a first-class Windows citizen — similar to OneDrive or Dropbox. Files show status at a glance, right-click menus work anywhere in Explorer, Windows Search finds organized statements by bank name and year, and toast notifications appear natively in the Windows Notification Center.

---

## 2. Shell Extension Project

`Ledger.ShellExtension` is a separate COM-visible .NET 9 DLL registered by the MSIX installer. It runs inside the Windows Explorer process, so it must be:
- Lightweight (no heavy service loads)
- Read-only DB access (never writes to the SQLCipher DB)
- Crash-safe (exceptions cannot bring down Explorer)

```
Ledger.ShellExtension.dll
├── LedgerOverlayHandler.cs     IShellIconOverlayIdentifier
├── LedgerContextMenu.cs        IContextMenu / SharpContextMenu
└── SearchPropertyHandler.cs   IPropertyStore for Windows Search
```

**Registration (via MSIX custom action):**
```cmd
SharpShell /install /type=x64 Ledger.ShellExtension.dll
```

This writes to:
- `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\ShellIconOverlayIdentifiers\LedgerSyncing`
- `HKLM\SOFTWARE\Classes\CLSID\{...}\InProcServer32 = Ledger.ShellExtension.dll`
- `HKCR\*\shellex\ContextMenuHandlers\LedgerContextMenu`

**Code Signing Requirement:** SharpShell overlay handlers require a code-signed DLL. EV code signing certificate is mandatory (see doc 11—Packaging).

---

## 3. File Overlay Icons

### 3.1 States

| State | Icon | Meaning |
|---|---|---|
| `Syncing` | Animated spinner (static ICO: clock) | File queued or being processed |
| `Done` | Green checkmark | File fully processed, transactions in ledger |
| `Error` | Red X | File failed after 3 parse attempts |
| `Missing` | Yellow warning triangle | File is in FileRegistry but not on disk |

Icons are bundled as four `.ico` files in ShellExtension resources. Each `.ico` contains multiple sizes: 16×16, 32×32, 48×48 (required by Windows Shell).

### 3.2 LedgerOverlayHandler

```csharp
[ComVisible(true)]
[ClassInterface(ClassInterfaceType.None)]
public class LedgerOverlayHandler : SharpIconOverlayHandler
{
    private readonly ShellOverlayState _targetState;
    private static readonly SqliteConnection _readonlyConn =
        new SqliteConnection($"Data Source={DbPath};Mode=ReadOnly");

    protected override bool CanShowOverlay(string path, FILE_ATTRIBUTE attributes)
    {
        if (!path.StartsWith(GetLedgerDrivePath(), StringComparison.OrdinalIgnoreCase))
            return false;

        var state = GetState(path);
        return state == _targetState;
    }

    protected override int GetPriority() => _targetState switch {
        ShellOverlayState.Error   => 1,   // highest priority
        ShellOverlayState.Missing => 2,
        ShellOverlayState.Syncing => 3,
        ShellOverlayState.Done    => 10,
        _                         => 50
    };

    private ShellOverlayState GetState(string path)
    {
        // Read-only query — never write
        const string sql = """
            SELECT shell_overlay_state
            FROM file_registry
            WHERE organized_path = @path OR original_path = @path
            LIMIT 1
            """;
        _readonlyConn.Open();
        using var cmd = new SqliteCommand(sql, _readonlyConn);
        cmd.Parameters.AddWithValue("@path", path);
        var result = cmd.ExecuteScalar() as string;
        return Enum.TryParse<ShellOverlayState>(result, out var s) ? s : ShellOverlayState.Missing;
    }
}
```

**Four registered classes** (one per state), each registered in its own CLSID:
```
LedgerOverlaySyncing  { _targetState = Syncing }
LedgerOverlayDone     { _targetState = Done }
LedgerOverlayError    { _targetState = Error }
LedgerOverlayMissing  { _targetState = Missing }
```

**Windows Slot Limit:** Windows Explorer supports only 15 overlay handlers. At install, check current count. If >= 12 (leaving slot headroom for system handlers), warn user:
> "Ledger overlay icons may not display because too many icon overlay handlers are installed. You can disable OneDrive or Dropbox overlays in their settings."

### 3.3 ShellOverlayState Update (from main app)

The main app process updates `FileRegistry.ShellOverlayState` in the DB. The next time Explorer refreshes or the user navigates to the folder, the overlay handler reads the new state.

Force refresh via the main app:
```csharp
// After organizing a file
SHChangeNotify(SHCNE_UPDATEITEM, SHCNF_PATH | SHCNF_FLUSHNOWAIT, organizedPath, null);
```

---

## 4. Context Menu

### 4.1 Menu Items

**When right-clicking inside LedgerDrive:**
```
------ [standard Explorer items] ------
📥 Add to LedgerDrive         (copy this file to LedgerDrive root)
🔍 View in Ledger             (bring app window to foreground, navigate to file record)
📁 View Vault Copy            (open .vault\ counterpart in Explorer)
```

**When right-clicking any file OUTSIDE LedgerDrive:**
```
------ [standard Explorer items] ------
📥 Add to LedgerDrive
```

### 4.2 LedgerContextMenu

```csharp
[ComVisible(true)]
public class LedgerContextMenu : SharpContextMenu
{
    protected override bool CanShowMenu()
    {
        // Show for all files (Add to LedgerDrive)
        // Show "View in Ledger" only for LedgerDrive files
        return SelectedItemPaths.Any(p => File.Exists(p));
    }

    protected override ContextMenuStrip CreateMenu()
    {
        var menu = new ContextMenuStrip();
        var ledgerDrivePath = GetLedgerDrivePath();
        bool isInsideLedgerDrive = SelectedItemPaths
            .All(p => p.StartsWith(ledgerDrivePath, StringComparison.OrdinalIgnoreCase));

        menu.Items.Add("Add to LedgerDrive", Resources.LedgerIcon, (s, e) =>
            OnAddToLedgerDrive());

        if (isInsideLedgerDrive)
        {
            menu.Items.Add("View in Ledger", Resources.LedgerIcon, (s, e) =>
                OnViewInLedger());
            menu.Items.Add("View Vault Copy", Resources.VaultIcon, (s, e) =>
                OnViewVaultCopy());
        }

        return menu;
    }

    private void OnAddToLedgerDrive()
    {
        foreach (var path in SelectedItemPaths)
        {
            var dest = Path.Combine(GetLedgerDrivePath(), Path.GetFileName(path));
            File.Copy(path, dest, overwrite: false);
        }
    }

    private void OnViewInLedger()
    {
        var hash = ComputeSha256(SelectedItemPaths.First());
        // Activate app via named pipe message
        NamedPipeClient.SendCommand($"openFile:{hash}");
    }

    private void OnViewVaultCopy()
    {
        var hash = ComputeSha256(SelectedItemPaths.First());
        var vaultPath = LookupVaultPath(hash);
        if (vaultPath != null)
            Process.Start("explorer.exe", $"/select,\"{vaultPath}\"");
    }
}
```

---

## 5. Custom Folder Icon

Written by `LedgerDriveManager.InitializeFolderAsync()` — no COM registration needed:

```csharp
// Copy Folder.ico from app resources into LedgerDrive root
File.WriteAllBytes(Path.Combine(ledgerDrivePath, "Folder.ico"), 
    ResourceHelper.GetBytes("LedgerDrive.ico"));

// Write desktop.ini
File.WriteAllText(Path.Combine(ledgerDrivePath, "desktop.ini"), """
    [.ShellClassInfo]
    IconResource=Folder.ico,0
    InfoTip=Your LedgerDrive — drop financial documents here
    [ViewState]
    Mode=
    Vid=
    FolderType=Documents
    """);

// desktop.ini must be hidden+system for Windows to read it
var ini = new FileInfo(Path.Combine(ledgerDrivePath, "desktop.ini"));
ini.Attributes |= FileAttributes.Hidden | FileAttributes.System;

// Folder itself must have ReadOnly attribute for desktop.ini to take effect
var folder = new DirectoryInfo(ledgerDrivePath);
folder.Attributes |= FileAttributes.ReadOnly;

// Notify Shell of attribute change
SHChangeNotify(SHCNE_UPDATEDIR, SHCNF_PATH, ledgerDrivePath, null);
```

---

## 6. Windows Search Integration

### 6.1 Register LedgerDrive as Crawl Scope

```csharp
// SearchIndexService.cs — called once at setup completion
[ComImport, Guid("AB310581-AC80-11D1-8DF3-00C04FB6EF69")]
interface ISearchManager { ... }

var searchManager = (ISearchManager)new CSearchManager();
var catalog = searchManager.GetCatalog("SystemIndex");
var crawlScope = catalog.GetCrawlScopeManager();
crawlScope.AddUserScopeRule(ledgerDrivePath, include: true, followFlags: true, depth: 0);
crawlScope.SaveAll();
```

This tells Windows Search to index all files under LedgerDrive, making them searchable via Start menu and Explorer search.

### 6.2 Write Custom Property Metadata

After a file is organized, write custom metadata to its property store. This enables rich searches like "HDFC 2025" or "ICICI January":

```csharp
// SearchPropertyWriter.cs
var props = new Dictionary<PROPERTYKEY, object>
{
    [PKEY_BankName]         = reg.DetectedBank,                // "HDFC"
    [PKEY_AccountType]      = reg.DetectedSourceType,          // "HDFC_PDF"
    [PKEY_StatementYear]    = year.ToString(),                 // "2025"
    [PKEY_StatementMonth]   = monthName,                       // "January"
    [PKEY_TransactionCount] = proposalCount.ToString(),        // "117"
    [PKEY_FamilyMember]     = memberDisplayName                // v2: "Priya"
};

var store = SHGetPropertyStoreFromParsingName(
    organizedPath,
    IntPtr.Zero,
    GETPROPERTYSTOREFLAGS.GPS_READWRITE,
    typeof(IPropertyStore).GUID);

foreach (var (key, value) in props)
{
    var pv = new PROPVARIANT(value);
    store.SetValue(key, pv);
}
store.Commit();

// Force Windows Search to re-index this file immediately
SHChangeNotify(SHCNE_UPDATEITEM, SHCNF_PATH | SHCNF_FLUSH, organizedPath, null);
```

**Custom Property Keys** — registered via `propdesc` XML in MSIX manifest:
```xml
<propertyDescription name="Ledger.BankName" formatID="{...}" propID="100">
  <typeInfo type="String" multipleValues="false" isSearchable="true" />
</propertyDescription>
```

### 6.3 Search Examples (via Windows Search)

After integration, user can find files via Start menu or Explorer search bar:
- `HDFC 2025` → all HDFC statements from 2025
- `type:pdf kind:document statement January` → all January statements
- `LedgerBankName:ICICI` → all ICICI files (using custom property)

---

## 7. System Tray

```csharp
// TrayIcon.cs
_notifyIcon = new System.Windows.Forms.NotifyIcon {
    Icon = new Icon(ResourceHelper.GetStream("tray.ico")),
    Text = "Ledger",
    Visible = true,
    ContextMenuStrip = BuildTrayMenu()
};
_notifyIcon.DoubleClick += (_, _) => ShowMainWindow();

ContextMenuStrip BuildTrayMenu() => new() {
    Items = {
        new ToolStripMenuItem("Open Ledger",   null, (_, _) => ShowMainWindow()),
        new ToolStripMenuItem("Scan Now",      null, (_, _) => TriggerManualScan()),
        new ToolStripSeparator(),
        new ToolStripMenuItem("Open LedgerDrive Folder", null, (_, _) => OpenLedgerDrive()),
        new ToolStripSeparator(),
        new ToolStripMenuItem("Exit",          null, (_, _) => Application.Current.Shutdown())
    }
};
```

---

## 8. Toast Notifications

### 8.1 Notification Types

| Event | Title | Body | Action |
|---|---|---|---|
| File processed | "HDFC Jan 2025 processed" | "117 transactions pending review" | "Review Now" → opens /proposals |
| File needs password | "Password Required" | "Could not unlock [filename]" | "Enter Password" → opens /files?fileId=... |
| File failed | "Processing Failed" | "[filename] could not be parsed after 3 attempts" | "View Details" |
| Family file pw needed | "Password Required" | "Could not unlock [filename] (Priya's file)" | "Enter Password" |
| Low disk in .vault | "LedgerDrive Space Warning" | ".vault folder is using 4.7 GB" | "Manage Vault" → opens Settings |
| Update available | "Ledger Update Available" | "Version 1.2 is ready to install" | "Install Now" |

### 8.2 Implementation

```csharp
// ToastService.cs
AppNotificationManager.Default.NotificationInvoked += OnToastActivated;
AppNotificationManager.Default.Register();

public void Notify(ToastDefinition def)
{
    var builder = new AppNotificationBuilder()
        .AddText(def.Title)
        .AddText(def.Body);

    if (def.ActionLabel != null)
        builder.AddButton(new AppNotificationButton(def.ActionLabel)
            .AddArgument("action", def.ActionId)
            .AddArgument("param", def.ActionParam));

    AppNotificationManager.Default.Show(builder.BuildNotification());
}

private void OnToastActivated(AppNotificationManager sender, AppNotificationActivatedEventArgs args)
{
    var action = args.Arguments["action"];
    var param  = args.Arguments.GetValueOrDefault("param");

    // Route to WebView2 via postMessage
    _bridge.NavigateTo(action, param);   // e.g., navigateTo("/files", fileId)
}
```
