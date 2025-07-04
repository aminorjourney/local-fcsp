import voluptuous as vol
from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv

DOMAIN = "local_fcsp"

class LocalFCSPConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def _get_data_schema(self, user_input=None):
        user_input = user_input or {}
        return vol.Schema({
            vol.Required("host", default=user_input.get("host", "192.168.1.1")): str,
            vol.Required("devkey", default=user_input.get("devkey", "1bcr1ee0j58v9vzvy31n7w0imfz5dqi85tzem7om")): str,
            vol.Optional("port", default=user_input.get("port", 443)): cv.port,
            vol.Optional("timeout", default=user_input.get("timeout", 30)): int,
            vol.Optional("debug", default=user_input.get("debug", False)): bool,
        })

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            return self.async_create_entry(
                title="Local Ford Charge Station Pro",
                data=user_input
            )

        data_schema = self._get_data_schema()

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors
        )
