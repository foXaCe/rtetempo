"""Data models for the RTE Tempo API."""

from __future__ import annotations

import datetime
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TempoDay:
    """Represents a single tempo day."""

    start: datetime.datetime | datetime.date
    end: datetime.datetime | datetime.date
    value: str  # "RED" | "WHITE" | "BLUE"
    updated: datetime.datetime


@dataclass(frozen=True, slots=True)
class TempoData:
    """Container for parsed tempo API data."""

    adjusted_days: list[TempoDay]  # 6h-6h (datetime)
    regular_days: list[TempoDay]  # midnight-midnight (date)
    data_end: datetime.datetime | None  # for compute_wait_time
