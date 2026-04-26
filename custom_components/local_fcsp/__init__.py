# INIT: The VIP who swaggers into the fancy restaurant yelling "Hey! VIC coming through!"
# Also imports the usual suspects, including those lovely constants.
# Yes, I said "VIC". That stands for Queenie Octavia Christina Deerhart, a Very Important Collie.

import logging
from homeassistant.exceptions import ConfigEntryNotReady
from fcsp_api import FCSP
from .const import (
    DOMAIN,
    DEFAULT_HOST,
    DEFAULT_DEVKEY,
    MIN_TIMEOUT,
    API_TIMEOUT,
    MIN_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    CONF_SCAN_INTERVAL,
    CONF_API_TIMEOUT,
)

from .cache import LocalFcspCache
from .coordinator import FcspDataUpdateCoordinator


_LOGGER = logging.getLogger(__name__)

async def async_setup(hass, config):
    """
    Initial setup of the Local FCSP integration.

    Sets up a place to store our frozen peas (old data).
    """
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass, entry):
    """
    Set up the FCSP client using configuration from a config entry.

    Loads cached data so we can show stale data (frozen peas) immediately,
    then kicks off a background refresh to get fresh data.
    """
    host = entry.data.get("host", DEFAULT_HOST)
    devkey = entry.data.get("devkey", DEFAULT_DEVKEY)
    port = entry.data.get("port", 443)
    timeout = max(entry.data.get(CONF_API_TIMEOUT, API_TIMEOUT), MIN_TIMEOUT)

    _LOGGER.debug(f"Setting up FCSP client with host={host}, devkey={devkey}, port={port}, timeout={timeout}")

    fcsp = FCSP(host=host, devkey=devkey, port=port, timeout=timeout)

    try:
        await hass.async_add_executor_job(fcsp.connect)
    except Exception as err:
        _LOGGER.error(f"Failed to connect to FCSP device: {err}")
        raise ConfigEntryNotReady from err

    # Load cached data (frozen peas > no peas)
    cache = LocalFcspCache(hass)
    cached_data = await cache.load()

    # Get scan interval, falling back on defaults, and enforce minimum
    scan_interval = max(
        entry.options.get(CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)),
        MIN_SCAN_INTERVAL,
    )

    # Create our coordinator — it handles live data fetch, cache saving, and exposes .data for sensors.
    coordinator = FcspDataUpdateCoordinator(
        hass=hass,
        config_entry=entry,
        fcsp=fcsp,
        cache_store=cache,
        cached_data=cached_data,
        scan_interval=scan_interval,
    )

    # Store the coordinator so sensors and other platforms can access it.
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Kick off the first refresh in the background — no blocking HA startup!
    hass.async_create_task(coordinator.async_refresh())

    # Forward setup to sensor and binary_sensor platforms (e.g. your GridDown entity)
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "binary_sensor"])

    return True

async def async_unload_entry(hass, entry):
    """
    Unload a config entry and clean up.
    """
    await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    await hass.config_entries.async_forward_entry_unload(entry, "binary_sensor")
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True
