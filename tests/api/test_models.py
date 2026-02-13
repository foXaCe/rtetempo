"""Tests for the data models."""

from __future__ import annotations

import datetime

from custom_components.rtetempo.api.models import TempoData, TempoDay
from custom_components.rtetempo.const import FRANCE_TZ


class TestTempoDay:
    """Tests for TempoDay dataclass."""

    def test_creation_with_date(self):
        td = TempoDay(
            start=datetime.date(2024, 1, 15),
            end=datetime.date(2024, 1, 16),
            value="BLUE",
            updated=datetime.datetime(2024, 1, 15, 10, 0, tzinfo=FRANCE_TZ),
        )
        assert td.start == datetime.date(2024, 1, 15)
        assert td.end == datetime.date(2024, 1, 16)
        assert td.value == "BLUE"

    def test_creation_with_datetime(self):
        td = TempoDay(
            start=datetime.datetime(2024, 1, 15, 6, 0, tzinfo=FRANCE_TZ),
            end=datetime.datetime(2024, 1, 16, 6, 0, tzinfo=FRANCE_TZ),
            value="RED",
            updated=datetime.datetime(2024, 1, 15, 10, 0, tzinfo=FRANCE_TZ),
        )
        assert td.start.hour == 6  # type: ignore[union-attr]
        assert td.value == "RED"

    def test_frozen(self):
        td = TempoDay(
            start=datetime.date(2024, 1, 15),
            end=datetime.date(2024, 1, 16),
            value="WHITE",
            updated=datetime.datetime(2024, 1, 15, 10, 0, tzinfo=FRANCE_TZ),
        )
        try:
            td.value = "BLUE"  # type: ignore[misc]
            assert False, "Should have raised"
        except AttributeError:
            pass


class TestTempoData:
    """Tests for TempoData dataclass."""

    def test_creation(self):
        td = TempoDay(
            start=datetime.date(2024, 1, 15),
            end=datetime.date(2024, 1, 16),
            value="BLUE",
            updated=datetime.datetime(2024, 1, 15, 10, 0, tzinfo=FRANCE_TZ),
        )
        data = TempoData(
            adjusted_days=[td],
            regular_days=[td],
            data_end=datetime.datetime(2024, 1, 16, 0, 0, tzinfo=FRANCE_TZ),
        )
        assert len(data.adjusted_days) == 1
        assert len(data.regular_days) == 1
        assert data.data_end is not None

    def test_none_data_end(self):
        data = TempoData(adjusted_days=[], regular_days=[], data_end=None)
        assert data.data_end is None
        assert data.adjusted_days == []
