import logging
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.core import callback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Let's set up a class to determine if the FCSP is online or not. It's a simple, simple binary sensor (or will be when we're done)

class FCSPOnlineBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor to determine if we have a connection to the FCSP, or if it's offline"""
    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._attr_name = "FCSP Online"
        self._attr_unique_id = f"local_fcsp_online_{entry_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"charge_station_{entry_id}")},
        )
        self._attr_icon_on = "mdi:wifi-check"
        self._attr_icon_off = "mdi:wifi-off"

    @property
    def is_on(self) -> bool:
        """Return true if the device is online"""
        val = not self.coordinator.offline
        _LOGGER.debug("FCSP connectivity state is %s", val)
        return val
        
    @property
    def icon(self) -> str:
        """Return the appropriate icon based on online state."""
        return self._attr_icon_on if self.is_on else self._attr_icon_off

    @callback
    def _handle_coordinator_update(self) -> None:
        """Respond to data updates from the coordinator."""
        self.async_write_ha_state()

# OK, let's create the binary sensor now.

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the Online binary sensor from a config entry."""
    coordinator = hass.data[DOMAIN].get(entry.entry_id)
    if not coordinator:
        _LOGGER.error("No coordinator found for entry %s", entry.entry_id)
        return


    _LOGGER.debug("Creating Online BinarySensor for entry %s", entry.entry_id)
    async_add_entities(
        [FCSPOnlineBinarySensor(coordinator, entry.entry_id)],
        update_before_add=True,
    )
