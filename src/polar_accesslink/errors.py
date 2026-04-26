from __future__ import annotations


class PolarAccessLinkError(Exception):
    """Base class for user-safe application errors."""

    def __init__(self, message: str, hint: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint


class ValidationError(PolarAccessLinkError):
    pass


class UpstreamAuthError(PolarAccessLinkError):
    pass


class UpstreamRateLimitError(PolarAccessLinkError):
    pass


class UpstreamValidationError(PolarAccessLinkError):
    pass


class UpstreamServerError(PolarAccessLinkError):
    pass


class NotFoundError(PolarAccessLinkError):
    pass
