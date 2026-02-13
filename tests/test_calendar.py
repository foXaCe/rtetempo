"""Tests for the calendar platform."""
from __future__ import annotations

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.rtetempo.api_worker import TempoDay
from custom_components.rtetempo.calendar import (
    async_setup_entry,
    TempoCalendar,
    forge_calendar_event,
    forge_calendar_event_description,
    get_value_emoji,
)
from custom_components.rtetempo.const import (
    API_VALUE_BLUE,
    API_VALUE_RED,
    API_VALUE_WHITE,
    DOMAIN,
    FRANCE_TZ,
    SENSOR_COLOR_BLUE_EMOJI,
    SENSOR_COLOR_BLUE_NAME,
    SENSOR_COLOR_RED_EMOJI,
    SENSOR_COLOR_RED_NAME,
    SENSOR_COLOR_UNKNOWN_EMOJI,
    SENSOR_COLOR_WHITE_EMOJI,
    SENSOR_COLOR_WHITE_NAME,
)

from .conftest import make_tempo_day_date, make_tempo_day_time


# ── get_value_emoji ─────────────────────────────────────────────────────


class TestGetValueEmoji:
    """Tests for get_value_emoji."""

    def test_red(self):
        assert get_value_emoji(API_VALUE_RED) == SENSOR_COLOR_RED_EMOJI

    def test_white(self):
        assert get_value_emoji(API_VALUE_WHITE) == SENSOR_COLOR_WHITE_EMOJI

    def test_blue(self):
        assert get_value_emoji(API_VALUE_BLUE) == SENSOR_COLOR_BLUE_EMOJI

    def test_unknown(self):
        assert get_value_emoji("OTHER") == SENSOR_COLOR_UNKNOWN_EMOJI


# ── forge_calendar_event_description ────────────────────────────────────


class TestForgeCalendarEventDescription:
    """Tests for forge_calendar_event_description."""

    def test_red(self):
        td = make_tempo_day_date(2024, 1, 15, API_VALUE_RED)
        result = forge_calendar_event_description(td)
        assert SENSOR_COLOR_RED_NAME in result
        assert "Jour Tempo" in result

    def test_white(self):
        td = make_tempo_day_date(2024, 1, 15, API_VALUE_WHITE)
        result = forge_calendar_event_description(td)
        assert SENSOR_COLOR_WHITE_NAME in result

    def test_blue(self):
        td = make_tempo_day_date(2024, 1, 15, API_VALUE_BLUE)
        result = forge_calendar_event_description(td)
        assert SENSOR_COLOR_BLUE_NAME in result

    def test_unknown(self):
        td = make_tempo_day_date(2024, 1, 15, "MYSTERY")
        result = forge_calendar_event_description(td)
        assert "inconnu" in result
        assert "MYSTERY" in result


# ── forge_calendar_event ────────────────────────────────────────────────


class TestForgeCalendarEvent:
    """Tests for forge_calendar_event."""

    def test_date_event(self):
        td = make_tempo_day_date(2024, 1, 15, API_VALUE_BLUE)
        event = forge_calendar_event(td)
        assert event.start == datetime.date(2024, 1, 15)
        assert event.end == datetime.date(2024, 1, 16)
        assert event.summary == SENSOR_COLOR_BLUE_EMOJI
        assert "Bleu" in event.description
        assert event.location == "France"

    def test_time_event(self):
        td = make_tempo_day_time(2024, 1, 15, API_VALUE_RED)
        event = forge_calendar_event(td)
        assert event.start.hour == 6
        assert event.summary == SENSOR_COLOR_RED_EMOJI

    def test_uid_format(self):
        td = make_tempo_day_date(2024, 3, 20, API_VALUE_WHITE)
        event = forge_calendar_event(td)
        assert event.uid == f"{DOMAIN}_2024_3_20"


# ── TempoCalendar ───────────────────────────────────────────────────────


class TestTempoCalendar:
    """Tests for TempoCalendar entity."""

    def test_init(self, mock_api_worker):
        cal = TempoCalendar(mock_api_worker, "cfg")
        assert cal._attr_name == "Calendrier"
        assert cal._attr_unique_id == f"{DOMAIN}_cfg_calendar"

    def test_device_info(self, mock_api_worker):
        cal = TempoCalendar(mock_api_worker, "cfg")
        info = cal.device_info
        assert (DOMAIN, "cfg") in info["identifiers"]

    def test_event_current_adjusted(self, mock_api_worker):
        """Test current event with adjusted days (datetime-based)."""
        now = datetime.datetime(2024, 1, 15, 10, 0, tzinfo=FRANCE_TZ)
        day = make_tempo_day_time(2024, 1, 15, API_VALUE_BLUE)
        mock_api_worker.adjusted_days = True
        mock_api_worker.get_calendar_days.return_value = [day]
        cal = TempoCalendar(mock_api_worker, "cfg")
        with patch(
            "custom_components.rtetempo.calendar.datetime"
        ) as mock_dt:
            mock_dt.datetime.now.return_value = now
            event = cal.event
        assert event is not None
        assert event.summary == SENSOR_COLOR_BLUE_EMOJI

    def test_event_current_regular(self, mock_api_worker):
        """Test current event with regular days (date-based)."""
        now = datetime.datetime(2024, 1, 15, 10, 0, tzinfo=FRANCE_TZ)
        day = make_tempo_day_date(2024, 1, 15, API_VALUE_WHITE)
        mock_api_worker.adjusted_days = False
        mock_api_worker.get_calendar_days.return_value = [day]
        cal = TempoCalendar(mock_api_worker, "cfg")
        with patch(
            "custom_components.rtetempo.calendar.datetime"
        ) as mock_dt:
            mock_dt.datetime.now.return_value = now
            event = cal.event
        assert event is not None
        assert event.summary == SENSOR_COLOR_WHITE_EMOJI

    def test_event_no_match(self, mock_api_worker):
        """Test no current event."""
        now = datetime.datetime(2024, 1, 15, 10, 0, tzinfo=FRANCE_TZ)
        mock_api_worker.adjusted_days = False
        mock_api_worker.get_calendar_days.return_value = []
        cal = TempoCalendar(mock_api_worker, "cfg")
        with patch(
            "custom_components.rtetempo.calendar.datetime"
        ) as mock_dt:
            mock_dt.datetime.now.return_value = now
            event = cal.event
        assert event is None

    @pytest.mark.asyncio
    async def test_async_get_events_date_mode(self, mock_api_worker):
        """Test retrieving events in date mode."""
        days = [
            make_tempo_day_date(2024, 1, 15, API_VALUE_BLUE),
            make_tempo_day_date(2024, 1, 16, API_VALUE_WHITE),
            make_tempo_day_date(2024, 1, 17, API_VALUE_RED),
        ]
        mock_api_worker.adjusted_days = False
        mock_api_worker.get_calendar_days.return_value = days
        cal = TempoCalendar(mock_api_worker, "cfg")
        hass = MagicMock()
        start = datetime.datetime(2024, 1, 15, 0, 0, tzinfo=FRANCE_TZ)
        end = datetime.datetime(2024, 1, 18, 0, 0, tzinfo=FRANCE_TZ)
        events = await cal.async_get_events(hass, start, end)
        assert len(events) == 3

    @pytest.mark.asyncio
    async def test_async_get_events_time_mode(self, mock_api_worker):
        """Test retrieving events in adjusted time mode."""
        days = [
            make_tempo_day_time(2024, 1, 15, API_VALUE_BLUE),
            make_tempo_day_time(2024, 1, 16, API_VALUE_WHITE),
        ]
        mock_api_worker.adjusted_days = True
        mock_api_worker.get_calendar_days.return_value = days
        cal = TempoCalendar(mock_api_worker, "cfg")
        hass = MagicMock()
        start = datetime.datetime(2024, 1, 15, 0, 0, tzinfo=FRANCE_TZ)
        end = datetime.datetime(2024, 1, 18, 0, 0, tzinfo=FRANCE_TZ)
        events = await cal.async_get_events(hass, start, end)
        assert len(events) == 2

    @pytest.mark.asyncio
    async def test_async_get_events_partial_overlap_date(self, mock_api_worker):
        """Events that partially overlap the range should be included."""
        days = [
            make_tempo_day_date(2024, 1, 14, API_VALUE_BLUE),  # starts before range
            make_tempo_day_date(2024, 1, 15, API_VALUE_WHITE),  # in range
        ]
        mock_api_worker.adjusted_days = False
        mock_api_worker.get_calendar_days.return_value = days
        cal = TempoCalendar(mock_api_worker, "cfg")
        hass = MagicMock()
        start = datetime.datetime(2024, 1, 15, 0, 0, tzinfo=FRANCE_TZ)
        end = datetime.datetime(2024, 1, 17, 0, 0, tzinfo=FRANCE_TZ)
        events = await cal.async_get_events(hass, start, end)
        # day 14 ends on 15 which overlaps, day 15 is fully in range
        assert len(events) >= 1

    @pytest.mark.asyncio
    async def test_async_get_events_empty(self, mock_api_worker):
        """No events available."""
        mock_api_worker.adjusted_days = False
        mock_api_worker.get_calendar_days.return_value = []
        cal = TempoCalendar(mock_api_worker, "cfg")
        hass = MagicMock()
        start = datetime.datetime(2024, 1, 15, 0, 0, tzinfo=FRANCE_TZ)
        end = datetime.datetime(2024, 1, 18, 0, 0, tzinfo=FRANCE_TZ)
        events = await cal.async_get_events(hass, start, end)
        assert events == []

    @pytest.mark.asyncio
    async def test_async_get_events_time_partial_overlap_start(self, mock_api_worker):
        """Time mode: event starts before range but ends within it."""
        # Event: Jan 15 06:00 -> Jan 16 06:00
        day = make_tempo_day_time(2024, 1, 15, API_VALUE_BLUE)
        mock_api_worker.adjusted_days = True
        mock_api_worker.get_calendar_days.return_value = [day]
        cal = TempoCalendar(mock_api_worker, "cfg")
        hass = MagicMock()
        # Range starts mid-event
        start = datetime.datetime(2024, 1, 15, 12, 0, tzinfo=FRANCE_TZ)
        end = datetime.datetime(2024, 1, 17, 0, 0, tzinfo=FRANCE_TZ)
        events = await cal.async_get_events(hass, start, end)
        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_async_get_events_time_partial_overlap_end(self, mock_api_worker):
        """Time mode: event starts within range but ends after it."""
        # Event: Jan 16 06:00 -> Jan 17 06:00
        day = make_tempo_day_time(2024, 1, 16, API_VALUE_RED)
        mock_api_worker.adjusted_days = True
        mock_api_worker.get_calendar_days.return_value = [day]
        cal = TempoCalendar(mock_api_worker, "cfg")
        hass = MagicMock()
        # Range ends mid-event
        start = datetime.datetime(2024, 1, 15, 0, 0, tzinfo=FRANCE_TZ)
        end = datetime.datetime(2024, 1, 17, 0, 0, tzinfo=FRANCE_TZ)
        events = await cal.async_get_events(hass, start, end)
        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_async_get_events_date_end_overlap(self, mock_api_worker):
        """Date mode: event starts within range but ends after it."""
        # Event: Jan 17 -> Jan 18 (end is exactly at range end boundary)
        day = make_tempo_day_date(2024, 1, 17, API_VALUE_WHITE)
        mock_api_worker.adjusted_days = False
        mock_api_worker.get_calendar_days.return_value = [day]
        cal = TempoCalendar(mock_api_worker, "cfg")
        hass = MagicMock()
        start = datetime.datetime(2024, 1, 15, 0, 0, tzinfo=FRANCE_TZ)
        # End before event.End, so event starts in range but ends after
        end = datetime.datetime(2024, 1, 17, 12, 0, tzinfo=FRANCE_TZ)
        events = await cal.async_get_events(hass, start, end)
        assert len(events) == 1


# ── async_setup_entry ───────────────────────────────────────────────────


class TestCalendarAsyncSetupEntry:
    """Tests for calendar async_setup_entry."""

    @pytest.mark.asyncio
    async def test_success(self, mock_api_worker):
        """Setup creates calendar entity."""
        hass = MagicMock()
        hass.data = {DOMAIN: {"entry_id": mock_api_worker}}
        config_entry = MagicMock()
        config_entry.entry_id = "entry_id"
        config_entry.title = "Test"
        add_entities = MagicMock()
        with patch("custom_components.rtetempo.calendar.asyncio.sleep", new_callable=AsyncMock):
            await async_setup_entry(hass, config_entry, add_entities)
        add_entities.assert_called_once()
        entities = add_entities.call_args[0][0]
        assert len(entities) == 1
        assert isinstance(entities[0], TempoCalendar)

    @pytest.mark.asyncio
    async def test_missing_worker(self):
        """Missing worker -> returns early."""
        hass = MagicMock()
        hass.data = {DOMAIN: {}}
        config_entry = MagicMock()
        config_entry.entry_id = "missing_id"
        config_entry.title = "Test"
        add_entities = MagicMock()
        await async_setup_entry(hass, config_entry, add_entities)
        add_entities.assert_not_called()
