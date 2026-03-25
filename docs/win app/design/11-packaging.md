# Ledger Desktop — Packaging & Distribution

**Version:** 1.0  
**Status:** Design Review

---

## 1. Package Format: MSIX

MSIX is the modern Windows application packaging format. It provides:
- Clean install and uninstall (no registry pollution)
- Delta update support via AppInstaller
- Code integrity via mandatory code signing
- Virtualized file system and registry for the app
- Native Start menu entry, taskbar pinning, and uninstall via Settings

---

## 2. Solution Structure — Packaging Project

```
Ledger.Installer/               ← Windows Application Packaging Project (.wapproj)
├── Package.appxmanifest        ← MSIX manifest
├── Assets/
│   ├── LedgerIcon.png          ← 150x150, 44x44, 71x71
│   ├── SplashScreen.png        ← 620x300
│   └── BadgeLogo.png           ← 24x24
├── CustomActions/
│   └── ShellExtensionAction.cs ← COM registration for SharpShell
└── Ledger.AppInstaller         ← AppInstaller XML for delta updates
```

---

## 3. Package.appxmanifest

```xml
<?xml version="1.0" encoding="utf-8"?>
<Package
  xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10"
  xmlns:uap="http://schemas.microsoft.com/appx/manifest/uap/windows10"
  xmlns:com="http://schemas.microsoft.com/appx/manifest/com/windows10"
  xmlns:desktop="http://schemas.microsoft.com/appx/manifest/desktop/windows10"
  xmlns:rescap="http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities">

  <Identity
    Name="com.ledger.desktop"
    Publisher="CN=Ledger Inc, O=Ledger Inc, C=IN"
    Version="1.0.0.0"
    ProcessorArchitecture="x64" />

  <Properties>
    <DisplayName>Ledger</DisplayName>
    <PublisherDisplayName>Ledger Inc</PublisherDisplayName>
    <Logo>Assets\StoreLogo.png</Logo>
  </Properties>

  <Dependencies>
    <TargetDeviceFamily Name="Windows.Desktop" MinVersion="10.0.19041.0" MaxVersionTested="10.0.26100.0" />
  </Dependencies>

  <Resources>
    <Resource Language="en-IN" />
    <Resource Language="en-US" />
  </Resources>

  <Capabilities>
    <rescap:Capability Name="runFullTrust" />        <!-- Required for WPF + COM -->
    <Capability Name="privateNetworkClientServer" />  <!-- Local Kestrel -->
  </Capabilities>

  <Applications>
    <Application Id="LedgerDesktop"
      Executable="Ledger.Desktop.exe"
      EntryPoint="Windows.FullTrustApplication">

      <uap:VisualElements
        DisplayName="Ledger"
        Description="Your personal financial ledger"
        BackgroundColor="transparent"
        Square150x150Logo="Assets\LedgerIcon.png"
        Square44x44Logo="Assets\LedgerIcon44.png">
        <uap:SplashScreen Image="Assets\SplashScreen.png" BackgroundColor="#1a1a2e" />
        <uap:InitialRotationPreference>
          <uap:Rotation Preference="landscape" />
        </uap:InitialRotationPreference>
      </uap:VisualElements>

      <Extensions>
        <!-- COM Server registration for SharpShell overlay handler -->
        <com:Extension Category="windows.comServer">
          <com:ComServer>
            <com:ExeServer Executable="Ledger.Desktop.exe" DisplayName="Ledger Shell Host">
              <com:Class Id="{OVERLAY-SYNCING-CLSID}" DisplayName="LedgerOverlaySyncing" />
              <com:Class Id="{OVERLAY-DONE-CLSID}"    DisplayName="LedgerOverlayDone" />
              <com:Class Id="{OVERLAY-ERROR-CLSID}"   DisplayName="LedgerOverlayError" />
              <com:Class Id="{OVERLAY-MISSING-CLSID}" DisplayName="LedgerOverlayMissing" />
              <com:Class Id="{CONTEXT-MENU-CLSID}"    DisplayName="LedgerContextMenu" />
            </com:ExeServer>
          </com:ComServer>
        </com:Extension>

        <!-- Shell namespace / context menu handler -->
        <desktop:Extension Category="windows.fileTypeAssociation" Executable="Ledger.Desktop.exe"
          EntryPoint="Windows.FullTrustApplication">
          <desktop:FileTypeAssociation Name="ledger-file">
            <desktop:SupportedFileTypes>
              <desktop:FileType>.pdf</desktop:FileType>
              <desktop:FileType>.xlsx</desktop:FileType>
              <desktop:FileType>.csv</desktop:FileType>
            </desktop:SupportedFileTypes>
          </desktop:FileTypeAssociation>
        </desktop:Extension>

        <!-- Toast notification activation -->
        <desktop:Extension Category="windows.toastNotificationActivation">
          <desktop:ToastNotificationActivation ToastActivatorCLSID="{TOAST-CLSID}" />
        </desktop:Extension>

        <!-- Startup task (optional — user controls in Task Manager) -->
        <desktop:Extension Category="windows.startupTask" Executable="Ledger.Desktop.exe"
          EntryPoint="Windows.FullTrustApplication">
          <desktop:StartupTask TaskId="LedgerDriveWatcher" Enabled="false"
            DisplayName="Ledger File Watcher" />
        </desktop:Extension>
      </Extensions>
    </Application>
  </Applications>
</Package>
```

---

## 4. Bundling Third-Party Dependencies

### 4.1 Tesseract 5 OCR Data

Tesseract's `tessdata/` is bundled as content files:
```xml
<!-- Ledger.Desktop.csproj -->
<ItemGroup>
  <Content Include="tessdata\eng.traineddata" CopyToOutputDirectory="PreserveNewest" />
  <Content Include="tessdata\hin.traineddata" CopyToOutputDirectory="PreserveNewest" />
</ItemGroup>
```
At runtime, Tesseract is initialized with `dataPath = AppContext.BaseDirectory + "tessdata"`.

**Download script (CI):**
```powershell
# Runs in build pipeline before dotnet publish
$version = "4.1.1"
Invoke-WebRequest "https://github.com/tesseract-ocr/tessdata_best/raw/main/eng.traineddata" `
    -OutFile "src/Ledger.Desktop/tessdata/eng.traineddata"
```

### 4.2 ML.NET Model

The pre-trained category classification model is bundled the same way:
```xml
<Content Include="models\category_classifier.zip" CopyToOutputDirectory="PreserveNewest" />
```

### 4.3 React / Frontend

```
# Build pipeline step before dotnet publish:
cd frontend
npm ci
npm run build           → dist/ folder

# dotnet publish then copies dist/ contents into:
Ledger.Desktop/wwwroot/
```

In `Ledger.Desktop.csproj`:
```xml
<Target Name="BuildFrontend" BeforeTargets="BeforeBuild">
  <Exec Command="npm ci &amp;&amp; npm run build" WorkingDirectory="../../frontend" />
  <ItemGroup>
    <Content Include="../../frontend/dist/**" LinkBase="wwwroot\" CopyToOutputDirectory="PreserveNewest" />
  </ItemGroup>
</Target>
```

---

## 5. SharpShell COM Registration Custom Action

Because MSIX packages run in a virtualized environment, SharpShell's `serverregister` bootstrap runs as a **trusted installer custom action** that writes to real HKLM:

```csharp
// CustomActions/ShellExtensionAction.cs
[CustomAction]
public static ActionResult RegisterShellExtension(Session session)
{
    var dllPath = Path.Combine(session["INSTALLFOLDER"], "Ledger.ShellExtension.dll");
    var result = Process.Start(new ProcessStartInfo {
        FileName = "regsvr32.exe",
        Arguments = $"/s \"{dllPath}\"",
        UseShellExecute = false,
        Verb = "runas"
    }).WaitForExit(30_000);
    return result ? ActionResult.Success : ActionResult.Failure;
}
```

> **Note:** SharpShell overlays require `HKLM` write access. On first install, UAC elevation prompt is shown. After registration, the overlay DLL works without elevation.

---

## 6. Code Signing

### 6.1 Requirements

| Component | Signing Requirement |
|---|---|
| `Ledger.Desktop.exe` | Standard Authenticode (OV cert acceptable) |
| `Ledger.ShellExtension.dll` | **EV (Extended Validation)** code signing cert — required for shell overlay registration without SmartScreen warnings |
| MSIX Package | Same EV cert used for package signing |

### 6.2 CI Signing (Azure Trusted Signing)

```yaml
# .github/workflows/release.yml
- name: Sign MSIX
  uses: azure/trusted-signing-action@v0.4
  with:
    azure-tenant-id: ${{ secrets.AZURE_TENANT_ID }}
    azure-client-id: ${{ secrets.AZURE_CLIENT_ID }}
    azure-client-secret: ${{ secrets.AZURE_CLIENT_SECRET }}
    endpoint: https://eus.codesigning.azure.net/
    trusted-signing-account-name: ledger-signing
    certificate-profile-name: LedgerDesktop
    files-folder: ${{ github.workspace }}/output
    files-folder-filter: msix
    file-digest: SHA256
    timestamp-rfc3161: http://timestamp.acs.microsoft.com
    timestamp-digest: SHA256
```

---

## 7. AppInstaller for Delta Updates

`Ledger.AppInstaller` file published to a secure HTTPS server (GitHub Releases or CDN):

```xml
<?xml version="1.0" encoding="utf-8"?>
<AppInstaller Uri="https://releases.ledger.app/Ledger.appinstaller"
    Version="1.0.0.0"
    xmlns="http://schemas.microsoft.com/appx/appinstaller/2018">
  <MainPackage
    Name="com.ledger.desktop"
    Publisher="CN=Ledger Inc, O=Ledger Inc, C=IN"
    Version="1.0.0.0"
    Uri="https://releases.ledger.app/Ledger_1.0.0.0_x64.msix"
    ProcessorArchitecture="x64" />
  <UpdateSettings>
    <OnLaunch HoursBetweenUpdateChecks="24" />
    <AutomaticBackgroundTask />
    <ForceUpdateFromAnyVersion>true</ForceUpdateFromAnyVersion>
  </UpdateSettings>
</AppInstaller>
```

**In-app update notification:**
The `UpdateService` checks `PackageManager.GetUpdatesAsync()` at startup and once every 24 hours. If an update is available, a toast is shown:
```
Ledger 1.2 is available — New: Family Mode, SBI parser improvements
[Install Now]  [Remind Me Later]
```

---

## 8. Build Pipeline

```
CI Trigger: Push to main or version tag

Steps:
1. Restore NuGet packages
2. Build Frontend (npm ci && npm run build)
3. Download Tesseract tessdata (if not cached)
4. dotnet publish -c Release -r win-x64 --self-contained true
5. Run unit + integration tests
6. Run SharpShell COM registration validation
7. Package MSIX (msbuild Ledger.Installer.wapproj)
8. Sign with Azure Trusted Signing (EV cert)
9. Upload to GitHub Releases
10. Update AppInstaller file on CDN
11. Notify team via webhook

Artifacts:
- Ledger_{version}_x64.msix         ← Distributable installer
- Ledger_{version}_x64.msix.sig     ← Detached signature
- Ledger.appinstaller                ← AppInstaller manifest
```

---

## 9. System Requirements

| Requirement | Minimum | Recommended |
|---|---|---|
| OS | Windows 10 21H2 (10.0.19041) | Windows 11 23H2+ |
| RAM | 4 GB | 8 GB |
| Disk | 500 MB (app) + LedgerDrive | 2 GB+ |
| .NET | Bundled (self-contained) | — |
| WebView2 | Auto-installed by MSIX | — |
| Internet | Not required | Optional (LLM, updates) |
| Processor | x64 (Intel/AMD/ARM64 via x64 emulation) | x64 Intel Core i5+ |

---

## 10. Uninstall

MSIX uninstall is clean by default. The installer package itself is removed with no leftover files. However, **user data is intentionally preserved** on uninstall:

- `LedgerDrive\` folder — unchanged (user's files)
- `%AppData%\Ledger\` — SQLCipher database — preserved
- `%AppData%\Ledger\logs\` — preserved
- Windows Credential Store entry for PIN → cleared on uninstall via custom action

First-run after reinstall: app detects existing DB at `%AppData%\Ledger\ledger.db`, opens it using the machine-derived SQLCipher key (DPAPI + MachineGuid), and continues from last state. No data loss.
