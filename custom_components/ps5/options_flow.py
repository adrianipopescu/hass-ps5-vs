import voluptuous as vol
from homeassistant.config_entries import OptionsFlow, ConfigEntry
from homeassistant.data_entry_flow import FlowResult
from .const import CONF_HOST, CONF_PORT, DEFAULT_PORT
from .config_flow import _probe_voidshell


class PS5OptionsFlow(OptionsFlow):

    def __init__(self, config_entry: ConfigEntry):
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None) -> FlowResult:
        errors = {}

        current_host = self._config_entry.data.get(CONF_HOST, "")
        current_port = self._config_entry.data.get(CONF_PORT, DEFAULT_PORT)

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = user_input[CONF_PORT]
            result = await _probe_voidshell(host, port)
            if result is None:
                errors["base"] = "cannot_connect"
            else:
                self.hass.config_entries.async_update_entry(
                    self._config_entry,
                    data={CONF_HOST: host, CONF_PORT: port},
                )
                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST, default=current_host): str,
                vol.Optional(CONF_PORT, default=current_port): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=65535)
                ),
            }),
            errors=errors,
        )
