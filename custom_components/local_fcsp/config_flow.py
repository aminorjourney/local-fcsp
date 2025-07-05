import logging
from typing import Any, Dict, Optional

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SHOW_RAW_DATA,
    DEFAULT_SHOW_LAST_UPDATED,
    CONF_SHOW_RAW_DATA,
    CONF_SHOW_LAST_UPDATED,
    CONF_HOST,
    CONF_DEVKEY,
    CONF_PORT,
    CONF_TIMEOUT,
    CONF_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default="192.168.20.65"): str,
        vol.Required(CONF_DEVKEY, default="0000000000000000"): str,
        vol.Optional(CONF_PORT, default=443): int,
        vol.Optional(CONF_TIMEOUT, default=60): int,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
        vol.Optional(CONF_SHOW_RAW_DATA, default=DEFAULT_SHOW_RAW_DATA): bool,
        vol.Optional(CONF_SHOW_LAST_UPDATED, default=DEFAULT_SHOW_LAST_UPDATED): bool,
    }
)

class FCSPConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self._data: Dict[str, Any] = {}

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        if user_input is not None:
            # Validate connection here if you want, or defer to setup_entry
            self._data = user_input
            return self.async_create_entry(title="Ford Charge Station Pro", data=self._data)

        return self.async_show_form(step_id="user", data_schema=STEP_USER_DATA_SCHEMA)

    async def async_step_import(self, import_data: Dict[str, Any]) -> FlowResult:
        self._data = import_data
        return self.async_create_entry(title="Ford Charge Station Pro", data=self._data)

class FCSPOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        options = self.config_entry.options

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data_schema = vol.Schema(
            {
                vol.Optional(CONF_SCAN_INTERVAL, default=options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)): int,
                vol.Optional(CONF_SHOW_RAW_DATA, default=options.get(CONF_SHOW_RAW_DATA, DEFAULT_SHOW_RAW_DATA)): bool,
                vol.Optional(CONF_SHOW_LAST_UPDATED, default=options.get(CONF_SHOW_LAST_UPDATED, DEFAULT_SHOW_LAST_UPDATED)): bool,
            }
        )

        return self.async_show_form(step_id="init", data_schema=data_schema)
