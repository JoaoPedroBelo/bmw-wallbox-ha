"""Test BMW Wallbox config flow."""

from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest

from custom_components.bmw_wallbox.config_flow import ConfigFlow


@pytest.fixture
def mock_setup_entry():
    """Mock setup entry."""
    with patch(
        "custom_components.bmw_wallbox.async_setup_entry",
        return_value=True,
    ) as mock:
        yield mock


async def test_form(hass: HomeAssistant, mock_setup_entry) -> None:
    """Test we get the form."""
    # Register the flow handler directly
    flow = ConfigFlow()
    flow.hass = hass

    result = await flow.async_step_user()

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {}


async def test_user_input_valid(hass: HomeAssistant, mock_setup_entry) -> None:
    """Test valid user input creates entry."""
    flow = ConfigFlow()
    flow.hass = hass
    flow.context = {"source": config_entries.SOURCE_USER}

    with patch("os.path.isfile", return_value=True):
        result = await flow.async_step_user(
            user_input={
                "port": 9000,
                "ssl_cert": "/ssl/fullchain.pem",
                "ssl_key": "/ssl/privkey.pem",
                "charge_point_id": "DE*BMW*TEST123",
                "rfid_token": "00000000000000",
                "max_current": 32,
            }
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "BMW Wallbox (DE*BMW*TEST123)"
    assert result["data"]["port"] == 9000


async def test_invalid_port(hass: HomeAssistant, mock_setup_entry) -> None:
    """Test invalid port shows error."""
    flow = ConfigFlow()
    flow.hass = hass
    flow.context = {"source": config_entries.SOURCE_USER}

    with patch("os.path.isfile", return_value=True):
        result = await flow.async_step_user(
            user_input={
                "port": 70000,  # Invalid port
                "ssl_cert": "/ssl/fullchain.pem",
                "ssl_key": "/ssl/privkey.pem",
                "charge_point_id": "DE*BMW*TEST123",
                "rfid_token": "",
                "max_current": 32,
            }
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_port"}


async def test_invalid_ssl_cert(hass: HomeAssistant, mock_setup_entry) -> None:
    """Test invalid SSL cert shows error."""
    flow = ConfigFlow()
    flow.hass = hass
    flow.context = {"source": config_entries.SOURCE_USER}

    with patch("os.path.isfile", return_value=False):
        result = await flow.async_step_user(
            user_input={
                "port": 9000,
                "ssl_cert": "/nonexistent/cert.pem",
                "ssl_key": "/ssl/privkey.pem",
                "charge_point_id": "DE*BMW*TEST123",
                "rfid_token": "",
                "max_current": 32,
            }
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_ssl_cert"}


async def test_duplicate_entry(hass: HomeAssistant, mock_setup_entry) -> None:
    """Test duplicate entry is aborted."""
    from homeassistant.data_entry_flow import AbortFlow

    flow = ConfigFlow()
    flow.hass = hass
    flow.context = {"source": config_entries.SOURCE_USER}

    # Mock _abort_if_unique_id_configured to raise AbortFlow
    async def mock_set_unique_id(unique_id):
        flow._unique_id = unique_id

    def mock_abort_if_configured():
        raise AbortFlow("already_configured")

    with (
        patch("os.path.isfile", return_value=True),
        patch.object(flow, "async_set_unique_id", mock_set_unique_id),
        patch.object(flow, "_abort_if_unique_id_configured", mock_abort_if_configured),
        pytest.raises(AbortFlow, match="already_configured"),
    ):
        await flow.async_step_user(
            user_input={
                "port": 9000,
                "ssl_cert": "/ssl/fullchain.pem",
                "ssl_key": "/ssl/privkey.pem",
                "charge_point_id": "DE*BMW*TEST123",
                "rfid_token": "",
                "max_current": 32,
            }
        )
