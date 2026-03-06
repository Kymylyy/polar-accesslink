from __future__ import annotations


class PolarMcpError(Exception):
    """Base class for user-safe MCP errors."""

    def __init__(self, message: str, hint: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint


class ValidationError(PolarMcpError):
    pass


class UpstreamAuthError(PolarMcpError):
    pass


class UpstreamRateLimitError(PolarMcpError):
    pass


class UpstreamValidationError(PolarMcpError):
    pass


class UpstreamServerError(PolarMcpError):
    pass


class NotFoundError(PolarMcpError):
    pass
