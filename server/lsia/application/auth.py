from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from lsia.application.errors import BusinessRule, Conflict, NotFound, PermissionDenied, Unauthenticated
from lsia.application.events import append_event
from lsia.domain.permissions import Permission, Role, has_permission
from lsia.infrastructure.crypto import SchoolIdentity
from lsia.infrastructure.models import Meta, Teacher
from lsia.infrastructure.security import create_token, hash_password, verify_password

SCHOOL_NAME_KEY = "school_name"


def school_name(session: Session) -> str:
    row = session.get(Meta, SCHOOL_NAME_KEY)
    return row.value if row else "School"


def set_school_name(session: Session, name: str) -> None:
    row = session.get(Meta, SCHOOL_NAME_KEY)
    if row is None:
        session.add(Meta(key=SCHOOL_NAME_KEY, value=name))
    else:
        row.value = name


def needs_bootstrap(session: Session) -> bool:
    count = session.scalar(select(func.count()).select_from(Teacher).where(Teacher.revoked.is_(False)))
    return int(count or 0) == 0


def bootstrap(
    session: Session,
    identity: SchoolIdentity,
    *,
    name: str,
    password: str,
    school: str,
    teacher_id: str = "admin",
) -> tuple[str, Teacher]:
    if not needs_bootstrap(session):
        raise Conflict("An administrator already exists.")
    if len(password) < 8:
        raise BusinessRule("Password must be at least 8 characters.")
    role = Role(kind="administrator")
    teacher = Teacher(
        id=teacher_id,
        name=name.strip(),
        password_hash=hash_password(password),
        role_json=role.to_json(),
        revoked=False,
    )
    session.add(teacher)
    set_school_name(session, school.strip() or "School")
    session.flush()
    append_event(
        session,
        identity,
        operation="ADMIN_BOOTSTRAP",
        actor=teacher,
        payload={"school": school},
        entity_type="teacher",
        entity_id=teacher.id,
    )
    return create_token(teacher.id), teacher


def login(session: Session, username: str, password: str) -> tuple[str, Teacher]:
    teacher = session.get(Teacher, username)
    if teacher is None or not teacher.password_hash:
        raise Unauthenticated("Unknown account or password.")
    if teacher.revoked:
        raise BusinessRule("This account has been revoked.")
    if not verify_password(password, teacher.password_hash):
        raise Unauthenticated("Unknown account or password.")
    return create_token(teacher.id), teacher


def require_teacher(session: Session, teacher_id: str) -> Teacher:
    teacher = session.get(Teacher, teacher_id)
    if teacher is None:
        raise Unauthenticated()
    if teacher.revoked:
        raise BusinessRule("This account has been revoked.")
    return teacher


def require_permission(teacher: Teacher, permission: Permission) -> None:
    if not has_permission(teacher.role_json, permission):
        raise PermissionDenied()


def get_teacher(session: Session, teacher_id: str) -> Teacher:
    teacher = session.get(Teacher, teacher_id)
    if teacher is None:
        raise NotFound("Teacher not found.")
    return teacher
