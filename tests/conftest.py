"""Fixtures for RTE Tempo Calendar tests."""
from __future__ import annotations

import datetime
from unittest.mock import MagicMock

import pytest

from custom_components.rtetempo.api.models import TempoData, TempoDay
from custom_components.rtetempo.const import (
    API_VALUE_BLUE,
    API_VALUE_RED,
    API_VALUE_WHITE,
    FRANCE_TZ,
)
from custom_components.rtetempo.tempo_coordinator import TempoCoordinator


@pytest.fixture
def mock_coordinator() -> MagicMock:
    """Create a mock TempoCoordinator with empty TempoData."""
    coordinator = MagicMock(spec=TempoCoordinator)
    coordinator.data = TempoData(
        adjusted_days=[],
        regular_days=[],
        data_end=None,
    )
    return coordinator


def make_tempo_day_date(
    year: int, month: int, day: int, value: str
) -> TempoDay:
    """Create a TempoDay with date-based start/end."""
    return TempoDay(
        start=datetime.date(year, month, day),
        end=datetime.date(year, month, day) + datetime.timedelta(days=1),
        value=value,
        updated=datetime.datetime(year, month, day, 10, 0, tzinfo=FRANCE_TZ),
    )


def make_tempo_day_time(
    year: int, month: int, day: int, value: str
) -> TempoDay:
    """Create a TempoDay with datetime-based start/end (adjusted 6h-6h)."""
    start = datetime.datetime(year, month, day, 6, 0, tzinfo=FRANCE_TZ)
    end = start + datetime.timedelta(days=1)
    return TempoDay(
        start=start,
        end=end,
        value=value,
        updated=datetime.datetime(year, month, day, 10, 0, tzinfo=FRANCE_TZ),
    )


def build_sample_days_date(cycle_year: int = 2024) -> list[TempoDay]:
    """Build a sample list of tempo days (date-based) for a cycle starting Sept cycle_year.

    Returns days from Sept 1 to Dec 31 with a mix of colors.
    """
    days = []
    start = datetime.date(cycle_year, 9, 1)
    for i in range(80):
        d = start + datetime.timedelta(days=i)
        if i < 50:
            color = API_VALUE_BLUE
        elif i < 70:
            color = API_VALUE_WHITE
        else:
            color = API_VALUE_RED
        days.append(
            TempoDay(
                start=d,
                end=d + datetime.timedelta(days=1),
                value=color,
                updated=datetime.datetime(
                    d.year, d.month, d.day, 10, 0, tzinfo=FRANCE_TZ
                ),
            )
        )
    return days


def build_sample_days_time(cycle_year: int = 2024) -> list[TempoDay]:
    """Build a sample list of tempo days (time-based, 6h-6h)."""
    days = []
    start = datetime.date(cycle_year, 9, 1)
    for i in range(80):
        d = start + datetime.timedelta(days=i)
        if i < 50:
            color = API_VALUE_BLUE
        elif i < 70:
            color = API_VALUE_WHITE
        else:
            color = API_VALUE_RED
        s = datetime.datetime(d.year, d.month, d.day, 6, 0, tzinfo=FRANCE_TZ)
        days.append(
            TempoDay(
                start=s,
                end=s + datetime.timedelta(days=1),
                value=color,
                updated=datetime.datetime(
                    d.year, d.month, d.day, 10, 0, tzinfo=FRANCE_TZ
                ),
            )
        )
    return days


def make_tempo_data(
    adjusted_days: list[TempoDay] | None = None,
    regular_days: list[TempoDay] | None = None,
    data_end: datetime.datetime | None = None,
) -> TempoData:
    """Helper to create TempoData."""
    return TempoData(
        adjusted_days=adjusted_days or [],
        regular_days=regular_days or [],
        data_end=data_end,
    )
