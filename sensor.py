"""Platform for sensor integration."""
from __future__ import annotations
from datetime import timedelta
import logging
from typing import Literal
from zuli.smartplug import ZuliSmartplug

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from . import ZuliCoordinator, ZuliState
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PowerReadingKey = Literal["irms_ma", "power_mw", "power_factor", "voltage_mv"]

_power_reading_sensors = [
    {
        "entity_name": "Power",
        "sensor_class": SensorDeviceClass.APPARENT_POWER,
        "unit": "mVA",
        "power_reading_key": "power_mw"
    },
    {
        "entity_name": "Current",
        "sensor_class": SensorDeviceClass.CURRENT,
        "unit": "mA",
        "power_reading_key": "irms_ma"
    },
    {
        "entity_name": "Voltage",
        "sensor_class": SensorDeviceClass.VOLTAGE,
        "unit": "mV",
        "power_reading_key": "voltage_mv"
    }
]

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Zuli sensor from a config entry."""
    coordinator: ZuliCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        ZuliPowerReadingSensor(coordinator, device_name=entry.title, **kwargs)
        for kwargs in _power_reading_sensors
    ])

class ZuliPowerReadingSensor(CoordinatorEntity, SensorEntity):
    """Representation of a power-related sensor in a Zuli Smartplug."""

    def __init__(self,
        coordinator: ZuliCoordinator,
        device_name: str,
        entity_name: str,
        sensor_class: SensorDeviceClass,
        unit: str,
        power_reading_key: PowerReadingKey
    ) -> None:
        super().__init__(coordinator)
        self._device: ZuliSmartplug = coordinator.device # type: ignore
        self._device_name = device_name
        self._entity_name = entity_name
        self._power_reading_key = power_reading_key
        self._sensor_class = sensor_class
        self._unit = unit
        self._value: int | None = None
        self.__set_state(coordinator.data) # type: ignore
    
    def __set_state(self, state: ZuliState) -> bool:
        power_reading = state["power_reading"]
        if power_reading:
            self._value = power_reading[self._power_reading_key]
            return True
        else:
            return False

    @callback
    def _handle_coordinator_update(self):
        if self.__set_state(self.coordinator.data): # type: ignore
            self.async_write_ha_state()

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_{self._device.address}_{self._entity_name.lower()}"

    @property
    def name(self) -> str:
        return self._entity_name
    
    @property
    def device_class(self) -> SensorDeviceClass:
        return self._sensor_class

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._device.address)},
            manufacturer="Zuli",
            model="Smartplug",
            name=self._device_name,
        )
    
    @property
    def native_unit_of_measurement(self) -> str:
        return self._unit

    @property
    def native_value(self) -> int | None:
        return self._value
