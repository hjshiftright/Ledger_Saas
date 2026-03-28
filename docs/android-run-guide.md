# Ledger Android App — How to Run

## Overview

The Ledger Android app connects to the existing FastAPI backend running on your laptop.
The emulator maps `10.0.2.2` → `127.0.0.1` on the host, so the backend and emulator
run on the same machine with no extra networking required.

---

## Prerequisites

Install the following before starting:

| Tool | Version | Download |
|------|---------|----------|
| Android Studio | Latest stable (Hedgehog 2023.1+) | developer.android.com/studio |
| JDK | 17 | Bundled with Android Studio |
| Android SDK | API 37 (Android 16) | Via Android Studio SDK Manager |
| Android Emulator | Pixel 6 / API 37 image | Via Android Studio AVD Manager |
| Python | 3.10+ | Already installed (backend) |

> Android Studio bundles its own JDK 17. You do not need to install Java separately.

---

## Part 1 — One-Time Setup

### Step 1: Download the Gradle Wrapper Binary

The `gradle-wrapper.jar` binary file is not stored in git (it is a binary blob).
You must generate it once using Android Studio.

1. Open **Android Studio**
2. Go to **File → Open**
3. Select the `android/` folder:
   ```
   /home/testdevice/myledger/Ledger_Saas/android/
   ```
4. Android Studio will detect the missing wrapper and offer to generate it.
   Click **OK / Generate**.

   Alternatively, open the terminal inside Android Studio and run:
   ```bash
   cd /home/testdevice/myledger/Ledger_Saas/android
   gradle wrapper --gradle-version 8.4
   ```

   This creates `android/gradle/wrapper/gradle-wrapper.jar`.

---

### Step 2: Install the Android SDK (API 34)

1. In Android Studio, go to **Tools → SDK Manager**
2. Under **SDK Platforms** tab, check:
   - **Android 16.0 (API 37)**
3. Under **SDK Tools** tab, check:
   - **Android SDK Build-Tools 37**
   - **Android Emulator**
   - **Android SDK Platform-Tools**
4. Click **Apply** and wait for download to finish.

---

### Step 3: Create a Virtual Device (Emulator)

1. Go to **Tools → Device Manager**
2. Click **Create Device**
3. Select: **Phone → Pixel 6**
4. Click **Next**
5. Select system image: **API 37 (Android 16)** — download it if not present
6. Click **Next → Finish**
7. The new device appears in the Device Manager list.

---

### Step 4: Sync the Gradle Project

1. With the `android/` folder open in Android Studio, wait for the
   "Gradle sync" notification at the top.
2. Click **Sync Now** if it does not start automatically.
3. Wait for sync to complete (first sync downloads ~500 MB of dependencies).

You should see **"BUILD SUCCESSFUL"** or no errors in the **Build** panel.

---

## Part 2 — Starting the Backend

The app calls the FastAPI backend. It must be running before you launch the app.

### Step 5: Start the FastAPI Backend

Open a terminal in the project root:

```bash
cd /home/testdevice/myledger/Ledger_Saas/backend

# Activate your virtual environment (if applicable)
source .venv/bin/activate    # Linux/Mac
# or: .venv\Scripts\activate  # Windows

# Start the server — must bind to 0.0.0.0 so the emulator can reach it
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

Verify it is running by opening in your browser:
```
http://127.0.0.1:8000/health
```

Expected response:
```json
{"status": "ok", "version": "3.0", "env": "development"}
```

> **Why `0.0.0.0`?** The Android Emulator reaches your laptop via `10.0.2.2`.
> Binding to `0.0.0.0` makes the server reachable on all interfaces including
> the one the emulator uses.

---

## Part 3 — Running the App

### Step 6: Start the Emulator

1. In Android Studio, click the **Device Manager** icon (right toolbar)
2. Click the **Play ▶** button next to your Pixel 6 / API 34 device
3. Wait for the emulator to boot fully (home screen visible — takes 1–2 min first time)

---

### Step 7: Run the App

**Option A — From Android Studio:**

1. In the toolbar, select your emulator from the device dropdown
2. Click the **Run ▶** button (Shift+F10)
3. Android Studio will build and install the app on the emulator

**Option B — From the terminal:**

```bash
cd /home/testdevice/myledger/Ledger_Saas/android

# Make gradlew executable (first time only)
chmod +x gradlew

# Build and install debug APK
./gradlew installDebug

# Then launch the app on the running emulator
adb shell am start -n com.ledger.app/.ui.auth.LoginActivity
```

---

### Step 8: Use the App

Once the app launches on the emulator:

1. **Login Screen** appears
2. Enter your credentials (email + password registered in the backend)
3. If no account exists yet — tap **Create Account** to sign up
4. After login, if you have multiple tenants, select one from the list
5. The **Dashboard** loads with your financial data

---

## Part 4 — Running the Tests

### Step 9: Run Unit Tests (No Emulator Needed)

These tests run on the JVM — fast, no emulator required.

```bash
cd /home/testdevice/myledger/Ledger_Saas/android

# Run all unit tests
./gradlew test

# Run a specific test class
./gradlew test --tests "com.ledger.app.util.CurrencyFormatterTest"

# Run with detailed output
./gradlew test --info
```

Results are in:
```
android/app/build/reports/tests/testDebugUnitTest/index.html
```

---

### Step 10: Run Instrumented Tests (Emulator Required)

These tests run on the emulator. Make sure:
- The emulator is **booted and unlocked**
- The **backend is running** (`./gradlew` needs the API for integration tests)

```bash
cd /home/testdevice/myledger/Ledger_Saas/android

# Run all instrumented tests
./gradlew connectedAndroidTest

# Run a specific instrumented test class
./gradlew connectedAndroidTest \
  -Pandroid.testInstrumentationRunnerArguments.class=com.ledger.app.ui.auth.LoginActivityTest
```

Results are in:
```
android/app/build/reports/androidTests/connected/index.html
```

---

### Step 11: Run All Tests (Full Suite)

```bash
cd /home/testdevice/myledger/Ledger_Saas/android

# Full TDD gate: all phases must pass
./gradlew test && ./gradlew connectedAndroidTest
```

Expected: **~95 tests, 0 failures**

---

## Part 5 — Changing the Backend URL

The app is pre-configured for the Android Emulator (`10.0.2.2:8000`).

### To connect to a different server:

**Option A — In the app (at runtime):**
1. Open the app → tap **More** tab → **Settings**
2. Edit the **API Base URL** field
3. Tap **Test Connection** to verify
4. The app uses the new URL immediately

**Option B — Change the default (at build time):**

Edit [android/app/src/main/java/com/ledger/app/config/AppConfig.kt](../android/app/src/main/java/com/ledger/app/config/AppConfig.kt):
```kotlin
object AppConfig {
    var BASE_URL: String = "https://api.your-server.com"  // change this
}
```

Then rebuild: `./gradlew installDebug`

---

## Part 6 — Building a Release APK

```bash
cd /home/testdevice/myledger/Ledger_Saas/android

# Build release APK (unsigned)
./gradlew assembleRelease
```

Output APK location:
```
android/app/build/outputs/apk/release/app-release-unsigned.apk
```

To install on a physical device via USB:
```bash
adb install app/build/outputs/apk/debug/app-debug.apk
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| **Gradle sync fails** | File → Invalidate Caches → Restart. Then sync again. |
| **`gradle-wrapper.jar` missing** | Run `gradle wrapper --gradle-version 8.4` in the `android/` folder |
| **App can't connect to backend** | Confirm backend is running with `--host 0.0.0.0`. Check `http://10.0.2.2:8000/api/v1/health` inside the emulator browser |
| **"Cleartext traffic not permitted"** | `network_security_config.xml` allows `10.0.2.2` — verify `AndroidManifest.xml` references it |
| **Emulator too slow** | Enable **Hardware Acceleration** (HAXM on Intel / WHPX on AMD) in AVD settings |
| **`adb: command not found`** | Add Android SDK `platform-tools` to PATH: `export PATH=$PATH:~/Android/Sdk/platform-tools` |
| **Build fails: kapt error** | Clean and rebuild: `./gradlew clean assembleDebug` |
| **Tests timeout** | Increase emulator RAM to 4 GB in AVD settings |

---

## Quick Reference

```bash
# Terminal 1 — backend
cd /home/testdevice/myledger/Ledger_Saas/backend
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000

# Terminal 2 — Android
cd /home/testdevice/myledger/Ledger_Saas/android
./gradlew installDebug                 # build + install
./gradlew test                         # unit tests (fast)
./gradlew connectedAndroidTest         # UI tests (emulator)
```
