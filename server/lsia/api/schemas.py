from typing import Any

from pydantic import BaseModel, Field


class TeacherOut(BaseModel):
    id: str
    name: str
    role: dict[str, Any]
    revoked: bool
    has_password: bool
    enrolled_at: str | None = None


class LoginIn(BaseModel):
    username: str
    password: str


class BootstrapIn(BaseModel):
    name: str
    password: str
    school_name: str = "School"
    teacher_id: str = "admin"


class TeacherIn(BaseModel):
    id: str
    name: str
    password: str | None = None
    role: dict[str, Any] = Field(default_factory=lambda: {"role": "teacher"})


class TeacherPatch(BaseModel):
    name: str | None = None
    role: dict[str, Any] | None = None


class PasswordIn(BaseModel):
    password: str


class ClassIn(BaseModel):
    id: str
    name: str
    academic_year: str
    class_teacher_id: str | None = None


class ClassPatch(BaseModel):
    name: str | None = None
    academic_year: str | None = None
    class_teacher_id: str | None = None


class SubjectIn(BaseModel):
    id: str
    name: str
    code: str


class SubjectPatch(BaseModel):
    name: str | None = None
    code: str | None = None


class StudentIn(BaseModel):
    id: str
    class_id: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class StudentPatch(BaseModel):
    class_id: str | None = None
    data: dict[str, Any] | None = None
    expected_version: int | None = None


class EnrollmentTicketIn(BaseModel):
    base_url: str | None = None


class EnrollIn(BaseModel):
    ticket: str
    teacher_id: str
    password: str
    device_id: str
    device_name: str = "Teacher phone"
    public_key: str


class HandshakeIn(BaseModel):
    device_id: str
    timestamp: int
    challenge_response: str


class SyncOperationIn(BaseModel):
    id: str
    student_id: str | None = None
    type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    teacher_id: str
    device_id: str
    timestamp: int
    lamport_clock: int
    signature: str


class PushIn(BaseModel):
    device_id: str
    operations: list[SyncOperationIn]


class PullIn(BaseModel):
    device_id: str
    since_clock: int = 0
    limit: int = 20


class AttendanceItemIn(BaseModel):
    student_id: str
    status: str


class AttendanceIn(BaseModel):
    class_id: str
    date: str
    records: list[AttendanceItemIn]


class ScoreItemIn(BaseModel):
    student_id: str
    subject_id: str
    term: str
    ca_score: float | None = None
    exam_score: float | None = None


class ScoresIn(BaseModel):
    scores: list[ScoreItemIn]


class ApprovalDecisionIn(BaseModel):
    reason: str = ""


class ConflictResolveIn(BaseModel):
    choice: str  # keep_current, use_incoming, custom
    custom_payload: dict[str, Any] | None = None


class RestoreIn(BaseModel):
    filename: str

