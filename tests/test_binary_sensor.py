"""Tests for the binary sensor platform."""
from __future__ import annotations

import datetime
from unittest.mock import MagicMock, patch

import pytest

from custom_components.rtetempo.binary_sensor import OffPeakHours, async_setup_entry
from custom_components.rtetempo.const import DOMAIN, FRANCE_TZ


class TestOffPeakHours:
    """Tests for OffPeakHours binary sensor."""

    def test_init(self):
        sensor = OffPeakHours("cfg")
        assert sensor._attr_unique_id == f"{DOMAIN}_cfg_off_peak"
        assert sensor._attr_name == "Heures Creuses"
        assert sensor._attr_should_poll is True

    def test_device_info(self):
        sensor = OffPeakHours("cfg")
        info = sensor.device_info
        assert (DOMAIN, "cfg") in info["identifiers"]

    def test_off_peak_late_night(self):
        """After 22h -> off peak (on)."""
        now = datetime.datetime(2024, 1, 15, 23, 0, tzinfo=FRANCE_TZ)
        sensor = OffPeakHours("cfg")
        with patch(
            "custom_components.rtetempo.binary_sensor.datetime"
        ) as mock_dt:
            mock_dt.datetime.now.return_value = now
            sensor.update()
        assert sensor._attr_is_on is True

    def test_off_peak_early_morning(self):
        """Before 6h -> off peak (on)."""
        now = datetime.datetime(2024, 1, 15, 3, 0, tzinfo=FRANCE_TZ)
        sensor = OffPeakHours("cfg")
        with patch(
            "custom_components.rtetempo.binary_sensor.datetime"
        ) as mock_dt:
            mock_dt.datetime.now.return_value = now
            sensor.update()
        assert sensor._attr_is_on is True

    def test_peak_morning(self):
        """At 6h -> peak (off)."""
        now = datetime.datetime(2024, 1, 15, 6, 0, tzinfo=FRANCE_TZ)
        sensor = OffPeakHours("cfg")
        with patch(
            "custom_components.rtetempo.binary_sensor.datetime"
        ) as mock_dt:
            mock_dt.datetime.now.return_value = now
            sensor.update()
        assert sensor._attr_is_on is False

    def test_peak_afternoon(self):
        """At 14h -> peak (off)."""
        now = datetime.datetime(2024, 1, 15, 14, 0, tzinfo=FRANCE_TZ)
        sensor = OffPeakHours("cfg")
        with patch(
            "custom_components.rtetempo.binary_sensor.datetime"
        ) as mock_dt:
            mock_dt.datetime.now.return_value = now
            sensor.update()
        assert sensor._attr_is_on is False

    def test_peak_just_before_off_peak(self):
        """At 21h59 -> still peak (off)."""
        now = datetime.datetime(2024, 1, 15, 21, 59, tzinfo=FRANCE_TZ)
        sensor = OffPeakHours("cfg")
        with patch(
            "custom_components.rtetempo.binary_sensor.datetime"
        ) as mock_dt:
            mock_dt.datetime.now.return_value = now
            sensor.update()
        assert sensor._attr_is_on is False

    def test_off_peak_at_22(self):
        """At exactly 22h -> off peak (on)."""
        now = datetime.datetime(2024, 1, 15, 22, 0, tzinfo=FRANCE_TZ)
        sensor = OffPeakHours("cfg")
        with patch(
            "custom_components.rtetempo.binary_sensor.datetime"
        ) as mock_dt:
            mock_dt.datetime.now.return_value = now
            sensor.update()
        assert sensor._attr_is_on is True

    def test_off_peak_at_midnight(self):
        """At midnight -> off peak (on)."""
        now = datetime.datetime(2024, 1, 15, 0, 0, tzinfo=FRANCE_TZ)
        sensor = OffPeakHours("cfg")
        with patch(
            "custom_components.rtetempo.binary_sensor.datetime"
        ) as mock_dt:
            mock_dt.datetime.now.return_value = now
            sensor.update()
        assert sensor._attr_is_on is True

    def test_peak_at_5h59(self):
        """At 5h59 -> off peak (on), still before 6."""
        now = datetime.datetime(2024, 1, 15, 5, 59, tzinfo=FRANCE_TZ)
        sensor = OffPeakHours("cfg")
        with patch(
            "custom_components.rtetempo.binary_sensor.datetime"
        ) as mock_dt:
            mock_dt.datetime.now.return_value = now
            sensor.update()
        assert sensor._attr_is_on is True


# ── async_setup_entry ───────────────────────────────────────────────────


class TestBinarySensorAsyncSetupEntry:
    """Tests for binary_sensor async_setup_entry."""

    @pytest.mark.asyncio
    async def test_success(self):
        """Setup creates OffPeakHours entity."""
        hass = MagicMock()
        config_entry = MagicMock()
        config_entry.entry_id = "entry_id"
        add_entities = MagicMock()
        await async_setup_entry(hass, config_entry, add_entities)
        add_entities.assert_called_once()
        entities = add_entities.call_args[0][0]
        assert len(entities) == 1
        assert isinstance(entities[0], OffPeakHours)
