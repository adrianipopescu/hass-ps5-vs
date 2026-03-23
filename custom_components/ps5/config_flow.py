import aiohttp
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import zeroconf as ha_zeroconf
from homeassistant.data_entry_flow import FlowResult
from .const import DOMAIN, CONF_HOST, CONF_PORT, DEFAULT_PORT

_LOGGER = logging.getLogger(__name__)


async def _probe_voidshell(host: str, port: int, timeout: float = 3.0) -> dict | None:
    """Check if the PS5 API is reachable. Returns stats data or None."""
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

    @staticmethod
    def async_get_options_flow(config_entry):
        from .options_flow import PS5OptionsFlow
        return PS5OptionsFlow(config_entry)

    async def async_step_user(self, user_input=None) -> FlowResult:
        return await self.async_step_manual()

    async def async_step_zeroconf(
        self, discovery_info: ha_zeroconf.ZeroconfServiceInfo
    ) -> FlowResult:
        """Handle discovery by HA's zeroconf integration."""
        host = discovery_info.host
        port = DEFAULT_PORT

        result = await _probe_voidshell(host, port)
        if result is None:
            return self.async_abort(reason="not_found")

        await self.async_set_unique_id(host)
        self._abort_if_unique_id_configured()

        self._discovered_host = host
        self._discovered_port = port
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input=None) -> FlowResult:
        if user_input is not None:
            return self._create_entry(self._discovered_host, self._discovered_port)
        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),
            description_placeholders={
                "host": self._discovered_host,
                "port": str(self._discovered_port),
            },
        )

    async def async_step_manual(self, user_input=None, error=None) -> FlowResult:
        errors = {}
        if error == "not_found":
            errors["base"] = "not_found"

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = user_input.get(CONF_PORT, DEFAULT_PORT)
            result = await _probe_voidshell(host, port)
            if result is None:
                errors["base"] = "cannot_connect"
            else:
                return self._create_entry(host, port)

        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST, default="192.168.1.245"): str,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=65535)
                ),
            }),
            errors=errors,
            last_step=True,
        )

    def _create_entry(self, host: str, port: int) -> FlowResult:
        return self.async_create_entry(
            title=f"PlayStation 5 ({host})",
            data={CONF_HOST: host, CONF_PORT: port},
        )
