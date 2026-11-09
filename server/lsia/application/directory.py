from __future__ import annotations

import re
from typing import Any

from sqlalchemy import String, cast, or_, select
from sqlalchemy.orm import Session

from lsia.application.errors import BusinessRule, Conflict, NotFound, PermissionDenied
from lsia.application.events import append_event
from lsia.domain.permissions import Role, parse_role
from lsia.infrastructure.crypto import SchoolIdentity
from lsia.infrastructure.models import SchoolClass, Student, Subject, Teacher
from lsia.infrastructure.security import hash_password

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_./-]{1,63}$")


def _require_id(value: str, label: str) -> str:
    cleaned = value.strip()
    if not ID_RE.match(cleaned):
        raise BusinessRule(f"{label} must be 2–64 characters using letters, numbers, _ . / -")
    return cleaned


def assigned_class_ids(actor: Teacher) -> set[str] | None:
    role = parse_role(actor.role_json)
    if role.kind == "administrator":
        return None
    return set(role.classes)


def ensure_class_access(actor: Teacher, class_id: str | None, *, allow_unassigned: bool = False) -> None:
    allowed = assigned_class_ids(actor)
    if allowed is None:
        return
    if not class_id:
        if allow_unassigned:
            return
        raise PermissionDenied("This class is not assigned to you.")
    if class_id not in allowed:
        raise PermissionDenied("This class is not assigned to you.")


def list_classes(session: Session, actor: Teacher | None = None) -> list[SchoolClass]:
    rows = list(session.scalars(select(SchoolClass).order_by(SchoolClass.name)).all())
    if actor is None:
        return rows
    allowed = assigned_class_ids(actor)
    if allowed is None:
        return rows
    return [row for row in rows if row.id in allowed]


def create_class(
    session: Session,
    identity: SchoolIdentity,
    actor: Teacher,
    *,
    class_id: str,
    name: str,
    academic_year: str,
    class_teacher_id: str | None,
) -> SchoolClass:
    cid = _require_id(class_id, "Class id")
    if session.get(SchoolClass, cid):
        raise Conflict("A class with this id already exists.")
    if class_teacher_id:
        if session.get(Teacher, class_teacher_id) is None:
            raise NotFound("Class teacher not found.")
    record = SchoolClass(
        id=cid,
        name=name.strip(),
        academic_year=academic_year.strip(),
        class_teacher_id=class_teacher_id or None,
    )
    session.add(record)
    session.flush()
    append_event(
        session,
        identity,
        operation="CLASS_CREATE",
        actor=actor,
        payload={"name": record.name, "academic_year": record.academic_year},
        entity_type="class",
        entity_id=record.id,
    )
    return record


def update_class(
    session: Session,
    identity: SchoolIdentity,
    actor: Teacher,
    class_id: str,
    *,
    name: str | None,
    academic_year: str | None,
    class_teacher_id: str | None,
) -> SchoolClass:
    record = session.get(SchoolClass, class_id)
    if record is None:
        raise NotFound("Class not found.")
    if name is not None:
        record.name = name.strip()
    if academic_year is not None:
        record.academic_year = academic_year.strip()
    if class_teacher_id is not None:
        record.class_teacher_id = class_teacher_id or None
    append_event(
        session,
        identity,
        operation="CLASS_UPDATE",
        actor=actor,
        payload={"name": record.name, "academic_year": record.academic_year},
        entity_type="class",
        entity_id=record.id,
    )
    return record


def delete_class(session: Session, identity: SchoolIdentity, actor: Teacher, class_id: str) -> None:
    record = session.get(SchoolClass, class_id)
    if record is None:
        raise NotFound("Class not found.")
    assigned = session.scalar(select(Student).where(Student.class_id == class_id).limit(1))
    if assigned:
        raise BusinessRule("Move or remove students before deleting this class.")
    session.delete(record)
    append_event(
        session,
        identity,
        operation="CLASS_DELETE",
        actor=actor,
        payload={},
        entity_type="class",
        entity_id=class_id,
    )


def list_subjects(session: Session) -> list[Subject]:
    return list(session.scalars(select(Subject).order_by(Subject.name)).all())


def create_subject(
    session: Session,
    identity: SchoolIdentity,
    actor: Teacher,
    *,
    subject_id: str,
    name: str,
    code: str,
) -> Subject:
    sid = _require_id(subject_id, "Subject id")
    if session.get(Subject, sid):
        raise Conflict("A subject with this id already exists.")
    existing_code = session.scalar(select(Subject).where(Subject.code == code.strip().upper()))
    if existing_code:
        raise Conflict("A subject with this code already exists.")
    record = Subject(id=sid, name=name.strip(), code=code.strip().upper())
    session.add(record)
    session.flush()
    append_event(
        session,
        identity,
        operation="SUBJECT_CREATE",
        actor=actor,
        payload={"name": record.name, "code": record.code},
        entity_type="subject",
        entity_id=record.id,
    )
    return record


def update_subject(
    session: Session,
    identity: SchoolIdentity,
    actor: Teacher,
    subject_id: str,
    *,
    name: str | None,
    code: str | None,
) -> Subject:
    record = session.get(Subject, subject_id)
    if record is None:
        raise NotFound("Subject not found.")
    if name is not None:
        record.name = name.strip()
    if code is not None:
        record.code = code.strip().upper()
    append_event(
        session,
        identity,
        operation="SUBJECT_UPDATE",
        actor=actor,
        payload={"name": record.name, "code": record.code},
        entity_type="subject",
        entity_id=record.id,
    )
    return record


def delete_subject(session: Session, identity: SchoolIdentity, actor: Teacher, subject_id: str) -> None:
    record = session.get(Subject, subject_id)
    if record is None:
        raise NotFound("Subject not found.")
    session.delete(record)
    append_event(
        session,
        identity,
        operation="SUBJECT_DELETE",
        actor=actor,
        payload={},
        entity_type="subject",
        entity_id=subject_id,
    )


def list_teachers(session: Session) -> list[Teacher]:
    return list(session.scalars(select(Teacher).order_by(Teacher.name)).all())


def create_teacher(
    session: Session,
    identity: SchoolIdentity,
    actor: Teacher,
    *,
    teacher_id: str,
    name: str,
    password: str | None,
    role: dict[str, Any],
) -> Teacher:
    tid = _require_id(teacher_id, "Teacher id")
    if session.get(Teacher, tid):
        raise Conflict("A teacher with this id already exists.")
    parsed = Role(
        kind=role.get("role", "teacher"),
        classes=list(role.get("classes") or []),
        subjects=list(role.get("subjects") or []),
        permissions=role.get("permissions"),
    )
    record = Teacher(
        id=tid,
        name=name.strip(),
        password_hash=hash_password(password) if password else None,
        role_json=parsed.to_json(),
        revoked=False,
    )
    session.add(record)
    session.flush()
    append_event(
        session,
        identity,
        operation="TEACHER_CREATE",
        actor=actor,
        payload={"name": record.name, "role": parsed.kind},
        entity_type="teacher",
        entity_id=record.id,
    )
    return record


def update_teacher(
    session: Session,
    identity: SchoolIdentity,
    actor: Teacher,
    teacher_id: str,
    *,
    name: str | None,
    role: dict[str, Any] | None,
) -> Teacher:
    record = session.get(Teacher, teacher_id)
    if record is None:
        raise NotFound("Teacher not found.")
    if name is not None:
        record.name = name.strip()
    if role is not None:
        parsed = Role(
            kind=role.get("role", record.role_json.get("role", "teacher")),
            classes=list(role.get("classes") or []),
            subjects=list(role.get("subjects") or []),
            permissions=role.get("permissions"),
        )
        record.role_json = parsed.to_json()
    append_event(
        session,
        identity,
        operation="TEACHER_UPDATE",
        actor=actor,
        payload={"name": record.name},
        entity_type="teacher",
        entity_id=record.id,
    )
    return record


def set_teacher_password(
    session: Session, identity: SchoolIdentity, actor: Teacher, teacher_id: str, password: str
) -> Teacher:
    if len(password) < 8:
        raise BusinessRule("Password must be at least 8 characters.")
    record = session.get(Teacher, teacher_id)
    if record is None:
        raise NotFound("Teacher not found.")
    record.password_hash = hash_password(password)
    append_event(
        session,
        identity,
        operation="TEACHER_PASSWORD",
        actor=actor,
        payload={},
        entity_type="teacher",
        entity_id=record.id,
    )
    return record


def revoke_teacher(session: Session, identity: SchoolIdentity, actor: Teacher, teacher_id: str) -> Teacher:
    record = session.get(Teacher, teacher_id)
    if record is None:
        raise NotFound("Teacher not found.")
    if record.id == actor.id:
        raise BusinessRule("You cannot revoke your own account.")
    record.revoked = True
    from lsia.application.devices import revoke_teacher_devices

    revoke_teacher_devices(session, record.id)
    append_event(
        session,
        identity,
        operation="TEACHER_REVOKE",
        actor=actor,
        payload={},
        entity_type="teacher",
        entity_id=record.id,
    )
    return record


def list_students(
    session: Session,
    *,
    q: str | None = None,
    class_id: str | None = None,
    actor: Teacher | None = None,
) -> list[Student]:
    stmt = select(Student)
    if actor is not None:
        allowed = assigned_class_ids(actor)
        if allowed is not None:
            if class_id:
                ensure_class_access(actor, class_id)
                stmt = stmt.where(Student.class_id == class_id)
            elif not allowed:
                return []
            else:
                stmt = stmt.where(Student.class_id.in_(allowed))
        elif class_id:
            stmt = stmt.where(Student.class_id == class_id)
    elif class_id:
        stmt = stmt.where(Student.class_id == class_id)
    if q:
        needle = f"%{q.strip()}%"
        stmt = stmt.where(or_(Student.id.ilike(needle), cast(Student.data_json, String).ilike(needle)))
    return list(session.scalars(stmt.order_by(Student.id)).all())


def _student_payload(data: dict[str, Any], class_id: str | None) -> dict[str, Any]:
    return {
        "first_name": (data.get("first_name") or "").strip(),
        "last_name": (data.get("last_name") or "").strip(),
        "gender": (data.get("gender") or "").strip(),
        "date_of_birth": (data.get("date_of_birth") or "").strip(),
        "admission_number": (data.get("admission_number") or "").strip(),
        "guardian_name": (data.get("guardian_name") or "").strip(),
        "guardian_phone": (data.get("guardian_phone") or "").strip(),
        "address": (data.get("address") or "").strip(),
        "class_id": class_id,
    }


def create_student(
    session: Session,
    identity: SchoolIdentity,
    actor: Teacher,
    *,
    student_id: str,
    class_id: str | None,
    data: dict[str, Any],
) -> Student:
    sid = _require_id(student_id, "Student id")
    if session.get(Student, sid):
        raise Conflict("A student with this id already exists.")
    ensure_class_access(actor, class_id)
    if class_id:
        if session.get(SchoolClass, class_id) is None:
            raise NotFound("Class not found.")
    first = (data.get("first_name") or "").strip()
    last = (data.get("last_name") or "").strip()
    if not first or not last:
        raise BusinessRule("First and last name are required.")
    record = Student(
        id=sid,
        class_id=class_id or None,
        data_json=_student_payload(data, class_id),
        version=1,
        updated_by=actor.id,
    )
    session.add(record)
    session.flush()
    append_event(
        session,
        identity,
        operation="STUDENT_CREATE",
        actor=actor,
        payload=record.data_json,
        student_id=record.id,
        entity_type="student",
        entity_id=record.id,
    )
    return record


def get_student(session: Session, student_id: str, actor: Teacher | None = None) -> Student:
    record = session.get(Student, student_id)
    if record is None:
        raise NotFound("Student not found.")
    if actor is not None:
        ensure_class_access(actor, record.class_id, allow_unassigned=False)
    return record


def update_student(
    session: Session,
    identity: SchoolIdentity,
    actor: Teacher,
    student_id: str,
    *,
    class_id: str | None,
    data: dict[str, Any] | None,
    expected_version: int | None,
) -> Student:
    record = get_student(session, student_id, actor=actor)
    if expected_version is not None and record.version != expected_version:
        raise Conflict("This student record changed since you loaded it. Refresh and try again.")
    if class_id is not None:
        ensure_class_access(actor, class_id)
        if class_id and session.get(SchoolClass, class_id) is None:
            raise NotFound("Class not found.")
        record.class_id = class_id or None
    if data:
        merged = {**record.data_json, **data, "class_id": record.class_id}
        record.data_json = _student_payload(merged, record.class_id)
    record.version += 1
    record.updated_by = actor.id
    append_event(
        session,
        identity,
        operation="STUDENT_UPDATE",
        actor=actor,
        payload=record.data_json,
        student_id=record.id,
        entity_type="student",
        entity_id=record.id,
    )
    return record
