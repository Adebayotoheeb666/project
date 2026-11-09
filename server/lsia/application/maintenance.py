from __future__ import annotations

import os
import shutil
import tarfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from lsia.application.errors import BusinessRule, NotFound, PermissionDenied
from lsia.application.events import append_event
from lsia.config import settings
from lsia.domain.permissions import parse_role
from lsia.infrastructure.crypto import SchoolIdentity
from lsia.infrastructure.models import Teacher


def get_backup_dir() -> Path:
    backup_dir = settings.data_dir / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def create_backup(
    session: Session,
    identity: SchoolIdentity,
    actor: Teacher,
) -> dict[str, Any]:
    role = parse_role(actor.role_json)
    if role.kind != "administrator":
        raise PermissionDenied("Only administrators can create system backups.")

    backup_dir = get_backup_dir()
    timestamp_str = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    backup_filename = f"lsia_backup_{identity.school_id}_{timestamp_str}.tar.gz"
    backup_path = backup_dir / backup_filename

    # Gather database and keys
    db_file = None
    if settings.database_url.startswith("sqlite:///"):
        raw_path = settings.database_url.replace("sqlite:///", "")
        db_path = Path(raw_path)
        if db_path.exists():
            db_file = db_path

    with tarfile.open(backup_path, "w:gz") as tar:
        if db_file and db_file.exists():
            tar.add(db_file, arcname="lsia.db")
        if settings.keys_dir.exists():
            tar.add(settings.keys_dir, arcname="keys")

    stat = backup_path.stat()
    backup_signature = identity.sign(f"BACKUP:{backup_filename}:{stat.st_size}".encode("utf-8"))

    append_event(
        session,
        identity,
        operation="SYSTEM_BACKUP",
        actor=actor,
        payload={
            "filename": backup_filename,
            "size_bytes": stat.st_size,
            "signature": backup_signature,
        },
        entity_type="backup",
        entity_id=backup_filename,
    )

    return {
        "filename": backup_filename,
        "size_bytes": stat.st_size,
        "created_at": datetime.now(UTC).isoformat(),
        "signature": backup_signature,
    }


def list_backups(actor: Teacher) -> list[dict[str, Any]]:
    role = parse_role(actor.role_json)
    if role.kind != "administrator":
        raise PermissionDenied("Only administrators can view system backups.")

    backup_dir = get_backup_dir()
    results = []
    for file_path in sorted(backup_dir.glob("lsia_backup_*.tar.gz"), reverse=True):
        stat = file_path.stat()
        results.append(
            {
                "filename": file_path.name,
                "size_bytes": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
            }
        )
    return results


def restore_backup(
    session: Session,
    identity: SchoolIdentity,
    actor: Teacher,
    filename: str,
) -> dict[str, Any]:
    role = parse_role(actor.role_json)
    if role.kind != "administrator":
        raise PermissionDenied("Only administrators can restore system backups.")

    backup_dir = get_backup_dir()
    backup_path = backup_dir / filename
    if not backup_path.exists():
        raise NotFound("Backup file not found.")

    # Extract to temporary directory to verify integrity
    temp_extract = settings.data_dir / f"restore_temp_{int(time.time())}"
    temp_extract.mkdir(parents=True, exist_ok=True)

    try:
        with tarfile.open(backup_path, "r:gz") as tar:
            try:
                tar.extractall(temp_extract, filter="data")
            except TypeError:
                tar.extractall(temp_extract)

        restored_db = temp_extract / "lsia.db"
        if restored_db.exists() and settings.database_url.startswith("sqlite:///"):
            target_db = Path(settings.database_url.replace("sqlite:///", ""))
            shutil.copy2(restored_db, target_db)

        restored_keys = temp_extract / "keys"
        if restored_keys.exists():
            shutil.copytree(restored_keys, settings.keys_dir, dirs_exist_ok=True)

    finally:
        if temp_extract.exists():
            shutil.rmtree(temp_extract, ignore_errors=True)

    append_event(
        session,
        identity,
        operation="SYSTEM_RESTORE",
        actor=actor,
        payload={"filename": filename},
        entity_type="backup",
        entity_id=filename,
    )

    return {"status": "ok", "message": f"Successfully restored from {filename}"}
