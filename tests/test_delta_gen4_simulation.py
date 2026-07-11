"""End-to-end simulations against a Delta Gen 4 firmware model (issues #14/#19).

Runs the integration's real OCPP server (WallboxChargePoint + coordinator)
against a simulated wallbox that reproduces the firmware quirks reported on
the Delta-built BMW wallboxes (Wallbox Plus Gen 4 / EIAW-E22KTSE6B04):

Issue #14:
- Sends NotifyEVChargingNeeds (ISO 15118); an unanswered/errored reply used to
  desync the response queue and kill every following SetChargingProfile.
- Rejects any charging profile above stack level 0
  (ChargingProfileMaxStackLevel=0).
- Does NOT replace an existing profile with the same id - it rejects the
  duplicate, and after one rejection keeps rejecting every profile on that
  transaction until a new transaction starts.

Issue #19:
- SetChargingProfile (TxProfile) sent while the transaction is suspended is
  answered "Accepted" but silently discarded.
- ClearChargingProfile wipes everything, including the TxDefaultProfile.

With those quirks, the pre-fix resume path (clear-all + TxProfile only) left
the session completely unrestricted: the wallbox resumed at its hardware
maximum (16A x 3 phases ~= 11kW) instead of the configured limit.
"""

import asyncio
import contextlib
from datetime import UTC, datetime
import itertools
import json
from unittest.mock import AsyncMock, MagicMock

from ocpp.v201.enums import ChargingProfilePurposeEnumType
import pytest

from custom_components.bmw_wallbox.coordinator import (
    BMWWallboxCoordinator,
    WallboxChargePoint,
)

HARDWARE_MAX_A = 16.0


class DeltaGen4Simulator:
    """Websockets-like connection simulating the Delta Gen 4 charge point.

    Feeds the real ocpp message pump: CSMS->CP Calls sent by the integration
    are answered according to the firmware model, and CP->CSMS Calls (e.g.
    TransactionEvent, NotifyEVChargingNeeds) can be injected with
    :meth:`send_to_csms`.
    """

    def __init__(self):
        self.charging_state = "Charging"
        self.applied_tx_limit: float | None = None
        self.stored_default_limit: float | None = None
        self.stored_profile_ids: set[int] = set()
        # Issue #14: after one profile rejection the firmware rejects every
        # further profile on the transaction until a new transaction starts.
        self.poisoned = False
        self.sent_actions: list[str] = []
        self.call_errors: list[str] = []  # CallErrors the CSMS sent us
        self.csms_results: list[dict] = []  # CallResults to our own calls
        self._incoming: asyncio.Queue[str] = asyncio.Queue()
        self._uid = itertools.count(1)

    def drawn_current(self) -> float:
        """Current the wallbox would draw once charging - the issue #19 crux."""
        limits = [HARDWARE_MAX_A]
        if self.applied_tx_limit is not None:
            limits.append(self.applied_tx_limit)
        if self.stored_default_limit is not None:
            limits.append(self.stored_default_limit)
        return min(limits)

    async def send(self, message: str) -> None:
        data = json.loads(message)
        if data[0] == 3:  # CallResult for one of our own calls
            self.csms_results.append(data[2])
            return
        if data[0] == 4:  # CallError - the pre-#16 NotifyEVChargingNeeds killer
            self.call_errors.append(str(data))
            return
        _, uid, action, payload = data
        self.sent_actions.append(action)
        await self._incoming.put(json.dumps([3, uid, self._respond(action, payload)]))

    def _respond(self, action: str, payload: dict) -> dict:
        if action == "SetChargingProfile":
            return self._respond_set_profile(payload)
        if action == "ClearChargingProfile":
            had_profiles = bool(self.stored_profile_ids)
            self.applied_tx_limit = None
            self.stored_default_limit = None
            self.stored_profile_ids.clear()
            return {"status": "Accepted" if had_profiles else "Unknown"}
        if action == "GetTransactionStatus":
            return {"ongoingIndicator": True, "messagesInQueue": False}
        return {"status": "Accepted"}

    def _respond_set_profile(self, payload: dict) -> dict:
        profile = payload["chargingProfile"]
        # Issue #14: one rejection poisons the whole transaction
        if self.poisoned:
            return {"status": "Rejected", "statusInfo": {"reasonCode": "TxPoisoned"}}
        # Issue #14: ChargingProfileMaxStackLevel=0
        if profile["stackLevel"] > 0:
            return {
                "status": "Rejected",
                "statusInfo": {"reasonCode": "StackLevelOutOfRange"},
            }
        # Issue #14: same-id profiles are not replaced - the duplicate is
        # rejected and the transaction is poisoned from here on
        if profile["id"] in self.stored_profile_ids:
            self.poisoned = True
            return {"status": "Rejected", "statusInfo": {"reasonCode": "DuplicateId"}}

        limit = profile["chargingSchedule"][0]["chargingSchedulePeriod"][0]["limit"]
        purpose = profile["chargingProfilePurpose"]
        if purpose == "TxDefaultProfile":
            # Persistent config - stored regardless of charging state
            self.stored_default_limit = limit
            self.stored_profile_ids.add(profile["id"])
        elif self.charging_state == "Charging":
            self.applied_tx_limit = limit
            self.stored_profile_ids.add(profile["id"])
        # else: the issue #19 quirk - "Accepted", then silently discarded
        return {"status": "Accepted"}

    async def recv(self) -> str:
        return await self._incoming.get()

    async def send_to_csms(self, action: str, payload: dict) -> None:
        """Inject a CP->CSMS Call into the pump (e.g. TransactionEvent)."""
        uid = f"sim-{next(self._uid)}"
        await self._incoming.put(json.dumps([2, uid, action, payload]))

    async def send_transaction_event(
        self, event_type: str, charging_state: str, seq_no: int
    ) -> None:
        self.charging_state = charging_state
        if event_type == "Started":
            self.poisoned = False  # a new transaction resets the rejection latch
        await self.send_to_csms(
            "TransactionEvent",
            {
                "eventType": event_type,
                "timestamp": datetime.now(UTC).isoformat(),
                "triggerReason": "ChargingStateChanged",
                "seqNo": seq_no,
                "transactionInfo": {
                    "transactionId": "tx-19",
                    "chargingState": charging_state,
                },
            },
        )

    async def send_notify_ev_charging_needs(self) -> None:
        """The ISO 15118 message that crashed the pre-#16 integration."""
        await self.send_to_csms(
            "NotifyEVChargingNeeds",
            {
                "evseId": 1,
                "chargingNeeds": {
                    "requestedEnergyTransfer": "AC_three_phase",
                    "acChargingParameters": {
                        "energyAmount": 30000,
                        "evMinCurrent": 6,
                        "evMaxCurrent": 16,
                        "evMaxVoltage": 400,
                    },
                },
            },
        )


async def _wait_for(condition, timeout: float = 2.0) -> None:
    """Poll ``condition`` until true or fail the test after ``timeout``."""
    deadline = asyncio.get_event_loop().time() + timeout
    while not condition():
        if asyncio.get_event_loop().time() > deadline:
            pytest.fail("timed out waiting for simulated wallbox state")
        await asyncio.sleep(0.01)


@pytest.fixture
def coordinator():
    hass = MagicMock()
    hass.async_add_executor_job = AsyncMock(return_value=None)
    return BMWWallboxCoordinator(
        hass,
        {
            "port": 9000,
            "charge_point_id": "DE*BMW*TEST123",
            "rfid_token": "",
            "max_current": 32,
        },
    )


@pytest.fixture
async def sim_setup(coordinator):
    """Wire a simulator to the real message pump and clean up all tasks."""
    sim = DeltaGen4Simulator()
    cp = WallboxChargePoint("CP", sim, coordinator)
    coordinator.charge_point = cp
    pump = asyncio.create_task(cp.start())

    yield sim, coordinator

    pump.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await pump
    # Reap stragglers (e.g. the resume path's delayed meter-values refresh)
    current = asyncio.current_task()
    for task in asyncio.all_tasks():
        if task is not current and not task.done():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task


# ==============================================================================
# ISSUE #19 - resume clears profiles without re-applying the limit
# ==============================================================================


async def test_issue19_resume_keeps_configured_limit(sim_setup):
    """Full issue #19 scenario: set 6A, suspend, Start Charging, resume.

    Pre-fix, the resume's clear-all wiped the TxDefaultProfile and the
    replacement TxProfile was discarded by the suspended firmware, so the
    wallbox resumed at HARDWARE_MAX_A. The fix reinstalls the TxDefaultProfile
    during resume AND re-pushes both profiles once the state flips back to
    Charging, so the drawn current must stay at the configured 6A.
    """
    sim, coordinator = sim_setup

    # 1. Active session, charging
    await sim.send_transaction_event("Started", "Charging", seq_no=1)
    await _wait_for(lambda: coordinator.current_transaction_id == "tx-19")

    # 2. User limits the current to 6A - both profiles land on the wallbox
    assert await coordinator.async_set_current_limit(6.0) is True
    assert sim.applied_tx_limit == 6.0
    assert sim.stored_default_limit == 6.0

    # 3. The EV suspends the session
    await sim.send_transaction_event("Updated", "SuspendedEVSE", seq_no=2)
    await _wait_for(lambda: coordinator.data.get("charging_state") == "SuspendedEVSE")

    # 4. User presses the Start Charging button -> resume path
    result = await coordinator.async_start_charging()
    assert result["success"] is True
    assert result["action"] == "resumed"

    # Fix layer 1: the TxDefaultProfile safety net survives the resume's
    # clear-all, even though the firmware discarded the suspended TxProfile.
    assert sim.applied_tx_limit is None  # quirk: accepted but discarded
    assert sim.stored_default_limit == 6.0

    # 5. The wallbox actually resumes charging
    await sim.send_transaction_event("Updated", "Charging", seq_no=3)

    # Fix layer 2: the Suspended->Charging transition re-pushes the limit,
    # now in a state where the firmware honours the TxProfile.
    await _wait_for(lambda: sim.applied_tx_limit == 6.0)

    # The issue #19 assertion: 6A, not the unrestricted hardware maximum.
    assert sim.drawn_current() == 6.0


async def test_issue19_regression_without_charging_transition(sim_setup):
    """Even if the wallbox never reports the Charging transition, the resume
    itself must leave a limit in place (the reinstalled TxDefaultProfile)."""
    sim, coordinator = sim_setup
    sim.charging_state = "SuspendedEVSE"
    coordinator.current_transaction_id = "tx-19"
    coordinator.data["charging_state"] = "SuspendedEVSE"
    coordinator.data["current_limit"] = 6.0

    result = await coordinator.async_resume_charging()
    assert result["success"] is True

    # Pre-fix this was HARDWARE_MAX_A: no TxProfile (discarded while
    # suspended) and no TxDefaultProfile (wiped by the clear-all).
    assert sim.drawn_current() == 6.0


# ==============================================================================
# ISSUE #14 - NotifyEVChargingNeeds + duplicate-profile rejection latch
# ==============================================================================


async def test_issue14_notify_ev_charging_needs_answered_cleanly(sim_setup):
    """NotifyEVChargingNeeds must get a CallResult, never a CallError.

    Pre-#16 the integration had no handler: the ocpp lib answered with a
    CallError (NotImplementedError), the wallbox resent, and the response
    queue desynced ("Ignoring response with unknown unique id") - after which
    every SetChargingProfile stopped being applied.
    """
    sim, coordinator = sim_setup
    await sim.send_transaction_event("Started", "Charging", seq_no=1)
    await _wait_for(lambda: coordinator.current_transaction_id == "tx-19")

    await sim.send_notify_ev_charging_needs()
    # csms_results[0] is the TransactionEvent reply; [1] is the notify's
    await _wait_for(lambda: len(sim.csms_results) >= 2)

    assert sim.call_errors == []
    assert sim.csms_results[-1].get("status") == "Accepted"

    # And the OCPP channel is still healthy: a limit change right after the
    # ISO 15118 negotiation must land normally.
    assert await coordinator.async_set_current_limit(10.0) is True
    assert sim.applied_tx_limit == 10.0


async def test_issue14_consecutive_limit_changes_never_poison(sim_setup):
    """The live-validated #18 sequence: consecutive mid-charge limit changes.

    The firmware rejects a same-id profile instead of replacing it, and one
    rejection poisons the whole transaction. Only the clear-first pattern
    avoids it - if any code path ever skips the clear, this test trips the
    poison latch and every later change fails.
    """
    sim, coordinator = sim_setup
    await sim.send_transaction_event("Started", "Charging", seq_no=1)
    await _wait_for(lambda: coordinator.current_transaction_id == "tx-19")

    for amps in (6.0, 20.0, 12.0, 16.0):
        assert await coordinator.async_set_current_limit(amps) is True, (
            f"limit change to {amps}A was rejected"
        )
        assert sim.applied_tx_limit == amps
        assert sim.poisoned is False

    # Interleave the ISO 15118 message like the real Gen 4 does, then keep going
    await sim.send_notify_ev_charging_needs()
    assert await coordinator.async_set_current_limit(8.0) is True
    assert sim.applied_tx_limit == 8.0
    assert sim.call_errors == []


async def test_issue14_pause_resume_cycle_survives_duplicate_quirk(sim_setup):
    """Pause (0A) then resume must work after limit changes (issue #14 fallout).

    Pre-#18, the duplicate rejection latched after the first re-sent profile,
    the 0A pause was then rejected too and the integration fell back to the
    last-resort wallbox reboot ("nuke"). The whole cycle must now complete
    without a single rejection.
    """
    sim, coordinator = sim_setup
    await sim.send_transaction_event("Started", "Charging", seq_no=1)
    await _wait_for(lambda: coordinator.current_transaction_id == "tx-19")
    coordinator.data["power"] = 4000.0

    assert await coordinator.async_set_current_limit(6.0) is True

    # Pause: clear + TxProfile(0A) - a duplicate id 999 without the clear
    # would poison the transaction and trigger the nuke fallback.
    result = await coordinator.async_pause_charging(allow_nuke=False)
    assert result["success"] is True
    assert result["action"] == "paused"
    assert sim.drawn_current() == 0.0
    assert sim.poisoned is False

    # The wallbox suspends, then the user resumes
    await sim.send_transaction_event("Updated", "SuspendedEVSE", seq_no=2)
    await _wait_for(lambda: coordinator.data.get("charging_state") == "SuspendedEVSE")
    coordinator.data["power"] = 0

    result = await coordinator.async_start_charging()
    assert result["success"] is True
    assert result["action"] == "resumed"

    await sim.send_transaction_event("Updated", "Charging", seq_no=3)
    await _wait_for(lambda: sim.applied_tx_limit == 6.0)
    assert sim.drawn_current() == 6.0
    assert sim.poisoned is False


async def test_issue14_duplicate_without_clear_poisons_transaction(sim_setup):
    """Characterises the firmware quirk itself, so the tests above mean something.

    Sending the same profile id twice without clearing must latch the
    rejection - proving the simulator actually models the #14 behaviour the
    clear-first pattern exists to avoid.
    """
    sim, coordinator = sim_setup
    # Set the session up directly - the Started event would trigger the
    # integration's own auto-apply and install profiles before we do.
    coordinator.current_transaction_id = "tx-19"

    send = coordinator._send_charging_profile
    assert (
        await send(
            6.0,
            purpose=ChargingProfilePurposeEnumType.tx_profile,
            profile_id=999,
            stack_level=0,
            transaction_id="tx-19",
        )
        is True
    )
    # Same id again without a clear -> rejected + transaction poisoned
    assert (
        await send(
            10.0,
            purpose=ChargingProfilePurposeEnumType.tx_profile,
            profile_id=999,
            stack_level=0,
            transaction_id="tx-19",
        )
        is False
    )
    assert sim.poisoned is True
    # From now on even a fresh id is rejected (until a new transaction)
    assert (
        await send(
            10.0,
            purpose=ChargingProfilePurposeEnumType.tx_default_profile,
            profile_id=998,
            stack_level=0,
        )
        is False
    )
    # A stack level above 0 is always rejected (ChargingProfileMaxStackLevel=0)
    # even on a fresh transaction (which resets the rejection latch)
    sim.poisoned = False
    sim.stored_profile_ids.clear()
    assert (
        await send(
            10.0,
            purpose=ChargingProfilePurposeEnumType.tx_profile,
            profile_id=997,
            stack_level=1,
            transaction_id="tx-19",
        )
        is False
    )
