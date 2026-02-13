"""Tests for the TempoCoordinator and compute_wait_time."""

from __future__ import annotations

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.rtetempo.api.exceptions import RTETempoServerError
from custom_components.rtetempo.api.models import TempoData, TempoDay
from custom_components.rtetempo.const import FRANCE_TZ
from custom_components.rtetempo.tempo_coordinator import (
    TempoCoordinator,
    compute_wait_time,
)

# ── compute_wait_time ────────────────────────────────────────────────


class TestComputeWaitTime:
    """Tests for the standalone compute_wait_time function."""

    def test_no_data_end(self):
        now = datetime.datetime(2024, 1, 15, 12, 0, tzinfo=FRANCE_TZ)
        result = compute_wait_time(now, None)
        assert result == datetime.timedelta(minutes=10)

    def test_diff_2_days_past_confirmation(self):
        """Have next day color, past confirmation hour -> wait until tomorrow."""
        now = datetime.datetime(2024, 1, 15, 11, 0, tzinfo=FRANCE_TZ)
        data_end = datetime.datetime(2024, 1, 17, 0, 0, tzinfo=FRANCE_TZ)
        with patch(
            "custom_components.rtetempo.tempo_coordinator.random.randrange"
        ) as mock_rand:
            mock_rand.return_value = 70000
            result = compute_wait_time(now, data_end)
        assert result.total_seconds() > 0

    def test_diff_2_days_before_confirmation(self):
        """Have next day color but before confirmation hour."""
        now = datetime.datetime(2024, 1, 15, 8, 0, tzinfo=FRANCE_TZ)
        data_end = datetime.datetime(2024, 1, 17, 0, 0, tzinfo=FRANCE_TZ)
        with patch(
            "custom_components.rtetempo.tempo_coordinator.random.randrange"
        ) as mock_rand:
            mock_rand.return_value = 90000
            result = compute_wait_time(now, data_end)
        assert result.total_seconds() > 0

    def test_diff_1_day_before_6am(self):
        """No next day color, before 6 AM."""
        now = datetime.datetime(2024, 1, 15, 4, 0, tzinfo=FRANCE_TZ)
        data_end = datetime.datetime(2024, 1, 16, 0, 0, tzinfo=FRANCE_TZ)
        with patch(
            "custom_components.rtetempo.tempo_coordinator.random.randrange"
        ) as mock_rand:
            mock_rand.return_value = 8000
            result = compute_wait_time(now, data_end)
        assert result.total_seconds() > 0

    def test_diff_1_day_after_6am(self):
        """No next day color, after 6 AM -> retry soon (~30 min)."""
        now = datetime.datetime(2024, 1, 15, 10, 0, tzinfo=FRANCE_TZ)
        data_end = datetime.datetime(2024, 1, 16, 0, 0, tzinfo=FRANCE_TZ)
        with patch(
            "custom_components.rtetempo.tempo_coordinator.random.randrange"
        ) as mock_rand:
            mock_rand.return_value = 1500
            result = compute_wait_time(now, data_end)
        assert result.total_seconds() > 0
        assert result.total_seconds() < 7200

    def test_unexpected_diff(self):
        """Unexpected diff -> fallback ~1h."""
        now = datetime.datetime(2024, 1, 15, 10, 0, tzinfo=FRANCE_TZ)
        data_end = datetime.datetime(2024, 1, 15, 0, 0, tzinfo=FRANCE_TZ)
        with patch(
            "custom_components.rtetempo.tempo_coordinator.random.randrange"
        ) as mock_rand:
            mock_rand.return_value = 3000
            result = compute_wait_time(now, data_end)
        assert result.total_seconds() > 0


# ── TempoCoordinator ─────────────────────────────────────────────────


@pytest.fixture
def mock_hass():
    hass = MagicMock()
    hass.data = {}
    return hass


@pytest.fixture
def mock_client():
    return AsyncMock()


def _make_coordinator(mock_hass, mock_client):
    """Create a TempoCoordinator with frame helper patched."""
    with patch("homeassistant.helpers.frame.report_usage"):
        return TempoCoordinator(mock_hass, mock_client)


class TestTempoCoordinator:
    """Tests for the TempoCoordinator."""

    @pytest.mark.asyncio
    async def test_successful_fetch_updates_interval(self, mock_hass, mock_client):
        """Successful fetch sets dynamic interval."""
        data = TempoData(
            adjusted_days=[
                TempoDay(
                    start=datetime.datetime(2024, 1, 15, 6, 0, tzinfo=FRANCE_TZ),
                    end=datetime.datetime(2024, 1, 16, 6, 0, tzinfo=FRANCE_TZ),
                    value="BLUE",
                    updated=datetime.datetime(2024, 1, 15, 10, 0, tzinfo=FRANCE_TZ),
                )
            ],
            regular_days=[
                TempoDay(
                    start=datetime.date(2024, 1, 15),
                    end=datetime.date(2024, 1, 16),
                    value="BLUE",
                    updated=datetime.datetime(2024, 1, 15, 10, 0, tzinfo=FRANCE_TZ),
                )
            ],
            data_end=datetime.datetime(2024, 1, 17, 0, 0, tzinfo=FRANCE_TZ),
        )
        mock_client.async_get_tempo_data.return_value = data
        coordinator = _make_coordinator(mock_hass, mock_client)

        with patch(
            "custom_components.rtetempo.tempo_coordinator.random.randrange"
        ) as mock_rand:
            mock_rand.return_value = 70000
            result = await coordinator._async_update_data()

        assert result == data
        # Interval should have been updated from default
        assert coordinator.update_interval != datetime.timedelta(minutes=1)

    @pytest.mark.asyncio
    async def test_error_raises_update_failed(self, mock_hass, mock_client):
        """API error raises UpdateFailed and sets error interval."""
        mock_client.async_get_tempo_data.side_effect = RTETempoServerError(
            500, "Internal Server Error"
        )
        coordinator = _make_coordinator(mock_hass, mock_client)

        with pytest.raises(UpdateFailed, match="RTE Tempo API error"):
            await coordinator._async_update_data()

        assert coordinator.update_interval == datetime.timedelta(minutes=10)
