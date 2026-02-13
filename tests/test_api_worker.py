"""Tests for the API Worker module."""
from __future__ import annotations

import datetime
from unittest.mock import MagicMock, patch

import pytest
import requests
from oauthlib.oauth2 import TokenExpiredError
from oauthlib.oauth2.rfc6749.errors import OAuth2Error

from custom_components.rtetempo.api_worker import (
    APIWorker,
    BadRequest,
    ServerError,
    TempoDay,
    UnexpectedError,
    adjust_tempo_time,
    application_tester,
    handle_api_errors,
    parse_rte_api_date,
    parse_rte_api_datetime,
)
from custom_components.rtetempo.const import FRANCE_TZ, HOUR_OF_CHANGE

from .conftest import make_tempo_day_date, make_tempo_day_time


# ── parse_rte_api_datetime ──────────────────────────────────────────────


class TestParseRteApiDatetime:
    """Tests for parse_rte_api_datetime."""

    def test_standard_date(self):
        result = parse_rte_api_datetime("2024-01-15T00:00:00+01:00")
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 0
        assert result.minute == 0

    def test_with_non_zero_time(self):
        result = parse_rte_api_datetime("2024-06-20T14:30:00+02:00")
        assert result.hour == 14
        assert result.minute == 30

    def test_timezone_preserved(self):
        result = parse_rte_api_datetime("2024-01-15T00:00:00+01:00")
        assert result.tzinfo is not None

    def test_negative_offset(self):
        """Verify negative UTC offsets are handled."""
        result = parse_rte_api_datetime("2024-01-15T00:00:00-05:00")
        assert result.tzinfo is not None


# ── parse_rte_api_date ──────────────────────────────────────────────────


class TestParseRteApiDate:
    """Tests for parse_rte_api_date."""

    def test_returns_date(self):
        result = parse_rte_api_date("2024-01-15T00:00:00+01:00")
        assert isinstance(result, datetime.date)
        assert not isinstance(result, datetime.datetime)

    def test_correct_date(self):
        result = parse_rte_api_date("2024-03-20T00:00:00+01:00")
        assert result == datetime.date(2024, 3, 20)


# ── adjust_tempo_time ───────────────────────────────────────────────────


class TestAdjustTempoTime:
    """Tests for adjust_tempo_time."""

    def test_adds_6_hours(self):
        dt = datetime.datetime(2024, 1, 15, 0, 0, tzinfo=FRANCE_TZ)
        result = adjust_tempo_time(dt)
        assert result.hour == HOUR_OF_CHANGE
        assert result.day == 15

    def test_midnight_becomes_6am(self):
        dt = datetime.datetime(2024, 1, 15, 0, 0, tzinfo=FRANCE_TZ)
        result = adjust_tempo_time(dt)
        assert result == datetime.datetime(2024, 1, 15, 6, 0, tzinfo=FRANCE_TZ)

    def test_next_day_midnight_becomes_6am(self):
        dt = datetime.datetime(2024, 1, 16, 0, 0, tzinfo=FRANCE_TZ)
        result = adjust_tempo_time(dt)
        assert result == datetime.datetime(2024, 1, 16, 6, 0, tzinfo=FRANCE_TZ)


# ── handle_api_errors ───────────────────────────────────────────────────


class TestHandleApiErrors:
    """Tests for handle_api_errors."""

    def _mock_response(self, status_code: int, json_data=None, text=""):
        resp = MagicMock(spec=requests.Response)
        resp.status_code = status_code
        resp.text = text
        if json_data is not None:
            resp.json.return_value = json_data
        else:
            resp.json.side_effect = requests.JSONDecodeError("", "", 0)
        return resp

    def test_200_no_error(self):
        resp = self._mock_response(200)
        handle_api_errors(resp)  # Should not raise

    def test_400_with_json(self):
        resp = self._mock_response(
            400, {"error": "invalid_request", "error_description": "bad param"}
        )
        with pytest.raises(BadRequest) as exc_info:
            handle_api_errors(resp)
        assert exc_info.value.code == 400
        assert "invalid_request" in str(exc_info.value)

    def test_400_without_json(self):
        resp = self._mock_response(400, text="bad request body")
        with pytest.raises(BadRequest) as exc_info:
            handle_api_errors(resp)
        assert exc_info.value.code == 400

    def test_400_json_missing_keys(self):
        resp = self._mock_response(400, {"unexpected": "format"})
        with pytest.raises(BadRequest):
            handle_api_errors(resp)

    def test_401(self):
        resp = self._mock_response(401)
        with pytest.raises(BadRequest) as exc_info:
            handle_api_errors(resp)
        assert exc_info.value.code == 401
        assert "Unauthorized" in str(exc_info.value)

    def test_403(self):
        resp = self._mock_response(403)
        with pytest.raises(BadRequest) as exc_info:
            handle_api_errors(resp)
        assert exc_info.value.code == 403

    def test_404(self):
        resp = self._mock_response(404)
        with pytest.raises(BadRequest) as exc_info:
            handle_api_errors(resp)
        assert exc_info.value.code == 404

    def test_408(self):
        resp = self._mock_response(408)
        with pytest.raises(BadRequest) as exc_info:
            handle_api_errors(resp)
        assert exc_info.value.code == 408

    def test_413(self):
        resp = self._mock_response(413)
        with pytest.raises(BadRequest) as exc_info:
            handle_api_errors(resp)
        assert exc_info.value.code == 413

    def test_414(self):
        resp = self._mock_response(414)
        with pytest.raises(BadRequest) as exc_info:
            handle_api_errors(resp)
        assert exc_info.value.code == 414

    def test_429(self):
        resp = self._mock_response(429)
        with pytest.raises(BadRequest) as exc_info:
            handle_api_errors(resp)
        assert exc_info.value.code == 429

    def test_500_with_json(self):
        resp = self._mock_response(
            500, {"error": "internal", "error_description": "oops"}
        )
        with pytest.raises(ServerError) as exc_info:
            handle_api_errors(resp)
        assert exc_info.value.code == 500

    def test_500_without_json(self):
        resp = self._mock_response(500, text="server error body")
        with pytest.raises(ServerError) as exc_info:
            handle_api_errors(resp)
        assert exc_info.value.code == 500

    def test_500_json_missing_keys(self):
        resp = self._mock_response(500, {"unexpected": "format"})
        with pytest.raises(ServerError):
            handle_api_errors(resp)

    def test_503(self):
        resp = self._mock_response(503)
        with pytest.raises(ServerError) as exc_info:
            handle_api_errors(resp)
        assert exc_info.value.code == 503

    def test_509(self):
        resp = self._mock_response(509)
        with pytest.raises(ServerError) as exc_info:
            handle_api_errors(resp)
        assert exc_info.value.code == 509

    def test_unexpected_code(self):
        resp = self._mock_response(418, text="I'm a teapot")
        with pytest.raises(UnexpectedError) as exc_info:
            handle_api_errors(resp)
        assert exc_info.value.code == 418


# ── TempoDay ────────────────────────────────────────────────────────────


class TestTempoDay:
    """Tests for TempoDay NamedTuple."""

    def test_creation(self):
        td = TempoDay(
            Start=datetime.date(2024, 1, 15),
            End=datetime.date(2024, 1, 16),
            Value="BLUE",
            Updated=datetime.datetime(2024, 1, 15, 10, 0, tzinfo=FRANCE_TZ),
        )
        assert td.Start == datetime.date(2024, 1, 15)
        assert td.Value == "BLUE"

    def test_named_access(self):
        td = make_tempo_day_date(2024, 1, 15, "RED")
        assert td.Start == datetime.date(2024, 1, 15)
        assert td.End == datetime.date(2024, 1, 16)
        assert td.Value == "RED"

    def test_time_based(self):
        td = make_tempo_day_time(2024, 1, 15, "WHITE")
        assert td.Start.hour == 6
        assert td.End.hour == 6
        assert td.End.day == 16


# ── Exception classes ───────────────────────────────────────────────────


class TestExceptions:
    """Tests for exception classes."""

    def test_bad_request(self):
        exc = BadRequest(400, "bad")
        assert exc.code == 400
        assert "400" in str(exc)
        assert "bad" in str(exc)

    def test_server_error(self):
        exc = ServerError(500, "oops")
        assert exc.code == 500
        assert "500" in str(exc)

    def test_unexpected_error(self):
        exc = UnexpectedError(418, "teapot")
        assert exc.code == 418
        assert "teapot" in str(exc)


# ── APIWorker ───────────────────────────────────────────────────────────


class TestAPIWorkerInit:
    """Tests for APIWorker initialization and basic methods."""

    def test_init(self):
        worker = APIWorker(
            client_id="test_id",
            client_secret="test_secret",
            adjusted_days=True,
        )
        assert worker.adjusted_days is True
        assert worker._tempo_days_time == []
        assert worker._tempo_days_date == []
        assert worker.name == "RTE Tempo API Worker"

    def test_update_options(self):
        worker = APIWorker("id", "secret", adjusted_days=False)
        assert worker.adjusted_days is False
        worker.update_options(True)
        assert worker.adjusted_days is True

    def test_get_calendar_days_adjusted(self):
        worker = APIWorker("id", "secret", adjusted_days=True)
        worker._tempo_days_time = [make_tempo_day_time(2024, 1, 15, "BLUE")]
        worker._tempo_days_date = [make_tempo_day_date(2024, 1, 15, "BLUE")]
        result = worker.get_calendar_days()
        assert result == worker._tempo_days_time

    def test_get_calendar_days_regular(self):
        worker = APIWorker("id", "secret", adjusted_days=False)
        worker._tempo_days_time = [make_tempo_day_time(2024, 1, 15, "BLUE")]
        worker._tempo_days_date = [make_tempo_day_date(2024, 1, 15, "BLUE")]
        result = worker.get_calendar_days()
        assert result == worker._tempo_days_date

    def test_get_adjusted_days(self):
        worker = APIWorker("id", "secret", adjusted_days=False)
        worker._tempo_days_time = [make_tempo_day_time(2024, 1, 15, "BLUE")]
        assert worker.get_adjusted_days() == worker._tempo_days_time

    def test_get_regular_days(self):
        worker = APIWorker("id", "secret", adjusted_days=False)
        worker._tempo_days_date = [make_tempo_day_date(2024, 1, 15, "BLUE")]
        assert worker.get_regular_days() == worker._tempo_days_date

    def test_signalstop(self):
        worker = APIWorker("id", "secret", adjusted_days=False)
        assert not worker._stopevent.is_set()
        worker.signalstop("test")
        assert worker._stopevent.is_set()


# ── APIWorker._compute_wait_time ────────────────────────────────────────


class TestComputeWaitTime:
    """Tests for _compute_wait_time."""

    def test_no_data_end(self):
        worker = APIWorker("id", "secret", adjusted_days=False)
        now = datetime.datetime(2024, 1, 15, 12, 0, tzinfo=FRANCE_TZ)
        result = worker._compute_wait_time(now, None)
        assert result == datetime.timedelta(minutes=10)

    def test_diff_2_days_past_confirmation(self):
        """When we have next day and past confirmation hour -> wait until tomorrow."""
        worker = APIWorker("id", "secret", adjusted_days=False)
        now = datetime.datetime(2024, 1, 15, 11, 0, tzinfo=FRANCE_TZ)
        # data_end = 2 days from today start
        data_end = datetime.datetime(2024, 1, 17, 0, 0, tzinfo=FRANCE_TZ)
        with patch("custom_components.rtetempo.api_worker.random.randrange") as mock_rand:
            mock_rand.return_value = 70000
            result = worker._compute_wait_time(now, data_end)
        assert result.total_seconds() > 0

    def test_diff_2_days_before_confirmation(self):
        """When we have next day but before confirmation hour."""
        worker = APIWorker("id", "secret", adjusted_days=False)
        now = datetime.datetime(2024, 1, 15, 8, 0, tzinfo=FRANCE_TZ)
        data_end = datetime.datetime(2024, 1, 17, 0, 0, tzinfo=FRANCE_TZ)
        with patch("custom_components.rtetempo.api_worker.random.randrange") as mock_rand:
            mock_rand.return_value = 90000
            result = worker._compute_wait_time(now, data_end)
        assert result.total_seconds() > 0

    def test_diff_1_day_before_6am(self):
        """When we don't have next day and it's before 6 AM."""
        worker = APIWorker("id", "secret", adjusted_days=False)
        now = datetime.datetime(2024, 1, 15, 4, 0, tzinfo=FRANCE_TZ)
        data_end = datetime.datetime(2024, 1, 16, 0, 0, tzinfo=FRANCE_TZ)
        with patch("custom_components.rtetempo.api_worker.random.randrange") as mock_rand:
            mock_rand.return_value = 8000
            result = worker._compute_wait_time(now, data_end)
        assert result.total_seconds() > 0

    def test_diff_1_day_after_6am(self):
        """When we don't have next day and it's after 6 AM -> retry soon."""
        worker = APIWorker("id", "secret", adjusted_days=False)
        now = datetime.datetime(2024, 1, 15, 10, 0, tzinfo=FRANCE_TZ)
        data_end = datetime.datetime(2024, 1, 16, 0, 0, tzinfo=FRANCE_TZ)
        with patch("custom_components.rtetempo.api_worker.random.randrange") as mock_rand:
            mock_rand.return_value = 1500
            result = worker._compute_wait_time(now, data_end)
        # Should be around 30 minutes
        assert result.total_seconds() > 0
        assert result.total_seconds() < 7200

    def test_unexpected_diff(self):
        """When diff is unexpected (0 or negative) -> fallback 1h."""
        worker = APIWorker("id", "secret", adjusted_days=False)
        now = datetime.datetime(2024, 1, 15, 10, 0, tzinfo=FRANCE_TZ)
        data_end = datetime.datetime(2024, 1, 15, 0, 0, tzinfo=FRANCE_TZ)
        with patch("custom_components.rtetempo.api_worker.random.randrange") as mock_rand:
            mock_rand.return_value = 3000
            result = worker._compute_wait_time(now, data_end)
        assert result.total_seconds() > 0


# ── APIWorker._update_tempo_days ────────────────────────────────────────


class TestUpdateTempoDays:
    """Tests for _update_tempo_days."""

    def _make_api_response(self, values, status_code=200):
        resp = MagicMock(spec=requests.Response)
        resp.status_code = status_code
        resp.json.return_value = {
            "tempo_like_calendars": {
                "values": values,
            }
        }
        resp.text = ""
        return resp

    def test_parse_single_day(self):
        worker = APIWorker("id", "secret", adjusted_days=False)
        resp = self._make_api_response([
            {
                "start_date": "2024-01-15T00:00:00+01:00",
                "end_date": "2024-01-16T00:00:00+01:00",
                "value": "BLUE",
                "updated_date": "2024-01-15T10:00:00+01:00",
            }
        ])
        with patch.object(worker, "_get_tempo_data", return_value=resp):
            reftime = datetime.datetime(2024, 1, 15, 12, 0, tzinfo=FRANCE_TZ)
            result = worker._update_tempo_days(reftime, 1, 2)
        assert result is not None
        assert len(worker._tempo_days_date) == 1
        assert len(worker._tempo_days_time) == 1
        assert worker._tempo_days_date[0].Value == "BLUE"

    def test_parse_multiple_days(self):
        worker = APIWorker("id", "secret", adjusted_days=False)
        values = [
            {
                "start_date": f"2024-01-{15 + i:02d}T00:00:00+01:00",
                "end_date": f"2024-01-{16 + i:02d}T00:00:00+01:00",
                "value": "BLUE",
                "updated_date": f"2024-01-{15 + i:02d}T10:00:00+01:00",
            }
            for i in range(5)
        ]
        resp = self._make_api_response(values)
        with patch.object(worker, "_get_tempo_data", return_value=resp):
            reftime = datetime.datetime(2024, 1, 15, 12, 0, tzinfo=FRANCE_TZ)
            result = worker._update_tempo_days(reftime, 1, 2)
        assert len(worker._tempo_days_date) == 5

    def test_api_request_error(self):
        worker = APIWorker("id", "secret", adjusted_days=False)
        with patch.object(
            worker, "_get_tempo_data",
            side_effect=requests.exceptions.ConnectionError("no network"),
        ):
            reftime = datetime.datetime(2024, 1, 15, 12, 0, tzinfo=FRANCE_TZ)
            result = worker._update_tempo_days(reftime, 1, 2)
        assert result is None

    def test_bad_request_error(self):
        worker = APIWorker("id", "secret", adjusted_days=False)
        resp = MagicMock(spec=requests.Response)
        resp.status_code = 400
        resp.json.return_value = {
            "error": "bad",
            "error_description": "request",
        }
        resp.text = ""
        with patch.object(worker, "_get_tempo_data", return_value=resp):
            reftime = datetime.datetime(2024, 1, 15, 12, 0, tzinfo=FRANCE_TZ)
            result = worker._update_tempo_days(reftime, 1, 2)
        assert result is None

    def test_json_decode_error(self):
        worker = APIWorker("id", "secret", adjusted_days=False)
        resp = MagicMock(spec=requests.Response)
        resp.status_code = 200
        resp.json.side_effect = requests.JSONDecodeError("", "", 0)
        resp.text = "not json"
        with patch.object(worker, "_get_tempo_data", return_value=resp):
            reftime = datetime.datetime(2024, 1, 15, 12, 0, tzinfo=FRANCE_TZ)
            result = worker._update_tempo_days(reftime, 1, 2)
        assert result is None

    def test_missing_value_key_known_date_workaround(self):
        """The known 2022-12-28 workaround should fallback to BLUE."""
        worker = APIWorker("id", "secret", adjusted_days=False)
        resp = self._make_api_response([
            {
                "start_date": "2022-12-28T00:00:00+01:00",
                "end_date": "2022-12-29T00:00:00+01:00",
                "updated_date": "2022-12-28T10:00:00+01:00",
                # Missing "value" key
            }
        ])
        with patch.object(worker, "_get_tempo_data", return_value=resp):
            reftime = datetime.datetime(2022, 12, 28, 12, 0, tzinfo=FRANCE_TZ)
            result = worker._update_tempo_days(reftime, 1, 2)
        assert len(worker._tempo_days_date) == 1
        assert worker._tempo_days_date[0].Value == "BLUE"

    def test_missing_value_key_unknown_date_skipped(self):
        """Unknown dates with missing value key should be skipped."""
        worker = APIWorker("id", "secret", adjusted_days=False)
        resp = self._make_api_response([
            {
                "start_date": "2024-01-15T00:00:00+01:00",
                "end_date": "2024-01-16T00:00:00+01:00",
                "updated_date": "2024-01-15T10:00:00+01:00",
                # Missing "value" key
            }
        ])
        with patch.object(worker, "_get_tempo_data", return_value=resp):
            reftime = datetime.datetime(2024, 1, 15, 12, 0, tzinfo=FRANCE_TZ)
            result = worker._update_tempo_days(reftime, 1, 2)
        assert len(worker._tempo_days_date) == 0

    def test_empty_results(self):
        worker = APIWorker("id", "secret", adjusted_days=False)
        resp = self._make_api_response([])
        with patch.object(worker, "_get_tempo_data", return_value=resp):
            reftime = datetime.datetime(2024, 1, 15, 12, 0, tzinfo=FRANCE_TZ)
            result = worker._update_tempo_days(reftime, 1, 2)
        assert result is None
        assert len(worker._tempo_days_date) == 0

    def test_oauth2_error(self):
        """OAuth2Error during _get_tempo_data -> returns None."""
        worker = APIWorker("id", "secret", adjusted_days=False)
        resp = MagicMock(spec=requests.Response)
        resp.status_code = 200
        resp.json.return_value = {"tempo_like_calendars": {"values": []}}
        resp.text = ""
        # First call to _get_tempo_data succeeds, but handle_api_errors
        # is not the issue here. We need to trigger the OAuth2Error branch.
        with patch.object(
            worker,
            "_get_tempo_data",
            side_effect=OAuth2Error("token problem"),
        ):
            reftime = datetime.datetime(2024, 1, 15, 12, 0, tzinfo=FRANCE_TZ)
            result = worker._update_tempo_days(reftime, 1, 2)
        assert result is None


# ── APIWorker._get_access_token ─────────────────────────────────────────


class TestGetAccessToken:
    """Tests for _get_access_token."""

    def test_success(self):
        worker = APIWorker("id", "secret", adjusted_days=False)
        with patch.object(worker._oauth, "fetch_token") as mock_fetch:
            worker._get_access_token()
        mock_fetch.assert_called_once()

    def test_request_exception(self):
        worker = APIWorker("id", "secret", adjusted_days=False)
        with patch.object(
            worker._oauth,
            "fetch_token",
            side_effect=requests.exceptions.ConnectionError("offline"),
        ):
            # Should not raise, just log error
            worker._get_access_token()

    def test_oauth2_error(self):
        worker = APIWorker("id", "secret", adjusted_days=False)
        with patch.object(
            worker._oauth,
            "fetch_token",
            side_effect=OAuth2Error("bad token"),
        ):
            # Should not raise, just log error
            worker._get_access_token()


# ── APIWorker._get_tempo_data ───────────────────────────────────────────


class TestGetTempoData:
    """Tests for _get_tempo_data."""

    def test_success(self):
        worker = APIWorker("id", "secret", adjusted_days=False)
        mock_resp = MagicMock(spec=requests.Response)
        with patch.object(worker._oauth, "get", return_value=mock_resp):
            start = datetime.datetime(2024, 1, 1, 0, 0, tzinfo=FRANCE_TZ)
            end = datetime.datetime(2024, 1, 3, 0, 0, tzinfo=FRANCE_TZ)
            result = worker._get_tempo_data(start, end)
        assert result == mock_resp

    def test_token_expired_retry(self):
        """TokenExpiredError triggers token refresh and retry."""
        worker = APIWorker("id", "secret", adjusted_days=False)
        mock_resp = MagicMock(spec=requests.Response)
        with (
            patch.object(
                worker._oauth,
                "get",
                side_effect=[TokenExpiredError(), mock_resp],
            ),
            patch.object(worker, "_get_access_token") as mock_refresh,
        ):
            start = datetime.datetime(2024, 1, 1, 0, 0, tzinfo=FRANCE_TZ)
            end = datetime.datetime(2024, 1, 3, 0, 0, tzinfo=FRANCE_TZ)
            result = worker._get_tempo_data(start, end)
        mock_refresh.assert_called_once()
        assert result == mock_resp


# ── APIWorker.run ───────────────────────────────────────────────────────


class TestAPIWorkerRun:
    """Tests for the run() thread method."""

    def test_run_stops_immediately(self):
        """Thread loop runs once then stops."""
        worker = APIWorker("id", "secret", adjusted_days=False)
        # Pre-set a token so it skips _get_access_token
        worker._oauth.token = {"access_token": "fake"}
        with (
            patch.object(
                worker,
                "_update_tempo_days",
                return_value=None,
            ),
            patch.object(
                worker,
                "_compute_wait_time",
                return_value=datetime.timedelta(seconds=1),
            ),
            patch.object(
                worker._stopevent,
                "wait",
                return_value=True,  # Simulate stop signal
            ),
        ):
            worker.run()
        # Thread should have finished

    def test_run_fetches_token_on_empty(self):
        """When token is empty, _get_access_token is called."""
        worker = APIWorker("id", "secret", adjusted_days=False)
        assert worker._oauth.token == {}
        with (
            patch.object(worker, "_get_access_token") as mock_auth,
            patch.object(
                worker,
                "_update_tempo_days",
                return_value=None,
            ),
            patch.object(
                worker,
                "_compute_wait_time",
                return_value=datetime.timedelta(seconds=1),
            ),
            patch.object(
                worker._stopevent,
                "wait",
                return_value=True,
            ),
        ):
            worker.run()
        mock_auth.assert_called_once()


# ── application_tester ──────────────────────────────────────────────────


class TestApplicationTester:
    """Tests for application_tester."""

    def test_success(self):
        mock_resp = MagicMock(spec=requests.Response)
        mock_resp.status_code = 200
        with (
            patch(
                "custom_components.rtetempo.api_worker.OAuth2Session"
            ) as mock_session_cls,
        ):
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.get.return_value = mock_resp
            application_tester("client_id", "client_secret")
        mock_session.fetch_token.assert_called_once()
        mock_session.get.assert_called_once()

    def test_api_error_raised(self):
        mock_resp = MagicMock(spec=requests.Response)
        mock_resp.status_code = 401
        mock_resp.json.side_effect = requests.JSONDecodeError("", "", 0)
        mock_resp.text = ""
        with (
            patch(
                "custom_components.rtetempo.api_worker.OAuth2Session"
            ) as mock_session_cls,
        ):
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.get.return_value = mock_resp
            with pytest.raises(BadRequest):
                application_tester("client_id", "client_secret")
