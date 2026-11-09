class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400, details: dict | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class Unauthenticated(AppError):
    def __init__(self, message: str = "Sign in required.") -> None:
        super().__init__("UNAUTHENTICATED", message, 401)


class PermissionDenied(AppError):
    def __init__(self, message: str = "You do not have permission for this action.") -> None:
        super().__init__("PERMISSION_DENIED", message, 403)


class NotFound(AppError):
    def __init__(self, message: str = "Record not found.") -> None:
        super().__init__("NOT_FOUND", message, 404)


class Conflict(AppError):
    def __init__(self, message: str) -> None:
        super().__init__("CONFLICT", message, 409)


class BusinessRule(AppError):
    def __init__(self, message: str) -> None:
        super().__init__("BUSINESS_RULE", message, 422)
