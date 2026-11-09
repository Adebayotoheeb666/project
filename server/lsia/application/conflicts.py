from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from lsia.application.errors import BusinessRule, NotFound, PermissionDenied
from lsia.application.events import append_event
from lsia.domain.permissions import parse_role
from lsia.infrastructure.crypto import SchoolIdentity
from lsia.infrastructure.models import Event, Score, Student, Teacher


def list_conflicts(session: Session) -> list[dict[str, Any]]:
    events = list(
        session.scalars(
            select(Event).where(Event.status == "CONFLICT").order_by(Event.timestamp.desc())
        ).all()
    )

    conflicts = []
    for ev in events:
        current_state = None
        if ev.operation == "SCORE_UPDATE" and ev.student_id:
            subj = ev.payload.get("subject_id")
            term = ev.payload.get("term")
            score = session.scalar(
                select(Score).where(
                    Score.student_id == ev.student_id,
                    Score.subject_id == subj,
                    Score.term == term,
                )
            )
            if score:
                current_state = {
                    "ca_score": score.ca_score,
                    "exam_score": score.exam_score,
                    "total_score": score.total_score,
                    "recorded_by": score.recorded_by,
                }
        elif ev.operation == "STUDENT_UPSERT" and ev.student_id:
            student = session.get(Student, ev.student_id)
            if student:
                current_state = {
                    "class_id": student.class_id,
                    "version": student.version,
                    "data": student.data_json,
                    "updated_by": student.updated_by,
                }

        conflicts.append(
            {
                "id": ev.id,
                "operation": ev.operation,
                "student_id": ev.student_id,
                "incoming_payload": ev.payload,
                "incoming_teacher_id": ev.teacher_id,
                "incoming_device_id": ev.device_id,
                "incoming_timestamp": ev.timestamp,
                "current_state": current_state,
                "status": ev.status,
            }
        )
    return conflicts


def resolve_conflict(
    session: Session,
    identity: SchoolIdentity,
    actor: Teacher,
    event_id: str,
    *,
    choice: str,
    custom_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    role = parse_role(actor.role_json)
    if role.kind != "administrator":
        raise PermissionDenied("Only administrators can resolve data conflicts.")

    ev = session.get(Event, event_id)
    if ev is None:
        raise NotFound("Conflict event not found.")
    if ev.status != "CONFLICT":
        raise BusinessRule(f"Event is not in conflict status (status: {ev.status}).")

    if choice not in ("keep_current", "use_incoming", "custom"):
        raise BusinessRule("Choice must be 'keep_current', 'use_incoming', or 'custom'.")

    # If use_incoming or custom, apply to database
    applied_payload: dict[str, Any] = {}
    if choice == "use_incoming":
        applied_payload = ev.payload
    elif choice == "custom":
        applied_payload = custom_payload or {}

    if choice in ("use_incoming", "custom") and ev.student_id:
        if ev.operation == "SCORE_UPDATE":
            subj = applied_payload.get("subject_id") or ev.payload.get("subject_id")
            term = applied_payload.get("term") or ev.payload.get("term")
            ca = applied_payload.get("ca_score")
            exam = applied_payload.get("exam_score")
            total = (ca or 0.0) + (exam or 0.0) if (ca is not None or exam is not None) else None

            score = session.scalar(
                select(Score).where(
                    Score.student_id == ev.student_id,
                    Score.subject_id == subj,
                    Score.term == term,
                )
            )
            if score:
                score.ca_score = ca
                score.exam_score = exam
                score.total_score = total
                score.recorded_by = actor.id

        elif ev.operation == "STUDENT_UPSERT":
            student = session.get(Student, ev.student_id)
            if student:
                if "class_id" in applied_payload:
                    student.class_id = applied_payload["class_id"]
                if "data" in applied_payload:
                    data = dict(student.data_json or {})
                    data.update(applied_payload["data"])
                    student.data_json = data
                student.version += 1
                student.updated_by = actor.id

    ev.status = "RESOLVED"
    append_event(
        session,
        identity,
        operation="CONFLICT_RESOLVED",
        actor=actor,
        student_id=ev.student_id,
        payload={"conflict_event_id": ev.id, "choice": choice, "applied": applied_payload},
        entity_type="conflict",
        entity_id=ev.id,
    )

    return {"id": ev.id, "status": "RESOLVED", "choice": choice}
