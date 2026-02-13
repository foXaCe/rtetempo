"""Tests for sensor_forecast.py - OpenDPE forecast sensor entities."""

from __future__ import annotations

import datetime
from unittest.mock import MagicMock, patch

import pytest

from custom_components.rtetempo.const import (
    API_VALUE_BLUE,
    API_VALUE_RED,
    API_VALUE_WHITE,
    DEVICE_MANUFACTURER,
    DEVICE_MODEL,
    DEVICE_NAME,
    DOMAIN,
    FRANCE_TZ,
    OPENDPE_ATTRIBUTION,
    SENSOR_COLOR_BLUE_EMOJI,
    SENSOR_COLOR_BLUE_NAME,
    SENSOR_COLOR_RED_NAME,
    SENSOR_COLOR_UNKNOWN_NAME,
    SENSOR_COLOR_WHITE_EMOJI,
    SENSOR_COLOR_WHITE_NAME,
)
from custom_components.rtetempo.forecast import ForecastDay
from custom_components.rtetempo.sensor_forecast import OpenDPEForecastSensor


@pytest.fixture
def mock_coordinator():
    """Create a mock ForecastCoordinator."""
    coord = MagicMock()
    coord.data = None
    coord.last_update_success = True
    return coord


def _make_forecast(
    offset_days: int,
    color: str = API_VALUE_BLUE,
    prob: float = 90.0,
) -> ForecastDay:
    """Create a ForecastDay for today + offset_days."""
    target = datetime.datetime.now(FRANCE_TZ).date() + datetime.timedelta(days=offset_days)
    return ForecastDay(date=target, color=color, probability=prob)


def _make_sensor(coordinator, offset, visual=False):
    """Create sensor and populate cache via _handle_coordinator_update."""
    sensor = OpenDPEForecastSensor(
        coordinator,
        "cfg",
        offset,
        visual,
    )
    with patch.object(sensor, "async_write_ha_state"):
        sensor._handle_coordinator_update()
    return sensor


class TestOpenDPEForecastSensorInit:
    """Tests for sensor initialization."""

    def test_text_init(self, mock_coordinator):
        sensor = OpenDPEForecastSensor(
            mock_coordinator,
            "cfg",
            3,
            False,
        )
        assert sensor._attr_name == "Prévision J+3"
        assert sensor._attr_unique_id == f"{DOMAIN}_cfg_forecast_j3"
        assert SENSOR_COLOR_BLUE_NAME in sensor._attr_options
        assert SENSOR_COLOR_WHITE_NAME in sensor._attr_options
        assert SENSOR_COLOR_RED_NAME in sensor._attr_options
        assert SENSOR_COLOR_UNKNOWN_NAME in sensor._attr_options

    def test_visual_init(self, mock_coordinator):
        sensor = OpenDPEForecastSensor(
            mock_coordinator,
            "cfg",
            5,
            True,
        )
        assert sensor._attr_name == "Prévision J+5 (visuel)"
        assert f"{DOMAIN}_cfg_forecast_j5_emoji" == sensor._attr_unique_id
        assert SENSOR_COLOR_BLUE_EMOJI in sensor._attr_options

    def test_attribution(self, mock_coordinator):
        sensor = OpenDPEForecastSensor(
            mock_coordinator,
            "cfg",
            2,
            False,
        )
        assert sensor._attr_attribution == OPENDPE_ATTRIBUTION

    def test_cached_forecast_init_none(self, mock_coordinator):
        sensor = OpenDPEForecastSensor(
            mock_coordinator,
            "cfg",
            2,
            False,
        )
        assert sensor._cached_forecast is None


class TestOpenDPEForecastSensorDeviceInfo:
    """Tests for device_info."""

    def test_device_info(self, mock_coordinator):
        sensor = OpenDPEForecastSensor(
            mock_coordinator,
            "cfg",
            2,
            False,
        )
        info = sensor.device_info
        assert (DOMAIN, "cfg") in info["identifiers"]
        assert info["name"] == DEVICE_NAME
        assert info["manufacturer"] == DEVICE_MANUFACTURER
        assert info["model"] == DEVICE_MODEL


class TestOpenDPEForecastSensorNativeValue:
    """Tests for native_value."""

    def test_text_value(self, mock_coordinator):
        mock_coordinator.data = [_make_forecast(3, API_VALUE_RED)]
        sensor = _make_sensor(mock_coordinator, 3, visual=False)
        assert sensor.native_value == SENSOR_COLOR_RED_NAME

    def test_visual_value(self, mock_coordinator):
        mock_coordinator.data = [_make_forecast(4, API_VALUE_WHITE)]
        sensor = _make_sensor(mock_coordinator, 4, visual=True)
        assert sensor.native_value == SENSOR_COLOR_WHITE_EMOJI

    def test_no_data(self, mock_coordinator):
        mock_coordinator.data = None
        sensor = _make_sensor(mock_coordinator, 2, visual=False)
        assert sensor.native_value is None

    def test_no_matching_date(self, mock_coordinator):
        mock_coordinator.data = [_make_forecast(5, API_VALUE_BLUE)]
        sensor = _make_sensor(mock_coordinator, 3, visual=False)
        assert sensor.native_value is None


class TestOpenDPEForecastSensorIcon:
    """Tests for dynamic icon."""

    def test_icon_red(self, mock_coordinator):
        mock_coordinator.data = [_make_forecast(2, API_VALUE_RED)]
        sensor = _make_sensor(mock_coordinator, 2)
        assert sensor.icon == "mdi:alert"

    def test_icon_white(self, mock_coordinator):
        mock_coordinator.data = [_make_forecast(2, API_VALUE_WHITE)]
        sensor = _make_sensor(mock_coordinator, 2)
        assert sensor.icon == "mdi:information-outline"

    def test_icon_blue(self, mock_coordinator):
        mock_coordinator.data = [_make_forecast(2, API_VALUE_BLUE)]
        sensor = _make_sensor(mock_coordinator, 2)
        assert sensor.icon == "mdi:check-bold"

    def test_icon_no_data(self, mock_coordinator):
        mock_coordinator.data = None
        sensor = _make_sensor(mock_coordinator, 2)
        assert sensor.icon == "mdi:palette"


class TestOpenDPEForecastSensorExtraAttributes:
    """Tests for extra_state_attributes."""

    def test_with_data(self, mock_coordinator):
        mock_coordinator.data = [
            _make_forecast(3, API_VALUE_BLUE, 85.5),
        ]
        sensor = _make_sensor(mock_coordinator, 3)
        attrs = sensor.extra_state_attributes
        assert attrs is not None
        target_date = datetime.datetime.now(FRANCE_TZ).date() + datetime.timedelta(days=3)
        assert attrs["date"] == target_date.isoformat()
        assert attrs["emoji"] == SENSOR_COLOR_BLUE_EMOJI
        assert attrs["couleur"] == SENSOR_COLOR_BLUE_NAME
        assert attrs["probabilite"] == 85.5

    def test_without_data(self, mock_coordinator):
        mock_coordinator.data = None
        sensor = _make_sensor(mock_coordinator, 3)
        assert sensor.extra_state_attributes is None


class TestOpenDPEForecastSensorAvailable:
    """Tests for available property."""

    def test_available_with_matching_data(self, mock_coordinator):
        mock_coordinator.data = [_make_forecast(2, API_VALUE_BLUE)]
        mock_coordinator.last_update_success = True
        sensor = _make_sensor(mock_coordinator, 2)
        assert sensor._cached_forecast is not None

    def test_not_available_no_data(self, mock_coordinator):
        mock_coordinator.data = None
        sensor = _make_sensor(mock_coordinator, 2)
        assert sensor._cached_forecast is None

    def test_not_available_no_matching_date(self, mock_coordinator):
        mock_coordinator.data = [_make_forecast(5, API_VALUE_BLUE)]
        sensor = _make_sensor(mock_coordinator, 2)
        assert sensor._cached_forecast is None


class TestHandleCoordinatorUpdate:
    """Tests for _handle_coordinator_update cache."""

    def test_populates_cache(self, mock_coordinator):
        mock_coordinator.data = [_make_forecast(3, API_VALUE_RED)]
        sensor = OpenDPEForecastSensor(
            mock_coordinator,
            "cfg",
            3,
            False,
        )
        assert sensor._cached_forecast is None
        with patch.object(sensor, "async_write_ha_state"):
            sensor._handle_coordinator_update()
        assert sensor._cached_forecast is not None
        assert sensor._cached_forecast.color == API_VALUE_RED

    def test_clears_cache_when_no_data(self, mock_coordinator):
        mock_coordinator.data = [_make_forecast(3, API_VALUE_BLUE)]
        sensor = _make_sensor(mock_coordinator, 3)
        assert sensor._cached_forecast is not None
        # Data disappears
        mock_coordinator.data = None
        with patch.object(sensor, "async_write_ha_state"):
            sensor._handle_coordinator_update()
        assert sensor._cached_forecast is None
