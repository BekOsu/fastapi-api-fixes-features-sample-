"""Custom exception classes for the application."""

from typing import Any


class AppException(Exception):
    """Base exception for application errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(AppException):
    """Raised when a requested resource is not found."""

    def __init__(self, resource: str, identifier: Any = None):
        message = f"{resource} not found"
        if identifier:
            message = f"{resource} with id '{identifier}' not found"
        super().__init__(
            message=message,
            status_code=404,
            error_code="NOT_FOUND",
            details={"resource": resource, "identifier": identifier},
        )


class BadRequestError(AppException):
    """Raised when the request is invalid."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            status_code=400,
            error_code="BAD_REQUEST",
            details=details,
        )


class UnauthorizedError(AppException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            status_code=401,
            error_code="UNAUTHORIZED",
        )


class ForbiddenError(AppException):
    """Raised when the user lacks permission."""

    def __init__(self, message: str = "Permission denied"):
        super().__init__(
            message=message,
            status_code=403,
            error_code="FORBIDDEN",
        )


class ConflictError(AppException):
    """Raised when there's a conflict (e.g., duplicate resource)."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            status_code=409,
            error_code="CONFLICT",
            details=details,
        )


class ValidationError(AppException):
    """Raised when validation fails."""

    def __init__(self, message: str, errors: list[dict[str, Any]] | None = None):
        super().__init__(
            message=message,
            status_code=422,
            error_code="VALIDATION_ERROR",
            details={"errors": errors or []},
        )


class InvalidTransitionError(AppException):
    """Raised when a state transition is not allowed."""

    def __init__(self, current_state: str, target_state: str):
        message = f"Cannot transition from '{current_state}' to '{target_state}'"
        super().__init__(
            message=message,
            status_code=400,
            error_code="INVALID_TRANSITION",
            details={"current_state": current_state, "target_state": target_state},
        )
