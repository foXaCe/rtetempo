"""Tests for the async RTE Tempo API client."""

from __future__ import annotations

import datetime
import time
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from custom_components.rtetempo.api.client import (
    RTETempoClient,
    _CircuitState,
    _parse_response,
    adjust_tempo_time,
    parse_rte_api_date,
    parse_rte_api_datetime,
)
from custom_components.rtetempo.api.exceptions import (
    RTETempoAuthError,
    RTETempoClientError,
    RTETempoConnectionError,
    RTETempoRateLimitError,
    RTETempoServerError,
)
from custom_components.rtetempo.api.models import TempoData
from custom_components.rtetempo.const import FRANCE_TZ, HOUR_OF_CHANGE

# ── Parsing helpers ──────────────────────────────────────────────────


class TestParseRteApiDatetime:
    """Tests for parse_rte_api_datetime."""

    def test_standard(self):
        result = parse_rte_api_datetime("2024-01-15T00:00:00+01:00")
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_with_time(self):
        result = parse_rte_api_datetime("2024-06-20T14:30:00+02:00")
        assert result.hour == 14
        assert result.minute == 30

    def test_timezone_preserved(self):
        result = parse_rte_api_datetime("2024-01-15T00:00:00+01:00")
        assert result.tzinfo is not None

    def test_negative_offset(self):
        result = parse_rte_api_datetime("2024-01-15T00:00:00-05:00")
        assert result.tzinfo is not None


class TestParseRteApiDate:
    """Tests for parse_rte_api_date."""

    def test_returns_date(self):
        result = parse_rte_api_date("2024-01-15T00:00:00+01:00")
        assert isinstance(result, datetime.date)
        assert not isinstance(result, datetime.datetime)

    def test_correct_date(self):
        result = parse_rte_api_date("2024-03-20T00:00:00+01:00")
        assert result == datetime.date(2024, 3, 20)


class TestAdjustTempoTime:
    """Tests for adjust_tempo_time."""

    def test_adds_6_hours(self):
        dt = datetime.datetime(2024, 1, 15, 0, 0, tzinfo=FRANCE_TZ)
        result = adjust_tempo_time(dt)
        assert result.hour == HOUR_OF_CHANGE

    def test_midnight_becomes_6am(self):
        dt = datetime.datetime(2024, 1, 15, 0, 0, tzinfo=FRANCE_TZ)
        result = adjust_tempo_time(dt)
        assert result == datetime.datetime(2024, 1, 15, 6, 0, tzinfo=FRANCE_TZ)


# ── _parse_response ──────────────────────────────────────────────────


class TestParseResponse:
    """Tests for _parse_response."""

    def _make_payload(self, values):
        return {"tempo_like_calendars": {"values": values}}

    def test_single_day(self):
        payload = self._make_payload([
            {
                "start_date": "2024-01-15T00:00:00+01:00",
                "end_date": "2024-01-16T00:00:00+01:00",
                "value": "BLUE",
                "updated_date": "2024-01-15T10:00:00+01:00",
            }
        ])
        data = _parse_response(payload)
        assert isinstance(data, TempoData)
        assert len(data.adjusted_days) == 1
        assert len(data.regular_days) == 1
        assert data.adjusted_days[0].value == "BLUE"
        assert data.adjusted_days[0].start.hour == 6  # type: ignore[union-attr]
        assert data.data_end is not None

    def test_multiple_days(self):
        values = [
            {
                "start_date": f"2024-01-{15 + i:02d}T00:00:00+01:00",
                "end_date": f"2024-01-{16 + i:02d}T00:00:00+01:00",
                "value": "BLUE",
                "updated_date": f"2024-01-{15 + i:02d}T10:00:00+01:00",
            }
            for i in range(5)
        ]
        data = _parse_response(self._make_payload(values))
        assert len(data.adjusted_days) == 5
        assert len(data.regular_days) == 5

    def test_missing_key_skipped(self):
        payload = self._make_payload([
            {
                "start_date": "2024-01-15T00:00:00+01:00",
                "end_date": "2024-01-16T00:00:00+01:00",
                "updated_date": "2024-01-15T10:00:00+01:00",
                # Missing "value"
            }
        ])
        data = _parse_response(payload)
        assert len(data.adjusted_days) == 0
        assert len(data.regular_days) == 0

    def test_empty_values(self):
        data = _parse_response(self._make_payload([]))
        assert data.data_end is None
        assert data.adjusted_days == []
        assert data.regular_days == []

    def test_data_end_is_latest(self):
        values = [
            {
                "start_date": "2024-01-15T00:00:00+01:00",
                "end_date": "2024-01-16T00:00:00+01:00",
                "value": "BLUE",
                "updated_date": "2024-01-15T10:00:00+01:00",
            },
            {
                "start_date": "2024-01-17T00:00:00+01:00",
                "end_date": "2024-01-18T00:00:00+01:00",
                "value": "RED",
                "updated_date": "2024-01-17T10:00:00+01:00",
            },
        ]
        data = _parse_response(self._make_payload(values))
        assert data.data_end is not None
        assert data.data_end.day == 18


# ── RTETempoClient ───────────────────────────────────────────────────


@pytest.fixture
def mock_auth():
    auth = AsyncMock()
    auth.async_get_access_token = AsyncMock(return_value="test_token")
    return auth


@pytest.fixture
def mock_session():
    return MagicMock(spec=aiohttp.ClientSession)


def _make_get_response(status=200, json_data=None, headers=None):
    """Create a mock context manager for session.get."""
    resp = AsyncMock()
    resp.status = status
    resp.reason = "OK" if status == 200 else "Error"
    resp.json = AsyncMock(return_value=json_data or {})
    resp.text = AsyncMock(return_value="error")
    resp.headers = headers or {}
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


class TestAsyncTestCredentials:
    """Tests for async_test_credentials."""

    @pytest.mark.asyncio
    async def test_success(self, mock_session, mock_auth):
        client = RTETempoClient(mock_session, mock_auth)
        mock_session.get.return_value = _make_get_response(200)
        await client.async_test_credentials()
        mock_auth.async_get_access_token.assert_called_once()

    @pytest.mark.asyncio
    async def test_auth_error(self, mock_session, mock_auth):
        client = RTETempoClient(mock_session, mock_auth)
        mock_session.get.return_value = _make_get_response(401)
        with pytest.raises(RTETempoAuthError):
            await client.async_test_credentials()

    @pytest.mark.asyncio
    async def test_connection_error(self, mock_session, mock_auth):
        client = RTETempoClient(mock_session, mock_auth)
        mock_session.get.side_effect = aiohttp.ClientError("offline")
        with pytest.raises(RTETempoConnectionError):
            await client.async_test_credentials()

    @pytest.mark.asyncio
    async def test_timeout_error(self, mock_session, mock_auth):
        client = RTETempoClient(mock_session, mock_auth)
        mock_session.get.side_effect = TimeoutError("timeout")
        with pytest.raises(RTETempoConnectionError):
            await client.async_test_credentials()


class TestAsyncGetTempoData:
    """Tests for async_get_tempo_data."""

    def _make_valid_payload(self):
        return {
            "tempo_like_calendars": {
                "values": [
                    {
                        "start_date": "2024-01-15T00:00:00+01:00",
                        "end_date": "2024-01-16T00:00:00+01:00",
                        "value": "BLUE",
                        "updated_date": "2024-01-15T10:00:00+01:00",
                    }
                ]
            }
        }

    @pytest.mark.asyncio
    async def test_success(self, mock_session, mock_auth):
        client = RTETempoClient(mock_session, mock_auth)
        mock_session.get.return_value = _make_get_response(
            200, self._make_valid_payload()
        )
        start = datetime.datetime(2024, 1, 14, 0, 0, tzinfo=FRANCE_TZ)
        end = datetime.datetime(2024, 1, 17, 0, 0, tzinfo=FRANCE_TZ)
        data = await client.async_get_tempo_data(start, end)
        assert isinstance(data, TempoData)
        assert len(data.adjusted_days) == 1

    @pytest.mark.asyncio
    async def test_retry_on_server_error(self, mock_session, mock_auth):
        """Server error retries 3 times with backoff."""
        client = RTETempoClient(mock_session, mock_auth)
        # First two calls fail with 500, third succeeds
        mock_session.get.side_effect = [
            _make_get_response(500),
            _make_get_response(500),
            _make_get_response(200, self._make_valid_payload()),
        ]
        start = datetime.datetime(2024, 1, 14, 0, 0, tzinfo=FRANCE_TZ)
        end = datetime.datetime(2024, 1, 17, 0, 0, tzinfo=FRANCE_TZ)
        with patch("custom_components.rtetempo.api.client.asyncio.sleep", new_callable=AsyncMock):
            data = await client.async_get_tempo_data(start, end)
        assert len(data.adjusted_days) == 1

    @pytest.mark.asyncio
    async def test_retry_exhausted(self, mock_session, mock_auth):
        """All retries fail -> raises last error."""
        client = RTETempoClient(mock_session, mock_auth)
        mock_session.get.side_effect = [
            _make_get_response(500),
            _make_get_response(500),
            _make_get_response(500),
        ]
        start = datetime.datetime(2024, 1, 14, 0, 0, tzinfo=FRANCE_TZ)
        end = datetime.datetime(2024, 1, 17, 0, 0, tzinfo=FRANCE_TZ)
        with patch("custom_components.rtetempo.api.client.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(RTETempoServerError):
                await client.async_get_tempo_data(start, end)

    @pytest.mark.asyncio
    async def test_no_retry_on_client_error(self, mock_session, mock_auth):
        """4xx errors (except 429) do not retry."""
        client = RTETempoClient(mock_session, mock_auth)
        mock_session.get.return_value = _make_get_response(403)
        start = datetime.datetime(2024, 1, 14, 0, 0, tzinfo=FRANCE_TZ)
        end = datetime.datetime(2024, 1, 17, 0, 0, tzinfo=FRANCE_TZ)
        with pytest.raises(RTETempoClientError) as exc_info:
            await client.async_get_tempo_data(start, end)
        assert exc_info.value.status_code == 403
        # Only one call - no retries
        assert mock_session.get.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_rate_limit(self, mock_session, mock_auth):
        """429 errors trigger retry with Retry-After."""
        client = RTETempoClient(mock_session, mock_auth)
        mock_session.get.side_effect = [
            _make_get_response(429, headers={"Retry-After": "2"}),
            _make_get_response(200, self._make_valid_payload()),
        ]
        start = datetime.datetime(2024, 1, 14, 0, 0, tzinfo=FRANCE_TZ)
        end = datetime.datetime(2024, 1, 17, 0, 0, tzinfo=FRANCE_TZ)
        sleep_path = "custom_components.rtetempo.api.client.asyncio.sleep"
        with patch(sleep_path, new_callable=AsyncMock) as mock_sleep:
            data = await client.async_get_tempo_data(start, end)
        assert len(data.adjusted_days) == 1
        # Sleep should have used at least the Retry-After value
        mock_sleep.assert_called_once()
        assert mock_sleep.call_args[0][0] >= 2.0

    @pytest.mark.asyncio
    async def test_retry_on_connection_error(self, mock_session, mock_auth):
        """Connection errors trigger retry."""
        client = RTETempoClient(mock_session, mock_auth)
        mock_session.get.side_effect = [
            aiohttp.ClientError("offline"),
            _make_get_response(200, self._make_valid_payload()),
        ]
        start = datetime.datetime(2024, 1, 14, 0, 0, tzinfo=FRANCE_TZ)
        end = datetime.datetime(2024, 1, 17, 0, 0, tzinfo=FRANCE_TZ)
        with patch("custom_components.rtetempo.api.client.asyncio.sleep", new_callable=AsyncMock):
            data = await client.async_get_tempo_data(start, end)
        assert len(data.adjusted_days) == 1

    @pytest.mark.asyncio
    async def test_no_retry_on_auth_error(self, mock_session, mock_auth):
        """Auth errors do not retry."""
        client = RTETempoClient(mock_session, mock_auth)
        mock_session.get.return_value = _make_get_response(401)
        start = datetime.datetime(2024, 1, 14, 0, 0, tzinfo=FRANCE_TZ)
        end = datetime.datetime(2024, 1, 17, 0, 0, tzinfo=FRANCE_TZ)
        with pytest.raises(RTETempoAuthError):
            await client.async_get_tempo_data(start, end)
        assert mock_session.get.call_count == 1


class TestCircuitBreaker:
    """Tests for circuit breaker behavior."""

    @pytest.mark.asyncio
    async def test_opens_after_threshold(self, mock_session, mock_auth):
        """Circuit opens after 5 consecutive failures."""
        client = RTETempoClient(mock_session, mock_auth)
        mock_session.get.return_value = _make_get_response(500)
        start = datetime.datetime(2024, 1, 14, 0, 0, tzinfo=FRANCE_TZ)
        end = datetime.datetime(2024, 1, 17, 0, 0, tzinfo=FRANCE_TZ)
        with patch("custom_components.rtetempo.api.client.asyncio.sleep", new_callable=AsyncMock):
            # 3 retries per call = 3 failures
            with pytest.raises(RTETempoServerError):
                await client.async_get_tempo_data(start, end)
            # 3 more retries = 6 total failures -> circuit open
            with pytest.raises((RTETempoServerError, RTETempoConnectionError)):
                await client.async_get_tempo_data(start, end)
        # Circuit should be open now
        assert client._cb_state == _CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_open_circuit_rejects_immediately(self, mock_session, mock_auth):
        """Open circuit raises immediately without making a request."""
        client = RTETempoClient(mock_session, mock_auth)
        client._cb_state = _CircuitState.OPEN
        client._cb_last_failure = time.monotonic()
        start = datetime.datetime(2024, 1, 14, 0, 0, tzinfo=FRANCE_TZ)
        end = datetime.datetime(2024, 1, 17, 0, 0, tzinfo=FRANCE_TZ)
        with pytest.raises(RTETempoConnectionError, match="Circuit breaker"):
            await client.async_get_tempo_data(start, end)
        mock_session.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_half_open_after_recovery_timeout(self, mock_session, mock_auth):
        """Circuit transitions to half-open after recovery timeout."""
        client = RTETempoClient(mock_session, mock_auth)
        client._cb_state = _CircuitState.OPEN
        # Simulate recovery timeout elapsed
        client._cb_last_failure = time.monotonic() - 301
        mock_session.get.return_value = _make_get_response(
            200,
            {
                "tempo_like_calendars": {
                    "values": [
                        {
                            "start_date": "2024-01-15T00:00:00+01:00",
                            "end_date": "2024-01-16T00:00:00+01:00",
                            "value": "BLUE",
                            "updated_date": "2024-01-15T10:00:00+01:00",
                        }
                    ]
                }
            },
        )
        start = datetime.datetime(2024, 1, 14, 0, 0, tzinfo=FRANCE_TZ)
        end = datetime.datetime(2024, 1, 17, 0, 0, tzinfo=FRANCE_TZ)
        data = await client.async_get_tempo_data(start, end)
        # Should have succeeded and closed the circuit
        assert client._cb_state == _CircuitState.CLOSED
        assert len(data.adjusted_days) == 1

    @pytest.mark.asyncio
    async def test_success_resets_circuit(self, mock_session, mock_auth):
        """Successful request resets failure count."""
        client = RTETempoClient(mock_session, mock_auth)
        client._cb_failure_count = 3
        mock_session.get.return_value = _make_get_response(
            200,
            {
                "tempo_like_calendars": {
                    "values": [
                        {
                            "start_date": "2024-01-15T00:00:00+01:00",
                            "end_date": "2024-01-16T00:00:00+01:00",
                            "value": "BLUE",
                            "updated_date": "2024-01-15T10:00:00+01:00",
                        }
                    ]
                }
            },
        )
        start = datetime.datetime(2024, 1, 14, 0, 0, tzinfo=FRANCE_TZ)
        end = datetime.datetime(2024, 1, 17, 0, 0, tzinfo=FRANCE_TZ)
        await client.async_get_tempo_data(start, end)
        assert client._cb_failure_count == 0
        assert client._cb_state == _CircuitState.CLOSED


class TestCheckResponseStatus:
    """Tests for _check_response_status."""

    def _make_resp(self, status, headers=None):
        resp = MagicMock(spec=aiohttp.ClientResponse)
        resp.status = status
        resp.reason = "Test"
        resp.headers = headers or {}
        return resp

    def test_200_ok(self):
        RTETempoClient._check_response_status(self._make_resp(200))

    def test_429_rate_limit(self):
        with pytest.raises(RTETempoRateLimitError) as exc_info:
            RTETempoClient._check_response_status(
                self._make_resp(429, {"Retry-After": "10"})
            )
        assert exc_info.value.retry_after == 10.0

    def test_429_no_retry_after(self):
        with pytest.raises(RTETempoRateLimitError) as exc_info:
            RTETempoClient._check_response_status(self._make_resp(429))
        assert exc_info.value.retry_after is None

    def test_429_invalid_retry_after(self):
        with pytest.raises(RTETempoRateLimitError) as exc_info:
            RTETempoClient._check_response_status(
                self._make_resp(429, {"Retry-After": "not-a-number"})
            )
        assert exc_info.value.retry_after is None

    def test_401_auth_error(self):
        with pytest.raises(RTETempoAuthError):
            RTETempoClient._check_response_status(self._make_resp(401))

    def test_403_client_error(self):
        with pytest.raises(RTETempoClientError) as exc_info:
            RTETempoClient._check_response_status(self._make_resp(403))
        assert exc_info.value.status_code == 403

    def test_404_client_error(self):
        with pytest.raises(RTETempoClientError) as exc_info:
            RTETempoClient._check_response_status(self._make_resp(404))
        assert exc_info.value.status_code == 404

    def test_500_server_error(self):
        with pytest.raises(RTETempoServerError) as exc_info:
            RTETempoClient._check_response_status(self._make_resp(500))
        assert exc_info.value.status_code == 500

    def test_503_server_error(self):
        with pytest.raises(RTETempoServerError) as exc_info:
            RTETempoClient._check_response_status(self._make_resp(503))
        assert exc_info.value.status_code == 503
