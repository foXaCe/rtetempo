"""Exception hierarchy for the RTE Tempo API client."""

from __future__ import annotations


class RTETempoError(Exception):
    """Base exception for all RTE Tempo API errors."""


class RTETempoAuthError(RTETempoError):
    """OAuth2 authentication error (invalid/expired token)."""


class RTETempoConnectionError(RTETempoError):
    """Network-level error (timeout, DNS, connection refused)."""


class RTETempoClientError(RTETempoError):
    """HTTP 4xx error (except 429)."""

    def __init__(self, status_code: int, message: str) -> None:
        """Initialize with HTTP status code."""
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}: {message}")


class RTETempoRateLimitError(RTETempoError):
    """HTTP 429 Too Many Requests."""

    def __init__(self, retry_after: float | None = None) -> None:
        """Initialize with optional Retry-After value in seconds."""
        self.retry_after = retry_after
        msg = "Rate limited (HTTP 429)"
        if retry_after is not None:
            msg += f", retry after {retry_after}s"
        super().__init__(msg)


class RTETempoServerError(RTETempoError):
    """HTTP 5xx server error."""

    def __init__(self, status_code: int, message: str) -> None:
        """Initialize with HTTP status code."""
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}: {message}")
