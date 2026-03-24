import aiohttp
import logging
from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.core import HomeAssistant
from .const import DOMAIN, POLL_INTERVAL, EVENT_GAME_CHANGED

_LOGGER = logging.getLogger(__name__)


class PS5Coordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, host: str, port: int, mac: str = ""):
        self.host = host
        self.port = port
        self.mac = mac
        self._available = True
        self._last_game: str | None = None
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=POLL_INTERVAL),
        )

    @property
    def available(self) -> bool:
        return self._available

    async def _async_update_data(self) -> dict:
        url = f"http://{self.host}:{self.port}/api/stats"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    resp.raise_for_status()
                    data = await resp.json()

            if not self._available:
                _LOGGER.info("PS5 (%s:%s) is back online", self.host, self.port)
            self._available = True

            # Fire game changed event if active game has changed
            current_game = data.get("active_game")
            if current_game and current_game != self._last_game:
                self.hass.bus.async_fire(
                    EVENT_GAME_CHANGED,
                    {
                        "previous_game": self._last_game,
                        "current_game": current_game,
                        "current_game_name": data.get("active_game_name"),
                        "username": data.get("username"),
                    },
                )
                self._last_game = current_game

            return data

        except aiohttp.ClientConnectionError:
            if self._available:
                _LOGGER.warning(
                    "PS5 (%s:%s) is offline — entities marked unavailable",
                    self.host,
                    self.port,
                )
            self._available = False
            raise UpdateFailed(f"Cannot reach PS5 at {self.host}:{self.port}")

        except Exception as err:
            self._available = False
            raise UpdateFailed(f"Unexpected error from PS5: {err}")
