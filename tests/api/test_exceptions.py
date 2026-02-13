"""Tests for the exception hierarchy."""

from __future__ import annotations

from custom_components.rtetempo.api.exceptions import (
    RTETempoAuthError,
    RTETempoClientError,
    RTETempoConnectionError,
    RTETempoError,
    RTETempoRateLimitError,
    RTETempoServerError,
)


class TestExceptionHierarchy:
    """Verify that all exceptions inherit from RTETempoError."""

    def test_base_is_exception(self):
        assert issubclass(RTETempoError, Exception)

    def test_auth_error(self):
        err = RTETempoAuthError("bad token")
        assert isinstance(err, RTETempoError)
        assert "bad token" in str(err)

    def test_connection_error(self):
        err = RTETempoConnectionError("timeout")
        assert isinstance(err, RTETempoError)
        assert "timeout" in str(err)

    def test_client_error(self):
        err = RTETempoClientError(403, "Forbidden")
        assert isinstance(err, RTETempoError)
        assert err.status_code == 403
        assert "403" in str(err)
        assert "Forbidden" in str(err)

    def test_rate_limit_error_with_retry(self):
        err = RTETempoRateLimitError(retry_after=30.0)
        assert isinstance(err, RTETempoError)
        assert err.retry_after == 30.0
        assert "30" in str(err)

    def test_rate_limit_error_without_retry(self):
        err = RTETempoRateLimitError()
        assert err.retry_after is None
        assert "429" in str(err)

    def test_server_error(self):
        err = RTETempoServerError(503, "Service Unavailable")
        assert isinstance(err, RTETempoError)
        assert err.status_code == 503
        assert "503" in str(err)

    def test_catch_all_with_base(self):
        """All typed exceptions should be catchable with RTETempoError."""
        for exc_class in (
            RTETempoAuthError,
            RTETempoConnectionError,
            RTETempoRateLimitError,
        ):
            try:
                raise exc_class("test")
            except RTETempoError:
                pass

        for exc_class_with_code in (RTETempoClientError, RTETempoServerError):
            try:
                raise exc_class_with_code(400, "test")
            except RTETempoError:
                pass
