"""Test BMW Wallbox config flow."""

from unittest.mock import MagicMock, patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest

from custom_components.bmw_wallbox.config_flow import ConfigFlow, OptionsFlow


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


def _mock_config_entry(data, options=None):
    """Create a mock ConfigEntry compatible with all HA versions."""
    entry = MagicMock(spec_set=["data", "options"])
    entry.data = data
    entry.options = options or {}
    return entry


async def test_options_flow_shows_current_values(hass: HomeAssistant) -> None:
    """Test options flow shows current config values."""
    entry = _mock_config_entry(
        data={
            "port": 9000,
            "ssl_cert": "/ssl/fullchain.pem",
            "ssl_key": "/ssl/privkey.pem",
            "charge_point_id": "DE*BMW*TEST123",
            "rfid_token": "MYTOKEN123",
            "max_current": 16,
            "scan_interval": 30,
        },
    )

    flow = OptionsFlow()
    flow.config_entry = entry
    flow.hass = hass

    result = await flow.async_step_init()
    assert result["type"] == FlowResultType.FORM

    schema = result["data_schema"]
    schema_dict = {str(k): k for k in schema.schema}
    assert "rfid_token" in schema_dict
    assert "max_current" in schema_dict
    assert "scan_interval" in schema_dict


async def test_options_flow_updates_values(hass: HomeAssistant) -> None:
    """Test options flow saves updated values."""
    entry = _mock_config_entry(
        data={
            "port": 9000,
            "ssl_cert": "/ssl/fullchain.pem",
            "ssl_key": "/ssl/privkey.pem",
            "charge_point_id": "DE*BMW*TEST123",
            "rfid_token": "",
            "max_current": 32,
            "scan_interval": 30,
        },
    )

    flow = OptionsFlow()
    flow.config_entry = entry
    flow.hass = hass

    result = await flow.async_step_init(
        user_input={
            "rfid_token": "NEWTOKEN456",
            "max_current": 16,
            "scan_interval": 10,
        }
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["rfid_token"] == "NEWTOKEN456"
    assert result["data"]["max_current"] == 16
    assert result["data"]["scan_interval"] == 10
