from __future__ import annotations
from dataclasses import dataclass
from typing import Callable

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
    BinarySensorDeviceClass,
)
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN
from .device_info import ps5_device_info


@dataclass
class PS5BinarySensorDescription(BinarySensorEntityDescription):
    value_fn: Callable[[dict], bool] | None = None


BINARY_SENSOR_DESCRIPTIONS: list[PS5BinarySensorDescription] = [
    PS5BinarySensorDescription(
        key="fan_active",
        name="PS5 Custom Fan Active",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:fan",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: bool(d.get("fan_active")),
    ),
    PS5BinarySensorDescription(
        key="kstuff_active",
        name="PS5 Kstuff Active",
        icon="mdi:chip",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: bool(d.get("kstuff_active")),
    ),
]


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        PS5BinarySensor(coordinator, desc)
        for desc in BINARY_SENSOR_DESCRIPTIONS
    )


class PS5BinarySensor(CoordinatorEntity, BinarySensorEntity):

    def __init__(self, coordinator, description: PS5BinarySensorDescription):
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"ps5_{coordinator.host}_{description.key}"

    @property
    def device_info(self) -> DeviceInfo:
        return ps5_device_info(self.coordinator)

    @property
    def available(self) -> bool:
        return self.coordinator.available and super().available

    @property
    def is_on(self) -> bool:
        if self.coordinator.data is None:
            return False
        return self.entity_description.value_fn(self.coordinator.data)
