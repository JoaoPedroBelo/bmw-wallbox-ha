"""Test BMW Wallbox coordinator."""

import asyncio
import contextlib
from datetime import datetime
import json
import logging
from unittest.mock import AsyncMock, MagicMock, patch

from ocpp.v201 import call, call_result
from ocpp.v201.enums import ChargingProfilePurposeEnumType, MessageTriggerEnumType
import pytest

from custom_components.bmw_wallbox.coordinator import (
    OCPP_CALL_BACKSTOP_TIMEOUT,
    OCPP_RESPONSE_TIMEOUT,
    BMWWallboxCoordinator,
    WallboxChargePoint,
    _compute_live_current,
)


@pytest.fixture
def hass():
    """Mock HomeAssistant."""
    hass = MagicMock()
    hass.async_add_executor_job = AsyncMock(return_value=None)
    return hass


@pytest.fixture
def config():
    """Configuration for coordinator."""
    return {
        "port": 9000,
        "ssl_cert": "/ssl/fullchain.pem",
        "ssl_key": "/ssl/privkey.pem",
        "charge_point_id": "DE*BMW*TEST123",
        "rfid_token": "00000000000000",
        "max_current": 32,
    }


@pytest.fixture
def coordinator(hass, config):
    """Create coordinator."""
    return BMWWallboxCoordinator(hass, config)


@pytest.fixture
def mock_websocket():
    """Mock websocket."""
    ws = MagicMock()
    ws.request.path = "/DE*BMW*TEST123"
    return ws


@pytest.fixture
def charge_point(coordinator, mock_websocket):
    """Create charge point."""
    return WallboxChargePoint("DE*BMW*TEST123", mock_websocket, coordinator)


# ==============================================================================
# COORDINATOR INITIALIZATION TESTS
# ==============================================================================


async def test_coordinator_initialization(coordinator):
    """Test coordinator initializes with correct defaults."""
    assert coordinator.config["port"] == 9000
    assert coordinator.server is None
    assert coordinator.charge_point is None
    assert coordinator.current_transaction_id is None
    assert coordinator.data["connected"] is False
    assert coordinator.data["power"] == 0.0
    assert coordinator.data["charging_state"] == "Unknown"


async def test_coordinator_async_update_data(coordinator):
    """Test coordinator data update method."""
    coordinator.data["power"] = 5000.0

    result = await coordinator._async_update_data()

    assert result == coordinator.data
    assert result["power"] == 5000.0


# ==============================================================================
# OCPP MESSAGE HANDLER TESTS
# ==============================================================================


async def test_boot_notification_handler(charge_point):
    """Test BootNotification handler."""
    charging_station = {
        "model": "EIAW-E22KTSE6B04",
        "vendor_name": "BMW",
        "serial_number": "TEST123",
        "firmware_version": "1.0.0",
    }

    response = await charge_point.on_boot_notification(
        charging_station=charging_station, reason="PowerUp"
    )

    assert response.status == "Accepted"
    assert charge_point.coordinator.device_info["model"] == "EIAW-E22KTSE6B04"
    assert charge_point.coordinator.device_info["vendor"] == "BMW"
    assert charge_point.coordinator.device_info["serial_number"] == "TEST123"
    assert charge_point.coordinator.device_info["firmware_version"] == "1.0.0"


async def test_status_notification_handler(charge_point):
    """Test StatusNotification handler."""
    _response = await charge_point.on_status_notification(
        timestamp=datetime.utcnow().isoformat(),
        connector_status="Charging",
        evse_id=1,
        connector_id=1,
    )

    assert charge_point.coordinator.data["connector_status"] == "Charging"
    assert charge_point.coordinator.data["evse_id"] == 1
    assert charge_point.coordinator.data["connector_id"] == 1


async def test_heartbeat_handler(charge_point):
    """Test Heartbeat handler."""
    response = await charge_point.on_heartbeat()

    assert charge_point.coordinator.data["connected"] is True
    assert charge_point.coordinator.data["last_heartbeat"] is not None
    assert response.current_time is not None


async def test_meter_values_handler(charge_point):
    """Test MeterValues handler."""
    meter_value = [
        {
            "timestamp": datetime.utcnow().isoformat(),
            "sampled_value": [
                {
                    "measurand": "Power.Active.Import",
                    "value": "7200",
                    "phase": None,
                    "context": "Sample.Periodic",
                },
                {
                    "measurand": "Energy.Active.Import.Register",
                    "value": "25500",
                    "phase": None,
                    "context": "Sample.Periodic",
                },
            ],
        }
    ]

    _response = await charge_point.on_meter_values(evse_id=1, meter_value=meter_value)

    assert charge_point.coordinator.data["power"] == 7200.0
    assert charge_point.coordinator.data["energy_total"] == 25.5  # Converted to kWh


async def test_meter_values_current_phases(charge_point):
    """Test MeterValues with per-phase currents."""
    meter_value = [
        {
            "timestamp": datetime.utcnow().isoformat(),
            "sampled_value": [
                {"measurand": "Current.Import", "value": "10.5", "phase": "L1-N"},
                {"measurand": "Current.Import", "value": "11.2", "phase": "L2-N"},
                {"measurand": "Current.Import", "value": "9.8", "phase": "L3-N"},
            ],
        }
    ]

    await charge_point.on_meter_values(evse_id=1, meter_value=meter_value)

    assert charge_point.coordinator.data["current_l1"] == 10.5
    assert charge_point.coordinator.data["current_l2"] == 11.2
    assert charge_point.coordinator.data["current_l3"] == 9.8


async def test_meter_values_voltage_phases(charge_point):
    """Test MeterValues with per-phase voltages."""
    meter_value = [
        {
            "timestamp": datetime.utcnow().isoformat(),
            "sampled_value": [
                {"measurand": "Voltage", "value": "230", "phase": "L1-N"},
                {"measurand": "Voltage", "value": "231", "phase": "L2-N"},
                {"measurand": "Voltage", "value": "229", "phase": "L3-N"},
            ],
        }
    ]

    await charge_point.on_meter_values(evse_id=1, meter_value=meter_value)

    assert charge_point.coordinator.data["voltage_l1"] == 230.0
    assert charge_point.coordinator.data["voltage_l2"] == 231.0
    assert charge_point.coordinator.data["voltage_l3"] == 229.0


async def test_transaction_event_handler(charge_point):
    """Test TransactionEvent handler."""
    transaction_info = {
        "transaction_id": "test-tx-123",
        "charging_state": "Charging",
    }

    meter_value = [
        {
            "sampled_value": [
                {"measurand": "Power.Active.Import", "value": "7000"},
            ]
        }
    ]

    _response = await charge_point.on_transaction_event(
        event_type="Updated",
        timestamp=datetime.utcnow().isoformat(),
        trigger_reason="MeterValuePeriodic",
        seq_no=5,
        transaction_info=transaction_info,
        meter_value=meter_value,
    )

    assert charge_point.coordinator.data["transaction_id"] == "test-tx-123"
    assert charge_point.coordinator.data["charging_state"] == "Charging"
    assert charge_point.coordinator.data["power"] == 7000.0
    assert charge_point.coordinator.data["event_type"] == "Updated"
    assert charge_point.coordinator.data["trigger_reason"] == "MeterValuePeriodic"
    assert charge_point.coordinator.data["sequence_number"] == 5


async def test_transaction_event_calculates_current(charge_point):
    """Test TransactionEvent calculates current from power when not reported."""
    transaction_info = {
        "transaction_id": "test-tx-123",
        "charging_state": "Charging",
    }

    meter_value = [
        {
            "sampled_value": [
                {"measurand": "Power.Active.Import", "value": "7200"},  # 7200W
            ]
        }
    ]

    # Initialize with no current but voltage will be assumed as 230V
    charge_point.coordinator.data["current"] = 0
    charge_point.coordinator.data["voltage"] = 0
    charge_point.coordinator.data["phases_used"] = 1

    await charge_point.on_transaction_event(
        event_type="Updated",
        timestamp=datetime.utcnow().isoformat(),
        trigger_reason="MeterValuePeriodic",
        seq_no=5,
        transaction_info=transaction_info,
        meter_value=meter_value,
    )

    # Should calculate: I = 7200W / 230V ≈ 31.3A
    assert charge_point.coordinator.data["current"] is not None
    assert 31 <= charge_point.coordinator.data["current"] <= 32


async def test_transaction_event_derives_connector_status(charge_point):
    """Test TransactionEvent derives connector status from charging state."""
    transaction_info = {
        "transaction_id": "test-tx-123",
        "charging_state": "Charging",
    }

    charge_point.coordinator.data["connector_status"] = "Unknown"

    await charge_point.on_transaction_event(
        event_type="Updated",
        timestamp=datetime.utcnow().isoformat(),
        trigger_reason="ChargingStateChanged",
        seq_no=1,
        transaction_info=transaction_info,
    )

    assert charge_point.coordinator.data["connector_status"] == "Occupied"


async def test_notify_report_handler(charge_point):
    """Test NotifyReport handler."""
    response = await charge_point.on_notify_report(
        request_id=123,
        seq_no=1,
        generated_at=datetime.utcnow().isoformat(),
        report_data=[],
    )

    # Should not raise exception
    assert response is not None


async def test_security_event_notification_handler(charge_point):
    """Test SecurityEventNotification handler."""
    response = await charge_point.on_security_event_notification(
        type="SettingSystemTime",
        timestamp=datetime.utcnow().isoformat(),
    )

    # Should not raise exception
    assert response is not None


async def test_notify_event_handler(charge_point):
    """Test NotifyEvent handler.

    Some wallboxes send NotifyEvent frequently. The handler accepts it
    to prevent NotImplementedError spam in logs.
    """
    response = await charge_point.on_notify_event(
        generated_at=datetime.utcnow().isoformat(),
        seq_no=1,
        event_data=[
            {
                "event_id": 1,
                "timestamp": datetime.utcnow().isoformat(),
                "trigger": "Alerting",
                "actual_value": "true",
                "component": {"name": "Connector", "evse": {"id": 1}},
                "variable": {"name": "Available"},
            }
        ],
    )

    # Should not raise exception
    assert response is not None


async def test_notify_ev_charging_needs_handler(charge_point):
    """Test NotifyEVChargingNeeds handler (issue #14).

    BMW Wallbox Plus Gen 4 (Delta) sends NotifyEVChargingNeeds during the EV
    charging negotiation. The handler must accept it; otherwise the ocpp library
    raises NotImplementedError, breaking the message pump and stopping
    SetChargingProfile from being applied.
    """
    response = await charge_point.on_notify_ev_charging_needs(
        evse_id=1,
        charging_needs={
            "requested_energy_transfer": "AC_single_phase",
            "ac_charging_parameters": {
                "energy_amount": 10000,
                "ev_min_current": 6,
                "ev_max_current": 16,
                "ev_max_voltage": 230,
            },
        },
    )

    # Should not raise exception and must return an Accepted status
    assert response is not None
    assert response.status == "Accepted"


async def test_notify_charging_limit_handler(charge_point):
    """Test NotifyChargingLimit handler (issue #14).

    The BMW/Delta Gen 4 firmware sends NotifyChargingLimit (e.g. with
    chargingLimitSource 'SO') even when no car is charging. Without a handler
    the ocpp library raises NotImplementedError and floods the HA log with
    KeyError: 'NotifyChargingLimit'.
    """
    response = await charge_point.on_notify_charging_limit(
        charging_limit={"charging_limit_source": "SO"},
    )

    assert response is not None
    assert isinstance(response, call_result.NotifyChargingLimit)


async def test_cleared_charging_limit_handler(charge_point):
    """Test ClearedChargingLimit handler (issue #14 - counterpart message)."""
    response = await charge_point.on_cleared_charging_limit(
        charging_limit_source="SO",
        evse_id=1,
    )

    assert response is not None
    assert isinstance(response, call_result.ClearedChargingLimit)


# ==============================================================================
# COMMAND TESTS
# ==============================================================================


async def test_async_start_charging_already_charging(coordinator):
    """Test start charging when already charging."""
    coordinator.charge_point = MagicMock()
    coordinator.data["charging_state"] = "Charging"
    coordinator.data["power"] = 7000.0

    result = await coordinator.async_start_charging()

    assert result["success"] is True
    assert result["action"] == "already_charging"


async def test_async_start_charging_with_transaction(coordinator):
    """Test start charging resumes existing transaction."""
    coordinator.charge_point = MagicMock()
    coordinator.current_transaction_id = "test-tx-123"
    coordinator.data["charging_state"] = "SuspendedEVSE"
    coordinator.data["power"] = 0

    # Mock the resume method
    coordinator.async_resume_charging = AsyncMock(
        return_value={"success": True, "message": "Resumed"}
    )

    result = await coordinator.async_start_charging()

    assert result["success"] is True
    assert result["action"] == "resumed"
    coordinator.async_resume_charging.assert_called_once()


async def test_async_start_charging_new_transaction(coordinator):
    """Test start charging creates new transaction."""
    mock_charge_point = MagicMock()
    mock_charge_point.call = AsyncMock()

    # Mock the response
    mock_response = MagicMock()
    mock_response.status = "Accepted"
    mock_response.transaction_id = "new-tx-456"
    mock_charge_point.call.return_value = mock_response

    coordinator.charge_point = mock_charge_point
    coordinator.current_transaction_id = None

    result = await coordinator.async_start_charging()

    assert result["success"] is True
    assert result["action"] == "started"
    assert coordinator.current_transaction_id == "new-tx-456"


async def test_async_start_charging_no_wallbox(coordinator):
    """Test start charging fails when wallbox not connected."""
    coordinator.charge_point = None

    result = await coordinator.async_start_charging()

    assert result["success"] is False
    assert "not connected" in result["message"]


async def test_async_pause_charging(coordinator):
    """Test pause charging."""
    mock_charge_point = MagicMock()
    mock_charge_point.call = AsyncMock()

    mock_response = MagicMock()
    mock_response.status = "Accepted"
    mock_charge_point.call.return_value = mock_response

    coordinator.charge_point = mock_charge_point
    coordinator.current_transaction_id = "test-tx-123"
    coordinator.data["power"] = 7000.0

    result = await coordinator.async_pause_charging()

    assert result["success"] is True
    assert "paused" in result["message"].lower()


async def test_async_pause_charging_already_paused(coordinator):
    """Test pause charging when already paused."""
    mock_charge_point = MagicMock()
    mock_charge_point.call = AsyncMock()

    # Mock GetTransactionStatus response for refresh_transaction_id
    mock_response = MagicMock()
    mock_response.ongoing_indicator = True
    mock_charge_point.call.return_value = mock_response

    coordinator.charge_point = mock_charge_point
    coordinator.current_transaction_id = "test-tx-123"
    coordinator.data["power"] = 0

    result = await coordinator.async_pause_charging()

    assert result["success"] is True
    assert "already paused" in result["message"].lower()


async def test_async_pause_charging_nuke_on_rejection(coordinator):
    """Test pause triggers NUKE (reboot) when SetChargingProfile is rejected."""
    mock_charge_point = MagicMock()

    # First call: TriggerMessage (meter refresh before pause check)
    # Second call: GetTransactionStatus (refresh)
    # Third call: ClearChargingProfile
    # Fourth call: SetChargingProfile (rejected)
    # Fifth call: Reset (NUKE)
    call_count = 0

    async def mock_call(request):
        nonlocal call_count
        call_count += 1

        if call_count <= 3:
            # TriggerMessage, GetTransactionStatus, and ClearChargingProfile
            mock_resp = MagicMock()
            mock_resp.ongoing_indicator = True
            mock_resp.status = "Accepted"
            return mock_resp
        if call_count == 4:
            # SetChargingProfile - REJECTED!
            mock_resp = MagicMock()
            mock_resp.status = "Rejected"
            mock_resp.status_info = None
            return mock_resp
        # Reset - accepted
        mock_resp = MagicMock()
        mock_resp.status = "Accepted"
        return mock_resp

    mock_charge_point.call = mock_call
    coordinator.charge_point = mock_charge_point
    coordinator.current_transaction_id = "test-tx-123"
    coordinator.data["power"] = 7000.0

    result = await coordinator.async_pause_charging(allow_nuke=True)

    assert result["success"] is True
    assert result["action"] == "nuked"
    assert "reboot" in result["message"].lower() or "💣" in result["message"]


async def test_async_pause_charging_no_nuke_when_disabled(coordinator):
    """Test pause does NOT trigger NUKE when allow_nuke=False."""
    mock_charge_point = MagicMock()

    call_count = 0

    async def mock_call(request):
        nonlocal call_count
        call_count += 1

        if call_count <= 3:
            # TriggerMessage, GetTransactionStatus, ClearChargingProfile
            mock_resp = MagicMock()
            mock_resp.ongoing_indicator = True
            mock_resp.status = "Accepted"
            return mock_resp
        # SetChargingProfile - REJECTED!
        mock_resp = MagicMock()
        mock_resp.status = "Rejected"
        mock_resp.status_info = None
        return mock_resp

    mock_charge_point.call = mock_call
    coordinator.charge_point = mock_charge_point
    coordinator.current_transaction_id = "test-tx-123"
    coordinator.data["power"] = 7000.0

    result = await coordinator.async_pause_charging(allow_nuke=False)

    assert result["success"] is False
    assert "rejected" in result["message"].lower()
    # Should NOT have called Reset (only 4 calls: trigger + tx_status + clear + set)
    assert call_count == 4


async def test_async_pause_charging_nuke_on_timeout(coordinator):
    """Test pause triggers NUKE when command times out."""
    mock_charge_point = MagicMock()

    call_count = 0

    async def mock_call(request):
        nonlocal call_count
        call_count += 1

        if call_count <= 3:
            # TriggerMessage, GetTransactionStatus, ClearChargingProfile
            mock_resp = MagicMock()
            mock_resp.ongoing_indicator = True
            mock_resp.status = "Accepted"
            return mock_resp
        if call_count == 4:
            # SetChargingProfile - TIMEOUT!
            raise TimeoutError("Connection timed out")
        # Reset - accepted
        mock_resp = MagicMock()
        mock_resp.status = "Accepted"
        return mock_resp

    mock_charge_point.call = mock_call
    coordinator.charge_point = mock_charge_point
    coordinator.current_transaction_id = "test-tx-123"
    coordinator.data["power"] = 7000.0

    result = await coordinator.async_pause_charging(allow_nuke=True)

    assert result["success"] is True
    assert result["action"] == "nuked"


async def test_async_resume_charging(coordinator):
    """Test resume charging."""
    mock_charge_point = MagicMock()
    mock_charge_point.call = AsyncMock()

    mock_response = MagicMock()
    mock_response.status = "Accepted"
    mock_charge_point.call.return_value = mock_response

    coordinator.charge_point = mock_charge_point
    coordinator.current_transaction_id = "test-tx-123"

    # Patch create_task to avoid lingering tasks from delayed_refresh
    with patch("asyncio.create_task"):
        result = await coordinator.async_resume_charging(32.0)

    assert result["success"] is True
    assert "resumed" in result["message"].lower()


async def test_async_stop_charging(coordinator):
    """Test stop charging calls pause."""
    coordinator.async_pause_charging = AsyncMock(
        return_value={"success": True, "message": "Paused"}
    )

    result = await coordinator.async_stop_charging()

    assert result["success"] is True
    coordinator.async_pause_charging.assert_called_once()


async def test_async_reset_wallbox(coordinator):
    """Test reset wallbox."""
    mock_charge_point = MagicMock()
    mock_charge_point.call = AsyncMock()

    mock_response = MagicMock()
    mock_response.status = "Accepted"
    mock_charge_point.call.return_value = mock_response

    coordinator.charge_point = mock_charge_point
    coordinator.current_transaction_id = "test-tx-123"

    result = await coordinator.async_reset_wallbox()

    assert result["success"] is True
    assert "reset" in result["message"].lower() or "reboot" in result["message"].lower()
    assert coordinator.current_transaction_id is None


async def test_async_set_current_limit(coordinator):
    """Test set current limit."""
    mock_charge_point = MagicMock()
    mock_charge_point.call = AsyncMock()

    mock_response = MagicMock()
    mock_response.status = "Accepted"
    mock_charge_point.call.return_value = mock_response

    coordinator.charge_point = mock_charge_point
    coordinator.current_transaction_id = "test-tx-123"

    result = await coordinator.async_set_current_limit(16.0)

    assert result is True


async def test_async_set_current_limit_no_transaction(coordinator):
    """Without a transaction the limit is still set via TxDefaultProfile (#15)."""
    mock_charge_point = MagicMock()
    mock_response = MagicMock()
    mock_response.status = "Accepted"
    mock_charge_point.call = AsyncMock(return_value=mock_response)

    coordinator.charge_point = mock_charge_point
    coordinator.current_transaction_id = None

    result = await coordinator.async_set_current_limit(16.0)

    assert result is True
    purposes = _profile_purposes(mock_charge_point.call)
    assert purposes == [ChargingProfilePurposeEnumType.tx_default_profile]


async def test_async_trigger_meter_values(coordinator):
    """Test trigger meter values."""
    mock_charge_point = MagicMock()
    mock_charge_point.call = AsyncMock()

    mock_response = MagicMock()
    mock_response.status = "Accepted"
    mock_charge_point.call.return_value = mock_response

    coordinator.charge_point = mock_charge_point

    result = await coordinator.async_trigger_meter_values()

    assert result is True


async def test_async_set_led_brightness(coordinator):
    """Test set LED brightness."""
    mock_charge_point = MagicMock()
    mock_charge_point.call = AsyncMock()

    mock_response = MagicMock()
    mock_response.set_variable_result = [{"attribute_status": "Accepted"}]
    mock_charge_point.call.return_value = mock_response

    coordinator.charge_point = mock_charge_point

    result = await coordinator.async_set_led_brightness(50)

    assert result is True


async def test_async_set_led_brightness_clamps_value(coordinator):
    """Test LED brightness is clamped to 0-100 range."""
    mock_charge_point = MagicMock()
    mock_charge_point.call = AsyncMock()

    mock_response = MagicMock()
    mock_response.set_variable_result = [{"attribute_status": "Accepted"}]
    mock_charge_point.call.return_value = mock_response

    coordinator.charge_point = mock_charge_point

    # Test clamping
    result = await coordinator.async_set_led_brightness(150)  # Should clamp to 100
    assert result is True

    result = await coordinator.async_set_led_brightness(-10)  # Should clamp to 0
    assert result is True


# ==============================================================================
# ERROR HANDLING TESTS
# ==============================================================================


async def test_start_charging_timeout(coordinator):
    """Test start charging handles timeout."""
    mock_charge_point = MagicMock()
    mock_charge_point.call = AsyncMock(side_effect=TimeoutError())

    coordinator.charge_point = mock_charge_point
    coordinator.current_transaction_id = None

    result = await coordinator.async_start_charging(allow_nuke=False)

    assert result["success"] is False
    assert "timed out" in result["message"].lower()


async def test_pause_charging_timeout(coordinator):
    """Test pause charging handles timeout."""
    mock_charge_point = MagicMock()
    mock_charge_point.call = AsyncMock(side_effect=TimeoutError())

    coordinator.charge_point = mock_charge_point
    coordinator.current_transaction_id = "test-tx-123"
    coordinator.data["power"] = 7000.0

    result = await coordinator.async_pause_charging()

    assert result["success"] is False
    assert "timed out" in result["message"].lower()


async def test_resume_charging_timeout(coordinator):
    """Test resume charging handles timeout."""
    mock_charge_point = MagicMock()
    mock_charge_point.call = AsyncMock(side_effect=TimeoutError())

    coordinator.charge_point = mock_charge_point
    coordinator.current_transaction_id = "test-tx-123"

    result = await coordinator.async_resume_charging(32.0)

    assert result["success"] is False
    assert "timed out" in result["message"].lower()


async def test_trigger_meter_values_error(coordinator):
    """Test trigger meter values handles errors."""
    mock_charge_point = MagicMock()
    mock_charge_point.call = AsyncMock(side_effect=Exception("Test error"))

    coordinator.charge_point = mock_charge_point

    result = await coordinator.async_trigger_meter_values()

    assert result is False


# ==============================================================================
# LIVE CURRENT CALCULATION TESTS (issue #15 - stale Current sensor)
# ==============================================================================


def test_compute_live_current_direct_total_last_resort():
    """A directly reported total is used only when nothing else is available."""
    assert _compute_live_current({}, 14.0, 0, 0, 1) == 14.0


def test_compute_live_current_phase_beats_stale_total():
    """Per-phase reading wins over a stale non-phased total (issue #15).

    The Delta firmware keeps reporting a frozen non-phased Current.Import (e.g.
    30.4 from before the limit was applied) while the per-phase reading tracks
    the real current. The per-phase value must win.
    """
    data = {"current_l1": 9.38, "current_l2": 0, "current_l3": 0}
    assert _compute_live_current(data, 30.37, 2087, 230, 1) == 9.4


def test_compute_live_current_power_beats_stale_total():
    """Power-derived value wins over a stale non-phased total too."""
    assert _compute_live_current({}, 30.37, 2300, 230, 1) == 10.0


def test_compute_live_current_single_phase_average():
    """Single-phase current comes from the active phase, not stale total."""
    data = {"current_l1": 9.0, "current_l2": 0, "current_l3": 0}
    assert _compute_live_current(data, None, 2080, 230, 1) == 9.0


def test_compute_live_current_three_phase_average():
    """Three-phase balanced current is the per-phase value."""
    data = {"current_l1": 16.0, "current_l2": 16.0, "current_l3": 16.0}
    assert _compute_live_current(data, None, 11000, 230, 3) == 16.0


def test_compute_live_current_derived_from_power_single_phase():
    """Falls back to P/V when no phase currents are reported."""
    assert _compute_live_current({}, None, 2300, 230, 1) == 10.0


def test_compute_live_current_derived_from_power_three_phase():
    """Three-phase derivation uses sqrt(3)."""
    assert _compute_live_current({}, None, 11000, 230, 3) == 27.6


def test_compute_live_current_none_when_no_data():
    """Returns None when there is nothing to compute from."""
    assert _compute_live_current({}, None, 0, 0, 1) is None


async def test_meter_values_current_not_stale(charge_point):
    """Current sensor must refresh from phases, not stick at an old total.

    Regression for issue #15: once a stale total was stored it was never
    recomputed, so the Current sensor stayed frozen while power dropped.
    """
    data = charge_point.coordinator.data
    # Simulate a previously-stored stale total current.
    data["current"] = 30.4

    # The wallbox keeps sending a frozen non-phased total (30.4) alongside a
    # fresh per-phase reading (9.0) - exactly what was seen live.
    meter_value = [
        {
            "timestamp": datetime.utcnow().isoformat(),
            "sampled_value": [
                {"measurand": "Power.Active.Import", "value": "2080"},
                {"measurand": "Current.Import", "value": "30.4"},
                {"measurand": "Current.Import", "value": "9.0", "phase": "L1"},
            ],
        }
    ]

    await charge_point.on_meter_values(evse_id=1, meter_value=meter_value)

    # Should reflect the fresh per-phase reading, not the stale non-phased 30.4
    assert data["current_l1"] == 9.0
    assert data["current"] == 9.0


async def test_transaction_event_ended_resets_live_readings(charge_point):
    """When the session ends, live readings must reset (issue #15)."""
    data = charge_point.coordinator.data
    data["current"] = 16.0
    data["power"] = 3680.0
    data["current_l1"] = 16.0

    await charge_point.on_transaction_event(
        event_type="Ended",
        timestamp=datetime.utcnow().isoformat(),
        trigger_reason="EVCommunicationLost",
        seq_no=99,
        transaction_info={"transaction_id": "tx-1", "charging_state": "Available"},
    )

    assert data["current"] == 0
    assert data["power"] == 0
    assert data["current_l1"] == 0


# ==============================================================================
# CURRENT LIMIT TIMING TESTS (issue #15 - startup overshoot)
# ==============================================================================


def _profile_purposes(mock_call):
    """Extract the charging_profile_purpose of every SetChargingProfile sent."""
    purposes = []
    for call_args in mock_call.call_args_list:
        msg = call_args.args[0]
        purposes.append(msg.charging_profile.charging_profile_purpose)
    return purposes


async def test_set_current_limit_sends_tx_default_profile(coordinator):
    """During a session both TxDefaultProfile and TxProfile are sent (issue #15)."""
    mock_cp = MagicMock()
    mock_response = MagicMock()
    mock_response.status = "Accepted"
    mock_cp.call = AsyncMock(return_value=mock_response)
    coordinator.charge_point = mock_cp
    coordinator.current_transaction_id = "tx-123"

    result = await coordinator.async_set_current_limit(13.0)

    assert result is True
    purposes = _profile_purposes(mock_cp.call)
    assert ChargingProfilePurposeEnumType.tx_default_profile in purposes
    assert ChargingProfilePurposeEnumType.tx_profile in purposes
    assert coordinator.data["current_limit"] == 13.0


async def test_set_current_limit_without_transaction_uses_default_only(coordinator):
    """Without an active session the TxDefaultProfile alone still sets the limit."""
    mock_cp = MagicMock()
    mock_response = MagicMock()
    mock_response.status = "Accepted"
    mock_cp.call = AsyncMock(return_value=mock_response)
    coordinator.charge_point = mock_cp
    coordinator.current_transaction_id = None

    result = await coordinator.async_set_current_limit(10.0)

    assert result is True
    purposes = _profile_purposes(mock_cp.call)
    assert purposes == [ChargingProfilePurposeEnumType.tx_default_profile]
    assert coordinator.data["current_limit"] == 10.0


async def test_set_current_limit_no_wallbox(coordinator):
    """Setting the limit fails cleanly when the wallbox is not connected."""
    coordinator.charge_point = None

    result = await coordinator.async_set_current_limit(16.0)

    assert result is False


async def test_apply_limit_on_transaction_start(coordinator):
    """A starting transaction triggers an immediate limit push (issue #15)."""
    coordinator.charge_point = MagicMock()
    coordinator.data["current_limit"] = 13.0
    coordinator.async_set_current_limit = AsyncMock(return_value=True)

    await coordinator.async_apply_limit_on_transaction_start()

    coordinator.async_set_current_limit.assert_called_once_with(13.0)


# ==============================================================================
# OCPP CALL SERIALISATION / RESPONSE-QUEUE DESYNC TESTS (issue #14)
# ==============================================================================


class _FakeWallboxConnection:
    """Minimal websockets-like connection that drives the real ocpp pump.

    It replies to every Call (message type 2) with a CallResult
    {"status": "Accepted"} after ``response_delay`` seconds, so tests can
    exercise the library's real request/response matching (self._response_queue
    + self._get_specific_response) that issue #14 desynced.
    """

    def __init__(self, response_delay: float = 0.0):
        self.response_delay = response_delay
        self.sent: list[str] = []
        self._incoming: asyncio.Queue[str] = asyncio.Queue()

    async def send(self, message: str) -> None:
        self.sent.append(message)
        data = json.loads(message)
        if data[0] == 2:  # Call -> schedule a matching CallResult
            asyncio.create_task(self._reply(data[1]))

    async def _reply(self, unique_id: str) -> None:
        if self.response_delay:
            await asyncio.sleep(self.response_delay)
        await self._incoming.put(json.dumps([3, unique_id, {"status": "Accepted"}]))

    async def recv(self) -> str:
        return await self._incoming.get()


def _meter_trigger():
    return call.TriggerMessage(
        requested_message=MessageTriggerEnumType.meter_values,
        evse={"id": 1, "connector_id": 1},
    )


async def test_ocpp_call_raises_without_wallbox(coordinator):
    """_ocpp_call fails fast (not silently) when no wallbox is connected."""
    coordinator.charge_point = None

    with pytest.raises(RuntimeError):
        await coordinator._ocpp_call(_meter_trigger())


async def test_ocpp_call_serialises_concurrent_calls(coordinator):
    """Only one OCPP request may be in flight at a time (issue #14).

    Interleaved requests were part of what desynced the response queue; the
    coordinator lock must serialise every call regardless of how many callers
    fire concurrently.
    """
    in_flight = 0
    max_in_flight = 0

    async def fake_call(_payload):
        nonlocal in_flight, max_in_flight
        in_flight += 1
        max_in_flight = max(max_in_flight, in_flight)
        await asyncio.sleep(0.02)
        in_flight -= 1
        resp = MagicMock()
        resp.status = "Accepted"
        return resp

    cp = MagicMock()
    cp.call = fake_call
    coordinator.charge_point = cp

    await asyncio.gather(*(coordinator._ocpp_call(MagicMock()) for _ in range(8)))

    assert max_in_flight == 1


async def test_ocpp_call_uses_authoritative_timeout():
    """The wallbox response_timeout is the single authority (issue #14).

    A shorter external timeout would cancel an in-flight call() and orphan the
    reply. The backstop must therefore be longer than the library's own
    response_timeout, and the charge point must be built with it.
    """
    assert OCPP_CALL_BACKSTOP_TIMEOUT > OCPP_RESPONSE_TIMEOUT

    cp = WallboxChargePoint("CP", MagicMock(), MagicMock())
    assert cp._response_timeout == OCPP_RESPONSE_TIMEOUT


async def test_ocpp_call_stays_in_sync_through_real_pump(coordinator, caplog):
    """Rapid calls through _ocpp_call each get their own reply (issue #14).

    Runs against the real ocpp message pump: every _ocpp_call must resolve to a
    matching CallResult with no "Ignoring response with unknown unique id"
    desync, even when the wallbox is slow enough that a short external timeout
    would have cancelled the request mid-flight.
    """
    conn = _FakeWallboxConnection(response_delay=0.05)
    cp = WallboxChargePoint("CP", conn, coordinator)
    coordinator.charge_point = cp
    pump = asyncio.create_task(cp.start())

    try:
        with caplog.at_level(logging.ERROR, logger="ocpp"):
            results = await asyncio.gather(
                *(coordinator._ocpp_call(_meter_trigger()) for _ in range(10))
            )
    finally:
        pump.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await pump

    assert len(results) == 10
    assert all(r.status == "Accepted" for r in results)
    assert "unknown unique id" not in caplog.text.lower()


async def test_short_external_timeout_desyncs_queue_regression(coordinator, caplog):
    """Characterises the issue #14 root cause the fix removes.

    Wrapping call() in an external timeout shorter than the wallbox's reply
    cancels the in-flight request; the late reply is then orphaned in the ocpp
    response queue and the *next* call reads it first, logging "Ignoring
    response with unknown unique id". This is exactly the log line the reporter
    saw, and precisely what _ocpp_call avoids by never using a short external
    timeout.
    """
    conn = _FakeWallboxConnection(response_delay=0.2)
    cp = WallboxChargePoint("CP", conn, coordinator)
    coordinator.charge_point = cp
    pump = asyncio.create_task(cp.start())

    try:
        with caplog.at_level(logging.ERROR, logger="ocpp"):
            # Old pattern: external timeout (0.05s) shorter than the reply (0.2s)
            # cancels the request mid-flight.
            with pytest.raises((TimeoutError, asyncio.TimeoutError)):
                await asyncio.wait_for(cp.call(_meter_trigger()), 0.05)
            # The orphaned reply now poisons the following call.
            await cp.call(_meter_trigger())

        assert "unknown unique id" in caplog.text.lower()
    finally:
        pump.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await pump
