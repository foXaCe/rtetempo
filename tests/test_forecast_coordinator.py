"""Tests for forecast_coordinator.py."""

from __future__ import annotations

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.rtetempo.const import (
    API_VALUE_BLUE,
    DOMAIN,
    OPENDPE_UPDATE_INTERVAL,
)
from custom_components.rtetempo.forecast import ForecastDay
from custom_components.rtetempo.forecast_coordinator import ForecastCoordinator


@pytest.fixture
def coordinator():
    """Create a ForecastCoordinator with mocked dependencies."""
    hass = MagicMock()
    hass.async_create_task = MagicMock()
    with (
        patch(
            "custom_components.rtetempo.forecast_coordinator.async_get_clientsession",
        ) as mock_get_session,
        patch("homeassistant.helpers.frame.report_usage"),
    ):
        mock_get_session.return_value = AsyncMock(spec=aiohttp.ClientSession)
        coord = ForecastCoordinator(hass)
    return coord


class TestForecastCoordinatorInit:
    """Tests for ForecastCoordinator initialization."""

    def test_name(self, coordinator):
        assert coordinator.name == f"{DOMAIN}_opendpe_forecast"

    def test_update_interval(self, coordinator):
        assert coordinator.update_interval == OPENDPE_UPDATE_INTERVAL

    def test_session_set(self, coordinator):
        assert coordinator._session is not None


class TestForecastCoordinatorUpdate:
    """Tests for _async_update_data."""

    @pytest.mark.asyncio
    async def test_success(self, coordinator):
        sample = [
            ForecastDay(
                date=datetime.date(2025, 1, 10),
                color=API_VALUE_BLUE,
                probability=90.0,
            )
        ]
        with patch(
            "custom_components.rtetempo.forecast_coordinator.async_fetch_opendpe_forecast",
            new_callable=AsyncMock,
            return_value=sample,
        ):
            result = await coordinator._async_update_data()
        assert result == sample

    @pytest.mark.asyncio
    async def test_client_error(self, coordinator):
        with patch(
            "custom_components.rtetempo.forecast_coordinator.async_fetch_opendpe_forecast",
            new_callable=AsyncMock,
            side_effect=aiohttp.ClientError("connection failed"),
        ):
            with pytest.raises(UpdateFailed, match="Error communicating with OpenDPE"):
                await coordinator._async_update_data()

    @pytest.mark.asyncio
    async def test_timeout_error(self, coordinator):
        with patch(
            "custom_components.rtetempo.forecast_coordinator.async_fetch_opendpe_forecast",
            new_callable=AsyncMock,
            side_effect=TimeoutError("timed out"),
        ):
            with pytest.raises(UpdateFailed, match="Timeout fetching OpenDPE"):
                await coordinator._async_update_data()

    @pytest.mark.asyncio
    async def test_key_error(self, coordinator):
        with patch(
            "custom_components.rtetempo.forecast_coordinator.async_fetch_opendpe_forecast",
            new_callable=AsyncMock,
            side_effect=KeyError("missing_field"),
        ):
            with pytest.raises(UpdateFailed, match="Error parsing OpenDPE"):
                await coordinator._async_update_data()

    @pytest.mark.asyncio
    async def test_value_error(self, coordinator):
        with patch(
            "custom_components.rtetempo.forecast_coordinator.async_fetch_opendpe_forecast",
            new_callable=AsyncMock,
            side_effect=ValueError("bad data"),
        ):
            with pytest.raises(UpdateFailed, match="Error parsing OpenDPE"):
                await coordinator._async_update_data()
