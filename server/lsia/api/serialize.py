from lsia.application.academics import calculate_grade
from lsia.infrastructure.models import Attendance, Device, SchoolClass, Score, Student, Subject, Teacher


def teacher_out(row: Teacher) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "role": row.role_json,
        "revoked": row.revoked,
        "has_password": bool(row.password_hash),
        "enrolled_at": row.enrolled_at.isoformat() if row.enrolled_at else None,
    }


def class_out(row: SchoolClass) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "academic_year": row.academic_year,
        "class_teacher_id": row.class_teacher_id,
    }


def subject_out(row: Subject) -> dict:
    return {"id": row.id, "name": row.name, "code": row.code}


def device_out(row: Device) -> dict:
    return {
        "id": row.id,
        "teacher_id": row.teacher_id,
        "device_name": row.device_name,
        "public_key": row.public_key,
        "enrolled_at": row.enrolled_at.isoformat() if row.enrolled_at else None,
        "last_sync_at": row.last_sync_at.isoformat() if row.last_sync_at else None,
        "status": row.status,
    }


def student_out(row: Student) -> dict:
    return {
        "id": row.id,
        "class_id": row.class_id,
        "data": row.data_json,
        "version": row.version,
        "updated_by": row.updated_by,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def score_out(row: Score) -> dict:
    grade_info = calculate_grade(row.total_score)
    return {
        "id": row.id,
        "student_id": row.student_id,
        "subject_id": row.subject_id,
        "term": row.term,
        "ca_score": row.ca_score,
        "exam_score": row.exam_score,
        "total_score": row.total_score,
        "grade": grade_info["grade"],
        "remark": grade_info["remark"],
        "recorded_by": row.recorded_by,
    }


def attendance_out(row: Attendance) -> dict:
    return {
        "id": row.id,
        "student_id": row.student_id,
        "class_id": row.class_id,
        "date": row.date.isoformat(),
        "status": row.status,
        "recorded_by": row.recorded_by,
    }
