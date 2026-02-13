"""RTE Tempo Calendar."""
from __future__ import annotations

import datetime
import logging

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api.models import TempoDay
from .const import (
    API_ATTRIBUTION,
    API_VALUE_BLUE,
    API_VALUE_RED,
    API_VALUE_WHITE,
    DEVICE_MANUFACTURER,
    DEVICE_MODEL,
    DEVICE_NAME,
    DOMAIN,
    FRANCE_TZ,
    OPTION_ADJUSTED_DAYS,
    SENSOR_COLOR_BLUE_EMOJI,
    SENSOR_COLOR_BLUE_NAME,
    SENSOR_COLOR_RED_EMOJI,
    SENSOR_COLOR_RED_NAME,
    SENSOR_COLOR_UNKNOWN_EMOJI,
    SENSOR_COLOR_WHITE_EMOJI,
    SENSOR_COLOR_WHITE_NAME,
)
from .tempo_coordinator import TempoCoordinator

_LOGGER = logging.getLogger(__name__)


# config flow setup
async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up entry."""
    _LOGGER.debug("%s: setting up calendar plateform", config_entry.title)
    coordinator: TempoCoordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    adjusted_days = bool(config_entry.options.get(OPTION_ADJUSTED_DAYS))
    async_add_entities(
        [TempoCalendar(coordinator, config_entry.entry_id, adjusted_days)],
        True,
    )


class TempoCalendar(CoordinatorEntity[TempoCoordinator], CalendarEntity):
    """Create a Home Assistant calendar returning tempo days."""

    _attr_has_entity_name = True
    _attr_attribution = API_ATTRIBUTION

    def __init__(self, coordinator: TempoCoordinator, config_id: str, adjusted_days: bool) -> None:
        """Initialize the calendar."""
        super().__init__(coordinator)
        self._attr_name = "Calendrier"
        self._attr_unique_id = f"{DOMAIN}_{config_id}_calendar"
        self._config_id = config_id
        self._adjusted_days = adjusted_days

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        if not self.coordinator.data:
            return []
        events: list[CalendarEvent] = []
        if self._adjusted_days:
            tempo_days = self.coordinator.data.adjusted_days
            for tempo_day in tempo_days:
                if tempo_day.start >= start_date and tempo_day.end <= end_date:
                    events.append(forge_calendar_event(tempo_day))
                elif tempo_day.start < start_date < tempo_day.end < end_date:
                    events.append(forge_calendar_event(tempo_day))
                elif start_date < tempo_day.start < end_date < tempo_day.end:
                    events.append(forge_calendar_event(tempo_day))
        else:
            tempo_days = self.coordinator.data.regular_days
            for tempo_day in tempo_days:
                if (
                    tempo_day.start >= start_date.date()
                    and tempo_day.end <= end_date.date()
                ):
                    events.append(forge_calendar_event(tempo_day))
                elif (
                    tempo_day.start
                    <= start_date.date()
                    <= tempo_day.end
                    <= end_date.date()
                ):
                    events.append(forge_calendar_event(tempo_day))
                elif (
                    start_date.date()
                    <= tempo_day.start
                    <= end_date.date()
                    <= tempo_day.end
                ):
                    events.append(forge_calendar_event(tempo_day))
        _LOGGER.debug(
            "Returning %d events for range %s <> %s",
            len(events),
            start_date,
            end_date,
        )
        return events

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

    @property
    def event(self) -> CalendarEvent | None:
        """Return the current active event if any."""
        if not self.coordinator.data:
            return None
        localized_now = datetime.datetime.now(FRANCE_TZ)
        if self._adjusted_days:
            for tempo_day in self.coordinator.data.adjusted_days:
                if tempo_day.start <= localized_now < tempo_day.end:
                    return forge_calendar_event(tempo_day)
        else:
            for tempo_day in self.coordinator.data.regular_days:
                if tempo_day.start <= localized_now.date() < tempo_day.end:
                    return forge_calendar_event(tempo_day)
        return None


def forge_calendar_event(tempo_day: TempoDay):
    """Forge a Home Assistant Calendar Event from a Tempo day."""
    return CalendarEvent(
        start=tempo_day.start,
        end=tempo_day.end,
        summary=get_value_emoji(tempo_day.value),
        description=forge_calendar_event_description(tempo_day),
        location="France",
        uid=f"{DOMAIN}_{tempo_day.start.year}_{tempo_day.start.month}_{tempo_day.start.day}",
    )


def get_value_emoji(value: str) -> str:
    """Get corresponding emoji for tempo value."""
    if value == API_VALUE_RED:
        return SENSOR_COLOR_RED_EMOJI
    if value == API_VALUE_WHITE:
        return SENSOR_COLOR_WHITE_EMOJI
    if value == API_VALUE_BLUE:
        return SENSOR_COLOR_BLUE_EMOJI
    return SENSOR_COLOR_UNKNOWN_EMOJI


def forge_calendar_event_description(tempo_day: TempoDay) -> str:
    """Forge a calendar event summary from a tempo day value."""
    if tempo_day.value == API_VALUE_RED:
        return f"Jour Tempo {SENSOR_COLOR_RED_NAME}"
    if tempo_day.value == API_VALUE_WHITE:
        return f"Jour Tempo {SENSOR_COLOR_WHITE_NAME}"
    if tempo_day.value == API_VALUE_BLUE:
        return f"Jour Tempo {SENSOR_COLOR_BLUE_NAME}"
    return f"Jour Tempo inconnu ({tempo_day.value})"
