from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval

from .const import DOMAIN, CONF_HOST, CONF_PORT, CONF_MAC, DEFAULT_PORT
from .coordinator import PS5Coordinator
from .discovery import discover_ps5, save_ddp_cache, load_ddp_cache

PLATFORMS = ["sensor", "binary_sensor", "media_player", "image", "button", "switch"]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    async def _scan(_now=None) -> None:
        discovered = await discover_ps5()

        # Broadcast failed (cross-subnet etc.) — try unicast to cached hosts
        if not discovered:
            cache = await load_ddp_cache(hass)
            for entry_data in cache.values():
                result = await discover_ps5(host=entry_data["host"])
                if result:
                    discovered = result
                    break

        if not discovered:
            return

        await save_ddp_cache(hass, discovered)

        # Update config entry host if PS5 moved to a new IP
        for entry in hass.config_entries.async_entries(DOMAIN):
            if (
                entry.data.get(CONF_MAC)
                and entry.data.get(CONF_MAC) == discovered.get("mac")
                and entry.data.get(CONF_HOST) != discovered["host"]
            ):
                _LOGGER.info(
                    "PS5: IP changed from %s to %s, updating config entry",
                    entry.data[CONF_HOST],
                    discovered["host"],
                )
                hass.config_entries.async_update_entry(
                    entry, data={**entry.data, CONF_HOST: discovered["host"]}
                )

        configured = {e.data.get(CONF_HOST) for e in hass.config_entries.async_entries(DOMAIN)}
        if discovered["host"] in configured:
            return
        if any(f["handler"] == DOMAIN for f in hass.config_entries.flow.async_progress()):
            return
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "integration_discovery"},
                data=discovered,
            )
        )

    hass.async_create_task(_scan())
    async_track_time_interval(hass, _scan, timedelta(minutes=5))
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = PS5Coordinator(
        hass,
        host=entry.data[CONF_HOST],
        port=entry.data.get(CONF_PORT, DEFAULT_PORT),
        mac=entry.data.get(CONF_MAC, ""),
    )
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded
