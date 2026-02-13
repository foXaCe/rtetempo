"""Tests for the sensor platform."""

from __future__ import annotations

import datetime
from unittest.mock import MagicMock, patch

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
    make_tempo_data,
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

    def test_init_visual(self, mock_coordinator):
        sensor = CurrentColor(mock_coordinator, "config_123", True)
        assert sensor._attr_name == "Couleur actuelle (visuel)"
        assert f"{DOMAIN}_config_123_current_color_emoji" == sensor._attr_unique_id
        assert SENSOR_COLOR_BLUE_EMOJI in sensor._attr_options

    def test_init_text(self, mock_coordinator):
        sensor = CurrentColor(mock_coordinator, "config_123", False)
        assert sensor._attr_name == "Couleur actuelle"
        assert f"{DOMAIN}_config_123_current_color" == sensor._attr_unique_id
        assert SENSOR_COLOR_BLUE_NAME in sensor._attr_options

    def test_native_value_finds_current_day_text(self, mock_coordinator):
        now = datetime.datetime(2024, 1, 15, 10, 0, tzinfo=FRANCE_TZ)
        day = make_tempo_day_time(2024, 1, 15, API_VALUE_BLUE)
        mock_coordinator.data = make_tempo_data(adjusted_days=[day])
        sensor = CurrentColor(mock_coordinator, "cfg", False)
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            mock_dt.timedelta = datetime.timedelta
            value = sensor.native_value
        assert value == SENSOR_COLOR_BLUE_NAME
        assert sensor._attr_available is True

    def test_native_value_finds_current_day_visual(self, mock_coordinator):
        now = datetime.datetime(2024, 1, 15, 10, 0, tzinfo=FRANCE_TZ)
        day = make_tempo_day_time(2024, 1, 15, API_VALUE_RED)
        mock_coordinator.data = make_tempo_data(adjusted_days=[day])
        sensor = CurrentColor(mock_coordinator, "cfg", True)
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            mock_dt.timedelta = datetime.timedelta
            value = sensor.native_value
        assert value == SENSOR_COLOR_RED_EMOJI
        assert sensor._attr_icon == "mdi:alert"

    def test_native_value_no_match(self, mock_coordinator):
        now = datetime.datetime(2024, 1, 15, 10, 0, tzinfo=FRANCE_TZ)
        mock_coordinator.data = make_tempo_data(adjusted_days=[])
        sensor = CurrentColor(mock_coordinator, "cfg", False)
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            value = sensor.native_value
        assert sensor._attr_available is False
        assert value is None

    def test_device_info(self, mock_coordinator):
        sensor = CurrentColor(mock_coordinator, "cfg", False)
        info = sensor.device_info
        assert (DOMAIN, "cfg") in info["identifiers"]

    def test_native_value_no_match_visual_resets_icon(self, mock_coordinator):
        now = datetime.datetime(2024, 1, 15, 10, 0, tzinfo=FRANCE_TZ)
        mock_coordinator.data = make_tempo_data(adjusted_days=[])
        sensor = CurrentColor(mock_coordinator, "cfg", True)
        sensor._attr_icon = "mdi:alert"
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            _ = sensor.native_value
        assert sensor._attr_icon == "mdi:palette"
        assert sensor._attr_available is False


# ── NextColor ───────────────────────────────────────────────────────────


class TestNextColor:
    """Tests for NextColor sensor."""

    def test_init_visual(self, mock_coordinator):
        sensor = NextColor(mock_coordinator, "cfg", True)
        assert "visuel" in sensor._attr_name

    def test_init_text(self, mock_coordinator):
        sensor = NextColor(mock_coordinator, "cfg", False)
        assert sensor._attr_name == "Prochaine couleur"

    def test_native_value_finds_next_day_text(self, mock_coordinator):
        now = datetime.datetime(2024, 1, 15, 10, 0, tzinfo=FRANCE_TZ)
        today = make_tempo_day_time(2024, 1, 15, API_VALUE_BLUE)
        tomorrow = make_tempo_day_time(2024, 1, 16, API_VALUE_WHITE)
        mock_coordinator.data = make_tempo_data(adjusted_days=[today, tomorrow])
        sensor = NextColor(mock_coordinator, "cfg", False)
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            mock_dt.timedelta = datetime.timedelta
            value = sensor.native_value
        assert value == SENSOR_COLOR_WHITE_NAME
        assert sensor._attr_available is True

    def test_native_value_finds_next_day_visual(self, mock_coordinator):
        now = datetime.datetime(2024, 1, 15, 10, 0, tzinfo=FRANCE_TZ)
        today = make_tempo_day_time(2024, 1, 15, API_VALUE_BLUE)
        tomorrow = make_tempo_day_time(2024, 1, 16, API_VALUE_RED)
        mock_coordinator.data = make_tempo_data(adjusted_days=[today, tomorrow])
        sensor = NextColor(mock_coordinator, "cfg", True)
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            mock_dt.timedelta = datetime.timedelta
            value = sensor.native_value
        assert value == SENSOR_COLOR_RED_EMOJI
        assert sensor._attr_icon == "mdi:alert"

    def test_native_value_no_next_day_visual(self, mock_coordinator):
        now = datetime.datetime(2024, 1, 15, 10, 0, tzinfo=FRANCE_TZ)
        mock_coordinator.data = make_tempo_data(adjusted_days=[])
        sensor = NextColor(mock_coordinator, "cfg", True)
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            value = sensor.native_value
        assert value == SENSOR_COLOR_UNKNOWN_EMOJI
        assert sensor._attr_available is True

    def test_native_value_no_next_day_text(self, mock_coordinator):
        now = datetime.datetime(2024, 1, 15, 10, 0, tzinfo=FRANCE_TZ)
        mock_coordinator.data = make_tempo_data(adjusted_days=[])
        sensor = NextColor(mock_coordinator, "cfg", False)
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            value = sensor.native_value
        assert sensor._attr_available is False
        assert value is None


# ── NextColorTime ───────────────────────────────────────────────────────


class TestNextColorTime:
    """Tests for NextColorTime sensor."""

    def test_init(self):
        sensor = NextColorTime("cfg")
        assert sensor._attr_unique_id == f"{DOMAIN}_cfg_next_color_change"

    def test_update_after_6am(self):
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
        now = datetime.datetime(2024, 1, 15, 3, 0, tzinfo=FRANCE_TZ)
        sensor = NextColorTime("cfg")
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            mock_dt.datetime.side_effect = lambda *a, **kw: datetime.datetime(*a, **kw)
            mock_dt.timedelta = datetime.timedelta
            sensor.update()
        assert sensor._attr_native_value.day == 15
        assert sensor._attr_native_value.hour == HOUR_OF_CHANGE


# ── DaysLeft ────────────────────────────────────────────────────────


class TestDaysLeft:
    """Tests for DaysLeft sensor."""

    def test_init_blue(self, mock_coordinator):
        sensor = DaysLeft(mock_coordinator, "cfg", API_VALUE_BLUE)
        assert "Bleu" in sensor._attr_name
        assert "days_left_blue" in sensor._attr_unique_id

    def test_init_white(self, mock_coordinator):
        sensor = DaysLeft(mock_coordinator, "cfg", API_VALUE_WHITE)
        assert "Blanc" in sensor._attr_name

    def test_init_red(self, mock_coordinator):
        sensor = DaysLeft(mock_coordinator, "cfg", API_VALUE_RED)
        assert SENSOR_COLOR_RED_NAME in sensor._attr_name

    def test_init_invalid_color(self, mock_coordinator):
        with pytest.raises(ValueError, match="invalid color"):
            DaysLeft(mock_coordinator, "cfg", "PURPLE")

    def test_native_value_counts_remaining_days(self, mock_coordinator):
        now = datetime.datetime(2024, 11, 20, 10, 0, tzinfo=FRANCE_TZ)
        days = build_sample_days_date(2024)
        mock_coordinator.data = make_tempo_data(regular_days=days)
        sensor = DaysLeft(mock_coordinator, "cfg", API_VALUE_BLUE)
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            mock_dt.date = datetime.date
            mock_dt.timedelta = datetime.timedelta
            value = sensor.native_value
        assert value is not None
        assert isinstance(value, int)

    def test_native_value_before_cycle_start(self, mock_coordinator):
        now = datetime.datetime(2025, 3, 15, 10, 0, tzinfo=FRANCE_TZ)
        mock_coordinator.data = make_tempo_data(regular_days=[])
        sensor = DaysLeft(mock_coordinator, "cfg", API_VALUE_RED)
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            mock_dt.date = datetime.date
            mock_dt.timedelta = datetime.timedelta
            value = sensor.native_value
        assert value == 22

    def test_native_value_white_remaining(self, mock_coordinator):
        now = datetime.datetime(2025, 3, 15, 10, 0, tzinfo=FRANCE_TZ)
        mock_coordinator.data = make_tempo_data(regular_days=[])
        sensor = DaysLeft(mock_coordinator, "cfg", API_VALUE_WHITE)
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            mock_dt.date = datetime.date
            mock_dt.timedelta = datetime.timedelta
            value = sensor.native_value
        assert value == 43

    def test_native_value_with_days_before_cycle(self, mock_coordinator):
        now = datetime.datetime(2024, 11, 20, 10, 0, tzinfo=FRANCE_TZ)
        days = [
            make_tempo_day_date(2024, 9, 2, API_VALUE_BLUE),
            make_tempo_day_date(2024, 8, 31, API_VALUE_WHITE),
        ]
        mock_coordinator.data = make_tempo_data(regular_days=days)
        sensor = DaysLeft(mock_coordinator, "cfg", API_VALUE_BLUE)
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            mock_dt.date = datetime.date
            mock_dt.timedelta = datetime.timedelta
            value = sensor.native_value
        assert value is not None


# ── DaysUsed ────────────────────────────────────────────────────────


class TestDaysUsed:
    """Tests for DaysUsed sensor."""

    def test_init_blue(self, mock_coordinator):
        sensor = DaysUsed(mock_coordinator, "cfg", API_VALUE_BLUE)
        assert "Bleu" in sensor._attr_name
        assert "days_used_blue" in sensor._attr_unique_id

    def test_init_invalid_color(self, mock_coordinator):
        with pytest.raises(ValueError, match="invalid color"):
            DaysUsed(mock_coordinator, "cfg", "PURPLE")

    def test_native_value_counts_used_days(self, mock_coordinator):
        now = datetime.datetime(2024, 11, 20, 10, 0, tzinfo=FRANCE_TZ)
        days = build_sample_days_date(2024)
        mock_coordinator.data = make_tempo_data(regular_days=days)
        sensor = DaysUsed(mock_coordinator, "cfg", API_VALUE_BLUE)
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            mock_dt.date = datetime.date
            value = sensor.native_value
        assert value == 50

    def test_native_value_white_count(self, mock_coordinator):
        now = datetime.datetime(2024, 11, 20, 10, 0, tzinfo=FRANCE_TZ)
        days = build_sample_days_date(2024)
        mock_coordinator.data = make_tempo_data(regular_days=days)
        sensor = DaysUsed(mock_coordinator, "cfg", API_VALUE_WHITE)
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            mock_dt.date = datetime.date
            value = sensor.native_value
        assert value == 20

    def test_native_value_red_count(self, mock_coordinator):
        now = datetime.datetime(2024, 11, 20, 10, 0, tzinfo=FRANCE_TZ)
        days = build_sample_days_date(2024)
        mock_coordinator.data = make_tempo_data(regular_days=days)
        sensor = DaysUsed(mock_coordinator, "cfg", API_VALUE_RED)
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            mock_dt.date = datetime.date
            value = sensor.native_value
        assert value == 10

    def test_native_value_no_data(self, mock_coordinator):
        now = datetime.datetime(2024, 11, 20, 10, 0, tzinfo=FRANCE_TZ)
        mock_coordinator.data = make_tempo_data(regular_days=[])
        sensor = DaysUsed(mock_coordinator, "cfg", API_VALUE_BLUE)
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            mock_dt.date = datetime.date
            value = sensor.native_value
        assert value == 0

    def test_native_value_before_cycle_start_month(self, mock_coordinator):
        now = datetime.datetime(2025, 3, 15, 10, 0, tzinfo=FRANCE_TZ)
        mock_coordinator.data = make_tempo_data(regular_days=[])
        sensor = DaysUsed(mock_coordinator, "cfg", API_VALUE_WHITE)
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            mock_dt.date = datetime.date
            value = sensor.native_value
        assert value == 0

    def test_native_value_with_break(self, mock_coordinator):
        now = datetime.datetime(2024, 11, 20, 10, 0, tzinfo=FRANCE_TZ)
        days = [
            make_tempo_day_date(2024, 9, 2, API_VALUE_RED),
            make_tempo_day_date(2024, 8, 31, API_VALUE_BLUE),
        ]
        mock_coordinator.data = make_tempo_data(regular_days=days)
        sensor = DaysUsed(mock_coordinator, "cfg", API_VALUE_RED)
        with patch("custom_components.rtetempo.sensor.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = now
            mock_dt.date = datetime.date
            value = sensor.native_value
        assert value == 1


# ── NextCycleTime ───────────────────────────────────────────────────────


class TestNextCycleTime:
    """Tests for NextCycleTime sensor."""

    def test_init(self):
        sensor = NextCycleTime("cfg")
        assert sensor._attr_unique_id == f"{DOMAIN}_cfg_next_cycle_reinit"

    def test_update_after_cycle_start(self):
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
    async def test_success(self, mock_coordinator):
        """Setup creates 13 existing + 12 forecast sensor entities."""
        hass = MagicMock()
        hass.data = {DOMAIN: {"entry_id": {"coordinator": mock_coordinator}}}
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
        assert add_entities.call_count == 2
        existing_entities = add_entities.call_args_list[0][0][0]
        forecast_entities = add_entities.call_args_list[1][0][0]
        assert len(existing_entities) == 13
        assert len(forecast_entities) == 12
        config_entry.async_create_background_task.assert_called_once()


# ── Additional device_info tests ────────────────────────────────────────


class TestDeviceInfoCoverage:
    """Cover device_info properties for entities not yet tested."""

    def test_next_color_device_info(self, mock_coordinator):
        sensor = NextColor(mock_coordinator, "cfg", False)
        info = sensor.device_info
        assert (DOMAIN, "cfg") in info["identifiers"]

    def test_next_color_time_device_info(self):
        sensor = NextColorTime("cfg")
        info = sensor.device_info
        assert (DOMAIN, "cfg") in info["identifiers"]

    def test_days_left_device_info(self, mock_coordinator):
        sensor = DaysLeft(mock_coordinator, "cfg", API_VALUE_BLUE)
        info = sensor.device_info
        assert (DOMAIN, "cfg") in info["identifiers"]

    def test_days_used_device_info(self, mock_coordinator):
        sensor = DaysUsed(mock_coordinator, "cfg", API_VALUE_BLUE)
        info = sensor.device_info
        assert (DOMAIN, "cfg") in info["identifiers"]

    def test_next_cycle_time_device_info(self):
        sensor = NextCycleTime("cfg")
        info = sensor.device_info
        assert (DOMAIN, "cfg") in info["identifiers"]
