"""Test BMW Wallbox config flow."""
from unittest.mock import patch

import pytest

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.bmw_wallbox.config_flow import InvalidPort, InvalidSSLCert, InvalidSSLKey
from custom_components.bmw_wallbox.const import DOMAIN


async def test_form(hass: HomeAssistant) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {}


async def test_user_input_valid(hass: HomeAssistant) -> None:
    """Test valid user input creates entry."""
    with patch("os.path.isfile", return_value=True):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                "port": 9000,
                "ssl_cert": "/ssl/fullchain.pem",
                "ssl_key": "/ssl/privkey.pem",
                "charge_point_id": "DE*BMW*TEST123",
                "rfid_token": "00000000000000",
                "max_current": 32,
            },
        )
    
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "BMW Wallbox (DE*BMW*TEST123)"
    assert result["data"]["port"] == 9000


async def test_invalid_port(hass: HomeAssistant) -> None:
    """Test invalid port shows error."""
    with patch("os.path.isfile", return_value=True):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                "port": 70000,  # Invalid port
                "ssl_cert": "/ssl/fullchain.pem",
                "ssl_key": "/ssl/privkey.pem",
                "charge_point_id": "DE*BMW*TEST123",
            },
        )
    
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_port"}


async def test_invalid_ssl_cert(hass: HomeAssistant) -> None:
    """Test invalid SSL cert shows error."""
    with patch("os.path.isfile", return_value=False):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                "port": 9000,
                "ssl_cert": "/nonexistent/cert.pem",
                "ssl_key": "/ssl/privkey.pem",
                "charge_point_id": "DE*BMW*TEST123",
            },
        )
    
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_ssl_cert"}


async def test_duplicate_entry(hass: HomeAssistant) -> None:
    """Test duplicate entry is aborted."""
    # Create first entry
    with patch("os.path.isfile", return_value=True):
        result1 = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                "port": 9000,
                "ssl_cert": "/ssl/fullchain.pem",
                "ssl_key": "/ssl/privkey.pem",
                "charge_point_id": "DE*BMW*TEST123",
            },
        )
    
    assert result1["type"] == FlowResultType.CREATE_ENTRY
    
    # Try to create duplicate
    with patch("os.path.isfile", return_value=True):
        result2 = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                "port": 9000,
                "ssl_cert": "/ssl/fullchain.pem",
                "ssl_key": "/ssl/privkey.pem",
                "charge_point_id": "DE*BMW*TEST123",
            },
        )
    
    assert result2["type"] == FlowResultType.ABORT
    assert result2["reason"] == "already_configured"

