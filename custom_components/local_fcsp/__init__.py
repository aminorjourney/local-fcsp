# INIT: The VIP who swaggers into the fancy restaurant yelling "Hey! VIC coming through!"
# Also imports the usual suspects, including those lovely constants. 
# Yes, I said "VIC". That stands for Queenie Octavia Christina Deerhart, a Very Important Collie. 

import logging
from homeassistant.exceptions import ConfigEntryNotReady
from fcsp_api import FCSP
from .const import DOMAIN, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DEFAULT_HOST, DEFAULT_DEVKEY

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass, config):
    """
    Initial setup of the Local FCSP integration.

    This gets called once when Home Assistant starts up. We set up
    an empty data container keyed by our DOMAIN so we have a place
    to stash our stuff later.

    Args:
        hass: Home Assistant core object
        config: Configuration dict (usually empty for config entries)

    Returns:
        True, always (setup never fails here)
    """
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass, entry):
    """
    Set up the FCSP client using configuration from a config entry.

    This happens when a user adds the integration through the UI or
    when Home Assistant reloads the integration.

    It creates an FCSP client instance and tries to connect to the
    physical device (charger). If that fails, we politely tell HA
    to try again later (ConfigEntryNotReady).

    Args:
        hass: Home Assistant core object
        entry: ConfigEntry containing user settings

    Returns:
        True on successful setup
    """
    host = entry.data.get("host", DEFAULT_HOST)
    devkey = entry.data.get("devkey", DEFAULT_DEVKEY)
    port = entry.data.get("port", 443)
    timeout = entry.data.get("timeout", 60)

    _LOGGER.debug(f"Setting up FCSP client with host={host}, devkey={devkey}, port={port}, timeout={timeout}")

    fcsp = FCSP(host=host, devkey=devkey, port=port, timeout=timeout)

    try:
        # Connect to the charger. This is like putting a coin in the arcade machine—
        # without it, no game.
        await hass.async_add_executor_job(fcsp.connect)
        # Ping the device for status so we know it’s awake and kicking.
        await hass.async_add_executor_job(fcsp.get_status)
    except Exception as err:
        _LOGGER.error(f"Failed to connect to FCSP device: {err}")
        # Raise this so HA knows to retry later instead of giving up.
        raise ConfigEntryNotReady from err

    scan_interval = entry.options.get(
        CONF_SCAN_INTERVAL,
        entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    )

    # Store our client and config so other parts of the integration can find them.
    hass.data[DOMAIN][entry.entry_id] = {
        "config": entry.data,
        "fcsp": fcsp,
        "scan_interval": scan_interval,
    }

    # Forward the setup to sensors so they can start tracking data.
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    return True

async def async_unload_entry(hass, entry):
    """
    Unload a config entry.

    This happens when a user removes the integration or disables it.
    We tell Home Assistant to unload all entities related to this config,
    then clean up our stored data.

    Args:
        hass: Home Assistant core object
        entry: ConfigEntry being unloaded

    Returns:
        True if unload was successful
    """
    await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True
