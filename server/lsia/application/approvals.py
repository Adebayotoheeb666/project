from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from lsia.application.errors import BusinessRule, NotFound, PermissionDenied
from lsia.application.events import append_event
from lsia.domain.permissions import Permission, parse_role
from lsia.infrastructure.crypto import SchoolIdentity
from lsia.infrastructure.models import Approval, Event, Score, Student, Teacher


def create_approval_request(
    session: Session,
    *,
    event_id: str,
    requested_by: str,
) -> Approval:
    approval = Approval(
        id=str(uuid.uuid4()),
        event_id=event_id,
        requested_by=requested_by,
        status="PENDING_APPROVAL",
    )
    session.add(approval)
    session.flush()
    return approval


def list_approvals(session: Session, status: str | None = None) -> list[dict[str, Any]]:
    query = select(Approval).order_by(Approval.created_at.desc())
    if status:
        query = query.where(Approval.status == status)
    rows = list(session.scalars(query).all())

    results = []
    for app in rows:
        event = session.get(Event, app.event_id)
        results.append(
            {
                "id": app.id,
                "event_id": app.event_id,
                "requested_by": app.requested_by,
                "approved_by": app.approved_by,
                "status": app.status,
                "created_at": app.created_at.isoformat() if app.created_at else None,
                "updated_at": app.updated_at.isoformat() if app.updated_at else None,
                "event": {
                    "operation": event.operation if event else None,
                    "student_id": event.student_id if event else None,
                    "payload": event.payload if event else None,
                    "timestamp": event.timestamp if event else None,
                }
                if event
                else None,
            }
        )
    return results


def approve_request(
    session: Session,
    identity: SchoolIdentity,
    actor: Teacher,
    approval_id: str,
) -> dict[str, Any]:
    role = parse_role(actor.role_json)
    if role.kind != "administrator":
        raise PermissionDenied("Only administrators can approve requests.")

    approval = session.get(Approval, approval_id)
    if approval is None:
        raise NotFound("Approval request not found.")
    if approval.status != "PENDING_APPROVAL":
        raise BusinessRule(f"Approval request is already {approval.status}.")

    event = session.get(Event, approval.event_id)
    if event is None:
        raise NotFound("Linked event not found.")

    approval.status = "APPROVED"
    approval.approved_by = actor.id
    event.status = "APPLIED"

    # If event was a deferred score update or student update, apply it
    if event.operation == "SCORE_UPDATE" and event.student_id:
        p = event.payload
        score = session.scalar(
            select(Score).where(
                Score.student_id == event.student_id,
                Score.subject_id == p.get("subject_id"),
                Score.term == p.get("term"),
            )
        )
        if score:
            if "ca_score" in p:
                score.ca_score = p["ca_score"]
            if "exam_score" in p:
                score.exam_score = p["exam_score"]
            score.total_score = p.get("total_score")
            score.recorded_by = actor.id

    append_event(
        session,
        identity,
        operation="APPROVAL_DECISION",
        actor=actor,
        payload={"approval_id": approval.id, "decision": "APPROVED", "event_id": event.id},
        entity_type="approval",
        entity_id=approval.id,
    )
    return {"id": approval.id, "status": "APPROVED"}


def reject_request(
    session: Session,
    identity: SchoolIdentity,
    actor: Teacher,
    approval_id: str,
    reason: str = "",
) -> dict[str, Any]:
    role = parse_role(actor.role_json)
    if role.kind != "administrator":
        raise PermissionDenied("Only administrators can reject requests.")

    approval = session.get(Approval, approval_id)
    if approval is None:
        raise NotFound("Approval request not found.")
    if approval.status != "PENDING_APPROVAL":
        raise BusinessRule(f"Approval request is already {approval.status}.")

    event = session.get(Event, approval.event_id)
    if event:
        event.status = "REJECTED"

    approval.status = "REJECTED"
    approval.approved_by = actor.id

    append_event(
        session,
        identity,
        operation="APPROVAL_DECISION",
        actor=actor,
        payload={"approval_id": approval.id, "decision": "REJECTED", "reason": reason, "event_id": approval.event_id},
        entity_type="approval",
        entity_id=approval.id,
    )
    return {"id": approval.id, "status": "REJECTED"}
