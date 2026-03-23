from __future__ import annotations
import aiohttp
import logging

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerState,
    MediaPlayerEntityFeature,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN
from .device_info import ps5_device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([PS5MediaPlayer(coordinator)])


class PS5MediaPlayer(CoordinatorEntity, MediaPlayerEntity):
    _attr_name = "PS5"
    _attr_media_content_type = "game"
    _attr_supported_features = (
        MediaPlayerEntityFeature.SELECT_SOURCE
        | MediaPlayerEntityFeature.BROWSE_MEDIA
    )

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"ps5_{coordinator.host}_media_player"
        self._library: dict[str, dict] = {}

    @property
    def device_info(self) -> DeviceInfo:
        return ps5_device_info(self.coordinator)

    @property
    def available(self) -> bool:
        return self.coordinator.available and super().available

    @property
    def _data(self) -> dict:
        return self.coordinator.data or {}

    # -------------------------------------------------------------------------
    # State
    # -------------------------------------------------------------------------
    @property
    def state(self) -> MediaPlayerState:
        app_state = self._data.get("app_state", "").lower()
        if app_state in ("suspended", "standby", "rest"):
            return MediaPlayerState.STANDBY
        active_game = self._data.get("active_game")
        if not active_game or active_game == "MENU":
            return MediaPlayerState.ON
        return MediaPlayerState.PLAYING

    # -------------------------------------------------------------------------
    # Now playing
    # -------------------------------------------------------------------------
    @property
    def media_title(self) -> str | None:
        active_game = self._data.get("active_game")
        if not active_game or active_game == "MENU":
            return None
        return self._data.get("active_game_name") or active_game

    @property
    def media_content_id(self) -> str | None:
        active_game = self._data.get("active_game")
        return None if not active_game or active_game == "MENU" else active_game

    @property
    def media_image_url(self) -> str | None:
        active_game = self._data.get("active_game")
        if not active_game or active_game == "MENU":
            return None
        return (
            f"http://{self.coordinator.host}:{self.coordinator.port}"
            f"/assets/pic?id={active_game}"
        )

    @property
    def media_image_remotely_accessible(self) -> bool:
        return False

    @property
    def media_artist(self) -> str | None:
        return self._data.get("username") or None

    # -------------------------------------------------------------------------
    # Source / game library
    # -------------------------------------------------------------------------
    @property
    def source(self) -> str | None:
        active_game = self._data.get("active_game")
        if not active_game or active_game == "MENU":
            return None
        game = self._library.get(active_game)
        return game["name"] if game else active_game

    @property
    def source_list(self) -> list[str]:
        return sorted(g["name"] for g in self._library.values())

    async def async_select_source(self, source: str) -> None:
        game_id = next(
            (gid for gid, g in self._library.items() if g["name"] == source),
            None,
        )
        if not game_id:
            _LOGGER.warning("PS5: game '%s' not found in library", source)
            return

        url = f"http://{self.coordinator.host}:{self.coordinator.port}/api/launch"
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(url, data=game_id)
        except Exception as err:
            _LOGGER.error("PS5: failed to launch '%s': %s", source, err)

        await self.coordinator.async_request_refresh()

    # -------------------------------------------------------------------------
    # Library refresh
    # -------------------------------------------------------------------------
    async def async_refresh_library(self) -> None:
        url = f"http://{self.coordinator.host}:{self.coordinator.port}/api/library"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    self._library = {
                        g["id"]: {
                            "name": g["name"],
                            "type": g["type"],
                            "version": g.get("version"),
                            "region": g.get("region"),
                        }
                        for g in data.get("games", [])
                        if g.get("exists", True) not in (False, "false")
                    }
                    _LOGGER.debug(
                        "PS5: library loaded with %d games", len(self._library)
                    )
        except Exception as err:
            _LOGGER.warning("PS5: failed to refresh library: %s", err)

    def _handle_library_refresh(self) -> None:
        new_total = (self.coordinator.data or {}).get("total", 0)
        if new_total != len(self._library):
            self.hass.async_create_task(self.async_refresh_library())

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        await self.async_refresh_library()
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_library_refresh)
        )
