import asyncio
import aiohttp
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from .const import DOMAIN, CONF_HOST, CONF_PORT, CONF_MAC, DEFAULT_PORT

_LOGGER = logging.getLogger(__name__)

_DDP_PORT = 9302
_DDP_MSG = b"SRCH * HTTP/1.1\ndevice-discovery-protocol-version:00030010\n"


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


async def _discover_via_ddp() -> dict | None:
    loop = asyncio.get_running_loop()
    found: asyncio.Future = loop.create_future()
    transport = None

    class _Proto(asyncio.DatagramProtocol):
        def datagram_received(self, data, addr):
            if found.done():
                return
            text = data.decode("utf-8", errors="ignore")
            if "host-type:PS5" not in text:
                return
            info = {}
            for line in text.splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    info[k.strip().lower()] = v.strip()
            found.set_result({
                "host": addr[0],
                "mac": info.get("host-id", ""),
                "name": info.get("host-name", "PS5"),
            })

        def error_received(self, exc):
            if not found.done():
                found.cancel()

    try:
        transport, _ = await loop.create_datagram_endpoint(
            _Proto,
            local_addr=("0.0.0.0", 0),
            allow_broadcast=True,
        )
        transport.sendto(_DDP_MSG, ("255.255.255.255", _DDP_PORT))
        return await asyncio.wait_for(asyncio.shield(found), timeout=3.0)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        return None
    except Exception:
        return None
    finally:
        if transport:
            transport.close()


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
        discovered = await _discover_via_ddp()
        if discovered:
            self._discovered_host = discovered["host"]
            self._discovered_mac = discovered["mac"]
            self._discovered_name = discovered["name"]
            await self.async_set_unique_id(self._discovered_mac or self._discovered_host)
            self._abort_if_unique_id_configured()
            return await self.async_step_confirm()
        return await self.async_step_manual()

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
