"""DataUpdateCoordinator for RTE Tempo API data with dynamic polling."""

from __future__ import annotations

import datetime
import logging
import random

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api.client import RTETempoClient
from .api.exceptions import RTETempoError
from .api.models import TempoData
from .const import (
    CONFIRM_CHECK,
    CONFIRM_HOUR,
    CONFIRM_MIN,
    DOMAIN,
    FRANCE_TZ,
    HOUR_OF_CHANGE,
)

_LOGGER = logging.getLogger(__name__)


class TempoCoordinator(DataUpdateCoordinator[TempoData]):
    """Coordinator that fetches RTE Tempo data with dynamic polling intervals."""

    def __init__(self, hass: HomeAssistant, client: RTETempoClient) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_rte_tempo",
            update_interval=datetime.timedelta(minutes=1),
        )
        self._client = client

    async def _async_update_data(self) -> TempoData:
        """Fetch tempo data and adjust polling interval."""
        localized_now = datetime.datetime.now(FRANCE_TZ)
        localized_date = datetime.datetime.combine(
            localized_now.date(), datetime.time(tzinfo=FRANCE_TZ)
        )
        start = localized_date - datetime.timedelta(days=364)
        end = localized_date + datetime.timedelta(days=2)

        try:
            data = await self._client.async_get_tempo_data(start, end)
        except RTETempoError as err:
            self.update_interval = datetime.timedelta(minutes=10)
            raise UpdateFailed(f"RTE Tempo API error: {err}") from err

        self.update_interval = compute_wait_time(localized_now, data.data_end)
        return data


def compute_wait_time(
    localized_now: datetime.datetime,
    data_end: datetime.datetime | None,
) -> datetime.timedelta:
    """Compute the next polling interval based on data freshness.

    Compute the next polling interval based on data freshness, preserving all branches and jitter.
    """
    if not data_end:
        return datetime.timedelta(minutes=10)

    localized_today = datetime.datetime.combine(
        localized_now.date(), datetime.time(tzinfo=FRANCE_TZ)
    )
    diff = data_end - localized_today
    _LOGGER.debug(
        "Computing wait time based on data_end(%s) - today(%s) = diff(%s)",
        data_end,
        localized_now,
        diff,
    )

    if diff.days == 2:
        # we have next day color, check if we need to confirm or wait until tomorrow
        ref_confirmation = datetime.datetime(
            year=localized_now.year,
            month=localized_now.month,
            day=localized_now.day,
            hour=CONFIRM_HOUR,
            minute=CONFIRM_MIN,
            tzinfo=localized_now.tzinfo,
        )
        if localized_now > ref_confirmation:
            # we are past the confirmation hour, wait until tomorrow
            tomorrow = localized_now + datetime.timedelta(days=1)
            next_call = datetime.datetime(
                year=tomorrow.year,
                month=tomorrow.month,
                day=tomorrow.day,
                hour=HOUR_OF_CHANGE,
                tzinfo=localized_now.tzinfo,
            )
            wait_time = next_call - localized_now
            wait_secs = int(wait_time.total_seconds())
            wait_time = datetime.timedelta(
                seconds=random.randrange(wait_secs, wait_secs + 900)
            )
            _LOGGER.info(
                "We got next day color, waiting until tomorrow (wait time is %s)",
                wait_time,
            )
        else:
            # we are not past the confirmation hour yet, wait until 2nd confirmation call
            tomorrow = localized_now + datetime.timedelta(days=1)
            next_call = datetime.datetime(
                year=tomorrow.year,
                month=tomorrow.month,
                day=tomorrow.day,
                hour=CONFIRM_CHECK,
                tzinfo=localized_now.tzinfo,
            )
            wait_time = next_call - localized_now
            wait_secs = int(wait_time.total_seconds())
            wait_time = datetime.timedelta(
                seconds=random.randrange(
                    wait_secs - 900, wait_secs + 900
                )  # +- 15min
            )
            _LOGGER.info(
                "We got next day color but too early to confirm, "
                "waiting until confirmation hour (wait time is %s)",
                wait_time,
            )
    elif diff.days == 1:
        # we do not have next day color yet
        if localized_now.hour < 6:
            next_call = datetime.datetime(
                year=localized_now.year,
                month=localized_now.month,
                day=localized_now.day,
                hour=HOUR_OF_CHANGE,
                second=1,  # avoid multiple requests at 5:59:59
                tzinfo=localized_now.tzinfo,
            )
            wait_time = next_call - localized_now
            wait_secs = int(wait_time.total_seconds())
            wait_time = datetime.timedelta(
                seconds=random.randrange(wait_secs, wait_secs + 900)
            )
            _LOGGER.debug(
                "No next day color, waiting for %sh change (wait time is %s)",
                HOUR_OF_CHANGE,
                wait_time,
            )
        else:
            wait_time = datetime.timedelta(minutes=30)
            wait_secs = int(wait_time.total_seconds())
            wait_time = datetime.timedelta(
                seconds=random.randrange(
                    wait_secs * 5 // 6, wait_secs * 7 // 6
                )
            )
            _LOGGER.debug(
                "No next day color, hour of change (%sh) past, "
                "retrying soon (wait time is %s)",
                HOUR_OF_CHANGE,
                wait_time,
            )
    else:
        # weird, should not happen
        wait_time = datetime.timedelta(hours=1)
        wait_secs = int(wait_time.total_seconds())
        wait_time = datetime.timedelta(
            seconds=random.randrange(
                wait_secs * 5 // 6, wait_secs * 7 // 6
            )
        )
        _LOGGER.warning(
            "Unexpected delta between today and last result, "
            "waiting %s as fallback",
            wait_time,
        )

    return wait_time
