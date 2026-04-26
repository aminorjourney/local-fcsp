import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from .const import (
    DOMAIN,
    CONF_SCAN_INTERVAL,
    CONF_API_TIMEOUT,
    API_TIMEOUT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_HOST,
    DEFAULT_DEVKEY,
    CONF_DEBUG,
    DEFAULT_DEBUG,
    MIN_SCAN_INTERVAL,
    MIN_TIMEOUT,
    CONF_TIME_FORMAT, 
    DEFAULT_TIME_FORMAT, 
    TIME_FORMAT_OPTIONS,
)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Local FCSP.

    This shows the form to configure the integration in the UI."""

    # You know, because you're not a Binar or Johnny Number Five.
    # But if you are, 01001000 01100101 01101100 01101100 01101111 (Hello in binary!)

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            scan_interval = user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            timeout = user_input.get(CONF_API_TIMEOUT, API_TIMEOUT)

            if not user_input.get("devkey"):
                # Ideally use a translation key here, not a raw string
                errors["devkey"] = "invalid_devkey"
            else:
                # Sanitize user_input keys here if needed.
                # No idea what you'd sanitize—but always wash your hands for two full "Happy Birthdays."
                pass

            if scan_interval < MIN_SCAN_INTERVAL:
                errors[CONF_SCAN_INTERVAL] = "scan_interval_too_low"

            if timeout < MIN_TIMEOUT:
                errors[CONF_API_TIMEOUT] = "api_timeout_too_low"

            if not errors:
                return self.async_create_entry(
                    title="Local Ford Charge Station Pro",
                    data={
                        "host": user_input["host"],
                        "port": user_input["port"],
                        "devkey": user_input["devkey"],
                        CONF_API_TIMEOUT: timeout,
                        CONF_SCAN_INTERVAL: scan_interval,
                        CONF_DEBUG: user_input.get(CONF_DEBUG, DEFAULT_DEBUG),
                        CONF_TIME_FORMAT: user_input.get(CONF_TIME_FORMAT, DEFAULT_TIME_FORMAT),
                    },
                )

        # Like Vogons, Home Assistant insists forms are properly filled out.
        # This prevents crashes, even if the input is incomplete—
        # saving you from a poem about rediscovered cafeteria meatloaf.

        schema = vol.Schema({
            vol.Required("host", default=DEFAULT_HOST): str,
            vol.Required("devkey", default=DEFAULT_DEVKEY): str,
            vol.Required("port", default=443): int,
            vol.Required(CONF_API_TIMEOUT, default=API_TIMEOUT): int,
            vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
            vol.Optional(CONF_DEBUG, default=DEFAULT_DEBUG): bool,
            vol.Optional(CONF_TIME_FORMAT, default=DEFAULT_TIME_FORMAT): vol.In(TIME_FORMAT_OPTIONS),
        })

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)


# And here’s where you can tweak settings later,
# if you’re the kind of person who adjusts toaster darkness levels with a micrometer.

class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Local FCSP."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        errors = {}

        if user_input is not None:
            scan_interval = user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            timeout = user_input.get(CONF_API_TIMEOUT, API_TIMEOUT)

            if scan_interval < MIN_SCAN_INTERVAL:
                errors[CONF_SCAN_INTERVAL] = "scan_interval_too_low"

            if timeout < MIN_TIMEOUT:
                errors[CONF_API_TIMEOUT] = "api_timeout_too_low"

            if not errors:
                return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema({
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=self.config_entry.options.get(
                    CONF_SCAN_INTERVAL,
                    self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                )
            ): int,
            vol.Optional(
                CONF_TIME_FORMAT,
                default=self.config_entry.options.get(
                    CONF_TIME_FORMAT,
                    self.config_entry.data.get(CONF_TIME_FORMAT, DEFAULT_TIME_FORMAT)
                )
            ): vol.In(TIME_FORMAT_OPTIONS),

            vol.Optional(
                CONF_API_TIMEOUT,
                default=self.config_entry.options.get(
                    CONF_API_TIMEOUT,
                    self.config_entry.data.get(CONF_API_TIMEOUT, API_TIMEOUT)
                )
            ): int,
            vol.Optional(
                CONF_DEBUG,
                default=self.config_entry.options.get(
                    CONF_DEBUG,
                    self.config_entry.data.get(CONF_DEBUG, DEFAULT_DEBUG)
                )
            ): bool,
        })

        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
