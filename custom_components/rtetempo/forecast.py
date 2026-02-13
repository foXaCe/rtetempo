"""OpenDPE forecast data model and fetch logic."""

from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass

import aiohttp

from .const import FRANCE_TZ, OPENDPE_API_URL, OPENDPE_COLOR_MAP

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ForecastDay:
    """A single forecast day from OpenDPE."""

    date: datetime.date
    color: str
    probability: float


async def async_fetch_opendpe_forecast(
    session: aiohttp.ClientSession,
) -> list[ForecastDay]:
    """Fetch and parse forecast data from OpenDPE API.

    Returns only future days (from tomorrow onwards).
    """
    async with session.get(OPENDPE_API_URL, timeout=aiohttp.ClientTimeout(total=10)) as resp:
        resp.raise_for_status()
        data = await resp.json(content_type=None)

    today = datetime.datetime.now(FRANCE_TZ).date()
    forecasts: list[ForecastDay] = []

    for entry in data:
        date_str: str = entry["dateJour"]
        raw_color: str = entry["couleurJour"]
        probability: float = float(entry["probabilite"])

        day_date = datetime.date.fromisoformat(date_str)
        if day_date <= today:
            continue

        normalized = OPENDPE_COLOR_MAP.get(raw_color.lower())
        if normalized is None:
            _LOGGER.warning("Unknown OpenDPE color '%s' for %s, skipping", raw_color, date_str)
            continue

        forecasts.append(ForecastDay(date=day_date, color=normalized, probability=probability))

    return forecasts
