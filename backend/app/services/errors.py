"""Safe, user-facing service errors (mapped to HTTP responses in the API layer)."""

from __future__ import annotations


class ServiceError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(ServiceError):
    status_code = 404
    code = "not_found"


class ForbiddenError(ServiceError):
    status_code = 403
    code = "forbidden"


class ConflictError(ServiceError):
    status_code = 409
    code = "conflict"


class ValidationFailed(ServiceError):
    status_code = 422
    code = "validation_failed"


class UpstreamUnavailable(ServiceError):
    status_code = 503
    code = "upstream_unavailable"
