# Teacher Android application (Phase 2)

The phone is an offline register. The school computer remains the source of truth.

## First launch

1. Administrator opens **Phones** and issues a QR enrollment code (LAN address of the school computer).
2. Teacher scans the code (or pastes the JSON) and signs in with their staff password.
3. The phone generates an Ed25519 key, stores the private seed in EncryptedSharedPreferences, and registers the public key.
4. Assigned classes, subjects, and students are copied into Room.
5. The teacher sets a device PIN.

## Offline work

Student create/update is written to SQLite immediately and appended to `pending_operations` with a Lamport clock and signature. The queue stays on the device until Phase 3 LAN sync.

Status labels: Offline, Connected, Pending N.

## Build

Open `android/` in Android Studio, set the SDK, and run the `app` configuration. Minimum SDK 26.
