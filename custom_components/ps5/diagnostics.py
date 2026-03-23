from __future__ import annotations
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_HOST, CONF_PORT


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    return {
        "config": {
            "host": entry.data.get(CONF_HOST),
            "port": entry.data.get(CONF_PORT),
        },
        "coordinator": {
            "available": coordinator.available,
            "last_update_success": coordinator.last_update_success,
            "last_updated": str(coordinator.last_update_success_time)
            if hasattr(coordinator, "last_update_success_time")
            else None,
        },
        "last_api_response": coordinator.data or {},
    }
