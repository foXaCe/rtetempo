"""OpenDPE forecast sensor entities."""

from __future__ import annotations

import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DEVICE_MANUFACTURER,
    DEVICE_MODEL,
    DEVICE_NAME,
    DOMAIN,
    FRANCE_TZ,
    OPENDPE_ATTRIBUTION,
    SENSOR_COLOR_BLUE_EMOJI,
    SENSOR_COLOR_BLUE_NAME,
    SENSOR_COLOR_RED_EMOJI,
    SENSOR_COLOR_RED_NAME,
    SENSOR_COLOR_UNKNOWN_EMOJI,
    SENSOR_COLOR_UNKNOWN_NAME,
    SENSOR_COLOR_WHITE_EMOJI,
    SENSOR_COLOR_WHITE_NAME,
)
from .forecast import ForecastDay
from .forecast_coordinator import ForecastCoordinator
from .sensor import get_color_emoji, get_color_icon, get_color_name


class OpenDPEForecastSensor(CoordinatorEntity[ForecastCoordinator], SensorEntity):
    """Sensor entity for an OpenDPE forecast day."""

    __slots__ = ("_config_id", "_offset", "_visual", "_cached_forecast")

    _attr_has_entity_name = True
    _attr_attribution = OPENDPE_ATTRIBUTION
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_icon = "mdi:palette"

    def __init__(
        self,
        coordinator: ForecastCoordinator,
        config_id: str,
        offset: int,
        visual: bool,
    ) -> None:
        """Initialize the forecast sensor."""
        super().__init__(coordinator)
        self._config_id = config_id
        self._offset = offset
        self._visual = visual
        self._cached_forecast: ForecastDay | None = None

        if visual:
            self._attr_name = f"Prévision J+{offset} (visuel)"
            self._attr_unique_id = f"{DOMAIN}_{config_id}_forecast_j{offset}_emoji"
            self._attr_options = [
                SENSOR_COLOR_BLUE_EMOJI,
                SENSOR_COLOR_WHITE_EMOJI,
                SENSOR_COLOR_RED_EMOJI,
                SENSOR_COLOR_UNKNOWN_EMOJI,
            ]
        else:
            self._attr_name = f"Prévision J+{offset}"
            self._attr_unique_id = f"{DOMAIN}_{config_id}_forecast_j{offset}"
            self._attr_options = [
                SENSOR_COLOR_BLUE_NAME,
                SENSOR_COLOR_WHITE_NAME,
                SENSOR_COLOR_RED_NAME,
                SENSOR_COLOR_UNKNOWN_NAME,
            ]

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self._config_id)},
            name=DEVICE_NAME,
            manufacturer=DEVICE_MANUFACTURER,
            model=DEVICE_MODEL,
        )

    def _get_target_date(self) -> datetime.date:
        """Return the target date for this sensor."""
        return datetime.datetime.now(FRANCE_TZ).date() + datetime.timedelta(days=self._offset)

    def _find_forecast(self) -> ForecastDay | None:
        """Find the forecast entry for the target date."""
        if not self.coordinator.data:
            return None
        target = self._get_target_date()
        for forecast in self.coordinator.data:
            if forecast.date == target:
                return forecast
        return None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Cache forecast on coordinator update, then trigger state write."""
        self._cached_forecast = self._find_forecast()
        super()._handle_coordinator_update()

    @property
    def available(self) -> bool:
        """Return True if coordinator has data for this date."""
        return super().available and self._cached_forecast is not None

    @property
    def native_value(self) -> str | None:
        """Return the color name or emoji."""
        if self._cached_forecast is None:
            return None
        if self._visual:
            return get_color_emoji(self._cached_forecast.color)
        return get_color_name(self._cached_forecast.color)

    @property
    def icon(self) -> str:
        """Return a dynamic icon based on color."""
        if self._cached_forecast is None:
            return "mdi:palette"
        return get_color_icon(self._cached_forecast.color)

    @property
    def extra_state_attributes(self) -> dict[str, str | float] | None:
        """Return extra attributes."""
        if self._cached_forecast is None:
            return None
        return {
            "date": self._cached_forecast.date.isoformat(),
            "emoji": get_color_emoji(self._cached_forecast.color),
            "couleur": get_color_name(self._cached_forecast.color),
            "probabilite": self._cached_forecast.probability,
        }
