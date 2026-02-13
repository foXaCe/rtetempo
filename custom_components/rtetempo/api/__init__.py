"""RTE Tempo API client package."""

from .auth import RTETempoAuth
from .client import (
    RTETempoClient,
    adjust_tempo_time,
    parse_rte_api_date,
    parse_rte_api_datetime,
)
from .exceptions import (
    RTETempoAuthError,
    RTETempoClientError,
    RTETempoConnectionError,
    RTETempoError,
    RTETempoRateLimitError,
    RTETempoServerError,
)
from .models import TempoData, TempoDay

__all__ = [
    "RTETempoAuth",
    "RTETempoClient",
    "RTETempoAuthError",
    "RTETempoClientError",
    "RTETempoConnectionError",
    "RTETempoError",
    "RTETempoRateLimitError",
    "RTETempoServerError",
    "TempoData",
    "TempoDay",
    "adjust_tempo_time",
    "parse_rte_api_date",
    "parse_rte_api_datetime",
]
