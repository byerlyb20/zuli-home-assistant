"""Platform for select integration."""
from __future__ import annotations
from enum import Enum
import logging
from zuli.smartplug import ZuliSmartplug

from homeassistant.components.select import SelectEntity
from . import ZuliCoordinator, ZuliState
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class ZuliMode(Enum):
    APPLIANCE = "Appliance"
    DIMMABLE_LIGHT = "Dimmable Light"

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Zuli hardware type selector from a config entry."""
    coordinator: ZuliCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ZuliHardwareType(coordinator, entry.title)])


class ZuliHardwareType(CoordinatorEntity, SelectEntity): # type: ignore
    """Representation of a Zuli Smartplug hardware type selector."""

    def __init__(self, coordinator: ZuliCoordinator, name: str) -> None:
        super().__init__(coordinator)
        self._device: ZuliSmartplug = coordinator.device
        self._name = name
        self.__set_state(coordinator.data) # type: ignore
    
    def __set_state(self, state: ZuliState):
        self._is_appliance = state["is_appliance"]

    @callback
    def _handle_coordinator_update(self) -> None:
        self.__set_state(self.coordinator.data) # type: ignore
        self.async_write_ha_state()

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_{self._device.address}_mode"

    @property
    def name(self) -> str:
        return "Mode"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._device.address)},
            manufacturer="Zuli",
            model="Smartplug",
            name=self._name,
        )

    @property
    def current_option(self) -> str:
        return (ZuliMode.APPLIANCE if self._is_appliance else ZuliMode.DIMMABLE_LIGHT).value
    
    @property
    def options(self) -> list[str]:
        return [mode.value for mode in ZuliMode]
    
    @property
    def entity_registry_visible_default(self) -> bool:
        return False

    async def async_select_option(self, option: str):
        try:
            is_appliance = option == ZuliMode.APPLIANCE.value
            await self._device.set_mode(is_appliance)
            self._is_appliance = is_appliance
            self.async_write_ha_state()
        except Exception as e:
            _LOGGER.error("Unable to set mode")
            self._is_appliance = None
            self.async_write_ha_state()
            raise e
        finally:
            await self.coordinator.async_request_refresh()
