import asyncio
import aiohttp
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import zeroconf
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
        found = await self._discover_via_mdns()
        if found:
            self._discovered_host = found["host"]
            self._discovered_port = found["port"]
            return await self.async_step_confirm()
        return await self.async_step_manual(error="not_found")

    async def async_step_zeroconf(
        self, discovery_info: zeroconf.ZeroconfServiceInfo
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

    async def _discover_via_mdns(self) -> dict | None:
        aiozc = await zeroconf.async_get_async_instance(self.hass)
        discovered = []
        found_event = asyncio.Event()
        loop = asyncio.get_event_loop()

        from zeroconf.asyncio import AsyncServiceBrowser
        from zeroconf import ServiceStateChange

        def on_service_state_change(zeroconf_inst, service_type, name, state_change):
            if state_change != ServiceStateChange.Added:
                return

            async def _resolve():
                info = await aiozc.async_get_service_info(service_type, name)
                if not info:
                    return
                addresses = info.parsed_addresses()
                if addresses:
                    discovered.append({"host": addresses[0]})
                    found_event.set()

            loop.create_task(_resolve())

        browser = AsyncServiceBrowser(
            aiozc.zeroconf,
            ["_http._tcp.local."],
            handlers=[on_service_state_change],
        )
        try:
            await asyncio.wait_for(found_event.wait(), timeout=4.0)
        except asyncio.TimeoutError:
            pass
        finally:
            await browser.async_cancel()

        for candidate in discovered:
            result = await _probe_voidshell(candidate["host"], DEFAULT_PORT)
            if result is not None:
                return {"host": candidate["host"], "port": DEFAULT_PORT}
        return None

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
