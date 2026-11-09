from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from lsia.application.academics import MAX_CA_SCORE, MAX_EXAM_SCORE, MAX_TOTAL_SCORE
from lsia.application.auth import school_name
from lsia.application.clock import advance_lamport, get_lamport
from lsia.application.directory import assigned_class_ids
from lsia.application.errors import BusinessRule, NotFound, PermissionDenied
from lsia.domain.permissions import Permission, parse_role
from lsia.infrastructure.crypto import SchoolIdentity, verify_signature
from lsia.infrastructure.models import Attendance, AuditLog, Device, Event, SchoolClass, Score, Student, Subject, Teacher

MAX_SYNC_BATCH_SIZE = 20
MAX_SYNC_PAYLOAD_BYTES = 500 * 1024  # 500 KB


def canonical_operation_json(op: dict[str, Any]) -> bytes:
    canonical = {
        "id": op["id"],
        "student_id": op.get("student_id"),
        "type": op["type"],
        "payload": op["payload"],
        "teacher_id": op["teacher_id"],
        "device_id": op["device_id"],
        "timestamp": op["timestamp"],
        "lamport_clock": op["lamport_clock"],
    }
    return json.dumps(canonical, separators=(",", ":"), sort_keys=True).encode("utf-8")


def handshake(
    session: Session,
    identity: SchoolIdentity,
    *,
    device_id: str,
    timestamp: int,
    challenge_response: str,
) -> dict[str, Any]:
    device = session.get(Device, device_id.strip())
    if device is None:
        raise NotFound("Device not recognized. Please enroll this device first.")
    if device.status != "active":
        raise PermissionDenied("This device has been revoked.")

    teacher = session.get(Teacher, device.teacher_id)
    if teacher is None or teacher.revoked:
        raise PermissionDenied("Teacher account is inactive or revoked.")

    challenge = f"HANDSHAKE:{device.id}:{timestamp}".encode("utf-8")
    if not verify_signature(device.public_key, challenge_response, challenge):
        raise PermissionDenied("Cryptographic challenge failed. Invalid device signature.")

    role = parse_role(teacher.role_json)
    return {
        "school_id": identity.school_id,
        "school_name": school_name(session),
        "school_public_key": identity.public_key_b64,
        "teacher_id": teacher.id,
        "device_id": device.id,
        "role": role.to_json(),
        "assigned_classes": role.classes,
        "assigned_subjects": role.subjects,
        "server_clock": get_lamport(session),
        "status": "ready",
    }


def push_operations(
    session: Session,
    identity: SchoolIdentity,
    *,
    device_id: str,
    operations: list[dict[str, Any]],
    raw_size_bytes: int = 0,
) -> dict[str, Any]:
    if raw_size_bytes > MAX_SYNC_PAYLOAD_BYTES:
        raise BusinessRule(f"Sync batch size exceeds maximum limit of {MAX_SYNC_PAYLOAD_BYTES} bytes.")
    if len(operations) > MAX_SYNC_BATCH_SIZE:
        raise BusinessRule(f"Sync batch cannot contain more than {MAX_SYNC_BATCH_SIZE} operations.")

    device = session.get(Device, device_id.strip())
    if device is None:
        raise NotFound("Device not recognized.")
    if device.status != "active":
        raise PermissionDenied("Device is revoked.")

    teacher = session.get(Teacher, device.teacher_id)
    if teacher is None or teacher.revoked:
        raise PermissionDenied("Teacher account is inactive or revoked.")

    role = parse_role(teacher.role_json)
    receipts: list[dict[str, Any]] = []

    for op in operations:
        op_id = str(op.get("id", "")).strip()
        op_type = str(op.get("type", "")).strip()
        student_id = op.get("student_id")
        payload = op.get("payload", {})
        op_teacher_id = str(op.get("teacher_id", "")).strip()
        op_device_id = str(op.get("device_id", "")).strip()
        remote_clock = int(op.get("lamport_clock", 0))
        op_timestamp = int(op.get("timestamp", 0))
        signature = str(op.get("signature", ""))

        if not op_id or not op_type:
            receipts.append({"id": op_id, "status": "REJECTED", "error": "Invalid operation structure."})
            continue

        if op_device_id != device.id or op_teacher_id != teacher.id:
            receipts.append({"id": op_id, "status": "REJECTED", "error": "Device or teacher mismatch."})
            continue

        # Replay protection
        existing_event = session.get(Event, op_id)
        if existing_event is not None:
            receipts.append({"id": op_id, "status": existing_event.status, "error": None})
            continue

        # Verify device signature
        canonical_bytes = canonical_operation_json(op)
        if not verify_signature(device.public_key, signature, canonical_bytes):
            receipts.append({"id": op_id, "status": "REJECTED", "error": "Invalid cryptographic signature."})
            continue

        # Advance server clock
        server_clock = advance_lamport(session, remote_clock)

        # Process mutation
        status = "APPLIED"
        error_msg = None

        try:
            if op_type == "STUDENT_UPSERT":
                status = _apply_student_upsert(session, teacher, role, op_id, student_id, payload, remote_clock)
            elif op_type == "SCORE_UPDATE":
                status = _apply_score_update(session, teacher, role, op_id, student_id, payload, remote_clock)
            elif op_type == "ATTENDANCE_RECORD":
                status = _apply_attendance_record(session, teacher, role, op_id, student_id, payload)
            else:
                status = "REJECTED"
                error_msg = f"Unknown operation type: {op_type}"
        except Exception as exc:
            status = "REJECTED"
            error_msg = str(exc)

        # Store event
        event = Event(
            id=op_id,
            student_id=student_id,
            operation=op_type,
            payload=payload,
            teacher_id=teacher.id,
            device_id=device.id,
            signature=signature,
            timestamp=op_timestamp,
            lamport_clock=server_clock,
            status=status,
        )
        session.add(event)

        session.add(
            AuditLog(
                id=str(uuid.uuid4()),
                user_id=teacher.id,
                operation=f"SYNC_{op_type}",
                entity_type="event",
                entity_id=op_id,
                details={"status": status, "device_id": device.id, "error": error_msg},
            )
        )
        receipts.append({"id": op_id, "status": status, "error": error_msg})

    device.last_sync_at = datetime.now(UTC)
    session.flush()

    return {
        "server_clock": get_lamport(session),
        "receipts": receipts,
    }


def _apply_student_upsert(
    session: Session,
    teacher: Teacher,
    role: Any,
    op_id: str,
    student_id: str | None,
    payload: dict[str, Any],
    remote_clock: int,
) -> str:
    if not student_id:
        return "REJECTED"
    if not role.allows(Permission.EDIT_STUDENTS):
        return "REJECTED"

    class_id = payload.get("class_id")
    if role.kind != "administrator" and class_id and class_id not in role.classes:
        return "REJECTED"

    student = session.get(Student, student_id)
    expected_version = payload.get("expected_version")

    if student is not None:
        # Detect concurrent modification conflict
        if expected_version is not None and student.version != expected_version:
            # Preserved as conflict for administrative resolution
            return "CONFLICT"

        # Apply update
        student.class_id = class_id or student.class_id
        student_data = dict(student.data_json or {})
        student_data.update(payload.get("data", {}))
        student.data_json = student_data
        student.version += 1
        student.updated_by = teacher.id
    else:
        student = Student(
            id=student_id,
            class_id=class_id,
            data_json=payload.get("data", {}),
            version=1,
            updated_by=teacher.id,
        )
        session.add(student)

    return "APPLIED"


def _apply_score_update(
    session: Session,
    teacher: Teacher,
    role: Any,
    op_id: str,
    student_id: str | None,
    payload: dict[str, Any],
    remote_clock: int,
) -> str:
    if not student_id:
        return "REJECTED"

    subject_id = payload.get("subject_id")
    term = payload.get("term")
    ca = payload.get("ca_score")
    exam = payload.get("exam_score")

    if not subject_id or not term:
        return "REJECTED"

    student = session.get(Student, student_id)
    if student is None:
        return "REJECTED"

    if role.kind != "administrator":
        if student.class_id and student.class_id not in role.classes:
            return "REJECTED"
        if subject_id not in role.subjects:
            return "REJECTED"

    if ca is not None:
        if not role.allows(Permission.ENTER_CA) or ca < 0 or ca > MAX_CA_SCORE:
            return "REJECTED"
    if exam is not None:
        if not role.allows(Permission.ENTER_EXAM) or exam < 0 or exam > MAX_EXAM_SCORE:
            return "REJECTED"

    existing = session.scalar(
        select(Score).where(
            and_(
                Score.student_id == student_id,
                Score.subject_id == subject_id,
                Score.term == term,
            )
        )
    )

    final_ca = ca if ca is not None else (existing.ca_score if existing else None)
    final_exam = exam if exam is not None else (existing.exam_score if existing else None)
    final_total = (final_ca or 0.0) + (final_exam or 0.0) if (final_ca is not None or final_exam is not None) else None

    if final_total is not None and final_total > MAX_TOTAL_SCORE:
        return "REJECTED"

    # Check for conflict: if someone else modified this score recently
    if existing is not None and existing.recorded_by != teacher.id:
        # Concurrent modification by different teacher -> Conflict flag
        return "CONFLICT"

    if existing is None:
        new_score = Score(
            id=str(uuid.uuid4()),
            student_id=student_id,
            subject_id=subject_id,
            term=term,
            ca_score=final_ca,
            exam_score=final_exam,
            total_score=final_total,
            recorded_by=teacher.id,
        )
        session.add(new_score)
    else:
        existing.ca_score = final_ca
        existing.exam_score = final_exam
        existing.total_score = final_total
        existing.recorded_by = teacher.id

    return "APPLIED"


def _apply_attendance_record(
    session: Session,
    teacher: Teacher,
    role: Any,
    op_id: str,
    student_id: str | None,
    payload: dict[str, Any],
) -> str:
    if not student_id:
        return "REJECTED"

    class_id = payload.get("class_id")
    date_str = payload.get("date")
    status_val = str(payload.get("status", "")).strip().lower()

    if status_val not in {"present", "absent", "late", "excused"}:
        return "REJECTED"

    try:
        attendance_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception:
        return "REJECTED"

    student = session.get(Student, student_id)
    if student is None:
        return "REJECTED"

    if role.kind != "administrator" and class_id and class_id not in role.classes:
        return "REJECTED"

    existing = session.scalar(
        select(Attendance).where(
            and_(Attendance.student_id == student_id, Attendance.date == attendance_date)
        )
    )

    if existing is None:
        att = Attendance(
            id=str(uuid.uuid4()),
            student_id=student_id,
            class_id=class_id or student.class_id,
            date=attendance_date,
            status=status_val,
            recorded_by=teacher.id,
        )
        session.add(att)
    else:
        existing.class_id = class_id or existing.class_id
        existing.status = status_val
        existing.recorded_by = teacher.id

    return "APPLIED"


def pull_operations(
    session: Session,
    *,
    device_id: str,
    since_clock: int = 0,
    limit: int = 20,
) -> dict[str, Any]:
    device = session.get(Device, device_id.strip())
    if device is None:
        raise NotFound("Device not recognized.")
    if device.status != "active":
        raise PermissionDenied("Device is revoked.")

    teacher = session.get(Teacher, device.teacher_id)
    if teacher is None or teacher.revoked:
        raise PermissionDenied("Teacher account is inactive or revoked.")

    allowed_classes = assigned_class_ids(teacher)
    limit = min(max(1, limit), MAX_SYNC_BATCH_SIZE)

    # Fetch applied events newer than since_clock
    query = (
        select(Event)
        .where(and_(Event.lamport_clock > since_clock, Event.status == "APPLIED"))
        .order_by(Event.lamport_clock.asc())
        .limit(limit + 1)
    )
    rows = list(session.scalars(query).all())
    has_more = len(rows) > limit
    selected_rows = rows[:limit]

    out_events = []
    for row in selected_rows:
        # Filter by class if necessary
        if allowed_classes is not None and row.student_id:
            # Check if student belongs to one of the teacher's classes
            student = session.get(Student, row.student_id)
            if student and student.class_id and student.class_id not in allowed_classes:
                continue

        out_events.append(
            {
                "id": row.id,
                "student_id": row.student_id,
                "type": row.operation,
                "payload": row.payload,
                "teacher_id": row.teacher_id,
                "device_id": row.device_id,
                "timestamp": row.timestamp,
                "lamport_clock": row.lamport_clock,
                "signature": row.signature,
                "status": row.status,
            }
        )

    return {
        "events": out_events,
        "latest_clock": get_lamport(session),
        "has_more": has_more,
    }
