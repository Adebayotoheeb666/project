# Backup and Disaster Recovery

LSIA ensures institutional control and data resilience through self-contained, signed backup archives.

## Backup Contents

Each backup archive (`lsia_backup_<school_id>_<timestamp>.tar.gz`) contains:
- `lsia.db`: Complete SQLite database containing all students, classes, scores, attendance records, and cryptographic audit logs.
- `keys/`: School Ed25519 cryptographic private and public keys.

## Integrity and Verification

- The school computer signs each backup package upon creation using its Ed25519 private key:
  `signature = Sign("BACKUP:<filename>:<size_bytes>")`
- System backups can be downloaded directly from the administration desk or restored in-place.
- Restoration verifies tar integrity before overwriting database records.
