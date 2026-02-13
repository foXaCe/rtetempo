"""Tests for the async OAuth2 token manager."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from custom_components.rtetempo.api.auth import _TOKEN_EXPIRY_MARGIN, RTETempoAuth
from custom_components.rtetempo.api.exceptions import (
    RTETempoAuthError,
    RTETempoConnectionError,
)


@pytest.fixture
def mock_session():
    """Create a mock aiohttp session."""
    return MagicMock(spec=aiohttp.ClientSession)


def _make_token_response(status=200, json_data=None):
    """Create a mock context manager for session.post."""
    if json_data is None:
        json_data = {"access_token": "test_token", "expires_in": 7200}
    resp = AsyncMock()
    resp.status = status
    resp.json = AsyncMock(return_value=json_data)
    resp.text = AsyncMock(return_value="error text")
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


class TestRTETempoAuth:
    """Tests for RTETempoAuth."""

    @pytest.mark.asyncio
    async def test_fetch_token_success(self, mock_session):
        auth = RTETempoAuth(mock_session, "client_id", "client_secret")
        mock_session.post.return_value = _make_token_response()
        token = await auth.async_get_access_token()
        assert token == "test_token"
        mock_session.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_token_cached_until_expiry(self, mock_session):
        auth = RTETempoAuth(mock_session, "client_id", "client_secret")
        mock_session.post.return_value = _make_token_response()
        token1 = await auth.async_get_access_token()
        # Second call should not trigger another POST
        mock_session.post.reset_mock()
        token2 = await auth.async_get_access_token()
        assert token1 == token2
        mock_session.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_token_refreshed_when_expired(self, mock_session):
        auth = RTETempoAuth(mock_session, "client_id", "client_secret")
        mock_session.post.return_value = _make_token_response()
        await auth.async_get_access_token()
        # Simulate token expiry
        auth._token_expiry = time.monotonic() - 1
        mock_session.post.return_value = _make_token_response(
            json_data={"access_token": "new_token", "expires_in": 7200}
        )
        token = await auth.async_get_access_token()
        assert token == "new_token"

    @pytest.mark.asyncio
    async def test_401_raises_auth_error(self, mock_session):
        auth = RTETempoAuth(mock_session, "bad_id", "bad_secret")
        mock_session.post.return_value = _make_token_response(status=401)
        with pytest.raises(RTETempoAuthError, match="401"):
            await auth.async_get_access_token()

    @pytest.mark.asyncio
    async def test_500_raises_auth_error(self, mock_session):
        auth = RTETempoAuth(mock_session, "id", "secret")
        mock_session.post.return_value = _make_token_response(status=500)
        with pytest.raises(RTETempoAuthError, match="500"):
            await auth.async_get_access_token()

    @pytest.mark.asyncio
    async def test_connection_error(self, mock_session):
        auth = RTETempoAuth(mock_session, "id", "secret")
        mock_session.post.side_effect = aiohttp.ClientError("offline")
        with pytest.raises(RTETempoConnectionError, match="Connection error"):
            await auth.async_get_access_token()

    @pytest.mark.asyncio
    async def test_timeout_error(self, mock_session):
        auth = RTETempoAuth(mock_session, "id", "secret")
        mock_session.post.side_effect = TimeoutError("timed out")
        with pytest.raises(RTETempoConnectionError, match="Timeout"):
            await auth.async_get_access_token()

    @pytest.mark.asyncio
    async def test_invalid_json_response(self, mock_session):
        auth = RTETempoAuth(mock_session, "id", "secret")
        mock_session.post.return_value = _make_token_response(
            json_data={"unexpected": "format"}
        )
        with pytest.raises(RTETempoAuthError, match="Invalid token response"):
            await auth.async_get_access_token()

    @pytest.mark.asyncio
    async def test_expiry_margin_applied(self, mock_session):
        auth = RTETempoAuth(mock_session, "id", "secret")
        mock_session.post.return_value = _make_token_response(
            json_data={"access_token": "tok", "expires_in": 100}
        )
        before = time.monotonic()
        await auth.async_get_access_token()
        # Token expiry should be ~(now + 100 - 60)
        assert auth._token_expiry < before + 100
        assert auth._token_expiry >= before + 100 - _TOKEN_EXPIRY_MARGIN - 1
