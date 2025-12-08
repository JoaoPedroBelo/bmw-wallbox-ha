"""Test BMW Wallbox integration setup and teardown."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from custom_components.bmw_wallbox import (
    DOMAIN,
    PLATFORMS,
    async_setup_entry,
    async_unload_entry,
)


@pytest.fixture
def mock_hass():
    """Mock HomeAssistant."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    return hass


@pytest.fixture
def mock_config_entry():
    """Mock ConfigEntry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.data = {
        "port": 9000,
        "ssl_cert": "/ssl/fullchain.pem",
        "ssl_key": "/ssl/privkey.pem",
        "charge_point_id": "DE*BMW*TEST123",
        "rfid_token": "00000000000000",
        "max_current": 32,
    }
    return entry


async def test_platforms_defined():
    """Test that platforms are correctly defined."""
    assert Platform.SENSOR in PLATFORMS
    assert Platform.BINARY_SENSOR in PLATFORMS
    assert Platform.BUTTON in PLATFORMS
    assert len(PLATFORMS) == 3


async def test_async_setup_entry(mock_hass, mock_config_entry):
    """Test successful setup of a config entry."""
    with patch(
        "custom_components.bmw_wallbox.BMWWallboxCoordinator"
    ) as mock_coordinator_class:
        mock_coordinator = MagicMock()
        mock_coordinator.async_start_server = AsyncMock()
        mock_coordinator_class.return_value = mock_coordinator
        
        result = await async_setup_entry(mock_hass, mock_config_entry)
        
        assert result is True
        assert DOMAIN in mock_hass.data
        assert mock_config_entry.entry_id in mock_hass.data[DOMAIN]
        assert mock_hass.data[DOMAIN][mock_config_entry.entry_id] == mock_coordinator
        
        # Verify coordinator was created with correct config
        mock_coordinator_class.assert_called_once_with(mock_hass, mock_config_entry.data)
        
        # Verify server was started
        mock_coordinator.async_start_server.assert_called_once()
        
        # Verify platforms were set up
        mock_hass.config_entries.async_forward_entry_setups.assert_called_once_with(
            mock_config_entry, PLATFORMS
        )


async def test_async_setup_entry_server_start_fails(mock_hass, mock_config_entry):
    """Test setup fails when server cannot start."""
    with patch(
        "custom_components.bmw_wallbox.BMWWallboxCoordinator"
    ) as mock_coordinator_class:
        mock_coordinator = MagicMock()
        mock_coordinator.async_start_server = AsyncMock(
            side_effect=Exception("Failed to start server")
        )
        mock_coordinator_class.return_value = mock_coordinator
        
        with pytest.raises(ConfigEntryNotReady):
            await async_setup_entry(mock_hass, mock_config_entry)
        
        # Data should be set up even if server fails
        assert DOMAIN in mock_hass.data
        assert mock_config_entry.entry_id in mock_hass.data[DOMAIN]


async def test_async_unload_entry(mock_hass, mock_config_entry):
    """Test successful unload of a config entry."""
    # Set up coordinator in hass.data
    mock_coordinator = MagicMock()
    mock_coordinator.async_stop_server = AsyncMock()
    mock_hass.data[DOMAIN] = {mock_config_entry.entry_id: mock_coordinator}
    
    result = await async_unload_entry(mock_hass, mock_config_entry)
    
    assert result is True
    
    # Verify platforms were unloaded
    mock_hass.config_entries.async_unload_platforms.assert_called_once_with(
        mock_config_entry, PLATFORMS
    )
    
    # Verify server was stopped
    mock_coordinator.async_stop_server.assert_called_once()
    
    # Verify coordinator was removed from hass.data
    assert mock_config_entry.entry_id not in mock_hass.data[DOMAIN]


async def test_async_unload_entry_platforms_fail(mock_hass, mock_config_entry):
    """Test unload when platforms fail to unload."""
    mock_coordinator = MagicMock()
    mock_coordinator.async_stop_server = AsyncMock()
    mock_hass.data[DOMAIN] = {mock_config_entry.entry_id: mock_coordinator}
    
    # Make platform unload fail
    mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=False)
    
    result = await async_unload_entry(mock_hass, mock_config_entry)
    
    assert result is False
    
    # Verify server was NOT stopped since platforms failed to unload
    mock_coordinator.async_stop_server.assert_not_called()
    
    # Verify coordinator was NOT removed from hass.data
    assert mock_config_entry.entry_id in mock_hass.data[DOMAIN]


async def test_multiple_entries(mock_hass):
    """Test multiple config entries can coexist."""
    entry1 = MagicMock(spec=ConfigEntry)
    entry1.entry_id = "entry_1"
    entry1.data = {
        "port": 9000,
        "ssl_cert": "/ssl/fullchain.pem",
        "ssl_key": "/ssl/privkey.pem",
        "charge_point_id": "DE*BMW*TEST1",
    }
    
    entry2 = MagicMock(spec=ConfigEntry)
    entry2.entry_id = "entry_2"
    entry2.data = {
        "port": 9001,
        "ssl_cert": "/ssl/fullchain.pem",
        "ssl_key": "/ssl/privkey.pem",
        "charge_point_id": "DE*BMW*TEST2",
    }
    
    with patch(
        "custom_components.bmw_wallbox.BMWWallboxCoordinator"
    ) as mock_coordinator_class:
        mock_coordinator1 = MagicMock()
        mock_coordinator1.async_start_server = AsyncMock()
        mock_coordinator2 = MagicMock()
        mock_coordinator2.async_start_server = AsyncMock()
        
        mock_coordinator_class.side_effect = [mock_coordinator1, mock_coordinator2]
        
        # Set up both entries
        result1 = await async_setup_entry(mock_hass, entry1)
        result2 = await async_setup_entry(mock_hass, entry2)
        
        assert result1 is True
        assert result2 is True
        assert len(mock_hass.data[DOMAIN]) == 2
        assert mock_hass.data[DOMAIN]["entry_1"] == mock_coordinator1
        assert mock_hass.data[DOMAIN]["entry_2"] == mock_coordinator2
