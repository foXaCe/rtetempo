"""Tests for forecast.py - OpenDPE data model and fetch logic."""

from __future__ import annotations

import datetime
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from custom_components.rtetempo.const import (
    API_VALUE_BLUE,
    API_VALUE_RED,
    API_VALUE_WHITE,
    FRANCE_TZ,
)
from custom_components.rtetempo.forecast import (
    ForecastDay,
    async_fetch_opendpe_forecast,
)


def _make_api_entry(
    date_str: str,
    color: str,
    probability: float = 90.0,
) -> dict:
    """Build a single API response entry."""
    return {
        "dateJour": date_str,
        "couleurJour": color,
        "probabilite": probability,
    }


def _today() -> datetime.date:
    return datetime.datetime.now(FRANCE_TZ).date()


def _future(days: int = 2) -> str:
    return (_today() + datetime.timedelta(days=days)).isoformat()


def _past(days: int = 1) -> str:
    return (_today() - datetime.timedelta(days=days)).isoformat()


def _mock_session(response_data=None, side_effect=None):
    """Build a mock aiohttp session with a context-manager-compatible get."""
    session = AsyncMock(spec=aiohttp.ClientSession)
    if side_effect is not None:
        ctx = AsyncMock(
            __aenter__=AsyncMock(side_effect=side_effect),
            __aexit__=AsyncMock(return_value=False),
        )
    else:
        resp = AsyncMock()
        resp.raise_for_status = MagicMock()
        resp.json = AsyncMock(return_value=response_data)
        ctx = AsyncMock(
            __aenter__=AsyncMock(return_value=resp),
            __aexit__=AsyncMock(return_value=False),
        )
    session.get = MagicMock(return_value=ctx)
    return session


class TestForecastDay:
    """Tests for the ForecastDay dataclass."""

    def test_frozen(self):
        fd = ForecastDay(
            date=datetime.date(2024, 1, 1),
            color=API_VALUE_BLUE,
            probability=90.0,
        )
        with pytest.raises(AttributeError):
            fd.color = API_VALUE_RED  # type: ignore[misc]

    def test_fields(self):
        fd = ForecastDay(
            date=datetime.date(2024, 1, 1),
            color=API_VALUE_RED,
            probability=75.5,
        )
        assert fd.date == datetime.date(2024, 1, 1)
        assert fd.color == API_VALUE_RED
        assert fd.probability == 75.5


class TestAsyncFetchOpendpeForecast:
    """Tests for async_fetch_opendpe_forecast."""

    @pytest.mark.asyncio
    async def test_success_normalizes_colors(self):
        data = [
            _make_api_entry(_future(2), "bleu", 90.0),
            _make_api_entry(_future(3), "blanc", 80.0),
            _make_api_entry(_future(4), "rouge", 70.0),
        ]
        result = await async_fetch_opendpe_forecast(
            _mock_session(data),
        )
        assert len(result) == 3
        assert result[0].color == API_VALUE_BLUE
        assert result[1].color == API_VALUE_WHITE
        assert result[2].color == API_VALUE_RED

    @pytest.mark.asyncio
    async def test_filters_past_dates(self):
        data = [
            _make_api_entry(_past(1), "bleu", 90.0),
            _make_api_entry(_today().isoformat(), "blanc", 85.0),
            _make_api_entry(_future(2), "rouge", 70.0),
        ]
        result = await async_fetch_opendpe_forecast(
            _mock_session(data),
        )
        assert len(result) == 1
        assert result[0].color == API_VALUE_RED

    @pytest.mark.asyncio
    async def test_unknown_color_skipped(self):
        data = [
            _make_api_entry(_future(2), "violet", 90.0),
            _make_api_entry(_future(3), "bleu", 80.0),
        ]
        result = await async_fetch_opendpe_forecast(
            _mock_session(data),
        )
        assert len(result) == 1
        assert result[0].color == API_VALUE_BLUE

    @pytest.mark.asyncio
    async def test_network_error(self):
        session = _mock_session(
            side_effect=aiohttp.ClientError("fail"),
        )
        with pytest.raises(aiohttp.ClientError):
            await async_fetch_opendpe_forecast(session)

    @pytest.mark.asyncio
    async def test_timeout_error(self):
        session = _mock_session(
            side_effect=TimeoutError("timeout"),
        )
        with pytest.raises(TimeoutError):
            await async_fetch_opendpe_forecast(session)

    @pytest.mark.asyncio
    async def test_invalid_json_key_error(self):
        data = [{"wrong_key": "value"}]
        with pytest.raises(KeyError):
            await async_fetch_opendpe_forecast(
                _mock_session(data),
            )

    @pytest.mark.asyncio
    async def test_empty_response(self):
        result = await async_fetch_opendpe_forecast(
            _mock_session([]),
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_probability_field(self):
        data = [_make_api_entry(_future(2), "bleu", 42.5)]
        result = await async_fetch_opendpe_forecast(
            _mock_session(data),
        )
        assert result[0].probability == 42.5

    @pytest.mark.asyncio
    async def test_case_insensitive_color(self):
        data = [_make_api_entry(_future(2), "BLEU", 90.0)]
        result = await async_fetch_opendpe_forecast(
            _mock_session(data),
        )
        assert len(result) == 1
        assert result[0].color == API_VALUE_BLUE

    @pytest.mark.asyncio
    async def test_invalid_probability_raises(self):
        data = [
            _make_api_entry(_future(2), "bleu", "not_a_number"),
        ]
        with pytest.raises(ValueError):
            await async_fetch_opendpe_forecast(
                _mock_session(data),
            )
