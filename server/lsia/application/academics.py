from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from lsia.application.directory import assigned_class_ids, ensure_class_access
from lsia.application.errors import BusinessRule, NotFound, PermissionDenied
from lsia.application.events import append_event
from lsia.domain.permissions import Permission, parse_role
from lsia.infrastructure.crypto import SchoolIdentity
from lsia.infrastructure.models import Attendance, SchoolClass, Score, Student, Subject, Teacher

VALID_ATTENDANCE_STATUSES = {"present", "absent", "late", "excused"}
MAX_CA_SCORE = 40.0
MAX_EXAM_SCORE = 60.0
MAX_TOTAL_SCORE = 100.0


def calculate_grade(total_score: float | None) -> dict[str, str]:
    if total_score is None:
        return {"grade": "—", "remark": "No score"}
    score = round(total_score, 1)
    if score >= 75.0:
        return {"grade": "A1", "remark": "Excellent"}
    if score >= 70.0:
        return {"grade": "B2", "remark": "Very Good"}
    if score >= 65.0:
        return {"grade": "B3", "remark": "Good"}
    if score >= 60.0:
        return {"grade": "C4", "remark": "Credit"}
    if score >= 55.0:
        return {"grade": "C5", "remark": "Credit"}
    if score >= 50.0:
        return {"grade": "C6", "remark": "Credit"}
    if score >= 45.0:
        return {"grade": "D7", "remark": "Pass"}
    if score >= 40.0:
        return {"grade": "E8", "remark": "Pass"}
    return {"grade": "F9", "remark": "Fail"}


def ensure_subject_access(actor: Teacher, subject_id: str) -> None:
    role = parse_role(actor.role_json)
    if role.kind == "administrator":
        return
    if subject_id not in role.subjects:
        raise PermissionDenied(f"Subject '{subject_id}' is not assigned to you.")


def record_scores(
    session: Session,
    identity: SchoolIdentity,
    actor: Teacher,
    *,
    scores: list[dict[str, Any]],
) -> list[Score]:
    role = parse_role(actor.role_json)
    results: list[Score] = []

    for item in scores:
        student_id = item["student_id"].strip()
        subject_id = item["subject_id"].strip()
        term = item["term"].strip()
        ca = item.get("ca_score")
        exam = item.get("exam_score")

        student = session.get(Student, student_id)
        if student is None:
            raise NotFound(f"Student '{student_id}' not found.")
        subject = session.get(Subject, subject_id)
        if subject is None:
            raise NotFound(f"Subject '{subject_id}' not found.")

        ensure_class_access(actor, student.class_id)
        ensure_subject_access(actor, subject_id)

        if ca is not None:
            if not role.allows(Permission.ENTER_CA):
                raise PermissionDenied("You do not have permission to enter continuous assessment scores.")
            if ca < 0.0 or ca > MAX_CA_SCORE:
                raise BusinessRule(f"CA score must be between 0 and {MAX_CA_SCORE}.")

        if exam is not None:
            if not role.allows(Permission.ENTER_EXAM):
                raise PermissionDenied("You do not have permission to enter examination scores.")
            if exam < 0.0 or exam > MAX_EXAM_SCORE:
                raise BusinessRule(f"Exam score must be between 0 and {MAX_EXAM_SCORE}.")

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
        final_total = None
        if final_ca is not None or final_exam is not None:
            final_total = (final_ca or 0.0) + (final_exam or 0.0)
            if final_total > MAX_TOTAL_SCORE:
                raise BusinessRule(f"Total score cannot exceed {MAX_TOTAL_SCORE}.")

        if existing is None:
            score_rec = Score(
                id=str(uuid.uuid4()),
                student_id=student_id,
                subject_id=subject_id,
                term=term,
                ca_score=final_ca,
                exam_score=final_exam,
                total_score=final_total,
                recorded_by=actor.id,
            )
            session.add(score_rec)
        else:
            score_rec = existing
            score_rec.ca_score = final_ca
            score_rec.exam_score = final_exam
            score_rec.total_score = final_total
            score_rec.recorded_by = actor.id

        session.flush()

        append_event(
            session,
            identity,
            operation="SCORE_UPDATE",
            actor=actor,
            student_id=student_id,
            payload={
                "student_id": student_id,
                "subject_id": subject_id,
                "term": term,
                "ca_score": final_ca,
                "exam_score": final_exam,
                "total_score": final_total,
            },
            entity_type="score",
            entity_id=score_rec.id,
        )
        results.append(score_rec)

    return results


def list_scores(
    session: Session,
    actor: Teacher,
    *,
    class_id: str | None = None,
    subject_id: str | None = None,
    term: str | None = None,
    student_id: str | None = None,
) -> list[Score]:
    query = select(Score)
    if student_id:
        student = session.get(Student, student_id)
        if student:
            ensure_class_access(actor, student.class_id, allow_unassigned=True)
        query = query.where(Score.student_id == student_id)
    elif class_id:
        ensure_class_access(actor, class_id)
        student_ids = select(Student.id).where(Student.class_id == class_id)
        query = query.where(Score.student_id.in_(student_ids))
    else:
        allowed_classes = assigned_class_ids(actor)
        if allowed_classes is not None:
            student_ids = select(Student.id).where(Student.class_id.in_(allowed_classes))
            query = query.where(Score.student_id.in_(student_ids))

    if subject_id:
        query = query.where(Score.subject_id == subject_id)
    if term:
        query = query.where(Score.term == term)

    return list(session.scalars(query.order_by(Score.term, Score.subject_id)).all())


def record_attendance(
    session: Session,
    identity: SchoolIdentity,
    actor: Teacher,
    *,
    class_id: str,
    attendance_date: date,
    records: list[dict[str, str]],
) -> list[Attendance]:
    klass = session.get(SchoolClass, class_id)
    if klass is None:
        raise NotFound(f"Class '{class_id}' not found.")
    ensure_class_access(actor, class_id)

    results: list[Attendance] = []
    for item in records:
        student_id = item["student_id"].strip()
        status_val = item["status"].strip().lower()
        if status_val not in VALID_ATTENDANCE_STATUSES:
            raise BusinessRule(f"Invalid attendance status '{status_val}'. Must be one of: {', '.join(sorted(VALID_ATTENDANCE_STATUSES))}")

        student = session.get(Student, student_id)
        if student is None or student.class_id != class_id:
            raise NotFound(f"Student '{student_id}' does not belong to class '{class_id}'.")

        existing = session.scalar(
            select(Attendance).where(
                and_(Attendance.student_id == student_id, Attendance.date == attendance_date)
            )
        )
        if existing is None:
            att = Attendance(
                id=str(uuid.uuid4()),
                student_id=student_id,
                class_id=class_id,
                date=attendance_date,
                status=status_val,
                recorded_by=actor.id,
            )
            session.add(att)
        else:
            att = existing
            att.class_id = class_id
            att.status = status_val
            att.recorded_by = actor.id

        session.flush()

        append_event(
            session,
            identity,
            operation="ATTENDANCE_RECORD",
            actor=actor,
            student_id=student_id,
            payload={
                "student_id": student_id,
                "class_id": class_id,
                "date": attendance_date.isoformat(),
                "status": status_val,
            },
            entity_type="attendance",
            entity_id=att.id,
        )
        results.append(att)

    return results


def list_attendance(
    session: Session,
    actor: Teacher,
    *,
    class_id: str | None = None,
    student_id: str | None = None,
    attendance_date: date | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[Attendance]:
    query = select(Attendance)
    if student_id:
        student = session.get(Student, student_id)
        if student:
            ensure_class_access(actor, student.class_id, allow_unassigned=True)
        query = query.where(Attendance.student_id == student_id)
    elif class_id:
        ensure_class_access(actor, class_id)
        query = query.where(Attendance.class_id == class_id)
    else:
        allowed = assigned_class_ids(actor)
        if allowed is not None:
            query = query.where(Attendance.class_id.in_(allowed))

    if attendance_date:
        query = query.where(Attendance.date == attendance_date)
    if from_date:
        query = query.where(Attendance.date >= from_date)
    if to_date:
        query = query.where(Attendance.date <= to_date)

    return list(session.scalars(query.order_by(Attendance.date.desc(), Attendance.student_id)).all())


def attendance_summary(
    session: Session,
    actor: Teacher,
    *,
    class_id: str | None = None,
    student_id: str | None = None,
) -> dict[str, Any]:
    records = list_attendance(session, actor, class_id=class_id, student_id=student_id)
    total = len(records)
    present = sum(1 for r in records if r.status == "present")
    absent = sum(1 for r in records if r.status == "absent")
    late = sum(1 for r in records if r.status == "late")
    excused = sum(1 for r in records if r.status == "excused")
    pct = round(((present + late) / total * 100), 1) if total > 0 else 100.0

    return {
        "total_days": total,
        "present": present,
        "absent": absent,
        "late": late,
        "excused": excused,
        "percentage": pct,
    }
