from __future__ import annotations

import base64
import json
import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from lsia.application.auth import login, school_name
from lsia.application.directory import assigned_class_ids, list_classes, list_students, list_subjects
from lsia.application.errors import BusinessRule, Conflict, NotFound
from lsia.application.events import append_event
from lsia.config import settings
from lsia.infrastructure.crypto import SchoolIdentity
from lsia.infrastructure.models import Device, EnrollmentTicket, Teacher
from lsia.infrastructure.security import create_token

DEVICE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,63}$")
TICKET_MINUTES = 15


def _utcnow() -> datetime:
    return datetime.now(UTC)


def create_ticket(
    session: Session,
    identity: SchoolIdentity,
    actor: Teacher,
    *,
    base_url: str | None,
) -> dict[str, Any]:
    url = (base_url or settings.public_base_url).strip().rstrip("/")
    if not url.startswith("http://") and not url.startswith("https://"):
        raise BusinessRule("School address must start with http:// or https://")
    ticket = EnrollmentTicket(
        id=str(uuid.uuid4()),
        created_by=actor.id,
        base_url=url,
        expires_at=_utcnow() + timedelta(minutes=TICKET_MINUTES),
    )
    session.add(ticket)
    session.flush()
    append_event(
        session,
        identity,
        operation="ENROLLMENT_TICKET",
        actor=actor,
        payload={"base_url": url},
        entity_type="enrollment_ticket",
        entity_id=ticket.id,
    )
    return ticket_payload(session, identity, ticket)


def ticket_payload(session: Session, identity: SchoolIdentity, ticket: EnrollmentTicket) -> dict[str, Any]:
    return {
        "v": 1,
        "ticket": ticket.id,
        "school_id": identity.school_id,
        "school_name": school_name(session),
        "school_public_key": identity.public_key_b64,
        "base_url": ticket.base_url,
        "expires_at": int(ticket.expires_at.timestamp() * 1000),
    }


def get_open_ticket(session: Session, ticket_id: str) -> EnrollmentTicket:
    ticket = session.get(EnrollmentTicket, ticket_id)
    if ticket is None:
        raise NotFound("Enrollment code not found.")
    if ticket.used_at is not None:
        raise BusinessRule("This enrollment code has already been used.")
    expires = ticket.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires < _utcnow():
        raise BusinessRule("This enrollment code has expired. Ask the office for a new one.")
    return ticket


def inspect_ticket(session: Session, identity: SchoolIdentity, ticket_id: str) -> dict[str, Any]:
    ticket = get_open_ticket(session, ticket_id)
    return ticket_payload(session, identity, ticket)


def _require_ed25519_key(public_key: str) -> str:
    try:
        raw = base64.b64decode(public_key)
    except Exception as exc:
        raise BusinessRule("Device public key is not valid base64.") from exc
    if len(raw) != 32:
        raise BusinessRule("Device public key must be a 32-byte Ed25519 key.")
    return base64.b64encode(raw).decode("ascii")


def enroll_device(
    session: Session,
    identity: SchoolIdentity,
    *,
    ticket_id: str,
    teacher_id: str,
    password: str,
    device_id: str,
    device_name: str,
    public_key: str,
) -> dict[str, Any]:
    ticket = get_open_ticket(session, ticket_id)
    token, teacher = login(session, teacher_id, password)
    if not DEVICE_ID_RE.match(device_id.strip()):
        raise BusinessRule("Device id must be 2–64 characters using letters, numbers, _ . -")
    existing = session.get(Device, device_id.strip())
    if existing:
        raise Conflict("A device with this id is already registered.")
    key = _require_ed25519_key(public_key)
    name = (device_name or "Teacher phone").strip()[:120]
    device = Device(
        id=device_id.strip(),
        teacher_id=teacher.id,
        public_key=key,
        device_name=name,
        status="active",
    )
    session.add(device)
    ticket.used_at = _utcnow()
    ticket.device_id = device.id
    teacher.public_key = key
    session.flush()
    append_event(
        session,
        identity,
        operation="DEVICE_ENROLL",
        actor=teacher,
        payload={"device_id": device.id, "device_name": device.device_name},
        entity_type="device",
        entity_id=device.id,
    )
    return {
        "token": token,
        "teacher": teacher,
        "device": device,
        "school": {
            "id": identity.school_id,
            "name": school_name(session),
            "public_key": identity.public_key_b64,
            "base_url": ticket.base_url,
        },
        "directory": directory_snapshot(session, teacher),
    }


def list_devices(session: Session) -> list[Device]:
    return list(session.scalars(select(Device).order_by(Device.enrolled_at.desc())).all())


def revoke_device(session: Session, identity: SchoolIdentity, actor: Teacher, device_id: str) -> Device:
    device = session.get(Device, device_id)
    if device is None:
        raise NotFound("Device not found.")
    device.status = "revoked"
    append_event(
        session,
        identity,
        operation="DEVICE_REVOKE",
        actor=actor,
        payload={"teacher_id": device.teacher_id},
        entity_type="device",
        entity_id=device.id,
    )
    return device


def revoke_teacher_devices(session: Session, teacher_id: str) -> None:
    for device in session.scalars(select(Device).where(Device.teacher_id == teacher_id)).all():
        device.status = "revoked"


def directory_snapshot(session: Session, actor: Teacher) -> dict[str, Any]:
    from lsia.api.serialize import class_out, student_out, subject_out

    return {
        "classes": [class_out(row) for row in list_classes(session, actor=actor)],
        "subjects": [subject_out(row) for row in list_subjects(session)],
        "students": [student_out(row) for row in list_students(session, actor=actor)],
        "assigned_classes": sorted(assigned_class_ids(actor) or []),
    }


def qr_payload_bytes(payload: dict[str, Any]) -> bytes:
    import io

    import segno

    qr = segno.make(json.dumps(payload, separators=(",", ":"), sort_keys=True), error="m")
    buffer = io.BytesIO()
    qr.save(buffer, kind="png", scale=6, border=2)
    return buffer.getvalue()
