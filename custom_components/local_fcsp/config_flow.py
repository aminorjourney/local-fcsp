import voluptuous as vol
from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL

class LocalFCSPConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def _get_data_schema(self, user_input=None):
        user_input = user_input or {}
        return vol.Schema({
            vol.Required("host", default=user_input.get("host", "192.168.1.1")): str,
            vol.Required("devkey", default=user_input.get("devkey", "")): str,
            vol.Optional("port", default=user_input.get("port", 443)): cv.port,
            vol.Optional("timeout", default=user_input.get("timeout", 30)): int,
            vol.Optional("debug", default=user_input.get("debug", False)): bool,
            vol.Optional(CONF_SCAN_INTERVAL, default=user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)): int,
        })

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            return self.async_create_entry(
                title="Local Ford Charge Station Pro",
                data=user_input
            )

        data_schema = self._get_data_schema(user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors
        )

    async def async_get_options_flow(self, config_entry):
        return LocalFCSPOptionsFlowHandler(config_entry)


class LocalFCSPOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        user_input = user_input or {}

        data_schema = vol.Schema({
            vol.Optional(CONF_SCAN_INTERVAL, default=self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)): int,
            vol.Optional("debug", default=self.config_entry.options.get("debug", False)): bool,
        })

        if user_input:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(step_id="init", data_schema=data_schema)
