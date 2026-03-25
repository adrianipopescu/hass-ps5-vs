from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN
from .device_info import ps5_device_info


@dataclass
class PS5SensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict, str, int], any] | None = None
    retain_when_offline: bool = False


SENSOR_DESCRIPTIONS: list[PS5SensorDescription] = [
    # --- Standard entities ---
    PS5SensorDescription(
        key="total_games",
        name="PS5 Total Games",
        native_unit_of_measurement="Games",
        icon="mdi:library",
        value_fn=lambda d, h, p: d.get("total"),
        retain_when_offline=True,
    ),
    PS5SensorDescription(
        key="ps5_games",
        name="PS5 Game Count",
        native_unit_of_measurement="Games",
        icon="mdi:sony-playstation",
        value_fn=lambda d, h, p: d.get("ps5"),
        retain_when_offline=True,
    ),
    PS5SensorDescription(
        key="ps4_games",
        name="PS4 Game Count",
        native_unit_of_measurement="Games",
        icon="mdi:gamepad-square",
        value_fn=lambda d, h, p: d.get("ps4"),
        retain_when_offline=True,
    ),

    # --- Diagnostic entities ---
    PS5SensorDescription(
        key="cpu_temp",
        name="PS5 CPU Temperature",
        native_unit_of_measurement="°C",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:cpu-64-bit",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d, h, p: d.get("cpu"),
    ),
    PS5SensorDescription(
        key="soc_temp",
        name="PS5 SoC Temperature",
        native_unit_of_measurement="°C",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:thermometer",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d, h, p: d.get("soc"),
    ),
    PS5SensorDescription(
        key="fan_target",
        name="PS5 Fan Target",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:fan",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d, h, p: d.get("fan_target"),
    ),
    PS5SensorDescription(
        key="uptime",
        name="PS5 Uptime",
        icon="mdi:clock-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d, h, p: d.get("sys_uptime"),
    ),
    PS5SensorDescription(
        key="sentinel_state",
        name="PS5 Sentinel State",
        icon="mdi:shield-check",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d, h, p: d.get("sentinel_state"),
    ),
]


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        PS5Sensor(coordinator, desc)
        for desc in SENSOR_DESCRIPTIONS
    )


class PS5Sensor(CoordinatorEntity, SensorEntity):

    def __init__(self, coordinator, description: PS5SensorDescription):
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"ps5_{coordinator.host}_{description.key}"

    @property
    def device_info(self) -> DeviceInfo:
        return ps5_device_info(self.coordinator)

    @property
    def available(self) -> bool:
        if self.entity_description.retain_when_offline:
            return self.coordinator.data is not None and super().available
        return self.coordinator.available and super().available

    @property
    def native_value(self):
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(
            self.coordinator.data,
            self.coordinator.host,
            self.coordinator.port,
        )
