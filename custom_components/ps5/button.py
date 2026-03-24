from __future__ import annotations
import socket
from dataclasses import dataclass
from typing import Callable, Awaitable
import aiohttp
import logging

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN
from .device_info import ps5_device_info

_LOGGER = logging.getLogger(__name__)


@dataclass
class PS5ButtonDescription(ButtonEntityDescription):
    endpoint: str = ""
    method: str = "POST"
    entity_category: EntityCategory | None = EntityCategory.CONFIG


BUTTON_DESCRIPTIONS: list[PS5ButtonDescription] = [
    PS5ButtonDescription(
        key="rescan",
        name="PS5 Rescan Library",
        icon="mdi:refresh",
        endpoint="/api/rescan",
    ),
    PS5ButtonDescription(
        key="sleep",
        name="PS5 Sleep",
        icon="mdi:power-sleep",
        endpoint="/api/sleep",
    ),
    PS5ButtonDescription(
        key="repair",
        name="PS5 Repair",
        icon="mdi:wrench",
        endpoint="/api/repair",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    PS5ButtonDescription(
        key="clear_logs",
        name="PS5 Clear Logs",
        icon="mdi:delete-sweep",
        endpoint="/api/logs/clear",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
]


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[ButtonEntity] = [
        PS5Button(coordinator, desc) for desc in BUTTON_DESCRIPTIONS
    ]
    if coordinator.mac:
        entities.append(PS5WakeButton(coordinator))
    async_add_entities(entities)


class PS5Button(ButtonEntity):

    def __init__(self, coordinator, description: PS5ButtonDescription):
        self._coordinator = coordinator
        self.entity_description = description
        self._attr_unique_id = f"ps5_{coordinator.host}_{description.key}"

    @property
    def device_info(self) -> DeviceInfo:
        return ps5_device_info(self._coordinator)

    @property
    def available(self) -> bool:
        return self._coordinator.available

    async def async_press(self) -> None:
        url = (
            f"http://{self._coordinator.host}:{self._coordinator.port}"
            f"{self.entity_description.endpoint}"
        )
        try:
            async with aiohttp.ClientSession() as session:
                await session.request(self.entity_description.method, url)
            _LOGGER.debug("PS5: pressed button %s", self.entity_description.key)
        except Exception as err:
            _LOGGER.error(
                "PS5: failed to press button %s: %s",
                self.entity_description.key,
                err,
            )
        await self._coordinator.async_request_refresh()


class PS5WakeButton(ButtonEntity):
    _attr_name = "PS5 Wake"
    _attr_icon = "mdi:power"

    def __init__(self, coordinator):
        self._coordinator = coordinator
        self._attr_unique_id = f"ps5_{coordinator.host}_wake"

    @property
    def device_info(self) -> DeviceInfo:
        return ps5_device_info(self._coordinator)

    @property
    def available(self) -> bool:
        return bool(self._coordinator.mac)

    async def async_press(self) -> None:
        mac = self._coordinator.mac
        if not mac:
            return

        def _send() -> None:
            mac_bytes = bytes.fromhex(mac.replace(":", "").replace("-", ""))
            magic = b"\xff" * 6 + mac_bytes * 16
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                sock.sendto(magic, ("255.255.255.255", 9))

        await self.hass.async_add_executor_job(_send)
        _LOGGER.debug("PS5: sent WoL magic packet to %s", mac)
