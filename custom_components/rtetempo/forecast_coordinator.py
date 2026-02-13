"""DataUpdateCoordinator for OpenDPE forecast data."""

from __future__ import annotations

import logging

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, OPENDPE_UPDATE_INTERVAL
from .forecast import ForecastDay, async_fetch_opendpe_forecast

_LOGGER = logging.getLogger(__name__)


class ForecastCoordinator(DataUpdateCoordinator[list[ForecastDay]]):
    """Coordinator to fetch OpenDPE forecast data."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_opendpe_forecast",
            update_interval=OPENDPE_UPDATE_INTERVAL,
        )
        self._session = async_get_clientsession(hass)

    async def _async_update_data(self) -> list[ForecastDay]:
        """Fetch data from OpenDPE."""
        try:
            return await async_fetch_opendpe_forecast(self._session)
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error communicating with OpenDPE: {err}") from err
        except TimeoutError as err:
            raise UpdateFailed(f"Timeout fetching OpenDPE data: {err}") from err
        except (KeyError, ValueError) as err:
            raise UpdateFailed(f"Error parsing OpenDPE data: {err}") from err
