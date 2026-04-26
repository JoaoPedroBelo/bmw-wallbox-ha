"""Config flow for BMW Wallbox integration."""

from __future__ import annotations

import logging
import os
from typing import Any

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
import voluptuous as vol

from .const import (
    CONF_CHARGE_POINT_ID,
    CONF_MAX_CURRENT,
    CONF_PORT,
    CONF_RFID_TOKEN,
    CONF_SCAN_INTERVAL,
    CONF_SSL_CERT,
    CONF_SSL_KEY,
    DEFAULT_MAX_CURRENT,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_SSL_CERT, default="/ssl/fullchain.pem"): str,
        vol.Required(CONF_SSL_KEY, default="/ssl/privkey.pem"): str,
        vol.Required(CONF_CHARGE_POINT_ID): str,
        vol.Optional(CONF_RFID_TOKEN, default=""): str,
        vol.Optional(CONF_MAX_CURRENT, default=DEFAULT_MAX_CURRENT): vol.All(
            vol.Coerce(int), vol.Range(min=6, max=63)
        ),
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=5, max=60)
        ),
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""

    # Validate port range
    if not 1 <= data[CONF_PORT] <= 65535:
        raise InvalidPort

    # Validate SSL certificate files exist
    if not os.path.isfile(data[CONF_SSL_CERT]):
        raise InvalidSSLCert(f"Certificate file not found: {data[CONF_SSL_CERT]}")

    if not os.path.isfile(data[CONF_SSL_KEY]):
        raise InvalidSSLKey(f"Key file not found: {data[CONF_SSL_KEY]}")

    # Return info to store in the config entry
    return {
        "title": f"BMW Wallbox ({data[CONF_CHARGE_POINT_ID]})",
        "unique_id": data[CONF_CHARGE_POINT_ID],
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BMW Wallbox."""

    VERSION = 2

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,  # noqa: ARG004
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return OptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except InvalidPort:
                errors["base"] = "invalid_port"
            except InvalidSSLCert:
                errors["base"] = "invalid_ssl_cert"
            except InvalidSSLKey:
                errors["base"] = "invalid_ssl_key"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Check if already configured
                await self.async_set_unique_id(info["unique_id"])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class InvalidPort(HomeAssistantError):
    """Error to indicate invalid port."""


class InvalidSSLCert(HomeAssistantError):
    """Error to indicate invalid SSL certificate."""


class InvalidSSLKey(HomeAssistantError):
    """Error to indicate invalid SSL key."""


class OptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for BMW Wallbox."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_rfid = self.config_entry.options.get(
            CONF_RFID_TOKEN,
            self.config_entry.data.get(CONF_RFID_TOKEN, ""),
        )
        current_max = self.config_entry.options.get(
            CONF_MAX_CURRENT,
            self.config_entry.data.get(CONF_MAX_CURRENT, DEFAULT_MAX_CURRENT),
        )
        current_scan = self.config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_RFID_TOKEN, default=current_rfid): str,
                    vol.Optional(CONF_MAX_CURRENT, default=current_max): vol.All(
                        vol.Coerce(int), vol.Range(min=6, max=63)
                    ),
                    vol.Optional(CONF_SCAN_INTERVAL, default=current_scan): vol.All(
                        vol.Coerce(int), vol.Range(min=5, max=60)
                    ),
                }
            ),
        )
