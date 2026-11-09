# Local-First School Intelligence System (LSIA)

Privacy-focused, offline-first school management system. The school computer is the central authority and permanent source of truth. Teachers use Android phones to perform their activities offline and synchronize directly over the school local network (LAN) without requiring internet access.

## Implemented Phases

- **Phase 1: Core Foundation**
  - Project architecture, SQLite/PostgreSQL support, JWT session management, school Ed25519 identity, teachers, classes, subjects, students directory, and append-only cryptographic event logs.
- **Phase 2: Teacher Android Application**
  - Offline-first Kotlin & Jetpack Compose app, Room database, Android Keystore Ed25519 key management, device enrollment via QR codes, offline operation queue, and local student management.
- **Phase 3: Local-Network Synchronization**
  - Handshake with cryptographic signature challenge (`/sync/handshake`).
  - Batch operation push with replay protection, device signature validation, Lamport clock monotonicity, and conflict detection (`/sync/push`).
  - Watermark pull endpoint for device updates (`/sync/pull`).
- **Phase 4: Academic Management**
  - Daily attendance tracking (`present`, `absent`, `late`, `excused`) and percentage calculations.
  - Continuous Assessment (CA max 40) and Examination (max 60) score entry with automated total and grade assignments (A1 to F9).
- **Phase 5: Reporting, Approvals & Administration**
  - Broadsheet master matrix calculation (class averages, highest/lowest, subject rankings, deterministic student positions).
  - Termly Student Progress Report Cards with subject breakdown, attendance rate, performance-based teacher & principal remarks, and printable PDF view.
  - Administrative approval workflow for sensitive operations (`PENDING_APPROVAL` → `APPROVED` / `REJECTED`).
  - Concurrent edit conflict resolution desk (`keep_current`, `use_incoming`, or `custom`).
  - Permanent audit desk inspecting cryptographic signatures, Lamport timestamps, and user actions.

## Run Locally

SQLite is the default storage engine so the school computer can start immediately without extra setup.

```powershell
cd server
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn lsia.main:create_app --factory --host 0.0.0.0 --port 8080 --reload
```

In another terminal, start the administration desk:

```powershell
cd admin
npm install
npm run dev
```

Open `http://127.0.0.1:5173` (or `http://127.0.0.1:8080` when built) to bootstrap the first administrator.

To use PostgreSQL instead:

```powershell
docker compose up -d
$env:DATABASE_URL = "postgresql+psycopg://lsia:lsia@127.0.0.1:5432/lsia"
```

## Teacher Android App

Open the `android/` directory in Android Studio. From the school admin desk, visit **Phones** to generate an enrollment QR code pointing at the school computer on the local Wi-Fi (`http://<lan-ip>:8080`).

## Automated Tests

Run the full backend test suite:

```powershell
cd server
pytest
```

## Windows Installer (.msi & .exe)

- **Enterprise Windows Installer (`.msi`)**: Built using WiX Toolset. Includes automatic Windows Defender Firewall rule for port 8080 (School LAN), Start Menu & Desktop shortcuts, and silent installation support (`msiexec /i LSIASchoolComputer.msi /quiet`).
  - Configuration: `installer/wix/Product.wxs`
  - Local Build: `powershell -File installer/wix/build-msi.ps1`
  - GitHub Actions: `.github/workflows/build-windows-msi.yml`
- **One-Click Windows Setup**: `installer/install.bat` (automated installation and startup task configuration).
- **Inno Setup Script (`.exe`)**: `installer/lsia_setup.iss`.

