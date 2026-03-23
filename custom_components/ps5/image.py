from __future__ import annotations

from homeassistant.components.image import ImageEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .device_info import ps5_device_info


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([PS5UserImage(coordinator, hass)])


class PS5UserImage(CoordinatorEntity, ImageEntity):
    _attr_name = "PS5 Active User"
    _attr_content_type = "image/jpeg"

    def __init__(self, coordinator, hass):
        CoordinatorEntity.__init__(self, coordinator)
        ImageEntity.__init__(self, hass)
        self._attr_unique_id = f"ps5_{coordinator.host}_active_user"
        self._cached_url: str | None = None

    @property
    def device_info(self) -> DeviceInfo:
        return ps5_device_info(self.coordinator)

    @property
    def available(self) -> bool:
        return self.coordinator.available and super().available

    @property
    def _data(self) -> dict:
        return self.coordinator.data or {}

    @property
    def image_url(self) -> str | None:
        userid = self._data.get("userid")
        if not userid:
            return None
        return (
            f"http://{self.coordinator.host}:{self.coordinator.port}"
            f"/api/avatar?id={userid}"
        )

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "username": self._data.get("username"),
            "userid": self._data.get("userid"),
        }

    def _handle_coordinator_update(self) -> None:
        new_url = self.image_url
        if new_url != self._cached_url:
            self._cached_url = new_url
            self._attr_image_last_updated = dt_util.utcnow()
        super()._handle_coordinator_update()
