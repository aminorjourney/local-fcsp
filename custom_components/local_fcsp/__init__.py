from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from fcsp_api import FCSP

DOMAIN = "local_fcsp"

async def async_setup(hass: HomeAssistant, config: dict):
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    host = entry.data.get("host")
    devkey = entry.data.get("devkey")
    port = entry.data.get("port", 443)
    timeout = entry.data.get("timeout", 30)  # <-- Consistent default here

    fcsp = FCSP(host=host, devkey=devkey, port=port, timeout=timeout)

    try:
        await hass.async_add_executor_job(fcsp.connect)
        status = await hass.async_add_executor_job(fcsp.get_status)
    except Exception as err:
        raise ConfigEntryNotReady from err

    home_integration_attached = bool(status.get("inverter_count", 0))

    hass.data[DOMAIN][entry.entry_id] = {
        "config": entry.data,
        "fcsp": fcsp,
        "home_integration_attached": home_integration_attached,
    }

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True
