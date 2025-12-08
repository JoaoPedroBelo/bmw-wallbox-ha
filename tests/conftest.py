"""Fixtures for BMW Wallbox tests."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_coordinator():
    """Mock BMWWallboxCoordinator."""
    coordinator = MagicMock()
    coordinator.data = {
        "connected": True,
        "charging_state": "Charging",
        "power": 7000.0,
        "energy_total": 25.5,
        "current": 30.0,
        "voltage": 230.0,
        "transaction_id": "test-transaction-123",
        "connector_status": "Charging",
        "evse_id": 1,
        "connector_id": 1,
        "phases_used": 1,
        "current_limit": 32.0,
    }
    coordinator.device_info = {
        "model": "EIAW-E22KTSE6B04",
        "vendor": "BMW",
        "serial_number": "TEST123",
        "firmware_version": "1.0.0",
    }
    coordinator.current_transaction_id = "test-transaction-123"
    coordinator.async_start_charging = AsyncMock(return_value=True)
    coordinator.async_stop_charging = AsyncMock(return_value=True)
    coordinator.async_set_current_limit = AsyncMock(return_value=True)
    coordinator.async_set_updated_data = MagicMock()
    return coordinator


@pytest.fixture
def mock_config_entry():
    """Mock ConfigEntry."""
    entry = MagicMock()
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


@pytest.fixture
def mock_wallbox_charge_point():
    """Mock WallboxChargePoint."""
    with patch("custom_components.bmw_wallbox.coordinator.WallboxChargePoint") as mock:
        charge_point = AsyncMock()
        charge_point.current_transaction_id = "test-transaction-123"
        charge_point.call = AsyncMock()
        mock.return_value = charge_point
        yield charge_point
