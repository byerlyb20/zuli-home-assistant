"""The Zuli integration."""
from __future__ import annotations
from datetime import timedelta
import logging
from typing import TypedDict
from zuli.smartplug import ZuliSmartplug
from zuli.protocol import Power

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

PLATFORMS: list[str] = ["switch", "light", "sensor"]
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Zuli from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    coordinator = ZuliCoordinator(hass, entry)
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

class ZuliCoordinator(DataUpdateCoordinator):

    DEFAULT_INTERVAL = timedelta(seconds=60)
    MAX_INTERVAL = timedelta(minutes=15)

    def __init__(self, hass, config_entry):
        super().__init__(
            hass,
            _LOGGER,
            name="Zuli Smartplug",
            config_entry=config_entry,
            update_interval=self.DEFAULT_INTERVAL,
            always_update=False
        )
        self._hass = hass
        self._address: str = config_entry.data["address"]
        self.device: ZuliSmartplug | None = None

    async def _async_setup(self):
        ble_device = bluetooth.async_ble_device_from_address(
            self._hass, self._address.upper(), connectable=True
        )

        if ble_device is None:
            raise ConfigEntryNotReady(f"Could not find Zuli device at {self._address}")

        try:
            self.device = ZuliSmartplug(ble_device)
        except Exception as ex:
            raise ConfigEntryNotReady(f"Error creating Zuli device from {self._address}") from ex
        
        await self.async_request_refresh()

    async def _async_update_data(self) -> ZuliState:
        if not self.device:
            brightness = None
            is_appliance = None
            power_reading = None
        else:
            try:
                brightness = await self.device.read()
                is_appliance = await self.device.get_mode()
                power_reading = await self.device.read_power()
            except Exception as e:
                # Increase polling interval on failure (exponential backoff)
                new_interval_seconds = (self.update_interval or self.DEFAULT_INTERVAL).total_seconds() * 2
                new_interval_seconds = min(new_interval_seconds, self.MAX_INTERVAL.total_seconds())
                self.update_interval = timedelta(seconds=new_interval_seconds)
                
                raise UpdateFailed() from e
            else:
                self.update_interval = self.DEFAULT_INTERVAL

        return {
            "brightness": brightness,
            "is_appliance": is_appliance,
            "power_reading": power_reading
        }
        
class ZuliState(TypedDict):
    brightness: int | None
    is_appliance: bool | None
    power_reading: Power | None
