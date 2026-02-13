"""Tests for the config flow."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.data_entry_flow import FlowResultType
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError
from requests.exceptions import ConnectionError as RequestsConnectionError

from custom_components.rtetempo.api_worker import BadRequest, ServerError, UnexpectedError
from custom_components.rtetempo.config_flow import ConfigFlow, OptionsFlowHandler
from custom_components.rtetempo.const import (
    CONFIG_CLIEND_SECRET,
    CONFIG_CLIENT_ID,
    DOMAIN,
    OPTION_ADJUSTED_DAYS,
)


@pytest.fixture
def mock_hass():
    """Create a mock HomeAssistant instance."""
    hass = MagicMock()
    hass.async_add_executor_job = AsyncMock(side_effect=lambda f: f())
    return hass


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
        flow = ConfigFlow()
        flow.hass = mock_hass
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = MagicMock()
        flow.async_create_entry = MagicMock(return_value={"type": FlowResultType.CREATE_ENTRY})
        with patch(
            "custom_components.rtetempo.config_flow.application_tester"
        ):
            result = await flow.async_step_user(
                {CONFIG_CLIENT_ID: "my_id", CONFIG_CLIEND_SECRET: "my_secret"}
            )
        assert result["type"] == FlowResultType.CREATE_ENTRY

    @pytest.mark.asyncio
    async def test_step_user_network_error(self, mock_hass):
        """Network error -> form with error."""
        flow = ConfigFlow()
        flow.hass = mock_hass
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = MagicMock()
        flow.async_show_form = MagicMock(return_value={"type": FlowResultType.FORM})
        with patch(
            "custom_components.rtetempo.config_flow.application_tester",
            side_effect=RequestsConnectionError("offline"),
        ):
            result = await flow.async_step_user(
                {CONFIG_CLIENT_ID: "id", CONFIG_CLIEND_SECRET: "secret"}
            )
        assert result["type"] == FlowResultType.FORM

    @pytest.mark.asyncio
    async def test_step_user_oauth_error(self, mock_hass):
        """OAuth error -> form with error."""
        flow = ConfigFlow()
        flow.hass = mock_hass
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = MagicMock()
        flow.async_show_form = MagicMock(return_value={"type": FlowResultType.FORM})
        with patch(
            "custom_components.rtetempo.config_flow.application_tester",
            side_effect=InvalidGrantError("bad grant"),
        ):
            result = await flow.async_step_user(
                {CONFIG_CLIENT_ID: "id", CONFIG_CLIEND_SECRET: "secret"}
            )
        assert result["type"] == FlowResultType.FORM

    @pytest.mark.asyncio
    async def test_step_user_bad_request(self, mock_hass):
        """BadRequest error -> form with error."""
        flow = ConfigFlow()
        flow.hass = mock_hass
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = MagicMock()
        flow.async_show_form = MagicMock(return_value={"type": FlowResultType.FORM})
        with patch(
            "custom_components.rtetempo.config_flow.application_tester",
            side_effect=BadRequest(400, "bad"),
        ):
            result = await flow.async_step_user(
                {CONFIG_CLIENT_ID: "id", CONFIG_CLIEND_SECRET: "secret"}
            )
        assert result["type"] == FlowResultType.FORM

    @pytest.mark.asyncio
    async def test_step_user_server_error(self, mock_hass):
        """ServerError -> form with error."""
        flow = ConfigFlow()
        flow.hass = mock_hass
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = MagicMock()
        flow.async_show_form = MagicMock(return_value={"type": FlowResultType.FORM})
        with patch(
            "custom_components.rtetempo.config_flow.application_tester",
            side_effect=ServerError(500, "down"),
        ):
            result = await flow.async_step_user(
                {CONFIG_CLIENT_ID: "id", CONFIG_CLIEND_SECRET: "secret"}
            )
        assert result["type"] == FlowResultType.FORM

    @pytest.mark.asyncio
    async def test_step_user_unexpected_error(self, mock_hass):
        """UnexpectedError -> form with error."""
        flow = ConfigFlow()
        flow.hass = mock_hass
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = MagicMock()
        flow.async_show_form = MagicMock(return_value={"type": FlowResultType.FORM})
        with patch(
            "custom_components.rtetempo.config_flow.application_tester",
            side_effect=UnexpectedError(418, "teapot"),
        ):
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
