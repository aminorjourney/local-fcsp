from homeassistant.helpers import device_registry as dr
from homeassistant.exceptions import ConfigEntryNotReady
from .fcsp_api import FCSP  # Adjust import as needed
from .const import DOMAIN, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL

async def async_setup(hass, config):
    """Set up the FCSP integration."""
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass, entry):
    """Set up FCSP from a config entry."""

    host = entry.data.get("host")
    devkey = entry.data.get("devkey")
    port = entry.data.get("port", 443)
    timeout = entry.data.get("timeout", 10)

    # Create FCSP API client
    fcsp = FCSP(host=host, devkey=devkey, port=port, timeout=timeout)

    try:
        # Test connection or minimal API call in executor (since fcsp likely sync)
        await hass.async_add_executor_job(fcsp.get_status)
    except Exception as err:
        raise ConfigEntryNotReady from err

    # Get scan interval from options or fallback to defaults
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))

    # Save the entry data and API client for later use if needed
    hass.data[DOMAIN][entry.entry_id] = {
        "config": entry.data,
        "fcsp": fcsp,
        "scan_interval": scan_interval,
    }

    # Forward setup to platforms only if connection test succeeded
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    return True

async def async_unload_entry(hass, entry):
    """Unload a config entry."""
    await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True
