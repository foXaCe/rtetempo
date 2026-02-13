"""Async RTE Tempo API client with retry, circuit breaker, and rate limiting."""

from __future__ import annotations

import asyncio
import datetime
import logging
import time
from enum import Enum

import aiohttp

from ..const import (
    API_DATE_FORMAT,
    API_DEFAULT_TIMEOUT,
    API_KEY_END,
    API_KEY_RESULTS,
    API_KEY_START,
    API_KEY_UPDATED,
    API_KEY_VALUE,
    API_KEY_VALUES,
    API_TEMPO_ENDPOINT,
    FRANCE_TZ,
    HOUR_OF_CHANGE,
    USER_AGENT,
)
from .auth import RTETempoAuth
from .exceptions import (
    RTETempoAuthError,
    RTETempoClientError,
    RTETempoConnectionError,
    RTETempoError,
    RTETempoRateLimitError,
    RTETempoServerError,
)
from .models import TempoData, TempoDay

_LOGGER = logging.getLogger(__name__)

# Retry configuration
_MAX_RETRIES = 3
_BACKOFF_BASE = 1  # seconds: 1, 2, 4

# Circuit breaker configuration
_CB_FAILURE_THRESHOLD = 5
_CB_RECOVERY_TIMEOUT = 300  # 5 minutes


class _CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class RTETempoClient:
    """Async client for the RTE Tempo API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        auth: RTETempoAuth,
    ) -> None:
        """Initialize the client."""
        self._session = session
        self._auth = auth
        # Circuit breaker state
        self._cb_state = _CircuitState.CLOSED
        self._cb_failure_count = 0
        self._cb_last_failure: float = 0.0

    async def async_test_credentials(self) -> None:
        """Validate API credentials (for config flow). No retry, no circuit breaker."""
        token = await self._auth.async_get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }
        try:
            async with self._session.get(
                API_TEMPO_ENDPOINT,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=API_DEFAULT_TIMEOUT),
            ) as resp:
                self._check_response_status(resp)
        except aiohttp.ClientError as err:
            raise RTETempoConnectionError(
                f"Connection error during credential test: {err}"
            ) from err
        except TimeoutError as err:
            raise RTETempoConnectionError(
                f"Timeout during credential test: {err}"
            ) from err

    async def async_get_tempo_data(
        self,
        start: datetime.datetime,
        end: datetime.datetime,
    ) -> TempoData:
        """Fetch and parse tempo data with retry and circuit breaker."""
        self._check_circuit_breaker()
        last_err: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                payload = await self._async_fetch(start, end)
                data = _parse_response(payload)
                self._cb_on_success()
                return data
            except (RTETempoServerError, RTETempoRateLimitError, RTETempoConnectionError) as err:
                last_err = err
                self._cb_on_failure()
                if attempt < _MAX_RETRIES - 1:
                    wait = _BACKOFF_BASE * (2**attempt)
                    if isinstance(err, RTETempoRateLimitError) and err.retry_after:
                        wait = max(wait, err.retry_after)
                    _LOGGER.debug(
                        "Retryable error (attempt %d/%d), waiting %.1fs: %s",
                        attempt + 1,
                        _MAX_RETRIES,
                        wait,
                        err,
                    )
                    await asyncio.sleep(wait)
            except (RTETempoAuthError, RTETempoClientError):
                # Non-retryable errors
                self._cb_on_failure()
                raise
        # All retries exhausted
        raise last_err  # type: ignore[misc]

    async def _async_fetch(
        self,
        start: datetime.datetime,
        end: datetime.datetime,
    ) -> dict:
        """Perform the actual HTTP request."""
        token = await self._auth.async_get_access_token()
        start_str = start.strftime(API_DATE_FORMAT)
        end_str = end.strftime(API_DATE_FORMAT)
        params = {
            "start_date": start_str[:-2] + ":" + start_str[-2:],
            "end_date": end_str[:-2] + ":" + end_str[-2:],
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }
        _LOGGER.debug(
            "Calling %s with start_date=%s, end_date=%s",
            API_TEMPO_ENDPOINT,
            params["start_date"],
            params["end_date"],
        )
        try:
            async with self._session.get(
                API_TEMPO_ENDPOINT,
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=API_DEFAULT_TIMEOUT),
            ) as resp:
                self._check_response_status(resp)
                return await resp.json()
        except aiohttp.ClientError as err:
            raise RTETempoConnectionError(
                f"Connection error: {err}"
            ) from err
        except TimeoutError as err:
            raise RTETempoConnectionError(
                f"Request timeout: {err}"
            ) from err

    # ── Circuit breaker ──────────────────────────────────────────────

    def _check_circuit_breaker(self) -> None:
        """Raise if circuit is open and recovery timeout hasn't elapsed."""
        if self._cb_state == _CircuitState.OPEN:
            if time.monotonic() - self._cb_last_failure >= _CB_RECOVERY_TIMEOUT:
                _LOGGER.debug("Circuit breaker: transitioning to half-open")
                self._cb_state = _CircuitState.HALF_OPEN
            else:
                raise RTETempoConnectionError("Circuit breaker is open")

    def _cb_on_success(self) -> None:
        """Reset circuit breaker on success."""
        if self._cb_state != _CircuitState.CLOSED:
            _LOGGER.debug("Circuit breaker: closing after success")
        self._cb_state = _CircuitState.CLOSED
        self._cb_failure_count = 0

    def _cb_on_failure(self) -> None:
        """Record failure for circuit breaker."""
        self._cb_failure_count += 1
        self._cb_last_failure = time.monotonic()
        if self._cb_failure_count >= _CB_FAILURE_THRESHOLD:
            if self._cb_state != _CircuitState.OPEN:
                _LOGGER.warning(
                    "Circuit breaker: opening after %d failures",
                    self._cb_failure_count,
                )
            self._cb_state = _CircuitState.OPEN

    # ── HTTP status mapping ──────────────────────────────────────────

    @staticmethod
    def _check_response_status(resp: aiohttp.ClientResponse) -> None:
        """Map HTTP status codes to typed exceptions."""
        status = resp.status
        if status == 200:
            return
        reason = resp.reason or "Unknown"
        if status == 429:
            retry_after = resp.headers.get("Retry-After")
            retry_val: float | None = None
            if retry_after:
                try:
                    retry_val = float(retry_after)
                except ValueError:
                    retry_val = None
            raise RTETempoRateLimitError(retry_after=retry_val)
        if status == 401:
            raise RTETempoAuthError(f"Unauthorized (HTTP 401): {reason}")
        if 400 <= status < 500:
            raise RTETempoClientError(status, reason)
        if status >= 500:
            raise RTETempoServerError(status, reason)
        raise RTETempoError(f"Unexpected HTTP {status}: {reason}")


# ── Parsing helpers ──────────────────────────────────────────────────


def adjust_tempo_time(date: datetime.datetime) -> datetime.datetime:
    """RTE API gives midnight-to-midnight; actual tempo runs 6h to 6h."""
    return date + datetime.timedelta(hours=HOUR_OF_CHANGE)


def parse_rte_api_datetime(date: str) -> datetime.datetime:
    """Parse RTE API datetime string (removes ':' from timezone offset)."""
    date = date[:-3] + date[-2:]
    return datetime.datetime.strptime(date, API_DATE_FORMAT)


def parse_rte_api_date(date: str) -> datetime.date:
    """Parse RTE API datetime string to a date object."""
    day_datetime = parse_rte_api_datetime(date)
    return datetime.date(
        year=day_datetime.year, month=day_datetime.month, day=day_datetime.day
    )


def _parse_response(payload: dict) -> TempoData:
    """Parse an API JSON response into TempoData."""
    adjusted_days: list[TempoDay] = []
    regular_days: list[TempoDay] = []

    for entry in payload[API_KEY_RESULTS][API_KEY_VALUES]:
        try:
            adjusted_days.append(
                TempoDay(
                    start=adjust_tempo_time(
                        parse_rte_api_datetime(entry[API_KEY_START])
                    ),
                    end=adjust_tempo_time(
                        parse_rte_api_datetime(entry[API_KEY_END])
                    ),
                    value=entry[API_KEY_VALUE],
                    updated=parse_rte_api_datetime(entry[API_KEY_UPDATED]),
                )
            )
            regular_days.append(
                TempoDay(
                    start=parse_rte_api_date(entry[API_KEY_START]),
                    end=parse_rte_api_date(entry[API_KEY_END]),
                    value=entry[API_KEY_VALUE],
                    updated=parse_rte_api_datetime(entry[API_KEY_UPDATED]),
                )
            )
        except KeyError as key_error:
            _LOGGER.warning(
                "Day entry skipped due to %s: %s",
                repr(key_error),
                entry,
            )

    # Compute data_end: latest end date from regular days
    data_end: datetime.datetime | None = None
    if regular_days:
        newest = max(regular_days, key=lambda d: d.end).end
        data_end = datetime.datetime(
            year=newest.year,
            month=newest.month,
            day=newest.day,
            tzinfo=FRANCE_TZ,
        )

    return TempoData(
        adjusted_days=adjusted_days,
        regular_days=regular_days,
        data_end=data_end,
    )
