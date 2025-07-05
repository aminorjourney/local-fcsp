import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryNotReady

from fcsp_api import FCSP

from .const import DOMAIN, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DEFAULT_HOST, DEFAULT_DEVKEY

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the Local FCSP integration (YAML-based, unused here)."""
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the integration from a config entry."""
    host = entry.data.get("host", DEFAULT_HOST)
    devkey = entry.data.get("devkey", DEFAULT_DEVKEY)
    port = entry.data.get("port", 443)
    timeout = entry.data.get("timeout", 60)

    _LOGGER.debug(
        "Initializing FCSP client with host=%s, port=%d, timeout=%d",
        host, port, timeout
    )

    # Instantiate the client
    fcsp = FCSP(host=host, devkey=devkey, port=port, timeout=timeout)

    try:
        # Perform connection check in executor thread
        await hass.async_add_executor_job(fcsp.connect)
        await hass.async_add_executor_job(fcsp.get_status)
    except Exception as err:
        _LOGGER.error("Unable to communicate with FCSP device: %s", err)
        raise ConfigEntryNotReady from err

    scan_interval = entry.options.get(
        CONF_SCAN_INTERVAL,
        entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    )

    # Store only what’s needed for downstream components
    hass.data[DOMAIN][entry.entry_id] = {
        "fcsp": fcsp,
        "scan_interval": scan_interval,
    }

    # Forward entry to the sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry and remove its data."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
