import aiohttp
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from .const import DOMAIN, CONF_HOST, CONF_PORT, CONF_MAC, DEFAULT_PORT
from .discovery import discover_ps5

_LOGGER = logging.getLogger(__name__)


async def _probe_voidshell(host: str, port: int, timeout: float = 3.0) -> dict | None:
    url = f"http://{host}:{port}/api/stats"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if "app_state" in data or "cpu" in data:
                        return data
    except Exception:
        pass
    return None


class PS5ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self._discovered_host: str | None = None
        self._discovered_port: int = DEFAULT_PORT
        self._discovered_mac: str = ""
        self._discovered_name: str = "PS5"

    @staticmethod
    def async_get_options_flow(config_entry):
        from .options_flow import PS5OptionsFlow
        return PS5OptionsFlow(config_entry)

    async def async_step_user(self, user_input=None) -> FlowResult:
        discovered = await discover_ps5()
        if discovered:
            self._discovered_host = discovered["host"]
            self._discovered_mac = discovered["mac"]
            self._discovered_name = discovered["name"]
            await self.async_set_unique_id(self._discovered_mac or self._discovered_host)
            self._abort_if_unique_id_configured()
            return await self.async_step_confirm()
        return await self.async_step_manual()

    async def async_step_integration_discovery(self, discovery_info: dict) -> FlowResult:
        self._discovered_host = discovery_info["host"]
        self._discovered_mac = discovery_info["mac"]
        self._discovered_name = discovery_info["name"]
        await self.async_set_unique_id(self._discovered_mac or self._discovered_host)
        self._abort_if_unique_id_configured()
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input=None) -> FlowResult:
        if user_input is not None:
            return self._create_entry(
                self._discovered_host, self._discovered_port, self._discovered_mac
            )
        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),
            description_placeholders={
                "name": self._discovered_name,
                "host": self._discovered_host,
            },
        )

    async def async_step_manual(self, user_input=None) -> FlowResult:
        errors = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = user_input.get(CONF_PORT, DEFAULT_PORT)
            if await _probe_voidshell(host, port) is None:
                errors["base"] = "cannot_connect"
            else:
                return self._create_entry(host, port)

        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST, default=""): str,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=65535)
                ),
            }),
            errors=errors,
            last_step=True,
        )

    def _create_entry(self, host: str, port: int, mac: str = "") -> FlowResult:
        return self.async_create_entry(
            title=f"PlayStation 5 ({host})",
            data={CONF_HOST: host, CONF_PORT: port, CONF_MAC: mac},
        )
