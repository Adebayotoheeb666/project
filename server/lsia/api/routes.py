from datetime import date, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from lsia.api.deps import current_teacher, school_identity
from lsia.api.schemas import (
    ApprovalDecisionIn,
    AttendanceIn,
    BootstrapIn,
    ClassIn,
    ClassPatch,
    ConflictResolveIn,
    EnrollIn,
    EnrollmentTicketIn,
    HandshakeIn,
    LoginIn,
    PasswordIn,
    PullIn,
    PushIn,
    RestoreIn,
    ScoresIn,
    StudentIn,
    StudentPatch,
    SubjectIn,
    SubjectPatch,
    TeacherIn,
    TeacherPatch,
)
from lsia.api.serialize import attendance_out, class_out, device_out, score_out, student_out, subject_out, teacher_out
from lsia.application import academics, approvals, auth, conflicts, devices, directory, maintenance, reports, sync
from lsia.application.auth import require_permission
from lsia.domain.permissions import Permission
from lsia.infrastructure.crypto import SchoolIdentity
from lsia.infrastructure.db import get_session
from lsia.infrastructure.models import Approval, AuditLog, Event, Student, Teacher

router = APIRouter(prefix="/api/v1")
SessionDep = Annotated[Session, Depends(get_session)]
ActorDep = Annotated[Teacher, Depends(current_teacher)]
IdentityDep = Annotated[SchoolIdentity, Depends(school_identity)]


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/auth/bootstrap-status")
def bootstrap_status(session: SessionDep) -> dict[str, bool]:
    return {"needs_bootstrap": auth.needs_bootstrap(session)}


@router.post("/auth/bootstrap")
def bootstrap(body: BootstrapIn, session: SessionDep, identity: IdentityDep) -> dict[str, Any]:
    token, teacher = auth.bootstrap(
        session,
        identity,
        name=body.name,
        password=body.password,
        school=body.school_name,
        teacher_id=body.teacher_id,
    )
    return {"token": token, "teacher": teacher_out(teacher)}


@router.post("/auth/login")
def login(body: LoginIn, session: SessionDep) -> dict[str, Any]:
    token, teacher = auth.login(session, body.username, body.password)
    return {"token": token, "teacher": teacher_out(teacher)}


@router.get("/auth/me")
def me(actor: ActorDep) -> dict[str, Any]:
    return teacher_out(actor)


@router.get("/school")
def school(session: SessionDep, identity: IdentityDep, actor: ActorDep) -> dict[str, str]:
    return {
        "id": identity.school_id,
        "name": auth.school_name(session),
        "public_key": identity.public_key_b64,
    }


@router.get("/overview")
def overview(session: SessionDep, actor: ActorDep) -> dict[str, Any]:
    require_permission(actor, Permission.VIEW_STUDENTS)
    students = int(session.scalar(select(func.count()).select_from(Student)) or 0)
    teachers = int(session.scalar(select(func.count()).select_from(Teacher)) or 0)
    events = int(session.scalar(select(func.count()).select_from(Event)) or 0)
    pending_approvals = int(
        session.scalar(
            select(func.count()).select_from(Approval).where(Approval.status == "PENDING_APPROVAL")
        )
        or 0
    )
    pending_conflicts = int(
        session.scalar(
            select(func.count()).select_from(Event).where(Event.status == "CONFLICT")
        )
        or 0
    )
    recent = session.scalars(select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(12)).all()
    return {
        "students": students,
        "teachers": teachers,
        "events": events,
        "pending_approvals": pending_approvals,
        "pending_conflicts": pending_conflicts,
        "recent": [
            {
                "id": row.id,
                "user_id": row.user_id,
                "operation": row.operation,
                "entity_type": row.entity_type,
                "entity_id": row.entity_id,
                "timestamp": row.timestamp.isoformat() if row.timestamp else None,
            }
            for row in recent
        ],
    }


# --- Teachers Directory ---


@router.get("/teachers")
def teachers(session: SessionDep, actor: ActorDep) -> list[dict[str, Any]]:
    require_permission(actor, Permission.MANAGE_TEACHERS)
    return [teacher_out(row) for row in directory.list_teachers(session)]


@router.post("/teachers", status_code=201)
def create_teacher(body: TeacherIn, session: SessionDep, actor: ActorDep, identity: IdentityDep) -> dict[str, Any]:
    require_permission(actor, Permission.MANAGE_TEACHERS)
    row = directory.create_teacher(
        session,
        identity,
        actor,
        teacher_id=body.id,
        name=body.name,
        password=body.password,
        role=body.role,
    )
    return teacher_out(row)


@router.patch("/teachers/{teacher_id}")
def patch_teacher(
    teacher_id: str, body: TeacherPatch, session: SessionDep, actor: ActorDep, identity: IdentityDep
) -> dict[str, Any]:
    require_permission(actor, Permission.MANAGE_TEACHERS)
    row = directory.update_teacher(session, identity, actor, teacher_id, name=body.name, role=body.role)
    return teacher_out(row)


@router.post("/teachers/{teacher_id}/password")
def teacher_password(
    teacher_id: str, body: PasswordIn, session: SessionDep, actor: ActorDep, identity: IdentityDep
) -> dict[str, str]:
    require_permission(actor, Permission.MANAGE_TEACHERS)
    directory.set_teacher_password(session, identity, actor, teacher_id, body.password)
    return {"status": "ok"}


@router.post("/teachers/{teacher_id}/revoke")
def teacher_revoke(teacher_id: str, session: SessionDep, actor: ActorDep, identity: IdentityDep) -> dict[str, Any]:
    require_permission(actor, Permission.MANAGE_TEACHERS)
    row = directory.revoke_teacher(session, identity, actor, teacher_id)
    return teacher_out(row)


# --- Classes & Subjects ---


@router.get("/classes")
def classes(session: SessionDep, actor: ActorDep) -> list[dict[str, Any]]:
    require_permission(actor, Permission.VIEW_STUDENTS)
    return [class_out(row) for row in directory.list_classes(session, actor=actor)]


@router.post("/classes", status_code=201)
def create_class(body: ClassIn, session: SessionDep, actor: ActorDep, identity: IdentityDep) -> dict[str, Any]:
    require_permission(actor, Permission.MANAGE_CLASSES)
    row = directory.create_class(
        session,
        identity,
        actor,
        class_id=body.id,
        name=body.name,
        academic_year=body.academic_year,
        class_teacher_id=body.class_teacher_id,
    )
    return class_out(row)


@router.patch("/classes/{class_id}")
def patch_class(
    class_id: str, body: ClassPatch, session: SessionDep, actor: ActorDep, identity: IdentityDep
) -> dict[str, Any]:
    require_permission(actor, Permission.MANAGE_CLASSES)
    row = directory.update_class(
        session,
        identity,
        actor,
        class_id,
        name=body.name,
        academic_year=body.academic_year,
        class_teacher_id=body.class_teacher_id,
    )
    return class_out(row)


@router.delete("/classes/{class_id}", status_code=204)
def remove_class(class_id: str, session: SessionDep, actor: ActorDep, identity: IdentityDep) -> None:
    require_permission(actor, Permission.MANAGE_CLASSES)
    directory.delete_class(session, identity, actor, class_id)


@router.get("/subjects")
def subjects(session: SessionDep, actor: ActorDep) -> list[dict[str, Any]]:
    require_permission(actor, Permission.VIEW_STUDENTS)
    return [subject_out(row) for row in directory.list_subjects(session)]


@router.post("/subjects", status_code=201)
def create_subject(body: SubjectIn, session: SessionDep, actor: ActorDep, identity: IdentityDep) -> dict[str, Any]:
    require_permission(actor, Permission.MANAGE_CLASSES)
    row = directory.create_subject(session, identity, actor, subject_id=body.id, name=body.name, code=body.code)
    return subject_out(row)


@router.patch("/subjects/{subject_id}")
def patch_subject(
    subject_id: str, body: SubjectPatch, session: SessionDep, actor: ActorDep, identity: IdentityDep
) -> dict[str, Any]:
    require_permission(actor, Permission.MANAGE_CLASSES)
    row = directory.update_subject(session, identity, actor, subject_id, name=body.name, code=body.code)
    return subject_out(row)


@router.delete("/subjects/{subject_id}", status_code=204)
def remove_subject(subject_id: str, session: SessionDep, actor: ActorDep, identity: IdentityDep) -> None:
    require_permission(actor, Permission.MANAGE_CLASSES)
    directory.delete_subject(session, identity, actor, subject_id)


# --- Students ---


@router.get("/students")
def students(
    session: SessionDep,
    actor: ActorDep,
    q: str | None = None,
    class_id: str | None = Query(default=None),
) -> list[dict[str, Any]]:
    require_permission(actor, Permission.VIEW_STUDENTS)
    return [student_out(row) for row in directory.list_students(session, q=q, class_id=class_id, actor=actor)]


@router.post("/students", status_code=201)
def create_student(body: StudentIn, session: SessionDep, actor: ActorDep, identity: IdentityDep) -> dict[str, Any]:
    require_permission(actor, Permission.EDIT_STUDENTS)
    row = directory.create_student(
        session, identity, actor, student_id=body.id, class_id=body.class_id, data=body.data
    )
    return student_out(row)


@router.get("/students/{student_id:path}")
def student(student_id: str, session: SessionDep, actor: ActorDep) -> dict[str, Any]:
    require_permission(actor, Permission.VIEW_STUDENTS)
    return student_out(directory.get_student(session, student_id, actor=actor))


@router.patch("/students/{student_id:path}")
def patch_student(
    student_id: str, body: StudentPatch, session: SessionDep, actor: ActorDep, identity: IdentityDep
) -> dict[str, Any]:
    require_permission(actor, Permission.EDIT_STUDENTS)
    row = directory.update_student(
        session,
        identity,
        actor,
        student_id,
        class_id=body.class_id,
        data=body.data,
        expected_version=body.expected_version,
    )
    return student_out(row)


# --- Devices & Enrollment ---


@router.get("/me/directory")
def my_directory(session: SessionDep, actor: ActorDep) -> dict[str, Any]:
    require_permission(actor, Permission.VIEW_STUDENTS)
    return devices.directory_snapshot(session, actor)


@router.post("/devices/enrollment-tickets", status_code=201)
def create_enrollment_ticket(
    body: EnrollmentTicketIn, session: SessionDep, actor: ActorDep, identity: IdentityDep
) -> dict[str, Any]:
    require_permission(actor, Permission.MANAGE_TEACHERS)
    return devices.create_ticket(session, identity, actor, base_url=body.base_url)


@router.get("/devices/enrollment-tickets/{ticket_id}")
def read_enrollment_ticket(ticket_id: str, session: SessionDep, identity: IdentityDep) -> dict[str, Any]:
    return devices.inspect_ticket(session, identity, ticket_id)


@router.get("/devices/enrollment-tickets/{ticket_id}/qr.png")
def enrollment_qr(ticket_id: str, session: SessionDep, identity: IdentityDep) -> Response:
    payload = devices.inspect_ticket(session, identity, ticket_id)
    return Response(content=devices.qr_payload_bytes(payload), media_type="image/png")


@router.post("/devices/enroll")
def enroll_device(body: EnrollIn, session: SessionDep, identity: IdentityDep) -> dict[str, Any]:
    result = devices.enroll_device(
        session,
        identity,
        ticket_id=body.ticket,
        teacher_id=body.teacher_id,
        password=body.password,
        device_id=body.device_id,
        device_name=body.device_name,
        public_key=body.public_key,
    )
    return {
        "token": result["token"],
        "teacher": teacher_out(result["teacher"]),
        "device": device_out(result["device"]),
        "school": result["school"],
        "directory": result["directory"],
    }


@router.get("/devices")
def devices_list(session: SessionDep, actor: ActorDep) -> list[dict[str, Any]]:
    require_permission(actor, Permission.MANAGE_TEACHERS)
    return [device_out(row) for row in devices.list_devices(session)]


@router.post("/devices/{device_id}/revoke")
def device_revoke(device_id: str, session: SessionDep, actor: ActorDep, identity: IdentityDep) -> dict[str, Any]:
    require_permission(actor, Permission.MANAGE_TEACHERS)
    return device_out(devices.revoke_device(session, identity, actor, device_id))


# --- Phase 3: Synchronization ---


@router.post("/sync/handshake")
def sync_handshake(body: HandshakeIn, session: SessionDep, identity: IdentityDep) -> dict[str, Any]:
    return sync.handshake(
        session,
        identity,
        device_id=body.device_id,
        timestamp=body.timestamp,
        challenge_response=body.challenge_response,
    )


@router.post("/sync/push")
async def sync_push(
    request: Request, body: PushIn, session: SessionDep, identity: IdentityDep
) -> dict[str, Any]:
    raw_body = await request.body()
    return sync.push_operations(
        session,
        identity,
        device_id=body.device_id,
        operations=[op.model_dump() for op in body.operations],
        raw_size_bytes=len(raw_body),
    )


@router.post("/sync/pull")
def sync_pull(body: PullIn, session: SessionDep) -> dict[str, Any]:
    return sync.pull_operations(
        session,
        device_id=body.device_id,
        since_clock=body.since_clock,
        limit=body.limit,
    )


# --- Phase 4: Academic Management (Attendance & Scores) ---


@router.post("/attendance")
def record_attendance(
    body: AttendanceIn, session: SessionDep, actor: ActorDep, identity: IdentityDep
) -> list[dict[str, Any]]:
    dt = datetime.strptime(body.date, "%Y-%m-%d").date()
    recs = academics.record_attendance(
        session,
        identity,
        actor,
        class_id=body.class_id,
        attendance_date=dt,
        records=[r.model_dump() for r in body.records],
    )
    return [attendance_out(r) for r in recs]


@router.get("/attendance")
def get_attendance(
    session: SessionDep,
    actor: ActorDep,
    class_id: str | None = None,
    student_id: str | None = None,
    date_val: str | None = Query(default=None, alias="date"),
    from_date: str | None = None,
    to_date: str | None = None,
) -> list[dict[str, Any]]:
    dt = datetime.strptime(date_val, "%Y-%m-%d").date() if date_val else None
    f_dt = datetime.strptime(from_date, "%Y-%m-%d").date() if from_date else None
    t_dt = datetime.strptime(to_date, "%Y-%m-%d").date() if to_date else None

    recs = academics.list_attendance(
        session,
        actor,
        class_id=class_id,
        student_id=student_id,
        attendance_date=dt,
        from_date=f_dt,
        to_date=t_dt,
    )
    return [attendance_out(r) for r in recs]


@router.get("/attendance/summary")
def get_attendance_summary(
    session: SessionDep,
    actor: ActorDep,
    class_id: str | None = None,
    student_id: str | None = None,
) -> dict[str, Any]:
    return academics.attendance_summary(session, actor, class_id=class_id, student_id=student_id)


@router.post("/scores")
def record_scores(
    body: ScoresIn, session: SessionDep, actor: ActorDep, identity: IdentityDep
) -> list[dict[str, Any]]:
    scores = academics.record_scores(
        session,
        identity,
        actor,
        scores=[s.model_dump() for s in body.scores],
    )
    return [score_out(s) for s in scores]


@router.get("/scores")
def get_scores(
    session: SessionDep,
    actor: ActorDep,
    class_id: str | None = None,
    subject_id: str | None = None,
    term: str | None = None,
    student_id: str | None = None,
) -> list[dict[str, Any]]:
    scores = academics.list_scores(
        session,
        actor,
        class_id=class_id,
        subject_id=subject_id,
        term=term,
        student_id=student_id,
    )
    return [score_out(s) for s in scores]


# --- Phase 5: Reports, Broadsheet, Approvals, Conflicts ---


@router.get("/reports/broadsheet")
def get_broadsheet(
    class_id: str,
    term: str,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    require_permission(actor, Permission.VIEW_STUDENTS)
    return reports.generate_broadsheet(session, class_id=class_id, term=term)


@router.get("/reports/student")
def get_student_report(
    student_id: str,
    term: str,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    require_permission(actor, Permission.VIEW_STUDENTS)
    return reports.generate_student_report(session, student_id=student_id, term=term)


@router.get("/approvals")
def get_approvals(
    session: SessionDep,
    actor: ActorDep,
    status: str | None = None,
) -> list[dict[str, Any]]:
    require_permission(actor, Permission.MANAGE_TEACHERS)
    return approvals.list_approvals(session, status=status)


@router.post("/approvals/{approval_id}/approve")
def approve_item(
    approval_id: str,
    session: SessionDep,
    actor: ActorDep,
    identity: IdentityDep,
) -> dict[str, Any]:
    return approvals.approve_request(session, identity, actor, approval_id)


@router.post("/approvals/{approval_id}/reject")
def reject_item(
    approval_id: str,
    body: ApprovalDecisionIn,
    session: SessionDep,
    actor: ActorDep,
    identity: IdentityDep,
) -> dict[str, Any]:
    return approvals.reject_request(session, identity, actor, approval_id, reason=body.reason)


@router.get("/conflicts")
def get_conflicts(
    session: SessionDep,
    actor: ActorDep,
) -> list[dict[str, Any]]:
    require_permission(actor, Permission.MANAGE_TEACHERS)
    return conflicts.list_conflicts(session)


@router.post("/conflicts/{event_id}/resolve")
def resolve_conflict_item(
    event_id: str,
    body: ConflictResolveIn,
    session: SessionDep,
    actor: ActorDep,
    identity: IdentityDep,
) -> dict[str, Any]:
    return conflicts.resolve_conflict(
        session,
        identity,
        actor,
        event_id,
        choice=body.choice,
        custom_payload=body.custom_payload,
    )


# --- Audit Logs ---


@router.get("/audit")
def audit(session: SessionDep, actor: ActorDep, limit: int = 50) -> list[dict[str, Any]]:
    require_permission(actor, Permission.VIEW_AUDIT)
    rows = session.scalars(select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(min(limit, 200))).all()
    return [
        {
            "id": row.id,
            "user_id": row.user_id,
            "operation": row.operation,
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "timestamp": row.timestamp.isoformat() if row.timestamp else None,
            "details": row.details,
        }
        for row in rows
    ]


# --- System Maintenance & Backups ---


@router.post("/system/backup")
def trigger_backup(
    session: SessionDep,
    actor: ActorDep,
    identity: IdentityDep,
) -> dict[str, Any]:
    return maintenance.create_backup(session, identity, actor)


@router.get("/system/backups")
def get_backups(
    actor: ActorDep,
) -> list[dict[str, Any]]:
    return maintenance.list_backups(actor)


@router.get("/system/backups/{filename}/download")
def download_backup(
    filename: str,
    actor: ActorDep,
) -> FileResponse:
    require_permission(actor, Permission.MANAGE_TEACHERS)
    file_path = maintenance.get_backup_dir() / filename
    if not file_path.exists():
        from lsia.application.errors import NotFound
        raise NotFound("Backup file not found.")
    return FileResponse(path=file_path, filename=filename, media_type="application/gzip")


@router.post("/system/restore")
def trigger_restore(
    body: RestoreIn,
    session: SessionDep,
    actor: ActorDep,
    identity: IdentityDep,
) -> dict[str, Any]:
    return maintenance.restore_backup(session, identity, actor, body.filename)

