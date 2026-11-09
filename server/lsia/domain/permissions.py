from enum import StrEnum
from typing import Any


class Permission(StrEnum):
    VIEW_STUDENTS = "view_students"
    EDIT_STUDENTS = "edit_students"
    MANAGE_TEACHERS = "manage_teachers"
    MANAGE_CLASSES = "manage_classes"
    ENTER_CA = "enter_ca"
    ENTER_EXAM = "enter_exam"
    FINALIZE_RESULTS = "finalize_results"
    VIEW_AUDIT = "view_audit"


ADMIN_PERMISSIONS = {p: True for p in Permission}

TEACHER_DEFAULTS = {
    Permission.VIEW_STUDENTS: True,
    Permission.EDIT_STUDENTS: True,
    Permission.MANAGE_TEACHERS: False,
    Permission.MANAGE_CLASSES: False,
    Permission.ENTER_CA: True,
    Permission.ENTER_EXAM: True,
    Permission.FINALIZE_RESULTS: False,
    Permission.VIEW_AUDIT: False,
}


class Role:
    def __init__(
        self,
        kind: str,
        classes: list[str] | None = None,
        subjects: list[str] | None = None,
        permissions: dict[str, bool] | None = None,
    ) -> None:
        self.kind = kind
        self.classes = classes or []
        self.subjects = subjects or []
        defaults = ADMIN_PERMISSIONS if kind == "administrator" else TEACHER_DEFAULTS
        merged = {str(k): bool(v) for k, v in defaults.items()}
        if permissions:
            merged.update({str(k): bool(v) for k, v in permissions.items()})
        self.permissions = merged

    def allows(self, permission: Permission) -> bool:
        if self.kind == "administrator":
            return True
        return bool(self.permissions.get(str(permission), False))

    def to_json(self) -> dict[str, Any]:
        return {
            "role": self.kind,
            "classes": self.classes,
            "subjects": self.subjects,
            "permissions": self.permissions,
        }


def parse_role(raw: dict[str, Any] | None) -> Role:
    data = raw or {}
    return Role(
        kind=data.get("role", "teacher"),
        classes=list(data.get("classes") or []),
        subjects=list(data.get("subjects") or []),
        permissions=data.get("permissions"),
    )


def has_permission(role_json: dict[str, Any] | None, permission: Permission) -> bool:
    return parse_role(role_json).allows(permission)
