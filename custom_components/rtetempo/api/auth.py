"""Async OAuth2 token manager for the RTE API."""

from __future__ import annotations

import asyncio
import logging
import time

import aiohttp

from ..const import API_TOKEN_ENDPOINT, USER_AGENT
from .exceptions import RTETempoAuthError, RTETempoConnectionError

_LOGGER = logging.getLogger(__name__)

_TOKEN_EXPIRY_MARGIN = 60  # refresh 60s before expiration


class RTETempoAuth:
    """Async OAuth2 client credentials token manager."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        client_id: str,
        client_secret: str,
    ) -> None:
        """Initialize the auth manager."""
        self._session = session
        self._client_id = client_id
        self._client_secret = client_secret
        self._access_token: str | None = None
        self._token_expiry: float = 0.0  # monotonic timestamp
        self._lock = asyncio.Lock()

    async def async_get_access_token(self) -> str:
        """Get a valid access token, refreshing if necessary."""
        # Fast path: token still valid
        if self._access_token and time.monotonic() < self._token_expiry:
            return self._access_token
        # Slow path: acquire lock and double-check
        async with self._lock:
            if self._access_token and time.monotonic() < self._token_expiry:
                return self._access_token
            return await self._async_fetch_token()

    async def _async_fetch_token(self) -> str:
        """Fetch a new OAuth2 token via client credentials grant."""
        _LOGGER.debug("Requesting new OAuth2 access token")
        auth = aiohttp.BasicAuth(self._client_id, self._client_secret)
        try:
            async with self._session.post(
                API_TOKEN_ENDPOINT,
                auth=auth,
                data={"grant_type": "client_credentials"},
                headers={"User-Agent": USER_AGENT},
            ) as resp:
                if resp.status == 401:
                    raise RTETempoAuthError("Invalid client credentials (HTTP 401)")
                if resp.status != 200:
                    text = await resp.text()
                    raise RTETempoAuthError(
                        f"Token request failed (HTTP {resp.status}): {text}"
                    )
                data = await resp.json()
        except aiohttp.ClientError as err:
            raise RTETempoConnectionError(
                f"Connection error during token request: {err}"
            ) from err
        except TimeoutError as err:
            raise RTETempoConnectionError(
                f"Timeout during token request: {err}"
            ) from err

        try:
            access_token = data["access_token"]
            expires_in = int(data.get("expires_in", 3600))
        except (KeyError, TypeError, ValueError) as err:
            raise RTETempoAuthError(
                f"Invalid token response: {err}"
            ) from err

        self._access_token = access_token
        self._token_expiry = time.monotonic() + expires_in - _TOKEN_EXPIRY_MARGIN
        _LOGGER.debug("OAuth2 token acquired, expires in %ds", expires_in)
        return access_token
