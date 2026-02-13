"""Tests for the config flow."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.data_entry_flow import FlowResultType

from custom_components.rtetempo.api import (
    RTETempoAuthError,
    RTETempoClientError,
    RTETempoConnectionError,
    RTETempoError,
    RTETempoServerError,
)
from custom_components.rtetempo.config_flow import ConfigFlow, OptionsFlowHandler
from custom_components.rtetempo.const import (
    CONFIG_CLIEND_SECRET,
    CONFIG_CLIENT_ID,
    OPTION_ADJUSTED_DAYS,
)


@pytest.fixture
def mock_hass():
    """Create a mock HomeAssistant instance."""
    hass = MagicMock()
    hass.data = {}
    return hass


def _setup_flow(mock_hass) -> ConfigFlow:
    """Create a ConfigFlow with mocked internals."""
    flow = ConfigFlow()
    flow.hass = mock_hass
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = MagicMock()
    return flow


class TestConfigFlow:
    """Tests for the ConfigFlow."""

    @pytest.mark.asyncio
    async def test_step_user_form_shown(self, mock_hass):
        """No input -> form is shown."""
        flow = ConfigFlow()
        flow.hass = mock_hass
        result = await flow.async_step_user(None)
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"

    @pytest.mark.asyncio
    async def test_step_user_success(self, mock_hass):
        """Valid credentials -> entry created."""
        flow = _setup_flow(mock_hass)
        flow.async_create_entry = MagicMock(return_value={"type": FlowResultType.CREATE_ENTRY})
        with patch(
            "custom_components.rtetempo.config_flow.RTETempoClient"
        ) as mock_client_cls, patch(
            "custom_components.rtetempo.config_flow.RTETempoAuth"
        ), patch(
            "custom_components.rtetempo.config_flow.async_get_clientsession"
        ):
            mock_client_cls.return_value.async_test_credentials = AsyncMock()
            result = await flow.async_step_user(
                {CONFIG_CLIENT_ID: "my_id", CONFIG_CLIEND_SECRET: "my_secret"}
            )
        assert result["type"] == FlowResultType.CREATE_ENTRY

    @pytest.mark.asyncio
    async def test_step_user_auth_error(self, mock_hass):
        """Auth error -> form with oauth_error."""
        flow = _setup_flow(mock_hass)
        flow.async_show_form = MagicMock(return_value={"type": FlowResultType.FORM})
        with patch(
            "custom_components.rtetempo.config_flow.RTETempoClient"
        ) as mock_client_cls, patch(
            "custom_components.rtetempo.config_flow.RTETempoAuth"
        ), patch(
            "custom_components.rtetempo.config_flow.async_get_clientsession"
        ):
            mock_client_cls.return_value.async_test_credentials = AsyncMock(
                side_effect=RTETempoAuthError("bad grant")
            )
            result = await flow.async_step_user(
                {CONFIG_CLIENT_ID: "id", CONFIG_CLIEND_SECRET: "secret"}
            )
        assert result["type"] == FlowResultType.FORM

    @pytest.mark.asyncio
    async def test_step_user_connection_error(self, mock_hass):
        """Connection error -> form with network_error."""
        flow = _setup_flow(mock_hass)
        flow.async_show_form = MagicMock(return_value={"type": FlowResultType.FORM})
        with patch(
            "custom_components.rtetempo.config_flow.RTETempoClient"
        ) as mock_client_cls, patch(
            "custom_components.rtetempo.config_flow.RTETempoAuth"
        ), patch(
            "custom_components.rtetempo.config_flow.async_get_clientsession"
        ):
            mock_client_cls.return_value.async_test_credentials = AsyncMock(
                side_effect=RTETempoConnectionError("offline")
            )
            result = await flow.async_step_user(
                {CONFIG_CLIENT_ID: "id", CONFIG_CLIEND_SECRET: "secret"}
            )
        assert result["type"] == FlowResultType.FORM

    @pytest.mark.asyncio
    async def test_step_user_client_error(self, mock_hass):
        """Client error -> form with http_client_error."""
        flow = _setup_flow(mock_hass)
        flow.async_show_form = MagicMock(return_value={"type": FlowResultType.FORM})
        with patch(
            "custom_components.rtetempo.config_flow.RTETempoClient"
        ) as mock_client_cls, patch(
            "custom_components.rtetempo.config_flow.RTETempoAuth"
        ), patch(
            "custom_components.rtetempo.config_flow.async_get_clientsession"
        ):
            mock_client_cls.return_value.async_test_credentials = AsyncMock(
                side_effect=RTETempoClientError(400, "bad request")
            )
            result = await flow.async_step_user(
                {CONFIG_CLIENT_ID: "id", CONFIG_CLIEND_SECRET: "secret"}
            )
        assert result["type"] == FlowResultType.FORM

    @pytest.mark.asyncio
    async def test_step_user_server_error(self, mock_hass):
        """Server error -> form with http_server_error."""
        flow = _setup_flow(mock_hass)
        flow.async_show_form = MagicMock(return_value={"type": FlowResultType.FORM})
        with patch(
            "custom_components.rtetempo.config_flow.RTETempoClient"
        ) as mock_client_cls, patch(
            "custom_components.rtetempo.config_flow.RTETempoAuth"
        ), patch(
            "custom_components.rtetempo.config_flow.async_get_clientsession"
        ):
            mock_client_cls.return_value.async_test_credentials = AsyncMock(
                side_effect=RTETempoServerError(500, "down")
            )
            result = await flow.async_step_user(
                {CONFIG_CLIENT_ID: "id", CONFIG_CLIEND_SECRET: "secret"}
            )
        assert result["type"] == FlowResultType.FORM

    @pytest.mark.asyncio
    async def test_step_user_unexpected_error(self, mock_hass):
        """Unexpected error -> form with http_unexpected_error."""
        flow = _setup_flow(mock_hass)
        flow.async_show_form = MagicMock(return_value={"type": FlowResultType.FORM})
        with patch(
            "custom_components.rtetempo.config_flow.RTETempoClient"
        ) as mock_client_cls, patch(
            "custom_components.rtetempo.config_flow.RTETempoAuth"
        ), patch(
            "custom_components.rtetempo.config_flow.async_get_clientsession"
        ):
            mock_client_cls.return_value.async_test_credentials = AsyncMock(
                side_effect=RTETempoError("teapot")
            )
            result = await flow.async_step_user(
                {CONFIG_CLIENT_ID: "id", CONFIG_CLIEND_SECRET: "secret"}
            )
        assert result["type"] == FlowResultType.FORM

    def test_async_get_options_flow(self):
        """Options flow handler is returned."""
        config_entry = MagicMock()
        result = ConfigFlow.async_get_options_flow(config_entry)
        assert isinstance(result, OptionsFlowHandler)


class TestOptionsFlowHandler:
    """Tests for the OptionsFlowHandler."""

    @pytest.mark.asyncio
    async def test_step_init_no_input(self):
        """No input -> form shown."""
        handler = OptionsFlowHandler()
        mock_entry = MagicMock()
        mock_entry.options = {OPTION_ADJUSTED_DAYS: False}
        with patch.object(
            type(handler), "config_entry", new_callable=lambda: property(lambda self: mock_entry)
        ):
            handler.async_show_form = MagicMock(return_value={"type": FlowResultType.FORM})
            result = await handler.async_step_init(None)
        assert result["type"] == FlowResultType.FORM

    @pytest.mark.asyncio
    async def test_step_init_with_input(self):
        """With input -> entry created."""
        handler = OptionsFlowHandler()
        handler.async_create_entry = MagicMock(
            return_value={"type": FlowResultType.CREATE_ENTRY}
        )
        result = await handler.async_step_init({OPTION_ADJUSTED_DAYS: True})
        assert result["type"] == FlowResultType.CREATE_ENTRY
