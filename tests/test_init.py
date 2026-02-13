"""Tests for the integration __init__ module."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.rtetempo import (
    PLATFORMS,
    async_migrate_entry,
    async_setup_entry,
    async_unload_entry,
    update_listener,
)
from custom_components.rtetempo.const import (
    CONFIG_CLIEND_SECRET,
    CONFIG_CLIENT_ID,
    DOMAIN,
    OPTION_ADJUSTED_DAYS,
)


@pytest.fixture
def mock_hass():
    """Create a mock HomeAssistant."""
    hass = MagicMock()
    hass.data = {}
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    hass.bus = MagicMock()
    return hass


@pytest.fixture
def mock_entry():
    """Create a mock ConfigEntry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.title = "Test RTE Tempo"
    entry.data = {
        CONFIG_CLIENT_ID: "my_client_id",
        CONFIG_CLIEND_SECRET: "my_client_secret",
    }
    entry.options = {OPTION_ADJUSTED_DAYS: False}
    entry.async_on_unload = MagicMock()
    entry.add_update_listener = MagicMock()
    return entry


class TestAsyncMigrateEntry:
    """Tests for async_migrate_entry."""

    @pytest.mark.asyncio
    async def test_migrate_v1_returns_true(self, mock_hass, mock_entry):
        """Test migration from version 1 succeeds."""
        mock_entry.version = 1
        result = await async_migrate_entry(mock_hass, mock_entry)
        assert result is True


class TestAsyncSetupEntry:
    """Tests for async_setup_entry."""

    @pytest.mark.asyncio
    async def test_setup_success(self, mock_hass, mock_entry):
        """Test successful setup creates worker and forwards platforms."""
        with patch(
            "custom_components.rtetempo.APIWorker"
        ) as mock_worker_cls:
            mock_worker = MagicMock()
            mock_worker_cls.return_value = mock_worker
            result = await async_setup_entry(mock_hass, mock_entry)
        assert result is True
        mock_worker.start.assert_called_once()
        assert DOMAIN in mock_hass.data
        assert mock_entry.entry_id in mock_hass.data[DOMAIN]
        mock_hass.config_entries.async_forward_entry_setups.assert_called_once_with(
            mock_entry, PLATFORMS
        )

    @pytest.mark.asyncio
    async def test_setup_creates_domain_dict(self, mock_hass, mock_entry):
        """Test setup creates hass.data[DOMAIN] if not present."""
        assert DOMAIN not in mock_hass.data
        with patch(
            "custom_components.rtetempo.APIWorker"
        ) as mock_worker_cls:
            mock_worker_cls.return_value = MagicMock()
            await async_setup_entry(mock_hass, mock_entry)
        assert DOMAIN in mock_hass.data

    @pytest.mark.asyncio
    async def test_setup_existing_domain_dict(self, mock_hass, mock_entry):
        """Test setup works when hass.data[DOMAIN] already exists."""
        mock_hass.data[DOMAIN] = {}
        with patch(
            "custom_components.rtetempo.APIWorker"
        ) as mock_worker_cls:
            mock_worker_cls.return_value = MagicMock()
            await async_setup_entry(mock_hass, mock_entry)
        assert mock_entry.entry_id in mock_hass.data[DOMAIN]

    @pytest.mark.asyncio
    async def test_setup_registers_stop_listener(self, mock_hass, mock_entry):
        """Test setup registers the stop listener."""
        with patch(
            "custom_components.rtetempo.APIWorker"
        ) as mock_worker_cls:
            mock_worker = MagicMock()
            mock_worker_cls.return_value = mock_worker
            await async_setup_entry(mock_hass, mock_entry)
        mock_hass.bus.async_listen_once.assert_called_once()


class TestAsyncUnloadEntry:
    """Tests for async_unload_entry."""

    @pytest.mark.asyncio
    async def test_unload_success(self, mock_hass, mock_entry):
        """Test successful unload removes entry data."""
        mock_hass.data[DOMAIN] = {mock_entry.entry_id: MagicMock()}
        result = await async_unload_entry(mock_hass, mock_entry)
        assert result is True
        assert mock_entry.entry_id not in mock_hass.data[DOMAIN]

    @pytest.mark.asyncio
    async def test_unload_failure(self, mock_hass, mock_entry):
        """Test failed unload keeps entry data."""
        mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=False)
        mock_hass.data[DOMAIN] = {mock_entry.entry_id: MagicMock()}
        result = await async_unload_entry(mock_hass, mock_entry)
        assert result is False
        assert mock_entry.entry_id in mock_hass.data[DOMAIN]


class TestUpdateListener:
    """Tests for update_listener."""

    @pytest.mark.asyncio
    async def test_update_options(self, mock_hass, mock_entry):
        """Test options are updated on the worker."""
        mock_worker = MagicMock()
        mock_hass.data[DOMAIN] = {mock_entry.entry_id: mock_worker}
        mock_entry.options = {OPTION_ADJUSTED_DAYS: True}
        await update_listener(mock_hass, mock_entry)
        mock_worker.update_options.assert_called_once_with(True)

    @pytest.mark.asyncio
    async def test_update_listener_missing_worker(self, mock_hass, mock_entry):
        """Test update listener handles missing worker gracefully."""
        mock_hass.data[DOMAIN] = {}
        # Should not raise
        await update_listener(mock_hass, mock_entry)
