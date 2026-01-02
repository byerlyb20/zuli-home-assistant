"""Platform for switch integration."""
from __future__ import annotations
from datetime import timedelta
import logging
from zuli.smartplug import ZuliSmartplug

from homeassistant.components.switch import SwitchEntity
from . import ZuliCoordinator, ZuliState
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Zuli switch from a config entry."""
    coordinator: ZuliCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ZuliSwitch(coordinator, entry.title)])


class ZuliSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a Zuli Smartplug in appliance mode."""

    def __init__(self, coordinator: ZuliCoordinator, name: str) -> None:
        super().__init__(coordinator)
        self._device: ZuliSmartplug = coordinator.device # type: ignore
        self._name = name
        self.__set_state(coordinator.data) # type: ignore
    
    def __set_state(self, state: ZuliState):
        brightness = state["brightness"]
        self._state: bool | None = None if brightness == None else brightness > 0
        self._is_appliance = state["is_appliance"]

    @callback
    def _handle_coordinator_update(self) -> None:
        self.__set_state(self.coordinator.data) # type: ignore
        self.async_write_ha_state()

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_{self._device.address}_switch"

    @property
    def name(self) -> str:
        return "Switch"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._device.address)},
            manufacturer="Zuli",
            model="Smartplug",
            name=self._name,
        )

    @property
    def available(self) -> bool:
        return self._is_appliance == True and self.coordinator.last_update_success

    @property
    def is_on(self) -> bool | None:
        return self._state

    async def async_turn_on(self, **kwargs):
        try:
            _LOGGER.debug("Turning switch on")
            await self._device.on(100)
            _LOGGER.debug("Switch turned on")
            self._state = True
            self.async_write_ha_state()
        except Exception as e:
            _LOGGER.error("Unable to turn switch on")
            self._state = None
            self.async_write_ha_state()
            raise e
        finally:
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        try:
            _LOGGER.debug("Turning switch off")
            await self._device.off()
            _LOGGER.debug("Switch turned off")
            self._state = False
            self.async_write_ha_state()
        except Exception as e:
            _LOGGER.error("Unable to turn switch off")
            self._state = None
            self.async_write_ha_state()
            raise e
        finally:
            await self.coordinator.async_request_refresh()
