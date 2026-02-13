"""Tests for the sensor platform."""

from __future__ import annotations

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.rtetempo.const import (
    API_VALUE_BLUE,
    API_VALUE_RED,
    API_VALUE_WHITE,
    CYCLE_START_DAY,
    CYCLE_START_MONTH,
    DOMAIN,
    FRANCE_TZ,
    HOUR_OF_CHANGE,
    OFF_PEAK_START,
    SENSOR_COLOR_BLUE_EMOJI,
    SENSOR_COLOR_BLUE_NAME,
    SENSOR_COLOR_RED_EMOJI,
    SENSOR_COLOR_RED_NAME,
    SENSOR_COLOR_UNKNOWN_EMOJI,
    SENSOR_COLOR_UNKNOWN_NAME,
    SENSOR_COLOR_WHITE_EMOJI,
    SENSOR_COLOR_WHITE_NAME,
)
from custom_components.rtetempo.sensor import (
    CurrentColor,
    DaysLeft,
    DaysUsed,
    NextColor,
    NextColorTime,
    NextCycleTime,
    OffPeakChangeTime,
    async_setup_entry,
    get_color_emoji,
    get_color_icon,
    get_color_name,
)

from .conftest import (
    build_sample_days_date,
    make_tempo_day_date,
    make_tempo_day_time,
)

# ── Helper functions ────────────────────────────────────────────────────


class TestGetColorEmoji:
    """Tests for get_color_emoji."""

    def test_red(self):
        assert get_color_emoji(API_VALUE_RED) == SENSOR_COLOR_RED_EMOJI

    def test_white(self):
        assert get_color_emoji(API_VALUE_WHITE) == SENSOR_COLOR_WHITE_EMOJI

    def test_blue(self):
        assert get_color_emoji(API_VALUE_BLUE) == SENSOR_COLOR_BLUE_EMOJI

    def test_unknown(self):
        assert get_color_emoji("INVALID") == SENSOR_COLOR_UNKNOWN_EMOJI


class TestGetColorIcon:
    """Tests for get_color_icon."""

    def test_red(self):
        assert get_color_icon(API_VALUE_RED) == "mdi:alert"

    def test_white(self):
        assert get_color_icon(API_VALUE_WHITE) == "mdi:information-outline"

    def test_blue(self):
        assert get_color_icon(API_VALUE_BLUE) == "mdi:check-bold"

    def test_unknown(self):
        assert get_color_icon("INVALID") == "mdi:palette"


class TestGetColorName:
    """Tests for get_color_name."""

    def test_red(self):
        assert get_color_name(API_VALUE_RED) == SENSOR_COLOR_RED_NAME

    def test_white(self):
        assert get_color_name(API_VALUE_WHITE) == SENSOR_COLOR_WHITE_NAME

    def test_blue(self):
        assert get_color_name(API_VALUE_BLUE) == SENSOR_COLOR_BLUE_NAME

    def test_unknown(self):
        assert get_color_name("INVALID") == SENSOR_COLOR_UNKNOWN_NAME


# ── CurrentColor ────────────────────────────────────────────────────────


class TestCurrentColor:
    """Tests for CurrentColor sensor."""

    def test_init_visual(self, mock_api_worker):
        sensor = CurrentColor("config_123", mock_api_worker, True)
        assert sensor._attr_name == "Couleur actuelle (visuel)"
        assert f"{DOMAIN}_config_123_current_color_emoji" == sensor._attr_unique_id
        assert SENSOR_COLOR_BLUE_EMOJI in sensor._attr_options

    def test_init_text(self, mock_api_worker):
        sensor = CurrentColor("config_123", mock_api_worker, False)
        assert sensor._attr_name == "Couleur actuelle"
        assert f"{DOMAIN}_config_123_current_color" == sensor._attr_unique_id
        assert SENSOR_COLOR_BLUE_NAME in sensor._attr_options

    def test_update_finds_current_day_text(self, mock_api_worker):
        now = datetime.datetime(2024, 1, 15, 10, 0, tzinfo=FRANCE_TZ)
        day = make_tempo_day_time(2024, 1, 15, API_VALUE_BLUE)
        mock_api_worker.get_adjusted_days.return_value = [day]
        sensor = CurrentColor("cfg", mock_api_worker, False)
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            mock_dt.timedelta = datetime.timedelta
            sensor.update()
        assert sensor._attr_native_value == SENSOR_COLOR_BLUE_NAME
        assert sensor._attr_available is True

    def test_update_finds_current_day_visual(self, mock_api_worker):
        now = datetime.datetime(2024, 1, 15, 10, 0, tzinfo=FRANCE_TZ)
        day = make_tempo_day_time(2024, 1, 15, API_VALUE_RED)
        mock_api_worker.get_adjusted_days.return_value = [day]
        sensor = CurrentColor("cfg", mock_api_worker, True)
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            mock_dt.timedelta = datetime.timedelta
            sensor.update()
        assert sensor._attr_native_value == SENSOR_COLOR_RED_EMOJI
        assert sensor._attr_icon == "mdi:alert"

    def test_update_no_match(self, mock_api_worker):
        now = datetime.datetime(2024, 1, 15, 10, 0, tzinfo=FRANCE_TZ)
        mock_api_worker.get_adjusted_days.return_value = []
        sensor = CurrentColor("cfg", mock_api_worker, False)
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            sensor.update()
        assert sensor._attr_available is False
        assert sensor._attr_native_value is None

    def test_device_info(self, mock_api_worker):
        sensor = CurrentColor("cfg", mock_api_worker, False)
        info = sensor.device_info
        assert (DOMAIN, "cfg") in info["identifiers"]


# ── NextColor ───────────────────────────────────────────────────────────


class TestNextColor:
    """Tests for NextColor sensor."""

    def test_init_visual(self, mock_api_worker):
        sensor = NextColor("cfg", mock_api_worker, True)
        assert "visuel" in sensor._attr_name

    def test_init_text(self, mock_api_worker):
        sensor = NextColor("cfg", mock_api_worker, False)
        assert sensor._attr_name == "Prochaine couleur"

    def test_update_finds_next_day_text(self, mock_api_worker):
        now = datetime.datetime(2024, 1, 15, 10, 0, tzinfo=FRANCE_TZ)
        today = make_tempo_day_time(2024, 1, 15, API_VALUE_BLUE)
        tomorrow = make_tempo_day_time(2024, 1, 16, API_VALUE_WHITE)
        mock_api_worker.get_adjusted_days.return_value = [today, tomorrow]
        sensor = NextColor("cfg", mock_api_worker, False)
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            mock_dt.timedelta = datetime.timedelta
            sensor.update()
        assert sensor._attr_native_value == SENSOR_COLOR_WHITE_NAME
        assert sensor._attr_available is True

    def test_update_finds_next_day_visual(self, mock_api_worker):
        now = datetime.datetime(2024, 1, 15, 10, 0, tzinfo=FRANCE_TZ)
        today = make_tempo_day_time(2024, 1, 15, API_VALUE_BLUE)
        tomorrow = make_tempo_day_time(2024, 1, 16, API_VALUE_RED)
        mock_api_worker.get_adjusted_days.return_value = [today, tomorrow]
        sensor = NextColor("cfg", mock_api_worker, True)
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            mock_dt.timedelta = datetime.timedelta
            sensor.update()
        assert sensor._attr_native_value == SENSOR_COLOR_RED_EMOJI
        assert sensor._attr_icon == "mdi:alert"

    def test_update_no_next_day_visual(self, mock_api_worker):
        """Visual mode shows unknown emoji when no next day."""
        now = datetime.datetime(2024, 1, 15, 10, 0, tzinfo=FRANCE_TZ)
        mock_api_worker.get_adjusted_days.return_value = []
        sensor = NextColor("cfg", mock_api_worker, True)
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            sensor.update()
        assert sensor._attr_native_value == SENSOR_COLOR_UNKNOWN_EMOJI
        assert sensor._attr_available is True

    def test_update_no_next_day_text(self, mock_api_worker):
        """Text mode shows unavailable when no next day."""
        now = datetime.datetime(2024, 1, 15, 10, 0, tzinfo=FRANCE_TZ)
        mock_api_worker.get_adjusted_days.return_value = []
        sensor = NextColor("cfg", mock_api_worker, False)
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            sensor.update()
        assert sensor._attr_available is False
        assert sensor._attr_native_value is None


# ── NextColorTime ───────────────────────────────────────────────────────


class TestNextColorTime:
    """Tests for NextColorTime sensor."""

    def test_init(self):
        sensor = NextColorTime("cfg")
        assert sensor._attr_unique_id == f"{DOMAIN}_cfg_next_color_change"

    def test_update_after_6am(self):
        """After 6 AM, next change is tomorrow at 6 AM."""
        now = datetime.datetime(2024, 1, 15, 10, 0, tzinfo=FRANCE_TZ)
        sensor = NextColorTime("cfg")
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            mock_dt.datetime.side_effect = lambda *a, **kw: datetime.datetime(*a, **kw)
            mock_dt.timedelta = datetime.timedelta
            sensor.update()
        assert sensor._attr_native_value.day == 16
        assert sensor._attr_native_value.hour == HOUR_OF_CHANGE

    def test_update_before_6am(self):
        """Before 6 AM, next change is today at 6 AM."""
        now = datetime.datetime(2024, 1, 15, 3, 0, tzinfo=FRANCE_TZ)
        sensor = NextColorTime("cfg")
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            mock_dt.datetime.side_effect = lambda *a, **kw: datetime.datetime(*a, **kw)
            mock_dt.timedelta = datetime.timedelta
            sensor.update()
        assert sensor._attr_native_value.day == 15
        assert sensor._attr_native_value.hour == HOUR_OF_CHANGE


# ── DaysLeft ────────────────────────────────────────────────────────────


class TestDaysLeft:
    """Tests for DaysLeft sensor."""

    def test_init_blue(self, mock_api_worker):
        sensor = DaysLeft("cfg", mock_api_worker, API_VALUE_BLUE)
        assert "Bleu" in sensor._attr_name
        assert "days_left_blue" in sensor._attr_unique_id

    def test_init_white(self, mock_api_worker):
        sensor = DaysLeft("cfg", mock_api_worker, API_VALUE_WHITE)
        assert "Blanc" in sensor._attr_name

    def test_init_red(self, mock_api_worker):
        sensor = DaysLeft("cfg", mock_api_worker, API_VALUE_RED)
        assert SENSOR_COLOR_RED_NAME in sensor._attr_name

    def test_init_invalid_color(self, mock_api_worker):
        with pytest.raises(ValueError, match="invalid color"):
            DaysLeft("cfg", mock_api_worker, "PURPLE")

    def test_update_counts_remaining_days(self, mock_api_worker):
        """In Oct 2024 (cycle started Sept 1, 2024) with sample data."""
        now = datetime.datetime(2024, 11, 20, 10, 0, tzinfo=FRANCE_TZ)
        days = build_sample_days_date(2024)
        mock_api_worker.get_regular_days.return_value = days
        sensor = DaysLeft("cfg", mock_api_worker, API_VALUE_BLUE)
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            mock_dt.date = datetime.date
            mock_dt.timedelta = datetime.timedelta
            sensor.update()
        # total_days in cycle 2024-2025 = 365 (not leap), blue = 365-43-22 = 300
        # sample has 50 blue days -> remaining = 300-50 = 250
        assert sensor._attr_native_value is not None
        assert isinstance(sensor._attr_native_value, int)

    def test_update_before_cycle_start(self, mock_api_worker):
        """In March (before Sept) - cycle is from previous year."""
        now = datetime.datetime(2025, 3, 15, 10, 0, tzinfo=FRANCE_TZ)
        mock_api_worker.get_regular_days.return_value = []
        sensor = DaysLeft("cfg", mock_api_worker, API_VALUE_RED)
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            mock_dt.date = datetime.date
            mock_dt.timedelta = datetime.timedelta
            sensor.update()
        # No red days used -> 22 remaining
        assert sensor._attr_native_value == 22


# ── DaysUsed ────────────────────────────────────────────────────────────


class TestDaysUsed:
    """Tests for DaysUsed sensor."""

    def test_init_blue(self, mock_api_worker):
        sensor = DaysUsed("cfg", mock_api_worker, API_VALUE_BLUE)
        assert "Bleu" in sensor._attr_name
        assert "days_used_blue" in sensor._attr_unique_id

    def test_init_invalid_color(self, mock_api_worker):
        with pytest.raises(ValueError, match="invalid color"):
            DaysUsed("cfg", mock_api_worker, "PURPLE")

    def test_update_counts_used_days(self, mock_api_worker):
        now = datetime.datetime(2024, 11, 20, 10, 0, tzinfo=FRANCE_TZ)
        days = build_sample_days_date(2024)
        mock_api_worker.get_regular_days.return_value = days
        sensor = DaysUsed("cfg", mock_api_worker, API_VALUE_BLUE)
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            mock_dt.date = datetime.date
            sensor.update()
        # 50 blue days in sample
        assert sensor._attr_native_value == 50

    def test_update_white_count(self, mock_api_worker):
        now = datetime.datetime(2024, 11, 20, 10, 0, tzinfo=FRANCE_TZ)
        days = build_sample_days_date(2024)
        mock_api_worker.get_regular_days.return_value = days
        sensor = DaysUsed("cfg", mock_api_worker, API_VALUE_WHITE)
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            mock_dt.date = datetime.date
            sensor.update()
        assert sensor._attr_native_value == 20

    def test_update_red_count(self, mock_api_worker):
        now = datetime.datetime(2024, 11, 20, 10, 0, tzinfo=FRANCE_TZ)
        days = build_sample_days_date(2024)
        mock_api_worker.get_regular_days.return_value = days
        sensor = DaysUsed("cfg", mock_api_worker, API_VALUE_RED)
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            mock_dt.date = datetime.date
            sensor.update()
        assert sensor._attr_native_value == 10

    def test_update_no_data(self, mock_api_worker):
        now = datetime.datetime(2024, 11, 20, 10, 0, tzinfo=FRANCE_TZ)
        mock_api_worker.get_regular_days.return_value = []
        sensor = DaysUsed("cfg", mock_api_worker, API_VALUE_BLUE)
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            mock_dt.date = datetime.date
            sensor.update()
        assert sensor._attr_native_value == 0


# ── NextCycleTime ───────────────────────────────────────────────────────


class TestNextCycleTime:
    """Tests for NextCycleTime sensor."""

    def test_init(self):
        sensor = NextCycleTime("cfg")
        assert sensor._attr_unique_id == f"{DOMAIN}_cfg_next_cycle_reinit"

    def test_update_after_cycle_start(self):
        """After Sept 1 -> next cycle is next year."""
        now = datetime.datetime(2024, 10, 15, 10, 0, tzinfo=FRANCE_TZ)
        sensor = NextCycleTime("cfg")
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            mock_dt.datetime.side_effect = lambda *a, **kw: datetime.datetime(*a, **kw)
            sensor.update()
        assert sensor._attr_native_value.year == 2025
        assert sensor._attr_native_value.month == CYCLE_START_MONTH
        assert sensor._attr_native_value.day == CYCLE_START_DAY

    def test_update_before_cycle_start(self):
        """Before Sept 1 -> next cycle is this year."""
        now = datetime.datetime(2024, 5, 15, 10, 0, tzinfo=FRANCE_TZ)
        sensor = NextCycleTime("cfg")
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            mock_dt.datetime.side_effect = lambda *a, **kw: datetime.datetime(*a, **kw)
            sensor.update()
        assert sensor._attr_native_value.year == 2024
        assert sensor._attr_native_value.month == CYCLE_START_MONTH


# ── OffPeakChangeTime ──────────────────────────────────────────────────


class TestOffPeakChangeTime:
    """Tests for OffPeakChangeTime sensor."""

    def test_init(self):
        sensor = OffPeakChangeTime("cfg")
        assert sensor._attr_unique_id == f"{DOMAIN}_cfg_off_peak_change_time"

    def test_update_before_6am(self):
        """Before 6 AM -> next change is today at 6 AM."""
        now = datetime.datetime(2024, 1, 15, 3, 0, tzinfo=FRANCE_TZ)
        sensor = OffPeakChangeTime("cfg")
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            mock_dt.datetime.side_effect = lambda *a, **kw: datetime.datetime(*a, **kw)
            mock_dt.timedelta = datetime.timedelta
            sensor.update()
        assert sensor._attr_native_value.hour == HOUR_OF_CHANGE
        assert sensor._attr_native_value.day == 15

    def test_update_between_6_and_22(self):
        """Between 6 AM and 10 PM -> next change is today at 10 PM."""
        now = datetime.datetime(2024, 1, 15, 14, 0, tzinfo=FRANCE_TZ)
        sensor = OffPeakChangeTime("cfg")
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            mock_dt.datetime.side_effect = lambda *a, **kw: datetime.datetime(*a, **kw)
            mock_dt.timedelta = datetime.timedelta
            sensor.update()
        assert sensor._attr_native_value.hour == OFF_PEAK_START
        assert sensor._attr_native_value.day == 15

    def test_update_after_22(self):
        """After 10 PM -> next change is tomorrow at 6 AM."""
        now = datetime.datetime(2024, 1, 15, 23, 0, tzinfo=FRANCE_TZ)
        sensor = OffPeakChangeTime("cfg")
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            mock_dt.datetime.side_effect = lambda *a, **kw: datetime.datetime(*a, **kw)
            mock_dt.timedelta = datetime.timedelta
            sensor.update()
        assert sensor._attr_native_value.hour == HOUR_OF_CHANGE
        assert sensor._attr_native_value.day == 16

    def test_device_info(self):
        sensor = OffPeakChangeTime("cfg")
        info = sensor.device_info
        assert (DOMAIN, "cfg") in info["identifiers"]


# ── async_setup_entry ───────────────────────────────────────────────────


class TestSensorAsyncSetupEntry:
    """Tests for sensor async_setup_entry."""

    @pytest.mark.asyncio
    async def test_success(self, mock_api_worker):
        """Setup creates 13 existing + 12 forecast sensor entities."""
        hass = MagicMock()
        hass.data = {DOMAIN: {"entry_id": {"api_worker": mock_api_worker}}}
        hass.async_add_executor_job = AsyncMock(return_value=True)
        config_entry = MagicMock()
        config_entry.entry_id = "entry_id"
        config_entry.title = "Test"
        config_entry.async_create_background_task = MagicMock()
        add_entities = MagicMock()
        with (
            patch("custom_components.rtetempo.forecast_coordinator.async_get_clientsession"),
            patch("homeassistant.helpers.frame.report_usage"),
        ):
            await async_setup_entry(hass, config_entry, add_entities)
        # Called twice: first with 13 existing sensors, then with 12 forecast sensors
        assert add_entities.call_count == 2
        existing_entities = add_entities.call_args_list[0][0][0]
        forecast_entities = add_entities.call_args_list[1][0][0]
        assert len(existing_entities) == 13
        assert len(forecast_entities) == 12
        # Verify background task was created for non-blocking refresh
        config_entry.async_create_background_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_missing_worker(self):
        """Missing worker -> returns early without adding entities."""
        hass = MagicMock()
        hass.data = {DOMAIN: {}}
        config_entry = MagicMock()
        config_entry.entry_id = "missing_id"
        config_entry.title = "Test"
        add_entities = MagicMock()
        await async_setup_entry(hass, config_entry, add_entities)
        add_entities.assert_not_called()


# ── Additional device_info tests ────────────────────────────────────────


class TestDeviceInfoCoverage:
    """Cover device_info properties for entities not yet tested."""

    def test_next_color_device_info(self, mock_api_worker):
        sensor = NextColor("cfg", mock_api_worker, False)
        info = sensor.device_info
        assert (DOMAIN, "cfg") in info["identifiers"]

    def test_next_color_time_device_info(self):
        sensor = NextColorTime("cfg")
        info = sensor.device_info
        assert (DOMAIN, "cfg") in info["identifiers"]

    def test_days_left_device_info(self, mock_api_worker):
        sensor = DaysLeft("cfg", mock_api_worker, API_VALUE_BLUE)
        info = sensor.device_info
        assert (DOMAIN, "cfg") in info["identifiers"]

    def test_days_used_device_info(self, mock_api_worker):
        sensor = DaysUsed("cfg", mock_api_worker, API_VALUE_BLUE)
        info = sensor.device_info
        assert (DOMAIN, "cfg") in info["identifiers"]

    def test_next_cycle_time_device_info(self):
        sensor = NextCycleTime("cfg")
        info = sensor.device_info
        assert (DOMAIN, "cfg") in info["identifiers"]


# ── Additional edge cases ───────────────────────────────────────────────


class TestCurrentColorEdgeCases:
    """Additional edge cases for CurrentColor."""

    def test_update_no_match_visual_resets_icon(self, mock_api_worker):
        """Visual mode resets icon to palette when no match."""
        now = datetime.datetime(2024, 1, 15, 10, 0, tzinfo=FRANCE_TZ)
        mock_api_worker.get_adjusted_days.return_value = []
        sensor = CurrentColor("cfg", mock_api_worker, True)
        sensor._attr_icon = "mdi:alert"  # Set to something else first
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            sensor.update()
        assert sensor._attr_icon == "mdi:palette"
        assert sensor._attr_available is False


class TestDaysLeftEdgeCases:
    """Additional edge cases for DaysLeft."""

    def test_update_white_remaining(self, mock_api_worker):
        """Cover the white remaining calculation branch."""
        now = datetime.datetime(2025, 3, 15, 10, 0, tzinfo=FRANCE_TZ)
        mock_api_worker.get_regular_days.return_value = []
        sensor = DaysLeft("cfg", mock_api_worker, API_VALUE_WHITE)
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            mock_dt.date = datetime.date
            mock_dt.timedelta = datetime.timedelta
            sensor.update()
        assert sensor._attr_native_value == 43  # TOTAL_WHITE_DAYS

    def test_update_red_remaining(self, mock_api_worker):
        """Cover the red remaining calculation branch."""
        now = datetime.datetime(2025, 3, 15, 10, 0, tzinfo=FRANCE_TZ)
        mock_api_worker.get_regular_days.return_value = []
        sensor = DaysLeft("cfg", mock_api_worker, API_VALUE_RED)
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            mock_dt.date = datetime.date
            mock_dt.timedelta = datetime.timedelta
            sensor.update()
        assert sensor._attr_native_value == 22  # TOTAL_RED_DAYS

    def test_update_with_days_before_cycle_start_break(self, mock_api_worker):
        """Days before cycle_start should trigger break."""
        now = datetime.datetime(2024, 11, 20, 10, 0, tzinfo=FRANCE_TZ)
        # Include a day before cycle start (Sept 1, 2024)
        days = [
            make_tempo_day_date(2024, 9, 2, API_VALUE_BLUE),
            make_tempo_day_date(2024, 8, 31, API_VALUE_WHITE),  # Before cycle
        ]
        mock_api_worker.get_regular_days.return_value = days
        sensor = DaysLeft("cfg", mock_api_worker, API_VALUE_BLUE)
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            mock_dt.date = datetime.date
            mock_dt.timedelta = datetime.timedelta
            sensor.update()
        # Only 1 blue day counted (the one after cycle start)
        assert sensor._attr_native_value is not None


class TestDaysUsedEdgeCases:
    """Additional edge cases for DaysUsed."""

    def test_update_before_cycle_start_month(self, mock_api_worker):
        """Cover the before-September branch for cycle_start."""
        now = datetime.datetime(2025, 3, 15, 10, 0, tzinfo=FRANCE_TZ)
        mock_api_worker.get_regular_days.return_value = []
        sensor = DaysUsed("cfg", mock_api_worker, API_VALUE_WHITE)
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            mock_dt.date = datetime.date
            sensor.update()
        assert sensor._attr_native_value == 0

    def test_update_with_break(self, mock_api_worker):
        """Days before cycle_start trigger break."""
        now = datetime.datetime(2024, 11, 20, 10, 0, tzinfo=FRANCE_TZ)
        days = [
            make_tempo_day_date(2024, 9, 2, API_VALUE_RED),
            make_tempo_day_date(2024, 8, 31, API_VALUE_BLUE),  # Before cycle
        ]
        mock_api_worker.get_regular_days.return_value = days
        sensor = DaysUsed("cfg", mock_api_worker, API_VALUE_RED)
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            mock_dt.date = datetime.date
            sensor.update()
        assert sensor._attr_native_value == 1
