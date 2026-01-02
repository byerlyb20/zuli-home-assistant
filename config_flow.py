"""Config flow for Zuli integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import ConfigFlowResult

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class ZuliConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Zuli."""

    VERSION = 1

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle Bluetooth discovery."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        self.context["title_placeholders"] = {
            "name": f"Smartplug ({discovery_info.address})"
        }

        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle user confirmation of discovered device."""
        if user_input is not None:
            return self.async_create_entry(
                title=self.context["title_placeholders"]["name"], # type: ignore
                data={"address": self.unique_id},
            )

        self._set_confirm_only()
        return self.async_show_form(step_id="confirm")
