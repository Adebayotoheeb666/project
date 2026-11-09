from __future__ import annotations

import json
import time
import uuid
from typing import Any

from sqlalchemy.orm import Session

from lsia.application.clock import next_lamport
from lsia.infrastructure.crypto import SchoolIdentity
from lsia.infrastructure.models import AuditLog, Event, Teacher


def append_event(
    session: Session,
    identity: SchoolIdentity,
    *,
    operation: str,
    actor: Teacher,
    payload: dict[str, Any],
    student_id: str | None = None,
    entity_type: str,
    entity_id: str,
    status: str = "APPLIED",
) -> Event:
    event_id = str(uuid.uuid4())
    timestamp = int(time.time() * 1000)
    clock = next_lamport(session)
    canonical = json.dumps(
        {
            "id": event_id,
            "student_id": student_id,
            "type": operation,
            "payload": payload,
            "teacher_id": actor.id,
            "device_id": "school-computer",
            "timestamp": timestamp,
            "lamport_clock": clock,
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    event = Event(
        id=event_id,
        student_id=student_id,
        operation=operation,
        payload=payload,
        teacher_id=actor.id,
        device_id="school-computer",
        signature=identity.sign(canonical.encode("utf-8")),
        timestamp=timestamp,
        lamport_clock=clock,
        status=status,
    )
    session.add(event)
    session.add(
        AuditLog(
            id=str(uuid.uuid4()),
            user_id=actor.id,
            operation=operation,
            entity_type=entity_type,
            entity_id=entity_id,
            details=payload,
        )
    )
    return event
