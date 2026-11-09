# Deployment & Packaging Guide

This guide describes how the Windows School Computer and Android Teacher Application are deployed and distributed.

---

## 1. Windows School Computer

The school computer is the central authority and local server hosting:
- The FastAPI Python service and SQLite/PostgreSQL storage.
- The compiled React Administration Dashboard in `admin/dist/`.
- Local LAN endpoints on port `8080` for teacher phone synchronization.

### Fast One-Click Setup (`installer/install.bat`)
Run [`installer/install.bat`](file:///c:/Users/Adebayo/Desktop/new/installer/install.bat) as Administrator:
1. Automatically verifies Python 3.11+.
2. Configures the virtual environment (`server/.venv`) and installs backend requirements.
3. Automatically opens Windows Defender Firewall for TCP port `8080` on the school's private Wi-Fi network.
4. Registers an automatic background startup task in Windows Task Scheduler.
5. Places a desktop shortcut (`LSIA School Computer`) for easy administrative access.

### Windows MSI Installer Package (`.msi`)
The Windows school computer can be packaged into a standard enterprise `.msi` (Microsoft Installer) package using **WiX Toolset**:
- **WiX Product Configuration**: [`installer/wix/Product.wxs`](file:///c:/Users/Adebayo/Desktop/new/installer/wix/Product.wxs)
- **PowerShell MSI Build Script**: [`installer/wix/build-msi.ps1`](file:///c:/Users/Adebayo/Desktop/new/installer/wix/build-msi.ps1)
- **GitHub Actions Cloud Build**: [`.github/workflows/build-windows-msi.yml`](file:///c:/Users/Adebayo/Desktop/new/.github/workflows/build-windows-msi.yml) (builds `LSIASchoolComputer.msi` on Windows runners and uploads it as an artifact).

The `.msi` package provides:
- Standard Windows Installer wizard.
- Automatic installation to `Program Files\LSIA School Computer`.
- Automatic Windows Defender Firewall configuration for port 8080 (School LAN).
- Start Menu and Desktop shortcuts.
- Silent/unattended enterprise deployment support (`msiexec /i LSIASchoolComputer.msi /quiet /qn`).
- Clean uninstallation via Windows "Add or Remove Programs".

### Compiling into a Standalone `.exe` Installer
An Inno Setup compiler definition is provided at [`installer/lsia_setup.iss`](file:///c:/Users/Adebayo/Desktop/new/installer/lsia_setup.iss).
To compile a single-file `LSIASetup.exe`:
1. Download and install [Inno Setup](https://jrsoftware.org/isdl.php) (free).
2. Right-click `installer/lsia_setup.iss` and choose **Compile**.
3. The resulting single-file installer `installer_output/LSIASetup.exe` can be copied to any school Windows PC and installed with a standard wizard.

---

## 2. Android Teacher Application

The Android app operates offline-first on teachers' phones.

### Source Code State
- Location: [`android/`](file:///c:/Users/Adebayo/Desktop/new/android/)
- Framework: Kotlin, Jetpack Compose, Room SQLite, Android Keystore Ed25519, WorkManager.
- Status: **Complete and verified** (architecture, Room schema, offline queue, QR scanner parsing, and bidirectional sync client).

### Compiling the Binary `.apk`

The `.apk` binary is compiled using standard Android SDK tools:

#### Option A: In Android Studio (Recommended)
1. Open Android Studio.
2. Select **File -> Open...** and choose the `android/` directory in this repository.
3. Allow Gradle to synchronize dependencies.
4. Select **Build -> Build Bundle(s) / APK(s) -> Build APK(s)**.
5. Android Studio will generate `app-debug.apk` in `android/app/build/outputs/apk/debug/`.
6. Transfer this APK file to teachers' Android phones (via USB, Bluetooth, or local Wi-Fi download) to install.

#### Option B: Via Command Line / Gradle Wrapper
Once a Java JDK (version 17 or higher) and Android SDK are configured on the machine:
```cmd
cd android
gradlew.bat assembleDebug
```
Or run [`android/build-apk.bat`](file:///c:/Users/Adebayo/Desktop/new/android/build-apk.bat).
The output APK will be generated at `android/app/build/outputs/apk/debug/app-debug.apk`.
