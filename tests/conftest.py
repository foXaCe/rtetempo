"""Fixtures for RTE Tempo Calendar tests."""
from __future__ import annotations

import datetime
from unittest.mock import MagicMock

import pytest

from custom_components.rtetempo.api_worker import APIWorker, TempoDay
from custom_components.rtetempo.const import (
    API_VALUE_BLUE,
    API_VALUE_RED,
    API_VALUE_WHITE,
    FRANCE_TZ,
)


@pytest.fixture
def mock_api_worker() -> MagicMock:
    """Create a mock APIWorker."""
    worker = MagicMock(spec=APIWorker)
    worker.adjusted_days = False
    worker._tempo_days_time = []
    worker._tempo_days_date = []
    return worker


def make_tempo_day_date(
    year: int, month: int, day: int, value: str
) -> TempoDay:
    """Create a TempoDay with date-based Start/End."""
    return TempoDay(
        Start=datetime.date(year, month, day),
        End=datetime.date(year, month, day) + datetime.timedelta(days=1),
        Value=value,
        Updated=datetime.datetime(year, month, day, 10, 0, tzinfo=FRANCE_TZ),
    )


def make_tempo_day_time(
    year: int, month: int, day: int, value: str
) -> TempoDay:
    """Create a TempoDay with datetime-based Start/End (adjusted 6h-6h)."""
    start = datetime.datetime(year, month, day, 6, 0, tzinfo=FRANCE_TZ)
    end = start + datetime.timedelta(days=1)
    return TempoDay(
        Start=start,
        End=end,
        Value=value,
        Updated=datetime.datetime(year, month, day, 10, 0, tzinfo=FRANCE_TZ),
    )


def build_sample_days_date(cycle_year: int = 2024) -> list[TempoDay]:
    """Build a sample list of tempo days (date-based) for a cycle starting Sept cycle_year.

    Returns days from Sept 1 to Dec 31 with a mix of colors.
    """
    days = []
    # 50 blue, 20 white, 10 red in this sample set (Sept-Dec)
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
                Start=d,
                End=d + datetime.timedelta(days=1),
                Value=color,
                Updated=datetime.datetime(
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
                Start=s,
                End=s + datetime.timedelta(days=1),
                Value=color,
                Updated=datetime.datetime(
                    d.year, d.month, d.day, 10, 0, tzinfo=FRANCE_TZ
                ),
            )
        )
    return days
