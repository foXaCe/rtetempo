"""Tests for constants."""
from custom_components.rtetempo.const import (
    API_DOMAIN,
    API_TEMPO_ENDPOINT,
    API_TOKEN_ENDPOINT,
    CYCLE_START_DAY,
    CYCLE_START_MONTH,
    DOMAIN,
    FRANCE_TZ,
    HOUR_OF_CHANGE,
    OFF_PEAK_START,
    SENSOR_COLOR_RED_NAME,
    TOTAL_RED_DAYS,
    TOTAL_WHITE_DAYS,
)


class TestConstants:
    """Verify critical constants have expected values."""

    def test_domain(self):
        assert DOMAIN == "rtetempo"

    def test_timezone(self):
        assert str(FRANCE_TZ) == "Europe/Paris"

    def test_hour_of_change(self):
        assert HOUR_OF_CHANGE == 6

    def test_off_peak_start(self):
        assert OFF_PEAK_START == 22

    def test_cycle_start(self):
        assert CYCLE_START_MONTH == 9
        assert CYCLE_START_DAY == 1

    def test_total_days(self):
        assert TOTAL_RED_DAYS == 22
        assert TOTAL_WHITE_DAYS == 43

    def test_api_endpoints(self):
        assert "rte-france.com" in API_DOMAIN
        assert API_TOKEN_ENDPOINT.startswith("https://")
        assert API_TEMPO_ENDPOINT.startswith("https://")

    def test_red_name_workaround(self):
        """The codespell workaround should still produce the right name."""
        assert SENSOR_COLOR_RED_NAME == "Rouge"
