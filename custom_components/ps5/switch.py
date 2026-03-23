from __future__ import annotations
import aiohttp
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN
from .device_info import ps5_device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([PS5ScannerSwitch(coordinator)])


class PS5ScannerSwitch(CoordinatorEntity, SwitchEntity):
    _attr_name = "PS5 Scanner Paused"
    _attr_icon = "mdi:pause-circle"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"ps5_{coordinator.host}_scanner_paused"

    @property
    def device_info(self) -> DeviceInfo:
        return ps5_device_info(self.coordinator)

    @property
    def available(self) -> bool:
        return self.coordinator.available and super().available

    @property
    def is_on(self) -> bool:
        """True means scanner is paused."""
        data = self.coordinator.data or {}
        val = data.get("paused", False)
        return val is True or val == "true"

    async def async_turn_on(self, **kwargs) -> None:
        """Pause the scanner."""
        await self._toggle()

    async def async_turn_off(self, **kwargs) -> None:
        """Resume the scanner."""
        await self._toggle()

    async def _toggle(self) -> None:
        url = f"http://{self.coordinator.host}:{self.coordinator.port}/api/pause"
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(url)
        except Exception as err:
            _LOGGER.error("PS5: failed to toggle scanner: %s", err)
        await self.coordinator.async_request_refresh()
