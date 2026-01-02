"""Platform for light integration."""
from __future__ import annotations
import asyncio
from datetime import timedelta
import logging
from zuli.smartplug import ZuliSmartplug

from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode, LightEntity
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
    """Set up Zuli light from a config entry."""
    _LOGGER.info("Zuli light platform async_setup_entry")
    coordinator: ZuliCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ZuliLight(coordinator, entry.title)])


class ZuliLight(CoordinatorEntity, LightEntity):
    """Representation of a Zuli Smartplug in dimmable mode."""

    def __init__(self, coordinator: ZuliCoordinator, name: str) -> None:
        super().__init__(coordinator)
        self._device: ZuliSmartplug = coordinator.device # type: ignore
        self._name = name
        self.__set_state(self.coordinator.data) # type: ignore
    
    def __set_state(self, state: ZuliState):
        self._brightness = state["brightness"]
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
        return "Dimmer"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._device.address)},
            manufacturer="Zuli",
            model="Smartplug",
            name=self._name,
        )
    
    @property
    def supported_color_modes(self) -> set[ColorMode] | None:
        return {ColorMode.ONOFF, ColorMode.BRIGHTNESS}

    @property
    def available(self) -> bool:
        return self._is_appliance == False and self.coordinator.last_update_success

    @property
    def is_on(self) -> bool | None:
        if self._brightness == None:
            return None
        return self._brightness > 0
    
    @property
    def brightness(self) -> int | None:
        if self._brightness == None:
            return None
        return round(self._brightness / 100 * 255)

    async def async_turn_on(self, **kwargs):
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        if brightness:
            brightness = round(brightness / 255 * 100)
        else:
            brightness = 100

        try:
            await self._device.on(brightness)
            self._brightness = brightness
            self.async_write_ha_state()
            await asyncio.sleep(1)  # wait for dimming animation
        except Exception as e:
            self._brightness = None
            self.async_write_ha_state()
            raise e
        finally:
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        try:
            await self._device.off()
            self._brightness = 0
            self.async_write_ha_state()
            await asyncio.sleep(1)    # wait for dimming animation
        except Exception as e:
            self._brightness = None
            self.async_write_ha_state()
            raise e
        finally:
            await self.coordinator.async_request_refresh()
